#!/usr/bin/env bash
# =============================================================================
# setup-lab-env.sh: bring up the Kali-for-Beginners practice target lab.
#
# Verifies that Docker and the Compose v2 plugin are present and healthy,
# validates the lab bridge subnet against existing Docker networks, starts the
# attacker + target containers, waits for them to be healthy, and prints the
# commands to run next.
#
# Usage:
#   ./scripts/setup-lab-env.sh          # verify + start the lab
#   ./scripts/setup-lab-env.sh shell    # open a bash shell on the attacker box
#   ./scripts/setup-lab-env.sh status   # show container status
#   ./scripts/setup-lab-env.sh down     # stop and remove the lab
#
# Exit codes: 0 ok | 1 dependency missing | 2 daemon down | 3 compose error
#             4 subnet conflict
# =============================================================================
set -euo pipefail

# --- Resolve the repo root regardless of where the script is invoked from ----
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
LAB_NETWORK="pentest-lab-net"

LAB_SUBNET="10.77.0.0/24"
ATTACKER_IP="10.77.0.5"
WEB_TARGET_IP="10.77.0.10"
FTP_TARGET_IP="10.77.0.20"

# --- Minimal colourised logging ---------------------------------------------
if [[ -t 1 ]]; then
  C_RED=$'\033[0;31m'; C_GRN=$'\033[0;32m'; C_YEL=$'\033[0;33m'
  C_BLU=$'\033[0;34m'; C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YEL=""; C_BLU=""; C_RST=""
fi
info()  { printf '%s[*]%s %s\n'  "${C_BLU}" "${C_RST}" "$*"; }
ok()    { printf '%s[+]%s %s\n'  "${C_GRN}" "${C_RST}" "$*"; }
warn()  { printf '%s[!]%s %s\n'  "${C_YEL}" "${C_RST}" "$*" >&2; }
die()   { printf '%s[x]%s %s\n'  "${C_RED}" "${C_RST}" "$1" >&2; exit "${2:-1}"; }

# --- Trap so a mid-script failure is reported clearly ------------------------
trap 'die "Aborted at line ${LINENO}. See messages above." 3' ERR

compose() { docker compose -f "${COMPOSE_FILE}" "$@"; }

# --- Dependency checks -------------------------------------------------------
require_docker() {
  command -v docker >/dev/null 2>&1 \
    || die "Docker is not installed or not on PATH. Install Docker Engine first." 1
  ok "Found docker: $(docker --version)"

  # Compose v2 is a docker subcommand ('docker compose'), not the legacy binary.
  if docker compose version >/dev/null 2>&1; then
    ok "Found Compose v2: $(docker compose version --short 2>/dev/null || echo present)"
  else
    die "The 'docker compose' (v2) plugin is missing. Install docker-compose-plugin." 1
  fi
}

require_daemon() {
  if ! docker info >/dev/null 2>&1; then
    die "Cannot talk to the Docker daemon. Is it running? (try: sudo systemctl start docker, or start Docker Desktop)" 2
  fi
  ok "Docker daemon is reachable."
}

require_compose_file() {
  [[ -f "${COMPOSE_FILE}" ]] \
    || die "docker-compose.yml not found at ${COMPOSE_FILE}" 3
  ok "Compose file: ${COMPOSE_FILE}"
}

# --- Validate the lab subnet before we bind to it ---------------------------
# Prints "<network> <subnet>" for every IPv4 subnet of every other network.
other_subnets() {
  local ids
  ids="$(docker network ls -q)"
  [[ -n "${ids}" ]] || return 0
  # shellcheck disable=SC2086  # word-splitting the id list is intended
  docker network inspect ${ids} \
      --format '{{.Name}}{{range .IPAM.Config}} {{.Subnet}}{{end}}' 2>/dev/null \
    | awk -v self="${LAB_NETWORK}" '$1!=self {for (i=2;i<=NF;i++) print $1, $i}'
}

# Returns 0 if CIDR $1 overlaps CIDR $2 (IPv4 only; IPv6 never overlaps).
cidr_overlaps() {
  local a="$1" b="$2"
  [[ "${a}" == *:* || "${b}" == *:* ]] && return 1
  to_int() { local IFS=.; read -r o1 o2 o3 o4 <<<"$1"; echo $(( (o1<<24)|(o2<<16)|(o3<<8)|o4 )); }
  local an="${a%/*}" al="${a#*/}" bn="${b%/*}" bl="${b#*/}"
  local len=$(( al < bl ? al : bl ))
  local mask=$(( len == 0 ? 0 : (0xFFFFFFFF << (32 - len)) & 0xFFFFFFFF ))
  (( ( $(to_int "${an}") & mask ) == ( $(to_int "${bn}") & mask ) ))
}

validate_network() {
  info "Validating lab subnet ${LAB_SUBNET} ..."

  if docker network ls --format '{{.Name}}' | grep -qx "${LAB_NETWORK}"; then
    ok "Network '${LAB_NETWORK}' already exists; it will be reused."
  fi

  local conflicts="" name subnet
  while read -r name subnet; do
    [[ -n "${subnet:-}" ]] || continue
    if cidr_overlaps "${LAB_SUBNET}" "${subnet}"; then
      conflicts+="  ${name} (${subnet})"$'\n'
    fi
  done < <(other_subnets)

  if [[ -n "${conflicts}" ]]; then
    printf '%s' "${conflicts}" >&2
    die "Subnet ${LAB_SUBNET} overlaps the Docker network(s) above. Remove them (docker network rm <name>) or change the subnet in docker-compose.yml." 4
  fi
  ok "Subnet ${LAB_SUBNET} does not overlap any existing Docker network."
}

# --- Actions -----------------------------------------------------------------
wait_healthy() {
  local svc="$1" tries=40 status=""
  while (( tries-- > 0 )); do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${svc}" 2>/dev/null || true)"
    [[ "${status}" == "healthy" || "${status}" == "running" ]] && { ok "${svc} is ${status}."; return 0; }
    sleep 3
  done
  warn "${svc} is not healthy yet (status: ${status:-unknown}). Check: docker compose logs ${svc}"
}

lab_up() {
  info "Building and starting the lab (the first run downloads Kali; give it a few minutes) ..."
  mkdir -p "${REPO_ROOT}/workspace"
  compose up -d --build
  wait_healthy web-target
  wait_healthy ftp-service
  wait_healthy attacker

  cat <<EOF

${C_GRN}=== Lab is up ===${C_RST}
  attacker     ${ATTACKER_IP}    run commands from here:  ./scripts/setup-lab-env.sh shell
  web-target   ${WEB_TARGET_IP}   http://${WEB_TARGET_IP}   (from your host browser: http://127.0.0.1:8080)
  ftp-service  ${FTP_TARGET_IP}   ftp://${FTP_TARGET_IP}    (from your host: ftp 127.0.0.1 2121)

Only scan the ${LAB_SUBNET} range. From the attacker shell, try:
  nmap -sn ${LAB_SUBNET}
  nmap -sV ${WEB_TARGET_IP} ${FTP_TARGET_IP}
EOF

  # On Docker Desktop (Windows/macOS/WSL) the bridge IPs are not reachable
  # from the host. Say so up front instead of letting nmap report "host down".
  if command -v ping >/dev/null 2>&1 && ! ping -c1 -W1 "${WEB_TARGET_IP}" >/dev/null 2>&1; then
    cat <<EOF

${C_YEL}Note:${C_RST} ${WEB_TARGET_IP} is not reachable from this machine directly (normal
with Docker Desktop). Run the module commands from the attacker container:
  ./scripts/setup-lab-env.sh shell
EOF
  fi
}

lab_shell() {
  if [[ "$(docker inspect -f '{{.State.Running}}' attacker 2>/dev/null || true)" != "true" ]]; then
    info "Attacker container is not running; starting the lab first ..."
    lab_up
  fi
  info "Entering the attacker box (${ATTACKER_IP}). Repo is at /lab, save work in /root/work."
  exec docker exec -it attacker bash
}

lab_down() {
  info "Stopping the practice target lab ..."
  compose down
  ok "Lab stopped and containers removed."
}

lab_status() {
  compose ps
}

# --- Entry point -------------------------------------------------------------
main() {
  local action="${1:-up}"
  require_docker
  require_daemon
  require_compose_file

  case "${action}" in
    up)     validate_network; lab_up ;;
    shell)  lab_shell ;;
    down)   lab_down ;;
    status) lab_status ;;
    *)      die "Unknown action '${action}'. Use: up | shell | status | down" 1 ;;
  esac
}

main "$@"
