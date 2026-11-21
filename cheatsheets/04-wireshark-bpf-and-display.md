# Wireshark BPF & Display Filter Cheat Sheet

Condensed reference for module 05. **Two languages:** capture filters (BPF,
before capture) and display filters (`protocol.field`, after capture). Never mix
them.

---

## Capture filters (BPF): before capture (`-f` in tshark)

| Filter | Matches |
|--------|---------|
| `host 10.77.0.10` | To/from a host |
| `src host X` / `dst host X` | Source / destination host |
| `net 10.77.0.0/24` | A subnet |
| `port 80` / `tcp port 80` | A port / TCP port |
| `portrange 1-1024` | Port range |
| `tcp port 80 or tcp port 21` | Either |
| `not port 22` | Exclude (protect your SSH) |
| `ether host aa:bb:cc:11:22:33` | A MAC |
| `broadcast or multicast` | Broadcast/multicast |
| `icmp` / `arp` / `udp` | Protocol |
| `vlan` / `vlan 100` | VLAN-tagged |
| `tcp[tcpflags] & tcp-syn != 0` | SYN packets |

## Display filters: addressing / transport

| Filter | Matches |
|--------|---------|
| `ip.addr == X` | To/from host |
| `ip.src == X` / `ip.dst == X` | Source / dest |
| `ip.addr == 10.77.0.0/24` | Subnet |
| `tcp.port == 21` / `udp.port == 53` | Port |
| `ip.addr==X && tcp.port==Y` | Host + port |
| `tcp.stream eq N` | One conversation |
| `tcp.flags.syn==1 && tcp.flags.ack==0` | Connection attempts |
| `tcp.flags.reset==1` | Resets |
| `tcp.analysis.retransmission` | Retransmits |
| `tcp.analysis.zero_window` | Receiver stalled |
| `frame.len > 1000` | Large frames |
| `!(arp or dns)` | Hide noise |

## Display filters: HTTP

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

## Display filters: credentials / cleartext

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

## Display filters: DNS

| Filter | Matches |
|--------|---------|
| `dns` | All DNS |
| `dns.flags.response == 0` | Queries |
| `dns.flags.response == 1` | Responses |
| `dns.qry.name contains "example"` | Name match |
| `dns.qry.type == 1` | A-record queries |
| `dns.flags.rcode == 3` | NXDOMAIN |
| `dns.qry.name.len > 40` | Possible tunneling |

## Display filters: TLS / HTTPS

| Filter | Matches |
|--------|---------|
| `tls` | All TLS |
| `tls.handshake.type == 1` | Client Hello (SNI) |
| `tls.handshake.type == 2` | Server Hello |
| `tls.handshake.extensions_server_name` | SNI hostname |
| `tls.handshake.type == 11` | Certificate |
| `tls.record.version == 0x0301` | TLS 1.0 (weak) |

## Display filters: 802.11 (wireless captures)

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
| `contains` | n/a | `tcp contains "PASS"` |
| `matches` | `~` | `frame matches "pass"` |
| `in` | n/a | `tcp.port in {80 443}` |

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

## Try it in the lab `[Level 1: Intermediate]`

Run these from the attacker shell (`./scripts/setup-lab-env.sh shell`). They
capture the lab's own cleartext logins, the same traffic module 05 uses, then
read the file back with display filters. Only capture traffic on the lab
network (`10.77.0.0/24`).

```bash
cd /tmp
# Capture filter (BPF): only the FTP control channel to the FTP target.
tshark -i eth0 -f "host 10.77.0.20 and port 21" -w ftp.pcapng &
sleep 2                                    # give tshark time to open eth0
curl -s ftp://labuser:labpass@10.77.0.20/ >/dev/null
sleep 1; kill %1                           # flush, then stop the capture

# Same idea for the web target's login form.
tshark -i eth0 -f "host 10.77.0.10 and tcp port 80" -w web.pcapng &
sleep 2
curl -s -o /dev/null -d 'username=admin&password=hunter2' http://10.77.0.10/login
sleep 1; kill %1
```

Display filter: the FTP login commands.

```bash
tshark -r ftp.pcapng -Y 'ftp.request.command == "USER" || ftp.request.command == "PASS"'
```

```text
    6 0.000907523    10.77.0.5 → 10.77.0.20   FTP 80 Request: USER labuser
    9 0.000984096    10.77.0.5 → 10.77.0.20   FTP 80 Request: PASS labpass
```

Pull just the fields you want with `-T fields` (one line per matching packet):

```bash
tshark -r ftp.pcapng -Y 'ftp.request.command == "PASS"' -T fields -e ip.src -e ip.dst -e ftp.request.arg
```

```text
10.77.0.5	10.77.0.20	labpass
```

Display filter: the HTTP form POST, then the form fields inside it.

```bash
tshark -r web.pcapng -Y 'http.request.method == "POST"'
tshark -r web.pcapng -Y 'urlencoded-form' -T fields -e urlencoded-form.key -e urlencoded-form.value
```

```text
    4 0.000158516    10.77.0.5 → 10.77.0.10   HTTP 246 POST /login HTTP/1.1  (application/x-www-form-urlencoded)
username,password	admin,hunter2
```

Statistics without the GUI: who talked to whom (`-q` hides the packet list).

```bash
tshark -r ftp.pcapng -q -z conv,tcp
```

```text
================================================================================
TCP Conversations
Filter:<No Filter>
                                                           |       <-      | |       ->      | |     Total     |    Relative    |   Duration   |
                                                           | Frames  Bytes | | Frames  Bytes | | Frames  Bytes |      Start     |              |
10.77.0.5:45628            <-> 10.77.0.20:21                   15 1293 bytes      12 859 bytes      27 2152 bytes     0.000000000         0.0516
================================================================================
```

Defensive note: every password above was readable by anyone on the path. The
fix is the table above: replace FTP and HTTP with SFTP and HTTPS, and a capture
of the same login shows only encrypted TLS or SSH records.
