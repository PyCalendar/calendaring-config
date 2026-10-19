==========
Change log
==========

Every calendaring-config release, newest first. Entries are collected from the
fragments in ``news/`` by `towncrier <https://towncrier.readthedocs.io/>`_
at release time.

.. towncrier release notes start

0.2.0 (2026-10-19)
------------------

New features
~~~~~~~~~~~~

- Every ``CALDAV_<KEY>`` and ``JMAP_<KEY>`` environment variable is now the key ``<key>`` of the section, as if written in the file, except ``<PREFIX>CONFIG_*`` and ``<PREFIX>AUTH``.  Two sources of one secret in the environment are an error.  The keys ``test_*``, ``x_*`` and ``extra_config`` are reserved for test tooling and applications; backends should warn about other unknown keys.
- ``load(environment=False)`` reads no ``CALDAV_*``, ``JMAP_*`` or ``CALENDARING_*`` variable.  ``environment_connections()`` and ``expand_env_vars()`` are public, ``ConfigError`` is a ``ValueError``, and Python 3.10 is supported.
- Secrets from the environment, such as ``CALDAV_PASSWORD_KEYRING``, are resolved and checked like the file's, also when ``CALDAV_URL`` replaces the file, and replace all of the file's sources of that secret.  A ``Connection``'s ``repr`` hides every key that looks like a secret.
