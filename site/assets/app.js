/* =========================================================================
   Kali Linux for Beginners: progressive enhancement for the static site.
   Every page is pre-rendered HTML; this adds the theme toggle, mobile nav,
   copy buttons, full-text search, and per-browser progress tracking.
   No innerHTML with untrusted strings: everything is built with DOM APIs.
   ========================================================================= */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const ROOT = document.body.dataset.root || "./";
  const DOC = document.body.dataset.doc || "";

  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); }
      catch (_) { return fallback; }
    },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {} },
  };

  const el = (tag, props = {}, ...children) => {
    const node = document.createElement(tag);
    Object.entries(props).forEach(([k, v]) => {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    });
    children.forEach((c) => c && node.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
    return node;
  };

  /* ---------------- Theme ---------------- */
  $("#theme-toggle").addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (_) {}
  });

  /* ---------------- Mobile nav ---------------- */
  const sidebar = $("#sidebar"), scrim = $("#scrim"), menuToggle = $("#menu-toggle");
  function toggleSidebar(open) {
    const show = open ?? !sidebar.classList.contains("open");
    sidebar.classList.toggle("open", show);
    scrim.hidden = !show;
    menuToggle.setAttribute("aria-expanded", String(show));
  }
  menuToggle.addEventListener("click", () => toggleSidebar());
  scrim.addEventListener("click", () => toggleSidebar(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("open")) toggleSidebar(false);
  });

  /* ---------------- Copy buttons ---------------- */
  document.querySelectorAll(".markdown pre").forEach((pre) => {
    const btn = el("button", { class: "copy-btn", type: "button", text: "Copy",
                               "aria-label": "Copy code to clipboard" });
    btn.addEventListener("click", async () => {
      const code = pre.querySelector("code");
      try {
        await navigator.clipboard.writeText((code || pre).innerText);
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1500);
      } catch (_) { btn.textContent = "Press Ctrl-C"; }
    });
    pre.appendChild(btn);
  });

  /* ---------------- Progress tracking ---------------- */
  const navLinks = [...document.querySelectorAll(".nav-tree a[data-doc]")];
  const allDocs = navLinks.map((a) => a.dataset.doc);
  function renderProgress() {
    const done = new Set(store.get("done", []));
    navLinks.forEach((a) => a.classList.toggle("done", done.has(a.dataset.doc)));
    document.querySelectorAll(".card[data-section]").forEach((card) => {
      const links = [...card.querySelectorAll("a[href]")].map((a) => a.getAttribute("href"));
      card.classList.toggle("done", links.length > 0 && links.every((h) => done.has(h)));
    });
    const count = allDocs.filter((d) => done.has(d)).length;
    const wrap = $(".progress-wrap");
    if (wrap) {
      wrap.hidden = count === 0;
      $("#progress-text").textContent = `${count} of ${allDocs.length} complete`;
      $("#progress-fill").style.width = `${Math.round((100 * count) / Math.max(allDocs.length, 1))}%`;
    }
    const btn = $("#mark-done");
    if (btn) {
      const isDone = done.has(DOC);
      btn.setAttribute("aria-pressed", String(isDone));
      btn.textContent = isDone ? "Completed ✓ (undo)" : "Mark as complete";
    }
  }
  const markBtn = $("#mark-done");
  if (markBtn && DOC) {
    markBtn.addEventListener("click", () => {
      const done = new Set(store.get("done", []));
      if (done.has(DOC)) done.delete(DOC); else done.add(DOC);
      store.set("done", [...done]);
      renderProgress();
    });
  }
  renderProgress();

  /* ---------------- Full-text search (WAI-ARIA combobox) ---------------- */
  const input = $("#search"), list = $("#search-results"), status = $("#search-status");
  let index = null, loading = null, results = [], active = -1;

  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (!loading) {
      loading = fetch(ROOT + "search-index.json")
        .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then((data) => {
          index = data.map((d) => ({ ...d, lower: d.text.toLowerCase(),
                                     titleLower: d.title.toLowerCase() }));
          return index;
        })
        .catch(() => { loading = null; return []; });
    }
    return loading;
  }

  function snippet(text, lower, term) {
    const i = lower.indexOf(term);
    if (i < 0) return { before: text.slice(0, 120), match: "", after: "" };
    const start = Math.max(0, i - 50);
    return {
      before: (start > 0 ? "…" : "") + text.slice(start, i),
      match: text.slice(i, i + term.length),
      after: text.slice(i + term.length, i + term.length + 70) + "…",
    };
  }

  function search(q) {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length || !index) return [];
    return index
      .map((d) => {
        let score = 0;
        for (const t of terms) {
          const inTitle = d.titleLower.includes(t);
          const heading = d.headings.find((h) => h.text.toLowerCase().includes(t));
          const count = d.lower.split(t).length - 1;
          if (!inTitle && !heading && !count) return null;
          score += (inTitle ? 50 : 0) + (heading ? 20 : 0) + Math.min(count, 10);
        }
        const heading = d.headings.find((h) => h.text.toLowerCase().includes(terms[0]));
        return { d, score, heading, snip: snippet(d.text, d.lower, terms[0]) };
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)
      .slice(0, 10);
  }

  function hrefFor(r) {
    return ROOT + r.d.url + (r.heading ? "#" + r.heading.id : "");
  }

  function setActive(i) {
    const items = [...list.querySelectorAll("[role=option]")];
    items.forEach((it, n) => it.setAttribute("aria-selected", String(n === i)));
    active = i;
    if (items[i]) {
      input.setAttribute("aria-activedescendant", items[i].id);
      items[i].scrollIntoView({ block: "nearest" });
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  }

  function close() {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  }

  function render(q) {
    list.replaceChildren();
    if (!q.trim()) { close(); status.textContent = ""; return; }
    results = search(q);
    if (!results.length) {
      list.appendChild(el("li", { class: "search-empty", role: "presentation", text: "No matches" }));
    }
    results.forEach((r, i) => {
      const a = el("a", { href: hrefFor(r), tabindex: "-1" },
        el("span", { class: "sr-title", text: r.d.title }),
        el("small", { text: r.heading ? `${r.d.section} › ${r.heading.text}` : r.d.section }),
        el("span", { class: "sr-snippet" }, r.snip.before,
           r.snip.match ? el("mark", { text: r.snip.match }) : null, r.snip.after));
      list.appendChild(el("li", { id: `sr-${i}`, role: "option", "aria-selected": "false" }, a));
    });
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    status.textContent = results.length ? `${results.length} results` : "No results";
    setActive(-1);
  }

  input.addEventListener("focus", loadIndex, { once: true });
  input.addEventListener("input", () => loadIndex().then(() => render(input.value)));
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && results.length) {
      e.preventDefault(); setActive(Math.min(active + 1, results.length - 1));
    } else if (e.key === "ArrowUp" && results.length) {
      e.preventDefault(); setActive(Math.max(active - 1, 0));
    } else if (e.key === "Enter") {
      const r = results[active >= 0 ? active : 0];
      if (r) { e.preventDefault(); location.href = hrefFor(r); }
    } else if (e.key === "Escape") {
      input.value = ""; render(""); input.blur();
    }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search-wrap")) close(); });
  document.addEventListener("keydown", (e) => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    if (e.key === "/" && !typing) { e.preventDefault(); input.focus(); }
  });

  /* ---------------- Offline support ---------------- */
  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register(ROOT + "sw.js").catch(() => {});
  }
})();
