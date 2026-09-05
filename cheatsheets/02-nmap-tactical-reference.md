# Nmap Tactical Reference

Dense flag + workflow reference for module 03. Anything with `-sS`, `-sU`, `-O`,
or OS/packet-level features needs `sudo`. Scan only authorized targets.

---

## Target specification

| Syntax | Meaning |
|--------|---------|
| `192.168.1.1` | Single host |
| `192.168.1.1 192.168.1.5` | Multiple hosts |
| `192.168.1.0/24` | CIDR range (256 addrs) |
| `192.168.1.1-50` | Octet range |
| `192.168.1.*` | Wildcard octet |
| `-iL targets.txt` | Read targets from file |
| `--exclude 192.168.1.1` | Omit host(s) |
| `-sL` | List targets only (no packets sent) |

## Host discovery

| Flag | Action |
|------|--------|
| `-sn` | Ping scan — discovery only, no ports |
| `-Pn` | Skip discovery — treat all hosts as up |
| `-PS<ports>` | TCP SYN ping to ports |
| `-PA<ports>` | TCP ACK ping |
| `-PU<ports>` | UDP ping |
| `-PE` / `-PP` / `-PM` | ICMP echo / timestamp / netmask ping |
| `-PR` | ARP ping (fast, local segment) |
| `-n` / `-R` | Never / always do DNS resolution |

## Scan types

| Flag | Type | Notes |
|------|------|-------|
| `-sS` | TCP SYN "stealth" | Default w/ root; fast; half-open |
| `-sT` | TCP Connect | No root needed; full handshake, app-logged |
| `-sU` | UDP | Slow; open\|filtered ambiguity |
| `-sA` | TCP ACK | Map firewall rules (filtered vs unfiltered) |
| `-sN` / `-sF` / `-sX` | Null / FIN / Xmas | Evade some stateless filters |
| `-sY` / `-sZ` | SCTP INIT / COOKIE-ECHO | SCTP services |
| `-b <ftp>` | FTP bounce | Legacy |

## Port specification

| Flag | Meaning |
|------|---------|
| `-p 80` / `-p 1-1024` | Port / range |
| `-p 80,443,8080` | List |
| `-p-` | All 65535 TCP ports |
| `-p U:53,T:80` | Mixed UDP/TCP |
| `-F` | Fast: top 100 ports |
| `--top-ports N` | Top N most common |
| `-r` | Scan ports in order (not randomized) |

## Service / OS detection

| Flag | Action |
|------|--------|
| `-sV` | Service/version detection |
| `--version-intensity 0-9` | Probe aggressiveness (9 = all) |
| `--version-light` / `--version-all` | Intensity 2 / 9 shortcuts |
| `-O` | OS fingerprinting |
| `--osscan-guess` | Aggressive OS guessing |
| `-A` | Aggressive: `-O -sV -sC --traceroute` |

## Timing & performance

| Flag | Action |
|------|--------|
| `-T0`..`-T5` | paranoid → insane |
| `-T4` | Aggressive (good lab default) |
| `--min-rate N` / `--max-rate N` | pkts/sec floor / ceiling |
| `--min-parallelism N` | Concurrent probes |
| `--host-timeout 30m` | Give up on slow hosts |
| `--max-retries N` | Probe retransmit cap |
| `--scan-delay Nms` | Pause between probes |

## NSE (scripting engine)

| Flag | Action |
|------|--------|
| `-sC` | Run `default` scripts |
| `--script=default,safe` | Run categories |
| `--script=vuln` | Known-vuln checks (louder, intrusive) |
| `--script="http-*"` | Glob by name |
| `--script-args k=v` | Pass args to scripts |
| `--script-help=NAME` | Describe a script |
| `nmap --script-updatedb` | Rebuild script DB |

Common categories: `auth default discovery safe intrusive vuln exploit brute
malware dos`.

## Firewall / IDS evasion (authorized only)

| Flag | Action |
|------|--------|
| `-f` / `--mtu N` | Fragment packets |
| `-D d1,d2,ME,d3` | Decoy source addresses |
| `-S <ip>` | Spoof source IP |
| `--source-port N` / `-g N` | Spoof source port (e.g. 53) |
| `--data-length N` | Append random bytes |
| `--randomize-hosts` | Shuffle target order |
| `-sI <zombie>` | Idle/zombie scan |
| `--spoof-mac <mac\|vendor\|0>` | Spoof MAC |

## Output

| Flag | Format |
|------|--------|
| `-oN file` | Normal (human) |
| `-oG file` | Greppable |
| `-oX file` | XML (feed `parse-nmap-xml.py`) |
| `-oA base` | All three |
| `-v` / `-vv` | Verbose |
| `-d` / `-dd` | Debug |
| `--reason` | Why a port is in its state |
| `--open` | Show only open ports |
| `--packet-trace` | Show every packet sent/recv |
| `--resume file` | Resume an aborted scan |

## Recipe one-liners

```bash
# Discover live hosts on a subnet
nmap -sn 172.28.0.0/24

# Fast triage of a host
nmap -F -T4 172.28.0.10

# Full TCP + version + default scripts, all outputs
sudo nmap -sS -p- -sV -sC -T4 -oA full 172.28.0.10

# Two-step: find open ports fast, then version just those
ports=$(sudo nmap -sS -p- -T4 --min-rate 5000 172.28.0.10 | awk -F/ '/open/{print $1}' | paste -sd,)
nmap -sV -p "$ports" 172.28.0.10

# Top UDP services
sudo nmap -sU --top-ports 20 172.28.0.10

# Vuln scripts (authorized)
nmap --script=vuln -sV 172.28.0.10

# XML → clean table via the repo parser
nmap -sV -oX - 172.28.0.10 | ../scripts/parse-nmap-xml.py -
```

## Port states cheat

| State | Meaning |
|-------|---------|
| `open` | Service listening |
| `closed` | Host up, nothing listening (RST) |
| `filtered` | No response — firewall dropped it |
| `unfiltered` | Reachable but state undetermined (ACK scan) |
| `open\|filtered` | Can't tell (common in UDP/NULL/FIN) |
| `closed\|filtered` | Can't tell (idle scan) |
