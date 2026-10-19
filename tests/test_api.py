"""The API caldav and plann use: kinds, and one section at a time."""

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from calendaring_config import ConfigError, Connection, environment_connections, load, section_connection

Write = Callable[..., Path]

PRINT = [sys.executable, "-c", "print('s3cret')"]
CONFIG = {"default": {"kind": "caldav", "url": "https://dav.example.com/", "username": "alice"}}


def test_url_of_another_kind_does_not_replace_the_file(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JMAP_URL", "https://jmap.example.com/")
    monkeypatch.setenv("CALDAV_PASSWORD", "env")
    path = write_config(CONFIG)
    assert load(path, kinds=("caldav",)) == [
        Connection("default", "caldav", {"url": "https://dav.example.com/", "username": "alice", "password": "env"})
    ]
    assert load(path)[0].kind == "jmap"  # without kinds, as before
    monkeypatch.setenv("CALDAV_URL", "https://env.example.com/")
    assert [c.params["url"] for c in load(path, kinds=("caldav",))] == ["https://env.example.com/"]


def test_environment_connections_by_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_URL", "https://env.example.com/")
    monkeypatch.setenv("JMAP_URL", "https://jmap.example.com/")
    assert [k for k, _ in environment_connections(kinds=("caldav",))] == ["caldav"]
    assert [k for k, _ in environment_connections()] == ["caldav", "jmap"]


def test_environment_connections_resolve_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_URL", "https://env.example.com/")
    monkeypatch.setenv("CALDAV_PASSWORD_COMMAND", "pass show dav")
    with pytest.raises(ConfigError, match="must be a list"):
        environment_connections()


def test_section_connection(tmp_path: Path) -> None:
    path = tmp_path / "calendar.yaml"
    path.write_text("")
    path.chmod(0o600)
    section = {"caldav_url": "https://dav.example.com/", "caldav_password_command": PRINT, "caldav_proxy": None}
    assert section_connection("work", section, path) == Connection(
        "work", "caldav", {"url": "https://dav.example.com/", "password": "s3cret"}
    )
    assert section_connection("new", {"kind": "jmap", "url": "x"}) == Connection("new", "jmap", {"url": "x"})


def test_section_connection_needs_the_file_to_run_a_command() -> None:
    with pytest.raises(ConfigError, match="file"):
        section_connection("work", {"caldav_url": "https://dav.example.com/", "caldav_password_command": PRINT})


def test_kinds_filters_the_result(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JMAP_PASSWORD", "env")
    config = {
        "dav": {"kind": "caldav", "url": "https://dav.example.com/"},
        "mail": {"kind": "jmap", "url": "https://jmap.example.com/"},
        "files": {"url": "~/calendars"},
        "all": {"contains": ["*"]},
    }
    path = write_config(config)
    assert [c.name for c in load(path, "all", kinds=("caldav",))] == ["dav", "files"]
    assert load(path, "mail", kinds=("caldav",)) == []
    assert load(path, "mail")[0].params["password"] == "env"


def test_kinds_as_a_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALDAV_URL", "https://env.example.com/")
    monkeypatch.setenv("JMAP_URL", "https://jmap.example.com/")
    assert [k for k, _ in environment_connections(iter(["jmap", "caldav"]))] == ["caldav", "jmap"]


def test_kinds_as_a_string_is_refused() -> None:
    with pytest.raises(ConfigError, match="kinds"):
        environment_connections("caldav")
    with pytest.raises(ConfigError, match="kinds"):
        load(kinds="caldav")


def test_only_secret_commands_need_the_file() -> None:
    assert section_connection("w", {"url": "u", "pre_command": "x"}).params == {"url": "u", "pre_command": "x"}


def test_missing_file_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="missing"):
        section_connection("w", {"url": "u", "password_command": PRINT}, "/nonexistent/missing.yaml")


def test_unsafe_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "calendar.yaml"
    path.write_text("")
    path.chmod(0o620)
    with pytest.raises(ConfigError, match="writable"):
        section_connection("w", {"url": "u", "password_command": PRINT}, path)


def test_section_connection_wants_a_merged_section(monkeypatch: pytest.MonkeyPatch) -> None:
    for section in ({"inherits": "base", "username": "bob"}, {"contains": ["a"]}):
        with pytest.raises(ConfigError, match="merged"):
            section_connection("w", section)
    with pytest.raises(ConfigError, match="mapping"):
        section_connection("w", ["not", "a", "section"])  # type: ignore[arg-type]
    monkeypatch.setenv("CALDAV_PASSWORD", "env")
    assert section_connection("w", {"kind": "caldav", "url": "u"}).params == {"url": "u"}
