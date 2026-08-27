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
})();
