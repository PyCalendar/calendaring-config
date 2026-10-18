"""docs/format.md, "The environment"."""

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from calendaring_config import ConfigError, Connection, load

Write = Callable[..., Path]

FAIL = [sys.executable, "-c", "raise SystemExit(1)"]

CONFIG = {
    "default": {"kind": "caldav", "url": "https://dav.example.com/", "username": "alice", "password_command": FAIL},
    "jmap": {"kind": "jmap", "url": "https://jmap.example.com/", "username": "bob", "password": "file"},
    "unknown": {"url": "https://feed.example.com/", "username": "carol"},
    "old": {"caldav_url": "https://old.example.com/", "caldav_user": "frank"},
    "fine": {"kind": "caldav", "url": "https://dav.example.com/", "password": "file"},
    "both_fine": {"contains": ["fine", "jmap"]},
    "both": {"contains": ["default", "jmap"]},
}


def test_url_in_environment_skips_the_file(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_config("not: [valid")
    monkeypatch.setenv("CALDAV_URL", "https://env.example.com/")
    monkeypatch.setenv("CALDAV_USER", "dave")
    monkeypatch.setenv("JMAP_URL", "https://jmap-env.example.com/")
    monkeypatch.setenv("JMAP_TIMEOUT", "30")
    assert load(path, "both") == [
        Connection("environment", "caldav", {"url": "https://env.example.com/", "username": "dave"}),
        Connection("environment", "jmap", {"url": "https://jmap-env.example.com/", "timeout": 30.0}),
    ]


def test_secret_from_environment_replaces_the_command(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_PASSWORD", "from-env")
    [conn] = load(write_config(CONFIG))
    assert conn.params == {"url": "https://dav.example.com/", "username": "alice", "password": "from-env"}


def test_variables_of_another_kind_do_not_apply(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_PASSWORD", "from-env")
    path = write_config(CONFIG)
    assert load(path, "jmap")[0].params["password"] == "file"
    assert "password" not in load(path, "unknown")[0].params


def test_jmap_variables_apply_to_a_jmap_section(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JMAP_USERNAME", "eve")
    assert load(write_config(CONFIG), "jmap")[0].params["username"] == "eve"


def test_variables_without_url_skip_a_multi_section_expansion(
    write_config: Write, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JMAP_PASSWORD", "from-env")
    monkeypatch.setenv("CALDAV_PASSWORD", "from-env")
    path = write_config(CONFIG)
    assert [c.params["password"] for c in load(path, "both_fine")] == ["file", "file"]
    with pytest.raises(ConfigError, match="default"):  # the env did not hide the failing command
        load(path, "both")


def test_variables_apply_to_an_old_style_section(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_PASSWORD", "")
    [conn] = load(write_config(CONFIG), "old")
    assert conn.params == {"url": "https://old.example.com/", "username": "frank", "password": ""}


def test_timeout_must_be_a_number(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_URL", "https://env.example.com/")
    monkeypatch.setenv("CALDAV_TIMEOUT", "2.5")
    assert load()[0].params["timeout"] == 2.5
    monkeypatch.setenv("CALDAV_TIMEOUT", "soon")
    with pytest.raises(ConfigError, match="CALDAV_TIMEOUT"):
        load()
