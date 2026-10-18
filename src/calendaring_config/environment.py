"""Environment variables, one connection of one kind (docs/format.md, "The environment")."""

import os
from typing import Any

from .errors import ConfigError

__all__ = ["apply_environment", "environment_connections"]

# key -> variables, the first set one wins
VARIABLES: dict[str, dict[str, tuple[str, ...]]] = {
    "caldav": {
        "url": ("CALDAV_URL",),
        "username": ("CALDAV_USERNAME", "CALDAV_USER"),
        "password": ("CALDAV_PASSWORD", "CALDAV_PASS"),
        "proxy": ("CALDAV_PROXY",),
        "timeout": ("CALDAV_TIMEOUT",),
        "auth_type": ("CALDAV_AUTH_TYPE",),
        "ssl_verify_cert": ("CALDAV_SSL_VERIFY_CERT",),
        "ssl_cert": ("CALDAV_SSL_CERT",),
    },
    "jmap": {
        "url": ("JMAP_URL",),
        "username": ("JMAP_USERNAME",),
        "password": ("JMAP_PASSWORD",),
        "auth_type": ("JMAP_AUTH_TYPE",),
        "timeout": ("JMAP_TIMEOUT",),
    },
}


def _timeout(name: str, value: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ConfigError(f"{name} must be a number of seconds") from None


def _from_environment(kind: str) -> dict[str, Any]:
    """The variables set for ``kind``.  An empty string counts: a server may need an empty password."""
    values: dict[str, Any] = {}
    for key, names in VARIABLES.get(kind, {}).items():
        name = next((n for n in names if n in os.environ), None)
        if name is None:
            continue
        value = os.environ[name]
        if key == "url" and not value:
            continue
        values[key] = _timeout(name, value) if key == "timeout" else value
    return values


def environment_connections() -> list[tuple[str, dict[str, Any]]]:
    """``(kind, params)`` for each kind whose URL is in the environment."""
    found = ((kind, _from_environment(kind)) for kind in VARIABLES)
    return [(kind, params) for kind, params in found if "url" in params]


def apply_environment(kind: str, params: dict[str, Any]) -> None:
    """Override ``params`` key by key.  A secret given here replaces the file's command or keyring entry."""
    for key, value in _from_environment(kind).items():
        params[key] = value
        params.pop(f"{key}_command", None)
        params.pop(f"{key}_keyring", None)
