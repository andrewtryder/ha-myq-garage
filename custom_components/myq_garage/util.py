"""Shared helpers for the MyQ Garage integration."""

from __future__ import annotations

from urllib.parse import urlparse

_DEFAULT_PORTS = {"http": 80, "https": 443}


class InvalidURLError(Exception):
    """Raised when the configured API URL is not usable."""


def normalize_url(url: str) -> str:
    """Validate and normalize the API base URL.

    Raises InvalidURLError if the URL does not use http/https, has no
    hostname, embeds credentials, or carries a query string or fragment
    (which would otherwise be silently dropped when building API request
    URLs). The hostname is lowercased and a redundant default port
    (``:80`` for http, ``:443`` for https) is stripped, so equivalent URLs
    normalize identically for duplicate-entry detection. This normalized
    form is also what gets stored as the entry's configured URL.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("URL must use the http or https scheme")
    if not parsed.hostname:
        raise InvalidURLError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise InvalidURLError("URL must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise InvalidURLError("URL must not contain a query string or fragment")

    try:
        port = parsed.port
    except ValueError as err:
        raise InvalidURLError("URL contains an invalid port") from err

    hostname = parsed.hostname.lower()
    if ":" in hostname:  # IPv6 literal
        hostname = f"[{hostname}]"

    if port is not None and port != _DEFAULT_PORTS[parsed.scheme]:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{netloc}{path}"
