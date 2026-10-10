# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases are
tagged `vMAJOR.MINOR.PATCH`: a new module is a minor release, fixes and
wording changes are patches.

## [Unreleased]

## [1.0.0] - 2026-10-09

First tagged release: five modules, four cheatsheets, a working practice lab,
and a generated documentation site.

### Added
- Kali attacker container (`10.77.0.5`) with nmap, tshark, tcpdump, ftp, and
  curl, so the modules work the same on Linux, Docker Desktop, and WSL2.
  `./scripts/setup-lab-env.sh shell` opens a shell in it.
- Custom Alpine vsftpd target with working anonymous and `labuser` logins.
- `tests/lab-smoke.sh`: 14 end-to-end checks that the lab behaves the way the
  modules describe.
- `parse-nmap-xml.py --format table|markdown|csv|json`, IPv6 and MAC fallback,
  and all hostnames.
- Documentation site rebuilt as pre-rendered pages: one URL per page, full-text
  search of commands, per-page progress tracking, a landing page with module
  cards and time estimates, sitemap, link previews, offline support, and a
  strict Content Security Policy.
- GitHub Codespaces devcontainer: the lab builds and starts with nothing
  installed locally.
- CI: ruff, pytest, shellcheck, actionlint, an offline link check, and the lab
  smoke test. The site deploys only when all of them pass.
- Dependabot for GitHub Actions, Docker images, and Python dev dependencies.
- CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue forms, a pull request
  template, and a guide for teaching with the course.

### Changed
- The lab moved to `10.77.0.0/24` to stay clear of Docker's default address
  pools. Every module and cheatsheet uses the new addresses.
- Lab containers drop all Linux capabilities except the few each daemon needs,
  run with `no-new-privileges`, and publish ports on `127.0.0.1` only. Base
  images are pinned by digest.
- The web target serves the checked-in ACME login page instead of the nginx
  default page.
- Module 04 and the Aircrack-ng cheatsheet use current hcxdumptool 7.x syntax.
- Module 03 documents `nmap -sL -n` and real expected output from the lab.
- Module 05 captures on the attacker's `eth0` and explains BPF operator
  precedence.
- README leads with who the course is for, what you need, and how long it takes.

### Fixed
- Anonymous FTP and the web target's login page now work as documented.
- The module 02 SUID exercise works on `nosuid` mounts.

### Security
- The docs site's client-side rendering of the URL fragment was replaced by
  build-time rendering, removing a DOM injection path.

[Unreleased]: https://github.com/TMHSDigital/Kali-Linux-for-beginners/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/TMHSDigital/Kali-Linux-for-beginners/releases/tag/v1.0.0
