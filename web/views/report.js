"use strict";

App.report = {
  bound: false,
  timer: null,

  init() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    const editor = document.getElementById("report-editor");
    editor.addEventListener("input", () => {
      App.markReportDirty(true);
      this.updateStatus();
      this.schedulePreview();
    });
    document.getElementById("report-save").addEventListener("click", () => this.save());
    document.getElementById("report-export").addEventListener("click", (event) => {
      if (!App.state.currentTaskId) {
        event.preventDefault();
      }
    });
  },

  async fetch(taskId) {
    const data = await App.api("/api/tasks/" + taskId + "/report");
    data.dirty = false;
    return data;
  },

  setStatus(text, danger) {
    const node = document.getElementById("report-status");
    node.textContent = text;
    node.style.color = danger ? "var(--danger)" : "";
  },

  updateStatus() {
    const task = App.state.currentTask;
    const report = App.state.report;
    if (!task) {
      this.setStatus("请选择一个分析任务。");
      return;
    }
    if (report && report.dirty) {
      this.setStatus("有未保存的修改");
      return;
    }
    if (report && report.exists) {
      this.setStatus(
        "已保存" + (report.edited_at ? " · " + App.formatTime(report.edited_at) : "")
      );
      return;
    }
    this.setStatus("尚未生成报告，可直接编辑并保存。");
  },

  render() {
    const editor = document.getElementById("report-editor");
    const task = App.state.currentTask;
    const exportLink = document.getElementById("report-export");
    const saveButton = document.getElementById("report-save");
    if (!task) {
      editor.value = "";
      editor.disabled = true;
      saveButton.disabled = true;
      exportLink.removeAttribute("href");
      document.getElementById("report-preview").textContent = "";
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "选择任务后在这里预览报告。";
      document.getElementById("report-preview").append(empty);
      this.setStatus("请选择一个分析任务。");
      return;
    }
    editor.disabled = false;
    saveButton.disabled = false;
    exportLink.href = "/api/tasks/" + task.id + "/report.docx";
    if (App.state.report && !App.state.report.dirty) {
      editor.value = App.state.report.content_md || "";
    }
    this.updateStatus();
    this.renderPreview();
  },

  schedulePreview() {
    window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => this.renderPreview(), 300);
  },

  async renderPreview() {
    const editor = document.getElementById("report-editor");
    const preview = document.getElementById("report-preview");
    if (!App.state.currentTask) {
      return;
    }
    if (!editor.value.trim()) {
      preview.textContent = "";
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "报告内容为空。";
      preview.append(empty);
      return;
    }
    try {
      const data = await App.api("/api/render", {
        method: "POST",
        body: { markdown: editor.value },
      });
      preview.innerHTML = data.html;
    } catch (error) {
      preview.textContent = "预览失败：" + error.message;
    }
  },

  async save() {
    const task = App.state.currentTask;
    if (!task) {
      return;
    }
    const button = document.getElementById("report-save");
    const content = document.getElementById("report-editor").value;
    button.disabled = true;
    try {
      const data = await App.api("/api/tasks/" + task.id + "/report", {
        method: "PUT",
        body: { content_md: content },
      });
      App.state.report = {
        task_id: task.id,
        title: "",
        content_md: content,
        edited_at: data.edited_at,
        exists: true,
        dirty: false,
      };
      this.updateStatus();
      await App.refreshTasks();
    } catch (error) {
      this.setStatus("保存失败：" + error.message, true);
    } finally {
      button.disabled = false;
    }
  },
};
