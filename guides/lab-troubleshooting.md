# Lab troubleshooting

When the practice lab won't start or a module command doesn't behave, check this
page first. Each entry shows the message you see, what it means, and the fix.
The error text below is real output from `./scripts/setup-lab-env.sh`.

Quick reference: `./scripts/setup-lab-env.sh --help` lists the actions and exit
codes. `0` ok, `1` dependency missing, `2` Docker daemon down, `3` compose
error, `4` subnet conflict.

## Summary

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Docker is not installed or not on PATH` (exit 1) | No Docker on this machine | Install Docker Desktop (Windows/macOS) or Docker Engine (Linux), or use GitHub Codespaces |
| `Cannot talk to the Docker daemon` (exit 2) | Docker is installed but not running | Start Docker Desktop, or `sudo systemctl start docker`, then rerun |
| `Subnet 10.77.0.0/24 overlaps the Docker network(s) above` (exit 4) | Another Docker network uses part of `10.77.0.0/24` | Remove that network, see below |
| `ports are not available` / `address already in use` (exit 3) | Something on your machine already uses port 8080, 2121, or 21100-21110 | Stop that program, see below |
| `10.77.0.10 is not reachable from this machine directly` | Normal on Docker Desktop: the lab bridge lives inside Docker's VM | Run module commands from `./scripts/setup-lab-env.sh shell` |
| The first start takes many minutes | The first run downloads the Kali image and installs tools | Wait; later starts reuse the images and take seconds |
| The lab behaves oddly after you changed things in it | Files uploaded to FTP, or tools changed in the attacker | `./scripts/setup-lab-env.sh reset` for fresh containers |
| `bash tests/lab-smoke.sh` prints `FAIL` | A target is unhealthy or a check timed out | Rerun once; if it still fails, report it, see below |

## Docker is not running (exit 2)

```text
[x] Cannot talk to the Docker daemon. Is it running? (try: sudo systemctl start docker, or start Docker Desktop)
```

On Windows and macOS, start Docker Desktop and wait until it says it is running.
On Linux, `sudo systemctl start docker`. If you get a permission error on Linux,
either use `sudo` or add yourself to the `docker` group and log in again.

## Subnet conflict (exit 4)

The lab needs the `10.77.0.0/24` range for itself. If another Docker network
already covers part of it, the script stops before touching anything:

```text
[*] Validating lab subnet 10.77.0.0/24 ...
  my-vpn-net (10.77.0.0/16)
[x] Subnet 10.77.0.0/24 overlaps the Docker network(s) above. Remove them (docker network rm <name>) or change the subnet in docker-compose.yml.
```

The line above the error names each conflicting network and its range. To look
at it yourself:

```bash
docker network ls                       # every Docker network by name
docker network inspect my-vpn-net --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

If you don't need that network, remove it (`docker network rm my-vpn-net`; stop
any containers using it first). If you do, change the lab's subnet in
`docker-compose.yml`, and remember that every module uses the `10.77.0.x`
addresses, so you will have to translate them as you go.

## A port is already in use (exit 3)

The lab publishes the web target on `127.0.0.1:8080` and the FTP target on
`127.0.0.1:2121` (plus passive ports 21100-21110). If another program already
listens on one of them, Docker refuses to start the container. On Windows it
looks like this:

```text
Error response from daemon: ports are not available: exposing port TCP 127.0.0.1:8080 -> 127.0.0.1:0: listen tcp4 127.0.0.1:8080: bind: Only one usage of each socket address (protocol/network address/port) is normally permitted.
[x] Aborted at line 58. See messages above.
```

On Linux and macOS the same problem reads `address already in use`. Find the
program holding the port, then stop it and rerun the script:

```bash
# Linux / macOS
sudo lsof -iTCP:8080 -sTCP:LISTEN
# Windows (PowerShell)
Get-NetTCPConnection -LocalPort 8080 -State Listen | Select-Object OwningProcess
```

Usual suspects are another local web server, a dev proxy, or a second copy of
this lab. The ports only matter for browsing the targets from your host; every
module command runs from the attacker shell.

## Targets not reachable from your host (Docker Desktop)

At the end of a successful start on Docker Desktop you will see:

```text
Note: 10.77.0.10 is not reachable from this machine directly (normal
with Docker Desktop). Run the module commands from the attacker container:
  ./scripts/setup-lab-env.sh shell
```

This is expected, not a fault. Docker Desktop runs containers inside a small VM,
so the `10.77.0.x` bridge exists only there. Open the attacker shell and run
`nmap`, `curl`, `ftp`, and `tshark` from it. To see the login form in your own
browser, use `http://127.0.0.1:8080`.

## The first start is slow

The first `./scripts/setup-lab-env.sh` downloads the Kali image and installs
the tools in it, which can take several minutes on a slow or shared connection.
Later starts reuse the built images. If you teach a group, have everyone do the
first start before the session (see [Teaching with this course](teaching-with-this-course.md)).

## A smoke check fails

`bash tests/lab-smoke.sh` prints one `PASS` or `FAIL` line per check and ends
with either `All lab checks passed.` or a count such as `1 check(s) failed.`
A single FTP check can occasionally fail right after the lab starts. Rerun the
script once. If a check still fails:

1. Try `./scripts/setup-lab-env.sh reset` and run the checks again.
2. If it keeps failing, open a
   [lab problem issue](https://github.com/TMHSDigital/Kali-Linux-for-beginners/issues/new?template=lab-problem.yml)
   and paste the full output of `./scripts/setup-lab-env.sh`,
   `bash tests/lab-smoke.sh`, and `docker compose logs --no-color`. Say which
   host OS you use (Linux, Windows with Docker Desktop, macOS, Codespaces).

The targets are insecure on purpose. If you find that the lab is reachable from
other machines on your network, report that privately as described in
`SECURITY.md` instead.
