"use client";

import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { LOCALES, LOCALE_LABELS, type TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import brandStyles from "./BrandLogo.module.css";
import languageStyles from "./LanguageSelector.module.css";
import { bindIdentityClientProjectionAdapters } from "@/domain/catalog/identityClientProjectionAdapters";
import { bindIdentityClientCommandAdapters } from "@/domain/catalog/identityClientCommandAdapters";

type NavItem = {
  id: string;
  pageUid: string;
  labelKey: TranslationKey;
  icon: "dashboard" | "project" | "asset" | "video" | "edit" | "qa" | "database" | "strategy" | "info";
  href: string;
};

type AppShellProps = {
  children?: ReactNode;
  activeNavId?: string;
  surface?: "front" | "admin";
};

const NAV_ITEMS: readonly NavItem[] = [
  { id: "NAV-01", pageUid: "workspace:WB-01", labelKey: "global.nav.dashboard", icon: "dashboard", href: "/" },
  { id: "NAV-02", pageUid: "CORE-01", labelKey: "global.nav.project_topic", icon: "project", href: "/core" },
  { id: "NAV-03", pageUid: "ASSET-01", labelKey: "global.nav.asset", icon: "asset", href: "/assets" },
  { id: "NAV-04", pageUid: "VIDEO-01", labelKey: "global.nav.video", icon: "video", href: "/video" },
  { id: "NAV-05", pageUid: "EDIT-01", labelKey: "global.nav.edit_voice", icon: "edit", href: "/edit" },
  { id: "NAV-06", pageUid: "QA-01", labelKey: "global.nav.qa", icon: "qa", href: "/qa" },
  { id: "NAV-07", pageUid: "admin:DB-01", labelKey: "global.nav.database", icon: "database", href: "/database" },
  { id: "NAV-08", pageUid: "workspace:STR-01", labelKey: "global.nav.strategy", icon: "strategy", href: "/strategy" },
] as const;

const ADMIN_NAV_ITEMS: readonly NavItem[] = [
  { id: "ADMIN-NAV-01", pageUid: "admin:SYS-01", labelKey: "global.admin.system", icon: "strategy", href: "/admin/system" },
  { id: "ADMIN-NAV-02", pageUid: "admin:IAM-01", labelKey: "global.admin.iam", icon: "project", href: "/admin/accounts" },
  { id: "ADMIN-NAV-03", pageUid: "admin:DEV-01", labelKey: "global.admin.dev", icon: "video", href: "/admin/dev" },
  { id: "ADMIN-NAV-04", pageUid: "admin:SOC-01", labelKey: "global.admin.social", icon: "info", href: "/admin/social" },
  { id: "ADMIN-NAV-05", pageUid: "admin:ERP-01", labelKey: "global.admin.erp", icon: "database", href: "/admin/erp" },
  { id: "ADMIN-NAV-06", pageUid: "admin:AIAPI-01", labelKey: "global.admin.aiapi", icon: "video", href: "/admin/aiapi" },
  { id: "ADMIN-NAV-07", pageUid: "admin:SG-02", labelKey: "global.admin.qa_criteria", icon: "qa", href: "/admin/qa-criteria" },
  { id: "ADMIN-NAV-08", pageUid: "admin:STR-01", labelKey: "global.admin.strategy", icon: "strategy", href: "/admin/strategy" },
] as const;

function Icon({ name }: { name: NavItem["icon"] }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "dashboard":
      return <svg {...common}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>;
    case "project":
      return <svg {...common}><path d="M3 7.5h7l2 2H21v9.5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 7.5V5a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v2.5"/></svg>;
    case "asset":
      return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m5 17 4.2-4.2 3.2 3.2 2.4-2.4L19 17"/></svg>;
    case "video":
      return <svg {...common}><rect x="3" y="5" width="14" height="14" rx="2"/><path d="m17 10 4-2v8l-4-2z"/><path d="m9.5 9 4 3-4 3z"/></svg>;
    case "edit":
      return <svg {...common}><path d="M4 5h6M14 5h6M4 12h3M11 12h9M4 19h9M17 19h3"/><circle cx="12" cy="5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="19" r="2"/></svg>;
    case "qa":
      return <svg {...common}><path d="M12 3 20 6v6c0 4.8-3.1 7.6-8 9-4.9-1.4-8-4.2-8-9V6z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg>;
    case "database":
      return <svg {...common}><ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/><path d="M4 11.5v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></svg>;
    case "strategy":
      return <svg {...common}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.5"/><path d="m14 10 4-4M18 6h-3M18 6v3"/></svg>;
    case "info":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7h.01"/></svg>;
  }
}

function HeaderIcon({ kind }: { kind: "bell" | "todo" | "running" }) {
  const common = {
    width: 17,
    height: 17,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (kind === "bell") return <svg {...common}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>;
  if (kind === "todo") return <svg {...common}><rect x="4" y="4" width="16" height="16" rx="2"/><path d="m8 12 2.2 2.2L16 8.5"/></svg>;
  return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
}

export function AppShell({ children, activeNavId, surface = "front" }: AppShellProps) {
  bindIdentityClientProjectionAdapters();
  bindIdentityClientCommandAdapters();
  const { locale, setLocale, t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [identityLabel, setIdentityLabel] = useState<string | null>(null);
  const [visiblePageUids, setVisiblePageUids] = useState<readonly string[]>([]);
  const collapseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sidebarRef = useRef<HTMLElement | null>(null);
  const languageRef = useRef<HTMLDivElement | null>(null);
  const accountRef = useRef<HTMLDivElement | null>(null);
  const visiblePageSet = new Set(visiblePageUids);
  const navItems = (surface === "admin" ? ADMIN_NAV_ITEMS : NAV_ITEMS).filter((item) => visiblePageSet.has(item.pageUid));
  const frontSurfaceTarget = NAV_ITEMS.find((item) => visiblePageSet.has(item.pageUid));
  const adminSurfaceTarget = ADMIN_NAV_ITEMS.find((item) => visiblePageSet.has(item.pageUid));

  const cancelCollapse = () => {
    if (collapseTimer.current) {
      clearTimeout(collapseTimer.current);
      collapseTimer.current = null;
    }
  };

  const openSidebar = () => {
    cancelCollapse();
    setExpanded(true);
  };

  const scheduleCollapse = () => {
    cancelCollapse();
    collapseTimer.current = setTimeout(() => {
      if (!sidebarRef.current?.contains(document.activeElement)) setExpanded(false);
    }, 180);
  };

  useEffect(() => {
    let cancelled = false;
    async function loadIdentity() {
      try {
        const response = await fetch("/v1/identity/session", { cache: "no-store", credentials: "include" });
        if (!response.ok) return;
        const payload: unknown = await response.json();
        if (!payload || typeof payload !== "object" || Array.isArray(payload)) return;
        const record = payload as Record<string, unknown>;
        if (!cancelled) {
          if (typeof record.email === "string") setIdentityLabel(record.email);
          const visible = Array.isArray(record.visible_page_uids)
            ? record.visible_page_uids.filter((value): value is string => typeof value === "string")
            : [];
          setVisiblePageUids(visible);
        }
      } catch {
        // Identity runtime status is surfaced by the page; shell remains fail-closed.
      }
    }
    void loadIdentity();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setLanguageOpen(false);
        setAccountOpen(false);
        if (expanded && !sidebarRef.current?.contains(document.activeElement)) setExpanded(false);
      }
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (languageRef.current && !languageRef.current.contains(target)) setLanguageOpen(false);
      if (accountRef.current && !accountRef.current.contains(target)) setAccountOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("pointerdown", onPointerDown);
      cancelCollapse();
    };
  }, [expanded]);

  const go = (href: string) => {
    if (window.location.pathname === href) return;
    window.location.assign(href);
  };

  return (
    <div className="acpos-shell" data-vis-step="VIS-00" data-sidebar-expanded={expanded ? "true" : "false"}>
      <header className="global-header" aria-label={t("global.shell.header")}>
        <div className={brandStyles.wrapper} aria-label={t("global.brand.name")}>
          <img className={brandStyles.logo} src="/brand/orange-one-logo.png" alt="ORANGE ONE" />
        </div>

        <div className="header-cluster">
          <button className="quick-button" type="button" aria-label={t("global.header.notifications")} onClick={() => go("/")}><HeaderIcon kind="bell"/><span>—</span></button>
          <button className="quick-button" type="button" aria-label={t("global.header.todo")} onClick={() => go("/")}><HeaderIcon kind="todo"/><span>—</span></button>
          <button className="quick-button" type="button" aria-label={t("global.header.running")} onClick={() => go("/")}><HeaderIcon kind="running"/><span>—</span></button>

          <div className={languageStyles.control} ref={languageRef}>
            <button
              className={languageStyles.button}
              type="button"
              aria-label={t("global.header.language")}
              aria-haspopup="listbox"
              aria-expanded={languageOpen}
              onClick={() => setLanguageOpen((open) => !open)}
            >
              {LOCALE_LABELS[locale]}
            </button>
            {languageOpen && (
              <div className={languageStyles.menu} role="listbox" aria-label={t("global.header.language")}>
                {LOCALES.map((option) => (
                  <button
                    key={option}
                    type="button"
                    role="option"
                    aria-selected={locale === option}
                    className={`${languageStyles.option} ${locale === option ? languageStyles.selected : ""}`}
                    onClick={() => {
                      setLocale(option);
                      setLanguageOpen(false);
                    }}
                  >
                    <span>{LOCALE_LABELS[option]}</span>
                    <span className={languageStyles.code}>{option}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="surface-switch-group" aria-label={`${t("global.header.frontend")} / ${t("global.header.admin")}`}>
            {frontSurfaceTarget && (
              <button
                type="button"
                className="surface-switch-button"
                data-control-uid="GHS-CTL-SURFACE-FRONT"
                data-target-page-uid={frontSurfaceTarget.pageUid}
                data-navigation-target={frontSurfaceTarget.href}
                aria-label={t("global.header.frontend")}
                aria-current={surface === "front" ? "page" : undefined}
                onClick={() => go(frontSurfaceTarget.href)}
              >
                {t("global.header.frontend")}
              </button>
            )}
            {adminSurfaceTarget && (
              <button
                type="button"
                className="surface-switch-button"
                data-control-uid="GHS-CTL-SURFACE-ADMIN"
                data-target-page-uid={adminSurfaceTarget.pageUid}
                data-navigation-target={adminSurfaceTarget.href}
                aria-label={t("global.header.admin")}
                aria-current={surface === "admin" ? "page" : undefined}
                onClick={() => go(adminSurfaceTarget.href)}
              >
                {t("global.header.admin")}
              </button>
            )}
          </div>

          <div ref={accountRef} className="account-menu" data-port-uid="GHS-PORT-IDENTITY">
            {identityLabel ? (
              <button className="account-button" type="button" aria-label={t("global.header.account")} onClick={() => setAccountOpen((open) => !open)} aria-expanded={accountOpen}>
                <span className="avatar-placeholder" aria-hidden="true"/>
                <span className="account-label">{identityLabel}</span>
                <span className="caret" aria-hidden="true">⌄</span>
              </button>
            ) : (
              <a className="account-button" href="/login" aria-label={t("global.header.login")}>
                <span className="avatar-placeholder" aria-hidden="true"/>
                <span className="account-label">{t("global.header.login")}</span>
              </a>
            )}
            {identityLabel && accountOpen && (
              <div className="account-popover">
                <div className="account-popover-link" aria-hidden="true">{identityLabel}</div>
                <button type="button" className="account-popover-link" onClick={() => go("/admin/accounts")}>{t("global.admin.iam")}</button>
              </div>
            )}
          </div>
        </div>
      </header>

      <aside
        ref={sidebarRef}
        className={expanded ? "global-sidebar is-expanded" : "global-sidebar"}
        aria-label={t("global.shell.primary_navigation")}
        onPointerEnter={openSidebar}
        onPointerLeave={scheduleCollapse}
        onFocusCapture={openSidebar}
        onBlurCapture={scheduleCollapse}
      >
        <div className="sidebar-surface" aria-hidden={!expanded} />
        <nav className="nav-list">
          {navItems.map((item) => {
            const isActive = item.id === activeNavId;
            const label = t(item.labelKey);
            return (
              <button
                key={item.id}
                type="button"
                className={isActive ? "nav-item is-active" : "nav-item"}
                aria-label={label}
                aria-current={isActive ? "page" : undefined}
                data-nav-id={item.id}
                data-target-page-uid={item.pageUid}
                data-navigation-target={item.href}
                onClick={() => go(item.href)}
              >
                <span className="nav-icon"><Icon name={item.icon}/></span>
                <span className="nav-label" aria-hidden={!expanded}>{label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace-slot" aria-label={t("global.shell.page_content")}>{children}</main>
    </div>
  );
}
