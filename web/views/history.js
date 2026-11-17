"use strict";

App.history = {
  bound: false,
  timer: null,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("history-search-toggle").addEventListener("click", () => {
      const box = document.getElementById("search-box");
      box.hidden = !box.hidden;
      if (!box.hidden) {
        document.getElementById("history-search").focus();
      }
    });
    document.getElementById("history-search").addEventListener("input", (event) => {
      App.state.search = event.target.value;
      window.clearTimeout(this.timer);
      this.timer = window.setTimeout(() => this.load(), 250);
    });
    document.getElementById("history-collapse").addEventListener("click", () => {
      const rail = document.getElementById("history-rail");
      rail.classList.toggle("collapsed");
      document.getElementById("history-collapse").textContent =
        rail.classList.contains("collapsed") ? "»" : "«";
    });
    document.getElementById("new-history").addEventListener("click", () => this.newHistory());
    document.getElementById("history-list").addEventListener("click", (event) => {
      const button = event.target.closest(".history-item");
      if (button) {
        this.select(Number(button.dataset.id));
      }
    });
  },

  async load() {
    try {
      const query = App.state.search ? "?q=" + encodeURIComponent(App.state.search) : "";
      const data = await App.api("/api/histories" + query);
      App.state.histories = data.histories || [];
      this.render();
      if (!App.state.activeHistory && !App.state.manualNew && App.state.histories.length) {
        await this.select(App.state.histories[0].id);
      }
    } catch (error) {
      /* The auth flow will handle 401; other errors are left to the next action. */
    }
  },

  render() {
    const list = document.getElementById("history-list");
    list.textContent = "";
    if (!App.state.histories.length) {
      const empty = App.el("p", "muted small", App.state.search ? "没有匹配的历史" : "还没有历史记录");
      empty.style.padding = "10px";
      list.append(empty);
      return;
    }
    App.state.histories.forEach((history) => {
      const button = App.el("button", "history-item");
      button.type = "button";
      button.dataset.id = String(history.id);
      if (App.state.activeHistory && App.state.activeHistory.id === history.id) {
        button.classList.add("active");
      }
      const title = App.el("span", "history-title", history.title || "未命名记录");
      const meta = App.el("span", "history-meta");
      meta.append(
        App.el("span", "", App.shortDate(history.updated_at)),
        App.el("span", "", history.record_count + " 条记录")
      );
      button.append(title, meta);
      list.append(button);
    });
  },

  async select(historyId) {
    try {
      const detail = await App.api("/api/histories/" + historyId);
      App.state.activeHistory = detail;
      App.state.manualNew = false;
      App.state.documents = detail.documents || [];
      document.getElementById("query-input").value = "";
      this.render();
      await App.reader.showHistory(detail);
      const hasParsed = (detail.documents || []).some((doc) => doc.parse_status === "parsed");
      if (hasParsed) {
        App.records.show(detail);
        if (detail.records && detail.records.length) {
          await App.records.select(detail.records[0].id, true);
        } else {
          App.records.clear();
        }
      } else {
        App.records.hide();
      }
    } catch (error) {
      /* The list stays usable; surface the error in the reader area. */
      App.reader.showError(error.message);
    }
  },

  async refresh() {
    if (!App.state.activeHistory) {
      return;
    }
    try {
      const detail = await App.api("/api/histories/" + App.state.activeHistory.id);
      App.state.activeHistory = detail;
      App.state.documents = detail.documents || [];
      const item = App.state.histories.find((history) => history.id === detail.id);
      if (item) {
        item.title = detail.title;
        item.record_count = (detail.records || []).length;
        item.updated_at = detail.updated_at;
      }
      this.render();
      App.records.show(detail);
    } catch (error) {
      /* Keep the current view. */
    }
  },

  newHistory() {
    document.getElementById("query-input").value = "";
    App.state.manualNew = true;
    App.state.activeHistory = null;
    App.state.activeTask = null;
    App.state.events = [];
    App.state.selectedEventId = null;
    this.render();
    App.records.hide();
    App.reader.showUpload();
  },
};
