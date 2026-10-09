# Contributing

Thanks for helping beginners learn security the right way. Fixes to a single
command are as welcome as whole new modules.

## Ways to help

- **Report a broken command or wrong output:** use the "Content error" issue
  form. Include your Kali version (`cat /etc/os-release`).
- **Report a lab problem:** use the "Lab problem" form, with your OS, Docker
  version, and CPU architecture.
- **Propose a module:** use the "New module proposal" form first, so we can
  agree on scope before you write it.
- **Pick up a starter task:** issues labeled
  [`good first issue`](https://github.com/TMHSDigital/Kali-Linux-for-beginners/labels/good%20first%20issue).
- **Ask a question:** use [Discussions](https://github.com/TMHSDigital/Kali-Linux-for-beginners/discussions),
  not issues.

## How the repo fits together

| Path | What it is |
|------|------------|
| `NN-topic/README.md` | A module. Other `.md` files in the folder are its sub-pages (lab exercises, references). |
| `cheatsheets/` | One-page quick references. |
| `guides/` | Guides for teachers and other non-module material. |
| `docker-compose.yml`, `lab/` | The practice lab: `attacker` (Kali, `10.77.0.5`), `web-target` (`10.77.0.10`), `ftp-service` (`10.77.0.20`). |
| `scripts/` | `setup-lab-env.sh` (lab launcher), `parse-nmap-xml.py` (scan-to-table), `build-site.py` (docs site). |
| `tests/` | pytest suites for the scripts and `lab-smoke.sh` for the lab. |

The docs site is generated from the file tree. A new `NN-topic/README.md`
appears in the navigation automatically, titled by its first `#` heading.

## Content style guide

1. **Structure each technique as:** what it is and why it matters, then the
   command(s), then the **expected output** (real output from the lab), then a
   **defensive note** (how to detect or prevent it).
2. **Tag depth** in code comments: `[Level 0: Fundamental]`,
   `[Level 1: Intermediate]`, `[Level 2+: Advanced / Field Ops]`. A module's H1
   ends with its level tag, e.g. ``# 06: Web Basics `[Level 2: Web]` ``, and the
   next line carries a time estimate: `<!-- time: ~3 hours -->`.
3. **Stay legal and in scope.** Examples target only the lab (`10.77.0.0/24`),
   `127.0.0.1`, or documentation ranges (`192.0.2.0/24`, `example.com`). Never
   name real third-party targets. Keep the authorization warnings at the top
   of offensive modules, and add a warning wherever a command is disruptive
   (deauth, aggressive scans, brute force).
4. **Verify everything.** Run each command on current Kali rolling or in the
   lab's attacker container (`./scripts/setup-lab-env.sh shell`) and paste the
   real output. Note the tool version if output varies between versions.
5. **Lab exercises self-grade.** Each exercise ends with a check command that
   prints `PASS`/`FAIL`. Where the answer is a secret (a password, a flag),
   compare a SHA-256 hash, not the plaintext.
6. **Plain ASCII punctuation** (no em dashes or smart quotes), relative links
   between Markdown files, and fenced code blocks with a language
   (`bash`, `text`, ...).

## Changing the lab

Lab images live in `lab/<service>/`. Pin base images by digest (Dependabot
keeps them current). Targets keep `cap_drop: [ALL]` plus only the capabilities
they need, and ports bind to `127.0.0.1` only. After any lab change:

```bash
./scripts/setup-lab-env.sh
bash tests/lab-smoke.sh          # every check must PASS
```

If you add a target or change behavior the docs rely on, add a check to
`tests/lab-smoke.sh`.

## Local checks (CI runs the same)

```bash
pip install -r requirements-dev.txt
ruff check scripts tests
pytest -q
python scripts/build-site.py --out _site && (cd _site && python -m http.server 8099)
```

CI also runs shellcheck, actionlint, an offline Markdown link and anchor check,
and the full lab smoke test. The site deploys from `main` only when all of
that passes.

## Pull requests

Keep PRs focused: one topic, module, or fix. Fill in the PR template
checklist. By contributing you agree your work is released under the
repository's [MIT license](LICENSE) and that you'll follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
