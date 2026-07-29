from __future__ import annotations

import datetime as dt
import hashlib
import ipaddress
import socket
from collections.abc import Callable, Iterable
from email.utils import parsedate_to_datetime
from typing import Protocol, runtime_checkable
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx
from defusedxml import ElementTree  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]
from httpx._transports.default import ResponseStream, map_httpcore_exceptions

from ..agent.models import NewsItem

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
NEWS_QUERY = '("SRAG" OR "síndrome respiratória aguda grave") when:14d'
NEWS_PARAMS = {"q": NEWS_QUERY, "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"}
_MAX_ITEMS = 5
_WINDOW_DAYS = 14
_MAX_REDIRECTS = 5
_MAX_RESPONSE_BYTES = 1_048_576
_MAX_TITLE_LENGTH = 300
_MAX_SOURCE_LENGTH = 100
_MAX_URL_LENGTH = 2_048
_TRANSIENT_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})
_TRANSIENT_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)
_ALLOWED_SOURCE_NAMES = frozenset(
    {"ministério da saúde", "fiocruz", "agência brasil", "g1", "estadão", "folha de s.paulo"}
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
    return " ".join(source.casefold().split()) in _ALLOWED_SOURCE_NAMES


def _resolve_hostname(hostname: str) -> tuple[str, ...]:
    addresses = tuple(
        sorted({item[4][0] for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)})
    )
    if not addresses:
        raise ValueError("news DNS result is empty")
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("news DNS result contains a non-global address")
    return addresses


class PinnedNetworkBackend(httpcore.NetworkBackend):
    """Connect only to preflight-validated addresses while preserving the origin hostname."""

    def __init__(self) -> None:
        self._backend = httpcore.SyncBackend()
        self._pins: dict[str, str] = {}

    def pin(self, hostname: str, address: str) -> None:
        self._pins[hostname.lower().rstrip(".")] = address

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:
        try:
            address = self._pins[host.lower().rstrip(".")]
        except KeyError as exc:
            raise OSError(f"no validated DNS pin for {host}") from exc
        return self._backend.connect_tcp(
            address,
            port,
            timeout,
            local_address,
            socket_options,
        )

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.NetworkStream:
        return self._backend.connect_unix_socket(path, timeout, socket_options)

    def sleep(self, seconds: float) -> None:
        self._backend.sleep(seconds)


class PinnedHTTPTransport(httpx.BaseTransport):
    """HTTPX transport whose httpcore pool retains the origin for Host and TLS SNI."""

    def __init__(self) -> None:
        self._network_backend = PinnedNetworkBackend()
        self._pool = httpcore.ConnectionPool(network_backend=self._network_backend)

    def pin_host(self, hostname: str, address: str) -> None:
        self._network_backend.pin(hostname, address)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        assert isinstance(request.stream, httpx.SyncByteStream)
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        with map_httpcore_exceptions():
            response = self._pool.handle_request(core_request)
        assert isinstance(response.stream, Iterable)
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=ResponseStream(response.stream),
            extensions=response.extensions,
        )

    def close(self) -> None:
        self._pool.close()


@runtime_checkable
class PinningTransport(Protocol):
    """Transport contract required before making an SSRF-sensitive request."""

    def pin_host(self, hostname: str, address: str) -> None: ...


def _pin_for_request(client: httpx.Client, hostname: str, address: str) -> None:
    transport = getattr(client, "_transport", None)
    if not isinstance(transport, PinningTransport):
        raise ValueError("news client transport must implement pin_host")
    transport.pin_host(hostname, address)


def _request_bounded(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None,
    resolver: Callable[[str], tuple[str, ...]],
) -> tuple[httpx.Response, bytes]:
    _validate_http_url(url)
    if not _request_domain_allowed(url):
        raise ValueError("news request targets a domain outside the allowlist")
    hostname = urlsplit(url).hostname
    assert hostname is not None
    addresses = resolver(hostname)
    if not addresses:
        raise ValueError("news DNS result is empty")
    parsed_addresses = tuple(ipaddress.ip_address(address) for address in addresses)
    if any(not address.is_global for address in parsed_addresses):
        raise ValueError("news DNS result contains a non-global address")
    _pin_for_request(client, hostname, str(parsed_addresses[0]))
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with client.stream("GET", url, params=params, follow_redirects=False) as response:
                if response.status_code in _TRANSIENT_STATUSES:
                    error = httpx.HTTPStatusError(
                        "transient RSS response", request=response.request, response=response
                    )
                    if attempt == 0:
                        last_error = error
                        continue
                    raise error
                if response.is_redirect:
                    return response, b""
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > _MAX_RESPONSE_BYTES:
                        raise ValueError("news response exceeds 1 MiB")
                return response, bytes(content)
        except _TRANSIENT_ERRORS as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise
    assert last_error is not None
    raise last_error


def _get_bounded_with_redirects(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None,
    resolver: Callable[[str], tuple[str, ...]],
) -> tuple[str, bytes]:
    """Follow policy-checked redirects manually and return the bounded final body."""
    current = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        response, content = _request_bounded(client, current, params=params, resolver=resolver)
        if not response.is_redirect:
            return str(response.url), content
        if redirect_count == _MAX_REDIRECTS:
            raise ValueError("news redirect limit exceeded")
        location = response.headers.get("location")
        if not location:
            raise ValueError("news redirect omitted Location")
        current = urljoin(current, location)
        params = None
    raise ValueError("news redirect resolution failed")


def _get_bounded(client: httpx.Client, url: str, *, params: dict[str, str] | None = None) -> bytes:
    """Perform validated, pinned RSS requests with manual redirects and a 1 MiB cap."""
    return _get_bounded_with_redirects(client, url, params=params, resolver=_resolve_hostname)[1]


def _resolve_url(
    client: httpx.Client, url: str, *, resolver: Callable[[str], tuple[str, ...]]
) -> str:
    current = url
    for redirect_count in range(_MAX_REDIRECTS + 1):
        response, _ = _request_bounded(client, current, params=None, resolver=resolver)
        if not response.is_redirect:
            final_url = str(response.url)
            _validate_http_url(final_url)
            if not _allowed_domain(final_url):
                raise ValueError("news final URL is outside the publisher allowlist")
            return final_url
        if redirect_count == _MAX_REDIRECTS:
            raise ValueError("news redirect limit exceeded")
        location = response.headers.get("location")
        if not location:
            raise ValueError("news redirect omitted Location")
        current = urljoin(current, location)
    raise ValueError("news redirect resolution failed")


def _parse_feed(
    content: bytes,
    *,
    client: httpx.Client,
    collected_at: dt.datetime,
    resolver: Callable[[str], tuple[str, ...]],
) -> tuple[NewsItem, ...]:
    try:
        root = ElementTree.fromstring(
            content, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except DefusedXmlException as exc:
        raise ValueError("news XML contains a forbidden DTD or entity") from exc
    except ElementTree.ParseError as exc:
        raise ValueError("news XML is malformed") from exc
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
            final_url = _resolve_url(client, source_url or link, resolver=resolver)
            if (
                len(title) > _MAX_TITLE_LENGTH
                or len(source) > _MAX_SOURCE_LENGTH
                or len(final_url) > _MAX_URL_LENGTH
            ):
                raise ValueError("news item exceeds a field bound")
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
    def __init__(
        self,
        client: httpx.Client,
        *,
        resolver: Callable[[str], tuple[str, ...]] = _resolve_hostname,
    ) -> None:
        self._client = client
        self._resolver = resolver

    def collect(self, *, generated_at: dt.datetime) -> tuple[NewsItem, ...]:
        if generated_at.utcoffset() != dt.timedelta(0):
            raise ValueError("generated_at must be timezone-aware UTC")
        content = _get_bounded_with_redirects(
            self._client, GOOGLE_NEWS_RSS, params=NEWS_PARAMS, resolver=self._resolver
        )[1]
        return _parse_feed(
            content, client=self._client, collected_at=generated_at, resolver=self._resolver
        )
