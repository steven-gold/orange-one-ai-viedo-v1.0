import { useCallback } from 'react';
import { useNavigationController } from './control/useNavigationController';
import type { NavigationArea, ResolvedNavigationItem } from './domain/navigation';
import { t } from './i18n/messages';
import { Header } from './shell/Header';
import { Sidebar } from './shell/Sidebar';
import { useKeyboardNav } from './shell/useKeyboardNav';
import { useSidebarState } from './shell/useSidebarState';
import './styles/shell.css';

export interface AppProps {
  accountUid?: string;
  activePath?: string;
  activePageUid?: string | null;
}

const DEFAULT_ACCOUNT = 'ACC-DEMO';

export function App({
  accountUid = DEFAULT_ACCOUNT,
  activePath = '/home',
  activePageUid = null,
}: AppProps) {
  const sidebar = useSidebarState(false);
  const keyboard = useKeyboardNav(sidebar.expand);
  const navigation = useNavigationController(accountUid, activePath, activePageUid);

  const onActivate = useCallback(
    (item: ResolvedNavigationItem) => {
      navigation.navigate(item.route);
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
      className={sidebar.collapsed ? 'shell shell--collapsed' : 'shell'}
      data-reduced-motion={sidebar.reducedMotion ? 'true' : 'false'}
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
        <main className="workspace" tabIndex={-1}>
          <h1 className="workspace-title">{t('shell.workspace.title')}</h1>
          {sidebar.collapsed && <p className="workspace-hint">{t('shell.workspace.maximized')}</p>}
          {navigation.error && (
            <div className="shell-error" role="alert">
              {navigation.error.code === 'NAVIGATION_TARGET_UNRESOLVABLE'
                ? t('shell.error.unresolvable')
                : t('shell.error.authority')}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
