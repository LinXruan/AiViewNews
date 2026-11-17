"use strict";

App.records = {
  bound: false,
  waitingTaskId: null,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("query-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.submit();
    });
    document.getElementById("records-toggle").addEventListener("click", () => {
      const list = document.getElementById("record-list");
      list.hidden = !list.hidden;
    });
    document.getElementById("record-collapse").addEventListener("click", () => {
      const rail = document.getElementById("record-rail");
      rail.classList.toggle("collapsed");
      document.getElementById("record-collapse").textContent =
        rail.classList.contains("collapsed") ? "»" : "«";
    });
    document.getElementById("record-list").addEventListener("click", (event) => {
      const button = event.target.closest(".record-item");
      if (button) {
        this.select(Number(button.dataset.id));
      }
    });
  },

  show(detail) {
    const rail = document.getElementById("record-rail");
    const hasParsed = (detail.documents || []).some((doc) => doc.parse_status === "parsed");
    rail.hidden = !hasParsed;
    if (!hasParsed) {
      return;
    }
    this.renderRecords(detail.records || []);
  },

  hide() {
    document.getElementById("record-rail").hidden = true;
    document.getElementById("record-list").hidden = true;
    App.state.activeTask = null;
    App.state.events = [];
    document.getElementById("save-btn").disabled = true;
  },

  clear() {
    App.state.activeTask = null;
    App.state.events = [];
    document.getElementById("query-input").value = "";
    document.getElementById("save-btn").disabled = true;
    this.renderTimeline();
    App.reader.clearSelection();
  },

  renderRecords(records) {
    App.state.records = records;
    const list = document.getElementById("record-list");
    list.textContent = "";
    if (!records.length) {
      list.append(App.el("p", "muted small", "还没有记录，先在下方提问。"));
      return;
    }
    records.forEach((record) => {
      const button = App.el("button", "record-item");
      button.type = "button";
      button.dataset.id = String(record.id);
      if (App.state.activeTask && App.state.activeTask.id === record.id) {
        button.classList.add("active");
      }
      const query = App.el("span", "record-query", record.query);
      const meta = App.el("span", "record-meta");
      meta.append(
        App.el("span", "", App.shortDate(record.created_at)),
        App.el("span", "", App.statusText[record.status] || record.status)
      );
      button.append(query, meta);
      list.append(button);
    });
  },

  async select(taskId, silent) {
    try {
      const task = await App.api("/api/tasks/" + taskId);
      const events = await App.api("/api/tasks/" + taskId + "/events");
      App.state.activeTask = task;
      App.state.events = events.events || [];
      document.getElementById("query-input").value = task.query;
      this.renderRecords(App.state.records || []);
      this.renderTimeline();
      App.reader.clearHighlight();
      App.reader.clearSelection();
      document.getElementById("save-btn").disabled = !["done", "partial"].includes(task.status);
      this.error(task.status === "failed" ? task.error || "分析失败" : "");
      if (["pending", "analyzing"].includes(task.status)) {
        this.waitForTask(task.id);
      }
    } catch (error) {
      if (!silent) {
        this.error(error.message);
      }
    }
  },

  renderTimeline() {
    const timeline = document.getElementById("timeline");
    const summary = document.getElementById("timeline-summary");
    timeline.textContent = "";
    const hint = document.getElementById("timeline-hint");
    const task = App.state.activeTask;
    summary.hidden = !task || !task.timeline_summary;
    summary.textContent = task && task.timeline_summary ? task.timeline_summary : "";
    if (!task) {
      hint.textContent = "提问后会在这里显示时间线。";
      return;
    }
    if (["pending", "analyzing"].includes(task.status)) {
      hint.textContent = "分析中……";
      return;
    }
    const events = App.state.events || [];
    if (!events.length) {
      hint.textContent = "本次查询没有抽取到相关事件。";
      return;
    }
    hint.textContent = "点击节点查看正文与简介。";
    events.forEach((event) => {
      const button = App.el("button", "timeline-node");
      button.type = "button";
      button.dataset.id = String(event.id);
      if (App.state.selectedEventId === event.id) {
        button.classList.add("active");
      }
      button.append(
        App.el("span", "node-date", event.event_time || "时间不详"),
        App.el("span", "node-text", event.event_text.length > 38
          ? event.event_text.slice(0, 38) + "…"
          : event.event_text)
      );
      button.addEventListener("click", () => App.reader.selectEvent(event));
      timeline.append(button);
    });
  },

  setActiveEvent(eventId) {
    App.state.selectedEventId = eventId;
    document.querySelectorAll(".timeline-node").forEach((node) => {
      node.classList.toggle("active", Number(node.dataset.id) === eventId);
    });
  },

  error(message) {
    const node = document.getElementById("query-error");
    node.textContent = message || "";
    node.hidden = !message;
  },

  async submit() {
    if (App.state.queryRunning) {
      return;
    }
    const query = document.getElementById("query-input").value.trim();
    if (!query) {
      this.error("请输入要查询的内容。");
      return;
    }
    if (!App.state.activeHistory) {
      this.error("请先上传并选择 PDF。");
      return;
    }
    this.error("");
    const button = document.getElementById("query-run");
    App.state.queryRunning = true;
    button.classList.add("running");
    button.textContent = "■";
    button.disabled = true;
    try {
      const task = await App.api("/api/tasks", {
        method: "POST",
        body: { history_id: App.state.activeHistory.id, query },
      });
      App.state.activeTask = task;
      App.state.events = [];
      document.getElementById("save-btn").disabled = true;
      this.renderTimeline();
      await App.history.refresh();
      this.waitingTaskId = null;
      this.waitForTask(task.id);
    } catch (error) {
      this.error(error.message);
      this.finishRun();
    }
  },

  finishRun() {
    App.state.queryRunning = false;
    const button = document.getElementById("query-run");
    button.classList.remove("running");
    button.textContent = "▶";
    button.disabled = false;
  },

  async waitForTask(taskId) {
    if (this.waitingTaskId === taskId) {
      return;
    }
    this.waitingTaskId = taskId;
    try {
      for (let index = 0; index < 400; index += 1) {
        const task = await App.api("/api/tasks/" + taskId);
        if (App.state.activeTask && App.state.activeTask.id !== taskId) {
          break;
        }
        App.state.activeTask = task;
        if (!["pending", "analyzing"].includes(task.status)) {
          const events = await App.api("/api/tasks/" + taskId + "/events");
          App.state.events = events.events || [];
          await App.history.refresh();
          this.renderRecords(App.state.records || []);
          this.renderTimeline();
          document.getElementById("save-btn").disabled = task.status === "failed";
          if (task.status === "failed") {
            this.error(task.error || "分析失败");
          }
          break;
        }
        await App.sleep(1500);
      }
    } catch (error) {
      this.error(error.message);
    } finally {
      this.waitingTaskId = null;
      if (!App.state.activeTask || App.state.activeTask.id === taskId) {
        this.finishRun();
      }
    }
  },

  async checkActive() {
    if (!App.state.activeTask) {
      return;
    }
    const task = await App.api("/api/tasks/" + App.state.activeTask.id);
    if (!["pending", "analyzing"].includes(task.status)) {
      await this.waitForTask(task.id);
    }
  },
};
