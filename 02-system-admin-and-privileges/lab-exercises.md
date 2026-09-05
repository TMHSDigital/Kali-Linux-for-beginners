# Lab Exercises — System Administration & Privileges

These exercises create throwaway users, groups, and files, then walk through
permission changes, a simulated SUID privilege-escalation audit, and service
management. **Run them on a disposable Kali VM**, not a machine you care about.
A cleanup section at the end removes everything.

> You'll need `sudo`. Confirm first:
>
> ```bash
> sudo -v && echo "sudo OK"
> ```

---

## Exercise 1 — Read the account files

**Goal:** Locate your own line in `/etc/passwd` and confirm `/etc/shadow` is a
privilege boundary.

```bash
grep "^$(whoami):" /etc/passwd
sudo grep "^$(whoami):" /etc/shadow      # works with sudo
cat /etc/shadow                          # Permission denied — expected
```

**Self-grade:**

```bash
if cat /etc/shadow >/dev/null 2>&1; then
  echo "FAIL: /etc/shadow is readable by you — that's a misconfiguration!"
else
  echo "PASS: /etc/shadow is protected from non-root users"
fi
```

---

## Exercise 2 — Create a user and group

**Goal:** Create user `analyst` with a home dir and bash shell, plus a
`pentesters` group, and put `analyst` in it.

```bash
sudo groupadd pentesters
sudo useradd -m -s /bin/bash analyst
echo 'analyst:Lab-Passw0rd!' | sudo chpasswd    # scriptable password set
sudo usermod -aG pentesters analyst
id analyst
```

**Self-grade:**

```bash
id analyst | grep -q "pentesters" && \
[ -d /home/analyst ] && \
echo PASS || echo "FAIL: check user creation / group / home dir"
```

---

## Exercise 3 — The `-aG` trap

**Goal:** Understand why `usermod -G` without `-a` is dangerous — *do this
safely by observing, not by breaking your own account.*

```bash
# analyst is currently in: analyst, pentesters
id analyst
# Add to 'sudo' the CORRECT way (append):
sudo usermod -aG sudo analyst
id analyst
# Observe: analyst is now in analyst, pentesters, AND sudo.
# If we had run 'usermod -G sudo analyst' (no -a), analyst would be in ONLY
# sudo — silently removed from pentesters. Never omit -a.
```

**Self-grade:**

```bash
groups analyst | grep -q pentesters && groups analyst | grep -q sudo \
  && echo "PASS: both groups retained (you used -aG)" \
  || echo "FAIL: analyst lost a group — did you forget -a?"
```

---

## Exercise 4 — Octal and symbolic permissions

**Goal:** Create files and set precise modes both ways.

```bash
cd /tmp
touch key.pem public.txt deploy.sh
chmod 600 key.pem          # rw-------
chmod 644 public.txt       # rw-r--r--
chmod +x deploy.sh         # add execute for all
ls -l key.pem public.txt deploy.sh
stat -c '%A %n' key.pem public.txt deploy.sh
```

**Self-grade:**

```bash
k=$(stat -c '%a' key.pem); p=$(stat -c '%a' public.txt)
[ "$k" = "600" ] && [ "$p" = "644" ] && echo PASS || echo "FAIL: modes are $k / $p"
```

---

## Exercise 5 — Ownership

**Goal:** Give a file to `analyst:pentesters`.

```bash
cd /tmp
sudo touch shared-report.txt
sudo chown analyst:pentesters shared-report.txt
ls -l shared-report.txt
```

**Self-grade:**

```bash
owner=$(stat -c '%U:%G' shared-report.txt)
[ "$owner" = "analyst:pentesters" ] && echo PASS || echo "FAIL: owner is $owner"
```

---

## Exercise 6 — SUID audit (privilege-escalation reconnaissance)

**Goal:** Enumerate SUID binaries and reason about which are dangerous.

```bash
# Baseline the SUID set (defenders do this on a clean box)
find / -perm -4000 -type f 2>/dev/null | tee /tmp/suid.list
wc -l /tmp/suid.list
# Expected legitimate entries include: passwd, sudo, su, mount, umount, chsh
grep -E "passwd|sudo|su$" /tmp/suid.list
```

**Self-grade:**

```bash
grep -q "/usr/bin/sudo" /tmp/suid.list \
  && echo "PASS: found expected SUID binaries — now compare against GTFOBins" \
  || echo "FAIL: sudo should be SUID; re-run the find"
```

**Think it through:** if `find`, `vim`, `nmap`, `bash`, or `cp` appeared as
SUID-root, an attacker could leverage it to become root. Look each one up on
[GTFOBins](https://gtfobins.github.io) to see the exact exploitation payload.

---

## Exercise 7 — Simulated privesc via a SUID binary (safe, self-contained)

**Goal:** *Demonstrate* the concept in a sandbox so you understand why SUID
misconfiguration is fatal. We make a harmless copy of `bash` SUID-root, show it
grants a root shell, then remove it immediately.

```bash
# Setup (as root): create a deliberately-vulnerable SUID bash copy
sudo cp /bin/bash /tmp/rootbash
sudo chmod 4755 /tmp/rootbash            # SUID + rwxr-xr-x
ls -l /tmp/rootbash                       # note the 's' in -rwsr-xr-x

# Exploit (as a NORMAL user): -p preserves the elevated privileges
/tmp/rootbash -p -c 'id'                  # prints uid=1000 ... euid=0(root)!
```

Expected:

```text
uid=1000(kali) gid=1000(kali) euid=0(root) egid=0(root) groups=...
```

The **euid=0(root)** proves you executed code as root from an unprivileged
account — exactly what an attacker wants.

**Self-grade:**

```bash
/tmp/rootbash -p -c 'id -u' 2>/dev/null | grep -q '^0$' \
  && echo "PASS: SUID bash yielded euid 0 — lesson learned" \
  || echo "FAIL: setup didn't take (check chmod 4755)"
```

**⚠️ Clean up this landmine immediately:**

```bash
sudo rm -f /tmp/rootbash
echo "Removed the SUID bash. Never leave one of these on a real system."
```

---

## Exercise 8 — sudoers enumeration

**Goal:** See what your accounts can do via sudo.

```bash
sudo -l                       # your rights
sudo -l -U analyst            # analyst's rights (run as root)
cat /etc/sudoers.d/* 2>/dev/null
```

**Self-grade (manual):** Confirm you can explain, in one sentence each, what the
run-as user, allowed hosts, and command list mean in any rule shown.

---

## Exercise 9 — Process management

**Goal:** Start a background process, find it, signal it politely, then force
it.

```bash
sleep 600 &                   # background a long sleep; note the [job] PID
jobs -l                       # list background jobs with PIDs
ps aux | grep "[s]leep 600"   # the [s] trick hides grep from its own results
PID=$(pgrep -f "sleep 600")
echo "sleep PID is $PID"
kill "$PID"                   # SIGTERM
```

**Self-grade:**

```bash
sleep 0.5
pgrep -f "sleep 600" >/dev/null && echo "FAIL: still running" || echo "PASS: process terminated"
```

---

## Exercise 10 — Service management with systemd

**Goal:** Query, start, and inspect a service. (Uses ssh; substitute any
installed service, or `sudo apt install openssh-server` first.)

```bash
systemctl status ssh --no-pager || true
sudo systemctl start ssh
systemctl is-active ssh
journalctl -u ssh --since "5 min ago" --no-pager | tail -n 5
```

**Self-grade:**

```bash
systemctl is-active ssh 2>/dev/null | grep -q "active" \
  && echo "PASS: ssh is active" \
  || echo "SKIP: ssh not installed or no systemd (WSL/container) — that's OK"
```

---

## Cleanup — remove everything this lab created

```bash
sudo userdel -r analyst 2>/dev/null
sudo groupdel pentesters 2>/dev/null
sudo rm -f /tmp/key.pem /tmp/public.txt /tmp/deploy.sh /tmp/shared-report.txt \
           /tmp/rootbash /tmp/suid.list
echo "Lab 02 artifacts removed."
```

---

### Scorecard

| # | Skill demonstrated |
|---|--------------------|
| 1 | Reading `/etc/passwd` / `/etc/shadow`; the privilege boundary |
| 2 | `useradd -m -s`, `groupadd`, `chpasswd`, `usermod -aG` |
| 3 | Why `-aG` (append) not `-G` (replace) |
| 4 | Octal + symbolic `chmod` |
| 5 | `chown user:group` |
| 6 | SUID enumeration + baselining |
| 7 | Concrete SUID privesc (and safe cleanup) |
| 8 | `sudo -l` sudoers enumeration |
| 9 | Background jobs, `pgrep`, `kill` |
| 10 | `systemctl` / `journalctl` |

All PASS/SKIP and you're ready for **[module 03 — Network Recon &
Nmap](../03-network-recon-and-nmap/)**.
