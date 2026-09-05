# Nmap Scan Profiles — Production-Ready One-Liners

Copy-pasteable Nmap invocations organized by **assessment scenario**. Replace
`$T` with your authorized target (a host, a comma list, or a CIDR range). All
examples default to the isolated lab; keep it that way unless you have written
authorization.

```bash
# Set your target once, then paste any profile below.
T="172.28.0.0/24"      # e.g. the lab subnet
# T="172.28.0.10 172.28.0.20"   # or specific hosts
```

> Legend for tags: `[L1]` intermediate · `[L2]` advanced/field-ops. Anything
> using `-sS`, `-sU`, `-O`, or OS/packet features needs `sudo`.

---

## A. Discovery — "what's alive?"

```bash
# [L1] Fast ping sweep of a subnet (no port scan)
nmap -sn "$T"

# [L1] Discovery + save a list of live hosts for later, grep the up ones
nmap -sn "$T" -oG - | awk '/Up$/{print $2}' > live-hosts.txt

# [L2] Discovery when ICMP is filtered: probe common TCP ports for liveness
sudo nmap -sn -PS22,80,443,3389 -PA80 "$T"

# [L2] ARP scan (fastest, most reliable on a local L2 segment; needs root)
sudo nmap -sn -PR "$T"
```

---

## B. Speed — "quick look, minimal wait"

```bash
# [L1] Top 100 ports, fast timing — a rapid triage sweep
nmap -F -T4 "$T"                       # -F = top 100 ports

# [L2] Aggressive rate-limited full-TCP where you control the network
sudo nmap -sS -p- -T4 --min-rate 2000 "$T"

# [L2] "Masscan-style" speed: find open ports fast, then version-scan only those
ports=$(sudo nmap -sS -p- -T4 --min-rate 5000 172.28.0.10 \
        | awk -F/ '/open/{print $1}' | paste -sd,)
nmap -sV -p "$ports" 172.28.0.10
```

---

## C. Thoroughness — "leave nothing unscanned"

```bash
# [L2] Full TCP port range with version + default scripts + OS + traceroute
sudo nmap -sS -p- -sV -sC -O --traceroute -T4 -oA full-tcp "$T"

# [L2] Add the top UDP ports (UDP is slow — keep it bounded)
sudo nmap -sU --top-ports 50 -sV -T4 -oA full-udp "$T"

# [L2] Everything-and-the-kitchen-sink single host, all output formats
sudo nmap -A -p- -T4 -oA deep-172-28-0-10 172.28.0.10
```

---

## D. Stealth / evasion — "stay quiet" (authorized red-team only)

```bash
# [L2] Slow SYN scan, fragmented packets, no ping, decoy timing
sudo nmap -sS -Pn -f -T1 -p 21,22,80,443 172.28.0.10

# [L2] Decoys: hide your real IP among fakes (ME = your position in the list)
sudo nmap -sS -Pn -D 10.0.0.5,10.0.0.6,ME,10.0.0.7 172.28.0.10

# [L2] Spoof source port (some firewalls trust 53/80) and randomize host order
sudo nmap -sS -Pn --source-port 53 --randomize-hosts -T2 "$T"

# [L2] Idle/zombie scan — attribute the scan to a third "zombie" host
sudo nmap -sI <zombie_ip> 172.28.0.10
```

> These reduce (never eliminate) detectability and legitimately trip IDS if
> mis-scoped. Only run inside an engagement whose rules of engagement permit it.

---

## E. Service enumeration — "what exactly is running?"

```bash
# [L1] Version detection with light intensity (faster, less certain)
nmap -sV --version-intensity 2 "$T"

# [L2] Max version intensity (all probes) for stubborn services
nmap -sV --version-intensity 9 172.28.0.10

# [L1] Default + version, the everyday enumeration combo
nmap -sC -sV -oA enum "$T"

# [L2] Banner grab specific services
nmap -sV -p 21 --script=banner 172.28.0.20        # FTP banner
nmap -sV -p 80 --script=http-title,http-headers,http-methods 172.28.0.10
```

---

## F. Vulnerability & script scanning — "known issues" (louder, authorized)

```bash
# [L2] Safe, non-intrusive checks only
nmap --script=safe -sV "$T"

# [L2] The vuln category (actively probes for known CVEs — can be disruptive)
nmap --script=vuln -sV 172.28.0.10

# [L2] FTP-specific: anonymous login + known vsftpd issues (our lab FTP box)
nmap -p 21 --script "ftp-anon,ftp-syst,ftp-vsftpd-backdoor" 172.28.0.20

# [L2] HTTP enumeration bundle
nmap -p 80 --script "http-enum,http-title,http-headers" 172.28.0.10
```

---

## G. Lab-specific quick wins (against the bundled Docker targets)

```bash
# 1) Confirm both lab targets are up
nmap -sn 172.28.0.0/24

# 2) Full service picture of both boxes, saved as XML, piped to the parser
nmap -sV -sC -oX lab.xml 172.28.0.10 172.28.0.20
../scripts/parse-nmap-xml.py lab.xml

# 3) Prove the web target speaks plain HTTP (feeds module 05 capture work)
nmap -p 80 -sV --script=http-methods,http-title 172.28.0.10

# 4) Prove the FTP target allows anonymous login (cleartext auth for module 05)
nmap -p 21 -sV --script=ftp-anon 172.28.0.20
```

Expected shape from profile G-2 via the parser:

```text
Host: 172.28.0.10   Status: up
  PORT   PROTO  STATE  SERVICE  PRODUCT / VERSION
  80     tcp    open   http     nginx 1.27.x

Host: 172.28.0.20   Status: up
  PORT   PROTO  STATE  SERVICE  PRODUCT / VERSION
  21     tcp    open   ftp      vsftpd 3.x
```

---

## Flag quick-reference

| Flag | Meaning |
|------|---------|
| `-sn` | Host discovery only (no ports) |
| `-Pn` | Skip discovery; assume host up |
| `-sT` / `-sS` | TCP connect / SYN stealth |
| `-sU` | UDP scan |
| `-sV` | Service/version detection |
| `-O` / `-A` | OS detection / aggressive (OS+version+scripts+traceroute) |
| `-p-` / `-F` / `--top-ports N` | all ports / top 100 / top N |
| `-T0`..`-T5` | timing: paranoid → insane |
| `-sC` / `--script=` | default scripts / choose scripts or categories |
| `-f` / `-D` / `--source-port` | fragment / decoys / spoof source port |
| `--min-rate` / `--max-rate` | packets-per-second floor / ceiling |
| `-oN`/`-oG`/`-oX`/`-oA` | normal / greppable / XML / all outputs |
