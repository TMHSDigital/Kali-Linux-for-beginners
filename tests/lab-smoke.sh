#!/usr/bin/env bash
# shellcheck disable=SC2016  # single-quoted strings are commands run inside the attacker container
# =============================================================================
# lab-smoke.sh: prove the practice lab does what the curriculum says it does.
#
# Run after ./scripts/setup-lab-env.sh. Every check runs from the attacker
# container, exactly where learners run the module commands, plus a couple of
# host-side checks for the published loopback ports.
#
#   bash tests/lab-smoke.sh
# =============================================================================
set -uo pipefail

export MSYS_NO_PATHCONV=1   # Git Bash on Windows: don't rewrite /paths in args
FAILS=0
pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; FAILS=$((FAILS + 1)); }
check() {  # check "<description>" <command...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "${desc}"; else fail "${desc}"; fi
}
att() { docker exec attacker bash -c "$1"; }

echo "== Containers"
for c in attacker web-target ftp-service; do
  check "${c} is running" test "$(docker inspect -f '{{.State.Running}}' "${c}" 2>/dev/null)" = true
done

echo "== web-target (module 03/05)"
check "serves the ACME login page" att 'curl -fsS http://10.77.0.10/ | grep -q "ACME Intranet"'
check "POST /login answers 200" att 'curl -fsS -d "username=admin&password=hunter2" http://10.77.0.10/login | grep -q "Received (lab)"'

echo "== ftp-service (module 03/05)"
check "anonymous login lists /pub" att 'curl -fsS ftp://10.77.0.20/pub/ | grep -q welcome.txt'
check "labuser/labpass login works" att 'curl -fsS ftp://labuser:labpass@10.77.0.20/ | grep -q notes.txt'
check "nmap ftp-anon reports anonymous allowed" att 'nmap -p21 --script ftp-anon 10.77.0.20 | grep -q "Anonymous FTP login allowed"'

echo "== Recon tooling (module 03)"
check "ping sweep finds both targets" att 'out=$(nmap -sn 10.77.0.0/24); grep -q 10.77.0.10 <<<"$out" && grep -q 10.77.0.20 <<<"$out"'
check "parse-nmap-xml.py is on PATH and parses a scan" att 'nmap -sV -p21,80 -oX - 10.77.0.10 10.77.0.20 | parse-nmap-xml.py - --no-color | grep -q "open   http"'

echo "== Packet capture (module 05)"
check "tshark captures FTP USER/PASS from the attacker" att '
  rm -f /tmp/smoke.pcapng
  tshark -i eth0 -f "tcp port 21" -a duration:8 -w /tmp/smoke.pcapng >/dev/null 2>&1 &
  sleep 3; curl -s ftp://labuser:labpass@10.77.0.20/ >/dev/null; wait
  tshark -r /tmp/smoke.pcapng -Y "ftp.request.command == \"PASS\"" -T fields -e ftp.request.arg | grep -qx labpass'
check "tshark captures the HTTP POST body" att '
  rm -f /tmp/smoke-web.pcapng
  tshark -i eth0 -f "tcp port 80" -a duration:8 -w /tmp/smoke-web.pcapng >/dev/null 2>&1 &
  sleep 3; curl -s -d "username=admin&password=hunter2" http://10.77.0.10/login >/dev/null; wait
  tshark -r /tmp/smoke-web.pcapng -Y "http.request.method == \"POST\"" -T fields -e urlencoded-form.value | grep -q hunter2'

echo "== Host loopback ports"
if command -v curl >/dev/null 2>&1; then
  check "http://127.0.0.1:8080 serves the login page" bash -c 'curl -fsS http://127.0.0.1:8080/ | grep -q "ACME Intranet"'
  check "ftp://127.0.0.1:2121 accepts labuser (skip PASV IP)" bash -c 'curl -fsS --ftp-skip-pasv-ip ftp://labuser:labpass@127.0.0.1:2121/ | grep -q notes.txt'
else
  echo "  SKIP  curl not installed on the host"
fi

echo
if (( FAILS > 0 )); then echo "${FAILS} check(s) failed."; exit 1; fi
echo "All lab checks passed."
