# Kali Linux for Beginners

A hands-on Kali Linux and ethical-hacking curriculum that goes from beginner
shell skills through system administration, network reconnaissance, wireless
security, and packet analysis. It is based on the concepts in freeCodeCamp's
*Hands-On Cybersecurity and Ethical Hacking* by Sunny Malu, organized into
modules with commands, expected output, defensive notes, and a Docker lab of
safe practice targets.

Documentation site: https://tmhsdigital.github.io/Kali-Linux-for-beginners/

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

## Curriculum

Four levels across five modules. Each links to its full write-up.

| Level | Module | Outcome |
|-------|--------|---------|
| 0, Fundamentals | [01. Terminal & Linux Core](01-terminal-and-linux-core/) | Navigate, inspect, and manipulate Linux from the shell; pipes and redirection |
| 1, Administration | [02. System Admin & Privileges](02-system-admin-and-privileges/) | Read the Unix privilege model; audit SUID and sudo for escalation surface |
| 2, Recon | [03. Network Recon & Nmap](03-network-recon-and-nmap/) | Map a network and choose the right scan for stealth, speed, or depth |
| 2, Wireless | [04. Wireless Security & Aircrack-ng](04-wireless-security-aircrack/) | Capture and crack a WPA2 handshake in a lab; understand WPA3 and PMF defenses |
| 3, Forensics | [05. Packet Analysis & Wireshark](05-packet-analysis-wireshark/) | Reassemble sessions, extract cleartext credentials, and describe the fix |

Commands are tagged by depth so you can find your level:
`[Level 0: Fundamental]`, `[Level 1: Intermediate]`, `[Level 2+: Advanced / Field Ops]`.

If you are new, start at [module 01](01-terminal-and-linux-core/), do its lab
exercises (they self-grade), then continue in order. Keep the
[cheatsheets](cheatsheets/) open alongside the modules.

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
├── site/                             # Docs site source (static, no build tools)
├── docker-compose.yml                # Practice lab (attacker + targets)
└── .github/workflows/pages.yml       # Deploys the docs site
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
required; the site and navigation update on the next push.

## License

[MIT](LICENSE), with an educational and authorized-testing disclaimer.
