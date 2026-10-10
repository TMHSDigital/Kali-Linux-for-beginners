from __future__ import annotations

import json
import re

import pytest

from conftest import REPO_ROOT


# --- pure helpers ------------------------------------------------------------
@pytest.mark.parametrize("text, expected", [
    ("Hello World", "hello-world"),
    ("1. Host discovery: who's alive?", "1-host-discovery-whos-alive"),
    ("03: Network Recon & Nmap", "03-network-recon--nmap"),
    ("`-sS` SYN scan", "-ss-syn-scan"),
    ("Under_score kept", "under_score-kept"),
])
def test_github_slug(site_builder, text, expected):
    assert site_builder.github_slug(text, {}) == expected


def test_github_slug_dedupes_like_github(site_builder):
    seen = {}
    assert [site_builder.github_slug("Setup", seen) for _ in range(3)] == ["setup", "setup-1", "setup-2"]


@pytest.mark.parametrize("rel, url", [
    ("README.md", "overview/"),
    ("03-network-recon-and-nmap/README.md", "03-network-recon-and-nmap/"),
    ("03-network-recon-and-nmap/scan-profiles.md", "03-network-recon-and-nmap/scan-profiles/"),
    ("cheatsheets/01-kali-survival-commands.md", "cheatsheets/01-kali-survival-commands/"),
])
def test_page_url(site_builder, rel, url):
    assert site_builder.page_url(rel) == url


@pytest.mark.parametrize("src, dst, expected", [
    ("03-a/", "03-a/b/", "b/"),
    ("03-a/b/", "05-c/", "../../05-c/"),
    ("", "03-a/", "03-a/"),
    ("03-a/", "", "../"),
    ("03-a/", "03-a/", "./"),
])
def test_rel_href(site_builder, src, dst, expected):
    assert site_builder.rel_href(src, dst) == expected


def test_split_title(site_builder):
    assert site_builder.split_title("03: Recon `[Level 2: Reconnaissance]`") == (
        "03: Recon", "Level 2: Reconnaissance")
    assert site_builder.split_title("Plain title") == ("Plain title", "")


# --- a full build of a small fixture repo -------------------------------------
@pytest.fixture()
def built(site_builder, tmp_path):
    repo = tmp_path / "repo"
    (repo / "01-first-module").mkdir(parents=True)
    (repo / "02-second-module").mkdir()
    (repo / "cheatsheets").mkdir()
    (repo / "scripts").mkdir()
    (repo / "README.md").write_text("# Project\n\nIntro paragraph.\n")
    (repo / "CLAUDE.md").write_text("# Internal\n")
    (repo / "01-first-module" / "README.md").write_text(
        "# 01: First Module `[Level 0: Basics]`\n<!-- time: ~2 hours -->\n\n"
        "The first module teaches basics.\n\n"
        "## Setup\n\nSee [the labs](lab-exercises.md), [section](#setup-1), "
        "[module 2](../02-second-module/), [deep](../02-second-module/README.md#usage) "
        "and [the script](../scripts/tool.py).\n\n## Setup\n\n"
        "| Left | Right |\n|:-----|------:|\n| a | b |\n\n"
        "```bash\nnmap -sV 10.77.0.10\n```\n\n<script>alert(1)</script>\n")
    (repo / "01-first-module" / "lab-exercises.md").write_text("# Lab Exercises\n\nDo things.\n")
    (repo / "02-second-module" / "README.md").write_text("# 02: Second\n\n## Usage\n\nText.\n")
    (repo / "cheatsheets" / "nmap.md").write_text("# Nmap Cheats\n\n`-sS` stealth.\n")
    (repo / "scripts" / "tool.py").write_text("print('hi')\n")

    site_src = REPO_ROOT / "site"
    out = tmp_path / "_site"
    result = site_builder.build(repo, out, site_src)
    return out, result


def read(out, rel):
    return (out / rel).read_text(encoding="utf-8")


def test_sections_and_ordering(built):
    _, result = built
    titles = [s["title"] for s in result["sections"]]
    assert titles == ["Start here", "01. First Module", "02. Second", "Cheatsheets"]
    first = result["sections"][1]["items"]
    assert [i["path"] for i in first] == ["01-first-module/README.md", "01-first-module/lab-exercises.md"]
    assert first[0]["level"] == "Level 0: Basics" and first[0]["time"] == "~2 hours"


def test_internal_files_excluded(built):
    out, result = built
    assert all("CLAUDE" not in d["path"] for d in result["docs"])
    assert not list(out.rglob("CLAUDE*"))


def test_pages_written_at_pretty_urls(built):
    out, _ = built
    for rel in ["index.html", "overview/index.html", "01-first-module/index.html",
                "01-first-module/lab-exercises/index.html", "cheatsheets/nmap/index.html",
                "404.html", "sitemap.xml", "robots.txt", "search-index.json", "assets/pygments.css"]:
        assert (out / rel).is_file(), rel


def test_links_rewritten(built):
    page = read(built[0], "01-first-module/index.html")
    assert 'href="lab-exercises/"' in page
    assert 'href="#setup-1"' in page
    assert 'href="../02-second-module/"' in page
    assert 'href="../02-second-module/#usage"' in page
    assert "github.com/TMHSDigital/Kali-Linux-for-beginners/blob/main/scripts/tool.py" in page


def test_heading_ids_match_github_and_dedupe(built):
    page = read(built[0], "01-first-module/index.html")
    assert 'id="setup"' in page and 'id="setup-1"' in page
    assert 'class="anchor" href="#setup"' in page


def test_level_tag_moves_from_h1_to_badge(built):
    page = read(built[0], "01-first-module/index.html")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page).group(1)
    assert "Level" not in h1
    assert '<span class="badge">Level 0: Basics</span>' in page


def test_csp_and_no_third_party_scripts(built):
    page = read(built[0], "01-first-module/index.html")
    assert "Content-Security-Policy" in page and "script-src 'self'" in page
    for src in re.findall(r'<script src="([^"]+)"', page):
        assert not src.startswith(("http:", "https:", "//")), src
    # Table alignment must not use inline styles (the CSP blocks them).
    assert 'style="text-align' not in page and 'class="align-right"' in page


def test_code_is_highlighted_at_build_time(built):
    page = read(built[0], "01-first-module/index.html")
    assert '<pre class="highlight"><code class="language-bash">' in page
    assert "<span" in page.split('language-bash">', 1)[1].split("</code>", 1)[0]


def test_seo_metadata(built):
    page = read(built[0], "01-first-module/index.html")
    assert "<title>01: First Module | Kali Linux for Beginners</title>" in page
    assert '<meta name="description" content="The first module teaches basics.">' in page
    assert ('<link rel="canonical" href="https://tmhsdigital.github.io/Kali-Linux-for-beginners/'
            '01-first-module/">') in page
    assert 'property="og:image"' in page
    sitemap = read(built[0], "sitemap.xml")
    assert sitemap.count("<url>") == 6  # landing + 5 docs


def test_search_index(built):
    data = json.loads(read(built[0], "search-index.json"))
    entry = next(d for d in data if d["url"] == "01-first-module/")
    assert "nmap -sV 10.77.0.10" in entry["text"]
    assert {"id": "setup", "text": "Setup"} in entry["headings"]


def test_404_uses_absolute_asset_paths(built):
    page = read(built[0], "404.html")
    assert 'href="/Kali-Linux-for-beginners/assets/styles.css"' in page


def test_service_worker_gets_build_id(built):
    assert "__BUILD_ID__" not in read(built[0], "sw.js")


def test_real_repo_builds(site_builder, tmp_path):
    result = site_builder.build(REPO_ROOT, tmp_path / "_site", REPO_ROOT / "site")
    assert len(result["docs"]) >= 15
    assert any(s["id"] == "cheatsheets" for s in result["sections"])


def test_code_blocks_get_header_bar(built):
    out, _ = built
    page = read(out, "01-first-module/index.html")
    assert '<div class="codeblock" data-lang="bash"><div class="codeblock-bar">' in page
    assert page.count('class="codeblock"') == 1


def test_toc_and_level_badges(built):
    out, _ = built
    page = read(out, "01-first-module/index.html")
    assert '<aside class="toc"' in page and 'href="#setup-1"' in page
    assert '<div class="doc-badges" data-level="0">' in page
    # A page with fewer than two headings gets no outline.
    assert '<aside class="toc"' not in read(out, "cheatsheets/nmap/index.html")


def test_tables_wrapped_for_scrolling(built):
    out, _ = built
    assert '<div class="table-wrap"><table>' in read(out, "01-first-module/index.html")


def test_github_alerts_become_callouts(site_builder, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# P\n\n> [!WARNING]\n> **Careful.** Lab only.\n\n> **Note:** plain.\n")
    out = tmp_path / "_site"
    site_builder.build(repo, out, REPO_ROOT / "site")
    page = read(out, "overview/index.html")
    assert '<blockquote class="callout callout-warn">\n<p><strong>Careful.' in page
    assert "[!WARNING]" not in page
    assert '<blockquote class="callout callout-note">' in page


def test_landing_page_module_list(built):
    out, _ = built
    page = read(out, "index.html")
    assert page.count('<li class="module" data-level=') == 2
    assert '<li class="module" data-level="0" data-section="01-first-module">' in page
    assert "about 2 hours" in page
    assert "10.77.0.5" in page and 'class="terminal"' in page


def test_nav_drops_repeated_module_names(built):
    out, _ = built
    page = read(out, "01-first-module/index.html")
    # The module README is "Overview" under its numbered heading, not the title again.
    assert '<h3><span class="nav-num">01</span>' in page
    assert '<span class="done-mark" aria-hidden="true"></span>Overview</a>' in page


def test_inline_level_tags_become_labels(site_builder, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# P\n\n## Scan `[Level 2+: Advanced / Field Ops]`\n\nText.\n")
    out = tmp_path / "_site"
    site_builder.build(repo, out, REPO_ROOT / "site")
    page = read(out, "overview/index.html")
    assert '<span class="level-tag" data-level="2">Level 2+: Advanced / Field Ops</span>' in page
