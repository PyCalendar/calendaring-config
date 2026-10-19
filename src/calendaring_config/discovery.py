"""Which file to read, and which section of it (docs/format.md, "Finding the file")."""

import os
from pathlib import Path

from .errors import ConfigError

__all__ = ["SYSTEM_PATHS", "find_config_file", "requested_section", "search_path", "section_name"]

FILE_VARIABLES = ("CALENDARING_CONFIG_FILE", "CALDAV_CONFIG_FILE")
SECTION_VARIABLES = ("CALENDARING_CONFIG_SECTION", "CALDAV_CONFIG_SECTION")

# caldav's system-wide paths, searched last
SYSTEM_PATHS: tuple[Path, ...] = (Path("/etc/calendar.conf"), Path("/etc/caldav/calendar.conf"))


def search_path() -> list[Path]:
    """The files searched when no path is given, in order."""
    home_config = Path.home() / ".config"
    xdg = Path(os.environ.get("XDG_CONFIG_HOME") or home_config)
    return [
        xdg / "pycal" / "calendar.yaml",
        # caldav's per-user paths, so existing files keep working where they are
        home_config / "caldav" / "calendar.conf",
        home_config / "caldav" / "calendar.yaml",
        home_config / "caldav" / "calendar.json",
        home_config / "calendar.conf",
        *SYSTEM_PATHS,
    ]


def find_config_file(path: str | Path | None = None, environment: bool = True) -> Path | None:
    """The configuration file to read, or ``None`` when there is none.

    A file named by ``path`` or by an environment variable must exist.
    """
    if path is None and environment:
        path = next((os.environ[v] for v in FILE_VARIABLES if os.environ.get(v)), None)
    if path is not None:
        named = Path(path).expanduser()
        if not named.is_file():
            raise ConfigError(f"configuration file {named} does not exist")
        return named
    return next((p for p in search_path() if p.is_file()), None)


def requested_section(name: str | None = None, environment: bool = True) -> str | None:
    """``name``, else the section named in the environment, else ``None``."""
    if name or not environment:
        return name or None
    return next((os.environ[v] for v in SECTION_VARIABLES if os.environ.get(v)), None)


def section_name(name: str | None = None, environment: bool = True) -> str:
    """``name``, else the section named in the environment, else ``default``."""
    return requested_section(name, environment) or "default"
