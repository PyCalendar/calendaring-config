# The configuration file format

This is the specification. The parser in this package implements it, and
any other parser of the file (caldav's, for one) should follow it. When the
code and this page disagree, one of them has a bug.

## The file

A JSON or YAML mapping of section names (strings) to sections. A section
is a mapping. The file is read as JSON first (so tab-indented JSON works,
which YAML refuses), then as YAML with a safe loader: tags that build
Python objects are refused.

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

notes:
  url: ~/calendars/notes

legacy:                              # an old caldav section, read unchanged
  caldav_url: https://old.example.com/
  caldav_user: alice

everything:
  contains: [work, fastmail, notes, legacy]
```

An empty file is an empty configuration. Anything else that is not a
mapping of mappings is an error.

## Finding the file

The first of these that applies is used:

1. a path given by the caller;
2. `CALENDARING_CONFIG_FILE`;
3. `CALDAV_CONFIG_FILE`;
4. the first file that exists of
   - `$XDG_CONFIG_HOME/pycal/calendar.yaml` (`XDG_CONFIG_HOME` defaults to
     `~/.config`),
   - `~/.config/caldav/calendar.conf`, `~/.config/caldav/calendar.yaml`,
     `~/.config/caldav/calendar.json`,
   - `~/.config/calendar.conf`,
   - `/etc/calendar.conf`, `/etc/caldav/calendar.conf`.

A path from 1–3 that does not exist is an error. When none of 4 exists,
there is no configuration, which is not an error. The first file of 4
that exists is used even if it is empty; caldav moves on to the next one
instead.

The paths in 4 after the first are caldav's, so that existing files keep
working where they are.

## Choosing the section

The section name is the one given by the caller, else
`CALENDARING_CONFIG_SECTION`, else `CALDAV_CONFIG_SECTION`, else `default`.
A name that matches no section is an error, with one exception, as in
caldav: when no name was given at all and the file has no `default`
section, there is no configuration.

A name expands to one or more *leaf* sections:

- a plain name is that section;
- a section with `contains: [a, b, …]` is a *meta-section*, and expands to
  the expansion of each name it lists, recursively, each leaf once, in
  order. A listed name may be a glob. A listed name that matches no
  section is skipped with a warning (caldav skips it silently);
- `*` is every section that is not a meta-section, in file order;
- a name with `*`, `?` or `[` is a glob, matched against the section
  names, each match expanded as above. A glob that matches nothing is an
  error.

A section with `disable: true` is left out of every expansion, a disabled
meta-section with all its members (caldav still expands one). Naming a
disabled section directly is an error.

## Inheritance

`inherits: other` copies the keys of section `other` in, and the
section's own keys win. A parent may inherit in turn. A cycle is an
error, and so is inheriting from a section of another kind (see below).
`contains` and `disable` are not inherited.

## Kinds and keys

After `inherits` is applied and the structural keys (`contains`,
`inherits`, `disable`) are removed, a section is the keyword arguments of
calendaring's `Backend.connect()`: `kind`, `url`, `username`, `password`,
`token` and the backend's own options.

- `kind` names the backend. Without it, the reader decides from `url`
  (calendaring's `connect()` treats a path as files and `webcal:` as a
  feed), and this package reports the kind as unknown. calendaring
  cannot yet connect an `http(s):` URL without `kind`; probing it for a
  feed or CalDAV is planned.
- A section with `caldav_*` keys is an old-style caldav section and has
  `kind: caldav`. The prefix is dropped, and `caldav_user` and
  `caldav_pass` become `username` and `password`. Every `caldav_*` key
  is kept, not only the ones caldav knows. Mixing prefixed and
  unprefixed connection keys (`url`, `username`, `password`, `token` and
  any `_command` or `_keyring` key) in one section is an error. Other
  plain keys, such as `features`, `calendar_name`, `priority` or
  `testing_allowed`, are kept as they are in both styles.
- An explicit `kind` other than `caldav` beside `caldav_*` keys is an
  error.

## Values

`${VAR}` in a string is replaced with the environment variable `VAR`, or
the empty string when it is unset. `${VAR:-default}` uses `default`
instead, only when `VAR` is unset (not, as in the shell, when it is
empty). This applies to every string in a section, `kind` and nested
ones included.

A key whose value is null is left out.

## Secrets

`password` and `token` can each instead come from one of:

- `password_command` / `token_command`: a list of the program and its
  arguments. It is run without a shell, and its standard output, minus one
  trailing newline (`\n` or `\r\n`), is the secret. Its standard error
  goes to the terminal. A plain string is an error, since splitting it
  would need shell quoting rules. A non-zero exit is an error, and so is
  a command still running after 60 seconds.
- `password_keyring` / `token_keyring`: the service name to look up in
  the system keyring (the `keyring` extra), with the section's `username`.
  No username, no keyring package, no entry, or a keyring that fails
  (locked, no backend) is an error.

The old-style spelling (`caldav_password_command`, …) works as well.

At most one source per secret: `password` together with
`password_command` is an error.

Before a command is run, the file it came from is checked: it is refused
when it is writable by group or others, or owned by anyone but the
current user or root. Unlike ssh, the directories above it are not
checked. A command that is not run (another section's, or one the
environment replaces) is not checked.

Error messages name the section and the key, never the secret.

## The environment

Environment variables describe one connection of one kind, and win over
the file:

| kind | variables |
|---|---|
| `caldav` | `CALDAV_URL`, `CALDAV_USERNAME` (or `CALDAV_USER`), `CALDAV_PASSWORD` (or `CALDAV_PASS`), `CALDAV_PROXY`, `CALDAV_TIMEOUT`, `CALDAV_AUTH_TYPE`, `CALDAV_SSL_VERIFY_CERT`, `CALDAV_SSL_CERT` |
| `jmap` | `JMAP_URL`, `JMAP_USERNAME`, `JMAP_PASSWORD`, `JMAP_AUTH_TYPE`, `JMAP_TIMEOUT` |

Other kinds have none. The list is deliberately shorter than caldav's,
which maps every `CALDAV_<KEY>` its client takes. Values are strings, so
`CALDAV_SSL_VERIFY_CERT=false` is the string `"false"`, as in caldav;
only the timeouts become numbers, and a value that is not a number is an
error. An empty value counts (a server may need an empty password),
except for the URL.

- A `CALDAV_URL` or `JMAP_URL` means the file is not read at all: the
  configuration is that one connection (or two, if both are set; the
  CalDAV one first).
- Otherwise, when the name expands to exactly one section, the variables
  of that section's kind apply to it key by key: `CALDAV_PASSWORD` alone
  replaces the password and keeps the URL. A secret from the environment
  replaces the section's `_command` or `_keyring`, which is then not run.
- When the name expands to several sections, the variables without a URL
  are not applied.

A section whose kind is unknown (no `kind`, no `caldav_*` keys) takes no
environment variables.
