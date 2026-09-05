# Wireless Hardware, Drivers & VM Passthrough

Monitor mode and packet injection are **hardware-dependent**. Most built-in
laptop Wi-Fi cards either can't do monitor mode or can't inject. This guide
covers which adapters work, how to install their drivers, and how to hand a USB
adapter to a Kali VM.

---

## 1. Supported chipsets (what to buy)

| Chipset | Representative adapters | Bands | Injection | Driver situation |
|---------|-------------------------|-------|-----------|------------------|
| **Atheros AR9271** | Alfa AWUS036NHA, TP-Link TL-WN722N **v1** | 2.4 GHz | Excellent | `ath9k_htc`: **in-kernel**, works out of the box. Best beginner choice. |
| **Realtek RTL8812AU** | Alfa AWUS036ACH / AWUS036AC | 2.4 + 5 GHz | Good | Out-of-tree `8812au` DKMS driver required |
| **Realtek RTL8811AU / RTL8821AU** | small dual-band dongles | 2.4 + 5 GHz | Good | Out-of-tree driver required |
| **Ralink RT3070 / RT5370** | older Alfa models | 2.4 GHz | Good | `rt2800usb` in-kernel |
| **MediaTek MT7612U** | Alfa AWUS036ACM | 2.4 + 5 GHz | Very good | `mt76` in-kernel (recent kernels) |

### Buying gotchas

- **TL-WN722N: only v1 has the AR9271.** v2/v3 switched to a Realtek chip
  (RTL8188EUS) with weaker monitor/injection support. Check the label.
- Realtek `8812au` performance depends heavily on driver + kernel version; the
  `aircrack-ng/rtl8812au` fork is the most reliable.
- 5 GHz monitor mode is fussier than 2.4 GHz across the board.

### Identify what you have

```bash
lsusb                              # USB adapters: look for Realtek/Atheros IDs
lspci | grep -i network            # built-in cards
iw list | grep -A8 "Supported interface modes"   # look for '* monitor'
airmon-ng                          # aircrack-ng's chipset/driver view
```

If `iw list` shows `* monitor` under "Supported interface modes", the card can
enter monitor mode. Injection is separately verified in section 4.

---

## 2. Installing the RTL8812AU driver (DKMS)

The most common "my Alfa AC dongle doesn't work" fix. DKMS rebuilds the module
automatically on kernel upgrades.

```bash
# [Level 1: Intermediate] Prerequisites + the maintained driver package
sudo apt update
sudo apt install -y realtek-rtl88xxau-dkms   # Kali's packaged driver (easiest)

# --- OR build the aircrack-ng fork from source (most up-to-date) -------------
sudo apt install -y build-essential dkms git bc \
                    linux-headers-$(uname -r)
git clone https://github.com/aircrack-ng/rtl8812au.git
cd rtl8812au
sudo make dkms_install        # registers with DKMS and builds for current kernel

# Reload and confirm
sudo modprobe 8812au
lsmod | grep 8812au
iw dev                        # your dual-band interface should now appear
```

Troubleshooting the build:

```bash
# "linux-headers not found": install the exact headers for your running kernel
sudo apt install -y linux-headers-$(uname -r)
uname -r                      # must match the installed headers version
# After a kernel upgrade, DKMS rebuilds automatically; verify with:
dkms status
```

> **Secure Boot** blocks unsigned out-of-tree modules. If `modprobe` fails with
> "Key was rejected by service", either disable Secure Boot in firmware or
> enroll a MOK key to sign the module.

---

## 3. AR9271 (the easy path)

Nothing to install on Kali, `ath9k_htc` is in the mainline kernel. It may need
firmware, which Kali ships:

```bash
sudo apt install -y firmware-atheros
sudo modprobe ath9k_htc
iw dev                       # wlanX appears
sudo airmon-ng start wlan0   # straight into monitor mode
```

This is why the AR9271 is the recommended first adapter: plug in, go.

---

## 4. Verifying monitor mode AND injection

Monitor mode (listening) and injection (transmitting) are separate
capabilities. Test both before relying on the card in module 04.

```bash
# Enable monitor mode
sudo airmon-ng check kill
sudo airmon-ng start wlan0            # creates wlan0mon
iw dev                                # confirm type 'monitor'

# Injection test, REQUIRES a nearby AP to respond; run near your own AP
sudo aireplay-ng --test wlan0mon
```

Expected injection-test success:

```text
Trying broadcast probe requests...
Injection is working!
Found 3 APs
...
30/30: 100%
```

If injection reports 0% or "no answer", the card can listen but not transmit:
capture will work but deauth/PMKID attacks won't.

---

## 5. Setting channel / band manually

Sometimes you need to pin the radio yourself (e.g. `airmon-ng` picked the wrong
channel):

```bash
sudo iw dev wlan0mon set channel 6            # 2.4 GHz channel 6
sudo iw dev wlan0mon set channel 36           # 5 GHz channel 36
sudo iw dev wlan0mon set freq 2437            # by frequency (MHz) instead
iw dev wlan0mon info                          # confirm current channel/freq
```

Regulatory domain can lock out channels (especially 5 GHz / higher power):

```bash
iw reg get                                    # current regulatory domain
sudo iw reg set US                            # set to your legal country code
```

---

## 6. VirtualBox: USB passthrough

Monitor mode from a VM works only if the *USB adapter* is passed through
(virtual NICs can't do RFMON).

1. Install the **VirtualBox Extension Pack** (matching your VBox version), this
   provides USB 2.0/3.0 support.
2. Add your user to the `vboxusers` group so the host lets the VM grab USB:
   ```bash
   sudo usermod -aG vboxusers "$USER"     # then log out/in
   ```
3. VM **Settings → USB**: choose the USB 3.0 (xHCI) controller.
4. Click the **add-filter** icon and pick your adapter (e.g. "ATHEROS
   AR9271") so it auto-attaches whenever the VM boots.
5. Boot Kali. With the dongle plugged in, `lsusb` inside the VM should list it,
   and `airmon-ng` should see the chipset.

If it doesn't appear: `Devices → USB → <your adapter>` in the running VM's
menu to attach it live. Unplug/replug the physical adapter if the host claimed
it first.

---

## 7. VMware Workstation / Fusion: USB passthrough

VMware is generally the smoother option for Realtek AC dongles.

1. Ensure the VMware USB Arbitration Service is running (installed by default).
2. VM **Settings → USB Controller**: set compatibility to **USB 3.1**, and
   enable "Show all USB input devices".
3. Boot Kali, plug in the adapter, then **VM → Removable Devices → <adapter> →
   Connect (Disconnect from Host)**. This detaches it from the host OS and pins
   it to the guest.
4. Verify inside the guest with `lsusb` and `airmon-ng`.

> On both hypervisors: if the **host OS** (Windows/macOS) grabs the adapter for
> its own Wi-Fi, the guest can't use it. Passthrough gives the VM exclusive
> control, expect to lose that adapter on the host while the VM holds it.

---

## 8. WSL2: the honest limitation

WSL2 runs a real Linux kernel but has **no native raw 802.11 access**. Even with
`usbipd-win` to forward a USB device into WSL2, the WSL2 kernel usually lacks
the wireless drivers (`ath9k_htc`, `8812au`) and `cfg80211`/`mac80211` monitor
support, so monitor mode typically fails.

```powershell
# On Windows (admin PowerShell), forward a USB device to WSL2 (best-effort):
winget install usbipd
usbipd list                       # find the BUSID of your adapter
usbipd bind   --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

```bash
# Inside WSL2:
lsusb                             # may show the device...
iw list                          # ...but often no 'monitor' mode / no driver
```

**Recommendation:** use WSL2 for modules 01-03 and 05 (analyzing saved `.cap`
files with `tshark`), and use bare-metal Kali or a full VM with USB passthrough
for the live wireless work in module 04.

---

## 9. Restoring normal networking when you're done

```bash
sudo airmon-ng stop wlan0mon
sudo systemctl start NetworkManager      # or: sudo systemctl restart NetworkManager
nmcli device status                       # confirm the card is 'connected' again
```

---

## Quick decision guide

- **Just starting / want zero hassle** → Atheros **AR9271** (Alfa AWUS036NHA).
- **Need 5 GHz** → **RTL8812AU** (Alfa AWUS036ACH) + DKMS driver, or MT7612U.
- **Running in a VM** → VMware + USB passthrough is the most reliable combo.
- **On WSL2** → do offline capture analysis only; get real hardware for live RF.
