"use strict";

App.timeline = {
  bound: false,
  selected: null,

  init() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("detail-close").addEventListener("click", () => {
      document.getElementById("event-detail").hidden = true;
      this.selected = null;
    });
    document.getElementById("detail-source-btn").addEventListener("click", () => this.showSource());
  },

  render() {
    const task = App.state.currentTask;
    const summary = document.getElementById("timeline-summary");
    const track = document.getElementById("timeline-track");
    const undated = document.getElementById("timeline-undated");
    const empty = document.getElementById("timeline-empty");
    track.textContent = "";
    undated.textContent = "";
    undated.hidden = true;
    if (!task) {
      summary.textContent = "请选择一个分析任务。";
      empty.hidden = false;
      document.getElementById("event-detail").hidden = true;
      return;
    }
    summary.textContent = task.timeline_summary || "时间线摘要尚未生成。";
    const events = App.state.events || [];
    const dated = events.filter((event) => event.event_time);
    const unknown = events.filter((event) => !event.event_time);
    dated.forEach((event) => track.append(this.node(event, event.event_time)));
    if (!events.length) {
      empty.textContent = task.status === "done" || task.status === "partial"
        ? "本次查询没有抽取到相关事件，可以尝试更换查询词。"
        : "正在抽取事件，请稍候……";
      empty.hidden = false;
    } else {
      empty.hidden = true;
    }
    if (unknown.length) {
      undated.hidden = false;
      const head = document.createElement("h3");
      head.textContent = "时间不详（" + unknown.length + " 条）";
      undated.append(head);
      const wrap = document.createElement("div");
      wrap.className = "doc-picker";
      unknown.forEach((event) => wrap.append(this.node(event, "时间不详")));
      undated.append(wrap);
    }
    if (this.selected) {
      const current = events.find((event) => event.id === this.selected.id);
      if (current) {
        this.showDetail(current);
      }
    }
  },

  node(event, dateText) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "timeline-node";
    button.dataset.eventId = String(event.id);
    if (this.selected && this.selected.id === event.id) {
      button.classList.add("active");
    }
    const date = document.createElement("span");
    date.className = "node-date";
    date.textContent = dateText;
    const title = document.createElement("span");
    title.className = "node-title";
    title.textContent = event.event_text.length > 42
      ? event.event_text.slice(0, 42) + "…"
      : event.event_text;
    button.append(date, title);
    button.addEventListener("click", () => this.showDetail(event));
    return button;
  },

  showDetail(event) {
    this.selected = event;
    document.querySelectorAll(".timeline-node").forEach((node) => {
      node.classList.toggle("active", node.dataset.eventId === String(event.id));
    });
    document.getElementById("detail-time").textContent = event.event_time || "时间不详";
    document.getElementById("detail-text").textContent = event.event_text;
    document.getElementById("detail-doc").textContent = event.filename || "—";
    document.getElementById("detail-page").textContent = event.page ? "第 " + event.page + " 页" : "未知";
    document.getElementById("detail-quote").textContent = event.source_quote || "—";
    const source = document.getElementById("source-view");
    source.hidden = true;
    source.textContent = "";
    document.getElementById("detail-source-btn").hidden = !event.source_offset;
    document.getElementById("event-detail").hidden = false;
  },

  async showSource() {
    const event = this.selected;
    if (!event || !event.source_offset) {
      return;
    }
    const container = document.getElementById("source-view");
    container.hidden = false;
    container.textContent = "加载中……";
    try {
      const offset = Math.max(0, event.source_offset.start - 1500);
      const data = await App.api(
        "/api/documents/" + event.doc_id + "/text?offset=" + offset + "&limit=5000"
      );
      const start = event.source_offset.start - data.offset;
      const end = event.source_offset.end - data.offset;
      container.textContent = "";
      if (start < 0 || end > data.text.length) {
        container.textContent = data.text;
        return;
      }
      container.append(document.createTextNode(data.text.slice(0, start)));
      const mark = document.createElement("mark");
      mark.textContent = data.text.slice(start, end);
      container.append(mark, document.createTextNode(data.text.slice(end)));
    } catch (error) {
      container.textContent = "原文加载失败：" + error.message;
    }
  },
};
