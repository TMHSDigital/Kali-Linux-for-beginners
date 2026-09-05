#!/usr/bin/env bash
# =============================================================================
# setup-lab-env.sh: bring up the Kali-for-Beginners practice target lab.
#
# Verifies that Docker and the Compose v2 plugin are present and healthy,
# validates the isolated bridge network configuration, starts the testbed
# containers, and prints the target IPs you should scan.
#
# Usage:
#   ./scripts/setup-lab-env.sh          # verify + start the lab
#   ./scripts/setup-lab-env.sh down     # stop and remove the lab
#   ./scripts/setup-lab-env.sh status   # show container status
#
# Exit codes: 0 ok | 1 dependency missing | 2 daemon down | 3 compose error
# =============================================================================
set -euo pipefail

# --- Resolve the repo root regardless of where the script is invoked from ----
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

LAB_SUBNET="172.28.0.0/16"
WEB_TARGET_IP="172.28.0.10"
FTP_TARGET_IP="172.28.0.20"

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
die()   { printf '%s[x]%s %s\n'  "${C_RED}" "${C_RST}" "$*" >&2; exit "${2:-1}"; }

# --- Trap so a mid-script failure is reported clearly ------------------------
trap 'die "Aborted at line ${LINENO}. See messages above." 3' ERR

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
    die "Cannot talk to the Docker daemon. Is it running? (try: sudo systemctl start docker)" 2
  fi
  ok "Docker daemon is reachable."
}

require_compose_file() {
  [[ -f "${COMPOSE_FILE}" ]] \
    || die "docker-compose.yml not found at ${COMPOSE_FILE}" 3
  ok "Compose file: ${COMPOSE_FILE}"
}

# --- Validate the isolated bridge subnet before we bind to it ----------------
validate_network() {
  info "Validating lab subnet ${LAB_SUBNET} ..."

  # Warn (do not fail) if the target subnet already exists on another network,
  # which would cause an address-pool overlap on 'up'.
  if docker network ls --format '{{.Name}}' | grep -qx 'pentest-lab-net'; then
    warn "A network named 'pentest-lab-net' already exists; reusing it."
  fi

  # Detect an overlap of 172.28.0.0/16 with any *other* existing docker network.
  local overlap
  overlap="$(docker network inspect $(docker network ls -q) \
      --format '{{.Name}} {{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null \
      | awk '$2=="172.28.0.0/16" && $1!="pentest-lab-net" {print $1}' || true)"
  if [[ -n "${overlap}" ]]; then
    warn "Subnet ${LAB_SUBNET} overlaps existing network(s): ${overlap}"
    warn "Remove/relocate them, or edit docker-compose.yml to a free subnet."
  else
    ok "Subnet ${LAB_SUBNET} is free to allocate."
  fi
}

# --- Actions -----------------------------------------------------------------
lab_up() {
  info "Starting the practice target lab ..."
  docker compose -f "${COMPOSE_FILE}" up -d --build
  ok "Containers requested. Current status:"
  docker compose -f "${COMPOSE_FILE}" ps
  cat <<EOF

${C_GRN}=== Lab is up ===${C_RST}
  web-target   ${WEB_TARGET_IP}   http://${WEB_TARGET_IP}   (host: http://127.0.0.1:8080)
  ftp-service  ${FTP_TARGET_IP}   ftp://${FTP_TARGET_IP}    (host: ftp://127.0.0.1:2121)

Only scan the ${LAB_SUBNET} range. Try:
  nmap -sn ${LAB_SUBNET%/16}.0/24
  nmap -sV -p- ${WEB_TARGET_IP} ${FTP_TARGET_IP}
EOF
}

lab_down() {
  info "Stopping the practice target lab ..."
  docker compose -f "${COMPOSE_FILE}" down
  ok "Lab stopped and containers removed."
}

lab_status() {
  docker compose -f "${COMPOSE_FILE}" ps
}

# --- Entry point -------------------------------------------------------------
main() {
  local action="${1:-up}"
  require_docker
  require_daemon
  require_compose_file

  case "${action}" in
    up)     validate_network; lab_up ;;
    down)   lab_down ;;
    status) lab_status ;;
    *)      die "Unknown action '${action}'. Use: up | down | status" 1 ;;
  esac
}

main "$@"
