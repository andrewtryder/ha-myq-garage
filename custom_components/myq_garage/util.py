"""Shared helpers for the MyQ Garage integration."""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlparse

from homeassistant.util.network import is_ip_address, is_local

_DEFAULT_PORTS = {"http": 80, "https": 443}
_LOCAL_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
    }
)


class InvalidURLError(Exception):
    """Raised when the configured API URL is not usable."""


class InsecureURLError(InvalidURLError):
    """Raised when plain HTTP is used for a non-local host."""


def is_allowed_insecure_http_host(hostname: str) -> bool:
    """Return True if plain HTTP is permitted for the given hostname.

    HTTPS is required for public hosts. HTTP is only allowed for loopback,
    RFC1918 private addresses, link-local addresses, localhost, and common
    local development / mDNS hostnames (``.local``).
    """
    host = hostname.strip("[]").lower().rstrip(".")
    if host in _LOCAL_HOSTNAMES or host.endswith(".local"):
        return True
    if not is_ip_address(host):
        return False
    return is_local(ip_address(host))


def normalize_url(url: str) -> str:
    """Validate and normalize the API base URL.

    Raises InvalidURLError if the URL does not use http/https, has no
    hostname, embeds credentials, or carries a query string or fragment
    (which would otherwise be silently dropped when building API request
    URLs). Raises InsecureURLError when plain HTTP targets a non-local
    host. The hostname is lowercased and a redundant default port
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
    if parsed.scheme == "http" and not is_allowed_insecure_http_host(hostname):
        raise InsecureURLError(
            "Plain HTTP is only allowed for localhost and private/link-local "
            "addresses; use HTTPS for public hosts"
        )

    if ":" in hostname:  # IPv6 literal
        hostname = f"[{hostname}]"

    if port is not None and port != _DEFAULT_PORTS[parsed.scheme]:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{netloc}{path}"
