"use strict";

App.upload = {
  bound: false,

  bind() {
    if (this.bound) {
      return;
    }
    this.bound = true;
    document.getElementById("pdf-input").addEventListener("change", (event) => {
      const files = Array.from(event.target.files || []);
      event.target.value = "";
      if (files.length) {
        this.send(files);
      }
    });
  },

  send(files) {
    const status = document.getElementById("upload-status");
    status.textContent = "上传中……";
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/documents");
    xhr.withCredentials = true;
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        status.textContent = "上传中 " + Math.round((event.loaded / event.total) * 100) + "%";
      }
    });
    xhr.addEventListener("load", () => {
      let data = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch (error) {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300 && data) {
        this.pollDraft(data.history_id);
      } else {
        status.textContent =
          data && data.error ? data.error.message : "上传失败（" + xhr.status + "）";
      }
    });
    xhr.addEventListener("error", () => {
      status.textContent = "网络错误，上传失败。";
    });
    xhr.send(form);
  },

  async pollDraft(historyId) {
    const status = document.getElementById("upload-status");
    for (let index = 0; index < 600; index += 1) {
      try {
        const detail = await App.api("/api/histories/" + historyId);
        const docs = detail.documents || [];
        const parsing = docs.filter((doc) => ["pending", "parsing"].includes(doc.parse_status));
        status.textContent =
          detail.status === "draft"
            ? "解析中：" + docs.length + " 个文件" + (parsing.length ? "，剩余 " + parsing.length : "")
            : "解析完成";
        if (detail.status !== "draft") {
          await App.history.load();
          await App.history.select(historyId);
          status.textContent = "";
          return;
        }
      } catch (error) {
        status.textContent = error.message;
        return;
      }
      await App.sleep(1200);
    }
    status.textContent = "解析超时，请稍后刷新历史列表。";
  },
};
