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
        plain = re.sub(r'<a class="anchor"[^>]*>#</a>', "", body)
        plain = re.sub(r"</(p|li|h[1-6]|td|th|tr|pre|blockquote|div)>|<br\s*/?>", " ", plain)
        plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", plain))).strip()
        desc = re.sub(r"[`*_\[\]]|\(http[^)]*\)", "", description)
        desc = re.sub(r"\s+", " ", desc).strip()
        if len(desc) > 160:
            desc = desc[:157].rsplit(" ", 1)[0] + "..."
        return {"html": body, "headings": headings, "text": plain, "description": desc}


# --------------------------------------------------------------------------- #
# Page templates
# --------------------------------------------------------------------------- #
def esc(s: str) -> str:
    return html.escape(s, quote=True)


def nav_html(sections: List[Dict], current_url: str) -> str:
    out = []
    for sec in sections:
        items = []
        for it in sec["items"]:
            active = it["url"] == current_url
            items.append(
                f'<li><a href="{esc(rel_href(current_url, it["url"]))}" data-doc="{esc(it["url"])}"'
                + (' class="active" aria-current="page"' if active else "")
                + f'><span class="done-mark" aria-hidden="true"></span>{esc(it["title"])}</a></li>'
            )
        out.append(f'<div class="nav-section"><h3>{esc(sec["title"])}</h3>'
                   f'<ul>{"".join(items)}</ul></div>')
    return "".join(out)


def page_html(*, title: str, description: str, url: str, body: str, sections: List[Dict],
              extra_head: str = "", doc_url: Optional[str] = None, prefix: Optional[str] = None,
              generated: str = "", total_docs: int = 0) -> str:
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
  <meta name="theme-color" content="#0d1117">
  <link rel="icon" href="{p}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{p}assets/styles.css">
  <link rel="stylesheet" href="{p}assets/pygments.css">
  <script src="{p}assets/theme-init.js"></script>
  {extra_head}
</head>
<body data-root="{p}"{data_doc}>
  <a class="skip-link" href="#doc">Skip to content</a>
  <header class="topbar">
    <button id="menu-toggle" class="icon-btn" type="button" aria-label="Toggle navigation"
            aria-expanded="false" aria-controls="sidebar">&#8801;</button>
    <a class="brand" href="{p}">
      <span class="brand-mark" aria-hidden="true">$_</span>
      <span class="brand-text"><strong>{esc(SITE_TITLE)}</strong></span>
    </a>
    <div class="topbar-spacer"></div>
    <div class="search-wrap">
      <input id="search" type="search" placeholder="Search commands and docs (press /)"
             autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list"
             aria-controls="search-results" aria-label="Search documentation">
      <ul id="search-results" class="search-results" role="listbox" hidden></ul>
      <p id="search-status" class="visually-hidden" aria-live="polite"></p>
    </div>
    <button id="theme-toggle" class="icon-btn" type="button" aria-label="Toggle light/dark theme">&#9680;</button>
    <a class="icon-btn" href="https://github.com/{REPO}" rel="noopener" aria-label="View on GitHub"
       title="View on GitHub">&#8599;</a>
  </header>
  <div class="layout">
    <nav id="sidebar" class="sidebar" aria-label="Documentation navigation">
      <div class="progress-wrap" hidden>
        <div class="progress-label"><span id="progress-text"></span></div>
        <div class="progress-bar"><span id="progress-fill"></span></div>
      </div>
      <div class="nav-tree">{nav_html(sections, url)}</div>
      <p class="nav-meta muted">{total_docs} documents &middot; built {esc(generated[:10])}</p>
    </nav>
    <div id="scrim" class="scrim" hidden></div>
    <main class="content">
      {body}
    </main>
  </div>
  <script src="{p}assets/app.js"></script>
</body>
</html>
"""


def doc_body(entry: Dict, rendered: Dict, prev: Optional[Dict], nxt: Optional[Dict]) -> str:
    url = entry["url"]
    badges = ""
    if entry["level"] or entry["time"]:
        b = []
        if entry["level"]:
            b.append(f'<span class="badge">{esc(entry["level"])}</span>')
        if entry["time"]:
            b.append(f'<span class="badge badge-time">{esc(entry["time"])}</span>')
        badges = f'<div class="doc-badges">{"".join(b)}</div>'
    pager = []
    if prev:
        pager.append(f'<a class="pager-btn" rel="prev" href="{esc(rel_href(url, prev["url"]))}">'
                     f'<small>&larr; Previous</small><span>{esc(prev["title"])}</span></a>')
    else:
        pager.append('<span></span>')
    if nxt:
        pager.append(f'<a class="pager-btn pager-next" rel="next" href="{esc(rel_href(url, nxt["url"]))}">'
                     f'<small>Next &rarr;</small><span>{esc(nxt["title"])}</span></a>')
    return f"""<article id="doc" class="markdown">
        {badges}
        {rendered["html"]}
      </article>
      <div class="doc-actions">
        <button id="mark-done" class="done-btn" type="button" aria-pressed="false">Mark as complete</button>
      </div>
      <nav class="pager" aria-label="Previous and next document">{"".join(pager)}</nav>
      <footer class="doc-footer">
        <a href="https://github.com/{REPO}/blob/{BRANCH}/{esc(entry["path"])}"
           rel="noopener">Edit this page on GitHub &#8599;</a>
      </footer>"""


def landing_body(sections: List[Dict], docs_meta: Dict[str, Dict]) -> str:
    modules = [s for s in sections if re.match(r"^\d", s["id"])]
    others = [s for s in sections if s["id"] != "home" and not re.match(r"^\d", s["id"])]
    first = modules[0]["items"][0]["url"] if modules else "overview/"
    cards = []
    for sec in modules:
        lead = sec["items"][0]
        meta = docs_meta.get(lead["path"], {})
        badges = "".join(
            f'<span class="badge{cls}">{esc(v)}</span>'
            for v, cls in ((lead["level"], ""), (lead["time"], " badge-time")) if v)
        extra = "".join(f'<li><a href="{esc(it["url"])}">{esc(it["title"])}</a></li>'
                        for it in sec["items"][1:])
        cards.append(f"""<article class="card" data-section="{esc(sec["id"])}">
          <h3><a href="{esc(lead["url"])}">{esc(sec["title"])}</a></h3>
          <div class="card-badges">{badges}</div>
          <p>{esc(meta.get("description", ""))}</p>
          {f'<ul class="card-links">{extra}</ul>' if extra else ""}
        </article>""")
    other_cards = []
    for sec in others:
        links = "".join(f'<li><a href="{esc(it["url"])}">{esc(it["title"])}</a></li>'
                        for it in sec["items"])
        other_cards.append(f'<article class="card"><h3>{esc(sec["title"])}</h3>'
                           f'<ul class="card-links">{links}</ul></article>')
    reference = (f'<section aria-labelledby="ref-h"><h2 id="ref-h">Reference</h2>'
                 f'<div class="card-grid">{"".join(other_cards)}</div></section>') if other_cards else ""
    return f"""<div id="doc" class="landing">
        <section class="hero">
          <p class="hero-kicker">Free &middot; self-paced &middot; no account needed</p>
          <h1>Learn Kali Linux by doing</h1>
          <p class="hero-lead">{esc(SITE_TAGLINE)}</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="{esc(first)}">Start module 01</a>
            <a class="btn" href="overview/">Set up the lab</a>
            <a class="btn" href="https://codespaces.new/{REPO}" rel="noopener">Open in Codespaces</a>
          </div>
          <ul class="hero-points">
            <li><strong>Hands-on:</strong> every command comes with expected output and a defensive note.</li>
            <li><strong>Safe practice lab:</strong> Docker targets and a Kali attacker box on a private network.</li>
            <li><strong>Self-grading:</strong> lab checks print PASS/FAIL so you know you've got it.</li>
          </ul>
        </section>
        <section aria-labelledby="modules-h">
          <h2 id="modules-h">The path</h2>
          <div class="card-grid">{"".join(cards)}</div>
        </section>
        {reference}
        <p class="legal muted">For education and authorized testing only. Only use these techniques on
          systems you own or have written permission to test.</p>
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
            body=doc_body(it, r, prev, nxt), doc_url=it["url"], **common))
        search.append({"url": it["url"], "title": it["title"], "section": it["section"],
                       "headings": r["headings"], "text": r["text"]})

    write(out, "", page_html(title=SITE_TITLE, description=SITE_TAGLINE, url="",
                             body=landing_body(sections, rendered_all), **common))

    base_path = urlsplit(SITE_URL).path  # 404 is served at any depth: absolute paths
    (out / "404.html").write_text(page_html(
        title="Page not found", description="This page does not exist.", url="404.html",
        prefix=base_path, body=f"""<div id="doc" class="markdown"><h1>Page not found</h1>
        <p>That page doesn't exist (or moved). Try the search box, or
        <a href="{base_path}">go to the start</a>.</p></div>""", **common),
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
