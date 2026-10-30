# attacker: a slim Kali box that sits ON the lab network (10.77.0.5), so the
# curriculum works the same everywhere, including Docker Desktop on Windows and
# macOS, where the lab's bridge IPs are not reachable from the host.
#
#   ./scripts/setup-lab-env.sh shell     # start it and drop into bash
FROM kalilinux/kali-rolling@sha256:ea20024e16833dab1a5337f5998602f3b81f8a38f3b0995dda272c83a1b0c1b9

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
