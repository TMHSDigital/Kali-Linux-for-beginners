# Wireshark / tshark Filter Cheat Sheet

Cross-referenced tables mapping **what you want to do** → the **exact filter**.
Remember the golden rule: **capture filters use BPF/tcpdump syntax** (applied
before capture), **display filters use `protocol.field` syntax** (applied
after). They are not interchangeable.

---

## 1. Capture filters (BPF) — applied before capture

| Use case | Capture filter (BPF) |
|----------|----------------------|
| Only one host | `host 172.28.0.10` |
| Only one subnet | `net 172.28.0.0/16` |
| Traffic from a source | `src host 172.28.0.10` |
| Traffic to a destination | `dst host 172.28.0.20` |
| One TCP port | `tcp port 80` |
| Two ports (either) | `tcp port 80 or tcp port 21` |
| Everything except SSH (avoid capturing your own admin session) | `not port 22` |
| One MAC address | `ether host aa:bb:cc:11:22:33` |
| Only broadcast/multicast | `broadcast or multicast` |
| HTTP + FTP for the lab web/ftp targets | `host 172.28.0.10 and tcp port 80 or host 172.28.0.20 and tcp port 21` |
| VLAN-tagged traffic | `vlan` |
| ICMP only (ping troubleshooting) | `icmp` |

CLI usage: `tshark -i docker0 -f "tcp port 80 or tcp port 21" -w out.pcapng`

---

## 2. Display filters — addressing & transport

| Use case | Display filter |
|----------|----------------|
| To or from a host | `ip.addr == 172.28.0.10` |
| Sourced from a host | `ip.src == 172.28.0.10` |
| Destined to a host | `ip.dst == 172.28.0.20` |
| A whole subnet | `ip.addr == 172.28.0.0/16` |
| A specific TCP port (either side) | `tcp.port == 21` |
| Host **and** port together | `ip.addr == 172.28.0.10 && tcp.port == 80` |
| A UDP port | `udp.port == 53` |
| One TCP conversation | `tcp.stream eq 3` |
| Connection attempts (SYN, no ACK) | `tcp.flags.syn == 1 && tcp.flags.ack == 0` |
| Connection refused/closed (RST) | `tcp.flags.reset == 1` |
| Retransmissions (loss/latency) | `tcp.analysis.retransmission` |
| Zero-window (receiver stalled) | `tcp.analysis.zero_window` |
| Exclude ARP + DNS noise | `!(arp || dns)` |

---

## 3. Display filters — HTTP

| Use case | Display filter |
|----------|----------------|
| All HTTP | `http` |
| Requests only | `http.request` |
| Responses only | `http.response` |
| **POST requests (form credentials live here)** | `http.request.method == "POST"` |
| GET requests | `http.request.method == "GET"` |
| A specific status code | `http.response.code == 200` |
| Server errors | `http.response.code >= 500` |
| By Host header | `http.host == "acme.lab"` / `http.host contains "acme"` |
| By URI | `http.request.uri contains "login"` |
| **HTTP Basic-Auth header (base64, trivially decoded)** | `http.authorization` |
| Requests with a form body | `http.request.method == "POST" && http.content_type contains "urlencoded"` |
| User-Agent match | `http.user_agent contains "curl"` |

---

## 4. Display filters — credential & cleartext hunting

| Use case | Display filter |
|----------|----------------|
| Any packet containing the literal word "password" | `tcp contains "password"` |
| Login verbs (FTP/POP/IMAP/SMTP) | `tcp contains "USER" || tcp contains "PASS"` |
| **FTP username** | `ftp.request.command == "USER"` |
| **FTP password (cleartext!)** | `ftp.request.command == "PASS"` |
| All FTP control + data | `ftp || ftp-data` |
| Telnet session (every keystroke cleartext) | `telnet` |
| POP3 auth | `pop.request.command == "USER" || pop.request.command == "PASS"` |
| IMAP login | `imap contains "LOGIN"` |
| SMTP auth exchange | `smtp.req.command == "AUTH"` |
| Regex across payload | `frame matches "(?i)pass.?word"` |

---

## 5. Display filters — DNS

| Use case | Display filter |
|----------|----------------|
| All DNS | `dns` |
| Queries only | `dns.flags.response == 0` |
| Responses only | `dns.flags.response == 1` |
| A specific queried name | `dns.qry.name == "example.com"` |
| Partial name match | `dns.qry.name contains "example"` |
| Only A-record queries | `dns.qry.type == 1` |
| Failed lookups (NXDOMAIN) | `dns.flags.rcode == 3` |
| Suspiciously long labels (possible tunneling) | `dns.qry.name.len > 40` |

---

## 6. Display filters — TLS / HTTPS (metadata even when encrypted)

| Use case | Display filter |
|----------|----------------|
| All TLS | `tls` |
| Client Hello (reveals SNI hostname) | `tls.handshake.type == 1` |
| Server Hello | `tls.handshake.type == 2` |
| SNI (which site, even over HTTPS) | `tls.handshake.extensions_server_name` |
| Certificate messages | `tls.handshake.type == 11` |
| Old/weak protocol versions | `tls.record.version == 0x0301` (TLS 1.0) |

---

## 7. Display filters — 802.11 / wireless (module 04 captures)

| Use case | Display filter |
|----------|----------------|
| Beacon frames (APs announcing themselves) | `wlan.fc.type_subtype == 0x08` |
| Probe requests (clients searching) | `wlan.fc.type_subtype == 0x04` |
| **Deauthentication frames (the aireplay attack)** | `wlan.fc.type_subtype == 0x0c` |
| **EAPOL / 4-way handshake** | `eapol` |
| Traffic for one AP (BSSID) | `wlan.bssid == aa:bb:cc:11:22:33` |
| A specific SSID | `wlan.ssid == "MyLabAP"` |
| Management frames only | `wlan.fc.type == 0` |
| Data frames only | `wlan.fc.type == 2` |

---

## 8. tshark equivalents (headless)

| Task | Command |
|------|---------|
| List interfaces | `tshark -D` |
| Capture with BPF, save | `sudo tshark -i docker0 -f "tcp port 21" -w ftp.pcapng` |
| Read + apply display filter | `tshark -r ftp.pcapng -Y 'ftp'` |
| Print chosen fields | `tshark -r ftp.pcapng -Y ftp -T fields -e ftp.request.command -e ftp.request.arg` |
| Extract HTTP POST bodies | `tshark -r c.pcapng -Y 'http.request.method=="POST"' -T fields -e http.file_data` |
| Protocol hierarchy stats | `tshark -r c.pcapng -q -z io,phs` |
| TCP conversations | `tshark -r c.pcapng -q -z conv,tcp` |
| Follow a TCP stream (ASCII) | `tshark -r c.pcapng -q -z follow,tcp,ascii,0` |
| Count packets matching a filter | `tshark -r c.pcapng -Y 'http' \| wc -l` |
| Slice a big capture by time | `editcap -A "2026-09-05 12:00:00" -B "2026-09-05 12:05:00" big.pcapng slice.pcapng` |

---

## 9. Operator quick reference (display-filter language)

| Operator | Meaning | Example |
|----------|---------|---------|
| `==` / `eq` | equal | `tcp.port == 80` |
| `!=` / `ne` | not equal | `ip.src != 172.28.0.5` |
| `>` `<` `>=` `<=` | comparison | `http.response.code >= 400` |
| `&&` / `and` | logical AND | `http && ip.addr == 172.28.0.10` |
| `\|\|` / `or` | logical OR | `ftp || http` |
| `!` / `not` | negation | `!arp` |
| `contains` | literal byte substring | `tcp contains "PASS"` |
| `matches` / `~` | regex (PCRE) | `frame matches "(?i)pass"` |
| `in` | set membership | `tcp.port in {80 443 8080}` |

---

### Colour-coding tip

In the Wireshark GUI, **View → Coloring Rules** lets you flag anything a filter
can match — e.g. turn every `http.request.method == "POST"` or
`ftp.request.command == "PASS"` packet bright red so credentials jump out of a
busy capture without retyping the filter.
