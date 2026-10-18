import os
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

import calendaring_config.discovery


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No test sees the real home, the real /etc or the caller's variables."""
    for name in list(os.environ):
        if name.startswith(("CALDAV_", "JMAP_", "CALENDARING_")):
            monkeypatch.delenv(name)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(calendaring_config.discovery, "SYSTEM_PATHS", (tmp_path / "etc" / "calendar.conf",))


@pytest.fixture
def write_config(tmp_path: Path) -> Callable[..., Path]:
    def write(data: object, name: str = "calendar.yaml", mode: int = 0o600) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else yaml.safe_dump(data))
        path.chmod(mode)
        return path

    return write
