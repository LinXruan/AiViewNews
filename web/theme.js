"use strict";

// Theme preference: light | dark | system (PLAN 23).
// Loaded in <head> before the stylesheets so the first paint already
// uses the stored or system-resolved theme.
(function () {
  const KEY = "theme.mode";
  const MODES = ["light", "dark", "system"];
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  function stored() {
    try {
      const value = localStorage.getItem(KEY);
      return MODES.includes(value) ? value : "system";
    } catch (error) {
      return "system";
    }
  }

  function resolve(mode) {
    if (mode === "system") {
      return media.matches ? "dark" : "light";
    }
    return mode;
  }

  function paint(mode) {
    document.documentElement.dataset.theme = resolve(mode);
    document.documentElement.dataset.themeMode = mode;
  }

  function set(mode) {
    const next = MODES.includes(mode) ? mode : "system";
    try {
      localStorage.setItem(KEY, next);
    } catch (error) {
      /* Storage may be unavailable; the choice still applies this session. */
    }
    paint(next);
    return next;
  }

  media.addEventListener("change", () => {
    if (stored() === "system") {
      paint("system");
    }
  });

  paint(stored());

  window.AppTheme = {
    get: stored,
    set,
    resolved: () => resolve(stored()),
  };
})();
