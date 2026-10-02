"use client";

import type { ResolvedNavigationItem } from "@/lib/navigation";
import { t } from "@/lib/i18n";

export interface NavItemProps {
  item: ResolvedNavigationItem;
  collapsed: boolean;
  reducedMotion: boolean;
  onActivate: (item: ResolvedNavigationItem) => void;
}

export function NavItem({ item, collapsed, reducedMotion, onActivate }: NavItemProps) {
  const label = t(item.labelKey);
  return (
    <li className="nav-item">
      <button
        type="button"
        className={item.active ? "nav-link nav-link--active" : "nav-link"}
        aria-current={item.active ? "page" : undefined}
        aria-label={collapsed ? t(item.ariaLabelKey) : undefined}
        data-reduced-motion={reducedMotion ? "true" : "false"}
        onClick={() => onActivate(item)}
      >
        <span className="nav-icon" aria-hidden="true">
          {item.icon}
        </span>
        {!collapsed && <span className="nav-label">{label}</span>}
      </button>
    </li>
  );
}
