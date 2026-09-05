<div align="center">

# Kali Linux for Beginners
### Zero to Field-Ready

A modular, hands-on curriculum and field reference for offensive & defensive security — scaled from absolute beginner to expert tradecraft.

[![Docs site](https://img.shields.io/badge/docs-live%20site-3fb950?style=flat-square)](https://tmhsdigital.github.io/Kali-Linux-for-beginners/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Made for](https://img.shields.io/badge/platform-Kali%20Linux-557c94?style=flat-square)](https://www.kali.org/)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-orange?style=flat-square)](#contributing)

**📖 [Read the docs online →](https://tmhsdigital.github.io/Kali-Linux-for-beginners/)**

</div>

---

Built on the foundations of freeCodeCamp's *Hands-On Cybersecurity and Ethical Hacking* by Sunny Malu, then expanded into a structured path. Every module pairs **how the subsystem actually works** with **fully commented, copy-pasteable commands**, expected output, defensive counter-measures, and troubleshooting — plus a one-command Docker lab of safe practice targets.

> [!WARNING]
> **For education and authorized testing only.** Using these techniques against
> systems, networks, or wireless access points you don't own or lack **written**
> permission to test is illegal in most jurisdictions. You are solely responsible
> for your actions. See the [full disclaimer](LICENSE).

---

## 🚀 Quickstart

```bash
# 1. Clone
git clone https://github.com/TMHSDigital/Kali-Linux-for-beginners.git
cd Kali-Linux-for-beginners

# 2. Launch the isolated practice-target lab (Docker required)
./scripts/setup-lab-env.sh          # verifies Docker + bridge, then starts it
#   └─ or:  docker compose up -d

# 3. Start learning — open module 01, or browse the live docs site.
```

Lab targets come up on an isolated `172.28.0.0/16` bridge:

| Target | Address | Purpose |
|--------|---------|---------|
| `web-target` | `172.28.0.10` | Plain-HTTP login form → intercept cleartext credentials |
| `ftp-service` | `172.28.0.20` | Anonymous FTP → capture cleartext auth |

Tear down anytime with `docker compose down`.

---

## 🗺️ Curriculum

Four levels, five modules. Each links to its full write-up.

| Level | Module | You'll be able to… |
|:-----:|--------|--------------------|
| **0** · Fundamentals | **[01 · Terminal & Linux Core](01-terminal-and-linux-core/)** | Navigate, inspect, and manipulate Linux fluently; pipes & redirection |
| **1** · Administration | **[02 · System Admin & Privileges](02-system-admin-and-privileges/)** | Read the Unix privilege model; audit SUID & sudo for escalation surface |
| **2** · Recon | **[03 · Network Recon & Nmap](03-network-recon-and-nmap/)** | Map a network; choose the right scan for stealth, speed, or depth |
| **2** · Wireless | **[04 · Wireless Security & Aircrack-ng](04-wireless-security-aircrack/)** | Capture & crack a WPA2 handshake in a lab; understand WPA3/PMF defenses |
| **3** · Forensics | **[05 · Packet Analysis & Wireshark](05-packet-analysis-wireshark/)** | Reassemble sessions, extract cleartext creds, and articulate the fix |

Every command is tagged by depth so you can find your level:
`[Level 0: Fundamental]` · `[Level 1: Intermediate]` · `[Level 2+: Advanced / Field Ops]`

### 📌 New here? Start at **[module 01](01-terminal-and-linux-core/)** → do its **lab exercises** (they self-grade) → move on. Keep the **[cheatsheets](cheatsheets/)** open in a second pane.

---

## 📚 Quick reference

High-density, zero-filler cheatsheets:

- **[Kali survival commands](cheatsheets/01-kali-survival-commands.md)** — the everyday shell
- **[Nmap tactical reference](cheatsheets/02-nmap-tactical-reference.md)** — every flag that matters
- **[Aircrack-ng workflow](cheatsheets/03-aircrack-workflow.md)** — capture → deauth → crack
- **[Wireshark BPF & display filters](cheatsheets/04-wireshark-bpf-and-display.md)** — both filter languages

---

## 🧰 Lab environment setup

<details>
<summary><strong>Choose your platform</strong> (bare-metal · VirtualBox · VMware · WSL2)</summary>

<br>

You need Kali Linux (or any Debian-based distro). Pick the path matching your hardware:

- **Bare-metal** — best wireless performance; the only option with unrestricted access to internal radios. **Required for reliable monitor-mode work (module 04).**
- **VirtualBox** — install the **Extension Pack** for USB passthrough; ≥ 2 vCPU / 4 GB RAM / 40 GB disk; use Host-Only/NAT Network to isolate the lab.
- **VMware Workstation/Fusion** — smoother USB passthrough for RTL8812AU-class Wi-Fi adapters; use a Host-Only `vmnet` to fence off the lab.
- **WSL2** — `wsl --install -d kali-linux` gives the full CLI toolchain. **No native 802.11 radio access**, so use it for modules 01–03 and 05 (analyzing saved captures with `tshark`); use bare-metal or a full VM for live wireless.

</details>

<details>
<summary><strong>Recommended Wi-Fi adapters</strong> (monitor mode + injection)</summary>

<br>

| Adapter | Chipset | Notes |
|---------|---------|-------|
| Alfa AWUS036NHA | Atheros **AR9271** | 2.4 GHz; `ath9k_htc` is **in-kernel** — works out of the box. **Best first adapter.** |
| Alfa AWUS036ACH | Realtek **RTL8812AU** | Dual-band; needs the out-of-tree DKMS driver |
| TP-Link TL-WN722N **v1** | Atheros AR9271 | Only **v1** uses Atheros — check the label |

Driver compilation and VM USB passthrough: **[04 · hardware-and-setup.md](04-wireless-security-aircrack/hardware-and-setup.md)**.

</details>

---

## 📁 Repository layout

```text
Kali-Linux-for-beginners/
├── 01-terminal-and-linux-core/       # Level 0
├── 02-system-admin-and-privileges/   # Level 1
├── 03-network-recon-and-nmap/        # Level 2
├── 04-wireless-security-aircrack/    # Level 2
├── 05-packet-analysis-wireshark/     # Level 3
├── cheatsheets/                      # Quick reference
├── scripts/
│   ├── setup-lab-env.sh              # Guarded lab launcher
│   ├── parse-nmap-xml.py             # Nmap XML → clean terminal table
│   └── build-site.py                 # Generates the docs site from the repo
├── site/                             # Docs site source (static, no build tools)
├── docker-compose.yml                # Isolated practice targets
└── .github/workflows/pages.yml       # Auto-deploys the docs site
```

**Handy:** turn any Nmap scan into a readable table —

```bash
nmap -sV -oX - 172.28.0.10 | ./scripts/parse-nmap-xml.py -
```

---

## 🌐 Documentation site

The live site at **[tmhsdigital.github.io/Kali-Linux-for-beginners](https://tmhsdigital.github.io/Kali-Linux-for-beginners/)**
renders this repo with search, dark/light themes, and section navigation.

It's **fully dynamic**: a GitHub Action runs [`scripts/build-site.py`](scripts/build-site.py)
on every push, which scans the repo, derives navigation from the directory
structure, and reads each page's title from its first heading. **Add a module or
cheatsheet and it appears automatically — no site edits required.**

<details>
<summary>Preview the site locally</summary>

<br>

```bash
python scripts/build-site.py --out _site   # generate manifest + copy content
cd _site && python -m http.server 8099     # serve (fetch() needs http://, not file://)
# open http://127.0.0.1:8099
```

One-time repo setting to publish: **Settings → Pages → Build and deployment →
Source: GitHub Actions.**

</details>

---

## Contributing

Content lives in Markdown under the module and `cheatsheets/` directories.
Because the site is generated from the file tree, a new `NN-topic/` folder with a
`README.md` (first `# heading` becomes the nav title) is all it takes to add a
module — the docs site and navigation update on the next push.

## License

[MIT](LICENSE) with an educational and authorized-testing disclaimer. Use responsibly.
