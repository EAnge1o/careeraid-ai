/* 全局工具：认证、API 调用、渲染 */
(function () {
  const STORAGE_KEY = "careeraid_token";

  function getApiBase() {
    // 兼容用户直接用 file:// 打开前端页面的场景
    // 正常情况（通过 Flask 打开 http://127.0.0.1:5000/）保持同源相对路径即可
    if (window.location && window.location.protocol === "file:") {
      return "http://127.0.0.1:5000";
    }
    return "";
  }

  function getToken() {
    return localStorage.getItem(STORAGE_KEY) || "";
  }

  function setToken(token) {
    if (token) localStorage.setItem(STORAGE_KEY, token);
  }

  function clearToken() {
    localStorage.removeItem(STORAGE_KEY);
  }

  async function logout() {
    // 通知后端使 token 失效；接口失败（token 已失效/后端未启动）不影响本地退出
    try {
      await apiFetch("/logout", { method: "POST" });
    } catch (e) {
      /* 忽略 */
    }
    clearToken();
    window.location.href = "index.html";
  }

  function requireAuth() {
    const token = getToken();
    if (!token) {
      window.location.href = "login.html";
      // 阻止后续代码执行
      throw new Error("not authed");
    }
    return true;
  }

  async function apiFetch(path, options = {}) {
    const headers = Object.assign({}, options.headers || {});
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const opts = Object.assign({}, options, { headers });
    const url = (getApiBase() || "") + path;
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      const hint =
        "网络请求失败（Failed to fetch）。请确认：\n" +
        "1) 后端已启动：python app.py（默认 http://127.0.0.1:5000）\n" +
        "2) 前端请用浏览器打开：http://127.0.0.1:5000/ （不要用 file:// 直接打开 html）\n" +
        "3) 若端口有改动，请同步修改后端启动端口或在浏览器访问正确地址";
      const msg = (e && e.message) ? e.message : String(e);
      throw new Error(hint + "\n\n原始错误：" + msg);
    }
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { ok: res.ok, raw: text };
    }
    if (!res.ok) {
      const msg = (data && data.error) ? data.error : ("请求失败：" + res.status);
      throw new Error(msg);
    }
    return data;
  }

  function qs(id) {
    return document.getElementById(id);
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function scoreClass(score) {
    const n = Number(score || 0);
    if (n >= 75) return "good";
    if (n >= 55) return "mid";
    return "bad";
  }

  function mountTopbar(active) {
    const topbar = document.querySelector(".topbar");
    if (!topbar) return;
    const nav = topbar.querySelector(".nav");
    if (!nav) return;
    const token = getToken();
    const authed = Boolean(token);

    // 比赛/验收版：核心导航 4 个按钮
    const links = [
      { href: "upload.html", text: "简历上传", id: "upload" },
      { href: "test.html", text: "性格测评", id: "test" },
      { href: "job.html", text: "提升规划", id: "job" },
      { href: "report.html", text: "报告生成", id: "report" },
    ];

    nav.innerHTML = "";
    if (authed) {
      // chat 作为核心页入口
      const chat = document.createElement("a");
      chat.href = "chat.html";
      chat.className = "btn" + (active === "chat" ? " primary" : "");
      chat.textContent = "Agent对话";
      nav.appendChild(chat);

      for (const l of links) {
        const a = document.createElement("a");
        a.href = l.href;
        a.className = "btn" + (active === l.id ? " primary" : "");
        a.textContent = l.text;
        nav.appendChild(a);
      }
      const logoutBtn = document.createElement("button");
      logoutBtn.className = "btn danger";
      logoutBtn.textContent = "退出登录";
      logoutBtn.addEventListener("click", () => {
        logout();
      });
      nav.appendChild(logoutBtn);
    } else {
      const login = document.createElement("a");
      login.href = "login.html";
      login.className = "btn primary";
      login.textContent = "立即登录";
      nav.appendChild(login);
    }
  }

  window.CareerAid = {
    getToken,
    setToken,
    clearToken,
    logout,
    requireAuth,
    apiFetch,
    qs,
    escapeHtml,
    scoreClass,
    mountTopbar,
  };
})();
