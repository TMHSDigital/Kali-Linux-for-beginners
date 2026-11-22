# attacker: a slim Kali box that sits ON the lab network (10.77.0.5), so the
# curriculum works the same everywhere, including Docker Desktop on Windows and
# macOS, where the lab's bridge IPs are not reachable from the host.
#
#   ./scripts/setup-lab-env.sh shell     # start it and drop into bash
FROM kalilinux/kali-rolling@sha256:1ff4a2be3849333687b3ed2b31bb5af0cd1b7c0a11ec7713feb5abe5a6b2795c

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      nmap tshark tcpdump ftp curl wget dnsutils iproute2 iputils-ping \
      netcat-openbsd python3 ca-certificates less nano man-db sudo \
      procps openssh-server \
 && rm -rf /var/lib/apt/lists/*

# Modules 01 and 02 teach the difference between a normal user and root, so the
# box also has the same non-root account a Kali VM ships with: kali/kali, in the
# sudo group. `./scripts/setup-lab-env.sh user-shell` logs in as kali; `shell`
# stays root for the scanning and capture modules.
RUN useradd -m -s /bin/bash -G sudo kali \
 && echo 'kali:kali' | chpasswd

# The repo is mounted read-only at /lab (scripts live in /lab/scripts) and a
# writable scratch dir at /root/work for scans and captures.
ENV PATH="/lab/scripts:${PATH}"
WORKDIR /root/work
CMD ["sleep", "infinity"]
