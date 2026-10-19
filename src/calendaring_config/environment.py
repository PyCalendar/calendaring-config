"""Environment variables, one connection of one kind (docs/format.md, "The environment")."""

import os
from typing import Any

from .errors import ConfigError
from .secrets import SECRETS

__all__ = ["apply_environment", "environment_connections"]

# Every PREFIX_<KEY> is the key <key> of a section of that kind
PREFIXES = {"caldav": "CALDAV_", "jmap": "JMAP_"}
# Short names, used when the long one is not set
ALIASES = {"user": "username", "pass": "password"}
# PREFIX_CONFIG_* choose the file and the section; auth is an object, not a string
SKIPPED_KEYS = ("auth", "config")
SKIPPED_PREFIX = "config_"
# A secret's sources: a value from the environment replaces the file's other ones
SECRET_SUFFIXES = ("", "_command", "_keyring")


def _sources(secret: str) -> list[str]:
    return [secret + suffix for suffix in SECRET_SUFFIXES]


def _timeout(name: str, value: str) -> float:
    try:
        return float(value)
    except ValueError:
        raise ConfigError(f"{name} must be a number of seconds") from None


def _from_environment(kind: str) -> dict[str, Any]:
    """The variables set for ``kind``.  An empty string counts: a server may need an empty password."""
    prefix = PREFIXES.get(kind)
    if prefix is None:
        return {}
    found: dict[str, tuple[str, str]] = {}  # key -> (name, value), long names over aliases
    for name, value in os.environ.items():
        key = name[len(prefix) :].lower() if name.startswith(prefix) else ""
        if not key or key in SKIPPED_KEYS or key.startswith(SKIPPED_PREFIX):
            continue
        if key in ALIASES:
            found.setdefault(ALIASES[key], (name, value))
        else:
            found[key] = (name, value)
    for secret in SECRETS:
        given = [found[k][0] for k in _sources(secret) if k in found]
        if len(given) > 1:
            raise ConfigError(f"the environment gives {secret} more than once: {', '.join(given)}")
    values: dict[str, Any] = {}
    for key, (name, value) in found.items():
        if key == "url" and not value:
            continue
        values[key] = _timeout(name, value) if key == "timeout" else value
    return values


def environment_connections() -> list[tuple[str, dict[str, Any]]]:
    """``(kind, params)`` for each kind whose URL is in the environment."""
    found = ((kind, _from_environment(kind)) for kind in PREFIXES)
    return [(kind, params) for kind, params in found if "url" in params]


def apply_environment(kind: str, params: dict[str, Any]) -> None:
    """Override ``params`` key by key.  A secret given here replaces the file's command or keyring entry."""
    for key, value in _from_environment(kind).items():
        for secret in SECRETS:
            if key in _sources(secret):
                for source in _sources(secret):
                    params.pop(source, None)
        params[key] = value
