# 01 — Terminal & Linux Core `[Level 0: Fundamentals]`

Everything in offensive and defensive security runs through the shell. Before
you scan a network or crack a handshake, you must move around a Linux system
without thinking about it. This module builds that muscle memory and explains
*why* the filesystem and shell behave the way they do.

---

## 1. How the shell actually works (architecture)

When you open a terminal in Kali you are running a **shell** — almost always
**Bash** (`/bin/bash`) or **Zsh** (Kali's default since 2020.4). The shell is a
program that:

1. Prints a **prompt** and waits for a line of input.
2. **Parses** that line into a command + arguments, expanding globs (`*`),
   variables (`$HOME`), and pipes (`|`).
3. **Forks** a child process and **exec**s the requested program, or runs a
   *builtin* (like `cd`) inside itself.
4. Connects three standard streams to the process and waits for it to exit,
   then reports the **exit status** (`$?`, `0` = success).

The three standard streams matter enormously later (redirection, log capture):

| Stream | FD | Default | Purpose |
|--------|----|---------|---------|
| stdin  | 0  | keyboard | input to the program |
| stdout | 1  | terminal | normal output |
| stderr | 2  | terminal | errors / diagnostics |

### The Linux filesystem hierarchy (why paths look like they do)

Linux has **one** tree rooted at `/` — there are no drive letters. Key branches:

| Path | Contains |
|------|----------|
| `/` | Root of everything |
| `/home/<user>` | Your files (`~` is a shortcut for your home) |
| `/root` | The root user's home |
| `/etc` | System-wide config (`passwd`, `shadow`, `sudoers`) |
| `/bin`, `/usr/bin` | Executable programs |
| `/var/log` | Logs |
| `/tmp` | World-writable scratch space (cleared on reboot) |
| `/proc`, `/sys` | Virtual filesystems exposing kernel/process state |

---

## 2. Reading the prompt (prompt anatomy)

A default Kali prompt tells you *who* and *where* you are, and *how much power*
you hold:

```text
kali@kali:~$
└┬─┘ └┬─┘ └┬┘└┬┘
 │    │    │  └── prompt symbol: $ = normal user, # = root (full power!)
 │    │    └───── current directory (~ means /home/kali)
 │    └────────── hostname
 └─────────────── username
```

The single most important character is the **last one**:

- `$` — you are a **regular user**. Destructive mistakes are mostly contained.
- `#` — you are **root** (or in a root shell). Every command runs with total
  authority; a typo like `rm -rf /` is catastrophic. Respect the `#`.

```bash
# [Level 0: Fundamental] Who am I, and where am I?
whoami          # prints your username
id              # your UID/GID and group memberships (0 = root)
hostname        # the machine name shown in the prompt
```

Expected output:

```text
kali
uid=1000(kali) gid=1000(kali) groups=1000(kali),27(sudo),...
kali
```

---

## 3. Navigation

```bash
# [Level 0: Fundamental] Where am I? (print working directory)
pwd
# -> /home/kali

# [Level 0: Fundamental] Change directory
cd /etc          # absolute path (starts at /)
cd ..            # up one level
cd               # with no argument, go HOME (/home/kali)
cd -             # jump back to the PREVIOUS directory
cd ~/Downloads   # ~ expands to your home

# [Level 0: Fundamental] List directory contents
ls               # names only
ls -l            # long format: perms, owner, size, mtime
ls -a            # include hidden dotfiles (.bashrc, .ssh)
ls -la           # the everyday combo: long + all
ls -lh           # human-readable sizes (K/M/G instead of bytes)
ls -lt           # sort by modification time, newest first
```

Reading `ls -la` output — every column matters later for permissions work:

```text
drwxr-xr-x  2 kali kali 4096 Sep  5 12:00 Documents
-rw-r--r--  1 kali kali  220 Sep  5 11:58 .bashrc
 │└┬┘└┬┘└┬┘ │ └┬─┘ └┬─┘  └┬─┘ └────┬────┘ └───┬───┘
 │ │  │  │  │  │    │     │        │          └ name
 │ │  │  │  │  │    │     │        └ last-modified time
 │ │  │  │  │  │    │     └ size in bytes
 │ │  │  │  │  │    └ group owner
 │ │  │  │  │  └ user owner
 │ │  │  │  └ hard-link count
 │ │  │  └ others' permissions (r-x)
 │ │  └ group permissions (r-x)
 │ └ owner permissions (rwx)
 └ type: d=directory, -=file, l=symlink
```

---

## 4. Inspecting and creating files

```bash
# [Level 0: Fundamental] Print a file to the screen
cat /etc/hostname
cat -n script.sh          # with line numbers

# [Level 0: Fundamental] Page through a long file (q to quit)
less /etc/services         # scroll, /search, q to exit
head -n 20 /var/log/syslog # first 20 lines
tail -n 20 /var/log/syslog # last 20 lines
tail -f  /var/log/syslog   # FOLLOW: stream new lines live (Ctrl-C to stop)

# [Level 0: Fundamental] Create an empty file / update its timestamp
touch notes.txt

# [Level 0: Fundamental] Make directories (-p creates parents as needed)
mkdir recon
mkdir -p engagement/acme/scans   # creates all three levels at once
```

Expected output of `mkdir -p` then `ls -R`:

```text
engagement/
engagement/acme/
engagement/acme/scans/
```

---

## 5. Copying, moving, deleting `[Level 1: Intermediate]`

```bash
# Copy a file
cp report.txt report.bak
# Copy a directory tree recursively (-r) preserving attrs (-a)
cp -r engagement/ engagement-backup/
cp -a engagement/ engagement-archive/   # -a keeps timestamps/perms/symlinks

# Move OR rename (same command — moving to the same dir = rename)
mv notes.txt engagement/acme/notes.txt
mv oldname.txt newname.txt

# Remove files and directories
rm report.bak                # delete a file
rm -r engagement-backup/     # delete a directory tree
rm -rf engagement-archive/   # -f = force, no prompts (DANGEROUS)
```

> ⚠️ **`rm -rf` has no undo and no recycle bin.** There is no confirmation. A
> stray space — `rm -rf / home/kali` instead of `rm -rf /home/kali` — will try
> to erase the entire system. Habits that save you:
> - Run `ls <target>` first to confirm you're pointing at the right thing.
> - Prefer `rm -ri` (interactive) when unsure; it asks per file.
> - Never run `rm -rf` as root against a variable you didn't sanity-check
>   (`rm -rf "$DIR"/` where `$DIR` is empty = `rm -rf /`).

---

## 6. Search: finding files and content

```bash
# [Level 0: Fundamental] Where does a command live on disk?
which nmap
# -> /usr/bin/nmap

# [Level 1: Intermediate] Find files by name (starts at a path, recurses down)
find / -name "sshd_config" 2>/dev/null       # search whole disk, hide errors
find /etc -type f -name "*.conf"             # only regular files ending .conf
find /home -type d -name ".ssh"              # only directories named .ssh
find / -perm -u=s -type f 2>/dev/null        # SUID binaries (preview of mod 02)
find /var/log -mmin -10                       # files modified in last 10 minutes

# [Level 0: Fundamental] Search *inside* files for a pattern
grep "root" /etc/passwd                       # lines containing 'root'
grep -i "error" /var/log/syslog               # -i = case-insensitive
grep -r "password" /etc/ 2>/dev/null          # -r = recurse into directories
grep -n "kali" /etc/passwd                    # -n = show line numbers
grep -v "^#" /etc/ssh/sshd_config             # -v = INVERT: lines NOT matching
```

Why `2>/dev/null`? `find /` walking the whole disk as a normal user hits many
"Permission denied" errors on **stderr (fd 2)**. Redirecting fd 2 to the null
device throws those away so only real matches (on stdout) remain — the first
practical use of stream redirection.

---

## 7. Pipes and redirection (the heart of the shell) `[Level 1: Intermediate]`

**Redirection** sends a stream to/from a file. **Pipes** connect one program's
stdout to the next program's stdin. Composing small tools this way is the whole
Unix philosophy.

```bash
# Redirect stdout to a file (> overwrites, >> appends)
ls -la > listing.txt          # create/overwrite listing.txt
echo "new line" >> listing.txt # append one line

# Redirect stderr (fd 2) specifically
find / -name secret 2> errors.txt        # errors go to file, matches to screen
find / -name secret 2>/dev/null          # discard errors entirely

# Merge stderr INTO stdout so both land in the same place
./scan.sh > scan.log 2>&1     # order matters: send stdout to file, then 2->1
./scan.sh &> scan.log         # bash shorthand for the same thing

# Pipe: feed one command's output into another
cat /etc/passwd | grep bash               # users with a bash login shell
ps aux | grep ssh                         # find ssh processes
history | grep nmap                       # your past nmap commands
ls -l /usr/bin | wc -l                    # COUNT executables (wc -l = line count)
cat access.log | grep 404 | sort | uniq -c | sort -rn   # top 404 URLs
```

Understanding `2>&1` ordering (a classic gotcha):

```text
command > file 2>&1    # ✅ stdout->file, THEN stderr->wherever stdout points (file)
command 2>&1 > file    # ❌ stderr->terminal (copied first), THEN stdout->file
```

Redirection is applied **left to right**; `2>&1` copies wherever fd 1 points *at
that moment*.

---

## 8. Command history and recall `[Level 1: Intermediate]`

```bash
history                 # numbered list of past commands
history | tail -n 20    # last 20
!123                    # re-run history entry #123
!!                      # re-run the previous command
!nmap                   # re-run the last command starting with 'nmap'
sudo !!                 # re-run previous command, this time with sudo
```

Interactive recall:

- **Ctrl-R** — reverse-search history as you type; Enter to run, Ctrl-R again
  to cycle older matches.
- **↑ / ↓** — walk through recent commands.
- History persists in `~/.bash_history` (or `~/.zsh_history`).

---

## 9. Getting help (never memorize — look it up)

```bash
man ls              # full manual page (q to quit, / to search)
ls --help           # quick flag summary for most tools
whatis grep         # one-line description
apropos network     # search man page descriptions by keyword
type cd             # is it a builtin, alias, or a program?
```

---

## Defensive counter-measures (blue-team lens)

Even at Level 0, notice the defensive angles:

- **Shell history is evidence.** Investigators read `~/.bash_history`,
  `~/.zsh_history`, and auditd logs to reconstruct what an intruder did.
  Attackers who set `HISTFILE=/dev/null` or `unset HISTFILE` leave a *different*
  tell. On systems you defend, ship history to a remote log so it can't be wiped.
- **World-writable `/tmp`** is a favorite staging area for dropped tools — watch
  it.
- **Unexpected SUID files** (`find / -perm -u=s`) are a top privilege-escalation
  vector (covered in module 02) — baseline them so you notice new ones.
- **`/var/log` tampering:** truncated or missing logs are themselves a signal.

---

## Common troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `command not found` | Program not installed or not on `$PATH` | `sudo apt install <pkg>`; check `echo $PATH` |
| `Permission denied` on a script | Not executable | `chmod +x script.sh` then `./script.sh` |
| `No such file or directory` | Wrong path / typo / relative vs absolute | `pwd`, `ls`, use Tab-completion |
| `cd: not a directory` | Target is a file | `ls -l` to confirm the type |
| Output "disappears" | It went to a redirected file or to stderr | Check `> file`; try `2>&1` |
| Terminal frozen after `less`/`tail -f` | Program is still running | `q` for `less`, `Ctrl-C` for `tail -f` |

---

➡️ Continue to the hands-on **[lab-exercises.md](lab-exercises.md)** to prove
you can do all of the above from memory.
