#!/usr/bin/env python3
"""parse-nmap-xml.py: render an Nmap XML report as a terminal table.

Ingests the XML produced by ``nmap -oX <file>`` (or ``-oX -`` to stdout) and
prints, per host, a formatted table of open/ open|filtered ports with their
protocol, state, service name, product, and version.

Standard library only (``xml.etree.ElementTree`` + ``argparse``); no pip
installs required; it runs anywhere Python 3.7+ is available.

Examples
--------
    nmap -sV -oX scan.xml 172.28.0.10 172.28.0.20
    ./scripts/parse-nmap-xml.py scan.xml
    nmap -sV -oX - 172.28.0.10 | ./scripts/parse-nmap-xml.py -
    ./scripts/parse-nmap-xml.py scan.xml --all-states --no-color
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, TextIO


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Port:
    portid: int
    protocol: str
    state: str
    service: str
    product: str
    version: str

    @property
    def version_str(self) -> str:
        """Combine product + version into one human-readable column."""
        parts = [p for p in (self.product, self.version) if p]
        return " ".join(parts)


@dataclass
class Host:
    address: str
    hostname: str
    status: str
    ports: List[Port]


# --------------------------------------------------------------------------- #
# ANSI colour helpers (auto-disabled when not writing to a TTY)
# --------------------------------------------------------------------------- #
class Palette:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def bold(self, t: str) -> str:   return self._wrap("1", t)
    def green(self, t: str) -> str:  return self._wrap("0;32", t)
    def yellow(self, t: str) -> str: return self._wrap("0;33", t)
    def red(self, t: str) -> str:    return self._wrap("0;31", t)
    def blue(self, t: str) -> str:   return self._wrap("0;34", t)

    def state(self, s: str) -> str:
        if s == "open":
            return self.green(s)
        if s.endswith("filtered"):
            return self.yellow(s)
        return self.red(s)


# --------------------------------------------------------------------------- #
# XML parsing
# --------------------------------------------------------------------------- #
def _text(elem: Optional[ET.Element], attr: str, default: str = "") -> str:
    """Safely read an attribute from a possibly-None element."""
    if elem is None:
        return default
    return elem.get(attr, default)


def parse_hosts(root: ET.Element, keep_all_states: bool) -> List[Host]:
    """Walk the <nmaprun> tree and build a list of Host objects."""
    hosts: List[Host] = []

    for host_el in root.findall("host"):
        status = _text(host_el.find("status"), "state", "unknown")

        # Prefer the IPv4 address; fall back to IPv6 or MAC.
        address = ""
        for addr_el in host_el.findall("address"):
            addr_type = addr_el.get("addrtype", "")
            if addr_type == "ipv4":
                address = addr_el.get("addr", "")
                break
            if not address:  # remember first non-ipv4 as a fallback
                address = addr_el.get("addr", "")

        # Hostname, if resolved.
        hostname = ""
        hostnames_el = host_el.find("hostnames")
        if hostnames_el is not None:
            hn = hostnames_el.find("hostname")
            hostname = _text(hn, "name", "")

        ports: List[Port] = []
        ports_el = host_el.find("ports")
        if ports_el is not None:
            for port_el in ports_el.findall("port"):
                state_el = port_el.find("state")
                state = _text(state_el, "state", "unknown")

                # By default only surface actionable ports.
                if not keep_all_states and not (
                    state == "open" or state.endswith("filtered")
                ):
                    continue

                svc_el = port_el.find("service")
                ports.append(
                    Port(
                        portid=int(port_el.get("portid", "0")),
                        protocol=port_el.get("protocol", ""),
                        state=state,
                        service=_text(svc_el, "name", ""),
                        product=_text(svc_el, "product", ""),
                        version=_text(svc_el, "version", ""),
                    )
                )

        ports.sort(key=lambda p: (p.protocol, p.portid))
        hosts.append(Host(address=address, hostname=hostname,
                          status=status, ports=ports))
    return hosts


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(hosts: List[Host], pal: Palette, out: TextIO) -> None:
    if not hosts:
        print("No hosts found in the Nmap XML.", file=out)
        return

    headers = ("PORT", "PROTO", "STATE", "SERVICE", "PRODUCT / VERSION")
    up_hosts = [h for h in hosts if h.status == "up"]
    print(pal.bold(f"\nNmap results: {len(hosts)} host(s), "
                   f"{len(up_hosts)} up\n"), file=out)

    for host in hosts:
        label = host.address or "(unknown address)"
        if host.hostname:
            label += f" ({host.hostname})"
        status_str = (pal.green(host.status) if host.status == "up"
                      else pal.red(host.status))
        print(pal.blue("=" * 64), file=out)
        print(f"{pal.bold('Host:')} {label}   {pal.bold('Status:')} {status_str}",
              file=out)
        print(pal.blue("=" * 64), file=out)

        if not host.ports:
            print("  (no open/filtered ports reported)\n", file=out)
            continue

        # Compute column widths from the data so the table always lines up.
        rows = [
            (
                str(p.portid),
                p.protocol,
                p.state,
                p.service,
                p.version_str,
            )
            for p in host.ports
        ]
        widths = [
            max(len(headers[i]), *(len(r[i]) for r in rows))
            for i in range(len(headers))
        ]

        header_line = "  ".join(
            pal.bold(headers[i].ljust(widths[i])) for i in range(len(headers))
        )
        print("  " + header_line, file=out)
        print("  " + "  ".join("-" * widths[i] for i in range(len(headers))),
              file=out)

        for p, r in zip(host.ports, rows):
            cells = [
                r[0].ljust(widths[0]),
                r[1].ljust(widths[1]),
                pal.state(r[2]).ljust(widths[2] + (len(pal.state(r[2])) - len(r[2]))),
                r[3].ljust(widths[3]),
                r[4].ljust(widths[4]),
            ]
            print("  " + "  ".join(cells), file=out)
        print("", file=out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render an Nmap -oX XML report as a terminal table.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "xml",
        help="Path to the Nmap XML file, or '-' to read from stdin.",
    )
    parser.add_argument(
        "--all-states",
        action="store_true",
        help="Include closed/filtered ports (default: open + *filtered only).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colour output.",
    )
    return parser


def load_xml(path: str) -> ET.Element:
    """Parse XML from a file path or stdin ('-'), returning the root element."""
    try:
        if path == "-":
            data = sys.stdin.buffer.read()
            return ET.fromstring(data)
        tree = ET.parse(path)
        return tree.getroot()
    except FileNotFoundError:
        sys.exit(f"error: file not found: {path}")
    except ET.ParseError as exc:
        sys.exit(f"error: could not parse XML ({exc}). "
                 f"Was it produced with 'nmap -oX'?")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = load_xml(args.xml)

    if root.tag != "nmaprun":
        sys.exit("error: root element is not <nmaprun>; this is not Nmap XML.")

    hosts = parse_hosts(root, keep_all_states=args.all_states)

    color_enabled = (not args.no_color) and sys.stdout.isatty()
    render(hosts, Palette(color_enabled), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
