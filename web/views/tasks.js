"use strict";

App.tasks = {
  bound: false,

  init() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("query-submit").addEventListener("click", () => this.submit());
    document.getElementById("tasks-refresh").addEventListener("click", () => {
      App.pollNow();
    });
  },

  showError(message) {
    const node = document.getElementById("query-error");
    node.textContent = message || "";
    node.hidden = !message;
  },

  renderDocPicker() {
    const picker = document.getElementById("doc-picker");
    picker.textContent = "";
    const parsed = App.state.documents.filter((doc) => doc.parse_status === "parsed");
    const parsedIds = new Set(parsed.map((doc) => doc.id));
    Array.from(App.state.selectedDocs).forEach((id) => {
      if (!parsedIds.has(id)) {
        App.state.selectedDocs.delete(id);
      }
    });
    parsed.forEach((doc) => {
      if (!App.state.knownParsed.has(doc.id)) {
        App.state.knownParsed.add(doc.id);
        App.state.selectedDocs.add(doc.id);
      }
    });
    if (!parsed.length) {
      const empty = document.createElement("span");
      empty.className = "no-doc";
      empty.textContent = "暂无已解析文档，请先上传 PDF。";
      picker.append(empty);
      return;
    }
    parsed.forEach((doc) => {
      const label = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = App.state.selectedDocs.has(doc.id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          App.state.selectedDocs.add(doc.id);
        } else {
          App.state.selectedDocs.delete(doc.id);
        }
      });
      const text = document.createElement("span");
      text.textContent = doc.filename;
      label.append(checkbox, text);
      picker.append(label);
    });
  },

  renderTasks() {
    const body = document.getElementById("task-rows");
    body.textContent = "";
    document.getElementById("task-empty").hidden = App.state.tasks.length > 0;
    App.state.tasks.forEach((task) => {
      const row = document.createElement("tr");
      const query = document.createElement("td");
      query.className = "query-cell";
      query.textContent = task.query;
      const count = document.createElement("td");
      count.className = "num-cell";
      count.textContent = String(task.event_count || 0);
      const titles = document.createElement("td");
      titles.className = "titles-cell";
      const names = task.event_titles || [];
      if (!names.length) {
        titles.textContent = "—";
      } else if ((task.event_count || 0) > names.length) {
        titles.textContent = names.join(" · ") + " 等 " + task.event_count + " 条";
      } else {
        titles.textContent = names.join(" · ");
      }
      const time = document.createElement("td");
      time.className = "time-cell";
      time.textContent = App.formatTime(task.created_at);
      const status = document.createElement("td");
      status.append(App.statusBadge(task.status));
      if (task.error) {
        status.title = task.error;
      }
      const duration = document.createElement("td");
      duration.className = "time-cell";
      duration.textContent = App.duration(task.created_at, task.finished_at);
      const action = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn ghost row-action";
      button.textContent = "打开";
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        App.selectTask(task.id, "timeline");
      });
      action.append(button);
      row.append(query, count, titles, time, status, duration, action);
      row.addEventListener("click", () => App.selectTask(task.id, "timeline"));
      body.append(row);
    });
  },

  async submit() {
    const input = document.getElementById("query-input");
    const query = input.value.trim();
    const docIds = Array.from(App.state.selectedDocs);
    if (!query) {
      this.showError("请输入查询内容。");
      return;
    }
    if (!docIds.length) {
      this.showError("请选择至少一个已解析文档。");
      return;
    }
    const button = document.getElementById("query-submit");
    button.disabled = true;
    this.showError("");
    try {
      const task = await App.api("/api/tasks", {
        method: "POST",
        body: { query: query, doc_ids: docIds },
      });
      await App.pollNow();
      await App.selectTask(task.id, "tasks");
    } catch (error) {
      this.showError(error.message);
    } finally {
      button.disabled = false;
    }
  },
};
