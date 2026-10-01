export interface LocalizedLabel {
  key: string;
  value: string;
}

const CATALOG: Record<string, string> = {
  'app.title': 'ACPOS',
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
  'admin.audit': 'Audit',
  'admin.integrations': 'Integrations',
  'admin.storage': 'Storage',
  'admin.system': 'System',
  'admin.security': 'Security',
};

export function localizeLabel(key: string, locale = 'en'): LocalizedLabel {
  const value = locale === 'en' ? (CATALOG[key] ?? key) : key;
  return { key, value };
}
