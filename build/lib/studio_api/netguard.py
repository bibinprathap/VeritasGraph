"""Outbound-request guard (SSRF protection) shared by every Studio HTTP client.

Studio calls operator-configured tool endpoints. Without a guard, anyone able to
register a tool could make the server reach its own loopback services (Ollama,
Studio itself), the operator's LAN, or the cloud metadata service.

Policy:

* Public (globally routable) addresses are allowed.
* Link-local (cloud metadata), multicast, reserved and unspecified addresses
  are always refused.
* Loopback and private ranges (RFC1918, CGNAT, IPv6 ULA) are refused unless the
  operator allowlists them with ``STUDIO_TOOL_ALLOWED_NETWORKS``, e.g.
  ``10.20.0.0/16,127.0.0.1/32``. Enterprise tools often live on internal
  networks, so this is an explicit opt-in rather than a hard block.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from typing import List, Union
from urllib import parse as urlparse

IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


class UnsafeURLError(ValueError):
    """Raised when an outbound URL is malformed or points at a blocked address."""


def allowed_networks() -> List[IPNetwork]:
    nets: List[IPNetwork] = []
    for item in os.environ.get("STUDIO_TOOL_ALLOWED_NETWORKS", "").split(","):
        item = item.strip()
        if item:
            nets.append(ipaddress.ip_network(item, strict=False))
    return nets


def is_blocked(ip: IPAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # ::ffff:127.0.0.1 must be treated as 127.0.0.1
    # Never reachable, even with an allowlist (cloud metadata, broadcast, ...).
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
        return True
    if ip.is_global:
        return False
    # Loopback, RFC1918, CGNAT, ULA: only when the operator allowlisted it.
    return not any(ip in net for net in allowed_networks())


def assert_safe_url(endpoint: str) -> str:
    """Validate scheme/host and refuse non-public targets unless allowlisted."""
    parsed = urlparse.urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Endpoint must be an http:// or https:// URL.")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("Endpoint is missing a host.")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeURLError(f"Invalid port in endpoint: {exc}") from exc

    try:
        infos = socket.getaddrinfo(host, port)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve host '{host}': {exc}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if is_blocked(ip):
            raise UnsafeURLError(
                f"Refusing to call non-public address {ip}. "
                "Add its network to STUDIO_TOOL_ALLOWED_NETWORKS to allow it."
            )
    return endpoint
