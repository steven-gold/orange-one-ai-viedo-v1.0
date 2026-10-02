"use client";

import { useCallback } from "react";
import { useNavigationController } from "./useNavigationController";
import type { NavigationArea, ResolvedNavigationItem } from "@/lib/navigation";
import { t } from "@/lib/i18n";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { useKeyboardNav } from "./useKeyboardNav";
import { useSidebarState } from "./useSidebarState";

export interface AppShellProps {
  accountUid?: string;
  sessionUid?: string;
  activePath?: string;
  activePageUid?: string | null;
}

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

export function AppShell({
  accountUid = DEFAULT_ACCOUNT,
  sessionUid = DEFAULT_SESSION,
  activePath = "/",
  activePageUid = null,
}: AppShellProps) {
  const sidebar = useSidebarState(false);
  const keyboard = useKeyboardNav(sidebar.expand);
  const navigation = useNavigationController(accountUid, activePath, activePageUid, sessionUid);

  const onActivate = useCallback(
    (item: ResolvedNavigationItem) => {
      navigation.navigate(item);
      sidebar.collapseOnNavigate();
    },
    [navigation, sidebar],
  );

  const onSwitchArea = useCallback(
    (area: NavigationArea) => {
      navigation.switchArea(area);
      sidebar.collapseOnNavigate();
    },
    [navigation, sidebar],
  );

  return (
    <div
      className={sidebar.collapsed ? "shell shell--collapsed" : "shell"}
      data-reduced-motion={sidebar.reducedMotion ? "true" : "false"}
    >
      <Header
        area={navigation.area}
        collapsed={sidebar.collapsed}
        onToggleSidebar={sidebar.toggle}
        onSwitchArea={onSwitchArea}
      />
      <div className="shell-body">
        <Sidebar
          items={navigation.items}
          collapsed={sidebar.collapsed}
          reducedMotion={sidebar.reducedMotion}
          onActivate={onActivate}
          onFocusWithin={keyboard.onSidebarFocus}
        />
        <main className="workspace deployment-shell" aria-label="ACPOS deployment shell" tabIndex={-1}>
          <h1 className="workspace-title">{t("shell.workspace.title")}</h1>
          {sidebar.collapsed && <p className="workspace-hint">{t("shell.workspace.maximized")}</p>}
          {navigation.loading && <p className="workspace-hint">Loading navigation</p>}
          {navigation.error && (
            <div className="shell-error" role="alert">
              {navigation.error.code === "NAVIGATION_TARGET_UNRESOLVABLE"
                ? t("shell.error.unresolvable")
                : t("shell.error.authority")}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
