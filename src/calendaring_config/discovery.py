from pathlib import Path

SYSTEM_PATHS: tuple[Path, ...] = ()


def find_config_file(path: str | Path | None = None) -> Path | None:
    raise NotImplementedError


def section_name(name: str | None = None) -> str:
    raise NotImplementedError
