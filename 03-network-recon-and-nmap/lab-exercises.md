# Lab exercises: Network recon & Nmap

Map the practice lab the way you would map a real engagement: find what's
alive, find what's listening, name the software, and save it all in a form you
can report on. Each task has a **goal**, the **commands** to try, and a
**self-grading check** that prints `PASS` when you got it right.

> **Authorized targets only.** Scan `10.77.0.0/24`, the bundled lab, and
> nothing else.

Run everything from the attacker's root shell, `./scripts/setup-lab-env.sh
shell`. Work in a scratch folder under `/root/work`, which shows up in
`workspace/` in your clone:

```bash
mkdir -p /root/work/lab03 && cd /root/work/lab03
```

---

## Exercise 1: Find every live host

**Goal:** Sweep the lab subnet without port scanning, save the result in
greppable format, and pull out a plain list of live addresses.

```bash
nmap -sn 10.77.0.0/24 -oG sweep.gnmap
grep "Status: Up" sweep.gnmap | cut -d" " -f2 > live-hosts.txt
cat live-hosts.txt
```

Expected output of the last command (the order can vary):

```text
10.77.0.1
10.77.0.10
10.77.0.20
10.77.0.5
```

`10.77.0.1` is the bridge gateway (your own machine) and `10.77.0.5` is the
attacker you're sitting on. Only `.10` and `.20` are targets.

**Self-grade:**

```bash
grep -qx 10.77.0.10 live-hosts.txt && grep -qx 10.77.0.20 live-hosts.txt \
  && echo "PASS: both targets found" \
  || echo "FAIL: live-hosts.txt is missing a target, re-run the sweep"
```

---

## Exercise 2: Find every open port

**Goal:** Scan all 65,535 TCP ports on both targets, not just Nmap's default
top 1,000, and work out which ports are open.

```bash
nmap -p- --open 10.77.0.10 10.77.0.20 -oG ports.gnmap
```

Read the scan output, then answer the questions in the check.

**Self-grade:**

```bash
read -rp "Open TCP port on 10.77.0.10: " web
read -rp "Open TCP port on 10.77.0.20: " ftp
grep -q "closed (65534)" ports.gnmap \
  && grep -q "10.77.0.10 .*Ports: ${web:-x}/open/" ports.gnmap \
  && grep -q "10.77.0.20 .*Ports: ${ftp:-x}/open/" ports.gnmap \
  && echo "PASS: full-range scan saved and both ports right" \
  || echo "FAIL: check your answers, and that you used -p- (all ports)"
```

**Think it through:** a default scan would have found the same ports here. On
a real network, services hide on high ports precisely because nobody scans
them. `-p-` is slower, but it's how you avoid missing them.

---

## Exercise 3: Name the software

**Goal:** Use version detection to find out exactly which web server
`10.77.0.10` runs.

```bash
nmap -sV -p80 10.77.0.10
```

**Self-grade:** answer with the version number only, for example `1.2.3`. The
check re-scans the target, so it stays right when the lab image is updated.

```bash
read -rp "nginx version on 10.77.0.10: " ans
[ -n "$ans" ] && nmap -sV -p80 10.77.0.10 | grep -Eq "nginx ${ans}( |$)" \
  && echo "PASS: version identified" \
  || echo "FAIL: look at the VERSION column of the -sV scan"
```

**Defensive note:** a version string tells an attacker which CVEs to try. Hide
it where you can (`server_tokens off;` in nginx) and, more importantly, keep the
software patched so the version doesn't matter.

---

## Exercise 4: Save a scan and turn it into a report table

**Goal:** Save one scan in all three formats with `-oA`, then use the repo's
parser to turn the XML into a CSV you could hand to someone.

```bash
nmap -sV -p21,80 -oA lab 10.77.0.10 10.77.0.20
ls lab.*
parse-nmap-xml.py --format csv lab.xml > lab.csv
cat lab.csv
```

Expected output of the last command (versions can be newer):

```text
address,hostname,status,port,protocol,state,service,product,version,scripts
10.77.0.10,web-target.pentest-lab-net,up,80,tcp,open,http,nginx,1.31.9,
10.77.0.20,ftp-service.pentest-lab-net,up,21,tcp,open,ftp,vsftpd,2.0.8 or later,
```

**Self-grade:**

```bash
[ -s lab.nmap ] && [ -s lab.gnmap ] && [ -s lab.xml ] \
  && grep -q "^10.77.0.20,.*,21,tcp,open,ftp," lab.csv \
  && echo "PASS: three formats saved and parsed" \
  || echo "FAIL: you need lab.nmap, lab.gnmap, lab.xml, and lab.csv"
```

---

## Exercise 5: Follow up a script finding

**Goal:** Let the scripting engine check the FTP server for anonymous access,
then prove the finding by downloading the file it exposes.

```bash
nmap -p21 --script ftp-anon 10.77.0.20
curl -s ftp://10.77.0.20/pub/                    # anonymous directory listing
curl -s -o welcome.txt ftp://10.77.0.20/pub/welcome.txt
cat welcome.txt
```

**Self-grade:** the check compares a SHA-256 hash, so it doesn't give the file
away.

```bash
[ "$(sha256sum < welcome.txt | cut -d' ' -f1)" = \
  "3dc9a3611c14c5ca621935c7ab48d29aaab31434329b7dea05986112782fdd60" ] \
  && echo "PASS: anonymous FTP finding confirmed" \
  || echo "FAIL: download pub/welcome.txt from 10.77.0.20"
```

**Defensive note:** a scanner result is a lead, not a finding. Confirming it,
as you just did, is what turns it into evidence for a report. On a real server,
`anonymous_enable=NO` in `vsftpd.conf` closes this.

---

## Cleanup

```bash
cd /root/work && rm -rf lab03
echo "Lab 03 files removed."
```

---

### Scorecard

| # | Skill demonstrated |
|---|--------------------|
| 1 | Host discovery with `-sn`, greppable output |
| 2 | Full-range port scan with `-p-` |
| 3 | Version detection with `-sV` |
| 4 | `-oA` output and `parse-nmap-xml.py` |
| 5 | NSE script finding, confirmed by hand |

Five PASSes and you're ready for **[module 04, Wireless security &
Aircrack-ng](../04-wireless-security-aircrack/)**.
