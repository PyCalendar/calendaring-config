# calendaring-config

One configuration file for the pycalendar libraries: `caldav`,
[`calendaring`](https://github.com/pycalendar/calendaring) and
`calendaring-jmap`. A user with a CalDAV server, a JMAP account, a
directory of `.ics` files and a GitHub repository describes them once:

```yaml
work:
  kind: caldav
  url: https://dav.example.com/
  username: alice
  password_command: [pass, show, dav/work]

fastmail:
  kind: jmap
  url: https://api.fastmail.com/jmap/session
  username: alice@example.com
  password_keyring: fastmail

everything:
  contains: [work, fastmail]
```

```python
from calendaring_config import load

for conn in load(section="everything"):
    print(conn.name, conn.kind, conn.params["url"])
```

`load()` finds the file, expands the section, resolves `inherits`,
`${VAR}` references and secrets, applies the environment, and returns one
`Connection` per backend: its section name, its kind (or `None`, when the
reader should decide from the URL), and the keyword arguments for the
backend's `connect()`. Old-style caldav files (`caldav_url`, …) are read
unchanged. `load(environment=False)` reads no `CALDAV_*`, `JMAP_*` or
`CALENDARING_*` variable. `load(kinds=("caldav",))` returns only CalDAV
sections and those without a kind, and lets only `CALDAV_URL` replace
the file. A reader that walks the file itself merges a section with
what it `inherits` using `merged_section()`, turns it into a `Connection`
with `section_connection()`, and finds the file
with `find_config_file()`; `search_path()` lists where it looks, the
first entry being where a new file belongs. Errors are `ConfigError`, a
`ValueError`.

The format is specified in [docs/format.md](docs/format.md).

It is in early development and has no release yet. The design notes are in
calendaring's
[CONFIGURATION_PROPOSAL.md](https://github.com/pycalendar/calendaring/blob/main/docs/design/CONFIGURATION_PROPOSAL.md).

## Installing

```sh
pip install calendaring-config            # or calendaring-config[keyring]
```

The `keyring` extra is needed only for `password_keyring` / `token_keyring`.

## Licence

GPL-3.0-or-later or Apache-2.0, at your option, like caldav and
calendaring.
