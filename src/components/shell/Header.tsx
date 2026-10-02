"use client";

import type { NavigationArea } from "@/lib/navigation";
import { t } from "@/lib/i18n";

export interface HeaderProps {
  area: NavigationArea;
  collapsed: boolean;
  onToggleSidebar: () => void;
  onSwitchArea: (area: NavigationArea) => void;
}

export function Header({ area, collapsed, onToggleSidebar, onSwitchArea }: HeaderProps) {
  return (
    <header className="shell-header">
      <button
        type="button"
        className="icon-button"
        onClick={onToggleSidebar}
        aria-label={collapsed ? t("shell.sidebar.expand") : t("shell.sidebar.collapse")}
      >
        <span aria-hidden="true">&#8801;</span>
      </button>
      <span className="shell-title">{t("app.title")}</span>
      <div className="area-switch" role="tablist" aria-label="Frontend Admin switch">
        <button
          type="button"
          role="tab"
          aria-selected={area === "FRONT"}
          className={area === "FRONT" ? "area-tab area-tab--active" : "area-tab"}
          onClick={() => onSwitchArea("FRONT")}
        >
          {t("shell.front")}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={area === "ADMIN"}
          className={area === "ADMIN" ? "area-tab area-tab--active" : "area-tab"}
          onClick={() => onSwitchArea("ADMIN")}
        >
          {t("shell.admin")}
        </button>
      </div>
    </header>
  );
}
