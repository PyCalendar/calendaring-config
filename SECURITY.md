# Security policy

Issues should be fixed as soon as possible, and information about a security
issue should be published once it is fixed. Report serious issues privately
and keep them under wraps until a fix is released: use
[GitHub's private vulnerability reporting](https://github.com/pycalendar/calendaring-config/security/advisories/new)
(the "Report a vulnerability" button on the Security tab). Use the public
issue tracker only for issues that are not sensitive.

There are no long-term-support releases, but the maintainer will consider
backporting a security fix where it is relevant. Maintenance is partly done
on a hobby basis, so no response times are guaranteed.

# Known security issues and risks

There is no released code yet. By design, this package:

- runs the programs named in `password_command` and `token_command`
  keys.  A file holding one is refused if anyone but its owner can write
  to it, or if it is owned by anyone but the current user or root.
  Directories above the file are not checked.
- reads YAML with a safe loader, so a file cannot build Python objects.
- never puts a secret into an error message.  The secrets it resolves are
  returned to the caller, who must not log them either.
