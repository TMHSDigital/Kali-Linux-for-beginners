/* Runs before first paint so the saved theme never flashes. (External file:
   the Content-Security-Policy forbids inline scripts.) */
(function () {
  var theme = "dark";
  try {
    var saved = localStorage.getItem("theme");
    if (saved === "dark" || saved === "light") theme = saved;
    else if (window.matchMedia && matchMedia("(prefers-color-scheme: light)").matches) theme = "light";
  } catch (_) {}
  document.documentElement.setAttribute("data-theme", theme);
})();
