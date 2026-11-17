"use strict";

App.account = {
  bound: false,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    const menu = document.getElementById("account-menu");
    const panel = document.getElementById("settings-panel");
    const avatar = document.getElementById("account-button");

    document.getElementById("account-button").addEventListener("click", (event) => {
      event.stopPropagation();
      panel.hidden = true;
      menu.hidden = !menu.hidden;
      if (!menu.hidden) {
        this.place(menu, avatar);
      }
    });

    document.getElementById("account-settings").addEventListener("click", (event) => {
      event.stopPropagation();
      menu.hidden = true;
      panel.hidden = false;
      this.place(panel, avatar);
    });

    document.getElementById("settings-account").addEventListener("click", () => {
      panel.hidden = true;
      if (App.state.user && App.state.user.username === "guest") {
        this.discardGuest();
      } else {
        document.getElementById("account-modal").hidden = false;
      }
    });

    document.getElementById("settings-console").addEventListener("click", () => {
      panel.hidden = true;
      App.admin.open();
    });

    document.addEventListener("click", (event) => {
      if (
        !event.target.closest("#account-box") &&
        !event.target.closest("#account-menu") &&
        !event.target.closest("#settings-panel")
      ) {
        menu.hidden = true;
        panel.hidden = true;
      }
    });
    window.addEventListener("resize", () => {
      menu.hidden = true;
      panel.hidden = true;
    });

    document.getElementById("account-modal-close").addEventListener("click", () => {
      document.getElementById("account-modal").hidden = true;
    });
    document.getElementById("account-logout").addEventListener("click", () => this.logout());
    document.getElementById("password-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.changePassword(event.currentTarget);
    });
    document.getElementById("delete-account").addEventListener("click", () => this.deleteAccount());
  },

  place(node, anchor) {
    const rect = anchor.getBoundingClientRect();
    const width = node.offsetWidth;
    const height = node.offsetHeight;
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    let top = rect.top - height - 6;
    if (top < 8) {
      top = rect.bottom + 6;
    }
    top = Math.min(top, window.innerHeight - height - 8);
    node.style.left = left + "px";
    node.style.top = top + "px";
  },

  error(message) {
    const node = document.getElementById("password-error");
    node.textContent = message || "";
    node.hidden = !message;
  },

  resetState() {
    App.state.user = null;
    App.state.activeHistory = null;
    App.state.activeTask = null;
    App.state.histories = [];
    App.state.events = [];
  },

  async logout() {
    try {
      await App.api("/api/logout", { method: "POST" });
    } catch (error) {
      /* Local logout still works. */
    }
    this.resetState();
    App.showAuth();
  },

  async discardGuest() {
    try {
      await App.api("/api/me/guest-data", { method: "DELETE" });
    } catch (error) {
      /* The session may already be gone; continue to the login page. */
    }
    this.resetState();
    App.showAuth();
  },

  async changePassword(form) {
    this.error("");
    if (form.new_password.value !== form.confirm_password.value) {
      this.error("两次输入的新密码不一致");
      return;
    }
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await App.api("/api/me/password", {
        method: "PATCH",
        body: {
          old_password: form.old_password.value,
          new_password: form.new_password.value,
        },
      });
      form.reset();
      this.error("");
      document.getElementById("account-modal").hidden = true;
      window.alert("密码已修改");
    } catch (error) {
      this.error(error.message);
    } finally {
      button.disabled = false;
    }
  },

  async deleteAccount() {
    const first = window.confirm("注销账号会删除你的全部 PDF 历史、查询记录、事件和报告，且无法恢复。继续吗？");
    if (!first) {
      return;
    }
    const second = window.confirm("最后确认：真的要注销账号并删除所有数据吗？");
    if (!second) {
      return;
    }
    try {
      await App.api("/api/me", { method: "DELETE" });
      this.resetState();
      document.getElementById("account-modal").hidden = true;
      App.showAuth();
    } catch (error) {
      this.error(error.message);
    }
  },
};
