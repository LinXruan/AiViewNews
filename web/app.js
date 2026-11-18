"use strict";

const App = {
  state: {
    user: null,
    histories: [],
    activeHistory: null,
    activeTask: null,
    events: [],
    documents: [],
    activeDocId: null,
    readerText: "",
    readerBlocks: [],
    selectedEventId: null,
    queryRunning: false,
    reportTaskId: null,
    reportDirty: false,
    search: "",
    manualNew: false,
    authMode: "login",
    setupAvailable: false,
  },
  polling: false,
};

App.api = async function (path, options) {
  const config = Object.assign(
    { method: "GET", credentials: "same-origin", cache: "no-store", headers: {} },
    options || {}
  );
  if (config.body !== undefined) {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(config.body);
  }
  let url = path;
  if ((config.method || "GET").toUpperCase() === "GET") {
    url += (url.includes("?") ? "&" : "?") + "_t=" + Date.now();
  }
  const response = await fetch(url, config);
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
      App.showAuth();
    }
    throw failure;
  }
  return data;
};

App.el = function (tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
};

App.showAuth = function () {
  App.state.activeHistory = null;
  App.state.activeTask = null;
  App.state.events = [];
  document.getElementById("auth-screen").hidden = false;
  document.getElementById("workspace").hidden = true;
  document.getElementById("report-screen").hidden = true;
  document.getElementById("admin-screen").hidden = true;
  document.getElementById("settings-panel").hidden = true;
  document.getElementById("account-menu").hidden = true;
  const error = document.getElementById("auth-error");
  error.hidden = true;
  if (App.auth) {
    App.auth.setMode("login");
  }
  if (App.auth) {
    App.auth.checkSetup();
  }
};

App.showWorkspace = function () {
  document.getElementById("auth-screen").hidden = true;
  document.getElementById("report-screen").hidden = true;
  document.getElementById("workspace").hidden = false;
};

App.setUser = function (user) {
  App.state.user = user;
  const guest = user.username === "guest";
  document.getElementById("account-name").textContent = guest ? "不登陆" : user.username;
  const avatar = document.getElementById("avatar");
  avatar.textContent = guest ? "" : (user.username[0] || "A").toUpperCase();
  avatar.classList.toggle("guest", guest);
  avatar.style.background = guest ? "" : (user.avatar_color || "");
  document.getElementById("settings-console").hidden = user.role !== "admin";
  document.getElementById("account-settings").hidden = false;
};

App.formatTime = function (value) {
  if (!value) {
    return "—";
  }
  let source = value;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) {
    source = value.replace(" ", "T") + "Z";
  }
  const date = new Date(source);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
};

App.shortDate = function (value) {
  if (!value) {
    return "";
  }
  let source = value;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) {
    source = value.replace(" ", "T") + "Z";
  }
  const date = new Date(source);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
};

App.statusText = {
  draft: "解析中",
  ready: "已就绪",
  failed: "解析失败",
  pending: "等待中",
  parsing: "解析中",
  parsed: "已解析",
  analyzing: "分析中",
  done: "已完成",
  partial: "部分完成",
};

App.statusBadge = function (status) {
  return App.el("span", "status " + status, App.statusText[status] || status);
};

App.sleep = function (ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
};

App.startSession = async function () {
  App.showWorkspace();
  App.history.bind();
  App.upload.bind();
  App.records.bind();
  App.reader.bind();
  App.resizer.bind();
  App.report.bind();
  App.account.bind();
  App.admin.bind();
  App.state.activeHistory = null;
  App.state.activeTask = null;
  App.state.events = [];
  App.state.manualNew = false;
  App.records.hide();
  document.getElementById("record-list").hidden = true;
  document.getElementById("timeline").textContent = "";
  document.getElementById("timeline-hint").textContent = "";
  document.getElementById("query-input").value = "";
  document.getElementById("query-error").hidden = true;
  document.getElementById("doc-tabs").textContent = "";
  document.getElementById("reader-body").textContent = "";
  document.getElementById("summary-panel").hidden = true;
  await App.history.load();
  if (!App.state.activeHistory) {
    App.reader.showUpload();
  }
  App.startPolling();
};

App.poll = async function () {
  if (!App.state.activeTask || !["pending", "analyzing"].includes(App.state.activeTask.status)) {
    return;
  }
  try {
    await App.records.checkActive();
  } catch (error) {
    /* transient polling error */
  }
};

App.startPolling = function () {
  if (App.polling) {
    return;
  }
  App.polling = true;
  window.setInterval(() => {
    if (!document.hidden && App.state.user) {
      App.poll();
    }
  }, 1500);
};

App.boot = async function () {
  App.auth.bind();
  try {
    const user = await App.api("/api/me");
    App.setUser(user);
    await App.startSession();
  } catch (error) {
    App.showAuth();
  }
};

window.App = App;
window.addEventListener("DOMContentLoaded", () => App.boot());
