"use strict";

App.showSetup = function (show) {
  document.getElementById("setup-view").hidden = !show;
  document.getElementById("setup-error").hidden = true;
  document.getElementById("admin-login-form").hidden = true;
};

App.refreshSetupStatus = async function () {
  try {
    const status = await App.api("/api/setup/status");
    const admin = await App.api("/api/setup/admin");
    App.state.setupAdminAvailable = Boolean(admin.available);
    App.updateAccountUi();

    const missing = [];
    if (!status.llm_ok) {
      missing.push("大模型");
    }
    if (!status.parse_ok) {
      missing.push("解析器");
    }
    const banner = document.getElementById("setup-banner");
    const text = document.getElementById("setup-banner-text");
    const link = document.getElementById("setup-banner-link");
    const isAdmin = App.state.user && App.state.user.role === "admin";
    if (admin.available && !isAdmin) {
      banner.hidden = false;
      text.textContent = "系统还没有管理员，点击右上角「创建管理员」完成初始化。";
      link.hidden = true;
      return;
    }
    if (!missing.length) {
      banner.hidden = true;
      return;
    }
    banner.hidden = false;
    text.textContent = isAdmin
      ? missing.join("、") + "尚未配置，请完成系统设置后再上传或查询。"
      : "系统尚未完成配置，请联系管理员。";
    link.hidden = !isAdmin;
    link.onclick = () => App.switchView("admin");
  } catch (error) {
    /* The banner is optional; API errors are surfaced elsewhere. */
  }
};

App.reloadSessionData = async function () {
  App.resetTaskState();
  App.updateContext();
  await App.refreshDocuments();
  await App.refreshTasks();
  await App.refreshSetupStatus();
  App.timeline.render();
  App.report.render();
};

App.startSession = async function () {
  App.updateContext();
  await App.refreshDocuments();
  await App.refreshTasks();
  App.upload.init();
  App.tasks.init();
  App.timeline.init();
  App.report.init();
  App.admin.init();
  await App.refreshSetupStatus();
  App.startPolling();
};

App.bindAuth = function () {
  if (App.authBound) {
    return;
  }
  App.authBound = true;

  const loginForm = document.getElementById("admin-login-form");
  document.getElementById("admin-login-toggle").addEventListener("click", () => {
    if (
      App.state.setupAdminAvailable &&
      App.state.user &&
      App.state.user.role !== "admin"
    ) {
      App.showSetup(true);
      return;
    }
    loginForm.hidden = !loginForm.hidden;
    if (!loginForm.hidden) {
      loginForm.username.focus();
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const errorNode = document.getElementById("admin-login-error");
    errorNode.hidden = true;
    button.disabled = true;
    try {
      const user = await App.api("/api/login", {
        method: "POST",
        body: { username: form.username.value, password: form.password.value },
      });
      form.reset();
      form.hidden = true;
      App.resetTaskState();
      App.setUser(user);
      await App.startSession();
      App.switchView("admin");
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("setup-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const errorNode = document.getElementById("setup-error");
    errorNode.hidden = true;
    button.disabled = true;
    try {
      const user = await App.api("/api/setup/admin", {
        method: "POST",
        body: {
          username: form.username.value,
          password: form.password.value,
          password_confirm: form.password_confirm.value,
        },
      });
      form.reset();
      App.showSetup(false);
      App.resetTaskState();
      App.setUser(user);
      await App.startSession();
      App.switchView("admin");
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("setup-close").addEventListener("click", () => {
    App.showSetup(false);
  });

  document.getElementById("logout-btn").addEventListener("click", async () => {
    if (!App.confirmDiscardReport()) {
      return;
    }
    try {
      const data = await App.api("/api/logout", { method: "POST" });
      App.setUser(data.user || (await App.api("/api/me")));
    } catch (error) {
      /* Fall back to the guest identity on the next refresh. */
    }
    await App.reloadSessionData();
    App.switchView("tasks");
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => App.switchView(tab.dataset.view));
  });

  document.addEventListener("click", (event) => {
    if (loginForm.hidden) {
      return;
    }
    if (!event.target.closest(".account")) {
      loginForm.hidden = true;
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (App.state.report && App.state.report.dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
};

App.boot = async function () {
  App.bindAuth();
  try {
    const user = await App.api("/api/me");
    App.setUser(user);
    await App.startSession();
  } catch (error) {
    App.show();
    const banner = document.getElementById("setup-banner");
    const text = document.getElementById("setup-banner-text");
    banner.hidden = false;
    text.textContent = "无法连接服务：" + error.message;
  }
};
