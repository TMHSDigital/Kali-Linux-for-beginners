# Security policy

## The practice lab is insecure on purpose

The Docker targets (`web-target`, `ftp-service`) intentionally send credentials
in cleartext and allow anonymous FTP. That's the lesson, not a vulnerability.
Please don't report "FTP is unencrypted" or "the demo password is weak".

The lab is only safe because of how it's isolated: published ports bind to
`127.0.0.1`, and targets run with all Linux capabilities dropped except the
few each daemon needs. Anything that breaks that isolation **is** a security
issue. For example: a target reachable from other machines, a container
escape path, or a script that exposes the host.

## What to report

- Weaknesses in the lab's isolation or hardening (see above).
- Vulnerabilities in the docs site (`site/`, `scripts/build-site.py`), such as
  script injection or a Content-Security-Policy bypass.
- Vulnerabilities in the repo's scripts (`scripts/`, `tests/`, CI workflows),
  including supply-chain issues such as an unpinned or compromised dependency.
- Instructions in the curriculum that would put a learner's own machine or
  network at real risk.

## How to report

Use GitHub's **private vulnerability reporting**:
[Report a vulnerability](https://github.com/TMHSDigital/Kali-Linux-for-beginners/security/advisories/new).
Please don't open a public issue for anything exploitable.

You can expect an acknowledgement within 7 days. We'll keep you updated, fix
confirmed issues as quickly as we can, and credit you in the advisory unless
you'd rather stay anonymous.

## Supported versions

Only the `main` branch (and the published site built from it) is supported.
