// Unit tests for site/assets/logic.js (search ranking, sections, progress).
// Node's built-in runner, no packages needed:  node --test tests/app-logic.test.js
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { prepareIndex, snippet, sectionAt, search, moduleProgress, parseProgress } =
  require(path.join(__dirname, "..", "site", "assets", "logic.js"));

// A tiny search index in the shape build-site.py writes to search-index.json.
const INDEX = prepareIndex([
  {
    url: "03-recon/", title: "03: Network Recon & Nmap",
    text: "Intro text. Run nmap -sS against the lab. Service detection with nmap -sV.",
    headings: [{ id: "syn-scan", text: "SYN scan" }, { id: "versions", text: "Versions" }],
    parts: [["syn-scan", 12], ["versions", 42]],
  },
  {
    url: "05-web/", title: "05: Web Testing",
    text: "Use nmap to find the web port first. Then nmap the host again. Nmap nmap nmap.",
    headings: [{ id: "find", text: "Finding the server" }],
    parts: [["find", 0]],
  },
  {
    url: "cheatsheets/tshark/", title: "tshark cheatsheet",
    text: "Capture with tshark. Filter SYN packets: tcp.flags.syn == 1 and -sS scans show up.",
    headings: [{ id: "capture", text: "Capture" }],
    parts: [["capture", 0]],
  },
]);
const urls = (results) => results.map((r) => r.d.url);

test("search: a title match outranks body matches", () => {
  // 05-web mentions nmap 6 times in its body; 03-recon has it in the title.
  assert.equal(search(INDEX, "nmap")[0].d.url, "03-recon/");
});

test("search: the phrase bonus applies to 'nmap -sS'", () => {
  const results = search(INDEX, "nmap -sS");
  const recon = results.find((r) => r.d.url === "03-recon/");
  // Per term: nmap = 50 (title) + 2 (body); -sS = 1 (body). Phrase bonus +25.
  assert.equal(recon.score, 50 + 2 + 1 + 25);
  assert.equal(recon.snip.match, "nmap -sS");
  assert.equal(recon.heading.id, "syn-scan");  // the section the phrase sits in
});

test("search: no result when one term is missing", () => {
  assert.deepEqual(urls(search(INDEX, "nmap wireshark")), []);
  assert.deepEqual(urls(search(INDEX, "tshark -sS")), ["cheatsheets/tshark/"]);
});

test("search: empty queries and a missing index return nothing", () => {
  assert.deepEqual(search(INDEX, "   "), []);
  assert.deepEqual(search(null, "nmap"), []);
});

test("sectionAt: a position before the first heading returns null", () => {
  assert.equal(sectionAt(INDEX[0], 0), null);
  assert.equal(sectionAt(INDEX[0], 11), null);
});

test("sectionAt: a position on a boundary returns that section", () => {
  assert.equal(sectionAt(INDEX[0], 12).id, "syn-scan");
  assert.equal(sectionAt(INDEX[0], 41).id, "syn-scan");
  assert.equal(sectionAt(INDEX[0], 42).id, "versions");
  assert.equal(sectionAt({ headings: [] }, 5), null);  // no parts at all
});

test("snippet: marks the match and trims long context", () => {
  const text = "x".repeat(80) + "MATCH" + "y".repeat(100);
  const s = snippet(text, text.toLowerCase(), "match");
  assert.equal(s.match, "MATCH");
  assert.ok(s.before.startsWith("…") && s.before.length === 51);
  assert.equal(s.after, "y".repeat(70) + "…");
  assert.deepEqual(snippet("short", "short", "zzz"), { before: "short", match: "", after: "" });
});

test("moduleProgress: counts only that module's pages", () => {
  const module03 = ["03-recon/", "03-recon/scan-profiles/", "03-recon/"];  // duplicate link
  const done = new Set(["03-recon/", "01-basics/", "05-web/"]);
  assert.deepEqual(moduleProgress(module03, done),
    { n: 1, total: 2, label: "1 of 2 done", complete: false });
  done.add("03-recon/scan-profiles/");
  assert.equal(moduleProgress(module03, done).label, "complete");
  assert.equal(moduleProgress(module03, new Set(["01-basics/"])).label, "");
});

test("parseProgress: keeps known pages, rejects bad files", () => {
  const all = ["01-basics/", "03-recon/"];
  const file = JSON.stringify({ format: "kali-beginners-progress", version: 1,
                                done: ["03-recon/", "gone-page/", 7] });
  assert.deepEqual(parseProgress(file, all), ["03-recon/"]);
  assert.deepEqual(parseProgress('["01-basics/"]', all), ["01-basics/"]);
  assert.throws(() => parseProgress("not json", all), /not valid JSON/);
  assert.throws(() => parseProgress('{"other": 1}', all), /not a kali-beginners-progress.json export/);
  assert.throws(() => parseProgress('["gone-page/"]', all), /no pages from this course/);
});
