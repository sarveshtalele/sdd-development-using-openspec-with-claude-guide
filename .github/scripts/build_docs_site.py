#!/usr/bin/env python3
"""Builds a static HTML site from every Markdown file in the repository.

Walks the repo, converts each .md file to a styled HTML page (product-docs
layout: sticky top bar, collapsible sidebar navigation, glassmorphic panels),
rewrites internal .md links to .html, and generates a browsable index.html
for every directory. Output goes to _site/, ready to be uploaded as a
GitHub Pages artifact.
"""

import hashlib
import os
import re
import sys
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "_site"

EXCLUDE_DIR_NAMES = {
    ".git", ".github", "_site", "node_modules", ".venv", "venv",
    "__pycache__", ".pytest_cache",
}
EXCLUDE_DIR_SUFFIXES = (".egg-info",)

# Directories whose contents are still built as pages, but left out of the
# shared sidebar to keep it focused on the documents a reader actually
# starts from.
SIDEBAR_EXCLUDE_COMPONENTS = {"archive", "changes", ".claude", "openspec", "specs"}

SITE_TITLE = "Spec-Driven Development with OpenSpec and Claude Code"
SITE_SHORT_TITLE = "OpenSpec × Claude Code"
GITHUB_REPO_URL = "https://github.com/sarveshtalele/sdd-development-using-openspec-with-claude-guide"
GITHUB_BLOB_BASE = GITHUB_REPO_URL + "/blob/main/"
GITHUB_TREE_BASE = GITHUB_REPO_URL + "/tree/main/"

GROUP_TITLES = {
    "": "Home",
    "openspec-guide": "OpenSpec Guide",
    "claude-guide": "Claude Code Guide",
    "travel-itinerary-agent": "Example Project",
}

MD_EXTENSIONS = ["extra", "toc", "sane_lists"]


def is_excluded_dir(name: str) -> bool:
    return name in EXCLUDE_DIR_NAMES or any(name.endswith(s) for s in EXCLUDE_DIR_SUFFIXES)


def find_markdown_files() -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if not is_excluded_dir(d)]
        for name in filenames:
            if name.lower().endswith(".md"):
                found.append(Path(dirpath) / name)
    return sorted(found)


def rel(path: Path) -> Path:
    return path.relative_to(REPO_ROOT)


def out_path_for(md_path: Path) -> Path:
    return OUTPUT_DIR / rel(md_path).with_suffix(".html")


LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")


def _rewrite_link(match: re.Match) -> str:
    target = match.group(1)
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return match.group(0)
    path_part, sep, frag = target.partition("#")
    if path_part.lower().endswith(".md"):
        new_path = path_part[:-3] + ".html"
        new_target = new_path + (sep + frag if sep else "")
        return f"]({new_target})"
    return match.group(0)


def rewrite_markdown_links(text: str) -> str:
    """Rewrites .md links to .html, skipping anything inside a fenced code
    block so that literal markdown-link syntax shown as an example is left
    untouched."""
    out_lines = []
    fence_char = None
    fence_len = 0
    for line in text.split("\n"):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(2)
            char, length = marker[0], len(marker)
            if fence_char is None:
                fence_char, fence_len = char, length
            elif char == fence_char and length >= fence_len:
                fence_char, fence_len = None, 0
            out_lines.append(line)
            continue
        if fence_char is not None:
            out_lines.append(line)
            continue
        out_lines.append(LINK_RE.sub(_rewrite_link, line))
    return "\n".join(out_lines)


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def group_title_for(top_component: str) -> str:
    return GROUP_TITLES.get(top_component, top_component.replace("-", " ").title())


def is_sidebar_eligible(rel_path: Path) -> bool:
    return not any(part in SIDEBAR_EXCLUDE_COMPONENTS for part in rel_path.parts[:-1])


def build_sidebar_model(pages: list[dict]):
    from collections import OrderedDict

    groups: "OrderedDict" = OrderedDict()
    root_pages = [p for p in pages if is_sidebar_eligible(p["rel"]) and len(p["rel"].parts) == 1]
    groups[""] = root_pages

    top_dirs = sorted({p["rel"].parts[0] for p in pages if len(p["rel"].parts) > 1})
    for top in top_dirs:
        children = [
            p for p in pages
            if is_sidebar_eligible(p["rel"])
            and p["rel"].parts[0] == top
            and len(p["rel"].parts) == 2
        ]
        if children:
            children.sort(key=lambda p: (p["rel"].name != "README.md", p["rel"].name.lower()))
            groups[top] = children
    return groups


def relhref(from_file_out: Path, to_file_out: Path) -> str:
    return os.path.relpath(to_file_out, start=from_file_out.parent).replace(os.sep, "/")


CHEVRON_SVG = (
    '<svg class="chevron" viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">'
    '<path d="M5 3l6 5-6 5" fill="none" stroke="currentColor" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def render_sidebar(current_out: Path, groups: dict) -> str:
    parts = ['<nav class="sidebar-nav">']

    root_pages = groups.get("", [])
    if root_pages:
        parts.append('<div class="nav-pinned">')
        for page in root_pages:
            href = relhref(current_out, page["out"])
            active = " active" if page["out"] == current_out else ""
            parts.append(f'<a class="nav-link nav-link-pinned{active}" href="{href}">{page["title"]}</a>')
        parts.append("</div>")

    for top, children in groups.items():
        if top == "":
            continue
        title = group_title_for(top)
        contains_active = any(page["out"] == current_out for page in children)
        expanded_class = " expanded" if contains_active else ""
        aria = "true" if contains_active else "false"
        parts.append(f'<div class="nav-group{expanded_class}" data-group="{top}">')
        parts.append(
            f'<button type="button" class="nav-group-toggle" aria-expanded="{aria}">'
            f'<span class="nav-group-title">{title}</span>{CHEVRON_SVG}</button>'
        )
        parts.append('<ul class="nav-group-list">')
        for page in children:
            href = relhref(current_out, page["out"])
            active = " active" if page["out"] == current_out else ""
            parts.append(f'<li><a class="nav-link{active}" href="{href}">{page["title"]}</a></li>')
        parts.append("</ul></div>")

    parts.append("</nav>")
    return "\n".join(parts)


def render_breadcrumbs(current_out: Path, rel_path: Path) -> str:
    crumbs = ['<a href="{}">Home</a>'.format(relhref(current_out, OUTPUT_DIR / "index.html"))]
    accumulated = OUTPUT_DIR
    parts = rel_path.parts[:-1]
    for part in parts:
        accumulated = accumulated / part
        index_html = accumulated / "index.html"
        crumbs.append(f'<a href="{relhref(current_out, index_html)}">{part}</a>')
    crumbs.append(f'<span>{rel_path.name}</span>')
    return '<div class="breadcrumbs">' + '<span class="crumb-sep">/</span>'.join(crumbs) + "</div>"


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title} · {site_title}</title>
<script>
(function () {{
  try {{
    var stored = localStorage.getItem('theme');
    var theme = stored || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  }} catch (e) {{}}
}})();
</script>
<link rel="stylesheet" href="{css_href}">
<link rel="preconnect" href="https://cdnjs.cloudflare.com">
<link rel="stylesheet" id="hljs-light-theme" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-light.min.css">
<link rel="stylesheet" id="hljs-dark-theme" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css" disabled>
</head>
<body>
<div class="bg-blob blob-1"></div>
<div class="bg-blob blob-2"></div>
<div class="bg-blob blob-3"></div>

<header class="topbar glass">
  <div class="topbar-inner">
    <button class="nav-toggle" id="navToggle" aria-label="Toggle navigation">
      <span></span><span></span><span></span>
    </button>
    <a class="topbar-brand" href="{home_href}">
      <span class="brand-mark">SD</span>
      <span class="brand-text">{site_short_title}</span>
    </a>
    <button class="theme-toggle" id="themeToggle" aria-label="Toggle dark mode" aria-pressed="false">
      <svg class="icon-sun" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
      <svg class="icon-moon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
    </button>
    <a class="topbar-github" href="{github_repo_url}" target="_blank" rel="noopener">
      View on GitHub
    </a>
  </div>
</header>

<div class="layout">
  <aside class="sidebar glass" id="sidebar">
    {sidebar_html}
  </aside>
  <main class="content-wrap">
    <div class="content glass">
      {breadcrumbs_html}
      {body_html}
      <div class="page-footer">
        <a class="edit-link" href="{edit_url}" target="_blank" rel="noopener">Edit this page on GitHub &#8599;</a>
      </div>
    </div>
  </main>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script src="{js_href}"></script>
</body>
</html>
"""


def render_page(md_path: Path, page_title: str, sidebar_html: str, breadcrumbs_html: str,
                 css_href: str, js_href: str, home_href: str, edit_url: str) -> str:
    raw = md_path.read_text(encoding="utf-8")
    raw = rewrite_markdown_links(raw)
    body_html = markdown.markdown(raw, extensions=MD_EXTENSIONS)
    return PAGE_TEMPLATE.format(
        page_title=page_title,
        site_title=SITE_TITLE,
        site_short_title=SITE_SHORT_TITLE,
        github_repo_url=GITHUB_REPO_URL,
        css_href=css_href,
        js_href=js_href,
        home_href=home_href,
        sidebar_html=sidebar_html,
        breadcrumbs_html=breadcrumbs_html,
        body_html=body_html,
        edit_url=edit_url,
    )


def render_dir_listing(dir_out: Path, dir_rel: Path, entries: list[dict], subdirs: list[str],
                        sidebar_html: str, css_href: str, js_href: str, home_href: str,
                        edit_url: str) -> str:
    title = dir_rel.name if dir_rel.parts else "Home"
    items = []
    for name in sorted(subdirs):
        target = dir_out / name / "index.html"
        items.append(f'<li><a href="{relhref(dir_out / "index.html", target)}">{name}/</a></li>')
    for page in sorted(entries, key=lambda p: p["rel"].name.lower()):
        items.append(
            f'<li><a href="{relhref(dir_out / "index.html", page["out"])}">{page["title"]}</a></li>'
        )
    body_html = f"<h1>{title}</h1><ul class='dir-listing'>" + "\n".join(items) + "</ul>"
    breadcrumbs_html = render_breadcrumbs(dir_out / "index.html", dir_rel) if dir_rel.parts else ""
    return PAGE_TEMPLATE.format(
        page_title=title,
        site_title=SITE_TITLE,
        site_short_title=SITE_SHORT_TITLE,
        github_repo_url=GITHUB_REPO_URL,
        css_href=css_href,
        js_href=js_href,
        home_href=home_href,
        sidebar_html=sidebar_html,
        breadcrumbs_html=breadcrumbs_html,
        body_html=body_html,
        edit_url=edit_url,
    )


def main() -> None:
    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    md_files = find_markdown_files()
    pages = []
    for md_path in md_files:
        rel_path = rel(md_path)
        out = out_path_for(md_path)
        text = md_path.read_text(encoding="utf-8")
        title = first_heading(text, rel_path.stem)
        pages.append({"md": md_path, "rel": rel_path, "out": out, "title": title})

    sidebar_groups = build_sidebar_model(pages)

    assets_dir = OUTPUT_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    css_hash = hashlib.sha256(CSS.encode("utf-8")).hexdigest()[:10]
    js_hash = hashlib.sha256(JS.encode("utf-8")).hexdigest()[:10]
    css_filename = f"style.{css_hash}.css"
    js_filename = f"app.{js_hash}.js"
    (assets_dir / css_filename).write_text(CSS, encoding="utf-8")
    (assets_dir / js_filename).write_text(JS, encoding="utf-8")
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

    for page in pages:
        out = page["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        css_href = relhref(out, assets_dir / css_filename)
        js_href = relhref(out, assets_dir / js_filename)
        home_href = relhref(out, OUTPUT_DIR / "index.html")
        sidebar_html = render_sidebar(out, sidebar_groups)
        breadcrumbs_html = render_breadcrumbs(out, page["rel"])
        edit_url = GITHUB_BLOB_BASE + str(page["rel"]).replace(os.sep, "/")
        html = render_page(page["md"], page["title"], sidebar_html, breadcrumbs_html,
                            css_href, js_href, home_href, edit_url)
        out.write_text(html, encoding="utf-8")

        if page["rel"].name == "README.md":
            index_out = out.parent / "index.html"
            index_out.write_text(html, encoding="utf-8")

    all_dirs = {OUTPUT_DIR}
    for page in pages:
        d = page["out"].parent
        while True:
            all_dirs.add(d)
            if d == OUTPUT_DIR:
                break
            d = d.parent

    for d in sorted(all_dirs, key=lambda p: len(p.parts)):
        index_file = d / "index.html"
        if index_file.exists():
            continue
        dir_rel = d.relative_to(OUTPUT_DIR)
        entries = [p for p in pages if p["out"].parent == d]
        subdirs = sorted({
            sub.relative_to(d).parts[0]
            for sub in all_dirs
            if sub != d and d in sub.parents and len(sub.relative_to(d).parts) == 1
        })
        css_href = relhref(index_file, assets_dir / css_filename)
        js_href = relhref(index_file, assets_dir / js_filename)
        home_href = relhref(index_file, OUTPUT_DIR / "index.html")
        sidebar_html = render_sidebar(index_file, sidebar_groups)
        edit_url = GITHUB_TREE_BASE + str(dir_rel).replace(os.sep, "/") if dir_rel.parts else GITHUB_REPO_URL
        html = render_dir_listing(d, dir_rel, entries, subdirs, sidebar_html, css_href, js_href,
                                   home_href, edit_url)
        index_file.write_text(html, encoding="utf-8")

    print(f"Built {len(pages)} pages into {OUTPUT_DIR}")


CSS = """
:root {
  --blue-deep: #0a5fb4;
  --blue-accent: #2f8fe0;
  --blue-soft: #cfe6fb;
  --cream: #fbf4e8;
  --ink: #1b2430;
  --ink-soft: #57646f;
  --ink-faint: #8a95a1;
  --white: #ffffff;
  --surface: #ffffff;
  --surface-soft: rgba(255, 255, 255, 0.5);
  --grey-bg: #f4f5f7;
  --grey-border: #e3e6ea;
  --grey-shadow: 0 3px 14px rgba(30, 40, 55, 0.09);
  --glass-bg: rgba(255, 255, 255, 0.6);
  --glass-border: rgba(255, 255, 255, 0.7);
  --glass-shadow: 0 8px 36px rgba(24, 66, 115, 0.12);
  --line: rgba(10, 95, 180, 0.12);
  --line-strong: rgba(10, 95, 180, 0.25);
  --underline: rgba(10, 95, 180, 0.28);
  --tint: rgba(47, 143, 224, 0.1);
  --tint-strong: rgba(47, 143, 224, 0.16);
  --radius-lg: 18px;
  --radius-md: 12px;
  --radius-sm: 8px;
  --topbar-h: 60px;
  color-scheme: light;
}

[data-theme="dark"] {
  --blue-deep: #7cc0f5;
  --blue-accent: #4fa3f0;
  --blue-soft: #1c3a56;
  --cream: #24211c;
  --ink: #e7edf4;
  --ink-soft: #aab6c3;
  --ink-faint: #7c8794;
  --white: #ffffff;
  --surface: #1c2330;
  --surface-soft: rgba(255, 255, 255, 0.06);
  --grey-bg: #202834;
  --grey-border: #333f4d;
  --grey-shadow: 0 3px 16px rgba(0, 0, 0, 0.35);
  --glass-bg: rgba(24, 30, 40, 0.62);
  --glass-border: rgba(255, 255, 255, 0.09);
  --glass-shadow: 0 8px 36px rgba(0, 0, 0, 0.45);
  --line: rgba(255, 255, 255, 0.12);
  --line-strong: rgba(255, 255, 255, 0.2);
  --underline: rgba(124, 192, 245, 0.35);
  --tint: rgba(79, 163, 240, 0.14);
  --tint-strong: rgba(79, 163, 240, 0.22);
  color-scheme: dark;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  min-height: 100%;
  scroll-behavior: smooth;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
    "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--ink);
  background: linear-gradient(160deg, #eaf3fc 0%, #f6f2e8 45%, #fdf8ef 100%);
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  line-height: 1.65;
  animation: fadein 0.35s ease;
  transition: background 0.25s ease, color 0.25s ease;
}

[data-theme="dark"] body {
  background: linear-gradient(160deg, #0e1219 0%, #12161e 45%, #151a20 100%);
}

@keyframes fadein {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.bg-blob {
  position: fixed;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.45;
  z-index: 0;
  pointer-events: none;
  transition: opacity 0.25s ease;
}
.blob-1 { width: 520px; height: 520px; top: -180px; left: -140px; background: radial-gradient(circle, #bcdcfb, transparent 70%); }
.blob-2 { width: 460px; height: 460px; bottom: -160px; right: -120px; background: radial-gradient(circle, #f3e2bd, transparent 70%); }
.blob-3 { width: 340px; height: 340px; top: 45%; right: 8%; background: radial-gradient(circle, #d9c9fb, transparent 70%); opacity: 0.28; }
[data-theme="dark"] .bg-blob { opacity: 0.16; }
[data-theme="dark"] .blob-3 { opacity: 0.14; }

.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(22px) saturate(180%);
  -webkit-backdrop-filter: blur(22px) saturate(180%);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}

/* Top bar */
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}
.topbar-inner {
  max-width: 1320px;
  margin: 0 auto;
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
}
.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--ink);
  font-weight: 700;
  font-size: 15px;
  letter-spacing: -0.01em;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(135deg, var(--blue-accent), var(--blue-deep));
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  box-shadow: 0 3px 10px rgba(10, 95, 180, 0.35);
}
.brand-text { white-space: nowrap; }

.theme-toggle {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--surface-soft);
  color: var(--blue-deep);
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
  flex-shrink: 0;
}
.theme-toggle:hover { background: var(--tint-strong); transform: translateY(-1px); }
.theme-toggle .icon-moon { display: none; }
[data-theme="dark"] .theme-toggle .icon-sun { display: none; }
[data-theme="dark"] .theme-toggle .icon-moon { display: inline-block; }

.topbar-github {
  font-size: 13px;
  font-weight: 600;
  color: var(--blue-deep);
  text-decoration: none;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: var(--surface-soft);
  transition: background 0.15s ease, transform 0.15s ease;
  white-space: nowrap;
}
.topbar-github:hover { background: var(--tint-strong); transform: translateY(-1px); }

.layout {
  position: relative;
  z-index: 1;
  display: flex;
  max-width: 1320px;
  margin: 0 auto;
  padding: 26px 24px 80px;
  gap: 28px;
  align-items: flex-start;
}

.sidebar {
  flex: 0 0 268px;
  position: sticky;
  top: calc(var(--topbar-h) + 18px);
  max-height: calc(100vh - var(--topbar-h) - 36px);
  overflow-y: auto;
  padding: 18px 14px;
  border-radius: var(--radius-lg);
}

.nav-pinned {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.nav-link-pinned { font-weight: 700; }

.nav-group { margin-bottom: 4px; }
.nav-group-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 9px 8px;
  border-radius: var(--radius-sm);
  color: var(--ink-soft);
  transition: background 0.15s ease;
}
.nav-group-toggle:hover { background: var(--tint); }
.nav-group-title {
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.chevron { transition: transform 0.2s ease; flex-shrink: 0; }
.nav-group.expanded .chevron { transform: rotate(90deg); }

.nav-group-list {
  list-style: none;
  margin: 0;
  padding: 2px 0 4px 4px;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.28s ease;
}
.nav-group.expanded .nav-group-list { max-height: 800px; }

.sidebar-nav ul { list-style: none; margin: 0; padding: 0; }
.nav-link {
  display: block;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  color: var(--ink);
  text-decoration: none;
  font-size: 13.5px;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}
.nav-link:hover {
  background: var(--tint-strong);
  color: var(--blue-deep);
  transform: translateX(2px);
}
.nav-link.active {
  background: linear-gradient(135deg, var(--blue-accent), var(--blue-deep));
  color: var(--white);
  font-weight: 600;
  box-shadow: 0 3px 10px rgba(10, 95, 180, 0.28);
}

.content-wrap { flex: 1 1 auto; min-width: 0; }
.content { padding: 42px 52px 30px; border-radius: var(--radius-lg); }

.breadcrumbs {
  font-size: 12.5px;
  color: var(--ink-faint);
  margin-bottom: 22px;
}
.breadcrumbs a { color: var(--blue-accent); text-decoration: none; }
.breadcrumbs a:hover { text-decoration: underline; }
.crumb-sep { margin: 0 8px; opacity: 0.5; }

.content h1, .content h2, .content h3, .content h4 {
  color: var(--ink);
  letter-spacing: -0.015em;
  font-weight: 700;
}
.content h1 {
  font-size: 32px;
  margin: 0 0 18px;
  background: linear-gradient(120deg, var(--blue-deep), var(--blue-accent) 60%, #6ab6ee);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.content h2 { font-size: 22px; margin: 38px 0 14px; padding-top: 6px; border-top: 1px solid var(--line); }
.content h2:first-of-type { border-top: none; padding-top: 0; }
.content h3 { font-size: 17.5px; margin: 26px 0 10px; color: var(--blue-deep); }
.content h4 { font-size: 15px; margin: 20px 0 8px; }

.content p, .content li { color: var(--ink); font-size: 15px; }
.content ul, .content ol { padding-left: 22px; }
.content li { margin: 4px 0; }

.content a { color: var(--blue-deep); text-decoration: none; border-bottom: 1px solid var(--underline); }
.content a:hover { color: var(--blue-accent); border-bottom-color: var(--blue-accent); }

/* Inline code: neutral grey chip */
.content code {
  font-family: "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  background: var(--grey-bg);
  border: 1px solid var(--grey-border);
  color: var(--ink);
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 13px;
}

/* Code blocks: grey panel with a soft drop shadow in both themes */
.content pre {
  background: var(--grey-bg);
  border: 1px solid var(--grey-border);
  color: var(--ink);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  overflow-x: auto;
  box-shadow: var(--grey-shadow);
  margin: 18px 0;
}
.content pre code {
  background: transparent;
  border: none;
  color: inherit;
  padding: 0;
  font-size: 13px;
}

.content table {
  width: 100%;
  border-collapse: collapse;
  margin: 18px 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--grey-shadow);
}
.content th, .content td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--grey-border);
  text-align: left;
  font-size: 13.5px;
  vertical-align: top;
}
.content th {
  background: var(--tint-strong);
  color: var(--blue-deep);
  font-weight: 700;
  font-size: 12.5px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.content tr:nth-child(even) td { background: var(--surface-soft); }

.content blockquote {
  margin: 18px 0;
  padding: 12px 18px;
  border-left: 3px solid var(--blue-accent);
  background: var(--tint);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--ink-soft);
}

.content hr { border: none; border-top: 1px solid var(--line); margin: 32px 0; }

.dir-listing { list-style: none; padding: 0; }
.dir-listing li { margin: 6px 0; }
.dir-listing a {
  display: inline-block;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: var(--surface);
  border: 1px solid var(--grey-border);
  color: var(--blue-deep);
  text-decoration: none;
  font-size: 14px;
  box-shadow: var(--grey-shadow);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.dir-listing a:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(24, 66, 115, 0.15); }

.page-footer {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.edit-link {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink-faint);
  text-decoration: none;
  border-bottom: none;
}
.edit-link:hover { color: var(--blue-deep); }

.nav-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line-strong);
  background: var(--surface-soft);
  cursor: pointer;
  padding: 0;
}
.nav-toggle span {
  display: block;
  height: 2px;
  margin: 0 7px;
  background: var(--blue-deep);
  border-radius: 2px;
}

@media (max-width: 860px) {
  .topbar-inner { padding: 0 14px; }
  .brand-text { display: none; }
  .layout { flex-direction: column; padding: 18px 14px 60px; }
  .sidebar {
    position: fixed;
    left: 14px;
    right: 14px;
    top: calc(var(--topbar-h) + 10px);
    z-index: 15;
    max-height: 72vh;
    display: none;
  }
  .sidebar.open { display: block; }
  .nav-toggle { display: flex; }
  .content { padding: 26px 20px; }
  .content h1 { font-size: 25px; }
  .topbar-github { padding: 6px 10px; font-size: 12px; }
}
"""

JS = """
function applyHljsTheme(theme) {
  var light = document.getElementById('hljs-light-theme');
  var dark = document.getElementById('hljs-dark-theme');
  if (light) light.disabled = theme === 'dark';
  if (dark) dark.disabled = theme !== 'dark';
}

document.addEventListener('DOMContentLoaded', function () {
  var currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  applyHljsTheme(currentTheme);

  if (window.hljs) {
    document.querySelectorAll('pre code').forEach(function (block) {
      hljs.highlightElement(block);
    });
  }

  var themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.setAttribute('aria-pressed', currentTheme === 'dark' ? 'true' : 'false');
    themeToggle.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      applyHljsTheme(next);
      themeToggle.setAttribute('aria-pressed', next === 'dark' ? 'true' : 'false');
    });
  }

  var toggle = document.getElementById('navToggle');
  var sidebar = document.getElementById('sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
  }

  var groups = document.querySelectorAll('.nav-group');
  groups.forEach(function (group) {
    var key = 'navgroup:' + group.dataset.group;
    var stored = null;
    try { stored = localStorage.getItem(key); } catch (e) {}
    var hasActive = group.querySelector('.nav-link.active') !== null;
    if (hasActive) {
      group.classList.add('expanded');
    } else if (stored === '1') {
      group.classList.add('expanded');
    } else if (stored === '0') {
      group.classList.remove('expanded');
    }
    var btn = group.querySelector('.nav-group-toggle');
    if (btn) {
      btn.setAttribute('aria-expanded', group.classList.contains('expanded') ? 'true' : 'false');
      btn.addEventListener('click', function () {
        var expanded = group.classList.toggle('expanded');
        btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        try { localStorage.setItem(key, expanded ? '1' : '0'); } catch (e) {}
      });
    }
  });
});
"""


if __name__ == "__main__":
    sys.exit(main())
