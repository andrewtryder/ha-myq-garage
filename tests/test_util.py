"""Tests for URL normalization and transport security policy."""

import pytest

from custom_components.myq_garage.util import (
    InsecureURLError,
    InvalidURLError,
    is_allowed_insecure_http_host,
    normalize_url,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://example.com", "https://example.com"),
        ("https://Example.COM/", "https://example.com"),
        ("https://example.com:443/api/", "https://example.com/api"),
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://127.0.0.1:9000/v1/", "http://127.0.0.1:9000/v1"),
        ("http://192.168.1.10", "http://192.168.1.10"),
        ("http://10.0.0.5/api", "http://10.0.0.5/api"),
        ("http://172.16.5.1", "http://172.16.5.1"),
        ("http://[::1]:8080", "http://[::1]:8080"),
        ("http://homeassistant.local", "http://homeassistant.local"),
        ("http://169.254.10.20", "http://169.254.10.20"),
    ],
)
def test_normalize_url_allows_secure_and_local_forms(raw: str, expected: str) -> None:
    """Public HTTPS and local HTTP URLs normalize successfully."""
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "http://example.com",
        "http://myq-api.example.com/api",
        "http://8.8.8.8",
        "http://1.1.1.1:8080",
    ],
)
def test_normalize_url_rejects_public_http(raw: str) -> None:
    """Plain HTTP to public hosts is rejected."""
    with pytest.raises(InsecureURLError):
        normalize_url(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "ftp://example.com",
        "https://",
        "https://user:pass@example.com",
        "https://example.com/?q=1",
        "https://example.com/#frag",
    ],
)
def test_normalize_url_rejects_invalid_urls(raw: str) -> None:
    """Structurally invalid URLs raise InvalidURLError."""
    with pytest.raises(InvalidURLError):
        normalize_url(raw)


@pytest.mark.parametrize(
    ("host", "allowed"),
    [
        ("localhost", True),
        ("127.0.0.1", True),
        ("::1", True),
        ("10.1.2.3", True),
        ("192.168.0.1", True),
        ("172.16.0.1", True),
        ("169.254.1.1", True),
        ("homeassistant.local", True),
        ("example.com", False),
        ("8.8.8.8", False),
    ],
)
def test_is_allowed_insecure_http_host(host: str, allowed: bool) -> None:
    """HTTP permission matches localhost / private / link-local policy."""
    assert is_allowed_insecure_http_host(host) is allowed
