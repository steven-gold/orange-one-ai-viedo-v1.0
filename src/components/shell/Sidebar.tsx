"use client";

import type { ResolvedNavigationItem } from "@/lib/navigation";
import { t } from "@/lib/i18n";
import { NavItem } from "./NavItem";

export interface SidebarProps {
  items: ResolvedNavigationItem[];
  collapsed: boolean;
  reducedMotion: boolean;
  onActivate: (item: ResolvedNavigationItem) => void;
  onFocusWithin: () => void;
}

export function Sidebar({ items, collapsed, reducedMotion, onActivate, onFocusWithin }: SidebarProps) {
  return (
    <nav
      className={collapsed ? "sidebar sidebar--collapsed" : "sidebar"}
      aria-label={t("shell.workspace.title")}
      data-collapsed={collapsed ? "true" : "false"}
      onFocus={onFocusWithin}
    >
      <ul className="nav-list">
        {items.map((item) => (
          <NavItem
            key={item.uid}
            item={item}
            collapsed={collapsed}
            reducedMotion={reducedMotion}
            onActivate={onActivate}
          />
        ))}
      </ul>
    </nav>
  );
}
