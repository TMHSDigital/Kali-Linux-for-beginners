#!/usr/bin/env python3
"""build-site.py: generate the GitHub Pages site from the repo content.

This is what makes the docs site *dynamic*: nothing about the navigation is
hardcoded. The script walks the repository, discovers every Markdown file,
groups them into sections by their top-level directory, derives human titles
from each file's first ``# heading``, and emits:

  _site/
    index.html            (copied from site/)
    assets/...            (copied from site/assets/)
    manifest.json         (generated navigation tree)
    content/<path>.md     (every discovered Markdown file, paths preserved)

Add a new module directory or a new cheatsheet, push, and it appears in the
site automatically; no edits here or in the front-end are required.

Usage:
    python scripts/build-site.py [--out _site]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Repo root = parent of this script's directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = REPO_ROOT / "site"

# Directories we never surface in the docs site.
EXCLUDE_DIRS = {
    ".git", ".github", "_site", "site", "node_modules",
    ".venv", "venv", "__pycache__", ".lab",
}
# Individual files to skip (internal / not curriculum content).
EXCLUDE_FILES = {"CLAUDE.md"}

H1_RE = re.compile(r"^\s*#\s+(.+?)\s*$", re.MULTILINE)


def first_heading(md_path: Path) -> Optional[str]:
    """Return the text of the first level-1 heading, if any."""
    try:
        text = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = H1_RE.search(text)
    return m.group(1).strip() if m else None


def prettify(name: str) -> str:
    """Turn a slug like '03-network-recon-and-nmap' into a readable title."""
    # Drop a leading numeric prefix ("03-") but keep it as an order hint.
    stem = re.sub(r"^\d+[-_]", "", name)
    words = re.split(r"[-_]+", stem)
    return " ".join(w.capitalize() for w in words if w)


def section_title(dir_name: str) -> str:
    """Section heading: keep the numeric prefix as a badge-friendly label."""
    m = re.match(r"^(\d+)[-_](.*)$", dir_name)
    if m:
        return f"{m.group(1)}. {prettify(m.group(2))}"
    return prettify(dir_name)


def item_title(md_path: Path, rel: str) -> str:
    """Best available title for a file: its H1, else a prettified filename."""
    heading = first_heading(md_path)
    if heading:
        return heading
    stem = md_path.stem
    if stem.lower() == "readme":
        return "Overview"
    return prettify(stem)


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
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        if md.name in EXCLUDE_FILES:
            continue

        rel = md.relative_to(repo).as_posix()
        entry = {"title": item_title(md, rel), "path": rel}

        if len(rel_parts) == 1:
            # Top-level file (e.g. README.md) → Home section.
            root_items.append(entry)
        else:
            top = rel_parts[0]
            sec = dir_sections.setdefault(
                top, {"id": top, "title": section_title(top), "items": []}
            )
            sec["items"].append(entry)

    sections: List[Dict] = []
    if root_items:
        sections.append(
            {"id": "home", "title": "Home", "items": sort_items(root_items)}
        )
    # Numeric-prefixed dirs first (in numeric order), then the rest alphabetically.
    for key in sorted(
        dir_sections,
        key=lambda d: (0, d) if re.match(r"^\d", d) else (1, d),
    ):
        sec = dir_sections[key]
        sec["items"] = sort_items(sec["items"])
        sections.append(sec)
    return sections


def copy_content(repo: Path, out: Path, sections: List[Dict]) -> None:
    """Copy every referenced Markdown file into _site/content/, paths intact."""
    content_root = out / "content"
    for sec in sections:
        for item in sec["items"]:
            src = repo / item["path"]
            dst = content_root / item["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="_site", help="Output directory")
    args = parser.parse_args(argv)

    out = (REPO_ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Copy static site shell (index.html + assets).
    if not SITE_SRC.exists():
        raise SystemExit(f"error: site source not found at {SITE_SRC}")
    for entry in SITE_SRC.iterdir():
        target = out / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)

    sections = discover(REPO_ROOT)
    copy_content(REPO_ROOT, out, sections)

    manifest = {
        "site": {
            "title": "Kali Linux for Beginners",
            "subtitle": "",
            "repo": "TMHSDigital/Kali-Linux-for-beginners",
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "sections": sections,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    total = sum(len(s["items"]) for s in sections)
    print(f"Built site -> {out}")
    print(f"  {len(sections)} section(s), {total} document(s)")
    for s in sections:
        # ASCII-safe: section titles may contain an em dash on some consoles.
        title = s["title"].encode("ascii", "replace").decode("ascii")
        print(f"  - {title}: {len(s['items'])} doc(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
