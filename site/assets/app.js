/* =========================================================================
   Kali Linux for Beginners — docs SPA
   Loads a generated manifest.json, renders Markdown client-side, and builds
   navigation dynamically. Nothing about the content is hardcoded here.
   ========================================================================= */
(() => {
  "use strict";

  const state = {
    manifest: null,
    flat: [],          // flattened [{title, path, section}] for routing/search
    current: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const el = {
    doc: $("#doc"),
    navTree: $("#nav-tree"),
    navMeta: $("#nav-meta"),
    search: $("#search"),
    searchResults: $("#search-results"),
    themeToggle: $("#theme-toggle"),
    menuToggle: $("#menu-toggle"),
    sidebar: $("#sidebar"),
    scrim: $("#scrim"),
    prev: $("#prev"),
    next: $("#next"),
    repoLink: $("#repo-link"),
    editLink: $("#edit-link"),
    hljsTheme: $("#hljs-theme"),
  };

  const HLJS = {
    dark: "https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css",
    light: "https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github.min.css",
  };

  /* ---------------- Theme ---------------- */
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    el.themeToggle.textContent = theme === "dark" ? "🌙" : "☀️";
    el.hljsTheme.href = HLJS[theme] || HLJS.dark;
    try { localStorage.setItem("theme", theme); } catch (_) {}
  }
  function initTheme() {
    let theme = "dark";
    try {
      const saved = localStorage.getItem("theme");
      if (saved) theme = saved;
      else if (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches)
        theme = "light";
    } catch (_) {}
    applyTheme(theme);
  }
  el.themeToggle.addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    applyTheme(cur === "dark" ? "light" : "dark");
    if (state.current) highlightAll();
  });

  /* ---------------- Manifest & nav ---------------- */
  async function loadManifest() {
    const res = await fetch("manifest.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(`manifest.json ${res.status}`);
    const m = await res.json();
    state.manifest = m;
    state.flat = [];
    m.sections.forEach((sec) =>
      sec.items.forEach((it) =>
        state.flat.push({ ...it, section: sec.title, sectionId: sec.id })
      )
    );

    if (m.site && m.site.repo) {
      el.repoLink.href = `https://github.com/${m.site.repo}`;
    }
    document.title = `${m.site.title} — ${m.site.subtitle}`;
    renderNav();
    if (m.site && m.site.generated) {
      const d = new Date(m.site.generated);
      el.navMeta.textContent = `${state.flat.length} documents · updated ${d.toLocaleDateString()}`;
    }
  }

  function renderNav() {
    const frag = document.createDocumentFragment();
    state.manifest.sections.forEach((sec) => {
      const wrap = document.createElement("div");
      wrap.className = "nav-section";
      const h = document.createElement("h3");
      h.textContent = sec.title;
      wrap.appendChild(h);
      const ul = document.createElement("ul");
      sec.items.forEach((it) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = "#/" + it.path;
        a.textContent = it.title;
        a.dataset.path = it.path;
        li.appendChild(a);
        ul.appendChild(li);
      });
      wrap.appendChild(ul);
      frag.appendChild(wrap);
    });
    el.navTree.innerHTML = "";
    el.navTree.appendChild(frag);
  }

  function markActiveNav(path) {
    el.navTree.querySelectorAll("a").forEach((a) =>
      a.classList.toggle("active", a.dataset.path === path)
    );
  }

  /* ---------------- Link rewriting ---------------- */
  // Resolve a relative link found inside a doc against the doc's own path,
  // so cross-references (../foo/bar.md, lab-exercises.md, ../scripts/x.py)
  // route correctly inside the SPA or out to GitHub.
  function resolvePath(fromPath, href) {
    const base = fromPath.split("/").slice(0, -1);
    const parts = href.split("/");
    for (const p of parts) {
      if (p === "." || p === "") continue;
      if (p === "..") base.pop();
      else base.push(p);
    }
    return base.join("/");
  }

  function rewriteLinks(container, fromPath) {
    const repo = state.manifest.site && state.manifest.site.repo;
    container.querySelectorAll("a[href]").forEach((a) => {
      const raw = a.getAttribute("href");
      if (!raw) return;
      if (/^(https?:|mailto:|#)/i.test(raw)) {
        if (/^https?:/i.test(raw)) { a.target = "_blank"; a.rel = "noopener"; }
        return;
      }
      // Strip any in-page anchor for resolution, re-append after.
      const [pathPart, anchor] = raw.split("#");
      let target = resolvePath(fromPath, pathPart || "");
      // Directory link → its README.
      if (target && !/\.[a-z0-9]+$/i.test(target)) {
        target = target.replace(/\/$/, "") + "/README.md";
      }
      const known = state.flat.some((f) => f.path === target);
      if (target.endsWith(".md") && known) {
        a.setAttribute("href", "#/" + target + (anchor ? "#" + anchor : ""));
      } else if (repo) {
        // Non-doc file (script, etc.) → link to it on GitHub.
        a.setAttribute("href", `https://github.com/${repo}/blob/main/${target}`);
        a.target = "_blank"; a.rel = "noopener";
      }
    });
  }

  /* ---------------- Rendering ---------------- */
  function highlightAll() {
    if (!window.hljs) return;
    el.doc.querySelectorAll("pre code").forEach((block) => {
      block.removeAttribute("data-highlighted");
      try { window.hljs.highlightElement(block); } catch (_) {}
    });
  }

  function addCopyButtons() {
    el.doc.querySelectorAll("pre").forEach((pre) => {
      if (pre.querySelector(".copy-btn")) return;
      const btn = document.createElement("button");
      btn.className = "copy-btn";
      btn.type = "button";
      btn.textContent = "Copy";
      btn.addEventListener("click", async () => {
        const code = pre.querySelector("code");
        try {
          await navigator.clipboard.writeText(code ? code.innerText : pre.innerText);
          btn.textContent = "Copied!";
          btn.classList.add("copied");
          setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1500);
        } catch (_) { btn.textContent = "Press ⌘/Ctrl-C"; }
      });
      pre.appendChild(btn);
    });
  }

  function slugify(text) {
    return text.toLowerCase().trim()
      .replace(/[^\w\s-]/g, "").replace(/\s+/g, "-");
  }
  function addHeadingAnchors() {
    el.doc.querySelectorAll("h2, h3, h4").forEach((h) => {
      if (!h.id) h.id = slugify(h.textContent);
    });
  }

  async function renderDoc(path) {
    const known = state.flat.find((f) => f.path === path);
    if (!known) {
      el.doc.innerHTML = `<h1>Not found</h1><p class="muted">No document at <code>${path}</code>.</p>`;
      return;
    }
    el.doc.innerHTML = `<p class="muted">Loading…</p>`;
    let md;
    try {
      const res = await fetch("content/" + path, { cache: "no-cache" });
      if (!res.ok) throw new Error(res.status);
      md = await res.text();
    } catch (e) {
      el.doc.innerHTML = `<h1>Error</h1><p class="muted">Could not load <code>${path}</code> (${e.message}).</p>`;
      return;
    }

    window.marked.setOptions({ gfm: true, breaks: false, headerIds: false, mangle: false });
    el.doc.innerHTML = window.marked.parse(md);

    rewriteLinks(el.doc, path);
    addHeadingAnchors();
    addCopyButtons();
    highlightAll();
    markActiveNav(path);
    updatePager(path);
    updateFooter(path, known);
    state.current = path;

    // Scroll to anchor or top.
    const hashAnchor = location.hash.split("#")[2];
    if (hashAnchor) {
      const target = document.getElementById(hashAnchor);
      if (target) target.scrollIntoView();
      else window.scrollTo(0, 0);
    } else {
      window.scrollTo(0, 0);
    }
  }

  function updatePager(path) {
    const i = state.flat.findIndex((f) => f.path === path);
    const prev = state.flat[i - 1];
    const next = state.flat[i + 1];
    if (prev) {
      el.prev.hidden = false;
      el.prev.href = "#/" + prev.path;
      el.prev.innerHTML = `<small>← Previous</small><span>${prev.title}</span>`;
    } else { el.prev.hidden = true; }
    if (next) {
      el.next.hidden = false;
      el.next.href = "#/" + next.path;
      el.next.innerHTML = `<small>Next →</small><span>${next.title}</span>`;
    } else { el.next.hidden = true; }
  }

  function updateFooter(path, known) {
    const repo = state.manifest.site && state.manifest.site.repo;
    if (repo) {
      el.editLink.innerHTML =
        `<a href="https://github.com/${repo}/blob/main/${path}" target="_blank" rel="noopener">Edit this page on GitHub ↗</a>`;
    }
  }

  /* ---------------- Search ---------------- */
  function runSearch(q) {
    q = q.trim().toLowerCase();
    if (!q) { el.searchResults.hidden = true; el.searchResults.innerHTML = ""; return; }
    const matches = state.flat
      .map((f) => {
        const hay = (f.title + " " + f.section + " " + f.path).toLowerCase();
        const idx = hay.indexOf(q);
        return idx === -1 ? null : { f, score: idx };
      })
      .filter(Boolean)
      .sort((a, b) => a.score - b.score)
      .slice(0, 12);

    if (!matches.length) {
      el.searchResults.innerHTML = `<li><a class="muted">No matches</a></li>`;
      el.searchResults.hidden = false;
      return;
    }
    el.searchResults.innerHTML = matches
      .map(({ f }) =>
        `<li><a href="#/${f.path}">${f.title}<small>${f.section}</small></a></li>`
      ).join("");
    el.searchResults.hidden = false;
  }

  el.search.addEventListener("input", (e) => runSearch(e.target.value));
  el.search.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { el.search.value = ""; runSearch(""); el.search.blur(); }
    if (e.key === "Enter") {
      const first = el.searchResults.querySelector("a[href]");
      if (first) { location.hash = first.getAttribute("href"); closeSearch(); }
    }
  });
  function closeSearch() { el.searchResults.hidden = true; el.search.value = ""; }
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrap")) el.searchResults.hidden = true;
  });
  // "/" focuses search from anywhere.
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== el.search) {
      e.preventDefault(); el.search.focus();
    }
  });

  /* ---------------- Mobile nav ---------------- */
  function toggleSidebar(open) {
    const show = open ?? !el.sidebar.classList.contains("open");
    el.sidebar.classList.toggle("open", show);
    el.scrim.hidden = !show;
    el.menuToggle.setAttribute("aria-expanded", String(show));
  }
  el.menuToggle.addEventListener("click", () => toggleSidebar());
  el.scrim.addEventListener("click", () => toggleSidebar(false));
  el.navTree.addEventListener("click", (e) => {
    if (e.target.closest("a")) toggleSidebar(false);
  });

  /* ---------------- Router ---------------- */
  function currentRoute() {
    const h = location.hash.replace(/^#\/?/, "");
    return h.split("#")[0] || null;
  }
  function route() {
    const path = currentRoute();
    if (!path) {
      // Default to the first document (Home / root README).
      const first = state.flat[0];
      if (first) { location.replace("#/" + first.path); return; }
    }
    renderDoc(path);
    el.searchResults.hidden = true;
  }
  window.addEventListener("hashchange", route);

  /* ---------------- Boot ---------------- */
  async function boot() {
    initTheme();
    try {
      await loadManifest();
      route();
    } catch (e) {
      el.doc.innerHTML =
        `<h1>Failed to load</h1><p class="muted">${e.message}. If you opened this file directly, serve it over HTTP (e.g. <code>python -m http.server</code>) — browsers block <code>fetch()</code> on <code>file://</code>.</p>`;
    }
  }
  boot();
})();
