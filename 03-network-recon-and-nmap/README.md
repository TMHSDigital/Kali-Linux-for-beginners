# 03 — Network Recon & Nmap `[Level 2: Reconnaissance]`

Reconnaissance answers three questions before any exploitation: *what hosts are
alive, what services do they run, and what versions are those services?* Nmap is
the canonical tool for all three. This module explains the TCP/IP mechanics that
make scanning work, then drills each scan type with the flags you'll actually
use in the field — always against the isolated Docker lab from the repo root.

> **Authorized targets only.** Everything here should be run against
> `172.28.0.0/16` (the bundled lab) or infrastructure you own / have written
> permission to test. Port scanning third-party hosts can be illegal.

---

## 1. How scanning works (TCP/IP architecture)

Nmap infers a port's state from how the target's TCP/IP stack responds to
carefully crafted packets. The **TCP three-way handshake** underpins most of it:

```text
Client                         Server
  | ---- SYN --------------->  |   "can we talk?"
  | <--- SYN/ACK ------------  |   "yes" (port OPEN)
  | ---- ACK --------------->  |   connection established
```

From the response Nmap classifies each port:

| Probe result | Port state | Meaning |
|--------------|-----------|---------|
| SYN/ACK | **open** | Something is listening |
| RST (reset) | **closed** | Host is up, nothing listening on that port |
| No response / ICMP unreachable | **filtered** | A firewall dropped the probe |

That third case is why firewalls matter (section 6): **drop** vs **reject**
changes what Nmap can even see.

---

## 2. Know your own network first (host & interface enumeration)

Before scanning others, map your own position on the network.

```bash
# [Level 0: Fundamental] Interfaces and IP addresses
ip a                       # all interfaces, IPs, MACs, up/down state
ip -brief a                # compact one-line-per-interface summary
ip route                   # routing table — where does traffic go? (default gw)
ip neigh                   # ARP/neighbor cache — hosts you've recently talked to

# [Level 0: Fundamental] What is MY machine listening on? (local footprint)
ss -tuln                   # TCP+UDP listening sockets, numeric ports
#   -t tcp  -u udp  -l listening  -n numeric (don't resolve names)
ss -tulpn                  # add -p to show the owning process (needs root)

# [Level 1: Intermediate] DNS resolution
dig example.com            # full DNS query/answer detail
dig +short example.com     # just the answer
dig -x 172.28.0.10         # reverse lookup (PTR)
nslookup example.com       # simpler, interactive-capable resolver query
host example.com           # one-line answer
```

Expected `ip -brief a`:

```text
lo               UNKNOWN   127.0.0.1/8 ::1/128
eth0             UP        172.28.0.5/16
```

---

## 3. Host discovery — who is alive? `[Level 1: Intermediate]`

Before port-scanning, find live hosts so you don't waste time on empty IPs.

```bash
# Ping scan (-sn): no port scan, just "is it up?"
nmap -sn 172.28.0.0/24               # sweep the lab /24
nmap -sn 172.28.0.10 172.28.0.20     # specific hosts

# Skip discovery entirely (-Pn): treat every host as up. Use when ICMP/probes
# are firewalled and -sn wrongly reports hosts as down.
nmap -Pn 172.28.0.10

# List targets WITHOUT sending packets (-sL): sanity-check your target spec
nmap -sL 172.28.0.0/28
```

Expected `-sn` output:

```text
Nmap scan report for 172.28.0.10
Host is up (0.00021s latency).
Nmap scan report for 172.28.0.20
Host is up (0.00018s latency).
Nmap done: 256 IP addresses (2 hosts up) scanned in 2.15 seconds
```

---

## 4. Port scan types — the core of Nmap

### TCP Connect vs SYN Stealth

```bash
# [Level 1: Intermediate] TCP Connect (-sT): completes the full handshake.
# No root needed. Reliable, but the full connection is logged by the target app.
nmap -sT 172.28.0.10

# [Level 2+: Advanced / Field Ops] SYN "stealth" (-sS): sends SYN, reads the
# reply, then sends RST instead of completing the handshake. Faster and less
# likely to be logged by the application layer. REQUIRES ROOT (raw sockets).
sudo nmap -sS 172.28.0.10
```

Why "stealth" is only half-true: `-sS` avoids the *application's* connection log
(the app never sees a completed connect), but a modern IDS/firewall logging at
the packet layer still sees the SYN. It's stealthier, not invisible.

### UDP scanning

```bash
# [Level 2+: Advanced / Field Ops] UDP (-sU): slow and tricky. UDP has no
# handshake, so "no reply" is ambiguous (open OR filtered). Nmap relies on ICMP
# port-unreachable for 'closed'. Scope it tightly to stay sane.
sudo nmap -sU --top-ports 20 172.28.0.10
sudo nmap -sU -p 53,67,123,161 172.28.0.10   # DNS, DHCP, NTP, SNMP
```

### Service & version detection, OS fingerprinting

```bash
# [Level 1: Intermediate] Service/version detection (-sV): grabs banners and
# matches them against Nmap's signature DB to name product + version.
nmap -sV 172.28.0.10

# [Level 2+: Advanced / Field Ops] OS fingerprinting (-O): infers the OS from
# TCP/IP stack quirks. Needs root and at least one open + one closed port.
sudo nmap -O 172.28.0.10

# Combine the greatest hits: version + OS + default scripts + traceroute
sudo nmap -A 172.28.0.10
```

Expected `-sV` against the lab web target:

```text
PORT   STATE SERVICE VERSION
80/tcp open  http    nginx 1.27.x
```

---

## 5. Targeting, timing, and the scripting engine

### Port specification

```bash
nmap 172.28.0.10                       # default: top 1000 TCP ports
nmap -p 80,443,8080 172.28.0.10        # specific ports
nmap -p 1-1024 172.28.0.10             # a range
nmap -p- 172.28.0.10                   # ALL 65535 TCP ports (thorough, slower)
nmap --top-ports 100 172.28.0.10       # the 100 statistically most common
nmap -p U:53,T:80,443 172.28.0.10      # mix UDP and TCP in one spec
```

### Timing templates `-T0`..`-T5`

Timing trades speed for stealth and reliability. Higher = faster/louder.

| Template | Name | Use when |
|----------|------|----------|
| `-T0` | paranoid | IDS evasion; one probe every ~5 min (glacial) |
| `-T1` | sneaky | slow, evasive |
| `-T2` | polite | reduce bandwidth/target load |
| `-T3` | **normal** (default) | balanced |
| `-T4` | aggressive | fast networks / lab / authorized speed |
| `-T5` | insane | very fast, may miss results / overwhelm targets |

```bash
sudo nmap -sS -T4 172.28.0.10          # a good default for a cooperative lab
sudo nmap -sS -T1 -f 172.28.0.10       # slow + fragment packets to dodge IDS
```

### Nmap Scripting Engine (NSE)

```bash
# [Level 2+: Advanced / Field Ops] Run script categories
nmap --script=default 172.28.0.10          # the '-sC' default set
nmap -sC -sV 172.28.0.10                    # shorthand: default scripts + version
nmap --script=safe 172.28.0.10             # non-intrusive checks only
nmap --script=vuln 172.28.0.10             # known-vulnerability probes (louder)
nmap --script=http-title,http-headers 172.28.0.10   # pick specific scripts
nmap --script "ftp-*" 172.28.0.20          # all FTP scripts (glob) on the FTP box
```

> `--script=vuln` and many `intrusive` scripts actively poke services and can
> crash fragile ones. Never run them outside authorized scope; get sign-off
> before pointing them at production.

---

## 6. Output formats (and feeding the parser) `[Level 1: Intermediate]`

Always save your scans — for reporting, diffing, and tooling.

```bash
nmap -sV -oN scan.nmap 172.28.0.10      # -oN: human-readable ("normal")
nmap -sV -oG scan.gnmap 172.28.0.10     # -oG: greppable (one host per line)
nmap -sV -oX scan.xml 172.28.0.10       # -oX: XML (machine-parseable)
nmap -sV -oA scan 172.28.0.10           # -oA: ALL three at once (scan.*)

# Feed the XML into the repo's parser for a clean port/service/version table:
nmap -sV -oX lab.xml 172.28.0.10 172.28.0.20
../scripts/parse-nmap-xml.py lab.xml
# ...or stream straight through without a temp file:
nmap -sV -oX - 172.28.0.10 | ../scripts/parse-nmap-xml.py -
```

---

## 7. Defensive visibility — how targets see (or don't see) you

Understanding the defender's view makes you both a better attacker and a better
blue-teamer.

### Firewall: DROP vs REJECT

- **DROP** — the firewall silently discards the probe. Nmap gets *no response*
  and marks the port **filtered**. Scans are slower (Nmap waits for timeouts)
  and you learn less. This is the stealthier defense.
- **REJECT** — the firewall replies with a TCP RST or ICMP unreachable. Nmap
  learns the port is **closed/filtered** *immediately* — faster for the
  attacker, but the reply confirms a live host/firewall.

```text
# iptables examples a defender might use:
iptables -A INPUT -p tcp --dport 22 -j DROP     # invisible; scans hang
iptables -A INPUT -p tcp --dport 22 -j REJECT   # fast RST; confirms presence
```

### What trips an IDS/IPS

- **SYN scans without follow-through** (many half-open connections) — a signature
  Snort/Suricata rules flag readily.
- **Fast timing** (`-T4`/`-T5`) and **full-range** (`-p-`) sweeps generate
  volume that rate-based rules catch.
- **`-sU`, `-O`, and `--script=vuln`** produce unusual probe patterns.
- **Sequential port touches** from one source in a short window = textbook
  port-scan alert.

Defender takeaways: log at the packet layer (not just the app), rate-limit new
connections, alert on horizontal (many hosts, one port) and vertical (one host,
many ports) sweeps, and prefer DROP to slow attackers down.

---

## Common troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `-sS`/`-sU`/`-O` fails: "requires root" | Raw sockets need privilege | Prefix with `sudo` |
| All hosts show "down" | ICMP/probes filtered | Add `-Pn` to skip host discovery |
| Scan is painfully slow | DROP firewall + timeouts, or `-p-` | Raise `-T`, scope ports, add `--min-rate` |
| `-sV` says "tcpwrapped" | Service closes the connection after banner | Try again; may be a proxy/firewall |
| No lab hosts found | Docker lab not up | `docker compose up -d` from repo root |
| OS detection "too many fingerprints" | No open+closed port pair found | Scan more ports; `-Pn` if needed |

---

➡️ Ready-to-run, scenario-organized commands live in
**[scan-profiles.md](scan-profiles.md)**.
