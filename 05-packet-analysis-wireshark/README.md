# 05 — Packet Analysis with Wireshark & tshark `[Level 3: Traffic Forensics]`

Once you can capture traffic, the skill becomes *reading* it: reconstructing
what happened on the wire, extracting cleartext secrets from insecure protocols,
and — crucially — articulating the fix. This module covers the capture engine,
the two very different filter languages, the core display filters you'll reach
for daily, session reassembly, credential extraction, and headless analysis with
`tshark`. Practice against the bundled Docker lab.

> Run the target lab first: from the repo root, `docker compose up -d`. Then
> capture on the interface facing `172.28.0.0/16` (often `docker0` or
> `br-pentestlab`). Only ever sniff traffic you are authorized to see.

---

## 1. The capture engine (architecture)

Wireshark itself doesn't touch the NIC — a **packet-capture library** does:

| Platform | Library | Notes |
|----------|---------|-------|
| Linux/Kali | **libpcap** | Kernel hands frames up via `AF_PACKET` |
| Windows | **Npcap** (successor to WinPcap) | Installs a driver; supports loopback + monitor mode |

Two capture modes to distinguish:

- **Promiscuous mode** — the NIC accepts *all* frames on the wire segment it can
  see, not just those addressed to it. On a switched network you mostly see your
  own traffic + broadcast/multicast unless the switch is mirroring a port. This
  is for **wired/Ethernet** sniffing.
- **Monitor mode (RFMON)** — the *wireless* equivalent from module 04: capture
  raw 802.11 frames off the air. Different mechanism, different use case.

On Kali, Wireshark needs capture privileges. The clean way:

```bash
# [Level 1: Intermediate] Allow non-root capture (recommended)
sudo dpkg-reconfigure wireshark-common   # answer "Yes" to non-superuser capture
sudo usermod -aG wireshark "$USER"        # then log out / back in
groups | grep wireshark                   # confirm membership
```

---

## 2. Capture filters (BPF) vs display filters — a critical distinction

Wireshark has **two entirely different filter languages**, and mixing them up is
the #1 beginner confusion.

|  | **Capture filter (BPF)** | **Display filter** |
|--|--------------------------|--------------------|
| When applied | *Before* capture — decides what hits disk | *After* capture — decides what's shown |
| Language | Berkeley Packet Filter (`tcpdump` syntax) | Wireshark's own expression language |
| Example | `tcp port 80` | `http.request.method == "POST"` |
| Can you recover filtered-out packets? | **No** — they were never recorded | **Yes** — clear the filter, they're still there |
| Memory/disk cost | Low — you only store what matches | High — everything is captured, then hidden |

**Rule of thumb:** use a **capture filter** to keep huge/high-rate captures
manageable (you know in advance you only care about one host/port). Use a
**display filter** for exploratory analysis, when you don't yet know what you're
looking for and don't want to lose anything.

```text
BPF capture filter examples (note the tcpdump-style syntax):
  host 172.28.0.10
  net 172.28.0.0/16
  tcp port 80 or tcp port 21
  src host 172.28.0.10 and not port 22
  ether host aa:bb:cc:11:22:33
```

```text
Display filter examples (note the protocol.field == value syntax):
  ip.addr == 172.28.0.10
  tcp.port == 80 && http
  http.request.method == "POST"
  ftp || ftp-data
```

They are **not interchangeable** — `tcp port 80` is a syntax error in the
display bar; `http.request.method == "POST"` is illegal as a capture filter.

---

## 3. Core display filters (your daily toolkit)

```text
# --- Addressing & ports -----------------------------------------------------
ip.addr == 172.28.0.10                # traffic to OR from that host
ip.src == 172.28.0.10                 # only sourced from it
ip.dst == 172.28.0.20                 # only destined to it
tcp.port == 21                        # either side is port 21
ip.addr == 172.28.0.10 && tcp.port == 80   # combine (X && Y)

# --- HTTP -------------------------------------------------------------------
http                                  # all HTTP
http.request                          # requests only
http.request.method == "POST"         # POSTs (where form creds live!)
http.request.method == "GET"
http.response.code == 200
http.host contains "acme"

# --- Credential hunting (cleartext protocols) -------------------------------
tcp contains "password"               # any packet whose bytes contain the word
tcp contains "USER" || tcp contains "PASS"   # FTP/POP/IMAP login verbs
ftp.request.command == "USER"         # FTP username
ftp.request.command == "PASS"         # FTP password (cleartext!)
http.authorization                    # HTTP Basic-Auth header (base64, trivially decoded)

# --- DNS --------------------------------------------------------------------
dns                                   # all DNS
dns.flags.response == 0               # queries only (0 = request)
dns.flags.response == 1               # responses only
dns.qry.name contains "example"

# --- TCP mechanics / troubleshooting ----------------------------------------
tcp.flags.syn == 1 && tcp.flags.ack == 0    # connection attempts (SYN only)
tcp.flags.reset == 1                        # RSTs (refused/closed)
tcp.analysis.retransmission                 # retransmits (loss/latency)
tcp.stream eq 3                             # everything in TCP stream #3

# --- Booleans & negation ----------------------------------------------------
http && ip.addr == 172.28.0.10        # AND (&& or 'and')
ftp || http                           # OR  (|| or 'or')
!(arp || dns)                         # NOT — hide noise
```

> **`contains` vs `matches`:** `tcp contains "password"` does a literal byte
> search; `frame matches "pass.*word"` applies a regex. `contains` is faster;
> `matches` is more powerful.

---

## 4. Following & reassembling streams `[Level 2+: Advanced / Field Ops]`

A single logical conversation (a login, a page load) is spread across many
packets. Wireshark reassembles them:

- **Right-click a packet → Follow → TCP Stream** (or HTTP/UDP/TLS Stream). This
  stitches both directions of the conversation into one readable transcript —
  the fastest way to see a cleartext login or an HTTP request/response pair.
- The dialog shows client bytes and server bytes in different colors; you can
  switch the "Show as" view to ASCII, Hex Dump, or Raw.
- Filtering to one stream: `tcp.stream eq N` (Wireshark fills in N when you
  follow a stream).

**Statistics** menu tools that pay off fast:

- **Statistics → Conversations** — every host/port pair, byte counts; find the
  loudest talkers.
- **Statistics → Protocol Hierarchy** — what protocols are present and in what
  proportion.
- **Statistics → Endpoints** — per-host totals, geolocation.

---

## 5. Extracting cleartext credentials (the lesson) `[Level 2+: Advanced / Field Ops]`

The point of these labs is to *viscerally* understand why unencrypted protocols
are indefensible. Using the Docker lab:

### HTTP form POST (web-target, 172.28.0.10)

1. Start capturing on the lab interface with display filter cleared.
2. Browse `http://127.0.0.1:8080/` (mapped to the web target) and submit the
   login form.
3. Apply: `http.request.method == "POST"`.
4. Select the POST → expand **HTML Form URL Encoded** in the detail pane, or
   **Follow → HTTP Stream**. The `username=admin&password=hunter2` body is right
   there in cleartext.

### FTP login (ftp-service, 172.28.0.20)

```bash
# Generate FTP auth traffic while capturing (cleartext USER/PASS on port 21)
ftp 127.0.0.1 2121        # or: curl ftp://labuser:labpass@127.0.0.1:2121/
```

Apply `ftp` and read the command stream directly:

```text
Request:  USER labuser
Response: 331 Please specify the password.
Request:  PASS labpass          <- the password, in the clear
Response: 230 Login successful.
```

### Telnet (concept)

Telnet transmits **every keystroke** in cleartext, including the password one
character at a time. `Follow → TCP Stream` on a telnet session reconstructs the
entire interactive session, credentials included — the historical reason SSH
replaced it.

### Exporting captured objects (files transferred over HTTP)

**File → Export Objects → HTTP** lists every file that crossed the wire over
HTTP (images, downloads, uploaded documents) and lets you save them to disk —
data exfiltration made visible.

---

## 6. Headless analysis with `tshark` `[Level 2+: Advanced / Field Ops]`

`tshark` is Wireshark's CLI. Essential for servers, scripting, and processing
capture files without a GUI — and the only realistic option under WSL2.

```bash
# List capture interfaces
tshark -D

# [Level 1: Intermediate] Live capture with a BPF capture filter, write to file
sudo tshark -i docker0 -f "tcp port 80 or tcp port 21" -w lab.pcapng

# Read a saved capture and apply a DISPLAY filter (-r read, -Y display filter)
tshark -r lab.pcapng -Y 'http.request.method == "POST"'

# Print only chosen fields (great for grep/CSV pipelines)
tshark -r lab.pcapng -Y ftp -T fields \
       -e frame.number -e ip.src -e ftp.request.command -e ftp.request.arg

# Extract HTTP POST bodies / form fields
tshark -r lab.pcapng -Y 'http.request.method=="POST"' \
       -T fields -e http.file_data

# One-liner credential sweep across a capture
tshark -r lab.pcapng -Y 'ftp.request.command=="USER" || ftp.request.command=="PASS"' \
       -T fields -e ftp.request.command -e ftp.request.arg

# Protocol statistics without the GUI
tshark -r lab.pcapng -q -z io,phs           # protocol hierarchy
tshark -r lab.pcapng -q -z conv,tcp         # TCP conversations
tshark -r lab.pcapng -q -z endpoints,ip     # per-IP endpoint totals

# Follow a specific TCP stream from the CLI
tshark -r lab.pcapng -q -z follow,tcp,ascii,3
```

Expected field-extraction output:

```text
5    172.28.0.5   USER   labuser
9    172.28.0.5   PASS   labpass
```

`dumpcap` is the lightweight capture-only tool Wireshark/tshark use under the
hood; for long unattended captures with ring buffers use it directly:

```bash
sudo dumpcap -i docker0 -b filesize:100000 -b files:10 -w rolling.pcapng
```

---

## Defensive counter-measures (blue-team lens)

Every extraction above has a one-line fix:

- **Encrypt everything in transit.** HTTPS (TLS) instead of HTTP; **FTPS/SFTP**
  instead of FTP; **SSH** instead of Telnet. TLS turns the credential-in-the-
  clear labs into undecryptable ciphertext for a passive sniffer.
- **HSTS** to prevent HTTP downgrade; disable plaintext protocol fallbacks.
- **Network segmentation + port security** so an attacker can't easily get a
  mirror/tap position; **802.1X** to authenticate devices onto the LAN.
- **Detection:** an IDS (Suricata/Zeek) watching for cleartext credentials,
  unexpected plaintext protocols, or a NIC entering promiscuous mode
  (`ip link` shows `PROMISC`) is your sensor.
- Remember: even with TLS, **metadata** (who talks to whom, when, how much)
  leaks — the Statistics tools above still reveal conversation patterns.

---

## Common troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No interfaces listed / permission denied | Missing capture privileges | `sudo dpkg-reconfigure wireshark-common`; add self to `wireshark` group |
| Capture is empty | Wrong interface, or switched network isolates you | Pick the lab interface (`docker0`/`br-pentestlab`); confirm with `tshark -D` |
| See only your own traffic | Switched LAN (no port mirror) | Use the Docker lab, a hub/tap, or SPAN port |
| HTTPS payloads unreadable | TLS encryption (working as intended) | Need server key or `SSLKEYLOGFILE`; passive decrypt is otherwise impossible |
| "capture filter syntax error" | Used a *display* filter in the capture box | Capture box = BPF (`tcp port 80`); display bar = `http.request` |
| tshark: "couldn't run dumpcap" | Privilege/group issue | Run under `sudo` or fix the `wireshark`/setcap permissions |
| Huge file, Wireshark sluggish | Captured everything | Use a capture (BPF) filter next time; or slice with `editcap` |

---

➡️ A cross-referenced table of use-cases → exact filters is in
**[filter-cheatsheet.md](filter-cheatsheet.md)**.
