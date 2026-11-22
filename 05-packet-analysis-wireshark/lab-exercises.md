# Lab exercises: Packet analysis with Wireshark & tshark

Capture the lab's cleartext logins and file transfers, then pull the secrets
back out of the capture files with `tshark`. Each task has a **goal**, the
**commands** to try, and a **self-grading check** that prints `PASS` when you
got it right. Where the answer is a secret, the check compares a SHA-256 hash
so it doesn't give the answer away.

> **Only sniff traffic you are authorized to see.** Here that's the lab's own
> traffic on `10.77.0.0/24`.

Run everything from the attacker's root shell, `./scripts/setup-lab-env.sh
shell`, where the lab interface is `eth0`. Work in a scratch folder:

```bash
mkdir -p /root/work/lab05 && cd /root/work/lab05
```

Every capture follows the same pattern: start `tshark` in the background with
`-a duration:6` so it stops itself after six seconds, give it two seconds to
open the interface, make the traffic, then `wait` for the capture to finish.

---

## Exercise 1: Recover a web password

**Goal:** Capture a login to the web target and read the password out of the
HTTP POST body.

```bash
tshark -i eth0 -f "tcp port 80" -a duration:6 -w web.pcapng &
sleep 2
curl -s -d 'username=admin&password=hunter2' http://10.77.0.10/login >/dev/null
wait                                     # until the capture stops

tshark -r web.pcapng -Y 'http.request.method == "POST"' \
       -T fields -e urlencoded-form.key -e urlencoded-form.value
```

Expected output of the last command:

```text
username,password	admin,hunter2
```

Yes, you typed the password yourself. The point is that anyone who can see
the traffic gets it just as easily.

**Self-grade:**

```bash
read -rp "Password in the captured POST: " ans
[ "$(printf %s "$ans" | sha256sum | cut -d' ' -f1)" = \
  "f52fbd32b2b3b86ff88ef6c490628285f482af15ddcb29541f94bcf526a3f6c7" ] \
  && tshark -r web.pcapng -Y 'urlencoded-form.key == "password"' 2>/dev/null | grep -q POST \
  && echo "PASS: password recovered from your capture" \
  || echo "FAIL: check web.pcapng has the POST, and your answer"
```

---

## Exercise 2: Extract FTP credentials

**Goal:** Capture an FTP login and save the username and password to
`creds.txt` with a single `tshark` field extraction.

```bash
tshark -i eth0 -f "tcp port 21" -a duration:6 -w ftp.pcapng &
sleep 2
curl -s ftp://labuser:labpass@10.77.0.20/ >/dev/null
wait                                     # until the capture stops

tshark -r ftp.pcapng \
       -Y 'ftp.request.command == "USER" || ftp.request.command == "PASS"' \
       -T fields -e ftp.request.command -e ftp.request.arg > creds.txt
cat creds.txt
```

**Self-grade:**

```bash
pass=$(awk '$1 == "PASS" {print $2}' creds.txt)
grep -q "^USER" creds.txt \
  && [ "$(printf %s "$pass" | sha256sum | cut -d' ' -f1)" = \
       "f7d048204bb7d898447148643429481bb3bfc70eefb126ad37fe577c4ffd1381" ] \
  && echo "PASS: USER and PASS extracted" \
  || echo "FAIL: creds.txt needs the USER and PASS lines from ftp.pcapng"
```

---

## Exercise 3: Carve a file out of the traffic

**Goal:** Capture an FTP download, then rebuild the downloaded file from the
packets alone.

FTP sends files over a second connection on a separate port, so capture
everything to and from the FTP server, not just port 21:

```bash
tshark -i eth0 -f "host 10.77.0.20" -a duration:6 -w ftp-file.pcapng &
sleep 2
curl -s -o /dev/null ftp://labuser:labpass@10.77.0.20/notes.txt   # the "victim" download
wait                                     # until the capture stops

rm -rf exported                    # tshark renames files that already exist
tshark -r ftp-file.pcapng -q --export-objects ftp-data,exported
ls exported
cat exported/notes.txt
```

The download went to `/dev/null`, so the only copy you have is the one you
rebuilt from the capture. In Wireshark the same thing is **File, Export
Objects, FTP-DATA**.

**Self-grade:**

```bash
[ "$(sha256sum < exported/notes.txt 2>/dev/null | cut -d' ' -f1)" = \
  "161ecae75fff0a2a074c04ef2825f3fc70e63d242d186df4c90797ce7de0112b" ] \
  && echo "PASS: file carved from the capture, byte for byte" \
  || echo "FAIL: exported/notes.txt missing or different, capture with -f \"host 10.77.0.20\""
```

---

## Exercise 4: Describe the fix

**Goal:** For each capture above, write one sentence on what would have made
it useless to you. Use the module's defensive section if you're stuck.

**Self-grade (manual):** each answer names a specific replacement (for
example HTTPS instead of HTTP, SFTP or FTPS instead of FTP) and says why a
passive sniffer can't read it.

---

## Cleanup

```bash
cd /root/work && rm -rf lab05
echo "Lab 05 files removed."
```

---

### Scorecard

| # | Skill demonstrated |
|---|--------------------|
| 1 | Capture filter, display filter, HTTP form fields |
| 2 | `tshark -T fields` credential extraction |
| 3 | Export objects: rebuild a transferred file |
| 4 | Naming the defense |

Four for four and you've finished the course's core path. The capture skills
carry straight into the reference pages:
**[filter-cheatsheet.md](filter-cheatsheet.md)**.
