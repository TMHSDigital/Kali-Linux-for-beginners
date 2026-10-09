# Kali Linux for Beginners: notes for AI assistants and contributors

A beginner ethical-hacking curriculum (Markdown modules + cheatsheets), a Docker
practice lab, two small Python tools, and a static docs site generated from the
Markdown. See CONTRIBUTING.md for the full guide; the essentials:

## Layout
- `NN-topic/README.md` is a module; other `.md` files in that folder are its
  sub-pages. `cheatsheets/` is quick reference. All of it becomes the site.
- `docker-compose.yml` + `lab/`: attacker (Kali, 10.77.0.5), web-target
  (10.77.0.10), ftp-service (10.77.0.20) on `10.77.0.0/24`.
- `scripts/setup-lab-env.sh` (lab launcher), `scripts/parse-nmap-xml.py`
  (stdlib only), `scripts/build-site.py` (markdown-it-py + Pygments).
- `tests/`: pytest for the Python scripts, `tests/lab-smoke.sh` for the lab.

## Content rules
- Tag commands by depth: `[Level 0: Fundamental]`, `[Level 1: Intermediate]`,
  `[Level 2+: Advanced / Field Ops]`. Module H1 ends with a level tag; add
  `<!-- time: ~N hours -->` on the line after it.
- Every technique gets the command, its expected output, and a defensive note.
- Examples only target the lab (`10.77.0.0/24`), `127.0.0.1`, or documentation
  ranges. Never real third-party hosts. Keep authorization warnings.
- Plain ASCII punctuation (no em dashes). Run commands against the lab before
  documenting them and paste real output.

## Checks before committing
```bash
pip install -r requirements-dev.txt
ruff check scripts tests && pytest -q
./scripts/setup-lab-env.sh && bash tests/lab-smoke.sh   # if you touched the lab or lab docs
python scripts/build-site.py --out _site                # if you touched content or the site
```
CI runs all of these plus shellcheck, actionlint, and an offline link check.
