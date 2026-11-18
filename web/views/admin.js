"use strict";

App.admin = {
  bound: false,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("admin-back").addEventListener("click", () => this.close());
    document.getElementById("settings-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.saveSettings();
    });
    document.getElementById("settings-test-llm").addEventListener("click", () => this.testLlm());
    document.getElementById("settings-detect").addEventListener("click", () => this.detect());
    document.getElementById("settings-detect-pandoc").addEventListener("click", () =>
      this.detectPandoc()
    );
    document.getElementById("create-user-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.createUser(event.currentTarget);
    });
    document.getElementById("admin-detail-close").addEventListener("click", () => {
      document.getElementById("admin-task-detail").hidden = true;
    });
  },

  async open() {
    if (!App.state.user || App.state.user.role !== "admin") {
      return;
    }
    this.bind();
    document.getElementById("workspace").hidden = true;
    document.getElementById("admin-screen").hidden = false;
    document.getElementById("admin-owner").textContent = App.state.user.username;
    await this.show();
  },

  close() {
    document.getElementById("admin-screen").hidden = true;
    document.getElementById("workspace").hidden = false;
  },

  async show() {
    try {
      await Promise.all([this.loadSettings(), this.loadUsers(), this.loadTasks()]);
    } catch (error) {
      this.status("加载管理数据失败：" + error.message, true);
    }
  },

  status(message, danger) {
    const node = document.getElementById("settings-status");
    node.textContent = message || "";
    node.style.color = danger ? "var(--danger)" : "var(--muted)";
  },

  fillSettings(data) {
    document.getElementById("set-base-url").value = data.llm.base_url || "";
    document.getElementById("set-model").value = data.llm.model || "";
    document.getElementById("set-api-key").value = "";
    document.getElementById("set-api-key").placeholder = data.llm.api_key_set
      ? "已设置（" + data.llm.api_key + "），留空不修改"
      : "尚未设置";
    document.getElementById("set-temperature").value = data.llm.temperature || "0.2";
    document.getElementById("set-timeout").value = data.llm.timeout || "60";
    document.getElementById("set-mineru-cmd").value = data.parse.mineru_cmd || "";
    document.getElementById("set-tier").value = data.parse.tier || "flash";
    document.getElementById("set-pandoc").value = (data.export && data.export.pandoc) || "";
  },

  async loadSettings() {
    const data = await App.api("/api/admin/settings");
    this.fillSettings(data);
  },

  payload() {
    return {
      llm: {
        base_url: document.getElementById("set-base-url").value.trim(),
        model: document.getElementById("set-model").value.trim(),
        api_key: document.getElementById("set-api-key").value,
        temperature: Number(document.getElementById("set-temperature").value),
        timeout: Number(document.getElementById("set-timeout").value),
      },
      parse: {
        mineru_cmd: document.getElementById("set-mineru-cmd").value.trim(),
        tier: document.getElementById("set-tier").value,
      },
      export: {
        pandoc: document.getElementById("set-pandoc").value.trim(),
      },
    };
  },

  async saveSettings() {
    this.status("保存中……");
    try {
      const data = await App.api("/api/admin/settings", {
        method: "PUT",
        body: this.payload(),
      });
      this.fillSettings(data);
      this.status("已保存");
    } catch (error) {
      this.status("保存失败：" + error.message, true);
    }
  },

  async testLlm() {
    this.status("正在测试大模型……");
    try {
      const data = await App.api("/api/admin/settings/test-llm", { method: "POST" });
      this.status("连接成功 · 模型 " + data.model + " · " + data.latency_ms + "ms");
    } catch (error) {
      this.status("连接失败：" + error.message, true);
    }
  },

  async detectPandoc() {
    this.status("正在探测 pandoc……");
    const box = document.getElementById("pandoc-candidates");
    box.textContent = "";
    try {
      const data = await App.api("/api/admin/settings/detect-pandoc");
      const candidates = data.candidates || [];
      if (!candidates.length) {
        this.status("没有找到 pandoc，请手动填写完整路径。", true);
        return;
      }
      candidates.forEach((path) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = path;
        button.addEventListener("click", () => {
          document.getElementById("set-pandoc").value = path;
          this.status("已填入候选路径，保存后生效。");
        });
        box.append(button);
      });
      this.status("找到 " + candidates.length + " 个候选路径，点击填入。");
    } catch (error) {
      this.status("探测失败：" + error.message, true);
    }
  },

  async detect() {
    this.status("正在探测 mineru……");
    const box = document.getElementById("mineru-candidates");
    box.textContent = "";
    try {
      const data = await App.api("/api/admin/settings/detect-mineru");
      const candidates = data.candidates || [];
      if (!candidates.length) {
        this.status("没有找到 mineru，请手动填写完整路径。", true);
        return;
      }
      candidates.forEach((path) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = path;
        button.addEventListener("click", () => {
          document.getElementById("set-mineru-cmd").value = path;
          this.status("已填入候选路径，保存后生效。");
        });
        box.append(button);
      });
      this.status("找到 " + candidates.length + " 个候选路径，点击填入。");
    } catch (error) {
      this.status("探测失败：" + error.message, true);
    }
  },

  async loadUsers() {
    const data = await App.api("/api/admin/users");
    const body = document.getElementById("admin-user-rows");
    body.textContent = "";
    (data.users || []).forEach((user) => {
      const row = document.createElement("tr");
      const id = document.createElement("td");
      id.textContent = String(user.id);
      const name = document.createElement("td");
      const dot = document.createElement("span");
      dot.className = "user-dot";
      dot.style.background = user.avatar_color || "#2563eb";
      name.append(dot, document.createTextNode(user.username));
      const role = document.createElement("td");
      const select = document.createElement("select");
      ["user", "admin"].forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value === "admin" ? "管理员" : "普通用户";
        select.append(option);
      });
      select.value = user.role;
      select.addEventListener("change", () => this.changeRole(user, select));
      role.append(select);
      const docs = document.createElement("td");
      docs.textContent = String(user.doc_count);
      const tasks = document.createElement("td");
      tasks.textContent = String(user.task_count);
      const active = document.createElement("td");
      active.textContent = App.formatTime(user.last_active);
      row.append(id, name, role, docs, tasks, active);
      body.append(row);
    });
  },

  async changeRole(user, select) {
    const errorNode = document.getElementById("admin-user-error");
    errorNode.hidden = true;
    try {
      await App.api("/api/admin/users/" + user.id, {
        method: "PATCH",
        body: { role: select.value },
      });
      await this.loadUsers();
      if (user.id === App.state.user.id) {
        App.state.user.role = select.value;
        App.setUser(App.state.user);
      }
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
      select.value = user.role;
    }
  },

  async createUser(form) {
    const errorNode = document.getElementById("admin-user-error");
    errorNode.hidden = true;
    try {
      await App.api("/api/admin/users", {
        method: "POST",
        body: {
          username: form.username.value,
          password: form.password.value,
          role: form.role.value,
        },
      });
      form.reset();
      await this.loadUsers();
    } catch (error) {
      errorNode.textContent = error.message;
      errorNode.hidden = false;
    }
  },

  async loadTasks() {
    const data = await App.api("/api/admin/tasks");
    const body = document.getElementById("admin-task-rows");
    body.textContent = "";
    (data.tasks || []).forEach((task) => {
      const row = document.createElement("tr");
      const id = document.createElement("td");
      id.textContent = String(task.id);
      const user = document.createElement("td");
      user.textContent = task.username || "—";
      const query = document.createElement("td");
      query.textContent = task.query;
      const count = document.createElement("td");
      count.textContent = String(task.event_count || 0);
      const status = document.createElement("td");
      status.append(App.statusBadge(task.status));
      const time = document.createElement("td");
      time.textContent = App.formatTime(task.created_at);
      row.append(id, user, query, count, status, time);
      row.addEventListener("click", () => this.showTask(task.id));
      body.append(row);
    });
  },

  async showTask(taskId) {
    const detail = document.getElementById("admin-task-detail");
    detail.hidden = false;
    document.getElementById("admin-detail-title").textContent = "加载中……";
    document.getElementById("admin-detail-summary").textContent = "";
    document.getElementById("admin-detail-events").textContent = "";
    document.getElementById("admin-detail-report").textContent = "";
    try {
      const data = await App.api("/api/admin/tasks/" + taskId);
      const task = data.task;
      document.getElementById("admin-detail-title").textContent =
        "任务 #" + task.id + " · " + task.query + "（" + task.username + "）";
      document.getElementById("admin-detail-summary").textContent =
        task.timeline_summary || "暂无时间线摘要。";
      const list = document.getElementById("admin-detail-events");
      (data.events || []).forEach((event) => {
        const item = document.createElement("li");
        const date = document.createElement("span");
        date.className = "event-date";
        date.textContent = event.event_time || "时间不详";
        item.append(date, document.createTextNode(event.event_text));
        list.append(item);
      });
      if (data.report && data.report.content_md) {
        const rendered = await App.api("/api/render", {
          method: "POST",
          body: { markdown: data.report.content_md },
        });
        document.getElementById("admin-detail-report").innerHTML = rendered.html;
      } else {
        document.getElementById("admin-detail-report").textContent = "该任务没有报告。";
      }
    } catch (error) {
      document.getElementById("admin-detail-title").textContent = "加载失败：" + error.message;
    }
  },
};
