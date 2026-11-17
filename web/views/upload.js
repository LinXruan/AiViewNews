"use strict";

App.upload = {
  bound: false,

  init() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("file-input").addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      event.target.value = "";
      if (files.length) {
        this.send(files);
      }
    });
    document.getElementById("docs-refresh").addEventListener("click", () => {
      App.pollNow();
    });
  },

  makeRow(filename) {
    const row = document.createElement("div");
    row.className = "upload-row";
    const top = document.createElement("div");
    top.className = "row-top";
    const name = document.createElement("span");
    name.className = "row-name";
    name.textContent = filename;
    const state = document.createElement("span");
    state.className = "muted";
    state.textContent = "上传中 0%";
    top.append(name, state);
    const progress = document.createElement("div");
    progress.className = "progress";
    const bar = document.createElement("span");
    progress.append(bar);
    row.append(top, progress);
    return { row, state, bar };
  },

  send(files) {
    if (App.state.uploading) {
      return;
    }
    const status = document.getElementById("upload-status");
    const rows = files.map((file) => {
      const item = this.makeRow(file.name);
      status.append(item.row);
      return item;
    });
    const form = new FormData();
    files.forEach((file) => form.append("files", file));

    const xhr = new XMLHttpRequest();
    App.state.uploading = true;
    xhr.open("POST", "/api/documents");
    xhr.withCredentials = true;
    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const percent = Math.round((event.loaded / event.total) * 100);
      rows.forEach((item) => {
        item.bar.style.width = percent + "%";
        item.state.textContent = "上传中 " + percent + "%";
      });
    });
    xhr.addEventListener("load", async () => {
      App.state.uploading = false;
      if (xhr.status >= 200 && xhr.status < 300) {
        let data = null;
        try {
          data = JSON.parse(xhr.responseText);
        } catch (error) {
          data = null;
        }
        const created = (data && data.documents) || [];
        rows.forEach((item, index) => {
          item.bar.style.width = "100%";
          const doc = created[index];
          if (doc) {
            item.state.textContent = App.statusText[doc.parse_status] || doc.parse_status;
          } else {
            item.state.textContent = "已接收";
          }
        });
        try {
          await App.pollNow();
        } catch (error) {
          /* Listed on the next poll. */
        }
        window.setTimeout(() => rows.forEach((item) => item.row.remove()), 1200);
      } else {
        let message = "上传失败（" + xhr.status + "）";
        try {
          const data = JSON.parse(xhr.responseText);
          if (data && data.error && data.error.message) {
            message = data.error.message;
          }
        } catch (error) {
          /* Keep the status text. */
        }
        rows.forEach((item) => {
          item.bar.style.width = "100%";
          item.bar.style.background = "var(--danger)";
          item.state.textContent = message;
          item.state.style.color = "var(--danger)";
        });
      }
    });
    xhr.addEventListener("error", () => {
      App.state.uploading = false;
      rows.forEach((item) => {
        item.state.textContent = "网络错误";
        item.state.style.color = "var(--danger)";
      });
    });
    xhr.send(form);
  },

  renderDocuments() {
    const list = document.getElementById("doc-list");
    list.textContent = "";
    if (!App.state.documents.length) {
      const empty = document.createElement("li");
      empty.className = "muted";
      empty.textContent = "还没有上传文档。";
      list.append(empty);
      return;
    }
    App.state.documents.forEach((doc) => {
      const item = document.createElement("li");
      const name = document.createElement("span");
      name.className = "doc-name";
      name.textContent = doc.filename;
      if (doc.parse_error) {
        name.title = doc.parse_error;
      }
      const meta = document.createElement("div");
      meta.className = "doc-meta";
      const pages = document.createElement("span");
      pages.textContent = doc.page_count ? doc.page_count + " 页" : "—";
      meta.append(pages, App.statusBadge(doc.parse_status));
      item.append(name, meta);
      list.append(item);
    });
  },
};
