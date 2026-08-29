import type { Locale } from "./catalog";

type DbLabel = { tw: string; en: string };

const DB_LABELS: readonly [string, string, string][] = [
  ["DB-01-FLD-ENV", "Environment", "Environment"],
  ["DB-01-FLD-SCHEMA-HEAD", "Schema Head", "Schema Head"],
  ["DB-01-FLD-MIGRATION-HEAD", "Migration Head", "Migration Head"],
  ["DB-01-FLD-SCOPE", "Authorized Scope", "Authorized Scope"],
  ["DB-01-FLD-HEALTH", "Data Integrity", "Data Integrity"],
  ["DB-01-BTN-REFRESH", "重新整理", "Refresh"],
  ["DB-01-INP-SEARCH", "搜尋 Entity / Table", "Search Entity / Table"],
  ["DB-01-SEL-DOMAIN", "Domain", "Domain"],
  ["DB-01-SEL-ENTITY-TYPE", "Entity Type", "Entity Type"],
  ["DB-01-LIST-ENTITIES", "Entity / Table Explorer", "Entity / Table Explorer"],
  ["DB-01-FLD-ENTITY", "Entity / Aggregate", "Entity / Aggregate"],
  ["DB-01-FLD-TABLE", "Table", "Table"],
  ["DB-01-FLD-OWNER", "Owner Service", "Owner Service"],
  ["DB-01-FLD-CLASSIFICATION", "Data Classification", "Data Classification"],
  ["DB-01-FLD-PK", "Primary Key", "Primary Key"],
  ["DB-01-FLD-VERSION-RULE", "Version Rule", "Version Rule"],
  ["DB-01-TBL-COLUMNS", "Columns / Type / Nullable / Default", "Columns / Type / Nullable / Default"],
  ["DB-01-TBL-CONSTRAINTS", "Constraints / Indexes", "Constraints / Indexes"],
  ["DB-01-BTN-SCHEMA-REFRESH", "重新讀取 Schema", "Reload Schema"],
  ["DB-01-TOGGLE-RELATION-VIEW", "Graph / List", "Graph / List"],
  ["DB-01-GRAPH-RELATIONS", "Exact Relation Graph", "Exact Relation Graph"],
  ["DB-01-LIST-RELATIONS", "Relation List", "Relation List"],
  ["DB-01-SEL-TRACE-TYPE", "Trace Source Type", "Trace Source Type"],
  ["DB-01-INP-TRACE-ID", "Exact Source ID / Version", "Exact Source ID / Version"],
  ["DB-01-BTN-TRACE", "追溯", "Trace"],
  ["DB-01-VIEW-TRACE-PATH", "Exact Lineage Path", "Exact Lineage Path"],
  ["DB-01-FLD-REF-INTEGRITY", "Reference Integrity", "Reference Integrity"],
  ["DB-01-FLD-ORPHAN", "Orphan Status", "Orphan Status"],
  ["DB-01-FLD-IMMUTABLE", "Version Immutability", "Version Immutability"],
  ["DB-01-FLD-TRACE-COMPLETE", "Trace Completeness", "Trace Completeness"],
  ["DB-01-FLD-MIGRATION-INTEGRITY", "Migration / Checksum", "Migration / Checksum"],
  ["DB-01-BTN-INTEGRITY-REFRESH", "重新整理完整性", "Refresh Integrity"],
  ["DB-01-INP-MIGRATION-SEARCH", "Migration ID", "Migration ID"],
  ["DB-01-TBL-MIGRATIONS", "Migration History", "Migration History"],
  ["DB-01-BTN-MIGRATION-REFRESH", "重新整理 Migration", "Refresh Migration"],
  ["DB-01-SEL-FINDING-TYPE", "Integrity Finding Type", "Integrity Finding Type"],
  ["DB-01-LIST-FINDINGS", "Integrity Findings", "Integrity Findings"],
  ["DB-01-FLD-FINDING-REASON", "Reason", "Reason"],
  ["DB-01-FLD-FINDING-AFFECTED", "Affected Exact Refs", "Affected Exact Refs"],
  ["DB-01-FLD-FINDING-EVIDENCE", "Evidence", "Evidence"],
  ["DB-01-FLD-FINDING-OWNER", "Owner / Repair Route", "Owner / Repair Route"],
  ["DB-01-INP-AUDIT-ID", "Correlation / Entity / Version Ref", "Correlation / Entity / Version Ref"],
  ["DB-01-BTN-AUDIT", "查看 Audit Trace", "View Audit Trace"],
  ["DB-01-VIEW-AUDIT", "Audit / Correlation", "Audit / Correlation"],
  ["DB-01-FLD-PAGE-STATE", "Page State", "Page State"],
  ["DB-01-FLD-SOURCE-SYNC", "Source / Last Sync", "Source / Last Sync"],
  ["DB-01-FLD-DISABLED", "Disabled Reason", "Disabled Reason"],
  ["DB-01-FLD-CHANGE-OWNER", "Schema Change Owner", "Schema Change Owner"],
  ["DB-01-BTN-SYSTEM-LIFECYCLE", "開啟 System Lifecycle / Change Management", "Open System Lifecycle / Change Management"],
] as const;

export const DB_CONTROL_TEXT: Record<string, DbLabel> = Object.fromEntries(DB_LABELS.map(([id, tw, en]) => [id, { tw, en }]));
const REPLACEMENTS: readonly [string, string][] = [["重新整理","重新整理"],["搜尋","搜索"],["讀取","读取"],["追溯","追溯"],["完整性","完整性"],["查看","查看"],["開啟","开启"]];
function toSimplified(input: string) { return REPLACEMENTS.reduce((v,[a,b]) => v.split(a).join(b), input); }
export function dbText(locale: Locale, id: string) { const e=DB_CONTROL_TEXT[id]; if(!e) return id; if(locale==="en") return e.en; if(locale==="zh-CN") return toSimplified(e.tw); return e.tw; }

export const DB_UI_TEXT = {
  explorer:{"zh-TW":"Entity Explorer","zh-CN":"Entity Explorer",en:"Entity Explorer"},
  schema:{"zh-TW":"Schema Inspector","zh-CN":"Schema Inspector",en:"Schema Inspector"},
  relations:{"zh-TW":"Relation Graph","zh-CN":"Relation Graph",en:"Relation Graph"},
  integrity:{"zh-TW":"Integrity / Version Summary","zh-CN":"Integrity / Version Summary",en:"Integrity / Version Summary"},
  trace:{"zh-TW":"Traceability Path","zh-CN":"Traceability Path",en:"Traceability Path"},
  migration:{"zh-TW":"Migration History","zh-CN":"Migration History",en:"Migration History"},
  findings:{"zh-TW":"Integrity Findings","zh-CN":"Integrity Findings",en:"Integrity Findings"},
  audit:{"zh-TW":"Audit / Correlation","zh-CN":"Audit / Correlation",en:"Audit / Correlation"},
  status:{"zh-TW":"Status / Boundary","zh-CN":"Status / Boundary",en:"Status / Boundary"},
  readOnly:{"zh-TW":"DB-01 為唯讀資料模型與追溯工作區；不提供 SQL、Row Editor、DDL 或 Migration 執行。","zh-CN":"DB-01 为只读数据模型与追溯工作区；不提供 SQL、Row Editor、DDL 或 Migration 执行。",en:"DB-01 is a read-only data model and traceability workspace. No SQL, row editor, DDL, or migration execution is exposed."}
} as const;
export type DbUiTextKey=keyof typeof DB_UI_TEXT;
export function dbUiText(locale:Locale,key:DbUiTextKey){return DB_UI_TEXT[key][locale];}
