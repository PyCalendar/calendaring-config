"""The shared configuration file of caldav, calendaring and calendaring-jmap.

The format is specified in ``docs/format.md``.
"""

from .discovery import find_config_file, section_name
from .errors import ConfigError
from .loader import Connection, expand_section, load, read_config

__all__ = ["ConfigError", "Connection", "expand_section", "find_config_file", "load", "read_config", "section_name"]
