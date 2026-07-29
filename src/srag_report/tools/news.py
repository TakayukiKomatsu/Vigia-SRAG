from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit

import httpx

from ..agent.models import NewsItem

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
NEWS_QUERY = '("SRAG" OR "síndrome respiratória aguda grave") when:14d'
NEWS_PARAMS = {"q": NEWS_QUERY, "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}
_MAX_ITEMS = 5
_WINDOW_DAYS = 14
_MAX_REDIRECTS = 5
_ALLOWED_SOURCE_NAMES = frozenset(
    {
        "ministério da saúde",
        "fiocruz",
        "agência brasil",
        "g1",
        "estadão",
        "folha de s.paulo",
    }
)
_ALLOWED_DOMAINS = (
    "gov.br",
    "saude.gov.br",
    "fiocruz.br",
    "agenciabrasil.ebc.com.br",
    "g1.globo.com",
    "estadao.com.br",
    "folha.uol.com.br",
)


def _validate_http_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("news URL must be absolute HTTP(S)")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("news URL must not contain credentials")
    if parsed.port not in {None, 80, 443}:
        raise ValueError("news URL uses an unexpected port")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("news URL must not target a non-global address")


def _allowed_domain(url: str) -> bool:
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in _ALLOWED_DOMAINS)


def _request_domain_allowed(url: str) -> bool:
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    return hostname == "news.google.com" or _allowed_domain(url)


def _allowed_source(source: str) -> bool:
    normalized = " ".join(source.casefold().split())
    return normalized in _ALLOWED_SOURCE_NAMES


def _resolve_url(client: httpx.Client, url: str) -> str:
    current = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        _validate_http_url(current)
        if not _request_domain_allowed(current):
            raise ValueError("news redirect targets a domain outside the allowlist")
        response = client.get(current, follow_redirects=False)
        if response.is_redirect:
            if redirect_count == _MAX_REDIRECTS:
                raise ValueError("news redirect limit exceeded")
            location = response.headers.get("location")
            if not location:
                raise ValueError("news redirect omitted Location")
            current = urljoin(current, location)
            continue
        response.raise_for_status()
        final_url = str(response.url)
        _validate_http_url(final_url)
        if not _allowed_domain(final_url):
            raise ValueError("news final URL is outside the publisher allowlist")
        return final_url
    raise ValueError("news redirect resolution failed")


def _parse_feed(
    content: bytes,
    *,
    client: httpx.Client,
    collected_at: dt.datetime,
) -> tuple[NewsItem, ...]:
    root = ET.fromstring(content)
    oldest = collected_at - dt.timedelta(days=_WINDOW_DAYS)
    accepted: list[NewsItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for node in root.findall("./channel/item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        published_text = (node.findtext("pubDate") or "").strip()
        source_node = node.find("source")
        source = (source_node.text or "").strip() if source_node is not None else ""
        source_url = (source_node.get("url") or "").strip() if source_node is not None else ""
        if not title or not link or not published_text or not source:
            continue
        try:
            published_at = parsedate_to_datetime(published_text)
            if published_at.tzinfo is None:
                continue
            published_at = published_at.astimezone(dt.UTC)
            if published_at < oldest or published_at > collected_at:
                continue
            if source_url:
                _validate_http_url(source_url)
                if not _allowed_domain(source_url):
                    raise ValueError("news source URL is outside the publisher allowlist")
                final_url = source_url
            else:
                final_url = _resolve_url(client, link)
        except (ValueError, httpx.HTTPError, TypeError):
            continue
        if not (_allowed_domain(final_url) and _allowed_source(source)):
            continue
        normalized_title = " ".join(title.casefold().split())
        if final_url in seen_urls or normalized_title in seen_titles:
            continue
        seen_urls.add(final_url)
        seen_titles.add(normalized_title)
        digest = hashlib.sha256(f"{final_url}\n{published_at.isoformat()}".encode()).hexdigest()
        accepted.append(
            NewsItem(
                news_id=f"news-{digest[:16]}",
                title=title,
                source=source,
                final_url=final_url,
                published_at=published_at,
                collected_at=collected_at,
            )
        )
        if len(accepted) == _MAX_ITEMS:
            break
    return tuple(accepted)


class GoogleNewsRssTool:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def collect(self, *, generated_at: dt.datetime) -> tuple[NewsItem, ...]:
        """Fetch the fixed Google News query with one transient retry."""
        if generated_at.utcoffset() != dt.timedelta(0):
            raise ValueError("generated_at must be timezone-aware UTC")
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self._client.get(GOOGLE_NEWS_RSS, params=NEWS_PARAMS)
                response.raise_for_status()
                return _parse_feed(
                    response.content,
                    client=self._client,
                    collected_at=generated_at,
                )
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt == 0 and (
                    isinstance(exc, httpx.TransportError)
                    or exc.response.status_code in {408, 409, 429}
                    or exc.response.status_code >= 500
                ):
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("news collection failed without an error")
