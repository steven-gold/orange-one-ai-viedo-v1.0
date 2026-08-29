from pathlib import Path
import re, json


def must_replace(path, old, new, count=1):
    p = Path(path)
    s = p.read_text()
    if s.count(old) < count:
        raise SystemExit(f"missing replacement in {path}: {old[:100]!r}")
    p.write_text(s.replace(old, new, count))


info_path = "authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml"
must_replace(info_path, "  surface: WORKSPACE\n", "  surface: FRONT_WORKSPACE\n")
must_replace(
    info_path,
    "  navigation_mode: SUPPORTING_CONTEXTUAL_DEEP_LINK\n  global_l1: false\n",
    "  navigation_mode: FRONT_L1\n  global_l1: true\n  navigation_id: NAV-09\n  navigation_label_zh: 最新資訊\n  navigation_label_en: Latest Information\n",
)
p = Path(info_path)
s = p.read_text()
s = s.replace("  status: FINAL_LOCKED\n", "  status: FINAL_LOCKED\n  revision: 2026-08-30-USER-APPROVED-FRONT-L1-NAV09\n", 1)
p.write_text(s)

nav = "authority/global/ACPOS_CURRENT_NAVIGATION_PERMISSION_AUTHORITY_FINAL_LOCKED.yaml"
p = Path(nav)
s = p.read_text()
s = s.replace("  status: FINAL_LOCKED\n", "  status: FINAL_LOCKED\n  revision: 2026-08-30-USER-APPROVED-INFO-NAV09\n", 1)
s = s.replace("  count: 8\n  flat_l1_only: true\n", "  count: 9\n  flat_l1_only: true\n", 1)
anchor = """  - order: 8
    nav_id: NAV-08
    label:
      zh-TW: 戰略中心
      en: Strategy Center
    page_uid: workspace:STR-01
    child_menu: FORBIDDEN
    unauthorized: HIDDEN
"""
addition = anchor + """  - order: 9
    nav_id: NAV-09
    label:
      zh-TW: 最新資訊
      en: Latest Information
    page_uid: workspace:INFO-01
    child_menu: FORBIDDEN
    unauthorized: HIDDEN
"""
if anchor not in s:
    raise SystemExit("NAV-08 anchor missing")
s = s.replace(anchor, addition, 1)
start = s.find("supporting_page_entry:\n")
end = s.find("iam_permission_bundles:\n", start)
if start < 0 or end < 0:
    raise SystemExit("supporting_page_entry block missing")
s = s[:start] + s[end:]
iam_anchor = """  - bundle: FRONT-L1-08
    page_uid: workspace:STR-01
    label_zh: 戰略中心
"""
if iam_anchor not in s:
    raise SystemExit("IAM front anchor missing")
s = s.replace(iam_anchor, iam_anchor + """  - bundle: FRONT-L1-09
    page_uid: workspace:INFO-01
    label_zh: 最新資訊
""", 1)
p.write_text(s)

shell = "authority/global/GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY_FINAL_LOCKED_V1.9.yaml"
p = Path(shell)
s = p.read_text()
s = s.replace("  revision: 2026-08-29-USER-APPROVED-LOGO-COLOR-ADAPTATION\n", "  revision: 2026-08-30-USER-APPROVED-INFO-NAV09\n", 1)
s = s.replace("- 'L1 navigation is exactly: 儀表板 / 專案/專題 / 素材 / 影片 / 剪輯配音 / QA / 資料庫 / 戰略中心'", "- 'L1 navigation is exactly: 儀表板 / 專案/專題 / 素材 / 影片 / 剪輯配音 / QA / 資料庫 / 戰略中心 / 最新資訊'", 1)
s = s.replace("All eight navigation items", "All nine navigation items")
s = s.replace("ONLY 8 canonical navigation icons", "ONLY 9 canonical navigation icons")
s = s.replace("ONLY the 8 navigation icons", "ONLY the 9 navigation icons")
s = s.replace("only the eight icons", "only the nine icons")
s = s.replace("only 8 nav icons", "only 9 nav icons")
s = s.replace("  count: 8\n  order_fixed: true\n", "  count: 9\n  order_fixed: true\n", 1)
nav8 = """  - nav_id: NAV-08
    label:
      zh-TW: 戰略中心
      zh-CN: 战略中心
      en: Strategy Center
    child_policy: NO_CHILD_MENU
    control_uid: GHS-CTL-NAV-08
    target: Resolve from Canonical Navigation Authority by nav_id; frontend must not invent route
    submenu: FORBIDDEN
    subtitle: FORBIDDEN
    chevron: FORBIDDEN
"""
nav9 = """  - nav_id: NAV-09
    label:
      zh-TW: 最新資訊
      zh-CN: 最新资讯
      en: Latest Information
    child_policy: NO_CHILD_MENU
    control_uid: GHS-CTL-NAV-09
    target: Resolve from Canonical Navigation Authority by nav_id; frontend must not invent route
    submenu: FORBIDDEN
    subtitle: FORBIDDEN
    chevron: FORBIDDEN
"""
if nav8 not in s:
    raise SystemExit("shell NAV08 block missing")
s = s.replace(nav8, nav8 + nav9, 1)
s = s.replace("ALL NAV-01..NAV-08 are direct L1 leaves", "ALL NAV-01..NAV-09 are direct L1 leaves")
s = s.replace("responsibility: Eight direct flat L1 navigation icons/labels; no child/submenu/subtitle", "responsibility: Nine direct flat L1 navigation icons/labels; no child/submenu/subtitle")
ctl8 = """- control_uid: GHS-CTL-NAV-08
  section_uid: GHS-SEC-03
  component_uid: GHS-CMP-NAV
  visual_uid: GHS-VIS-NAV
  type: NAV_ITEM
  label:
    zh-TW: 戰略中心
    zh-CN: 战略中心
    en: Strategy Center
  nav_id: NAV-08
  child_policy: NO_CHILD_MENU
  action_uid: GHS-ACT-NAVIGATE
  gate_uid: GHS-GATE-NAV
  permission_uid: GHS-PERM-NAV
  collapsed: ICON_ONLY_WITH_ACCESSIBLE_NAME
  expanded: ICON_PLUS_SINGLE_LINE_L1_LABEL_ONLY
  subtitle: FORBIDDEN
  submenu: FORBIDDEN
  chevron: FORBIDDEN
"""
ctl9 = """- control_uid: GHS-CTL-NAV-09
  section_uid: GHS-SEC-03
  component_uid: GHS-CMP-NAV
  visual_uid: GHS-VIS-NAV
  type: NAV_ITEM
  label:
    zh-TW: 最新資訊
    zh-CN: 最新资讯
    en: Latest Information
  nav_id: NAV-09
  child_policy: NO_CHILD_MENU
  action_uid: GHS-ACT-NAVIGATE
  gate_uid: GHS-GATE-NAV
  permission_uid: GHS-PERM-NAV
  collapsed: ICON_ONLY_WITH_ACCESSIBLE_NAME
  expanded: ICON_PLUS_SINGLE_LINE_L1_LABEL_ONLY
  subtitle: FORBIDDEN
  submenu: FORBIDDEN
  chevron: FORBIDDEN
"""
if ctl8 not in s:
    raise SystemExit("shell control NAV08 missing")
s = s.replace(ctl8, ctl8 + ctl9, 1)
p.write_text(s)

sys_path = "authority/global/ACPOS_SYSTEM_AUTHORITY_FINAL_LOCKED_CURRENT.yaml"
p = Path(sys_path)
s = p.read_text()
s = s.replace("  status: FINAL_LOCKED\n", "  status: FINAL_LOCKED\n  revision: 2026-08-30-USER-APPROVED-INFO-NAV09\n", 1)
s = s.replace("    l1_count: 8\n    meaning: Front workspace navigation only\n", "    l1_count: 9\n    meaning: Front workspace navigation only\n", 1)
front_start = s.find("  front_workspace:\n")
admin_start = s.find("  admin:\n", front_start)
front = s[front_start:admin_start]
if "    - workspace:INFO-01\n" not in front:
    front = front.replace("    - workspace:STR-01\n", "    - workspace:STR-01\n    - workspace:INFO-01\n", 1)
s = s[:front_start] + front + s[admin_start:]
s = s.replace("  supporting:\n    workspace:INFO-01: Not a ninth front L1; contextual/deep-link entry only.\n", "", 1)
p.write_text(s)

pim = "authority/global/ACPOS_PAGE_INTEGRATION_MATRIX_FINAL_LOCKED_CURRENT.yaml"
p = Path(pim)
s = p.read_text()
s = s.replace("  status: FINAL_LOCKED\n", "  status: FINAL_LOCKED\n  revision: 2026-08-30-USER-APPROVED-INFO-NAV09\n", 1)
s = s.replace("- page_uid: workspace:INFO-01\n  name_zh: 最新資訊工作區\n  surface: SUPPORTING_FRONT_WORKSPACE\n", "- page_uid: workspace:INFO-01\n  name_zh: 最新資訊工作區\n  surface: FRONT_WORKSPACE\n", 1)
s = s.replace("  navigation: SUPPORTING_CONTEXTUAL_DEEP_LINK_NOT_FRONT_L1\n", "  navigation: FRONT_L1_NAV-09\n", 1)
p.write_text(s)

i18na = "authority/global/ACPOS_I18N_TRANSLATION_ENCODING_FINAL_LOCKED_V1.0.yaml"
p = Path(i18na)
s = p.read_text()
s = s.replace("  status: FINAL_LOCKED\n", "  status: FINAL_LOCKED\n  revision: 2026-08-30-USER-APPROVED-INFO-NAV09\n", 1)
navstr = """    nav.strategy:
      zh-TW: 戰略中心
      zh-CN: 战略中心
      en: Strategy Center
"""
if navstr not in s:
    raise SystemExit("i18n strategy nav anchor missing")
s = s.replace(navstr, navstr + """    nav.latest_information:
      zh-TW: 最新資訊
      zh-CN: 最新资讯
      en: Latest Information
""", 1)
p.write_text(s)

cat = "src/i18n/catalog.ts"
p = Path(cat)
s = p.read_text()
navcode = """  \"global.nav.strategy\": {
    \"zh-TW\": \"戰略中心\",
    \"zh-CN\": \"战略中心\",
    en: \"Strategy Center\",
  },
"""
if navcode not in s:
    raise SystemExit("runtime strategy nav anchor missing")
s = s.replace(navcode, navcode + """  \"global.nav.latest_information\": {
    \"zh-TW\": \"最新資訊\",
    \"zh-CN\": \"最新资讯\",
    en: \"Latest Information\",
  },
""", 1)
p.write_text(s)

app = "src/components/shell/AppShell.tsx"
p = Path(app)
s = p.read_text()
s = s.replace('icon: "dashboard" | "project" | "asset" | "video" | "edit" | "qa" | "database" | "strategy";', 'icon: "dashboard" | "project" | "asset" | "video" | "edit" | "qa" | "database" | "strategy" | "info";', 1)
navline = '  { id: "NAV-08", labelKey: "global.nav.strategy", icon: "strategy", href: "/strategy" },\n'
if navline not in s:
    raise SystemExit("AppShell NAV08 line missing")
s = s.replace(navline, navline + '  { id: "NAV-09", labelKey: "global.nav.latest_information", icon: "info", href: "/info" },\n', 1)
strategy_case = '''    case "strategy":
      return <svg {...common}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="2.5"/><path d="m14 10 4-4M18 6h-3M18 6v3"/></svg>;
'''
if strategy_case not in s:
    raise SystemExit("AppShell strategy icon case missing")
s = s.replace(strategy_case, strategy_case + '''    case "info":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7h.01"/></svg>;
''', 1)
p.write_text(s)

text = Path(info_path).read_text()
block = text.split("  controls:\n", 1)[1].split("  integration_ports:\n", 1)[0]
entries = []
for chunk in re.split(r"(?m)^  - control_uid: ", block)[1:]:
    lines = chunk.splitlines()
    uid = lines[0].strip()
    def get(key):
        m = re.search(rf"(?m)^    {re.escape(key)}: (.+)$", chunk)
        return m.group(1).strip() if m else ""
    entries.append({"id": uid, "section": get("section_uid"), "component": get("component_uid"), "visual": get("visual_uid"), "type": get("type"), "label": get("label")})
if len(entries) != 66:
    raise SystemExit(f"expected 66 INFO controls, got {len(entries)}")
if len({e['id'] for e in entries}) != 66:
    raise SystemExit("duplicate INFO control uid")
if len({e['section'] for e in entries}) != 12:
    raise SystemExit("expected 12 INFO sections")
if len({e['component'] for e in entries}) != 20:
    raise SystemExit("expected 20 INFO components")

en_overrides = {
    "重新整理 / Refresh": "Refresh", "搜尋資訊 / Search": "Search", "範圍篩選 / Scope Filter": "Scope Filter",
    "來源健康狀態 / Source Health": "Source Health", "警示資訊流 / Alert Feed": "Alert Feed",
    "研究佇列 / Research Queue": "Research Queue", "候選決策 / Candidate Decision": "Candidate Decision",
    "查看 Citation": "View Citation", "採用 Context": "Adopt Context", "查看 Audit / Correlation": "View Audit / Correlation",
}
repl = {"資":"资","訊":"讯","範":"范","圍":"围","篩":"筛","選":"选","來":"来","狀":"状","態":"态","佇":"伫","採":"采","決":"决","匯":"汇","證":"证","據":"据","頁":"页","聯":"联","結":"结","錯":"错","誤":"误","關":"关","閉":"闭"}
for e in entries:
    e["tw"] = e["label"]
    e["cn"] = "".join(repl.get(ch, ch) for ch in e["label"])
    e["en"] = en_overrides.get(e["label"], e["label"])

controls_json = json.dumps(entries, ensure_ascii=False, indent=2)
Path("src/i18n/infoCatalog.ts").write_text(f'''import type {{ Locale }} from "./catalog";\n\nexport type InfoControlSpec = {{ id:string; section:string; component:string; visual:string; type:string; label:string; tw:string; cn:string; en:string }};\nexport const INFO_CONTROLS: readonly InfoControlSpec[] = {controls_json} as const;\nexport const INFO_CONTROL_COUNT = INFO_CONTROLS.length;\nexport function infoText(locale:Locale,item:InfoControlSpec){{return locale === "en" ? item.en : locale === "zh-CN" ? item.cn : item.tw;}}\nexport const INFO_PAGE_TEXT = {{\n  title: {{"zh-TW":"最新資訊工作區","zh-CN":"最新资讯工作区",en:"Latest Information Workspace"}},\n  fact: {{"zh-TW":"FACT","zh-CN":"FACT",en:"FACT"}},\n  inference: {{"zh-TW":"INFERENCE / RECOMMENDATION","zh-CN":"INFERENCE / RECOMMENDATION",en:"INFERENCE / RECOMMENDATION"}},\n  readOnly: {{"zh-TW":"Research Queue / Run 僅顯示受治理的唯讀狀態；不得在此啟動或取消研究。","zh-CN":"Research Queue / Run 仅显示受治理的只读状态；不得在此启动或取消研究。",en:"Research Queue / Run is governed read-only status here; no Start or Cancel Research action is exposed."}},\n  firewall: {{"zh-TW":"Knowledge Firewall：Fact / Inference / Recommendation 不可直接修改 Canon、Lock、Priority、Budget、Task、Release 或 Publish。","zh-CN":"Knowledge Firewall：Fact / Inference / Recommendation 不可直接修改 Canon、Lock、Priority、Budget、Task、Release 或 Publish。",en:"Knowledge Firewall: Fact / Inference / Recommendation cannot directly modify Canon, Lock, Priority, Budget, Task, Release, or Publish."}}\n}} as const;\nexport function infoPageText(locale:Locale,key:keyof typeof INFO_PAGE_TEXT){{return INFO_PAGE_TEXT[key][locale];}}\n''')

Path("src/components/pages/InfoVisual.tsx").write_text(r'''"use client";
import { useMemo, type ReactNode } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { INFO_CONTROLS, INFO_CONTROL_COUNT, infoText, infoPageText, type InfoControlSpec } from "@/i18n/infoCatalog";
import styles from "./InfoVisual.module.css";

const SECTION_TITLES: Record<string,string> = {
  "INFO-01-SEC-01":"Context / Projection Control","INFO-01-SEC-02":"Scope / Source Health","INFO-01-SEC-03":"Alert Feed",
  "INFO-01-SEC-04":"Fact Pack Explorer","INFO-01-SEC-05":"Fact / Inference Detail","INFO-01-SEC-06":"Evidence / Source Metadata",
  "INFO-01-SEC-07":"Freshness / Completeness / Confidence","INFO-01-SEC-08":"Research Queue / Runs","INFO-01-SEC-09":"Context Candidate Review",
  "INFO-01-SEC-10":"Citation","INFO-01-SEC-11":"Action Dock","INFO-01-SEC-12":"Audit / Status"
};
const bySection=(id:string)=>INFO_CONTROLS.filter(x=>x.section===id);
function Control({item}:{item:InfoControlSpec}){
  const {locale}=useI18n(); const label=infoText(locale,item);
  const common={"data-control-id":item.id,"data-component-uid":item.component,"data-visual-uid":item.visual,"data-disabled-reason":"Gate not satisfied"};
  if(item.type==="READONLY") return <div className={styles.readonly} {...common}><span>{label}</span><strong>—</strong></div>;
  if(item.type==="LIST") return <div className={styles.listControl} {...common}><span>{label}</span><div className={styles.listView}>—</div></div>;
  if(item.type==="FILTER") return <label className={styles.fieldControl} {...common}><span>{label}</span><select disabled defaultValue=""><option value="">—</option></select></label>;
  if(item.type==="TAB") return <button type="button" disabled className={styles.tab} {...common}>{label}</button>;
  return <button type="button" disabled className={`${styles.button} ${item.type==="PRIMARY_BUTTON"?styles.primary:""}`} {...common}>{label}</button>;
}
function Panel({id,children,className=""}:{id:string;children?:ReactNode;className?:string}){
  const items=bySection(id); return <section className={`${styles.panel} ${className}`} data-section-id={id} data-visual-uid={items[0]?.visual}><div className={styles.titleRow}><h2>{SECTION_TITLES[id]}</h2></div>{children??<div className={styles.stack}>{items.map(x=><Control key={x.id} item={x}/>)}</div>}</section>;
}
export function InfoVisual(){
  const {locale}=useI18n();
  const valid=useMemo(()=>INFO_CONTROL_COUNT===66&&new Set(INFO_CONTROLS.map(x=>x.id)).size===66&&new Set(INFO_CONTROLS.map(x=>x.section)).size===12&&new Set(INFO_CONTROLS.map(x=>x.component)).size===20,[]);
  const sec1=bySection("INFO-01-SEC-01"),sec5=bySection("INFO-01-SEC-05"),sec9=bySection("INFO-01-SEC-09"),sec10=bySection("INFO-01-SEC-10"),sec11=bySection("INFO-01-SEC-11"),sec12=bySection("INFO-01-SEC-12");
  const fact=sec5.filter(x=>x.component==="INFO-01-CMP-FACT"),inference=sec5.filter(x=>x.component==="INFO-01-CMP-INFERENCE");
  return <div className={styles.page} data-page-uid="workspace:INFO-01" data-vis-step="VIS-09" data-page-state="EMPTY" data-authority-sections="12" data-authority-visuals="12" data-authority-components="20" data-authority-controls="66" data-registry-valid={valid?"true":"false"}>
    <section className={styles.contextBar} data-section-id="INFO-01-SEC-01" data-visual-uid="INFO-01-VIS-CONTEXT"><div className={styles.contextGrid}>{sec1.slice(0,4).map(x=><Control key={x.id} item={x}/>)}</div><div className={styles.contextActions}>{sec1.slice(4).map(x=><Control key={x.id} item={x}/>)}</div></section>
    <div className={styles.primaryGrid}><aside className={styles.rail}><Panel id="INFO-01-SEC-02"/><Panel id="INFO-01-SEC-03"/></aside><main className={styles.center}><Panel id="INFO-01-SEC-04"/><Panel id="INFO-01-SEC-05"><div className={styles.factTabs}>{sec5.filter(x=>x.type==="TAB").map(x=><Control key={x.id} item={x}/>)}</div><div className={styles.factSplit}><div className={styles.factBox}><div className={styles.classLabel}>{infoPageText(locale,"fact")}</div>{fact.filter(x=>x.type!=="TAB").map(x=><Control key={x.id} item={x}/>)}</div><div className={styles.inferenceBox}><div className={styles.classLabel}>{infoPageText(locale,"inference")}</div>{inference.filter(x=>x.type!=="TAB").map(x=><Control key={x.id} item={x}/>)}</div></div></Panel><Panel id="INFO-01-SEC-06"/></main><aside className={styles.rail}><Panel id="INFO-01-SEC-07"/><Panel id="INFO-01-SEC-08"><div className={styles.stack}>{bySection("INFO-01-SEC-08").map(x=><Control key={x.id} item={x}/>)}</div><div className={styles.notice}>{infoPageText(locale,"readOnly")}</div></Panel></aside></div>
    <Panel id="INFO-01-SEC-09" className={styles.lower}><div className={styles.candidateGrid}>{sec9.map(x=><Control key={x.id} item={x}/>)}</div></Panel>
    <Panel id="INFO-01-SEC-10" className={styles.lower}><div className={styles.citationGrid}>{sec10.map(x=><Control key={x.id} item={x}/>)}</div></Panel>
    <Panel id="INFO-01-SEC-11" className={styles.lower}><div className={styles.actionDock}>{sec11.map(x=><Control key={x.id} item={x}/>)}</div></Panel>
    <Panel id="INFO-01-SEC-12" className={styles.lower}><div className={styles.statusGrid}>{sec12.map(x=><Control key={x.id} item={x}/>)}</div><div className={styles.notice}>{infoPageText(locale,"firewall")}</div></Panel>
  </div>;
}
''')

Path("src/components/pages/InfoVisual.module.css").write_text(r'''.page{min-width:1280px;min-height:100%;display:grid;gap:var(--section-gap);padding:0 0 var(--section-gap);color:var(--text-primary)}
.panel,.contextBar{min-width:0;border:1px solid var(--border-subtle);border-radius:var(--panel-radius);background:var(--surface-l1)}.panel{padding:var(--content-padding)}
.contextBar{min-height:56px;padding:var(--content-padding);display:grid;grid-template-columns:minmax(0,1fr) max-content;gap:var(--inner-gap);align-items:end}.contextGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.contextActions{display:flex;gap:8px;align-items:end}
.primaryGrid{display:grid;grid-template-columns:minmax(280px,1fr) minmax(720px,3fr) minmax(300px,1fr);gap:var(--section-gap);align-items:start}.rail,.center,.stack{min-width:0;display:grid;gap:var(--section-gap)}.stack{gap:8px}
.titleRow{min-height:28px;display:flex;align-items:center;margin-bottom:var(--inner-gap)}.titleRow h2{margin:0;font-size:14px;line-height:1.25;font-weight:720;color:var(--text-primary)}
.readonly,.fieldControl,.listControl{min-width:0;display:grid;gap:6px}.readonly>span,.fieldControl>span,.listControl>span{min-height:14px;color:var(--text-muted);font-size:10px;line-height:1.2}.readonly strong{height:var(--control-height);display:flex;align-items:center;padding:0 10px;border:1px solid var(--border-subtle);border-radius:var(--button-radius);background:var(--surface-input);color:var(--text-secondary);font-size:12px;font-weight:600}.fieldControl select{width:100%;height:var(--control-height);border:1px solid var(--border-normal);border-radius:var(--button-radius);background:var(--surface-input);color:var(--text-secondary);padding:0 10px}.listView{min-height:150px;display:grid;place-items:center;border:1px solid var(--border-subtle);border-radius:var(--button-radius);background:var(--surface-input);color:var(--text-muted)}
.button,.tab{min-height:var(--control-height);min-width:88px;padding:0 12px;border:1px solid var(--border-normal);border-radius:var(--button-radius);background:var(--surface-l2);color:var(--text-secondary);white-space:normal;line-height:1.2}.primary{min-width:120px;background:linear-gradient(135deg,var(--purple-secondary),var(--purple-primary));border-color:var(--border-active);color:var(--text-primary);box-shadow:0 0 18px var(--purple-glow)}
.factTabs{display:flex;gap:8px;margin-bottom:10px}.factSplit{display:grid;grid-template-columns:1fr 1fr;gap:16px}.factBox,.inferenceBox{min-width:0;display:grid;gap:8px;padding:12px;border:1px solid var(--border-subtle);border-radius:var(--button-radius);background:var(--surface-input)}.factBox{border-top:2px solid var(--border-active)}.inferenceBox{border-top:2px solid var(--border-normal)}.classLabel{font-size:11px;font-weight:760;letter-spacing:.04em;color:var(--text-secondary)}
.candidateGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.citationGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.actionDock{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.statusGrid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;align-items:end}.notice{margin-top:10px;padding:12px;border:1px solid var(--border-subtle);border-radius:var(--button-radius);background:var(--surface-input);color:var(--text-muted);font-size:12px;line-height:1.5}
@media(max-width:1599px){.primaryGrid{grid-template-columns:minmax(280px,1fr) minmax(0,3fr) minmax(300px,1fr)}}@media(max-width:1439px){.contextGrid{grid-template-columns:repeat(4,minmax(180px,1fr))}.candidateGrid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(prefers-reduced-motion:reduce){.page *{transition:none!important}}
''')
Path("src/app/info").mkdir(parents=True, exist_ok=True)
Path("src/app/info/page.tsx").write_text('''import { AppShell } from "@/components/shell/AppShell";\nimport { InfoVisual } from "@/components/pages/InfoVisual";\n\nexport default function InfoPage(){\n  return <AppShell activeNavId="NAV-09"><InfoVisual /></AppShell>;\n}\n''')

checks = {
    info_path: ["global_l1: true", "navigation_mode: FRONT_L1", "navigation_id: NAV-09"],
    nav: ["count: 9", "nav_id: NAV-09", "FRONT-L1-09"],
    shell: ["count: 9", "nav_id: NAV-09", "GHS-CTL-NAV-09", "ALL NAV-01..NAV-09"],
    sys_path: ["l1_count: 9", "workspace:INFO-01"],
    pim: ["surface: FRONT_WORKSPACE", "navigation: FRONT_L1_NAV-09"],
    i18na: ["nav.latest_information:"],
}
for path, needles in checks.items():
    data = Path(path).read_text()
    for needle in needles:
        if needle not in data:
            raise SystemExit(f"{path} missing {needle}")
for path in [info_path, nav, shell, sys_path, pim]:
    data = Path(path).read_text()
    for forbidden in ["no ninth front L1", "Not a ninth front L1", "SUPPORTING_CONTEXTUAL_DEEP_LINK_NOT_FRONT_L1", "global_l1: false"]:
        if forbidden in data:
            raise SystemExit(f"{path} still contains contradiction: {forbidden}")
print(f"VIS-09 generated: controls={len(entries)} sections={len({e['section'] for e in entries})} components={len({e['component'] for e in entries})}")
