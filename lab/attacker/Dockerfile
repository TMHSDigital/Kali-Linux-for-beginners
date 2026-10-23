# attacker: a slim Kali box that sits ON the lab network (10.77.0.5), so the
# curriculum works the same everywhere, including Docker Desktop on Windows and
# macOS, where the lab's bridge IPs are not reachable from the host.
#
#   ./scripts/setup-lab-env.sh shell     # start it and drop into bash
FROM kalilinux/kali-rolling@sha256:4be87f78671419c13dcf4f207ead1cfc0de178ea281b3f69c0f49b69ba4e79b1

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nmap tshark tcpdump ftp curl wget dnsutils iproute2 iputils-ping \
      netcat-openbsd python3 ca-certificates less nano man-db sudo \
 && rm -rf /var/lib/apt/lists/*

# The repo is mounted read-only at /lab (scripts live in /lab/scripts) and a
# writable scratch dir at /root/work for scans and captures.
ENV PATH="/lab/scripts:${PATH}"
WORKDIR /root/work
CMD ["sleep", "infinity"]
