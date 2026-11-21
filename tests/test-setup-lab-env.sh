#!/usr/bin/env bash
# =============================================================================
# test-setup-lab-env.sh: unit tests for the subnet guard in setup-lab-env.sh.
# Needs no Docker: it sources the script for its functions and stubs `docker`.
#
#   bash tests/test-setup-lab-env.sh
# =============================================================================
# shellcheck disable=SC1091  # sourced at run time; CI runs shellcheck without -x
source "$(dirname -- "${BASH_SOURCE[0]}")/../scripts/setup-lab-env.sh"
# The script turns on errexit and an ERR trap; a test runner must survive failures.
set +eE
trap - ERR

FAILS=0
expect() {  # expect <exit code> "<description>" <command...>
  local want="$1" desc="$2"; shift 2
  "$@" >/dev/null 2>&1
  local got=$?
  if [[ "${got}" == "${want}" ]]; then
    printf '  PASS  %s\n' "${desc}"
  else
    printf '  FAIL  %s (exit %s, wanted %s)\n' "${desc}" "${got}" "${want}"
    FAILS=$((FAILS + 1))
  fi
}

echo "== cidr_overlaps"
expect 0 "same /24 overlaps"                cidr_overlaps 10.77.0.0/24 10.77.0.0/24
expect 0 "a containing /16 overlaps"        cidr_overlaps 10.77.0.0/24 10.77.0.0/16
expect 0 "a containing /8 overlaps"         cidr_overlaps 10.77.0.0/24 10.0.0.0/8
expect 0 "0.0.0.0/0 overlaps everything"    cidr_overlaps 10.77.0.0/24 0.0.0.0/0
expect 0 "a smaller subnet inside overlaps" cidr_overlaps 10.77.0.0/24 10.77.0.128/25
expect 1 "the next /24 does not overlap"    cidr_overlaps 10.77.0.0/24 10.78.0.0/24
expect 1 "Docker's default bridge does not" cidr_overlaps 10.77.0.0/24 172.17.0.0/16
expect 1 "an IPv6 subnet never overlaps"    cidr_overlaps 10.77.0.0/24 fd00::/64

echo "== validate_network (docker stubbed)"
NETWORKS=""
docker() {  # just enough of the docker CLI for other_subnets and validate_network
  case "$1 $2" in
    "network ls") if [[ "$*" == *--format* ]]; then awk '{print $1}' <<<"${NETWORKS}"; else
                    [[ -n "${NETWORKS}" ]] && awk '{print "id-" $1}' <<<"${NETWORKS}"; fi ;;
    "network inspect") printf '%s\n' "${NETWORKS}" ;;
  esac
}
validate() { ( validate_network ); }   # die() exits, so run it in a subshell

NETWORKS=$'bridge 172.17.0.0/16\nhost'
expect 0 "no conflict with the default networks" validate
NETWORKS=$'bridge 172.17.0.0/16\npentest-lab-net 10.77.0.0/24'
expect 0 "the lab's own network is not a conflict" validate
NETWORKS=$'bridge 172.17.0.0/16\nmy-vpn-net 10.77.0.0/16'
expect 4 "an overlapping network exits 4" validate
NETWORKS=$'dual 192.168.50.0/24 fd00:1::/64'
expect 0 "a dual-stack network outside the range passes" validate

echo
if (( FAILS )); then echo "${FAILS} test(s) failed."; exit 1; fi
echo "All setup-lab-env tests passed."
