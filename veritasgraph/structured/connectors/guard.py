"""Where a connection may point: network allowlist for servers, file root for files."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path

from sqlalchemy.engine import make_url

from studio_api.netguard import is_blocked
from veritasgraph.structured import config
from veritasgraph.structured.connectors.dialects import Dialect, dialect_for
from veritasgraph.structured.errors import UnsafeConnection

# Driver options that make the client read local files or service definitions.
_FORBIDDEN_QUERY_KEYS = {"passfile", "service", "servicefile", "sslkey", "sslcert", "sslrootcert",
                         "local_infile", "read_default_file", "init_command"}


def check_dsn(dsn: str) -> Dialect:
    url = make_url(dsn)
    dialect = dialect_for(dsn)
    bad = _FORBIDDEN_QUERY_KEYS & {k.lower() for k in url.query}
    if bad:
        raise UnsafeConnection(f"Connection option(s) not allowed: {', '.join(sorted(bad))}")
    if dialect.file_based:
        _check_file(url.database)
    else:
        _check_host(url.host, url.port)
    return dialect


def _check_file(database: str | None) -> None:
    root = config.file_root()
    if root is None:
        raise UnsafeConnection("File databases are disabled: set VG_STRUCTURED_FILE_ROOT.")
    if not database or database == ":memory:":
        raise UnsafeConnection("A database file path is required.")
    path = Path(database).resolve()
    if not path.is_relative_to(root):
        raise UnsafeConnection("Database files must live under VG_STRUCTURED_FILE_ROOT.")
    if not path.is_file():
        raise UnsafeConnection("Database file does not exist.")


def _check_host(host: str | None, port: int | None) -> None:
    if not host:
        raise UnsafeConnection("Connection is missing a host.")
    try:
        infos = socket.getaddrinfo(host, port or 0)
    except socket.gaierror as exc:
        raise UnsafeConnection(f"Cannot resolve host '{host}'.") from exc
    allowed = config.allowed_networks()
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if is_blocked(ip, allowed):
            raise UnsafeConnection(
                f"Host '{host}' resolves to non-public address {ip}. "
                "Add its network to VG_STRUCTURED_ALLOWED_NETWORKS to allow it."
            )
