"""docs/format.md, "Finding the file" and "Choosing the section"."""

from pathlib import Path

import pytest

from calendaring_config import ConfigError, find_config_file, section_name


def _home() -> Path:
    return Path.home()


def test_explicit_path_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.yaml"
    explicit.touch()
    other = tmp_path / "other.yaml"
    other.touch()
    monkeypatch.setenv("CALENDARING_CONFIG_FILE", str(other))
    assert find_config_file(explicit) == explicit


def test_calendaring_variable_before_caldav_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ours, theirs = tmp_path / "ours.yaml", tmp_path / "theirs.yaml"
    ours.touch()
    theirs.touch()
    monkeypatch.setenv("CALENDARING_CONFIG_FILE", str(ours))
    monkeypatch.setenv("CALDAV_CONFIG_FILE", str(theirs))
    assert find_config_file() == ours
    monkeypatch.delenv("CALENDARING_CONFIG_FILE")
    assert find_config_file() == theirs


@pytest.mark.parametrize("variable", ["CALENDARING_CONFIG_FILE", "CALDAV_CONFIG_FILE"])
def test_named_file_that_does_not_exist_is_an_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, variable: str
) -> None:
    monkeypatch.setenv(variable, str(tmp_path / "missing.yaml"))
    with pytest.raises(ConfigError, match="missing.yaml"):
        find_config_file()
    with pytest.raises(ConfigError, match="gone.yaml"):
        find_config_file(tmp_path / "gone.yaml")


def test_nothing_found_is_not_an_error() -> None:
    assert find_config_file() is None


def test_pycal_path_comes_before_caldav_paths() -> None:
    caldav = _home() / ".config" / "caldav" / "calendar.conf"
    caldav.parent.mkdir(parents=True)
    caldav.touch()
    assert find_config_file() == caldav
    pycal = _home() / ".config" / "pycal" / "calendar.yaml"
    pycal.parent.mkdir(parents=True)
    pycal.touch()
    assert find_config_file() == pycal


def test_xdg_config_home_is_honoured(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    pycal = tmp_path / "xdg" / "pycal" / "calendar.yaml"
    pycal.parent.mkdir(parents=True)
    pycal.touch()
    assert find_config_file() == pycal


def test_section_name_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    assert section_name() == "default"
    monkeypatch.setenv("CALDAV_CONFIG_SECTION", "theirs")
    assert section_name() == "theirs"
    monkeypatch.setenv("CALENDARING_CONFIG_SECTION", "ours")
    assert section_name() == "ours"
    assert section_name("given") == "given"
