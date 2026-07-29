"""Shared pytest fixtures for T-DF-2 tests."""

from __future__ import annotations

import pathlib

import pytest

SYNTHETIC_DIR = pathlib.Path(__file__).parent / "fixtures" / "synthetic"


@pytest.fixture
def synthetic_dir() -> pathlib.Path:
    return SYNTHETIC_DIR
