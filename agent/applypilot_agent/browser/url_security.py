"""Strict URL validation and SSRF / DNS-rebinding protections for untrusted application URLs."""

from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """Raised when a target URL violates scheme, credential, or network isolation rules."""


@dataclass(frozen=True)
class ValidatedTarget:
    """Validated target URL with its resolved non-private IP addresses."""

    url: str
    scheme: str
    hostname: str
    port: int
    resolved_ips: tuple[str, ...]


_LOCALHOST_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1"})


def _is_disallowed_ip(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address, allow_loopback: bool) -> bool:
    """Check whether an IP address belongs to a private, link-local, reserved, or loopback range."""
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped is not None:
        ip_obj = ip_obj.ipv4_mapped

    if ip_obj.is_loopback:
        return not allow_loopback
    return (
        ip_obj.is_private
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def validate_target_url(raw_url: str, *, allow_localhost: bool = False) -> ValidatedTarget:
    """
    Validate an untrusted URL before opening it in Playwright.

    Blocks non-HTTP(S) schemes, embedded credentials, private networks, cloud metadata IPs
    (e.g. 169.254.169.254), and DNS rebinding to loopback/private addresses.
    """
    url = (raw_url or "").strip()
    if not url or len(url) > 2048:
        raise UnsafeURLError("URL must be a non-empty string under 2048 characters.")

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise UnsafeURLError(f"Unsupported URL scheme '{scheme or 'none'}'; only http and https are allowed.")

    if parsed.username or parsed.password:
        raise UnsafeURLError("Embedded credentials in URLs are forbidden.")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise UnsafeURLError("URL must include a valid hostname.")

    port = parsed.port or (443 if scheme == "https" else 80)
    is_explicit_localhost = hostname in _LOCALHOST_HOSTNAMES

    if is_explicit_localhost and not allow_localhost:
        raise UnsafeURLError("Localhost target URLs are blocked unless explicitly enabled for controlled testing.")

    try:
        addr_infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve hostname '{hostname}'.") from exc

    resolved_ips: list[str] = []
    for info in addr_infos:
        sockaddr = info[4]
        ip_str = str(sockaddr[0]).split("%")[0]
        ip_obj = ipaddress.ip_address(ip_str)
        # Anti-DNS-rebinding: only explicit localhost hostnames may ever resolve to loopback when allow_localhost=True.
        allow_this_loopback = allow_localhost and is_explicit_localhost
        if _is_disallowed_ip(ip_obj, allow_loopback=allow_this_loopback):
            raise UnsafeURLError(f"Target IP address '{ip_str}' is in a restricted network range.")
        if ip_str not in resolved_ips:
            resolved_ips.append(ip_str)

    if not resolved_ips:
        raise UnsafeURLError(f"No valid IP addresses resolved for '{hostname}'.")

    return ValidatedTarget(
        url=url,
        scheme=scheme,
        hostname=hostname,
        port=port,
        resolved_ips=tuple(resolved_ips),
    )

