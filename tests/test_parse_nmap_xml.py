from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET

import pytest

from conftest import FIXTURES


def hosts_from(parser_mod, name, keep_all_states=False):
    root = ET.parse(FIXTURES / name).getroot()
    return parser_mod.parse_hosts(root, keep_all_states=keep_all_states)


def run_cli(parser_mod, capsys, *argv):
    rc = parser_mod.main(list(argv))
    return rc, capsys.readouterr().out


# --- parsing ---------------------------------------------------------------
def test_real_lab_scan(nmap_parser):
    hosts = hosts_from(nmap_parser, "lab.xml")
    by_addr = {h.address: h for h in hosts}
    assert set(by_addr) == {"10.77.0.10", "10.77.0.20"}
    web = by_addr["10.77.0.10"]
    assert web.status == "up"
    assert [(p.portid, p.protocol, p.service) for p in web.ports] == [(80, "tcp", "http")]
    assert web.ports[0].version_str.startswith("nginx")
    assert by_addr["10.77.0.20"].ports[0].service == "ftp"


def test_address_preference_ignores_element_order(nmap_parser):
    v6 = hosts_from(nmap_parser, "edge.xml")[0]
    assert v6.address == "fd00::10"  # IPv6 beats a MAC listed first


def test_all_hostnames_are_kept(nmap_parser):
    v6 = hosts_from(nmap_parser, "edge.xml")[0]
    assert v6.hostname == "v6-host.lab, alias.lab"


def test_default_keeps_only_open_and_filtered(nmap_parser):
    v6 = hosts_from(nmap_parser, "edge.xml")[0]
    assert [(p.protocol, p.portid, p.state) for p in v6.ports] == [
        ("tcp", 443, "open"),
        ("tcp", 8080, "filtered"),
        ("udp", 53, "open|filtered"),
    ]


def test_all_states_includes_closed(nmap_parser):
    v6 = hosts_from(nmap_parser, "edge.xml", keep_all_states=True)[0]
    assert ("tcp", 22, "closed") in [(p.protocol, p.portid, p.state) for p in v6.ports]


def test_down_host_without_ports_element(nmap_parser):
    down = hosts_from(nmap_parser, "edge.xml")[1]
    assert (down.address, down.status, down.ports) == ("10.77.0.99", "down", [])


# --- table output -------------------------------------------------------------
def test_table_output(nmap_parser, capsys):
    rc, out = run_cli(nmap_parser, capsys, str(FIXTURES / "lab.xml"), "--no-color")
    assert rc == 0
    assert "Nmap results: 2 host(s), 2 up" in out
    assert "Host: 10.77.0.10 (web-target.pentest-lab-net)" in out
    assert "\033[" not in out


def test_table_reports_hosts_with_nothing_open(nmap_parser, capsys):
    _, out = run_cli(nmap_parser, capsys, str(FIXTURES / "edge.xml"), "--no-color")
    assert "(no open/filtered ports reported)" in out


def test_color_columns_stay_aligned(nmap_parser):
    hosts = hosts_from(nmap_parser, "edge.xml")
    plain, colored = io.StringIO(), io.StringIO()
    nmap_parser.render(hosts, nmap_parser.Palette(False), plain)
    nmap_parser.render(hosts, nmap_parser.Palette(True), colored)
    strip = __import__("re").compile(r"\033\[[0-9;]*m")
    assert strip.sub("", colored.getvalue()) == plain.getvalue()


def test_stdin_input(nmap_parser, capsys, monkeypatch):
    data = (FIXTURES / "lab.xml").read_bytes()
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data)))
    rc, out = run_cli(nmap_parser, capsys, "-", "--no-color")
    assert rc == 0 and "10.77.0.20" in out


# --- other formats ---------------------------------------------------------
def test_json_output(nmap_parser, capsys):
    _, out = run_cli(nmap_parser, capsys, str(FIXTURES / "lab.xml"), "--format", "json")
    doc = json.loads(out)
    assert {h["address"] for h in doc} == {"10.77.0.10", "10.77.0.20"}
    assert doc[0]["ports"][0]["port"] in (21, 80)


def test_csv_output(nmap_parser, capsys):
    _, out = run_cli(nmap_parser, capsys, str(FIXTURES / "edge.xml"), "--format", "csv")
    rows = list(csv.DictReader(io.StringIO(out)))
    assert rows[0].keys() >= {"address", "port", "state", "service"}
    assert {r["port"] for r in rows} == {"443", "8080", "53"}


def test_markdown_output_escapes_pipes(nmap_parser, capsys):
    _, out = run_cli(nmap_parser, capsys, str(FIXTURES / "edge.xml"), "--format", "markdown")
    assert "| Port | Proto | State | Service | Product / Version |" in out
    assert "open\\|filtered" in out
    assert "_No open/filtered ports reported._" in out


# --- errors ----------------------------------------------------------------
def test_missing_file(nmap_parser):
    with pytest.raises(SystemExit, match="file not found"):
        nmap_parser.main(["does-not-exist.xml"])


def test_not_xml(nmap_parser, tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("this is not xml")
    with pytest.raises(SystemExit, match="could not parse XML"):
        nmap_parser.main([str(bad)])


def test_not_nmap_xml(nmap_parser, tmp_path):
    other = tmp_path / "other.xml"
    other.write_text("<rss><channel/></rss>")
    with pytest.raises(SystemExit, match="not Nmap XML"):
        nmap_parser.main([str(other)])
