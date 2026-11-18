"use strict";

App.personal = {
  bound: false,

  // Keep in sync with AVATAR_COLORS in app/services/auth.py.
  palette: [
    "#1d4ed8",
    "#0f766e",
    "#b91c1c",
    "#7c3aed",
    "#be123c",
    "#0369a1",
    "#4d7c0f",
    "#a16207",
    "#4338ca",
    "#155e75",
    "#9a3412",
    "#86198f",
  ],

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("personal-close").addEventListener("click", () => this.close());
    document.getElementById("personal-modal").addEventListener("click", (event) => {
      if (event.target === event.currentTarget) {
        this.close();
      }
    });
    document.getElementById("avatar-color-toggle").addEventListener("click", () => this.toggle());
    const input = document.getElementById("avatar-color-input");
    input.addEventListener("input", (event) => this.sync(event.target.value));
    input.addEventListener("change", (event) => this.save(event.target.value));
  },

  open() {
    const user = App.state.user;
    if (!user || user.username === "guest") {
      return;
    }
    this.render();
    document.getElementById("avatar-palette").hidden = true;
    document.getElementById("avatar-color-toggle").classList.remove("open");
    document.getElementById("personal-status").textContent = "";
    this.sync(user.avatar_color || "#2563eb");
    document.getElementById("personal-modal").hidden = false;
  },

  close() {
    document.getElementById("personal-modal").hidden = true;
  },

  render() {
    const grid = document.getElementById("palette-grid");
    if (grid.childElementCount) {
      return;
    }
    for (const color of this.palette) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "palette-swatch";
      button.dataset.color = color;
      button.style.background = color;
      button.title = color;
      button.addEventListener("click", () => this.save(color));
      grid.appendChild(button);
    }
  },

  toggle() {
    const palette = document.getElementById("avatar-palette");
    const toggle = document.getElementById("avatar-color-toggle");
    palette.hidden = !palette.hidden;
    toggle.classList.toggle("open", !palette.hidden);
  },

  sync(color) {
    const value = String(color || "#2563eb").toLowerCase();
    document.getElementById("avatar-color-dot").style.background = value;
    document.getElementById("avatar-color-preview").style.background = value;
    document.getElementById("avatar-color-value").textContent = value;
    document.getElementById("avatar-color-input").value = value;
    for (const node of document.querySelectorAll(".palette-swatch")) {
      node.classList.toggle("active", node.dataset.color === value);
    }
  },

  status(message, danger) {
    const node = document.getElementById("personal-status");
    node.textContent = message || "";
    node.style.color = danger ? "var(--danger)" : "var(--muted)";
  },

  async save(color) {
    const value = String(color || "").toLowerCase();
    if (!/^#[0-9a-f]{6}$/.test(value)) {
      return;
    }
    this.status("保存中…");
    try {
      const data = await App.api("/api/me/avatar-color", {
        method: "PATCH",
        body: { avatar_color: value },
      });
      const saved = data.avatar_color || value;
      if (App.state.user) {
        App.state.user.avatar_color = saved;
      }
      document.getElementById("avatar").style.background = saved;
      this.sync(saved);
      this.status("已保存");
    } catch (error) {
      this.status(error.message, true);
    }
  },
};
