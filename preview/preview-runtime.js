(() => {
  "use strict";

  const STORAGE_KEY = "acpos.locale";
  const SUPPORTED = ["zh-TW", "zh-CN", "en"];
  const HTML_LANG = { "zh-TW": "zh-Hant-TW", "zh-CN": "zh-Hans-CN", en: "en" };
  const LOCALE_LABEL = { "zh-TW": "繁體中文", "zh-CN": "简体中文", en: "English" };

  const COPY = {
    "zh-TW": {
      header: ["通知", "待辦", "執行中"], language: "語言", frontend: "前台", admin: "後台", account: "帳戶",
      view: "查看", close: "關閉", noData: "目前無資料",
      previewNote: "此預覽不偽造實際營運資料；正式資料會在部署與實際操作後由 Dashboard Read Model 讀取。",
      nav: { "NAV-01":"儀表板","NAV-02":"專案 / 專題","NAV-03":"素材","NAV-04":"影片","NAV-05":"剪輯配音","NAV-06":"QA","NAV-07":"資料庫","NAV-08":"戰略中心","NAV-09":"最新資訊" },
      sections: {
        "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT":["專案總數","查看專案總數"],
        "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT":["執行中","查看執行中"],
        "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT":["待處理","查看待處理"],
        "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT":["待審查","查看待審查"],
        "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT":["已完成","查看已完成"],
        "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS":["平均進度","查看平均進度"],
        "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW":["專案進度","查看專案進度"],
        "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY":["公司整體進度","查看公司整體進度"],
        "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY":["生產總覽","查看生產總覽"],
        "SEC-WORKSPACE-WB-01-NOTIFICATIONS":["通知","查看通知"],
        "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS":["公司公告","查看公司公告"],
        "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS":["AI / 產業新聞","查看 AI / 產業新聞"],
        "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY":["系統狀態","查看系統狀態"],
        "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS":["近期完成","查看近期完成"]
      }
    },
    "zh-CN": {
      header: ["通知", "待办", "执行中"], language: "语言", frontend: "前台", admin: "后台", account: "账户",
      view: "查看", close: "关闭", noData: "目前无数据",
      previewNote: "此预览不伪造实际营运数据；正式数据会在部署与实际操作后由 Dashboard Read Model 读取。",
      nav: { "NAV-01":"仪表板","NAV-02":"项目 / 专题","NAV-03":"素材","NAV-04":"影片","NAV-05":"剪辑配音","NAV-06":"QA","NAV-07":"数据库","NAV-08":"战略中心","NAV-09":"最新资讯" },
      sections: {
        "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT":["专案总数","查看专案总数"],
        "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT":["执行中","查看执行中"],
        "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT":["待处理","查看待处理"],
        "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT":["待审查","查看待审查"],
        "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT":["已完成","查看已完成"],
        "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS":["平均进度","查看平均进度"],
        "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW":["专案进度","查看专案进度"],
        "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY":["公司整体进度","查看公司整体进度"],
        "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY":["生产总览","查看生产总览"],
        "SEC-WORKSPACE-WB-01-NOTIFICATIONS":["通知","查看通知"],
        "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS":["公司公告","查看公司公告"],
        "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS":["AI / 产业新闻","查看 AI / 产业新闻"],
        "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY":["系统状态","查看系统状态"],
        "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS":["近期完成","查看近期完成"]
      }
    },
    en: {
      header: ["Notification", "To-do", "Running"], language: "Language", frontend: "Frontend", admin: "Admin", account: "Account",
      view: "View", close: "Close", noData: "No data",
      previewNote: "This preview does not fabricate operational data. Real values are read from the Dashboard Read Model after deployment and real operation.",
      nav: { "NAV-01":"Dashboard","NAV-02":"Project / Topic","NAV-03":"Assets","NAV-04":"Video","NAV-05":"Editing & Voice","NAV-06":"QA","NAV-07":"Database","NAV-08":"Strategy Center","NAV-09":"Latest Information" },
      sections: {
        "SEC-WORKSPACE-WB-01-COMPANY-PROJECT-COUNT":["Company Project Count","View Project Count"],
        "SEC-WORKSPACE-WB-01-COMPANY-RUNNING-PROJECT-COUNT":["Running Projects","View Running Projects"],
        "SEC-WORKSPACE-WB-01-COMPANY-PENDING-ACTION-COUNT":["Pending Actions","View Pending Actions"],
        "SEC-WORKSPACE-WB-01-COMPANY-PENDING-REVIEW-COUNT":["Pending Reviews","View Pending Reviews"],
        "SEC-WORKSPACE-WB-01-COMPANY-COMPLETED-PROJECT-COUNT":["Completed Projects","View Completed Projects"],
        "SEC-WORKSPACE-WB-01-COMPANY-AVERAGE-PROGRESS":["Average Progress","View Average Progress"],
        "SEC-WORKSPACE-WB-01-PROJECT-PROGRESS-OVERVIEW":["Project Progress","View Project Progress"],
        "SEC-WORKSPACE-WB-01-COMPANY-PROGRESS-SUMMARY":["Company Progress","View Company Progress"],
        "SEC-WORKSPACE-WB-01-PRODUCTION-SUMMARY":["Production Summary","View Production Summary"],
        "SEC-WORKSPACE-WB-01-NOTIFICATIONS":["Notifications","View Notifications"],
        "SEC-WORKSPACE-WB-01-COMPANY-ANNOUNCEMENTS":["Company Announcements","View Company Announcements"],
        "SEC-WORKSPACE-WB-01-INDUSTRY-NEWS":["AI / Industry News","View AI / Industry News"],
        "SEC-WORKSPACE-WB-01-SYSTEM-STATUS-SUMMARY":["System Status","View System Status"],
        "SEC-WORKSPACE-WB-01-RECENT-COMPLETIONS":["Recent Completions","View Recent Completions"]
      }
    }
  };

  let locale = SUPPORTED.includes(localStorage.getItem(STORAGE_KEY) || "") ? localStorage.getItem(STORAGE_KEY) : "zh-TW";
  let openDrawerSection = null;

  function addStyles() {
    if (document.getElementById("acpos-preview-runtime-style")) return;
    const style = document.createElement("style");
    style.id = "acpos-preview-runtime-style";
    style.textContent = `
      #acpos-preview-language-menu{position:fixed;z-index:10020;min-width:190px;padding:8px;border:1px solid rgba(139,92,255,.42);border-radius:12px;background:rgba(8,9,28,.98);box-shadow:0 16px 42px rgba(0,0,0,.42);backdrop-filter:blur(16px)}
      #acpos-preview-language-menu button{display:flex;width:100%;justify-content:space-between;gap:16px;padding:9px 10px;border:0;border-radius:8px;background:transparent;color:#f4f1ff;cursor:pointer;text-align:left;font:inherit}
      #acpos-preview-language-menu button:hover,#acpos-preview-language-menu button[aria-selected=true]{background:rgba(139,92,255,.16)}
      #acpos-preview-language-menu .code{opacity:.62;font-size:12px}
      #acpos-preview-drawer-backdrop{position:fixed;inset:0;z-index:10030;background:rgba(0,0,0,.45);display:flex;justify-content:flex-end}
      #acpos-preview-drawer{width:min(480px,92vw);height:100%;padding:22px;background:rgba(7,8,25,.98);border-left:1px solid rgba(139,92,255,.4);box-shadow:-18px 0 48px rgba(0,0,0,.42);overflow:auto;color:#f6f3ff}
      #acpos-preview-drawer header{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:18px}
      #acpos-preview-drawer h2{margin:0;font-size:20px}
      #acpos-preview-drawer .close{border:1px solid rgba(139,92,255,.38);border-radius:9px;background:rgba(139,92,255,.1);color:#fff;padding:7px 11px;cursor:pointer}
      #acpos-preview-drawer .content{padding:16px;border:1px solid rgba(139,92,255,.25);border-radius:12px;background:rgba(255,255,255,.025)}
      #acpos-preview-drawer .note{margin-top:14px;padding:12px;border-radius:10px;background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);font-size:12px;line-height:1.6;opacity:.86}
    `;
    document.head.appendChild(style);
  }

  function languageButton() { return document.querySelector('button[aria-haspopup="listbox"]'); }
  function removeLanguageMenu() { document.getElementById("acpos-preview-language-menu")?.remove(); }

  function applyLocale(next) {
    if (!SUPPORTED.includes(next)) return;
    locale = next;
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = HTML_LANG[locale];
    const c = COPY[locale];

    const langButton = languageButton();
    if (langButton) { langButton.textContent = locale; langButton.setAttribute("aria-label", c.language); langButton.setAttribute("aria-expanded", "false"); }

    document.querySelectorAll(".quick-button").forEach((button, index) => { if (c.header[index]) button.setAttribute("aria-label", c.header[index]); });
    const surface = document.querySelector(".surface-switch-group");
    if (surface) {
      surface.setAttribute("aria-label", `${c.frontend} / ${c.admin}`);
      const links = surface.querySelectorAll("a");
      if (links[0]) { links[0].textContent = c.frontend; links[0].setAttribute("aria-label", c.frontend); }
      if (links[1]) { links[1].textContent = c.admin; links[1].setAttribute("aria-label", c.admin); }
    }
    const account = document.querySelector(".account-button");
    if (account) account.setAttribute("aria-label", c.account);

    document.querySelectorAll("[data-nav-id]").forEach((item) => {
      const value = c.nav[item.getAttribute("data-nav-id")];
      if (!value) return;
      item.setAttribute("aria-label", value);
      const label = item.querySelector(".nav-label");
      if (label) label.textContent = value;
    });

    Object.entries(c.sections).forEach(([sectionId, values]) => {
      const section = document.querySelector(`[data-section-id="${sectionId}"]`);
      if (!section) return;
      const title = section.querySelector("h2");
      if (title) title.textContent = values[0];
      const button = section.querySelector("button[data-control-id]");
      if (button) { button.textContent = c.view; button.setAttribute("aria-label", values[1]); }
    });

    document.querySelectorAll('[class*="emptyState"]').forEach((node) => { node.textContent = c.noData; });
    removeLanguageMenu();
    if (openDrawerSection) openDrawer(openDrawerSection);
  }

  function openLanguageMenu() {
    const button = languageButton();
    if (!button) return;
    if (document.getElementById("acpos-preview-language-menu")) { removeLanguageMenu(); button.setAttribute("aria-expanded", "false"); return; }
    const menu = document.createElement("div");
    menu.id = "acpos-preview-language-menu";
    menu.setAttribute("role", "listbox");
    SUPPORTED.forEach((option) => {
      const item = document.createElement("button");
      item.type = "button";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", String(option === locale));
      item.innerHTML = `<span>${LOCALE_LABEL[option]}</span><span class="code">${option}</span>`;
      item.addEventListener("click", (event) => { event.stopPropagation(); applyLocale(option); });
      menu.appendChild(item);
    });
    document.body.appendChild(menu);
    const rect = button.getBoundingClientRect();
    menu.style.top = `${Math.min(rect.bottom + 8, window.innerHeight - menu.offsetHeight - 12)}px`;
    menu.style.left = `${Math.max(12, rect.right - menu.offsetWidth)}px`;
    button.setAttribute("aria-expanded", "true");
  }

  function closeDrawer() {
    document.getElementById("acpos-preview-drawer-backdrop")?.remove();
    openDrawerSection = null;
  }

  function openDrawer(section) {
    closeDrawer();
    openDrawerSection = section;
    const c = COPY[locale];
    const sectionId = section.getAttribute("data-section-id");
    const title = c.sections[sectionId]?.[0] || section.querySelector("h2")?.textContent || "—";
    const body = section.querySelector('[class*="cardBody"]');
    const backdrop = document.createElement("div");
    backdrop.id = "acpos-preview-drawer-backdrop";
    backdrop.innerHTML = `<aside id="acpos-preview-drawer" role="dialog" aria-modal="true" aria-label="${title.replaceAll('"','&quot;')}"><header><h2></h2><button class="close" type="button"></button></header><div class="content"></div><div class="note"></div></aside>`;
    const drawer = backdrop.querySelector("#acpos-preview-drawer");
    drawer.querySelector("h2").textContent = title;
    drawer.querySelector(".close").textContent = c.close;
    drawer.querySelector(".content").innerHTML = body ? body.innerHTML : `<div>${c.noData}</div>`;
    drawer.querySelector(".note").textContent = c.previewNote;
    drawer.querySelector(".close").addEventListener("click", closeDrawer);
    backdrop.addEventListener("click", (event) => { if (event.target === backdrop) closeDrawer(); });
    document.body.appendChild(backdrop);
    drawer.querySelector(".close").focus();
  }

  function init() {
    addStyles();
    applyLocale(locale);
    const button = languageButton();
    if (button) {
      button.style.cursor = "pointer";
      button.addEventListener("click", (event) => { event.preventDefault(); event.stopPropagation(); openLanguageMenu(); });
    }
    document.addEventListener("click", (event) => {
      if (!document.getElementById("acpos-preview-language-menu")) return;
      if (!document.getElementById("acpos-preview-language-menu").contains(event.target) && event.target !== languageButton()) {
        removeLanguageMenu();
        languageButton()?.setAttribute("aria-expanded", "false");
      }
    });
    document.querySelectorAll("button[data-control-id]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        const section = button.closest("section[data-section-id]");
        if (section) openDrawer(section);
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (document.getElementById("acpos-preview-drawer-backdrop")) closeDrawer();
      else { removeLanguageMenu(); languageButton()?.setAttribute("aria-expanded", "false"); }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
