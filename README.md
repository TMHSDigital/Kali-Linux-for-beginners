# Kali Linux for Beginners

[![CI](https://github.com/TMHSDigital/Kali-Linux-for-beginners/actions/workflows/ci.yml/badge.svg)](https://github.com/TMHSDigital/Kali-Linux-for-beginners/actions/workflows/ci.yml)
[![Docs site](https://img.shields.io/badge/docs-site-2ea44f)](https://tmhsdigital.github.io/Kali-Linux-for-beginners/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/TMHSDigital/Kali-Linux-for-beginners)](https://github.com/TMHSDigital/Kali-Linux-for-beginners/commits/main)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/TMHSDigital/Kali-Linux-for-beginners)

**Learn Kali by doing.** A free, self-paced path from your first shell command
to pulling a password out of captured network traffic, with a safe practice lab
that runs on your own laptop.

- **A real lab, not screenshots.** One command starts a Kali attacker box and
  deliberately insecure targets on a private Docker network. Scan them, sniff
  them, log in to them.
- **Every technique shows the command, its real output, and the defense.** You
  learn what an attack looks like from both sides.
- **Offline and account-free.** No sign-ups, no VPN, no time limits. Clone it,
  or open it in Codespaces with nothing installed.

Read it on the [documentation site](https://tmhsdigital.github.io/Kali-Linux-for-beginners/),
which adds search and progress tracking, or right here on GitHub.

[![The documentation site's landing page](site/assets/screenshot.png)](https://tmhsdigital.github.io/Kali-Linux-for-beginners/)

| Who it's for | What you need | How long it takes |
|---|---|---|
| Complete beginners to Linux and security, and anyone who wants a hands-on refresher | A laptop with 8 GB RAM and Docker (or a free GitHub account for Codespaces). No prior Linux needed. A Wi-Fi adapter only for module 04's live work. | About 18 hours across five modules, at your own pace |

> **For education and authorized testing only.** Using these techniques against
> systems, networks, or wireless access points you do not own or lack written
> permission to test is illegal in most jurisdictions. You are responsible for
> your own actions. See the [full disclaimer](LICENSE).

## Quickstart

```bash
# 1. Clone
git clone https://github.com/TMHSDigital/Kali-Linux-for-beginners.git
cd Kali-Linux-for-beginners

# 2. Launch the practice lab (Docker required; first run downloads Kali)
./scripts/setup-lab-env.sh          # checks Docker + subnet, starts it, waits for health
#   or: docker compose up -d --build

# 3. Get a shell on the Kali attacker box that sits on the lab network
./scripts/setup-lab-env.sh shell

# 4. Open module 01 to start, or read the documentation site.
```

The lab comes up on a private `10.77.0.0/24` Docker bridge:

| Host | Address | Purpose |
|------|---------|---------|
| `attacker` | `10.77.0.5` | Kali toolbox (nmap, tshark, tcpdump, ftp, curl) to run the modules from |
| `web-target` | `10.77.0.10` | Plain-HTTP login form for intercepting cleartext credentials |
| `ftp-service` | `10.77.0.20` | vsftpd with anonymous and `labuser`/`labpass` logins, all cleartext |

The attacker box works the same on Linux, Docker Desktop (Windows/macOS), and
WSL2. With Docker Desktop, the `10.77.0.x` addresses aren't reachable from your
host, so run the module commands from `./scripts/setup-lab-env.sh shell`. The
repo is mounted read-only at `/lab`, and scans/captures you save in
`/root/work` show up in `workspace/` in your clone. From the host itself, the
targets are also published on `127.0.0.1:8080` (web) and `127.0.0.1:2121` (FTP).

Stop it with `./scripts/setup-lab-env.sh down` (or `docker compose down`).

## Zero-install option: GitHub Codespaces

Click **Open in GitHub Codespaces** above. You get a browser-based VS Code where
the practice lab builds and starts on its own (the first launch takes a few
minutes while Kali downloads). Then run `./scripts/setup-lab-env.sh shell` and
start at module 01. Modules 01-03 and 05 work fully there. Live wireless
(module 04) needs real hardware. Codespaces is free up to GitHub's monthly
quota, and it's worth stopping the codespace when you're done.

## Curriculum

Four levels across five modules. Each links to its full write-up.

| Level | Module | Time | Outcome |
|-------|--------|------|---------|
| 0, Fundamentals | [01. Terminal & Linux Core](01-terminal-and-linux-core/) | ~3 h | Navigate, inspect, and manipulate Linux from the shell; pipes and redirection |
| 1, Administration | [02. System Admin & Privileges](02-system-admin-and-privileges/) | ~4 h | Read the Unix privilege model; audit SUID and sudo for escalation surface |
| 2, Recon | [03. Network Recon & Nmap](03-network-recon-and-nmap/) | ~4 h | Map a network and choose the right scan for stealth, speed, or depth |
| 2, Wireless | [04. Wireless Security & Aircrack-ng](04-wireless-security-aircrack/) | ~4 h | Capture and crack a WPA2 handshake in a lab; understand WPA3 and PMF defenses |
| 3, Forensics | [05. Packet Analysis & Wireshark](05-packet-analysis-wireshark/) | ~3 h | Reassemble sessions, extract cleartext credentials, and describe the fix |

Commands are tagged by depth so you can find your level:
`[Level 0: Fundamental]`, `[Level 1: Intermediate]`, `[Level 2+: Advanced / Field Ops]`.

If you are new, start at [module 01](01-terminal-and-linux-core/), do its lab
exercises (modules 01 and 02 have self-grading checks that print PASS/FAIL),
then continue in order. Keep the
[cheatsheets](cheatsheets/) open alongside the modules.

## How this compares

This project is meant to complement platforms like TryHackMe and Hack The Box
Academy, not replace them:

| | This project | Hosted platforms |
|---|---|---|
| Cost | Free, MIT licensed | Free tiers, paid for most content |
| Account / VPN | None | Account, often a VPN connection |
| Where the lab runs | Your machine or your Codespace, works offline | Their cloud |
| Defensive notes | On every technique | Varies by room or course |
| Depth | Beginner foundations | Beginner to advanced |

A good route is to work through these modules first, then move to a hosted
platform for more targets.

## Quick reference

- [Kali survival commands](cheatsheets/01-kali-survival-commands.md)
- [Nmap tactical reference](cheatsheets/02-nmap-tactical-reference.md)
- [Aircrack-ng workflow](cheatsheets/03-aircrack-workflow.md)
- [Wireshark BPF and display filters](cheatsheets/04-wireshark-bpf-and-display.md)

## Lab environment setup

<details>
<summary>Choose your platform (bare-metal, VirtualBox, VMware, WSL2)</summary>

<br>

You need Kali Linux, or any Debian-based distro. Pick the path that matches your
hardware:

- **Bare-metal**: best wireless performance and unrestricted access to internal
  radios. Required for reliable monitor-mode work (module 04).
- **VirtualBox**: install the Extension Pack for USB passthrough; allocate at
  least 2 vCPU, 4 GB RAM, and 40 GB disk; use Host-Only or NAT Network to
  isolate the lab.
- **VMware Workstation/Fusion**: smoother USB passthrough for RTL8812AU-class
  Wi-Fi adapters; use a Host-Only `vmnet` to fence off the lab.
- **WSL2**: `wsl --install -d kali-linux` gives the full CLI toolchain, but has
  no native 802.11 radio access. Use it for modules 01-03 and 05 (analyzing
  saved captures with `tshark`), and use bare-metal or a full VM for live
  wireless.

</details>

<details>
<summary>Recommended Wi-Fi adapters (monitor mode and injection)</summary>

<br>

| Adapter | Chipset | Notes |
|---------|---------|-------|
| Alfa AWUS036NHA | Atheros AR9271 | 2.4 GHz; `ath9k_htc` is in-kernel and works without extra drivers. Good first adapter. |
| Alfa AWUS036ACH | Realtek RTL8812AU | Dual-band; needs the out-of-tree DKMS driver |
| TP-Link TL-WN722N v1 | Atheros AR9271 | Only v1 uses the Atheros chip; check the label |

Driver compilation and VM USB passthrough are covered in
[04/hardware-and-setup.md](04-wireless-security-aircrack/hardware-and-setup.md).

</details>

## Repository layout

```text
Kali-Linux-for-beginners/
├── 01-terminal-and-linux-core/       # Level 0
├── 02-system-admin-and-privileges/   # Level 1
├── 03-network-recon-and-nmap/        # Level 2
├── 04-wireless-security-aircrack/    # Level 2
├── 05-packet-analysis-wireshark/     # Level 3
├── cheatsheets/                      # Quick reference
├── lab/                              # Lab images: attacker, web-target, ftp-service
├── scripts/
│   ├── setup-lab-env.sh              # Guarded lab launcher
│   ├── parse-nmap-xml.py             # Nmap XML to terminal table
│   └── build-site.py                 # Generates the docs site from the repo
├── site/                             # Docs site assets (CSS, JS, service worker)
├── tests/                            # pytest for the scripts, lab smoke test
├── docker-compose.yml                # Practice lab (attacker + targets)
└── .github/workflows/ci.yml          # Lint, tests, lab smoke test, site deploy
```

Turn an Nmap scan into a readable table:

```bash
nmap -sV -oX - 10.77.0.10 | parse-nmap-xml.py -     # in the attacker shell (on PATH)
# from your own clone instead: ./scripts/parse-nmap-xml.py scan.xml
```

## Documentation site

The site at https://tmhsdigital.github.io/Kali-Linux-for-beginners/ renders this
repository with full-text search (it finds commands, not just page titles),
progress tracking, dark and light themes, printable cheatsheets, and offline
support after your first visit.

It's generated from the repository. CI runs
[`scripts/build-site.py`](scripts/build-site.py) on every push. The script scans
the repo, builds the navigation from the directory structure, takes each page's
title from its first heading, and pre-renders every page to static HTML, so each
document has its own URL, link preview, and search-engine entry. Adding a module
or cheatsheet is enough for it to appear; no site edits are needed.

<details>
<summary>Preview the site locally</summary>

<br>

```bash
pip install -r requirements-dev.txt        # markdown-it-py + Pygments (+ test tools)
python scripts/build-site.py --out _site
cd _site && python -m http.server 8099     # open http://127.0.0.1:8099
```

To publish, set the repository's Pages source to GitHub Actions
(Settings, then Pages, then Build and deployment, then Source: GitHub Actions).

</details>

## Contributing

Content is Markdown under the module and `cheatsheets/` directories. Because the
site is generated from the file tree, adding a `NN-topic/` folder with a
`README.md` (its first heading becomes the navigation title) is all that is
required; the site and navigation update on the next push. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the content rules and local checks.

## Credits

The curriculum follows the concepts in freeCodeCamp's *Hands-On Cybersecurity
and Ethical Hacking* by Sunny Malu, reorganized into modules with a practice
lab, expected output, and defensive notes.

## License

[MIT](LICENSE), with an educational and authorized-testing disclaimer.
