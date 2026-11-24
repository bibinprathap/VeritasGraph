"""Keep inference on-prem: refuse public model endpoints unless explicitly allowed."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse


class RemoteEndpointError(RuntimeError):
    pass


def assert_local_endpoint(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RemoteEndpointError(f"Model endpoint must be an http(s) URL: {url!r}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port)
    except socket.gaierror as exc:
        raise RemoteEndpointError(f"Cannot resolve model host {parsed.hostname!r}") from exc
    allow_remote = os.environ.get("VG_LLM_ALLOW_REMOTE", "").strip() == "1"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise RemoteEndpointError(f"Refusing model endpoint on {ip}")
        if ip.is_global and not allow_remote:
            raise RemoteEndpointError(
                f"Model endpoint {parsed.hostname} resolves to public address {ip}. "
                "Inference is on-prem only; set VG_LLM_ALLOW_REMOTE=1 to override."
            )
