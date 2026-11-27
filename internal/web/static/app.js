(function () {
  "use strict";

  const THEME_KEY = "logccino-theme";

  function applyTheme(theme) {
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
    const sun = document.getElementById("theme-icon-sun");
    const moon = document.getElementById("theme-icon-moon");
    if (sun && moon) {
      sun.style.display = theme === "light" ? "none" : "block";
      moon.style.display = theme === "light" ? "block" : "none";
    }
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || "dark";
    applyTheme(saved);
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) {
      btn.addEventListener("click", function () {
        const current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
        const next = current === "light" ? "dark" : "light";
        localStorage.setItem(THEME_KEY, next);
        applyTheme(next);
      });
    }
  }

  function toast(type, title, message) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const el = document.createElement("div");
    el.className = "toast " + (type ? "toast-" + type : "");
    const titleEl = document.createElement("div");
    titleEl.className = "toast-title";
    titleEl.textContent = title;
    const msgEl = document.createElement("div");
    msgEl.className = "toast-msg";
    msgEl.textContent = message;
    el.appendChild(titleEl);
    el.appendChild(msgEl);
    container.appendChild(el);
    setTimeout(function () {
      el.remove();
    }, 5500);
  }

  function initMobileSidebar() {
    const btn = document.getElementById("mobile-menu-btn");
    const sidebar = document.getElementById("app-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (!btn || !sidebar || !backdrop) return;
    function close() {
      sidebar.classList.remove("open");
      backdrop.classList.remove("open");
    }
    btn.addEventListener("click", function () {
      sidebar.classList.toggle("open");
      backdrop.classList.toggle("open");
    });
    backdrop.addEventListener("click", close);
  }

  function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (group) {
      const buttons = group.querySelectorAll("[data-tab-target]");
      const panels = group.querySelectorAll("[data-tab-panel]");
      buttons.forEach(function (btn) {
        btn.addEventListener("click", function () {
          const target = btn.getAttribute("data-tab-target");
          buttons.forEach(function (b) { b.classList.remove("active"); });
          panels.forEach(function (p) {
            if (p.getAttribute("data-tab-panel") === target) {
              p.classList.add("active");
            } else {
              p.classList.remove("active");
            }
          });
          btn.classList.add("active");
        });
      });
    });
  }

  function initCopyButtons() {
    document.querySelectorAll("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const targetId = btn.getAttribute("data-copy");
        let text = btn.getAttribute("data-copy-text") || "";
        if (!text && targetId) {
          const el = document.getElementById(targetId);
          if (el) text = el.textContent || "";
        }
        if (!text) return;
        navigator.clipboard.writeText(text).then(function () {
          const orig = btn.textContent;
          btn.textContent = "Copied";
          setTimeout(function () { btn.textContent = orig; }, 1600);
        });
      });
    });
  }

  function initTableFilters() {
    document.querySelectorAll("[data-filter-table]").forEach(function (container) {
      const tableId = container.getAttribute("data-filter-table");
      const table = document.getElementById(tableId);
      if (!table) return;
      const rows = Array.from(table.querySelectorAll("tbody tr[data-row]"));
      const searchInput = container.querySelector("[data-filter-search]");
      const selects = Array.from(container.querySelectorAll("select[data-filter-attr]"));
      const counter = container.querySelector("[data-filter-count]");

      function applyFilters() {
        const q = searchInput ? searchInput.value.trim().toLowerCase() : "";
        let visible = 0;
        rows.forEach(function (row) {
          let match = true;
          if (q) {
            const txt = (row.textContent || "").toLowerCase();
            if (txt.indexOf(q) === -1) match = false;
          }
          if (match) {
            selects.forEach(function (sel) {
              const attr = sel.getAttribute("data-filter-attr");
              const want = sel.value.trim().toLowerCase();
              if (want && want !== "all") {
                const actual = (row.getAttribute("data-" + attr) || "").toLowerCase();
                if (actual !== want) match = false;
              }
            });
          }
          row.style.display = match ? "" : "none";
          if (match) visible++;
        });
        if (counter) {
          counter.textContent = visible + " / " + rows.length;
        }
      }

      if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
      }
      selects.forEach(function (sel) {
        sel.addEventListener("change", applyFilters);
      });

      // Allow external pill buttons to control a filter select
      document.querySelectorAll("[data-quick-filter-target='" + tableId + "']").forEach(function (pillBtn) {
        pillBtn.addEventListener("click", function () {
          document.querySelectorAll("[data-quick-filter-target='" + tableId + "']").forEach(function (p) {
            p.classList.remove("active");
          });
          pillBtn.classList.add("active");
          const attr = pillBtn.getAttribute("data-quick-attr");
          const val = pillBtn.getAttribute("data-quick-val");
          selects.forEach(function (sel) {
            if (sel.getAttribute("data-filter-attr") === attr) {
              sel.value = val;
            } else {
              sel.value = "all";
            }
          });
          applyFilters();
        });
      });

      applyFilters();
    });
  }

  function initQuickSampleButtons() {
    document.querySelectorAll("[data-fill-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const target = document.getElementById(btn.getAttribute("data-fill-target"));
        const val = btn.getAttribute("data-fill-value");
        if (target && val !== null) {
          target.value = val;
          target.focus();
        }
      });
    });
  }

  function pollHealth() {
    fetch("/api/status")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        const splunkDot = document.getElementById("topbar-splunk-dot");
        const splunkTxt = document.getElementById("topbar-splunk-text");
        const llmDot = document.getElementById("topbar-llm-dot");
        const llmTxt = document.getElementById("topbar-llm-text");

        if (data && data.components) {
          if (splunkDot && splunkTxt) {
            const ok = data.components.splunk === "ok";
            splunkDot.className = "status-dot " + (ok ? "ok" : "err");
            splunkTxt.textContent = ok ? "Splunk Connected" : "Splunk Degraded";
          }
          if (llmDot && llmTxt && data.components.llm) {
            const st = data.components.llm.status;
            const ok = st === "ok";
            llmDot.className = "status-dot " + (ok ? "ok" : "warn");
            llmTxt.textContent = (data.components.llm.model || "LLM") + " (" + st + ")";
          }
        }
      })
      .catch(function () {});
  }

  function setStepState(stepIdx, state) {
    for (let i = 1; i <= 3; i++) {
      const el = document.getElementById("pipeline-step-" + i);
      if (!el) continue;
      el.classList.remove("active", "done");
      if (i < stepIdx) el.classList.add("done");
      else if (i === stepIdx) el.classList.add(state || "active");
    }
  }

  function runDailyPipeline() {
    const btn = document.getElementById("btn-run-pipeline");
    const statusEl = document.getElementById("pipeline-status-text");
    if (!btn) return;
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = "Executing Pipeline...";
    setStepState(1, "active");
    if (statusEl) statusEl.textContent = "Step 1/3: Generating & ingesting daily security telemetry into Splunk...";

    fetch("/api/testdata/generate", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (genRes) {
        if (genRes.error) throw new Error(genRes.error);
        setStepState(2, "active");
        if (statusEl) {
          statusEl.textContent = "Step 2/3: Ingested " + (genRes.total_events || 0) + " events. Running DLP exfiltration rules...";
        }
        return fetch("/api/dlp/scan", { method: "POST" });
      })
      .then(function (r) { return r.json(); })
      .then(function (scanRes) {
        if (scanRes.error) throw new Error(scanRes.error);
        setStepState(3, "done");
        const emitted = scanRes.alerts_emitted || 0;
        if (statusEl) {
          statusEl.textContent = "Completed: " + (scanRes.rules_evaluated || 0) + " rules evaluated, " + emitted + " alerts queued for Multi-Agent AI Triage.";
        }
        toast("success", "Daily Exfiltration Pipeline Completed", emitted + " alerts emitted and queued for AI triage.");
        btn.disabled = false;
        btn.innerHTML = orig;
      })
      .catch(function (err) {
        if (statusEl) statusEl.textContent = "Pipeline error: " + err.message;
        toast("error", "Pipeline Failed", err.message);
        btn.disabled = false;
        btn.innerHTML = orig;
      });
  }

  function runQuickDLPScan(btn) {
    if (!btn) return;
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = "Scanning...";
    fetch("/api/dlp/scan", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.error) throw new Error(res.error);
        toast("success", "DLP Exfiltration Scan Complete", (res.alerts_emitted || 0) + " alerts emitted across " + (res.rules_evaluated || 0) + " rules.");
        setTimeout(function () {
          if (window.location.pathname === "/tickets") {
            window.location.reload();
          } else {
            btn.disabled = false;
            btn.innerHTML = orig;
          }
        }, 900);
      })
      .catch(function (err) {
        toast("error", "DLP Scan Error", err.message);
        btn.disabled = false;
        btn.innerHTML = orig;
      });
  }

  function syncDACGit(btn) {
    if (!btn) return;
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.textContent = "Syncing...";
    fetch("/api/dac/git/sync", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.error) throw new Error(res.error);
        const msg = (res.sync && res.sync.message) ? res.sync.message : "Synchronized rules repository.";
        toast("success", "DaC Git Sync Complete", msg);
        setTimeout(function () { window.location.reload(); }, 900);
      })
      .catch(function (err) {
        toast("error", "Git Sync Failed", err.message);
        btn.disabled = false;
        btn.innerHTML = orig;
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initMobileSidebar();
    initTabs();
    initCopyButtons();
    initTableFilters();
    initQuickSampleButtons();
    setInterval(pollHealth, 30000);
  });

  window.Logccino = {
    toast: toast,
    runDailyPipeline: runDailyPipeline,
    runQuickDLPScan: runQuickDLPScan,
    syncDACGit: syncDACGit
  };
})();
