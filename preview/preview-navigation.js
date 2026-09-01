(() => {
  "use strict";
  const ROUTES = Object.freeze({
    "/":"index.html",
    "/core":"core.html",
    "/assets":"assets.html",
    "/video":"video.html",
    "/edit":"edit.html",
    "/qa":"qa.html",
    "/database":"db.html",
    "/strategy":"strategy.html",
    "/info":"info.html",
    "/admin/system":"system.html",
    "/admin/accounts":"accounts.html",
    "/admin/dev":"dev.html",
    "/admin/social":"social.html",
    "/admin/erp":"erp.html",
    "/admin/aiapi":"aiapi.html",
    "/admin/qa-criteria":"qa-criteria.html",
    "/admin/strategy":"strategy-admin.html",
    "/admin/knowledge":"knowledge-admin.html"
  });
  const TESTS = Object.freeze({
    "admin":["[data-control-uid='GHS-CTL-SURFACE-ADMIN']","/admin/system"],
    "front":["[data-control-uid='GHS-CTL-SURFACE-FRONT']","/"],
    "core":["[data-nav-id='NAV-02']","/core"],
    "assets":["[data-nav-id='NAV-03']","/assets"],
    "video":["[data-nav-id='NAV-04']","/video"],
    "edit":["[data-nav-id='NAV-05']","/edit"],
    "qa":["[data-nav-id='NAV-06']","/qa"],
    "database":["[data-nav-id='NAV-07']","/database"],
    "strategy":["[data-nav-id='NAV-08']","/strategy"],
    "info":["[data-nav-id='NAV-09']","/info"],
    "accounts":["[data-nav-id='ADMIN-NAV-02']","/admin/accounts"],
    "dev":["[data-nav-id='ADMIN-NAV-03']","/admin/dev"],
    "social":["[data-nav-id='ADMIN-NAV-04']","/admin/social"],
    "erp":["[data-nav-id='ADMIN-NAV-05']","/admin/erp"],
    "aiapi":["[data-nav-id='ADMIN-NAV-06']","/admin/aiapi"],
    "qa-criteria":["[data-nav-id='ADMIN-NAV-07']","/admin/qa-criteria"],
    "strategy-admin":["[data-nav-id='ADMIN-NAV-08']","/admin/strategy"],
    "knowledge-admin":["[data-nav-id='ADMIN-NAV-09']","/admin/knowledge"]
  });
  const flatUrl = (file) => new URL(file, location.href).href;
  const routeFromAnchor = (anchor) => {
    const raw = anchor.getAttribute("href") || "";
    if (raw.startsWith("/")) {
      try { return new URL(raw, location.origin).pathname.replace(/\/$/, "") || "/"; } catch { return null; }
    }
    return null;
  };
  const rewriteAnchor = (anchor) => {
    const route = routeFromAnchor(anchor);
    if (!route || !ROUTES[route]) return;
    anchor.dataset.previewCanonicalRoute = route;
    anchor.setAttribute("href", flatUrl(ROUTES[route]));
  };
  const rewriteAll = () => document.querySelectorAll("a[href]").forEach(rewriteAnchor);
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("a[href]") : null;
    if (!target) return;
    const canonical = target.dataset.previewCanonicalRoute || routeFromAnchor(target);
    if (!canonical || !ROUTES[canonical]) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    location.assign(flatUrl(ROUTES[canonical]));
  }, true);
  const observer = new MutationObserver(rewriteAll);
  observer.observe(document.documentElement, {subtree:true, childList:true, attributes:true, attributeFilter:["href"]});
  rewriteAll();
  document.documentElement.dataset.previewNavigation = "READY";
  const selftest = new URLSearchParams(location.search).get("acpos-nav-selftest");
  if (selftest && TESTS[selftest]) {
    const [selector, forcedRoute] = TESTS[selftest];
    setTimeout(() => {
      const anchor = document.querySelector(selector);
      if (!anchor) {
        document.documentElement.dataset.previewNavigationSelftest = "MISSING_ANCHOR";
        return;
      }
      anchor.setAttribute("href", forcedRoute);
      document.documentElement.dataset.previewNavigationSelftest = "CLICKING";
      anchor.click();
    }, 900);
  }
})();
