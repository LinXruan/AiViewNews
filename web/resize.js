"use strict";

// One drag handler for every adjustable pane. Mirrors the summary panel
// behaviour and blocks text selection while a handle is held.
App.resizer = {
  specs: {},

  bind() {
    if (Object.keys(this.specs).length) {
      this.restore();
      return;
    }
    this.specs = {
      history: {
        horizontal: true,
        min: 220,
        max: 420,
        key: "layout.history",
        target: () => document.getElementById("history-rail"),
        apply: (value) => this.setVar("--history-w", value),
      },
      records: {
        horizontal: true,
        min: 260,
        max: 520,
        key: "layout.records",
        target: () => document.getElementById("record-rail"),
        apply: (value) => this.setVar("--records-w", value),
      },
      query: {
        horizontal: false,
        invert: true,
        min: 96,
        max: 320,
        key: "layout.query",
        target: () => document.getElementById("query-input"),
        apply: (value) => this.setVar("--query-h", value),
      },
      report: {
        horizontal: true,
        min: 320,
        max: () => Math.max(360, window.innerWidth - 420),
        key: "layout.reportEditor",
        target: () => document.querySelector(".report-grid"),
        measure: () => {
          const editor = document.getElementById("report-editor");
          return editor ? editor.getBoundingClientRect().width : null;
        },
        apply: (value) => this.setVar("--editor-col", value),
      },
      summary: {
        horizontal: false,
        invert: true,
        min: 120,
        max: () => window.innerHeight * 0.6,
        key: "layout.summary",
        target: () => document.getElementById("summary-panel"),
        apply: (value) => {
          const panel = document.getElementById("summary-panel");
          if (panel) {
            panel.style.height = Math.round(value) + "px";
          }
        },
      },
    };
    document.querySelectorAll("[data-resize]").forEach((handle) => {
      const spec = this.specs[handle.dataset.resize];
      if (spec) {
        this.attach(handle, spec);
      }
    });
    window.addEventListener("resize", () => this.restore(true));
    this.restore();
  },

  setVar(name, value) {
    document.documentElement.style.setProperty(name, Math.round(value) + "px");
  },

  sizeOf(spec) {
    if (!spec.target()) {
      return null;
    }
    if (spec.measure) {
      return spec.measure();
    }
    const target = spec.target();
    const box = target.getBoundingClientRect();
    return spec.horizontal ? box.width : box.height;
  },

  attach(handle, spec) {
    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) {
        return;
      }
      const target = spec.target();
      if (!target) {
        return;
      }
      event.preventDefault();
      this.clearSelection();
      const startSize = this.sizeOf(spec) || spec.min;
      const origin = spec.horizontal ? event.clientX : event.clientY;
      document.body.classList.add("is-resizing");
      handle.setPointerCapture(event.pointerId);
      // A drag that ends over a button must not also fire that button's click.
      const blockClick = (clickEvent) => {
        clickEvent.preventDefault();
        clickEvent.stopPropagation();
        document.removeEventListener("click", blockClick, true);
      };
      document.addEventListener("click", blockClick, true);
      window.setTimeout(() => document.removeEventListener("click", blockClick, true), 400);

      const move = (moveEvent) => {
        const delta = (spec.horizontal ? moveEvent.clientX : moveEvent.clientY) - origin;
        const raw = startSize + (spec.invert ? -delta : delta);
        const upper = typeof spec.max === "function" ? spec.max() : spec.max;
        spec.apply(Math.min(upper, Math.max(spec.min, raw)));
      };
      const finish = () => {
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", finish);
        handle.removeEventListener("pointercancel", finish);
        document.body.classList.remove("is-resizing");
        const size = this.sizeOf(spec);
        if (size) {
          localStorage.setItem(spec.key, String(Math.round(size)));
        }
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", finish);
      handle.addEventListener("pointercancel", finish);
    });
  },

  clearSelection() {
    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
    }
  },

  restore(clampOnly) {
    Object.values(this.specs).forEach((spec) => {
      const stored = Number(localStorage.getItem(spec.key));
      if (!stored || !Number.isFinite(stored)) {
        return;
      }
      const upper = typeof spec.max === "function" ? spec.max() : spec.max;
      const value = Math.min(upper, Math.max(spec.min, stored));
      if (!clampOnly || value !== stored) {
        spec.apply(value);
      }
      if (value !== stored) {
        localStorage.setItem(spec.key, String(Math.round(value)));
      }
    });
  },
};
