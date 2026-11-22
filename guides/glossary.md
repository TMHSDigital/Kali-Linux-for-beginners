# Glossary

Plain-English definitions of the terms used across the course, in alphabetical
order. Each entry links to the section that teaches it.

**4-way handshake.** The four EAPOL messages a WPA2 client and access point
exchange to prove they share the Wi-Fi password and derive fresh session keys.
Capturing it lets you test password guesses offline.
See [module 04](../04-wireless-security-aircrack/README.md#2-the-wpa2-4-way-handshake-the-crypto-youre-attacking).

**Anonymous FTP.** An FTP server setting that lets anyone log in without a
password, usually as `anonymous` or `ftp`. The lab's FTP target allows it on
purpose. See [module 03](../03-network-recon-and-nmap/README.md#6-output-formats-and-feeding-the-parser-level-1-intermediate).

**BPF (Berkeley Packet Filter).** The capture filter language used by tcpdump,
tshark `-f`, and Wireshark's capture dialog, for example `host 10.77.0.20 and
port 21`. It decides which packets are recorded at all.
See [module 05](../05-packet-analysis-wireshark/README.md#2-capture-filters-bpf-vs-display-filters-a-critical-distinction).

**BSSID.** The MAC address of a Wi-Fi access point's radio. Tools such as
airodump-ng use it to tell networks apart, even when two share a name.
See [module 04](../04-wireless-security-aircrack/README.md#4-step-2-discover-targets-with-airodump-ng).

**Capture filter.** A filter applied while capturing, written in BPF. Anything
it excludes is never saved. Compare *display filter*.
See [the filter cheatsheet](../05-packet-analysis-wireshark/filter-cheatsheet.md#1-capture-filters-bpf-applied-before-capture).

**Cleartext.** Data sent without encryption, so anyone who can see the traffic
can read it. HTTP, FTP, and Telnet send passwords in cleartext.
See [module 05](../05-packet-analysis-wireshark/README.md#5-extracting-cleartext-credentials-level-2-advanced).

**Deauthentication (deauth).** A Wi-Fi management frame that disconnects a
client. Sending forged ones forces a client to reconnect so its handshake can be
captured. Protected Management Frames block this.
See [module 04](../04-wireless-security-aircrack/README.md#5-step-3-force-a-handshake-with-aireplay-ng-deauth).

**Display filter.** A Wireshark or tshark `-Y` filter applied to packets already
captured, for example `ftp.request.command == "PASS"`. It hides packets from
view but does not delete them. See [module 05](../05-packet-analysis-wireshark/README.md#3-core-display-filters-your-daily-toolkit).

**Docker bridge gateway.** The `.1` address of a Docker network (`10.77.0.1` in
the lab). It is your own machine, or Docker Desktop's VM, not a lab target.
See [module 03](../03-network-recon-and-nmap/README.md#3-host-discovery-who-is-alive-level-1-intermediate).

**Filtered (port state).** Nmap got no answer, or an ICMP error, so a firewall is
probably dropping its probes. Nmap cannot tell whether the port is open.
See [module 03](../03-network-recon-and-nmap/README.md#firewall-drop-vs-reject).

**Group.** A named set of users that can share file permissions. Every file has
an owning user and an owning group.
See [module 02](../02-system-admin-and-privileges/README.md#5-user--group-management-level-1-intermediate).

**Host discovery.** Finding which addresses in a range have a live machine,
before scanning ports, for example with `nmap -sn`.
See [module 03](../03-network-recon-and-nmap/README.md#3-host-discovery-who-is-alive-level-1-intermediate).

**Managed mode.** The normal mode of a Wi-Fi card: connected to one network and
seeing only its own traffic. Compare *monitor mode*.
See [module 04](../04-wireless-security-aircrack/README.md#managed-vs-monitor-mode).

**Monitor mode.** A Wi-Fi card mode that records every frame on a channel,
including other people's, without joining a network. Needed to capture
handshakes. See [module 04](../04-wireless-security-aircrack/README.md#3-step-1-prepare-the-interface-monitor-mode).

**NSE (Nmap Scripting Engine).** Nmap's built-in scripts that go beyond port
state, such as `ftp-anon` or `http-title`. `-sC` runs the default set.
See [module 03](../03-network-recon-and-nmap/README.md#nmap-scripting-engine-nse).

**Octal permissions.** File permissions written as three digits, one each for
owner, group, and others, where read is 4, write is 2, and execute is 1. `755`
is `rwxr-xr-x`. See [module 02](../02-system-admin-and-privileges/README.md#octal-vs-symbolic).

**Pipe.** The `|` operator, which sends one command's output into the next
command's input, for example `ps aux | grep nginx`.
See [module 01](../01-terminal-and-linux-core/README.md#7-pipes-and-redirection-level-1-intermediate).

**PMF (Protected Management Frames, 802.11w).** A Wi-Fi feature that
authenticates management frames, so forged deauthentication frames are ignored.
Required by WPA3. See [module 04](../04-wireless-security-aircrack/README.md#protected-management-frames-80211w--pmf).

**PMKID.** A value some access points send in the first handshake message. It
can be cracked offline like a full handshake, with no client and no deauth.
See [module 04](../04-wireless-security-aircrack/README.md#pmkid-attack-clientless-when-supported).

**Port.** A number from 0 to 65535 that identifies a service on a host, such as
80 for HTTP or 21 for FTP. A port scan asks which ones answer.
See [module 03](../03-network-recon-and-nmap/README.md#1-how-scanning-works-tcpip-architecture).

**Redirection.** Sending a command's output to a file (`>` to overwrite, `>>` to
append, `2>` for errors) or reading input from one (`<`).
See [module 01](../01-terminal-and-linux-core/README.md#7-pipes-and-redirection-level-1-intermediate).

**Root.** The Linux superuser, user ID 0, which bypasses normal permission
checks. Its prompt ends in `#` instead of `$`.
See [module 02](../02-system-admin-and-privileges/README.md#1-the-unix-privilege-model-architecture).

**SAE (Simultaneous Authentication of Equals).** The WPA3 password handshake,
also called Dragonfly. Captured traffic does not allow offline guessing the way
a WPA2 handshake does. See [module 04](../04-wireless-security-aircrack/README.md#wpa3--sae-simultaneous-authentication-of-equals--dragonfly).

**Service and version detection.** Nmap's `-sV`, which talks to each open port
to identify the software and its version, for example `vsftpd` or `nginx`.
See [module 03](../03-network-recon-and-nmap/README.md#service--version-detection-os-fingerprinting).

**SGID.** A special permission bit. On a program, it runs with the file's group;
on a directory, new files inherit the directory's group.
See [module 02](../02-system-admin-and-privileges/README.md#8-special-bits-suid-sgid-and-sticky).

**Shell.** The program that reads your commands and runs them, usually bash or
zsh on Kali. See [module 01](../01-terminal-and-linux-core/README.md#1-how-the-shell-actually-works-architecture).

**Sticky bit.** A special permission bit on a directory, such as `/tmp`, that
lets users delete only their own files there.
See [module 02](../02-system-admin-and-privileges/README.md#8-special-bits-suid-sgid-and-sticky).

**sudo.** Runs a single command as another user, usually root, if
`/etc/sudoers` allows it, and logs that it happened.
See [module 02](../02-system-admin-and-privileges/README.md#3-becoming-another-user-su-and-sudo).

**SUID.** A special permission bit that makes a program run as the file's
owner, often root, whoever starts it. A SUID program with a flaw is a classic
privilege escalation path. See [module 02](../02-system-admin-and-privileges/README.md#8-special-bits-suid-sgid-and-sticky).

**SYN scan.** Nmap's `-sS`: it sends a TCP SYN and reads the reply, but never
completes the connection. Faster than a connect scan and needs root.
See [module 03](../03-network-recon-and-nmap/README.md#tcp-connect-vs-syn-stealth).

**systemd.** The service manager on most Linux systems, controlled with
`systemctl` (start, stop, enable services) and `journalctl` (logs).
See [module 02](../02-system-admin-and-privileges/README.md#10-services-with-systemd-level-1-intermediate).

**TCP three-way handshake.** SYN, SYN-ACK, ACK: how a TCP connection opens.
Port scans work by watching how hosts answer the first step.
See [module 03](../03-network-recon-and-nmap/README.md#1-how-scanning-works-tcpip-architecture).

**tshark.** The command-line version of Wireshark, for capturing and reading
packets without a GUI. See [module 05](../05-packet-analysis-wireshark/README.md#6-headless-analysis-with-tshark-level-2-advanced).

**UDP scan.** Nmap's `-sU`. UDP has no handshake, so scans are slow and many
ports show as `open|filtered`.
See [module 03](../03-network-recon-and-nmap/README.md#udp-scanning).

**WPA2-PSK.** Wi-Fi security based on one shared password. Anyone who captures a
handshake can guess passwords offline, so weak passwords fall quickly.
See [module 04](../04-wireless-security-aircrack/README.md#2-the-wpa2-4-way-handshake-the-crypto-youre-attacking).

**WPA3.** The newer Wi-Fi security standard. It replaces the PSK handshake with
SAE and requires PMF. See [module 04](../04-wireless-security-aircrack/README.md#7-modern-defense-why-this-attack-is-dying).
