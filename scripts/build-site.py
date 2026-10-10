#!/usr/bin/env python3
"""build-site.py: generate the GitHub Pages site from the repo content.

Nothing about the navigation is hardcoded. The script walks the repository,
discovers every Markdown file, groups them into sections by top-level
directory, derives titles from each file's first ``# heading``, and renders
every page to static HTML at build time:

  _site/
    index.html                   landing page (module cards)
    overview/index.html          the root README
    <module>/index.html          each module's README
    <module>/<doc>/index.html    every other Markdown file
    search-index.json            full-text search data (loaded on demand)
    manifest.json                navigation tree (for tooling)
    sitemap.xml, robots.txt, 404.html, sw.js, assets/...

Static pages mean real, crawlable URLs with their own titles, descriptions,
and link previews; no client-side Markdown rendering and no third-party
scripts, so the Content-Security-Policy can be ``script-src 'self'``.

Add a module directory or a cheatsheet, push, and it appears automatically.

Usage:
    pip install -r requirements-dev.txt
    python scripts/build-site.py [--out _site]
"""
from __future__ import annotations

import argparse
import html
import json
import posixpath
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.token import Token
from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

# Repo root = parent of this script's directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = REPO_ROOT / "site"

SITE_TITLE = "Kali Linux for Beginners"
SITE_TAGLINE = ("A free, hands-on path from your first shell command to capturing "
                "credentials off the wire, with a safe practice lab that runs on your laptop.")
SITE_URL = "https://tmhsdigital.github.io/Kali-Linux-for-beginners/"
REPO = "TMHSDigital/Kali-Linux-for-beginners"
BRANCH = "main"

# Directories we never surface in the docs site.
EXCLUDE_DIRS = {
    ".git", ".github", "_site", "site", "node_modules", "tests", "workspace",
    ".venv", "venv", "__pycache__", ".lab", ".pytest_cache", ".ruff_cache",
}
# Individual files to skip (internal / not curriculum content).
EXCLUDE_FILES = {"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "CHANGELOG.md"}

H1_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)
LEVEL_RE = re.compile(r"\s*`\[(Level[^\]]*)\]`\s*$")
TIME_RE = re.compile(r"<!--\s*time:\s*(.+?)\s*-->")
# The practice lab from docker-compose.yml, shown on the landing page.
LAB_HOSTS = [
    ("attacker", "10.77.0.5", "Kali toolbox", "nmap, tshark, tcpdump, ftp, curl. You run every module from here."),
    ("web-target", "10.77.0.10", "nginx, plain HTTP", "A login form that sends credentials in cleartext."),
    ("ftp-service", "10.77.0.20", "vsftpd", "Anonymous and labuser/labpass logins, all cleartext."),
]
# What each module leaves you able to do (keep in step with the README's curriculum table).
MODULE_OUTCOMES = {
    "01": "Navigate, inspect, and manipulate Linux from the shell; use pipes and redirection.",
    "02": "Read the Unix privilege model; audit SUID and sudo for escalation surface.",
    "03": "Map a network and choose the right scan for stealth, speed, or depth.",
    "04": "Capture and crack a WPA2 handshake in a lab; understand WPA3 and PMF defenses.",
    "05": "Reassemble sessions, extract cleartext credentials, and describe the fix.",
}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; "
       "img-src 'self' data: https:; connect-src 'self'; font-src 'self'; "
       "object-src 'none'; base-uri 'self'; form-action 'none'")


# --------------------------------------------------------------------------- #
# Titles, slugs, URLs
# --------------------------------------------------------------------------- #
def prettify(name: str) -> str:
    """Turn a slug like '03-network-recon-and-nmap' into a readable title."""
    stem = re.sub(r"^\d+[-_]", "", name)
    words = re.split(r"[-_]+", stem)
    return " ".join(w.capitalize() for w in words if w)


def section_title(dir_name: str) -> str:
    """Section heading: keep the numeric prefix as a badge-friendly label."""
    m = re.match(r"^(\d+)[-_](.*)$", dir_name)
    if m:
        return f"{m.group(1)}. {prettify(m.group(2))}"
    return prettify(dir_name)


def split_title(heading: str) -> Tuple[str, str]:
    """'03: Recon `[Level 2: Recon]`' -> ('03: Recon', 'Level 2: Recon')."""
    m = LEVEL_RE.search(heading)
    level = m.group(1) if m else ""
    title = LEVEL_RE.sub("", heading).replace("`", "").strip()
    return title, level


def github_slug(text: str, seen: Dict[str, int]) -> str:
    """GitHub's heading-anchor algorithm (github-slugger), with de-duplication.

    Lowercase, drop everything except letters, digits, spaces, '-' and '_',
    turn each space into '-', then append -1, -2, ... to repeats.
    """
    slug = re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")
    if slug in seen:
        seen[slug] += 1
        candidate = f"{slug}-{seen[slug]}"
        while candidate in seen:
            seen[slug] += 1
            candidate = f"{slug}-{seen[slug]}"
        seen[candidate] = 0
        return candidate
    seen[slug] = 0
    return slug


def page_url(rel_md: str) -> str:
    """Site URL (relative to the site root, trailing slash) for a Markdown path."""
    parts = rel_md.split("/")
    stem = parts[-1][:-3] if parts[-1].lower().endswith(".md") else parts[-1]
    if len(parts) == 1:
        return "overview/" if stem.lower() == "readme" else f"{stem}/"
    base = "/".join(parts[:-1])
    return f"{base}/" if stem.lower() == "readme" else f"{base}/{stem}/"


def rel_href(from_url: str, to_url: str) -> str:
    """Relative link between two site URLs ('' is the site root)."""
    start = from_url.rstrip("/") or "."
    target = to_url.rstrip("/") or "."
    rel = posixpath.relpath(target, start)
    if rel == ".":
        return "./"
    return rel + ("/" if to_url.endswith("/") or to_url == "" else "")


def root_prefix(url: str) -> str:
    depth = url.count("/")
    return "../" * depth if depth else "./"


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def doc_entry(md: Path, repo: Path) -> Dict:
    rel = md.relative_to(repo).as_posix()
    text = read_text(md)
    m = H1_RE.search(text)
    if m:
        title, level = split_title(m.group(1))
    else:
        title, level = ("Overview" if md.stem.lower() == "readme" else prettify(md.stem)), ""
    if rel.lower() == "readme.md":
        title = "Overview"
    t = TIME_RE.search(text)
    return {"title": title, "level": level, "time": t.group(1) if t else "",
            "path": rel, "url": page_url(rel)}


def sort_items(items: List[Dict]) -> List[Dict]:
    """README/overview first, then alphabetical by path."""
    def key(it: Dict):
        name = Path(it["path"]).name.lower()
        return (0 if name == "readme.md" else 1, it["path"].lower())
    return sorted(items, key=key)


def discover(repo: Path) -> List[Dict]:
    """Build the ordered list of sections with their Markdown items."""
    root_items: List[Dict] = []
    dir_sections: Dict[str, Dict] = {}

    for md in repo.rglob("*.md"):
        rel_parts = md.relative_to(repo).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts) or md.name in EXCLUDE_FILES:
            continue
        entry = doc_entry(md, repo)
        if len(rel_parts) == 1:
            root_items.append(entry)
        else:
            top = rel_parts[0]
            sec = dir_sections.setdefault(
                top, {"id": top, "title": section_title(top), "items": []}
            )
            sec["items"].append(entry)

    sections: List[Dict] = []
    if root_items:
        sections.append({"id": "home", "title": "Start here", "items": sort_items(root_items)})
    # Numeric-prefixed dirs first (in numeric order), then the rest alphabetically.
    for key in sorted(dir_sections, key=lambda d: (0, d) if re.match(r"^\d", d) else (1, d)):
        sec = dir_sections[key]
        sec["items"] = sort_items(sec["items"])
        # A module README's own heading ("03: Network Recon & Nmap") beats a
        # title-cased slug ("Network Recon And Nmap").
        lead = sec["items"][0]
        m = re.match(r"^(\d+)[:.]\s*(.+)$", lead["title"])
        if lead["path"].lower().endswith("/readme.md") and m:
            sec["title"] = f"{m.group(1)}. {m.group(2)}"
        sections.append(sec)
    return sections


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
_FORMATTER = HtmlFormatter(nowrap=True)


def highlight_code(code: str, lang: str, _attrs) -> str:
    lang = (lang or "").strip().split()[0] if lang else ""
    cls = f' class="language-{html.escape(lang)}"' if lang else ""
    body = html.escape(code)
    if lang and lang not in ("text", "txt", "plain"):
        try:
            body = pyg_highlight(code, get_lexer_by_name(lang), _FORMATTER)
        except ClassNotFound:
            pass
    return f'<pre class="highlight"><code{cls}>{body}</code></pre>'


def make_md() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "highlight": highlight_code})
    md.enable(["table", "strikethrough"])
    return md


class Renderer:
    """Renders one repo's Markdown with build-time link and anchor rewriting."""

    def __init__(self, repo: Path, docs: Dict[str, Dict]):
        self.repo = repo
        self.docs = docs          # rel md path -> entry
        self.md = make_md()

    def resolve(self, from_rel: str, href: str, from_url: str) -> str:
        """Rewrite a link found in `from_rel` so it works on the site."""
        if not href or href.startswith("#") or urlsplit(href).scheme or href.startswith("//"):
            return href
        path_part, _, frag = href.partition("#")
        target = posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), path_part))
        if target.startswith("../"):
            return href
        if (self.repo / target).is_dir():
            readme = posixpath.join(target, "README.md")
            if readme in self.docs:
                target = readme
            else:
                return f"https://github.com/{REPO}/tree/{BRANCH}/{target}"
        if target in self.docs:
            out = rel_href(from_url, self.docs[target]["url"])
            return out + (f"#{frag}" if frag else "")
        # Not a published doc (script, config, ...): link to it on GitHub.
        return f"https://github.com/{REPO}/blob/{BRANCH}/{target}" + (f"#{frag}" if frag else "")

    def render(self, rel: str, text: str) -> Dict:
        entry = self.docs[rel]
        tokens = self.md.parse(text)
        seen: Dict[str, int] = {}
        headings: List[Dict] = []
        toc: List[Dict] = []
        description = ""
        for i, tok in enumerate(tokens):
            if tok.type == "heading_open":
                inline = tokens[i + 1]
                text_only = "".join(c.content for c in (inline.children or [])
                                    if c.type in ("text", "code_inline"))
                slug = github_slug(text_only, seen)
                tok.attrSet("id", slug)
                if tok.tag == "h1" and entry["level"]:
                    # The level tag is shown as a badge; drop it from the heading.
                    kids = inline.children or []
                    while kids and (kids[-1].type == "code_inline" and kids[-1].content.startswith("[Level")
                                    or kids[-1].type == "text" and not kids[-1].content.strip()):
                        kids.pop()
                    if kids and kids[-1].type == "text":
                        kids[-1].content = kids[-1].content.rstrip()
                if tok.tag != "h1":
                    headings.append({"id": slug, "text": text_only.strip()})
                    toc.append({"id": slug, "depth": int(tok.tag[1]),
                                "text": LEVEL_TAG_RE.sub("", text_only).strip()})
                    anchor = Token("html_inline", "", 0)
                    anchor.content = (f'<a class="anchor" href="#{slug}" '
                                      f'aria-label="Link to this section">#</a>')
                    inline.children.append(anchor)
            elif tok.type == "paragraph_open" and not description:
                description = tokens[i + 1].content
            if tok.type == "inline":
                for child in tok.children or []:
                    if child.type == "link_open":
                        href = child.attrGet("href") or ""
                        new = self.resolve(rel, href, entry["url"])
                        child.attrSet("href", new)
                        if urlsplit(new).scheme in ("http", "https"):
                            child.attrSet("rel", "noopener")
                    elif child.type == "image":
                        src = child.attrGet("src") or ""
                        if src and not urlsplit(src).scheme:
                            child.attrSet("src", f"https://raw.githubusercontent.com/{REPO}/"
                                                 f"{BRANCH}/" + posixpath.normpath(
                                                     posixpath.join(posixpath.dirname(rel), src)))
        body = self.md.renderer.render(tokens, self.md.options, {})
        # Table alignment comes out as inline styles; the CSP forbids those.
        body = re.sub(r' style="text-align:(left|center|right)"', r' class="align-\1"', body)
        plain = re.sub(r'<a class="anchor"[^>]*>#</a>|\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', "", body)
        plain = re.sub(r"</(p|li|h[1-6]|td|th|tr|pre|blockquote|div)>|<br\s*/?>", " ", plain)
        plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", plain))).strip()
        desc = re.sub(r"[`*_\[\]]|\(http[^)]*\)", "", description)
        desc = re.sub(r"\s+", " ", desc).strip()
        if len(desc) > 160:
            desc = desc[:157].rsplit(" ", 1)[0] + "..."
        body = PRE_RE.sub(frame_code, body)
        # Inline `[Level N: ...]` tags in headings and prose become level-coloured labels.
        body = LEVEL_CODE_RE.sub(lambda m: f'<span class="level-tag" data-level="{level_num(m.group(1))}">'
                                           f'{m.group(1)}</span>', body)
        body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        # GitHub alert syntax ("> [!WARNING]") becomes a styled callout.
        body = ALERT_RE.sub(lambda m: f'<blockquote class="callout callout-{alert_kind(m.group(1))}">\n<p>', body)
        body = CALLOUT_RE.sub(lambda m: f'<blockquote class="callout callout-{callout_kind(m.group(1))}">'
                                        f'\n<p><strong>{m.group(1)}', body)
        return {"html": body, "headings": headings, "toc": toc, "text": plain, "description": desc}


PRE_RE = re.compile(r"<pre( class=\"highlight\")?><code(?: class=\"language-([^\"]+)\")?>.*?</code></pre>", re.S)
LEVEL_TAG_RE = re.compile(r"\s*\[Level[^\]]*\]")
LEVEL_CODE_RE = re.compile(r"<code>\[(Level [^\]<]*)\]</code>")
ALERT_RE = re.compile(r"<blockquote>\n<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*")
CALLOUT_RE = re.compile(r"<blockquote>\n<p><strong>([^<]+)")
WARN_WORDS = ("legal", "authori", "warning", "sensitive", "trap", "education")


def frame_code(m: re.Match) -> str:
    """Give a code block a header bar with its language (app.js adds the copy button there)."""
    lang = m.group(2) or "text"
    return (f'<div class="codeblock" data-lang="{lang}"><div class="codeblock-bar">'
            f'<span class="codeblock-lang">{lang}</span></div>{m.group(0)}</div>')


def alert_kind(kind: str) -> str:
    return "warn" if kind in ("WARNING", "CAUTION", "IMPORTANT") else "note"


def callout_kind(label: str) -> str:
    return "warn" if any(w in label.lower() for w in WARN_WORDS) else "note"


def level_num(level: str) -> str:
    """'Level 2: Reconnaissance' -> '2' (used to colour-code the path)."""
    m = re.search(r"Level\s+(\d)", level or "")
    return m.group(1) if m else ""


def hours(time: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)", time or "")
    return float(m.group(1)) if m else 0.0


# --------------------------------------------------------------------------- #
# Page templates
# --------------------------------------------------------------------------- #
def esc(s: str) -> str:
    return html.escape(s, quote=True)


ICONS = {
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "sun": ('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4'
            'M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "github": ('<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 '
               '0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 '
               '3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>'),
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "check": '<path d="m5 12 5 5L20 7"/>',
    "edit": '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "issue": '<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/>',
}


def icon(name: str, cls: str = "icon") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{ICONS[name]}</svg>')


def section_level(sec: Dict) -> str:
    return level_num(sec["items"][0]["level"]) if sec["items"] else ""


def is_module(sec: Dict) -> bool:
    return bool(re.match(r"^\d", sec["id"]))


def module_name(sec: Dict) -> Tuple[str, str]:
    """'01. Terminal & Linux Core' -> ('01', 'Terminal & Linux Core')."""
    num, _, name = sec["title"].partition(". ")
    return (num, name) if name else ("", sec["title"])


def short_title(sec: Dict, idx: int, item: Dict) -> str:
    """Item label inside its module: the README is the 'Overview', and a
    ': <module name>' suffix that only repeats the heading above is dropped."""
    if not is_module(sec):
        return item["title"]
    if idx == 0:
        return "Overview"
    name = module_name(sec)[1]
    return re.sub(rf":\s*{re.escape(name)}$", "", item["title"])


def nav_html(sections: List[Dict], current_url: str) -> str:
    out = []
    for sec in sections:
        items = []
        for i, it in enumerate(sec["items"]):
            active = it["url"] == current_url
            items.append(
                f'<li><a href="{esc(rel_href(current_url, it["url"]))}" data-doc="{esc(it["url"])}"'
                + (' class="active" aria-current="page"' if active else "")
                + f'><span class="done-mark" aria-hidden="true"></span>{esc(short_title(sec, i, it))}</a></li>'
            )
        lvl = section_level(sec)
        attr = f' data-level="{lvl}"' if lvl else ""
        num, name = module_name(sec) if is_module(sec) else ("", sec["title"])
        num_html = f'<span class="nav-num">{esc(num)}</span>' if num else ""
        out.append(f'<div class="nav-section"{attr}><h3>{num_html}{esc(name)}</h3>'
                   f'<ul>{"".join(items)}</ul></div>')
    return "".join(out)


def toc_html(headings: List[Dict]) -> str:
    """Right-hand 'On this page' list (H2s, with H3s indented)."""
    headings = [h for h in headings if h["depth"] <= 3]
    if len(headings) < 2:
        return ""
    items = "".join(f'<li class="toc-d{h["depth"]}"><a href="#{esc(h["id"])}">{esc(h["text"])}</a></li>'
                    for h in headings[:48])
    return (f'<aside class="toc" aria-labelledby="toc-h"><p id="toc-h" class="toc-title">On this page</p>'
            f'<ol>{items}</ol></aside>')


def page_html(*, title: str, description: str, url: str, body: str, sections: List[Dict],
              extra_head: str = "", doc_url: Optional[str] = None, prefix: Optional[str] = None,
              generated: str = "", total_docs: int = 0, toc: str = "", page_class: str = "page-doc") -> str:
    p = prefix if prefix is not None else root_prefix(url)
    full_title = SITE_TITLE if title == SITE_TITLE else f"{title} | {SITE_TITLE}"
    canonical = SITE_URL + url
    data_doc = f' data-doc="{esc(doc_url)}"' if doc_url else ""
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{CSP}">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{esc(SITE_TITLE)}">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <meta property="og:image" content="{esc(SITE_URL)}assets/og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#0a0d12">
  <link rel="icon" href="{p}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{p}assets/styles.css">
  <link rel="stylesheet" href="{p}assets/pygments.css">
  <script src="{p}assets/theme-init.js"></script>
  {extra_head}
</head>
<body class="{page_class}" data-root="{p}"{data_doc}>
  <a class="skip-link" href="#doc">Skip to content</a>
  <header class="topbar">
    <button id="menu-toggle" class="icon-btn menu-btn" type="button" aria-label="Toggle navigation"
            aria-expanded="false" aria-controls="sidebar">{icon("menu")}</button>
    <a class="brand" href="{p}">
      <span class="brand-mark" aria-hidden="true">&gt;_</span>
      <span class="brand-text">{esc(SITE_TITLE)}</span>
    </a>
    <div class="search-wrap">
      {icon("search", "icon search-icon")}
      <input id="search" type="search" placeholder="Search commands, flags, docs"
             autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list"
             aria-controls="search-results" aria-label="Search documentation">
      <kbd class="search-kbd" aria-hidden="true">/</kbd>
      <ul id="search-results" class="search-results" role="listbox" hidden></ul>
      <p id="search-status" class="visually-hidden" aria-live="polite"></p>
    </div>
    <nav class="topnav" aria-label="Site">
      <a href="{p}{esc(first_module_url(sections))}">Course</a>
      <a href="{p}{esc(section_url(sections, "cheatsheets"))}">Cheatsheets</a>
      <a href="{p}overview/#quickstart">Lab</a>
    </nav>
    <button id="theme-toggle" class="icon-btn" type="button" aria-label="Toggle light/dark theme"
            title="Toggle theme">{icon("sun", "icon icon-sun")}{icon("moon", "icon icon-moon")}</button>
    <a class="icon-btn" href="https://github.com/{REPO}" rel="noopener" aria-label="View on GitHub"
       title="View on GitHub">{icon("github")}</a>
  </header>
  <div class="layout">
    <nav id="sidebar" class="sidebar" aria-label="Documentation navigation">
      <div class="progress-wrap" hidden>
        <div class="progress-label"><span id="progress-text"></span>
          <button id="progress-reset" class="link-btn" type="button">Reset</button></div>
        <div class="progress-bar"><span id="progress-fill"></span></div>
      </div>
      <div class="nav-tree">{nav_html(sections, url)}</div>
      <p class="nav-meta">{total_docs} documents &middot; built {esc(generated[:10])}</p>
    </nav>
    <div id="scrim" class="scrim" hidden></div>
    <main class="content">
      {body}
    </main>
    {toc}
  </div>
  <footer class="site-footer">
    <div class="footer-inner">
      <p class="footer-brand"><span class="brand-mark" aria-hidden="true">&gt;_</span> {esc(SITE_TITLE)}</p>
      <p class="footer-legal">For education and authorized testing only. Practice on the lab, on
        systems you own, or with written permission.</p>
      <p class="footer-links">
        <a href="https://github.com/{REPO}" rel="noopener">GitHub</a>
        <a href="https://github.com/{REPO}/blob/{BRANCH}/LICENSE" rel="noopener">MIT License</a>
        <a href="https://github.com/{REPO}/blob/{BRANCH}/CHANGELOG.md" rel="noopener">Changelog</a>
        <a href="https://github.com/{REPO}/discussions" rel="noopener">Discussions</a>
      </p>
      <p class="footer-credit">Built by <a href="https://github.com/TMHSDigital" rel="noopener">TMHSDigital</a></p>
    </div>
  </footer>
  <script src="{p}assets/app.js"></script>
</body>
</html>
"""


def section_url(sections: List[Dict], sec_id: str) -> str:
    sec = next((s for s in sections if s["id"] == sec_id and s["items"]), None)
    return sec["items"][0]["url"] if sec else "overview/"


def first_module_url(sections: List[Dict]) -> str:
    modules = [s for s in sections if re.match(r"^\d", s["id"])]
    return modules[0]["items"][0]["url"] if modules else "overview/"


def doc_body(entry: Dict, rendered: Dict, prev: Optional[Dict], nxt: Optional[Dict]) -> str:
    url = entry["url"]
    b = []
    if entry["level"]:
        b.append(f'<span class="badge">{esc(entry["level"])}</span>')
    if entry["time"]:
        b.append(f'<span class="badge badge-time">{esc(entry["time"])}</span>')
    lvl = level_num(entry["level"])
    lvl_attr = f' data-level="{lvl}"' if lvl else ""
    meta = f'<div class="doc-badges"{lvl_attr}>{"".join(b)}</div>'
    crumbs = (f'<nav class="crumbs" aria-label="Breadcrumb"><a href="{esc(root_prefix(url))}">Home</a>'
              f'<span aria-hidden="true">/</span><span>{esc(entry.get("section", ""))}</span></nav>')
    pager = []
    if prev:
        pager.append(f'<a class="pager-btn" rel="prev" href="{esc(rel_href(url, prev["url"]))}">'
                     f'<small>{icon("arrow-left")} Previous</small><span>{esc(prev["title"])}</span>'
                     f'<em>{esc(prev.get("section", ""))}</em></a>')
    else:
        pager.append('<span></span>')
    if nxt:
        pager.append(f'<a class="pager-btn pager-next" rel="next" href="{esc(rel_href(url, nxt["url"]))}">'
                     f'<small>Next {icon("arrow-right")}</small><span>{esc(nxt["title"])}</span>'
                     f'<em>{esc(nxt.get("section", ""))}</em></a>')
    issue = f"https://github.com/{REPO}/issues/new?title=" + esc(f"Docs: {entry['title']}").replace(" ", "+")
    return f"""{crumbs}
      <article id="doc" class="markdown">
        {meta}
        {rendered["html"]}
      </article>
      <div class="doc-actions">
        <button id="mark-done" class="done-btn" type="button" aria-pressed="false">Mark as complete</button>
        <span class="doc-actions-links">
          <a href="https://github.com/{REPO}/blob/{BRANCH}/{esc(entry["path"])}"
             rel="noopener">{icon("edit")} Edit this page</a>
          <a href="{issue}" rel="noopener">{icon("issue")} Report a problem</a>
        </span>
      </div>
      <nav class="pager" aria-label="Previous and next document">{"".join(pager)}</nav>"""


HERO_SESSION = [
    ("prompt", "nmap 10.77.0.10 10.77.0.20"),
    ("out", "Nmap scan report for web-target.pentest-lab-net (10.77.0.10)"),
    ("out", "PORT   STATE SERVICE"),
    ("hit", "80/tcp open  http"),
    ("out", ""),
    ("out", "Nmap scan report for ftp-service.pentest-lab-net (10.77.0.20)"),
    ("out", "PORT   STATE SERVICE"),
    ("hit", "21/tcp open  ftp"),
    ("out", ""),
    ("dim", "Nmap done: 2 IP addresses (2 hosts up) scanned in 0.19 seconds"),
]


def hero_terminal() -> str:
    lines = []
    for kind, text in HERO_SESSION:
        if kind == "prompt":
            lines.append(f'<span class="t-prompt">root@attacker:~#</span> <span class="t-cmd">{esc(text)}</span>')
        else:
            lines.append(f'<span class="t-{kind}">{esc(text)}</span>')
    return f"""<figure class="terminal">
            <figcaption class="terminal-bar">attacker (10.77.0.5): a real scan of the lab</figcaption>
            <pre class="terminal-body">{chr(10).join(lines)}</pre>
          </figure>"""


def landing_body(sections: List[Dict], docs_meta: Dict[str, Dict]) -> str:
    modules = [s for s in sections if is_module(s)]
    others = [s for s in sections if s["id"] != "home" and not is_module(s)]
    first = first_module_url(sections)
    total_h = sum(hours(s["items"][0]["time"]) for s in modules)

    rows = []
    for sec in modules:
        lead = sec["items"][0]
        num, name = module_name(sec)
        lvl = level_num(lead["level"])
        label = lead["level"].split(":", 1)[-1].strip() if lead["level"] else ""
        outcome = MODULE_OUTCOMES.get(num) or docs_meta.get(lead["path"], {}).get("description", "")
        subs = "".join(f'<li><a href="{esc(it["url"])}">{esc(short_title(sec, i, it))}</a></li>'
                       for i, it in enumerate(sec["items"]) if i)
        rows.append(f"""<li class="module" data-level="{lvl}" data-section="{esc(sec["id"])}">
            <span class="module-num">{esc(num)}</span>
            <div class="module-body">
              <h3><a href="{esc(lead["url"])}">{esc(name)}</a></h3>
              <p>{esc(outcome)}</p>
              {f'<ul class="module-pages">{subs}</ul>' if subs else ""}
            </div>
            <p class="module-meta"><span class="module-level">Level {esc(lvl)} &middot; {esc(label)}</span>
              <span>{esc(lead["time"])}</span><span class="module-progress" data-progress></span></p>
          </li>""")

    hosts = "".join(f"""<tr><th scope="row"><code>{esc(name)}</code></th><td><code>{esc(ip)}</code></td>
              <td>{esc(role)}</td><td>{esc(desc)}</td></tr>""" for name, ip, role, desc in LAB_HOSTS)

    lab_cmds = "\n".join(
        f'<span class="t-prompt">$</span> {esc(cmd):<34}<span class="t-dim"># {esc(note)}</span>'
        for cmd, note in (("./scripts/setup-lab-env.sh", "build and start the lab"),
                          ("./scripts/setup-lab-env.sh shell", "open a shell on the attacker")))

    refs = []
    for sec in others:
        links = "".join(f'<li><a href="{esc(it["url"])}">{esc(it["title"])}</a></li>' for it in sec["items"])
        refs.append(f'<div class="ref-group"><h3>{esc(sec["title"])}</h3><ul>{links}</ul></div>')
    reference = (f'<section class="band" aria-labelledby="ref-h"><h2 id="ref-h">Reference</h2>'
                 f'<div class="ref">{"".join(refs)}</div></section>') if refs else ""

    return f"""<div id="doc" class="landing">
        <section class="hero">
          <div class="hero-copy">
            <h1>{esc(SITE_TITLE)}</h1>
            <p class="hero-lead">{esc(SITE_TAGLINE)}</p>
            <div class="hero-actions">
              <a class="btn btn-primary" href="{esc(first)}">Start module 01 {icon("arrow-right")}</a>
              <a class="btn" href="overview/#quickstart">Set up the lab</a>
            </div>
            <p class="hero-facts">{len(modules)} modules &middot; about {total_h:g} hours &middot; free and
              MIT licensed</p>
          </div>
          {hero_terminal()}
        </section>

        <section class="band" aria-labelledby="course-h">
          <h2 id="course-h">Course</h2>
          <p class="band-lead">Take the modules in order. Every technique gives the command, the output it
            prints in the lab, and how a defender spots or stops it. Modules 01 and 02 end with lab checks
            that print PASS or FAIL. Pages you mark complete are remembered in this browser.</p>
          <ol class="modules">{"".join(rows)}</ol>
        </section>

        <section class="band" aria-labelledby="lab-h">
          <h2 id="lab-h">Practice lab</h2>
          <p class="band-lead">Docker Compose starts a Kali attacker and two deliberately insecure targets on
            an isolated bridge network, <code>10.77.0.0/24</code>. Every example in the course runs against
            it. No Docker? <a href="https://codespaces.new/{REPO}" rel="noopener">Open the repo in
            Codespaces</a> and run the same commands there.</p>
          <div class="table-wrap"><table class="hosts">
            <thead><tr><th scope="col">Host</th><th scope="col">Address</th><th scope="col">Service</th>
              <th scope="col">What it is for</th></tr></thead>
            <tbody>{hosts}</tbody>
          </table></div>
          <pre class="lab-cmd"><code>{lab_cmds}</code></pre>
        </section>

        {reference}

        <section class="band" aria-labelledby="safety-h">
          <div class="safety">
            <h2 id="safety-h">Authorized targets only</h2>
            <p>Using these techniques against systems, networks, or wireless access points you do not own or
              lack written permission to test is illegal in most jurisdictions. Every example in this course
              targets the lab, <code>127.0.0.1</code>, or documentation address ranges.</p>
          </div>
        </section>
      </div>"""


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def pygments_css() -> str:
    dark = HtmlFormatter(style="github-dark").get_style_defs('[data-theme="dark"] .highlight')
    light = HtmlFormatter(style="default").get_style_defs('[data-theme="light"] .highlight')
    # Let the site's own code background show through.
    strip_bg = re.compile(r"^(\[data-theme=\"(?:dark|light)\"\] \.highlight) \{ background: [^;]+; \}$", re.M)
    return strip_bg.sub("", dark + "\n" + light) + "\n"


def write(out: Path, url: str, content: str) -> None:
    target = out / url / "index.html" if url else out / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def build(repo: Path, out: Path, site_src: Path) -> Dict:
    # Empty (rather than delete) the output dir so a preview server running
    # inside it survives rebuilds.
    out.mkdir(parents=True, exist_ok=True)
    for child in out.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    if not site_src.exists():
        raise SystemExit(f"error: site source not found at {site_src}")
    shutil.copytree(site_src, out, dirs_exist_ok=True)
    (out / "assets" / "pygments.css").write_text(pygments_css(), encoding="utf-8")

    sections = discover(repo)
    flat = [dict(it, section=sec["title"]) for sec in sections for it in sec["items"]]
    docs = {it["path"]: it for it in flat}
    renderer = Renderer(repo, docs)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    common = {"sections": sections, "generated": generated, "total_docs": len(flat)}

    rendered_all: Dict[str, Dict] = {}
    for it in flat:
        rendered_all[it["path"]] = renderer.render(it["path"], read_text(repo / it["path"]))

    search = []
    for i, it in enumerate(flat):
        r = rendered_all[it["path"]]
        prev = flat[i - 1] if i > 0 else None
        nxt = flat[i + 1] if i + 1 < len(flat) else None
        write(out, it["url"], page_html(
            title=it["title"], description=r["description"] or SITE_TAGLINE, url=it["url"],
            body=doc_body(it, r, prev, nxt), doc_url=it["url"], toc=toc_html(r["toc"]), **common))
        search.append({"url": it["url"], "title": it["title"], "section": it["section"],
                       "headings": r["headings"], "text": r["text"]})

    write(out, "", page_html(title=SITE_TITLE, description=SITE_TAGLINE, url="",
                             body=landing_body(sections, rendered_all), page_class="page-landing", **common))

    base_path = urlsplit(SITE_URL).path  # 404 is served at any depth: absolute paths
    (out / "404.html").write_text(page_html(
        title="Page not found", description="This page does not exist.", url="404.html",
        prefix=base_path, body=f"""<div id="doc" class="markdown notfound">
        <h1>Page not found</h1>
        <p>That page doesn't exist or has moved. Try the search box above, or go to the
        <a href="{base_path}">course home page</a>.</p></div>""", **common),
        encoding="utf-8", newline="\n")

    (out / "search-index.json").write_text(json.dumps(search, separators=(",", ":")),
                                           encoding="utf-8")
    manifest = {"site": {"title": SITE_TITLE, "url": SITE_URL, "repo": REPO,
                         "generated": generated}, "sections": sections}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    urls = [""] + [it["url"] for it in flat]
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{esc(SITE_URL + u)}</loc><lastmod>{generated[:10]}</lastmod></url>\n"
                  for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n",
                                    encoding="utf-8")

    # Cache-bust the offline service worker on every build.
    sw = out / "sw.js"
    if sw.exists():
        sw.write_text(sw.read_text(encoding="utf-8").replace("__BUILD_ID__", generated),
                      encoding="utf-8")
    return {"sections": sections, "docs": flat}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="_site", help="Output directory")
    args = parser.parse_args(argv)

    out = (REPO_ROOT / args.out).resolve()
    result = build(REPO_ROOT, out, SITE_SRC)
    print(f"Built site -> {out}")
    print(f"  {len(result['sections'])} section(s), {len(result['docs'])} document(s)")
    for s in result["sections"]:
        print(f"  - {s['title']}: {len(s['items'])} doc(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
