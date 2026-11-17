"use strict";

const App = {
  state: {
    user: null,
    documents: [],
    tasks: [],
    currentTaskId: null,
    currentTask: null,
    events: [],
    report: null,
    selectedDocs: new Set(),
    knownParsed: new Set(),
    view: "tasks",
    uploading: false,
    taskToken: 0,
  },
};

App.api = async function (path, options) {
  const config = Object.assign(
    { method: "GET", credentials: "same-origin", headers: {} },
    options || {}
  );
  if (config.body !== undefined) {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(path, config);
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }
  if (!response.ok) {
    const message =
      data && data.error && data.error.message
        ? data.error.message
        : "请求失败（" + response.status + "）";
    const failure = new Error(message);
    failure.status = response.status;
    if (response.status === 401 && App.state.user) {
      App.state.user = null;
      App.show("login");
    }
    throw failure;
  }
  return data;
};

App.show = function (name) {
  const login = document.getElementById("login-view");
  const setup = document.getElementById("setup-view");
  const main = document.getElementById("app-main");
  const topbar = document.getElementById("topbar");
  const loggedIn = name === "app";
  login.hidden = name !== "login";
  setup.hidden = name !== "setup";
  main.hidden = !loggedIn;
  topbar.hidden = !loggedIn;
};

App.setUser = function (user) {
  App.state.user = user;
  document.getElementById("user-label").textContent =
    user.username + " · " + (user.role === "admin" ? "管理员" : "普通用户");
  document.getElementById("admin-tab").hidden = user.role !== "admin";
  App.show("app");
};

App.formatTime = function (value) {
  if (!value) {
    return "—";
  }
  const date = App.parseDate(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
};

App.parseDate = function (value) {
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) {
    return new Date(value.replace(" ", "T") + "Z");
  }
  return new Date(value);
};

App.duration = function (start, end) {
  if (!start || !end) {
    return "—";
  }
  const seconds = Math.max(0, Math.round((App.parseDate(end) - App.parseDate(start)) / 1000));
  if (seconds < 60) {
    return seconds + "s";
  }
  return Math.floor(seconds / 60) + "m " + (seconds % 60) + "s";
};

App.statusText = {
  pending: "待处理",
  parsing: "解析中",
  parsed: "已解析",
  failed: "失败",
  analyzing: "分析中",
  done: "已完成",
  partial: "部分完成",
};

App.statusBadge = function (status) {
  const span = document.createElement("span");
  span.className = "status " + status;
  span.textContent = App.statusText[status] || status;
  return span;
};

App.markReportDirty = function (dirty) {
  if (App.state.report) {
    App.state.report.dirty = dirty;
  }
};

App.confirmDiscardReport = function () {
  if (App.state.report && App.state.report.dirty) {
    return window.confirm("报告有未保存的修改，确定要离开吗？");
  }
  return true;
};

App.switchView = function (name) {
  if (!App.confirmDiscardReport()) {
    return;
  }
  App.state.view = name;
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === name);
  });
  document.getElementById("tasks-view").hidden = name !== "tasks";
  document.getElementById("timeline-view").hidden = name !== "timeline";
  document.getElementById("report-view").hidden = name !== "report";
  document.getElementById("admin-view").hidden = name !== "admin";
  if (name === "timeline") {
    App.timeline.render();
  }
  if (name === "report") {
    App.report.render();
  }
  if (name === "admin") {
    App.admin.show();
  }
};

App.refreshDocuments = async function () {
  const data = await App.api("/api/documents");
  App.state.documents = data.documents || [];
  App.upload.renderDocuments();
  App.tasks.renderDocPicker();
};

App.refreshTasks = async function () {
  const data = await App.api("/api/tasks");
  App.state.tasks = data.tasks || [];
  App.tasks.renderTasks();
};

App.selectTask = async function (taskId, view) {
  if (!App.confirmDiscardReport()) {
    return;
  }
  const token = ++App.state.taskToken;
  App.state.currentTaskId = taskId;
  App.state.currentTask = null;
  App.state.events = [];
  App.state.report = null;
  try {
    const task = await App.api("/api/tasks/" + taskId);
    const events = await App.api("/api/tasks/" + taskId + "/events");
    if (token !== App.state.taskToken) {
      return;
    }
    App.state.currentTask = task;
    App.state.events = events.events || [];
    App.state.report = await App.report.fetch(taskId);
    App.updateContext();
    App.timeline.render();
    App.report.render();
    if (view) {
      App.switchView(view);
    }
  } catch (error) {
    App.tasks.showError(error.message);
  }
};

App.updateContext = function () {
  const task = App.state.currentTask;
  const text = task
    ? "任务 #" + task.id + " · " + task.query
    : "未选择任务";
  document.getElementById("task-context").textContent = text;
  document.getElementById("timeline-task-label").textContent = task ? "任务 #" + task.id : "";
};

App.reloadCurrentTask = async function () {
  if (!App.state.currentTaskId) {
    return;
  }
  const task = await App.api("/api/tasks/" + App.state.currentTaskId);
  const wasActive = App.state.currentTask && ["pending", "analyzing"].includes(App.state.currentTask.status);
  const nowActive = ["pending", "analyzing"].includes(task.status);
  App.state.currentTask = task;
  App.updateContext();
  if (wasActive && !nowActive) {
    const events = await App.api("/api/tasks/" + task.id + "/events");
    App.state.events = events.events || [];
    const report = await App.report.fetch(task.id);
    if (!App.state.report || !App.state.report.dirty) {
      App.state.report = report;
    }
    App.timeline.render();
    App.report.render();
  }
};

App.startPolling = function () {
  if (App.polling) {
    return;
  }
  App.polling = true;
  window.setInterval(async () => {
    if (document.hidden || !App.state.user) {
      return;
    }
    try {
      const parsing = App.state.documents.some((doc) =>
        ["pending", "parsing"].includes(doc.parse_status)
      );
      const active = App.state.tasks.some((task) =>
        ["pending", "analyzing"].includes(task.status)
      );
      if (parsing) {
        await App.refreshDocuments();
      }
      if (active || App.state.view === "tasks") {
        await App.refreshTasks();
      }
      if (App.state.currentTask && ["pending", "analyzing"].includes(App.state.currentTask.status)) {
        await App.reloadCurrentTask();
      }
    } catch (error) {
      /* Transient polling errors are ignored; the next tick retries. */
    }
  }, 1500);
};

App.boot = async function () {
  App.bindAuth();
  try {
    const setup = await App.api("/api/setup/admin");
    if (setup.available) {
      App.show("setup");
      return;
    }
  } catch (error) {
    /* Fall back to login; the form will report connectivity errors. */
  }
  try {
    const user = await App.api("/api/me");
    App.setUser(user);
    await App.startSession();
  } catch (error) {
    App.show("login");
  }
};

window.App = App;
window.addEventListener("DOMContentLoaded", App.boot);
