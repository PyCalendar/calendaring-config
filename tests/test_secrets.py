"""docs/format.md, "Secrets"."""

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import keyring
import keyring.backend
import keyring.errors
import pytest

import calendaring_config.secrets
from calendaring_config import ConfigError, load

Write = Callable[..., Path]

PRINT = [sys.executable, "-c", "print('s3cret')"]


def _params(write: Write, section: dict[str, Any], mode: int = 0o600) -> dict[str, Any]:
    [conn] = load(write({"default": section}, mode=mode))
    return conn.params


def test_command_output_is_the_secret(write_config: Write) -> None:
    params = _params(write_config, {"url": "https://dav.example.com/", "password_command": PRINT})
    assert params == {"url": "https://dav.example.com/", "password": "s3cret"}


def test_only_one_trailing_newline_is_stripped(write_config: Write) -> None:
    command = [sys.executable, "-c", "print('s3cret', end='\\n\\n')"]
    assert _params(write_config, {"url": "x", "password_command": command})["password"] == "s3cret\n"


def test_hanging_command_times_out(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calendaring_config.secrets, "COMMAND_TIMEOUT", 0.2)
    command = [sys.executable, "-c", "import time; time.sleep(5)"]
    with pytest.raises(ConfigError, match="did not finish"):
        _params(write_config, {"url": "x", "password_command": command})


def test_token_command_and_old_style_spelling(write_config: Write) -> None:
    assert _params(write_config, {"kind": "github", "token_command": PRINT}) == {"token": "s3cret"}
    old = {"caldav_url": "https://dav.example.com/", "caldav_password_command": PRINT}
    assert _params(write_config, old)["password"] == "s3cret"


def test_command_as_a_string_is_an_error(write_config: Write) -> None:
    with pytest.raises(ConfigError, match="password_command"):
        _params(write_config, {"url": "https://dav.example.com/", "password_command": "pass show dav"})


def test_failing_command_is_an_error_without_its_output(write_config: Write) -> None:
    failing = [sys.executable, "-c", "print('leaked'); raise SystemExit(1)"]
    with pytest.raises(ConfigError) as excinfo:
        _params(write_config, {"url": "https://dav.example.com/", "password_command": failing})
    assert "leaked" not in str(excinfo.value)
    assert "default" in str(excinfo.value)


def test_two_sources_for_one_secret_is_an_error(write_config: Write) -> None:
    with pytest.raises(ConfigError, match="password"):
        _params(write_config, {"url": "https://dav.example.com/", "password": "x", "password_command": PRINT})


@pytest.mark.parametrize("mode", [0o620, 0o602])
def test_command_in_a_file_others_can_write_is_refused(write_config: Write, mode: int) -> None:
    with pytest.raises(ConfigError, match="writable"):
        _params(write_config, {"url": "https://dav.example.com/", "password_command": PRINT}, mode=mode)


def test_file_others_can_write_is_fine_without_commands(write_config: Write) -> None:
    assert _params(write_config, {"url": "https://dav.example.com/"}, mode=0o666) == {"url": "https://dav.example.com/"}


def _owned_by(monkeypatch: pytest.MonkeyPatch, path: Path, uid: int) -> None:
    real = path.stat()
    fake = os.stat_result((real.st_mode, *real[1:4], uid, *real[5:]))
    original = Path.stat
    monkeypatch.setattr(Path, "stat", lambda p, **kw: fake if p == path else original(p, **kw))


def test_command_in_a_file_owned_by_someone_else_is_refused(
    write_config: Write, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_config({"default": {"url": "https://dav.example.com/", "password_command": PRINT}})
    _owned_by(monkeypatch, path, os.getuid() + 1000)
    with pytest.raises(ConfigError, match="owned"):
        load(path)


def test_command_in_a_root_owned_file_is_run(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_config({"default": {"url": "https://dav.example.com/", "password_command": PRINT}})
    _owned_by(monkeypatch, path, 0)
    assert load(path)[0].params["password"] == "s3cret"


class _MemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.store = {("fastmail", "alice@example.com"): "kr-secret"}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        raise NotImplementedError

    def delete_password(self, service: str, username: str) -> None:
        raise NotImplementedError


@pytest.fixture
def memory_keyring() -> Any:
    previous = keyring.get_keyring()
    keyring.set_keyring(_MemoryKeyring())
    yield
    keyring.set_keyring(previous)


@pytest.mark.usefixtures("memory_keyring")
def test_keyring_lookup(write_config: Write) -> None:
    section = {"kind": "jmap", "url": "https://jmap.example.com/", "username": "alice@example.com"}
    assert _params(write_config, {**section, "password_keyring": "fastmail"})["password"] == "kr-secret"
    with pytest.raises(ConfigError, match="keyring"):
        _params(write_config, {**section, "password_keyring": "nosuch"})
    del section["username"]
    with pytest.raises(ConfigError, match="username"):
        _params(write_config, {**section, "password_keyring": "fastmail"})


class _BrokenKeyring(_MemoryKeyring):
    def get_password(self, service: str, username: str) -> str | None:
        raise keyring.errors.KeyringLocked("locked")


def test_keyring_failure_is_a_config_error(write_config: Write) -> None:
    previous = keyring.get_keyring()
    keyring.set_keyring(_BrokenKeyring())  # type: ignore[no-untyped-call]  # keyring is untyped there
    try:
        with pytest.raises(ConfigError, match="keyring failed"):
            _params(write_config, {"url": "x", "username": "alice", "password_keyring": "fastmail"})
    finally:
        keyring.set_keyring(previous)


def test_keyring_package_missing(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "keyring", None)
    with pytest.raises(ConfigError, match=r"calendaring-config\[keyring\]"):
        _params(write_config, {"url": "x", "username": "alice", "password_keyring": "fastmail"})
