from pathlib import Path

app = Path('src/components/shell/AppShell.tsx')
s = app.read_text()

s = s.replace('type AppShellProps = {\n  children?: ReactNode;\n  activeNavId?: string;\n};', 'type AppShellProps = {\n  children?: ReactNode;\n  activeNavId?: string;\n  surface?: "front" | "admin";\n};')

anchor = '] as const;\n\nfunction Icon'
admin_nav = ''' ] as const;\n\nconst ADMIN_NAV_ITEMS: readonly NavItem[] = [\n  { id: "ADMIN-NAV-01", labelKey: "global.admin.system", icon: "strategy", href: "/admin/system" },\n  { id: "ADMIN-NAV-02", labelKey: "global.admin.iam", icon: "project" },\n  { id: "ADMIN-NAV-03", labelKey: "global.admin.dev", icon: "video" },\n  { id: "ADMIN-NAV-04", labelKey: "global.admin.social", icon: "info" },\n  { id: "ADMIN-NAV-05", labelKey: "global.admin.erp", icon: "database" },\n  { id: "ADMIN-NAV-06", labelKey: "global.admin.aiapi", icon: "video" },\n  { id: "ADMIN-NAV-07", labelKey: "global.admin.qa_criteria", icon: "qa" },\n  { id: "ADMIN-NAV-08", labelKey: "global.admin.strategy", icon: "strategy" },\n  { id: "ADMIN-NAV-09", labelKey: "global.admin.knowledge", icon: "asset" },\n] as const;\n\nfunction Icon'''
if anchor not in s: raise SystemExit('nav anchor missing')
s = s.replace(anchor, admin_nav, 1)

s = s.replace('export function AppShell({ children, activeNavId }: AppShellProps) {', 'export function AppShell({ children, activeNavId, surface = "front" }: AppShellProps) {')
s = s.replace('  const [languageOpen, setLanguageOpen] = useState(false);', '  const [languageOpen, setLanguageOpen] = useState(false);\n  const [accountOpen, setAccountOpen] = useState(false);')
s = s.replace('  const languageRef = useRef<HTMLDivElement | null>(null);', '  const languageRef = useRef<HTMLDivElement | null>(null);\n  const accountRef = useRef<HTMLDivElement | null>(null);\n  const navItems = surface === "admin" ? ADMIN_NAV_ITEMS : NAV_ITEMS;')
s = s.replace('        if (languageOpen) setLanguageOpen(false);', '        if (languageOpen) setLanguageOpen(false);\n        if (accountOpen) setAccountOpen(false);')
s = s.replace('      if (languageOpen && languageRef.current && !languageRef.current.contains(event.target as Node)) {\n        setLanguageOpen(false);\n      }', '      if (languageOpen && languageRef.current && !languageRef.current.contains(event.target as Node)) {\n        setLanguageOpen(false);\n      }\n      if (accountOpen && accountRef.current && !accountRef.current.contains(event.target as Node)) {\n        setAccountOpen(false);\n      }')
s = s.replace('  }, [expanded, languageOpen]);', '  }, [expanded, languageOpen, accountOpen]);')

old_account = '<button className="account-button" type="button" aria-label={t("global.header.account")}><span className="avatar-placeholder" aria-hidden="true"/><span className="account-label">—</span><span className="caret" aria-hidden="true">⌄</span></button>'
new_account = '''<div className="account-menu" ref={accountRef}>\n            <button\n              className="account-button"\n              type="button"\n              aria-label={t("global.header.account")}\n              aria-haspopup="menu"\n              aria-expanded={accountOpen}\n              onClick={() => setAccountOpen((open) => !open)}\n            >\n              <span className="avatar-placeholder" aria-hidden="true"/>\n              <span className="account-label">—</span>\n              <span className="caret" aria-hidden="true">⌄</span>\n            </button>\n            {accountOpen && (\n              <div className="account-popover" role="menu">\n                <a className="account-popover-link" role="menuitem" href={surface === "admin" ? "/" : "/admin/system"}>\n                  {surface === "admin" ? t("global.header.frontend") : t("global.header.admin")}\n                </a>\n              </div>\n            )}\n          </div>'''
if old_account not in s: raise SystemExit('account anchor missing')
s = s.replace(old_account, new_account, 1)
s = s.replace('{NAV_ITEMS.map((item) => {', '{navItems.map((item) => {', 1)
app.write_text(s)

cat = Path('src/i18n/catalog.ts')
c = cat.read_text()
anchor = '''  "global.header.account": {\n    "zh-TW": "帳戶",\n    "zh-CN": "账户",\n    en: "Account",\n  },'''
insert = anchor + '''\n  "global.header.admin": {\n    "zh-TW": "進入後台",\n    "zh-CN": "进入后台",\n    en: "Open Admin",\n  },\n  "global.header.frontend": {\n    "zh-TW": "返回前台",\n    "zh-CN": "返回前台",\n    en: "Back to Front",\n  },\n  "global.admin.system": {\n    "zh-TW": "系統維護",\n    "zh-CN": "系统维护",\n    en: "System Maintenance",\n  },\n  "global.admin.iam": {\n    "zh-TW": "帳戶與權限",\n    "zh-CN": "账户与权限",\n    en: "Account & Permission",\n  },\n  "global.admin.dev": {\n    "zh-TW": "企業自動開發系統",\n    "zh-CN": "企业自动开发系统",\n    en: "Enterprise Automation",\n  },\n  "global.admin.social": {\n    "zh-TW": "社群發布",\n    "zh-CN": "社群发布",\n    en: "Social Publishing",\n  },\n  "global.admin.erp": {\n    "zh-TW": "ERP",\n    "zh-CN": "ERP",\n    en: "ERP & Finance",\n  },\n  "global.admin.aiapi": {\n    "zh-TW": "AI API",\n    "zh-CN": "AI API",\n    en: "AI API",\n  },\n  "global.admin.qa_criteria": {\n    "zh-TW": "QA 評分項目",\n    "zh-CN": "QA 评分项目",\n    en: "QA Review Criteria",\n  },\n  "global.admin.strategy": {\n    "zh-TW": "戰略中心",\n    "zh-CN": "战略中心",\n    en: "Strategy Administration",\n  },\n  "global.admin.knowledge": {\n    "zh-TW": "知識庫",\n    "zh-CN": "知识库",\n    en: "Knowledge & Experience",\n  },'''
if anchor not in c: raise SystemExit('catalog anchor missing')
c = c.replace(anchor, insert, 1)
cat.write_text(c)

css = Path('src/app/globals.css')
g = css.read_text()
needle = '.caret { color: var(--text-muted); font-size: 14px; }\n'
addition = '''.caret { color: var(--text-muted); font-size: 14px; }\n.account-menu { position: relative; }\n.account-button { cursor: pointer; }\n.account-popover {\n  position: absolute;\n  z-index: 140;\n  top: 42px;\n  right: 0;\n  min-width: 164px;\n  padding: 6px;\n  border: 1px solid var(--border-normal);\n  border-radius: 10px;\n  background: var(--surface-popup);\n  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.34);\n}\n.account-popover-link {\n  height: 34px;\n  display: flex;\n  align-items: center;\n  padding: 0 10px;\n  border-radius: 8px;\n  color: var(--text-secondary);\n  text-decoration: none;\n  font-size: 12px;\n}\n.account-popover-link:hover,\n.account-popover-link:focus-visible {\n  color: var(--text-primary);\n  background: var(--purple-hover);\n}\n'''
if needle not in g: raise SystemExit('css anchor missing')
g = g.replace(needle, addition, 1)
css.write_text(g)
