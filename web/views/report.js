"use strict";

App.report = {
  bound: false,
  timer: null,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("report-back").addEventListener("click", () => this.close());
    document.getElementById("report-save").addEventListener("click", () => this.save());
    document.getElementById("report-editor").addEventListener("input", () => {
      App.state.reportDirty = true;
      this.status("有未保存的修改");
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => this.preview(), 300);
    });
  },

  status(text, danger) {
    const node = document.getElementById("report-status");
    node.textContent = text;
    node.style.color = danger ? "var(--danger)" : "";
  },

  async open(taskId) {
    App.state.reportTaskId = taskId;
    App.state.reportDirty = false;
    try {
      const report = await App.api("/api/tasks/" + taskId + "/report");
      document.getElementById("report-editor").value = report.content_md || "";
      document.getElementById("report-export").href = "/api/tasks/" + taskId + "/report.docx";
      document.getElementById("report-screen").hidden = false;
      this.status(report.exists ? "已保存" : "尚未生成报告，可直接编辑并保存");
      await this.preview();
    } catch (error) {
      this.status("报告加载失败：" + error.message, true);
    }
  },

  close() {
    if (App.state.reportDirty && !window.confirm("报告有未保存的修改，确定返回吗？")) {
      return;
    }
    document.getElementById("report-screen").hidden = true;
  },

  async preview() {
    const markdown = document.getElementById("report-editor").value;
    const preview = document.getElementById("report-preview");
    if (!markdown.trim()) {
      preview.textContent = "报告内容为空。";
      return;
    }
    try {
      const data = await App.api("/api/render", {
        method: "POST",
        body: { markdown },
      });
      preview.innerHTML = data.html;
    } catch (error) {
      preview.textContent = "预览失败：" + error.message;
    }
  },

  async save() {
    if (!App.state.reportTaskId) {
      return;
    }
    const button = document.getElementById("report-save");
    button.disabled = true;
    try {
      const data = await App.api("/api/tasks/" + App.state.reportTaskId + "/report", {
        method: "PUT",
        body: { content_md: document.getElementById("report-editor").value },
      });
      App.state.reportDirty = false;
      this.status("已保存 · " + App.formatTime(data.edited_at));
    } catch (error) {
      this.status("保存失败：" + error.message, true);
    } finally {
      button.disabled = false;
    }
  },
};
