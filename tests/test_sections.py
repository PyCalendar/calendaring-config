"""docs/format.md, "The file", "Choosing the section", "Inheritance", "Kinds and keys" and "Values"."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from calendaring_config import ConfigError, Connection, expand_section, load, read_config

Write = Callable[..., Path]


def _load(write: Write, data: Any, section: str | None = None) -> list[Connection]:
    return load(write(data), section)


def test_unsafe_yaml_tag_is_refused(write_config: Write) -> None:
    path = write_config("default:\n  url: !!python/object/apply:os.getcwd []\n")
    with pytest.raises(ConfigError):
        read_config(path)


def test_tab_indented_json_is_read(write_config: Write) -> None:
    path = write_config('{\n\t"default": {\n\t\t"url": "https://dav.example.com/"\n\t}\n}\n', name="calendar.json")
    assert read_config(path) == {"default": {"url": "https://dav.example.com/"}}


def test_json_is_read(write_config: Write) -> None:
    path = write_config('{"default": {"url": "https://dav.example.com/"}}', name="calendar.json")
    assert read_config(path) == {"default": {"url": "https://dav.example.com/"}}


def test_empty_file_is_empty_configuration(write_config: Write) -> None:
    assert read_config(write_config("")) == {}


@pytest.mark.parametrize("text", ["- a\n- b\n", "default: 3\n", "2024:\n  url: x\n"])
def test_not_a_mapping_of_mappings_is_an_error(write_config: Write, text: str) -> None:
    with pytest.raises(ConfigError):
        read_config(write_config(text))


CONFIG = {
    "a": {"url": "https://a.example.com/"},
    "b": {"url": "https://b.example.com/"},
    "work_x": {"url": "https://x.example.com/"},
    "work_y": {"url": "https://y.example.com/", "disable": True},
    "pair": {"contains": ["b", "a"]},
    "nested": {"contains": ["pair", "a", "work_x"]},
    "dangling": {"contains": ["a", "nosuch"]},
    "all_work": {"contains": ["work_*"]},
    "off": {"contains": ["a", "work_y"]},
    "off_meta": {"contains": ["b"], "disable": True},
    "with_off_meta": {"contains": ["off_meta", "a"]},
}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a", ["a"]),
        ("pair", ["b", "a"]),
        ("nested", ["b", "a", "work_x"]),
        ("*", ["a", "b", "work_x"]),
        ("work_*", ["work_x"]),
        ("all_work", ["work_x"]),
        ("off", ["a"]),
        ("with_off_meta", ["a"]),
    ],
)
def test_expansion(name: str, expected: list[str]) -> None:
    assert expand_section(CONFIG, name) == expected


def test_contains_skips_a_missing_name_with_a_warning() -> None:
    with pytest.warns(UserWarning, match="nosuch") as record:
        assert expand_section(CONFIG, "dangling") == ["a"]
    assert record[0].filename == __file__


def test_glob_matching_nothing_is_an_error() -> None:
    with pytest.raises(ConfigError, match="home_"):
        expand_section(CONFIG, "home_*")


@pytest.mark.parametrize(
    "config",
    [{"m": {"contains": "a"}, "a": {}}, {"m": {"contains": [1]}}],
)
def test_contains_must_be_a_list_of_names(config: dict[str, dict[str, Any]]) -> None:
    with pytest.raises(ConfigError, match="contains"):
        expand_section(config, "m")


@pytest.mark.parametrize("name", ["nosuch", "work_y"])
def test_missing_or_disabled_section_named_directly_is_an_error(name: str) -> None:
    with pytest.raises(ConfigError, match=name):
        expand_section(CONFIG, name)


def test_load_returns_connections_without_structural_keys(write_config: Write) -> None:
    connections = _load(
        write_config,
        {
            "base": {"username": "alice", "kind": "caldav"},
            "work": {"inherits": "base", "url": "https://dav.example.com/"},
            "notes": {"url": "~/calendars/notes"},
            "both": {"contains": ["work", "notes"]},
        },
        "both",
    )
    assert connections == [
        Connection("work", "caldav", {"url": "https://dav.example.com/", "username": "alice"}),
        Connection("notes", None, {"url": "~/calendars/notes"}),
    ]


def test_child_keys_win_over_inherited_ones(write_config: Write) -> None:
    [conn] = _load(
        write_config,
        {"base": {"url": "https://a.example.com/", "username": "alice"}, "default": {"inherits": "base", "username": "bob"}},
    )
    assert conn.params == {"url": "https://a.example.com/", "username": "bob"}


def test_inheritance_chains_and_skips_structural_keys(write_config: Write) -> None:
    [conn] = _load(
        write_config,
        {
            "grand": {"username": "alice", "disable": True},
            "parent": {"inherits": "grand", "url": "https://dav.example.com/"},
            "default": {"inherits": "parent"},
        },
    )
    assert conn.params == {"url": "https://dav.example.com/", "username": "alice"}


def test_contains_is_not_inherited(write_config: Write) -> None:
    data = {"a": {"url": "https://a.example.com/"}, "meta": {"contains": ["a"]}, "default": {"inherits": "meta"}}
    [conn] = _load(write_config, data)
    assert conn.name == "default"


@pytest.mark.parametrize(("inherits", "match"), [("nosuch", "nosuch"), (["a"], "inherits")])
def test_bad_inherits_is_an_error(write_config: Write, inherits: object, match: str) -> None:
    with pytest.raises(ConfigError, match=match):
        _load(write_config, {"a": {}, "default": {"inherits": inherits, "url": "x"}})


def test_inheritance_cycle_is_an_error(write_config: Write) -> None:
    with pytest.raises(ConfigError, match="cycle"):
        _load(write_config, {"default": {"inherits": "b"}, "b": {"inherits": "default"}})


def test_inheriting_across_kinds_is_an_error(write_config: Write) -> None:
    data = {"old": {"caldav_url": "https://dav.example.com/"}, "default": {"inherits": "old", "kind": "jmap"}}
    with pytest.raises(ConfigError, match="kind"):
        _load(write_config, data)


def test_old_style_section_is_caldav(write_config: Write) -> None:
    [conn] = _load(
        write_config,
        {
            "default": {
                "caldav_url": "https://dav.example.com/",
                "caldav_user": "alice",
                "caldav_pass": "secret",
                "features": "radicale",
                "calendar_name": "Work",
            }
        },
    )
    assert conn == Connection(
        "default",
        "caldav",
        {
            "url": "https://dav.example.com/",
            "username": "alice",
            "password": "secret",
            "features": "radicale",
            "calendar_name": "Work",
        },
    )


def test_old_style_section_keeps_other_plain_keys(write_config: Write) -> None:
    section = {"caldav_url": "https://dav.example.com/", "kind": "caldav", "priority": 10, "testing_allowed": True}
    [conn] = _load(write_config, {"default": section})
    assert conn.params == {"url": "https://dav.example.com/", "priority": 10, "testing_allowed": True}


@pytest.mark.parametrize(
    "section",
    [
        {"caldav_url": "https://dav.example.com/", "username": "alice"},
        {"caldav_url": "https://dav.example.com/", "password_command": ["true"]},
        {"caldav_url": "https://dav.example.com/", "kind": "jmap"},
    ],
)
def test_mixed_styles_are_an_error(write_config: Write, section: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        _load(write_config, {"default": section})


def test_missing_default_section_is_no_configuration(write_config: Write) -> None:
    """As in caldav: a file with only named sections, read without a name."""
    assert _load(write_config, {"work": {"url": "https://dav.example.com/"}}) == []


def test_missing_section_asked_for_is_an_error(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_config({"work": {"url": "https://dav.example.com/"}})
    with pytest.raises(ConfigError, match="home"):
        load(path, "home")
    monkeypatch.setenv("CALDAV_CONFIG_SECTION", "default")
    with pytest.raises(ConfigError, match="default"):
        load(path)


def test_no_file_is_no_connections() -> None:
    assert load() == []


def test_env_references_are_expanded(write_config: Write, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DAV_HOST", "dav.example.com")
    [conn] = _load(
        write_config,
        {
            "default": {
                "kind": "${DAV_KIND:-caldav}",
                "url": "https://${DAV_HOST}/",
                "username": "${DAV_USER:-alice}",
                "headers": {"X": "${UNSET}"},
                "scopes": ["${DAV_HOST}"],
                "proxy": None,
            }
        },
    )
    assert conn.kind == "caldav"
    assert conn.params == {
        "url": "https://dav.example.com/",
        "username": "alice",
        "headers": {"X": ""},
        "scopes": ["dav.example.com"],
    }


def test_repr_masks_secrets() -> None:
    conn = Connection("default", "caldav", {"url": "https://dav.example.com/", "password": "hunter2", "token": "t0k"})
    assert "hunter2" not in repr(conn)
    assert "t0k" not in repr(conn)
    assert "dav.example.com" in repr(conn)
