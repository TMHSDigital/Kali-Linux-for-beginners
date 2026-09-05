# 02: System Administration & Privileges `[Level 1: Administration]`

Privilege determines what every process on a system is allowed to do. Most
attack chains end in the same place: turning the access you have into more
access than you should have. To exploit or defend that, you need to understand
how Linux models identity, permissions, and processes. This module covers that
model and how to audit it.

---

## 1. The Unix privilege model (architecture)

Every process on Linux runs as a **user** (UID) and one or more **groups**
(GIDs). The kernel checks those IDs against a file's owner/group/mode bits on
every access. There is exactly one all-powerful account:

- **root**: UID **0**. The kernel skips most permission checks for UID 0. Root
  can read/write any file, bind low ports, load kernel modules, and become any
  other user. This is why every privilege-escalation exploit is ultimately
  "become UID 0."

Regular users (UID ≥ 1000 for humans on Debian/Kali; 1-999 for system service
accounts) are constrained to what their UID/GID permits.

```bash
# [Level 0: Fundamental] Inspect your own identity
id                       # uid, gid, and all supplementary groups
id root                  # inspect another account
whoami                   # current effective username
groups                   # just the group names you belong to
```

Expected:

```text
uid=1000(kali) gid=1000(kali) groups=1000(kali),27(sudo),...
```

Membership in **`sudo`** (group 27 on Debian/Kali) is what lets `kali` escalate.
Note that for later.

---

## 2. `/etc/passwd` and `/etc/shadow` (where accounts live)

**`/etc/passwd`** is the world-readable account registry. One line per account:

```text
kali:x:1000:1000:Kali,,,:/home/kali:/bin/bash
 │   │  │    │     │        │          └ login shell (/usr/sbin/nologin = can't log in)
 │   │  │    │     │        └ home directory
 │   │  │    │     └ GECOS (full name / comment)
 │   │  │    └ primary GID
 │   │  └ UID
 │   └ password field: 'x' means "see /etc/shadow"
 └ username
```

**`/etc/shadow`** is root-readable **only** and holds the hashed passwords:

```text
kali:$y$j9T$...hash...:19600:0:99999:7:::
 │    │                 │
 │    │                 └ days since epoch of last password change
 │    └ hashed password ($y$ = yescrypt, $6$ = SHA-512, ! or * = locked)
 └ username
```

```bash
# [Level 0: Fundamental] Read the account registry (anyone can)
cat /etc/passwd
grep "bash" /etc/passwd          # accounts with an interactive shell

# [Level 1: Intermediate] Shadow requires root; this is a privilege boundary
sudo cat /etc/shadow             # works
cat /etc/shadow                  # -> Permission denied (that's the point)
```

> **Why this matters offensively:** if a misconfiguration makes `/etc/shadow`
> readable (or writable), an attacker can crack or replace the root hash.
> Defenders should check its mode regularly (it should be `640 root:shadow`).

---

## 3. Becoming another user: `su` and `sudo`

Two different mechanisms, often confused:

```bash
# [Level 1: Intermediate] su: switch user (needs the TARGET's password)
su -                 # become root; prompts for ROOT's password, loads root's env
su - kali            # become 'kali'; the trailing '-' gives a full login shell
exit                 # drop back to your previous identity

# [Level 1: Intermediate] sudo: run ONE command as root (needs YOUR password)
sudo apt update              # run a single command as root
sudo -i                      # interactive root shell (like 'su -' but via sudo)
sudo -u www-data whoami      # run as a DIFFERENT non-root user
sudo -l                      # list what YOU are allowed to run via sudo
```

Key distinction:

| | `su -` | `sudo` |
|-|--------|--------|
| Password prompted | the **target** account's | **your own** |
| Scope | opens a full shell | typically one command |
| Auditing | weak | every invocation logged to `/var/log/auth.log` |
| Best practice | avoid sharing root's password | preferred: accountable & granular |

---

## 4. `/etc/sudoers`: who may run what as whom

`sudo` is governed by `/etc/sudoers` (and drop-ins in `/etc/sudoers.d/`).
**Always** edit it with `visudo`, which syntax-checks before saving. A broken
sudoers file can lock everyone out of root.

```bash
# [Level 1: Intermediate] Safely edit the policy
sudo visudo                       # main file
sudo visudo -f /etc/sudoers.d/lab # a drop-in fragment
```

Anatomy of a sudoers rule:

```text
kali    ALL=(ALL:ALL)   ALL
 │       │   │    │       └ commands allowed (ALL = anything)
 │       │   │    └ groups the user may target
 │       │   └ users the user may become (run-as)
 │       └ hosts the rule applies to
 └ the user (or %group, e.g. %sudo) the rule is for
```

Common patterns:

```text
%sudo   ALL=(ALL:ALL) ALL                 # anyone in group 'sudo' → full root
kali    ALL=(ALL) NOPASSWD: /usr/bin/nmap # kali runs nmap as root, no password
deploy  ALL=(www-data) /usr/bin/systemctl restart app
```

> **`NOPASSWD` and overly broad command paths are classic privesc.** A rule
> like `NOPASSWD: /usr/bin/vim` lets a user open a root shell from inside vim
> (`:!bash`). Auditing sudoers for shell-spawning binaries (see
> [GTFOBins](https://gtfobins.github.io)) is a core assessment step.

```bash
# [Level 2+: Advanced / Field Ops] Enumerate your escalation surface fast
sudo -l 2>/dev/null                 # what can I run as root already?
cat /etc/sudoers.d/* 2>/dev/null    # drop-in rules people forget to audit
```

---

## 5. User & group management `[Level 1: Intermediate]`

```bash
# Create a user WITH a home dir (-m) and an explicit login shell (-s)
sudo useradd -m -s /bin/bash analyst

# Set / change a password
sudo passwd analyst              # set analyst's password
passwd                           # change YOUR OWN password

# Add a user to a supplementary group (-a APPEND, -G groups)
sudo usermod -aG sudo analyst    # grant sudo rights
sudo usermod -aG wireshark analyst
# WARNING: ALWAYS use -a with -G. 'usermod -G sudo analyst' (no -a) REPLACES all
#    supplementary groups, silently removing the user from every other group.

# Inspect group membership
groups analyst
id analyst

# Manage groups directly
sudo groupadd pentesters
sudo gpasswd -a analyst pentesters   # add to group
sudo gpasswd -d analyst pentesters   # remove from group

# Lock / unlock / delete an account
sudo usermod -L analyst          # lock (prepends ! to the hash)
sudo usermod -U analyst          # unlock
sudo userdel -r analyst          # delete + remove home dir (-r)
```

The three account files these commands touch:

- `/etc/passwd`: the account
- `/etc/shadow`: the password hash
- `/etc/group`: group membership (`sudo:x:27:kali,analyst`)

---

## 6. File permissions: the model

Every file/dir has a **type**, three permission triads (**owner**, **group**,
**others**), and each triad has **r** (4), **w** (2), **x** (1) bits.

```text
-rwxr-x---
│└┬┘└┬┘└┬┘
│ │  │  └ others: --- (0) nothing
│ │  └ group:  r-x (5) read + execute
│ └ owner:  rwx (7) read + write + execute
└ type: - file, d dir, l symlink
```

For directories the bits mean something slightly different:
- **r**: list the names inside
- **w**: create/delete entries inside
- **x**: enter/traverse the directory (`cd` into it, access files by path)

### Octal vs symbolic

```bash
# [Level 1: Intermediate] Octal modes (each digit = owner/group/other)
chmod 755 script.sh     # rwxr-xr-x  → executable, world-readable
chmod 644 notes.txt     # rw-r--r--  → typical file: owner writes, others read
chmod 600 id_rsa        # rw-------  → private key: owner only (SSH requires this)
chmod 700 ~/.ssh        # rwx------  → directory only owner may enter

# Symbolic modes (who: u/g/o/a, op: +/-/=, perms: rwx)
chmod +x deploy.sh      # add execute for everyone
chmod u+x,go-rwx secret # owner gets execute; group/other lose everything
chmod g+w shared/       # add group write
chmod -R o-rwx private/ # recursively strip 'others' access
```

Quick octal reference:

| Octal | Symbolic | Typical use |
|-------|----------|-------------|
| `600` | `rw-------` | SSH private keys, secrets |
| `644` | `rw-r--r--` | ordinary readable files |
| `700` | `rwx------` | private scripts / `~/.ssh` |
| `755` | `rwxr-xr-x` | executables, public directories |
| `777` | `rwxrwxrwx` | **almost always wrong**: world-writable |

---

## 7. Ownership: `chown` and `chgrp`

```bash
# [Level 1: Intermediate] Change owner and/or group
sudo chown analyst report.txt              # change owner
sudo chown analyst:pentesters report.txt   # owner AND group
sudo chgrp pentesters report.txt           # group only
sudo chown -R analyst:analyst /home/analyst # recurse over a tree

# Read current ownership
ls -l report.txt          # columns 3 and 4 are user and group
stat report.txt           # verbose: perms in octal + symbolic, owner, times
```

`stat` is the precise tool when `ls` is ambiguous:

```text
Access: (0644/-rw-r--r--)  Uid: ( 1000/ kali)   Gid: ( 1000/ kali)
```

---

## 8. Special bits: SUID, SGID, and sticky

Beyond rwx there are three special bits:

- **SUID** (`chmod u+s`, shows as `s` in owner-execute): the program runs with
  the **file owner's** UID, not the caller's. `passwd` is SUID-root so any user
  can update their hash in root-owned `/etc/shadow`.
- **SGID** (`chmod g+s`): runs as the file's group; on directories, new files
  inherit the directory's group.
- **Sticky** (`chmod +t`, `t` on other-execute): on a dir (`/tmp`), only a
  file's owner can delete it, even though the dir is world-writable.

```bash
# [Level 2+: Advanced / Field Ops] Audit SUID binaries, THE classic first step
find / -perm -u=s -type f 2>/dev/null            # all SUID files
find / -perm -g=s -type f 2>/dev/null            # all SGID files
find / -perm -4000 -type f -exec ls -la {} \; 2>/dev/null   # SUID w/ details

# Cross-reference results against GTFOBins. If an unexpected SUID binary can
# spawn a shell or read arbitrary files, it's a direct path to root.
```

Expected (trimmed) output:

```text
-rwsr-xr-x 1 root root  68208 /usr/bin/passwd    <- expected & normal
-rwsr-xr-x 1 root root 232416 /usr/bin/sudo      <- expected & normal
-rwsr-xr-x 1 root root 320000 /usr/bin/find      <- SUSPICIOUS: find can privesc!
```

> **Defender's move:** baseline the SUID set on a clean install
> (`find / -perm -4000 > /root/suid.baseline`), then diff periodically. Any new
> entry is investigated.

---

## 9. Process lifecycle & management `[Level 1: Intermediate]`

A **process** is a running program with a PID. Understanding process state is
essential for spotting implants, killing runaways, and managing services.

```bash
# [Level 0: Fundamental] Snapshot of processes
ps aux                     # every process: user, PID, %CPU, %MEM, command
ps aux | grep ssh          # find a specific process
ps -ef --forest            # tree view showing parent/child relationships

# [Level 0: Fundamental] Live, interactive view (q to quit)
top                        # real-time CPU/mem; press M=sort by mem, P=by cpu
htop                       # friendlier top (sudo apt install htop)

# [Level 1: Intermediate] Signal / terminate processes
kill 1337                  # polite: sends SIGTERM (15), lets it clean up
kill -9 1337               # forceful: SIGKILL (9), cannot be caught, last resort
kill -HUP 1337             # SIGHUP (1): many daemons reload config on this
pkill -f "python3 http"    # kill by matching the command line
killall nginx              # kill all processes named nginx
```

> `kill -9` gives a process no chance to flush files or release locks. Try plain
> `kill` (SIGTERM) first; escalate to `-9` only if it ignores you.

---

## 10. Services with `systemd` `[Level 1: Intermediate]`

Modern Kali uses **systemd** to manage background services ("units").

```bash
# Query state
systemctl status ssh              # is it running? recent log lines, PID
systemctl is-active ssh           # active / inactive
systemctl is-enabled ssh          # will it start at boot?
systemctl list-units --type=service --state=running   # everything running now

# Control a service (needs root)
sudo systemctl start ssh          # start now
sudo systemctl stop ssh           # stop now
sudo systemctl restart ssh        # stop then start
sudo systemctl reload ssh         # re-read config without dropping connections
sudo systemctl enable ssh         # start automatically at boot
sudo systemctl disable ssh        # don't start at boot
sudo systemctl enable --now ssh   # enable AND start in one step

# Read a service's logs (journald)
journalctl -u ssh                 # all logs for the ssh unit
journalctl -u ssh -f              # follow live (Ctrl-C to stop)
journalctl -u ssh --since "10 min ago"
```

> **Offense/defense:** `systemctl list-unit-files --state=enabled` and the
> contents of `/etc/systemd/system/` are where persistence hides, a malicious
> unit that re-launches an implant at boot. Baseline enabled units.

---

## Defensive counter-measures (blue-team lens)

- **Least privilege:** grant `sudo` narrowly; prefer `NOPASSWD` only for
  specific, non-shell-spawning binaries; never `NOPASSWD: ALL`.
- **Audit SUID/SGID** against a baseline; investigate every new one.
- **Protect the account files:** `/etc/shadow` must be `640 root:shadow`;
  `/etc/passwd` and `/etc/sudoers` should never be group/other-writable.
- **Watch `auth.log`:** `sudo`, `su`, failed logins, and new-user creation all
  land in `/var/log/auth.log`. Ship it off-box so an attacker who gets root
  can't erase the evidence.
- **Lock unused accounts** (`usermod -L`) and set `nologin` shells for service
  accounts so they can't be used for interactive login.

---

## Common troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `user is not in the sudoers file` | Account lacks sudo rights | Add via `usermod -aG sudo <user>` **as root**, then re-login |
| `sudo: /etc/sudoers is world writable` | Bad mode on sudoers | `pkexec chmod 440 /etc/sudoers` |
| Group change "didn't take" | Group membership is read at login | Log out/in, or run `newgrp <group>` |
| `chmod`/`chown` "Operation not permitted" | You don't own the file | Prefix with `sudo` |
| SSH refuses your key: "permissions too open" | Key not `600`, `~/.ssh` not `700` | `chmod 600 key; chmod 700 ~/.ssh` |
| `systemctl` "Failed to connect to bus" | Not running under systemd (e.g. WSL, container) | Use `service <name> start` or run the daemon directly |
| Locked out of root after editing sudoers | Syntax error | Boot to recovery / use `pkexec`; always edit with `visudo` |

---

 Practice these on the target lab and your own box in
**[lab-exercises.md](lab-exercises.md)**.
