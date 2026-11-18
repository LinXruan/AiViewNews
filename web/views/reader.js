"use strict";

App.reader = {
  bound: false,
  draftTimer: null,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("save-btn").addEventListener("click", () => {
      if (App.state.activeTask) {
        App.report.open(App.state.activeTask.id);
      }
    });
    document.getElementById("summary-close").addEventListener("click", () => {
      this.clearSelection();
    });
  },

  showUpload() {
    document.getElementById("upload-pane").hidden = false;
    document.getElementById("reader-pane").hidden = true;
    document.getElementById("summary-panel").hidden = true;
    document.getElementById("upload-status").textContent = "";
  },

  showError(message) {
    document.getElementById("upload-pane").hidden = true;
    document.getElementById("reader-pane").hidden = false;
    document.getElementById("doc-tabs").textContent = "";
    document.getElementById("reader-body").textContent = message;
    document.getElementById("summary-panel").hidden = true;
    document.getElementById("save-btn").disabled = true;
  },

  async showHistory(detail) {
    document.getElementById("upload-pane").hidden = true;
    document.getElementById("reader-pane").hidden = false;
    const parsed = (detail.documents || []).filter((doc) => doc.parse_status === "parsed");
    if (!parsed.length) {
      const failed = (detail.documents || []).find((doc) => doc.parse_status === "failed");
      this.showError(failed ? "PDF 解析失败：" + (failed.parse_error || "未知错误") : "没有可显示的正文。");
      return;
    }
    if (!parsed.some((doc) => doc.id === App.state.activeDocId)) {
      App.state.activeDocId = parsed[0].id;
    }
    this.renderDocTabs(parsed);
    await this.loadDoc(App.state.activeDocId);
    document.getElementById("save-btn").disabled = !App.state.activeTask;
    this.clearSelection();
  },

  renderDocTabs(docs) {
    const tabs = document.getElementById("doc-tabs");
    tabs.textContent = "";
    docs.forEach((doc) => {
      const button = App.el("button", "doc-tab", (doc.filename || "").replace(/\.pdf$/i, ""));
      button.type = "button";
      button.title = doc.filename || "";
      if (doc.id === App.state.activeDocId) {
        button.classList.add("active");
      }
      button.addEventListener("click", () => this.selectDoc(doc.id));
      tabs.append(button);
    });
  },

  async selectDoc(docId) {
    if (App.state.activeDocId === docId) {
      return;
    }
    App.state.activeDocId = docId;
    const parsed = (App.state.activeHistory.documents || []).filter(
      (doc) => doc.parse_status === "parsed"
    );
    this.renderDocTabs(parsed);
    this.clearSelection();
    await this.loadDoc(docId);
  },

  async loadDoc(docId) {
    const body = document.getElementById("reader-body");
    body.textContent = "加载正文……";
    try {
      let offset = 0;
      const parts = [];
      for (let index = 0; index < 20; index += 1) {
        const data = await App.api(
          "/api/documents/" + docId + "/text?offset=" + offset + "&limit=50000"
        );
        parts.push(data.text);
        if (!data.has_more || !data.text) {
          break;
        }
        offset += data.text.length;
      }
      App.state.readerText = parts.join("");
      this.renderText(App.state.readerText);
    } catch (error) {
      body.textContent = "正文加载失败：" + error.message;
    }
  },

  renderText(text) {
    const body = document.getElementById("reader-body");
    body.textContent = "";
    App.state.readerBlocks = [];
    const value = text.replace(/\r\n/g, "\n");
    const lines = value.split("\n");
    let offset = 0;
    let current = null;
    let blockStart = 0;
    let blockLines = [];

    const flush = () => {
      if (!blockLines.length) {
        return;
      }
      const raw = blockLines.join("\n");
      const block = App.el("div", "md-block", raw);
      block.dataset.start = String(blockStart);
      block.dataset.end = String(blockStart + raw.length);
      body.append(block);
      App.state.readerBlocks.push({
        el: block,
        start: blockStart,
        end: blockStart + raw.length,
        text: raw,
      });
      blockLines = [];
      current = null;
    };

    lines.forEach((line) => {
      if (!line.trim()) {
        flush();
        offset += line.length + 1;
        return;
      }
      if (!current) {
        current = true;
        blockStart = offset;
      }
      blockLines.push(line);
      offset += line.length + 1;
    });
    flush();

    App.state.readerBlocks.forEach((block) => {
      const first = block.text.split("\n")[0];
      const heading = first.match(/^(#{1,6})\s+(.*)$/);
      if (heading) {
        const level = Math.min(heading[1].length, 3);
        block.el.className = "md-block md-h" + level;
        block.el.textContent = block.text.replace(/^#{1,6}\s+/, "");
      }
    });
    if (!App.state.readerBlocks.length) {
      body.append(App.el("p", "muted", "正文为空。"));
    }
  },

  clearHighlight() {
    App.state.readerBlocks.forEach((block) => {
      block.el.textContent = block.text;
      const first = block.text.split("\n")[0];
      const heading = first.match(/^(#{1,6})\s+/);
      if (heading) {
        block.el.textContent = block.text.replace(/^#{1,6}\s+/, "");
      }
    });
  },

  clearSelection() {
    document.getElementById("summary-panel").hidden = true;
    App.state.selectedEventId = null;
    document.querySelectorAll(".timeline-node").forEach((node) => node.classList.remove("active"));
  },

  clearDocumentHighlight() {
    this.clearHighlight();
    this.clearSelection();
  },

  findBlock(event) {
    const offset = event.source_offset ? event.source_offset.start : null;
    if (offset !== null) {
      const byOffset = App.state.readerBlocks.find(
        (block) => block.start <= offset && offset < block.end
      );
      if (byOffset) {
        return byOffset;
      }
    }
    const quote = (event.source_quote || "").trim();
    if (quote) {
      return App.state.readerBlocks.find((block) => block.text.includes(quote)) || null;
    }
    return null;
  },

  highlight(block, quote) {
    const value = block.el.textContent;
    const target = quote.trim();
    if (!target) {
      block.el.textContent = "";
      block.el.append(App.el("mark", "", value));
      return;
    }
    let start = value.indexOf(target);
    let end = start + target.length;
    if (start < 0 && target) {
      const compact = [];
      const mapping = [];
      for (let index = 0; index < value.length; index += 1) {
        if (!/\s/.test(value[index])) {
          compact.push(value[index]);
          mapping.push(index);
        }
      }
      const compactTarget = target.replace(/\s+/g, "");
      const position = compact.join("").indexOf(compactTarget);
      if (position >= 0) {
        start = mapping[position];
        end = mapping[position + compactTarget.length - 1] + 1;
      }
    }
    if (start < 0) {
      block.el.textContent = "";
      const mark = App.el("mark", "", value);
      block.el.append(mark);
      return;
    }
    block.el.textContent = "";
    block.el.append(
      document.createTextNode(value.slice(0, start)),
      App.el("mark", "", value.slice(start, end)),
      document.createTextNode(value.slice(end))
    );
  },

  async selectEvent(event) {
    if (App.state.selectedEventId === event.id) {
      this.clearSelection();
      return;
    }
    if (event.doc_id !== App.state.activeDocId) {
      await this.selectDoc(event.doc_id);
    }
    this.clearHighlight();
    const block = this.findBlock(event);
    if (!block) {
      this.showSummary(event);
      return;
    }
    this.highlight(block, event.source_quote || "");
    if (!document.body.classList.contains("is-resizing")) {
      block.el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    App.state.selectedEventId = event.id;
    App.records.setActiveEvent(event.id);
    this.showSummary(event);
  },

  showSummary(event) {
    const panel = document.getElementById("summary-panel");
    const title = document.getElementById("summary-title");
    const body = document.getElementById("summary-body");
    title.textContent = event.event_time || "时间不详";
    body.textContent = "";
    body.append(App.el("p", "summary-text", event.event_text));
    panel.hidden = false;
  },
};
