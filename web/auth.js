"use strict";

App.auth = {
  bound: false,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.querySelectorAll("[data-auth]").forEach((button) => {
      button.addEventListener("click", () => this.setMode(button.dataset.auth));
    });
    document.getElementById("setup-link").addEventListener("click", () => this.setMode("setup"));
    document.getElementById("guest-btn").addEventListener("click", () => this.guest());
    document.getElementById("login-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.submit("/api/login", event.currentTarget);
    });
    document.getElementById("register-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.register(event.currentTarget);
    });
    document.getElementById("setup-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.setup(event.currentTarget);
    });
  },

  setMode(mode) {
    App.state.authMode = mode;
    document.getElementById("login-form").hidden = mode !== "login";
    document.getElementById("register-form").hidden = mode !== "register";
    document.getElementById("setup-form").hidden = mode !== "setup";
    document.querySelectorAll("[data-auth]").forEach((button) => {
      button.classList.toggle("active", button.dataset.auth === mode);
    });
    document.getElementById("auth-error").hidden = true;
  },

  error(message) {
    const node = document.getElementById("auth-error");
    node.textContent = message;
    node.hidden = !message;
  },

  async checkSetup() {
    try {
      const data = await App.api("/api/setup/admin");
      App.state.setupAvailable = Boolean(data.available);
      document.getElementById("setup-link").hidden = !data.available;
    } catch (error) {
      /* The login form will report connectivity errors. */
    }
  },

  async finish(user) {
    App.setUser(user);
    await App.startSession();
  },

  async submit(path, form) {
    this.error("");
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const user = await App.api(path, {
        method: "POST",
        body: { username: form.username.value, password: form.password.value },
      });
      form.reset();
      await this.finish(user);
    } catch (error) {
      this.error(error.message);
    } finally {
      button.disabled = false;
    }
  },

  async register(form) {
    this.error("");
    if (form.password.value !== form.confirm.value) {
      this.error("两次输入的密码不一致");
      return;
    }
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const user = await App.api("/api/register", {
        method: "POST",
        body: { username: form.username.value, password: form.password.value },
      });
      form.reset();
      await this.finish(user);
    } catch (error) {
      this.error(error.message);
    } finally {
      button.disabled = false;
    }
  },

  async setup(form) {
    this.error("");
    if (form.password.value !== form.confirm.value) {
      this.error("两次输入的密码不一致");
      return;
    }
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const user = await App.api("/api/setup/admin", {
        method: "POST",
        body: {
          username: form.username.value,
          password: form.password.value,
          password_confirm: form.confirm.value,
        },
      });
      form.reset();
      await this.finish(user);
    } catch (error) {
      this.error(error.message);
    } finally {
      button.disabled = false;
    }
  },

  async guest() {
    this.error("");
    try {
      const user = await App.api("/api/guest", { method: "POST" });
      await this.finish(user);
    } catch (error) {
      this.error(error.message);
    }
  },
};
