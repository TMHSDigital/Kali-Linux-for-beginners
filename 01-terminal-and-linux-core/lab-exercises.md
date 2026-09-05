# Lab Exercises — Terminal & Linux Core

Work through these in order in a Kali terminal. Each task has a **goal**, the
**commands** to try, and a **self-grading check** — a command that prints
`PASS` when you got it right. If a check fails, re-read the relevant section of
the module README and try again.

> Set up a scratch workspace first so you can delete everything cleanly at the
> end:
>
> ```bash
> mkdir -p ~/lab01 && cd ~/lab01
> ```

---

## Exercise 1 — Orient yourself

**Goal:** Confirm who and where you are.

```bash
whoami
id
pwd
```

**Self-grade:**

```bash
[ "$(pwd)" = "$HOME/lab01" ] && echo PASS || echo "FAIL: cd into ~/lab01 first"
```

---

## Exercise 2 — Build a directory tree in one shot

**Goal:** Create `engagement/acme/{scans,loot,notes}` using a single `mkdir`.

```bash
mkdir -p engagement/acme/scans engagement/acme/loot engagement/acme/notes
ls -R engagement
```

**Self-grade:**

```bash
count=$(find engagement -type d | wc -l)
[ "$count" -eq 5 ] && echo PASS || echo "FAIL: expected 5 dirs, found $count"
```

*(5 = `engagement`, `acme`, `scans`, `loot`, `notes`.)*

---

## Exercise 3 — Create, copy, rename, move

**Goal:** Make a file, copy it, rename the copy, then move it into `notes/`.

```bash
touch engagement/acme/scans/nmap-raw.txt
cp engagement/acme/scans/nmap-raw.txt engagement/acme/scans/nmap-copy.txt
mv engagement/acme/scans/nmap-copy.txt engagement/acme/scans/summary.txt
mv engagement/acme/scans/summary.txt engagement/acme/notes/summary.txt
```

**Self-grade:**

```bash
[ -f engagement/acme/notes/summary.txt ] && \
[ -f engagement/acme/scans/nmap-raw.txt ] && \
echo PASS || echo "FAIL: check the file locations"
```

---

## Exercise 4 — Redirection: capture stdout and stderr separately

**Goal:** Run a `find` that produces both matches and permission errors; send
matches to `hits.txt` and errors to `errs.txt`.

```bash
find /etc -name "*.conf" 1> hits.txt 2> errs.txt
wc -l hits.txt errs.txt
```

**Self-grade:**

```bash
[ -s hits.txt ] && echo PASS || echo "FAIL: hits.txt is empty — did stdout redirect?"
```

*(`-s` = file exists and is non-empty.)*

---

## Exercise 5 — Append vs overwrite

**Goal:** See the difference between `>` and `>>`.

```bash
echo "line one"  > log.txt      # create with one line
echo "line two" >> log.txt      # append
echo "clobbered" > log.txt      # OVERWRITE — line one/two are gone
cat log.txt
```

**Self-grade:**

```bash
lines=$(wc -l < log.txt)
[ "$lines" -eq 1 ] && echo PASS || echo "FAIL: expected 1 line after overwrite, got $lines"
```

---

## Exercise 6 — Pipes and counting

**Goal:** Count how many user accounts have a `/bin/bash` login shell.

```bash
grep "/bin/bash" /etc/passwd
grep "/bin/bash" /etc/passwd | wc -l
```

**Self-grade:**

```bash
mine=$(grep -c "/bin/bash" /etc/passwd)
real=$(grep "/bin/bash" /etc/passwd | wc -l)
[ "$mine" -eq "$real" ] && echo "PASS ($real bash users)" || echo "FAIL"
```

---

## Exercise 7 — grep filtering: strip comments and blanks

**Goal:** Print the SSH config with comment lines and blank lines removed.

```bash
grep -v "^#" /etc/ssh/sshd_config | grep -v "^$"
```

**Self-grade (there should be fewer lines than the raw file):**

```bash
raw=$(wc -l < /etc/ssh/sshd_config)
clean=$(grep -v "^#" /etc/ssh/sshd_config | grep -v "^$" | wc -l)
[ "$clean" -lt "$raw" ] && echo "PASS ($clean of $raw lines)" || echo "FAIL"
```

*(If `/etc/ssh/sshd_config` doesn't exist, `sudo apt install openssh-server`
first, or substitute any config file in `/etc`.)*

---

## Exercise 8 — find by permission (preview of module 02)

**Goal:** List SUID binaries — files that run as their owner regardless of who
launches them. These are prime privilege-escalation targets.

```bash
find / -perm -u=s -type f 2>/dev/null
find / -perm -u=s -type f 2>/dev/null | wc -l
```

**Self-grade:**

```bash
n=$(find / -perm -u=s -type f 2>/dev/null | wc -l)
[ "$n" -ge 1 ] && echo "PASS (found $n SUID files — remember this for module 02)" || echo "FAIL"
```

---

## Exercise 9 — History recall

**Goal:** Use history expansion to re-run a command.

```bash
echo "first command"
history | tail -n 5
!!                # re-runs the previous line
```

**Self-grade (manual):** You should see `first command` printed twice — once
directly, once from `!!`. There is no automated check; confirm visually.

---

## Exercise 10 — One-liner challenge (bring it together)

**Goal:** From `/etc/passwd`, produce a sorted, unique list of every login
shell in use, with a count of how many accounts use each — using only pipes.

```bash
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn
```

Expected output shape:

```text
     30 /usr/sbin/nologin
      3 /bin/bash
      1 /bin/sync
      ...
```

**Self-grade:**

```bash
cut -d: -f7 /etc/passwd | sort | uniq -c | sort -rn | head -n1 | grep -q "/" \
  && echo PASS || echo "FAIL: check the pipeline"
```

---

## Cleanup

```bash
cd ~ && rm -rf ~/lab01
echo "Lab 01 workspace removed."
```

---

### Scorecard

| # | Skill demonstrated |
|---|--------------------|
| 1 | Orientation (`whoami`, `id`, `pwd`) |
| 2 | `mkdir -p` nested trees |
| 3 | `touch`, `cp`, `mv` |
| 4 | Separating stdout/stderr redirection |
| 5 | `>` vs `>>` |
| 6 | Pipes + `wc -l` |
| 7 | `grep -v` filtering |
| 8 | `find -perm` (SUID) |
| 9 | History expansion |
| 10 | Multi-stage pipeline (`cut`/`sort`/`uniq`) |

Ten PASSes and you're ready for **[module 02](../02-system-admin-and-privileges/)**.
