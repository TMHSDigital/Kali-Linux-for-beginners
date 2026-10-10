/* =========================================================================
   Kali Linux for Beginners: progressive enhancement for the static site.
   Every page is pre-rendered HTML; this adds the theme toggle, mobile nav,
   copy buttons, the outline's scroll tracking, full-text search that jumps to
   the matching section, per-browser progress tracking (with "continue where
   you left off"), back-to-top, and 404 suggestions.
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
  menuToggle.addEventListener("click", () => {
    toggleSidebar();
    // Move focus into the drawer once it is visible (it is visibility:hidden until the class applies).
    if (sidebar.classList.contains("open")) {
      requestAnimationFrame(() => (sidebar.querySelector("a.active") || sidebar.querySelector("a"))?.focus({ preventScroll: true }));
    }
  });
  scrim.addEventListener("click", () => toggleSidebar(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar.classList.contains("open")) { toggleSidebar(false); menuToggle.focus(); }
  });
  // Picking a page closes the drawer; so does widening the window past the drawer breakpoint.
  sidebar.addEventListener("click", (e) => { if (e.target.closest("a")) toggleSidebar(false); });
  if (!document.body.classList.contains("page-landing")) {
    window.matchMedia("(min-width: 961px)").addEventListener("change", (e) => { if (e.matches) toggleSidebar(false); });
  }
  // Start with the current page in view in a long sidebar.
  const activeNav = sidebar.querySelector("a.active");
  if (activeNav && activeNav.offsetTop > sidebar.clientHeight * 0.6) {
    sidebar.scrollTop = activeNav.offsetTop - sidebar.clientHeight / 3;
  }

  /* ---------------- Copy buttons (in each code block's terminal bar) ---------------- */
  document.querySelectorAll(".markdown .codeblock").forEach((block) => {
    const pre = block.querySelector("pre");
    const bar = block.querySelector(".codeblock-bar");
    if (!pre || !bar) return;
    const btn = el("button", { class: "copy-btn", type: "button", text: "copy",
                               "aria-label": "Copy code to clipboard" });
    btn.addEventListener("click", async () => {
      const code = pre.querySelector("code");
      try {
        await navigator.clipboard.writeText((code || pre).innerText);
        btn.textContent = "copied";
        btn.classList.add("copied");
        setTimeout(() => { btn.textContent = "copy"; btn.classList.remove("copied"); }, 1600);
      } catch (_) { btn.textContent = "press ctrl-c"; }
    });
    bar.appendChild(btn);
  });

  /* ---------------- "On this page" scroll-spy ---------------- */
  const tocLinks = [...document.querySelectorAll(".toc a[href^='#']")];
  if (tocLinks.length) {
    const pairs = tocLinks
      .map((a) => [a, document.getElementById(decodeURIComponent(a.hash.slice(1)))])
      .filter(([, h]) => h);
    let ticking = false;
    const spy = () => {
      ticking = false;
      let current = pairs[0];
      for (const pair of pairs) {
        if (pair[1].getBoundingClientRect().top <= window.innerHeight * 0.3) current = pair; else break;
      }
      // At the very bottom, the last sections can't scroll up far enough: pick the last one.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) current = pairs[pairs.length - 1];
      tocLinks.forEach((a) => a.classList.toggle("active", current && a === current[0]));
    };
    window.addEventListener("scroll", () => {
      if (!ticking) { ticking = true; requestAnimationFrame(spy); }
    }, { passive: true });
    spy();
  }
  // The folded outline (narrow screens) closes once you pick a section.
  const tocInline = $(".toc-inline");
  if (tocInline) tocInline.addEventListener("click", (e) => { if (e.target.closest("a")) tocInline.open = false; });

  /* ---------------- Heading links: clicking "#" also copies the URL ---------------- */
  document.querySelectorAll(".markdown .anchor").forEach((a) => {
    a.addEventListener("click", () => {
      if (!navigator.clipboard) return;
      navigator.clipboard.writeText(location.href.split("#")[0] + a.getAttribute("href")).then(() => {
        a.classList.add("copied");
        setTimeout(() => a.classList.remove("copied"), 1400);
      }, () => {});
    });
  });

  /* ---------------- Back to top (long pages) ---------------- */
  if (document.body.classList.contains("page-doc")) {
    const toTop = el("button", { class: "to-top", type: "button", "aria-label": "Back to top", title: "Back to top",
                                 hidden: "" });
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    Object.entries({ viewBox: "0 0 24 24", width: "18", height: "18", fill: "none", stroke: "currentColor",
                     "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round",
                     "aria-hidden": "true" }).forEach(([k, v]) => svg.setAttribute(k, v));
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", "M12 19V5M6 11l6-6 6 6");
    svg.appendChild(path);
    toTop.appendChild(svg);
    toTop.addEventListener("click", () => {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
      const doc = $("#doc");
      if (doc) { doc.setAttribute("tabindex", "-1"); doc.focus({ preventScroll: true }); }
    });
    document.body.appendChild(toTop);
    let queued = false;
    window.addEventListener("scroll", () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => { queued = false; toTop.hidden = window.scrollY < window.innerHeight * 1.5; });
    }, { passive: true });
  }

  /* ---------------- Progress tracking ---------------- */
  const navLinks = [...document.querySelectorAll(".nav-tree a[data-doc]")];
  const allDocs = navLinks.map((a) => a.dataset.doc);
  function renderProgress() {
    const done = new Set(store.get("done", []));
    navLinks.forEach((a) => a.classList.toggle("done", done.has(a.dataset.doc)));
    document.querySelectorAll(".module[data-section]").forEach((row) => {
      const links = [...new Set([...row.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")))];
      const n = links.filter((h) => done.has(h)).length;
      const label = row.querySelector("[data-progress]");
      if (label) {
        label.textContent = n ? (n === links.length ? "complete" : `${n} of ${links.length} done`) : "";
        label.classList.toggle("is-done", n === links.length);
      }
    });
    const count = allDocs.filter((d) => done.has(d)).length;
    const wrap = $(".progress-wrap");
    if (wrap) {
      wrap.hidden = count === 0;
      $("#progress-text").textContent = `${count} of ${allDocs.length} complete`;
      $("#progress-fill").style.width = `${Math.round((100 * count) / Math.max(allDocs.length, 1))}%`;
    }
    // Per-module "done / total" beside each module heading in the sidebar.
    document.querySelectorAll(".nav-section").forEach((sec) => {
      const h = sec.querySelector("h3");
      if (!h || !sec.querySelector(".nav-num")) return;
      const docs = [...sec.querySelectorAll("a[data-doc]")].map((a) => a.dataset.doc);
      const n = docs.filter((d) => done.has(d)).length;
      let badge = h.querySelector(".nav-count");
      if (!badge) { badge = el("span", { class: "nav-count" }); h.appendChild(badge); }
      badge.textContent = n ? `${n}/${docs.length}` : "";
      badge.classList.toggle("is-done", n === docs.length);
    });
    const btn = $("#mark-done");
    if (btn) {
      const isDone = done.has(DOC);
      btn.setAttribute("aria-pressed", String(isDone));
      btn.textContent = isDone ? "Completed (undo)" : "Mark as complete";
      const doneNext = $("#done-next");
      if (doneNext) doneNext.hidden = isDone;
    }
    renderContinue(done);
  }

  // Home page: once you have started, the main button picks up at the first page you haven't finished.
  const startBtn = $("#start-btn");
  const startDefault = startBtn && { href: startBtn.getAttribute("href"), label: startBtn.firstElementChild.textContent };
  function renderContinue(done) {
    if (!startBtn) return;
    const pages = [...document.querySelectorAll(".nav-section")]
      .filter((sec) => sec.querySelector(".nav-num"))
      .flatMap((sec) => [...sec.querySelectorAll("a[data-doc]")].map((a) => ({ a, num: sec.querySelector(".nav-num").textContent })));
    const next = pages.find((p) => !done.has(p.a.dataset.doc));
    const started = pages.some((p) => done.has(p.a.dataset.doc));
    if (started && next) {
      startBtn.setAttribute("href", next.a.getAttribute("href"));
      startBtn.firstElementChild.textContent = `Continue module ${next.num}`;
    } else {
      startBtn.setAttribute("href", startDefault.href);
      startBtn.firstElementChild.textContent = started ? "Review module 01" : startDefault.label;
    }
  }
  const resetBtn = $("#progress-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (window.confirm("Clear your progress in this browser?")) { store.set("done", []); renderProgress(); }
    });
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
  const doneNextLink = $("#done-next");
  if (doneNextLink && DOC) {
    // Record the page as done, then let the link navigate to the next one.
    doneNextLink.addEventListener("click", () => store.set("done", [...new Set([...store.get("done", []), DOC])]));
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

  // The heading of the section that contains text offset `pos` (null = above the first heading).
  function sectionAt(d, pos) {
    let id = "";
    for (const [pid, start] of d.parts || []) { if (start <= pos) id = pid; else break; }
    return id ? d.headings.find((h) => h.id === id) || null : null;
  }

  function search(q) {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length || !index) return [];
    const phrase = terms.join(" ");
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
        // Prefer the whole query as typed ("nmap -sS"), then the first word on its own.
        const phraseAt = terms.length > 1 ? d.lower.indexOf(phrase) : -1;
        if (phraseAt >= 0) score += 25;
        const key = phraseAt >= 0 ? phrase : terms[0];
        const at = phraseAt >= 0 ? phraseAt : d.lower.indexOf(terms[0]);
        // Link to a heading that names the term, else to the section the text match sits in.
        const heading = d.headings.find((h) => h.text.toLowerCase().includes(key))
          || (at >= 0 ? sectionAt(d, at) : null);
        return { d, score, heading, snip: snippet(d.text, d.lower, key) };
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
    if ((e.key === "/" && !typing) || (e.key.toLowerCase() === "k" && (e.ctrlKey || e.metaKey))) {
      e.preventDefault(); input.focus(); input.select();
    }
  });

  /* ---------------- 404: suggest pages whose URL or title shares words with the bad path ---------------- */
  const suggest = $("#suggest");
  if (suggest) {
    const skip = new Set(["kali", "linux", "for", "beginners", "html", "index", "readme", "and", "the"]);
    const words = decodeURIComponent(location.pathname).toLowerCase().split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2 && !skip.has(w));
    if (words.length) {
      loadIndex().then((idx) => {
        const hits = idx
          .map((d) => ({ d, s: words.filter((w) => `${d.url} ${d.titleLower}`.includes(w)).length }))
          .filter((x) => x.s)
          .sort((a, b) => b.s - a.s)
          .slice(0, 5);
        if (!hits.length) return;
        const ul = suggest.querySelector("ul");
        hits.forEach(({ d }) => ul.appendChild(el("li", {}, el("a", { href: ROOT + d.url, text: d.title }))));
        suggest.hidden = false;
      });
    }
  }

  /* ---------------- Offline support ---------------- */
  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register(ROOT + "sw.js").catch(() => {});
  }
})();
