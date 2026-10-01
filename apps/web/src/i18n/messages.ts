export const messages: Record<string, string> = {
  'app.title': 'ACPOS Global Home',
  'shell.front': 'Front',
  'shell.admin': 'Admin',
  'shell.sidebar.toggle': 'Toggle navigation sidebar',
  'shell.sidebar.expand': 'Expand navigation sidebar',
  'shell.sidebar.collapse': 'Collapse navigation sidebar',
  'shell.workspace.title': 'Workspace',
  'shell.workspace.maximized': 'Workspace maximized',
  'shell.error.unresolvable': 'Navigation target cannot be resolved',
  'shell.error.authority': 'Navigation authority is unavailable',
  'nav.home': 'Home',
  'nav.dashboard': 'Dashboard',
  'nav.projects': 'Projects',
  'nav.tasks': 'Tasks',
  'nav.calendar': 'Calendar',
  'nav.reports': 'Reports',
  'nav.messages': 'Messages',
  'nav.files': 'Files',
  'nav.settings': 'Settings',
  'admin.overview': 'Overview',
  'admin.accounts': 'Accounts',
  'admin.roles': 'Roles',
  'admin.permissions': 'Permissions',
  'admin.audit': 'Audit Log',
  'admin.integrations': 'Integrations',
  'admin.storage': 'Storage',
  'admin.system': 'System',
  'admin.security': 'Security',
};

export function t(key: string): string {
  return messages[key] ?? key;
}
