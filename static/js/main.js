// Prevents double-submission of state-changing actions (e.g. tapping
// "Starting Point" twice on a slow mobile connection). Vanilla JS only.
(function () {
  "use strict";

  document.querySelectorAll("form.js-guard-submit").forEach(function (form) {
    form.addEventListener("submit", function () {
      var btn = form.querySelector("[type=submit]");
      if (!btn) return;
      if (btn.dataset.submitted === "true") {
        return; // already handled below via preventDefault path
      }
      btn.dataset.submitted = "true";
      btn.classList.add("is-loading");
      btn.setAttribute("disabled", "disabled");
    });
  });

  // Auto-dismiss flash messages after a few seconds.
  document.querySelectorAll(".alert[data-autohide]").forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.4s ease";
      alert.style.opacity = "0";
      setTimeout(function () { alert.remove(); }, 400);
    }, 4500);
  });

  // Generic "select all / none" toggle for a group of checkboxes, e.g.
  // <button data-select-all="#list input[type=checkbox]">
  document.querySelectorAll("[data-select-all]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var boxes = document.querySelectorAll(btn.getAttribute("data-select-all"));
      var allChecked = Array.prototype.every.call(boxes, function (b) { return b.checked; });
      boxes.forEach(function (b) { b.checked = !allChecked; });
    });
  });

  // Generic live text filter for a list of rows, e.g.
  // <input data-filter-target="#list"> filtering [data-filter-row] children.
  document.querySelectorAll("[data-filter-target]").forEach(function (input) {
    input.addEventListener("input", function () {
      var target = document.querySelector(input.getAttribute("data-filter-target"));
      if (!target) return;
      var query = input.value.trim().toLowerCase();
      target.querySelectorAll("[data-filter-row]").forEach(function (row) {
        row.style.display = row.textContent.toLowerCase().indexOf(query) !== -1 ? "" : "none";
      });
    });
  });
})();
