# Teaching with This Course

This page is for teachers, club leads, and anyone running the curriculum for a
group. The material is MIT licensed: you can copy, adapt, and reorder it for your
class, and you don't need to ask.

## Before the first session

**Set the ground rules in writing.** Every learner should agree, before they
touch a scanner, that they will only target the practice lab, `127.0.0.1`, or
equipment you explicitly provide for the exercise. A one-page rules-of-engagement
sheet they sign works well and mirrors what professional testers do. Point them
at the disclaimer in the [LICENSE](../LICENSE) and talk through why scanning a
school, employer, or neighbor's network without written permission is illegal in
most places, even "just to look".

**Talk to your network admin.** Everything in the lab stays on a private Docker
network inside each learner's own machine, and the published ports bind to
`127.0.0.1` only, so the lab itself doesn't put traffic on your network. Still,
nmap and packet capture tools on school machines can trip monitoring. A heads-up
saves an awkward conversation.

**Pick how learners will run the lab.**

| Option | Good for | What each learner needs |
|--------|----------|-------------------------|
| Their own laptop with Docker | Most groups | 8 GB RAM, a few GB of free disk, Docker Desktop or Docker Engine |
| GitHub Codespaces | Chromebooks, locked-down lab PCs, mixed hardware | A browser and a GitHub account. Free usage is capped monthly, so stop codespaces after class |
| A Kali VM per learner | Classes that also cover installing Kali | A VM host with 4 GB RAM per VM, plus Docker inside the VM |

Have everyone run the lab once before the first session that needs it. The first
`./scripts/setup-lab-env.sh` downloads the Kali image, which can take a while on a
shared connection. On the day, `bash tests/lab-smoke.sh` is a quick way to see
whose lab is healthy: it prints one `PASS` or `FAIL` line per check.

**Give each learner their own lab.** Don't point a whole room at one shared set of
targets. The lab is built for one person, and a shared target turns one
learner's mistake into everyone's outage.

## A suggested schedule

Six sessions of about 2 to 3 hours each, plus homework, fits the material. Adjust
to taste.

| Session | Cover | Hands-on |
|---------|-------|----------|
| 1 | Ground rules, lab setup, [01. Terminal & Linux Core](../01-terminal-and-linux-core/) | Module 01 lab exercises (self-grading) |
| 2 | [02. System Admin & Privileges](../02-system-admin-and-privileges/) | Module 02 lab exercises (self-grading) |
| 3 | [03. Network Recon & Nmap](../03-network-recon-and-nmap/) | Scan the lab and turn the XML into a table with `parse-nmap-xml.py` |
| 4 | [05. Packet Analysis & Wireshark](../05-packet-analysis-wireshark/) | Capture the lab's cleartext HTTP and FTP logins and recover the credentials |
| 5 | [04. Wireless Security & Aircrack-ng](../04-wireless-security-aircrack/) | Demo or small-group work, see below |
| 6 | Review and defense | Each learner writes up one finding: what they did, the evidence, and the fix |

Running module 05 before module 04 is deliberate. It only needs the Docker lab,
and it gives learners the most satisfying moment of the course (reading a password
off the wire) without any special hardware.

## Module 04 needs extra care

Live wireless work needs a USB adapter that supports monitor mode (see the
[hardware page](../04-wireless-security-aircrack/hardware-and-setup.md)) and,
above all, an access point that you own and have set up for the class. Use a
cheap dedicated router with a throwaway passphrase, keep it away from the
school's own Wi-Fi, and never let learners capture or deauthenticate networks
they don't own. Deauthentication frames hit every client in range, so a
demonstration in a shared building can knock real people offline.

If that isn't practical, teach module 04 as a demo from the front of the room, or
skip the live capture and have learners work through the concepts and the
WPA3/PMF defenses.

## Checking progress

- Modules 01 and 02 have self-grading lab exercises: each step prints `PASS` or
  a `FAIL` message that says what to fix.
- For modules 03 and 05, ask for evidence instead: the parsed nmap table, or the
  recovered credentials plus the display filter that found them.
- The documentation site tracks which pages a learner has marked done, stored in
  their own browser only. Nothing is sent anywhere, so it's a self-check, not a
  gradebook.

## Getting help and giving back

Ask questions or share how your class went in
[Discussions](https://github.com/TMHSDigital/Kali-Linux-for-beginners/discussions).
If a command didn't behave the way a page says, please
[open a content error](https://github.com/TMHSDigital/Kali-Linux-for-beginners/issues/new/choose)
with the real output. Fixes from teachers who watched a room of beginners get
stuck are the most valuable kind.
