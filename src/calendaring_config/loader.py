from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Connection:
    name: str
    kind: str | None
    params: dict[str, Any]


def read_config(path: str | Path) -> dict[str, dict[str, Any]]:
    raise NotImplementedError


def expand_section(config: dict[str, dict[str, Any]], name: str) -> list[str]:
    raise NotImplementedError


def load(path: str | Path | None = None, section: str | None = None) -> list[Connection]:
    raise NotImplementedError
