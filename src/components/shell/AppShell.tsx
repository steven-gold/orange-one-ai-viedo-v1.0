"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { activateNavigation, fetchNavigationContext } from "@/lib/client";
import type { NavigationArea, ResolvedNavigationItem } from "@/lib/navigation";
import { LOCALES, LOCALE_LABELS, type TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import brandStyles from "./BrandLogo.module.css";
import languageStyles from "./LanguageSelector.module.css";

type IconName =
  | "dashboard"
  | "project"
  | "asset"
  | "video"
  | "edit"
  | "qa"
  | "database"
  | "strategy"
  | "info";

type AppShellProps = {
  children?: ReactNode;
  accountUid?: string;
  sessionUid?: string;
  surface?: "front" | "admin";
};

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function asIcon(name: string): IconName {
  const allowed: IconName[] = [
    "dashboard",
    "project",
    "asset",
    "video",
    "edit",
    "qa",
    "database",
    "strategy",
    "info",
  ];
  return allowed.includes(name as IconName) ? (name as IconName) : "dashboard";
}

function Icon({ name }: { name: IconName }) {
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
      return <svg {...common}><path d="M4 5h6M14 5h6M4 12h3M11 12h9M4 19h3"/><circle cx="12" cy="5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="19" r="2"/></svg>;
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

export function AppShell({
  children,
  accountUid = DEFAULT_ACCOUNT,
  sessionUid = DEFAULT_SESSION,
  surface = "front",
}: AppShellProps) {
  const { locale, setLocale, t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const [languageOpen, setLanguageOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [area, setArea] = useState<NavigationArea>(surface === "admin" ? "ADMIN" : "FRONT");
  const [items, setItems] = useState<ResolvedNavigationItem[]>([]);
  const [activeUid, setActiveUid] = useState<string | null>(null);
  const collapseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sidebarRef = useRef<HTMLElement | null>(null);
  const languageRef = useRef<HTMLDivElement | null>(null);
  const accountRef = useRef<HTMLDivElement | null>(null);

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
    const controller = new AbortController();
    fetchNavigationContext(
      { area, accountUid, sessionUid, activePath: window.location.pathname },
      controller.signal,
    )
      .then((context) => {
        setItems(context.items);
        const match = context.items.find((item) => item.route === window.location.pathname);
        setActiveUid(match?.uid ?? context.items[0]?.uid ?? null);
      })
      .catch(() => {
        setItems([]);
      });
    return () => controller.abort();
  }, [area, accountUid, sessionUid]);

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

  const go = useCallback((item: ResolvedNavigationItem) => {
    void activateNavigation(accountUid, sessionUid, item.uid);
    setActiveUid(item.uid);
    if (window.location.pathname !== item.route) {
      window.history.pushState({}, "", item.route);
    }
  }, [accountUid, sessionUid]);

  const switchArea = (next: NavigationArea) => {
    setArea(next);
    setExpanded(false);
  };

  return (
    <div className="acpos-shell" data-vis-step="VIS-00" data-sidebar-expanded={expanded ? "true" : "false"}>
      <header className="global-header" aria-label={t("global.shell.header")}>
        <div className={brandStyles.wrapper} aria-label={t("global.brand.name")}>
          <img className={brandStyles.logo} src="/brand/orange-one-logo.png" alt="ORANGE ONE" />
        </div>

        <div className="header-cluster">
          <button className="quick-button" type="button" aria-label={t("global.header.notifications")} aria-disabled="true" disabled><HeaderIcon kind="bell"/><span>0</span></button>
          <button className="quick-button" type="button" aria-label={t("global.header.todo")} aria-disabled="true" disabled><HeaderIcon kind="todo"/><span>0</span></button>
          <button className="quick-button" type="button" aria-label={t("global.header.running")} aria-disabled="true" disabled><HeaderIcon kind="running"/><span>0</span></button>

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

          <div className="surface-switch-group" role="tablist" aria-label={`${t("global.header.frontend")} / ${t("global.header.admin")}`}>
            <button
              type="button"
              role="tab"
              className="surface-switch-button"
              aria-label={t("global.header.frontend")}
              aria-current={area === "FRONT" ? "page" : undefined}
              onClick={() => switchArea("FRONT")}
            >
              {t("global.header.frontend")}
            </button>
            <button
              type="button"
              role="tab"
              className="surface-switch-button"
              aria-label={t("global.header.admin")}
              aria-current={area === "ADMIN" ? "page" : undefined}
              onClick={() => switchArea("ADMIN")}
            >
              {t("global.header.admin")}
            </button>
          </div>

          <div ref={accountRef} className="account-menu">
            <button className="account-button" type="button" aria-label={t("global.header.account")} onClick={() => setAccountOpen((open) => !open)} aria-expanded={accountOpen}>
              <span className="avatar-placeholder" aria-hidden="true"/>
              <span className="account-label">{accountUid}</span>
              <span className="caret" aria-hidden="true">⌄</span>
            </button>
            {accountOpen && (
              <div className="account-popover">
                <div className="account-popover-link" aria-hidden="true">{accountUid}</div>
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
          {items.map((item) => {
            const isActive = item.uid === activeUid;
            const label = t(item.labelKey as TranslationKey);
            return (
              <button
                key={item.uid}
                type="button"
                className={isActive ? "nav-item is-active" : "nav-item"}
                aria-label={label}
                aria-current={isActive ? "page" : undefined}
                data-nav-id={item.uid}
                data-navigation-target={item.route}
                onClick={() => go(item)}
              >
                <span className="nav-icon"><Icon name={asIcon(item.icon)}/></span>
                <span className="nav-label" aria-hidden={!expanded}>{label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="workspace-slot deployment-shell" aria-label={t("global.shell.page_content")}>{children}</main>
    </div>
  );
}
