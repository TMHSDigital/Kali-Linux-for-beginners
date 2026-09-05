# Wireshark BPF & Display Filter Cheat Sheet

Condensed reference for module 05. **Two languages:** capture filters (BPF,
before capture) and display filters (`protocol.field`, after capture). Never mix
them.

---

## Capture filters (BPF) — before capture (`-f` in tshark)

| Filter | Matches |
|--------|---------|
| `host 172.28.0.10` | To/from a host |
| `src host X` / `dst host X` | Source / destination host |
| `net 172.28.0.0/16` | A subnet |
| `port 80` / `tcp port 80` | A port / TCP port |
| `portrange 1-1024` | Port range |
| `tcp port 80 or tcp port 21` | Either |
| `not port 22` | Exclude (protect your SSH) |
| `ether host aa:bb:cc:11:22:33` | A MAC |
| `broadcast or multicast` | Broadcast/multicast |
| `icmp` / `arp` / `udp` | Protocol |
| `vlan` / `vlan 100` | VLAN-tagged |
| `tcp[tcpflags] & tcp-syn != 0` | SYN packets |

## Display filters — addressing / transport

| Filter | Matches |
|--------|---------|
| `ip.addr == X` | To/from host |
| `ip.src == X` / `ip.dst == X` | Source / dest |
| `ip.addr == 172.28.0.0/16` | Subnet |
| `tcp.port == 21` / `udp.port == 53` | Port |
| `ip.addr==X && tcp.port==Y` | Host + port |
| `tcp.stream eq N` | One conversation |
| `tcp.flags.syn==1 && tcp.flags.ack==0` | Connection attempts |
| `tcp.flags.reset==1` | Resets |
| `tcp.analysis.retransmission` | Retransmits |
| `tcp.analysis.zero_window` | Receiver stalled |
| `frame.len > 1000` | Large frames |
| `!(arp or dns)` | Hide noise |

## Display filters — HTTP

| Filter | Matches |
|--------|---------|
| `http` | All HTTP |
| `http.request` / `http.response` | Requests / responses |
| `http.request.method == "POST"` | POSTs (form creds) |
| `http.request.method == "GET"` | GETs |
| `http.response.code == 200` | Status code |
| `http.response.code >= 500` | Server errors |
| `http.host contains "acme"` | By host |
| `http.request.uri contains "login"` | By URI |
| `http.authorization` | Basic-Auth header (base64) |
| `http.user_agent contains "curl"` | By UA |
| `http.file_data` | Body/payload present |

## Display filters — credentials / cleartext

| Filter | Matches |
|--------|---------|
| `tcp contains "password"` | Literal byte search |
| `ftp.request.command == "USER"` | FTP username |
| `ftp.request.command == "PASS"` | FTP password (cleartext) |
| `ftp \|\| ftp-data` | All FTP |
| `telnet` | Telnet (keystrokes cleartext) |
| `pop.request.command == "PASS"` | POP3 password |
| `imap contains "LOGIN"` | IMAP login |
| `smtp.req.command == "AUTH"` | SMTP auth |
| `frame matches "(?i)pass.?word"` | Regex payload |

## Display filters — DNS

| Filter | Matches |
|--------|---------|
| `dns` | All DNS |
| `dns.flags.response == 0` | Queries |
| `dns.flags.response == 1` | Responses |
| `dns.qry.name contains "example"` | Name match |
| `dns.qry.type == 1` | A-record queries |
| `dns.flags.rcode == 3` | NXDOMAIN |
| `dns.qry.name.len > 40` | Possible tunneling |

## Display filters — TLS / HTTPS

| Filter | Matches |
|--------|---------|
| `tls` | All TLS |
| `tls.handshake.type == 1` | Client Hello (SNI) |
| `tls.handshake.type == 2` | Server Hello |
| `tls.handshake.extensions_server_name` | SNI hostname |
| `tls.handshake.type == 11` | Certificate |
| `tls.record.version == 0x0301` | TLS 1.0 (weak) |

## Display filters — 802.11 (wireless captures)

| Filter | Matches |
|--------|---------|
| `wlan.fc.type_subtype == 0x08` | Beacons |
| `wlan.fc.type_subtype == 0x04` | Probe requests |
| `wlan.fc.type_subtype == 0x0c` | Deauth frames |
| `eapol` | 4-way handshake |
| `wlan.bssid == aa:bb:cc:11:22:33` | One AP |
| `wlan.ssid == "MyLabAP"` | One SSID |
| `wlan.fc.type == 0/1/2` | Mgmt / Control / Data |

## Operators (display language)

| Op | Alias | Example |
|----|-------|---------|
| `==` | `eq` | `tcp.port == 80` |
| `!=` | `ne` | `ip.src != X` |
| `> < >= <=` | `gt lt ge le` | `http.response.code >= 400` |
| `&&` | `and` | `http && ip.addr==X` |
| `\|\|` | `or` | `ftp \|\| http` |
| `!` | `not` | `!arp` |
| `contains` | — | `tcp contains "PASS"` |
| `matches` | `~` | `frame matches "pass"` |
| `in` | — | `tcp.port in {80 443}` |

## tshark essentials

| Command | Action |
|---------|--------|
| `tshark -D` | List interfaces |
| `tshark -i eth0 -f "tcp port 80" -w out.pcapng` | Capture w/ BPF to file |
| `tshark -r f.pcapng -Y 'http.request'` | Read + display filter |
| `tshark -r f -Y ftp -T fields -e ftp.request.command -e ftp.request.arg` | Field extract |
| `tshark -r f -q -z io,phs` | Protocol hierarchy |
| `tshark -r f -q -z conv,tcp` | TCP conversations |
| `tshark -r f -q -z follow,tcp,ascii,0` | Follow stream #0 |
| `editcap -A START -B END big small` | Time-slice a capture |
| `mergecap -w all.pcapng a.pcapng b.pcapng` | Merge captures |
| `dumpcap -i eth0 -b filesize:100000 -b files:10 -w ring.pcapng` | Ring-buffer capture |

## GUI power moves

| Action | Where |
|--------|-------|
| Follow a conversation | Right-click → Follow → TCP/HTTP/TLS Stream |
| Extract transferred files | File → Export Objects → HTTP/FTP-DATA/SMB |
| Talkers by volume | Statistics → Conversations |
| Protocol breakdown | Statistics → Protocol Hierarchy |
| Highlight creds automatically | View → Coloring Rules (`ftp.request.command=="PASS"`) |
| Decode a port as a protocol | Right-click → Decode As |

## Defensive one-liners (the fix for every cleartext lab)

| Cleartext protocol | Encrypted replacement |
|--------------------|----------------------|
| HTTP | HTTPS/TLS (+ HSTS) |
| FTP | FTPS / SFTP (over SSH) |
| Telnet | SSH |
| POP3/IMAP/SMTP plain | +STARTTLS / implicit TLS |
