/* =========================================================================
   Kali Linux for Beginners: the site's pure logic (search ranking, progress
   labels, progress-file parsing). No DOM access, so tests/app-logic.test.js
   can run it under `node --test`. In the browser it sets window.KaliSite for
   app.js; under Node it is a CommonJS module.
   ========================================================================= */
((root, factory) => {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.KaliSite = api;
})(typeof self !== "undefined" ? self : globalThis, () => {
  "use strict";

  // Lower-case copies of each search-index entry, computed once per page load.
  function prepareIndex(data) {
    return data.map((d) => ({ ...d, lower: d.text.toLowerCase(), titleLower: d.title.toLowerCase() }));
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

  // Top 10 entries of a prepared index that contain every term of `q`, best first.
  function search(index, q) {
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

  // Progress of one module: how many of its own pages are in the `done` set.
  function moduleProgress(pages, done) {
    const unique = [...new Set(pages)];
    const n = unique.filter((p) => done.has(p)).length;
    const total = unique.length;
    const label = n ? (n === total ? "complete" : `${n} of ${total} done`) : "";
    return { n, total, label, complete: n === total };
  }

  const PROGRESS_FILE = "kali-beginners-progress.json";

  // Pages from an exported progress file (or a bare JSON list) that this course knows.
  function parseProgress(text, allDocs) {
    let data;
    try { data = JSON.parse(text); } catch (_) { throw new Error("the file is not valid JSON."); }
    const list = Array.isArray(data) ? data : data && data.done;
    if (!Array.isArray(list)) throw new Error(`it is not a ${PROGRESS_FILE} export.`);
    const known = new Set(allDocs);
    const pages = list.filter((d) => typeof d === "string" && known.has(d));
    if (!pages.length) throw new Error("it lists no pages from this course.");
    return pages;
  }

  return { prepareIndex, snippet, sectionAt, search, moduleProgress, parseProgress, PROGRESS_FILE };
});
