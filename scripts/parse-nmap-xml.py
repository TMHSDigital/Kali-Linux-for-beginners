#!/usr/bin/env python3
"""parse-nmap-xml.py: render an Nmap XML report as a terminal table.

Ingests the XML produced by ``nmap -oX <file>`` (or ``-oX -`` to stdout) and
prints, per host, a formatted table of open/ open|filtered ports with their
protocol, state, service name, product, and version, plus any NSE script
results (``-sC``, ``--script``). ``--format`` switches the
output to Markdown (paste straight into a report), CSV, or JSON.

Standard library only (``xml.etree.ElementTree`` + ``argparse``); no pip
installs required; it runs anywhere Python 3.8+ is available.

Examples
--------
    nmap -sV -oX scan.xml 10.77.0.10 10.77.0.20
    ./scripts/parse-nmap-xml.py scan.xml
    nmap -sV -oX - 10.77.0.10 | ./scripts/parse-nmap-xml.py -
    ./scripts/parse-nmap-xml.py scan.xml --all-states --no-color
    ./scripts/parse-nmap-xml.py scan.xml --format markdown >> findings.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import xml.etree.ElementTree as ET
import re
from dataclasses import dataclass, field
from typing import List, Optional, TextIO, Tuple

# An NSE script result: (script id, output text). Script output is untrusted
# scan data, so control characters are stripped before it is printed.
Script = Tuple[str, str]
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


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
    scripts: List[Script] = field(default_factory=list)

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
    scripts: List[Script] = field(default_factory=list)


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


def _scripts(parent: Optional[ET.Element]) -> List[Script]:
    """The <script id=... output=...> children of a <port> or <hostscript>."""
    if parent is None:
        return []
    return [(el.get("id", ""), _CONTROL_RE.sub("", el.get("output", "")).strip("\n"))
            for el in parent.findall("script")]


def parse_hosts(root: ET.Element, keep_all_states: bool) -> List[Host]:
    """Walk the <nmaprun> tree and build a list of Host objects."""
    hosts: List[Host] = []

    for host_el in root.findall("host"):
        status = _text(host_el.find("status"), "state", "unknown")

        # Prefer IPv4, then IPv6, then MAC, regardless of element order.
        by_type = {}
        for addr_el in host_el.findall("address"):
            by_type.setdefault(addr_el.get("addrtype", ""), addr_el.get("addr", ""))
        address = next(
            (by_type[t] for t in ("ipv4", "ipv6", "mac") if by_type.get(t)),
            next(iter(by_type.values()), ""),
        )

        # Every resolved hostname (PTR, user-supplied, ...), comma-separated.
        names = [hn.get("name", "") for hn in host_el.findall("hostnames/hostname")]
        hostname = ", ".join(n for n in names if n)

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

                try:
                    portid = int(port_el.get("portid", "0"))
                except ValueError:
                    print(f"warning: skipping port with invalid portid "
                          f"{port_el.get('portid')!r} on {address}", file=sys.stderr)
                    continue

                svc_el = port_el.find("service")
                ports.append(
                    Port(
                        portid=portid,
                        protocol=port_el.get("protocol", ""),
                        state=state,
                        service=_text(svc_el, "name", ""),
                        product=_text(svc_el, "product", ""),
                        version=_text(svc_el, "version", ""),
                        scripts=_scripts(port_el),
                    )
                )

        ports.sort(key=lambda p: (p.protocol, p.portid))
        hosts.append(Host(address=address, hostname=hostname,
                          status=status, ports=ports,
                          scripts=_scripts(host_el.find("hostscript"))))
    return hosts


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def script_lines(scripts: List[Script]) -> List[str]:
    """Nmap's own layout: '| id: line', '|   more', and '|_' on the last line."""
    lines: List[str] = []
    for sid, output in scripts:
        body = output.splitlines() or [""]
        chunk = [f"{sid}: {body[0].strip()}".rstrip()] + body[1:]
        lines += ["| " + line for line in chunk[:-1]] + ["|_" + chunk[-1]]
    return lines


def script_summary(scripts: List[Script]) -> str:
    """All script results on one line (for CSV cells)."""
    return "; ".join(f"{sid}: " + " / ".join(ln.strip() for ln in out.splitlines() if ln.strip())
                     for sid, out in scripts)


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
            print("  (no open/filtered ports reported)", file=out)
            for line in script_lines(host.scripts):
                print("  " + line, file=out)
            print("", file=out)
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
            for line in script_lines(p.scripts):
                print("  " + line, file=out)
        if host.scripts:
            print("\n  " + pal.bold("Host script results:"), file=out)
            for line in script_lines(host.scripts):
                print("  " + line, file=out)
        print("", file=out)


def _flat_rows(hosts: List[Host]) -> List[dict]:
    """One dict per (host, port), the shape shared by CSV and JSON output."""
    return [
        {
            "address": h.address, "hostname": h.hostname, "status": h.status,
            "port": p.portid, "protocol": p.protocol, "state": p.state,
            "service": p.service, "product": p.product, "version": p.version,
            "scripts": script_summary(p.scripts),
        }
        for h in hosts for p in h.ports
    ]


def render_json(hosts: List[Host], out: TextIO) -> None:
    doc = [
        {
            "address": h.address, "hostname": h.hostname, "status": h.status,
            "ports": [
                {"port": p.portid, "protocol": p.protocol, "state": p.state,
                 "service": p.service, "product": p.product, "version": p.version,
                 "scripts": [{"id": sid, "output": o} for sid, o in p.scripts]}
                for p in h.ports
            ],
            "scripts": [{"id": sid, "output": o} for sid, o in h.scripts],
        }
        for h in hosts
    ]
    json.dump(doc, out, indent=2)
    out.write("\n")


def render_csv(hosts: List[Host], out: TextIO) -> None:
    fields = ["address", "hostname", "status", "port", "protocol", "state",
              "service", "product", "version", "scripts"]
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(_flat_rows(hosts))


def render_markdown(hosts: List[Host], out: TextIO) -> None:
    """A Markdown table per host, ready to paste into a findings report."""
    def cell(s: str) -> str:
        return s.replace("|", "\\|")

    for host in hosts:
        label = host.address or "(unknown address)"
        if host.hostname:
            label += f" ({host.hostname})"
        print(f"### {cell(label)} ({host.status})\n", file=out)
        if not host.ports:
            print("_No open/filtered ports reported._\n", file=out)
        else:
            print("| Port | Proto | State | Service | Product / Version |", file=out)
            print("|------|-------|-------|---------|-------------------|", file=out)
            for p in host.ports:
                print(f"| {p.portid} | {p.protocol} | {cell(p.state)} | "
                      f"{cell(p.service)} | {cell(p.version_str)} |", file=out)
            print("", file=out)
        # Script output is multi-line, so it goes in a code block after the table.
        entries = [(f"{p.portid}/{p.protocol}", sc) for p in host.ports for sc in p.scripts]
        entries += [("host", sc) for sc in host.scripts]
        if entries:
            text = "\n".join(f"{where} {ln}" if i == 0 else f"{' ' * len(where)} {ln}"
                             for where, sc in entries for i, ln in enumerate(script_lines([sc])))
            fence = "`" * max(3, 1 + max((len(m) for m in re.findall(r"`+", text)), default=0))
            print(f"Script output:\n\n{fence}text\n{text}\n{fence}\n", file=out)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
EPILOG = """examples:
  # pipe a scan straight in ('-' reads stdin)
  nmap -sV -oX - 10.77.0.10 | parse-nmap-xml.py -

  # read a saved scan, including closed ports
  nmap -sV -oX scan.xml 10.77.0.10 10.77.0.20
  parse-nmap-xml.py scan.xml --all-states

  # append a Markdown table to your report, or export CSV / JSON
  parse-nmap-xml.py scan.xml --format markdown >> findings.md
  parse-nmap-xml.py scan.xml --format csv > scan.csv
  parse-nmap-xml.py scan.xml --format json
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render an Nmap -oX XML report as a terminal table.",
        epilog=EPILOG,
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
    parser.add_argument(
        "--format",
        choices=("table", "markdown", "csv", "json"),
        default="table",
        help="Output format (default: table).",
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
    except OSError as exc:  # a directory, no permission, ...
        sys.exit(f"error: cannot read {path}: {exc.strerror or exc}")
    except ET.ParseError as exc:
        sys.exit(f"error: could not parse XML ({exc}). "
                 f"Was it produced with 'nmap -oX'?")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Scan data can hold characters the console code page lacks (cp1252 on
    # Windows); print a replacement character instead of crashing.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="replace")
    root = load_xml(args.xml)

    if root.tag != "nmaprun":
        sys.exit("error: root element is not <nmaprun>; this is not Nmap XML.")

    hosts = parse_hosts(root, keep_all_states=args.all_states)

    if args.format == "json":
        render_json(hosts, sys.stdout)
    elif args.format == "csv":
        render_csv(hosts, sys.stdout)
    elif args.format == "markdown":
        render_markdown(hosts, sys.stdout)
    else:
        color_enabled = (not args.no_color) and sys.stdout.isatty()
        render(hosts, Palette(color_enabled), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
