"use client";

import { useEffect, useRef, useState } from "react";

type NavItem = {
  id: string;
  label: string;
  icon: "dashboard" | "project" | "asset" | "video" | "edit" | "qa" | "database" | "strategy";
};

const NAV_ITEMS: readonly NavItem[] = [
  { id: "NAV-01", label: "儀表板", icon: "dashboard" },
  { id: "NAV-02", label: "專案 / 專題", icon: "project" },
  { id: "NAV-03", label: "素材", icon: "asset" },
  { id: "NAV-04", label: "影片", icon: "video" },
  { id: "NAV-05", label: "剪輯配音", icon: "edit" },
  { id: "NAV-06", label: "QA", icon: "qa" },
  { id: "NAV-07", label: "資料庫", icon: "database" },
  { id: "NAV-08", label: "戰略中心", icon: "strategy" },
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

export function AppShell() {
  const [expanded, setExpanded] = useState(false);
  const collapseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sidebarRef = useRef<HTMLElement | null>(null);

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
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && expanded && !sidebarRef.current?.contains(document.activeElement)) {
        setExpanded(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      cancelCollapse();
    };
  }, [expanded]);

  return (
    <div className="acpos-shell" data-vis-step="VIS-00">
      <header className="global-header" aria-label="Global Header">
        <div className="brand-lockup" aria-label="ORANGE ONE">ORANGE ONE</div>
        <div className="header-cluster">
          <button className="quick-button" type="button" aria-label="通知"><HeaderIcon kind="bell"/><span>0</span></button>
          <button className="quick-button" type="button" aria-label="待辦"><HeaderIcon kind="todo"/><span>0</span></button>
          <button className="quick-button" type="button" aria-label="執行中"><HeaderIcon kind="running"/><span>0</span></button>
          <button className="language-button" type="button" aria-label="語言">zh-TW</button>
          <button className="account-button" type="button" aria-label="帳戶登入"><span className="avatar-placeholder" aria-hidden="true"/><span className="account-label">—</span><span className="caret" aria-hidden="true">⌄</span></button>
        </div>
      </header>

      <aside
        ref={sidebarRef}
        className={expanded ? "global-sidebar is-expanded" : "global-sidebar"}
        aria-label="Primary Navigation"
        onPointerEnter={openSidebar}
        onPointerLeave={scheduleCollapse}
        onFocusCapture={openSidebar}
        onBlurCapture={scheduleCollapse}
      >
        <div className="sidebar-surface" aria-hidden={!expanded} />
        <nav className="nav-list">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className="nav-item"
              aria-label={item.label}
              data-nav-id={item.id}
            >
              <span className="nav-icon"><Icon name={item.icon}/></span>
              <span className="nav-label" aria-hidden={!expanded}>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace-slot" aria-label="Page Content Slot" />
    </div>
  );
}
