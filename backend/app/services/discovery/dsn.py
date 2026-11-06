"""Rewrite browser localhost DSNs to Compose service hosts when the API runs in Docker."""

from urllib.parse import urlparse, urlunparse

from app.config import settings

_LOCAL = {"localhost", "127.0.0.1"}


def resolve_dsn(dsn: str) -> str:
    if not getattr(settings, "docker_dsn_rewrite", False):
        return dsn
    parsed = urlparse(dsn)
    host = (parsed.hostname or "").lower()
    if host not in _LOCAL:
        return dsn

    port = parsed.port
    scheme = (parsed.scheme or "").lower()
    if port == 3307:
        new_host, new_port = "mysql-target", 3306
    elif port == 27017 or scheme.startswith("mongodb"):
        new_host, new_port = "mongo", port or 27017
    else:
        new_host, new_port = "mysql-source", port or 3306

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password is not None:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    return urlunparse(parsed._replace(netloc=f"{userinfo}{new_host}:{new_port}"))
