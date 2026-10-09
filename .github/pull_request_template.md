## What and why

<!-- One or two sentences. Link the issue: "Fixes #123". -->

## Checklist

- [ ] Commands were run on current Kali rolling or in the lab's attacker container, and the expected output is real
- [ ] Examples target only the lab (`10.77.0.0/24`), `127.0.0.1`, or documentation ranges
- [ ] New techniques include a defensive note; disruptive commands carry a warning
- [ ] `ruff check scripts tests && pytest -q` passes (if scripts changed)
- [ ] `bash tests/lab-smoke.sh` passes (if the lab or lab-dependent docs changed)
- [ ] `python scripts/build-site.py` builds and the page looks right (if content or the site changed)
