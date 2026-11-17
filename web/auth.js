"use strict";

App.bindAuth = function () {
  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const errorNode = document.getElementById("login-error");
    errorNode.hidden = true;
    button.disabled = true;
    try {
      const user = await App.api("/api/login", {
        method: "POST",
        body: { username: form.username.value, password: form.password.value },
      });
      form.reset();
      App.setUser(user);
      await App.startSession();
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
      App.setUser(user);
      await App.startSession();
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("logout-btn").addEventListener("click", async () => {
    if (!App.confirmDiscardReport()) {
      return;
    }
    try {
      await App.api("/api/logout", { method: "POST" });
    } catch (error) {
      /* Signed out locally regardless. */
    }
    App.state.user = null;
    App.state.taskToken += 1;
    App.state.currentTaskId = null;
    App.state.currentTask = null;
    App.state.report = null;
    App.show("login");
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => App.switchView(tab.dataset.view));
  });

  window.addEventListener("beforeunload", (event) => {
    if (App.state.report && App.state.report.dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
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


