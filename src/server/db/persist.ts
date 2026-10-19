import { seedScope } from "./seed";
import { pagePermissionEnforced } from "../auth/pageAccess";
import { applyWorkbenchAction } from "../runtime/applyAction";
import { fillProtocolNotes, refreshPublishedNotes, type AiapiOutcome } from "../aiapi/runtime";
import { resolveAssetInbound } from "@/lib/assetInbound";
import { resolveEditInbound, effectiveVideoCurrent } from "@/lib/editInbound";
import { resolveVideoInbound } from "@/lib/videoInbound";
import { exactName, namedList } from "@/lib/coreActionPreview";
import { ASSET_CORRECTION_RESPONSE_UID, VIDEO_CORRECTION_RESPONSE_UID } from "@/lib/aiReply";
import { AIAPI_REGISTRY_UID, readProfiles, serializeProfiles } from "@/lib/aiapiProfiles";
import { AIAPI_EXTRA_PROJECTION_KEYS } from "@/lib/aiapiActionPreview";
import { projectDashboardFromCore } from "@/lib/dashboardProjection";
import { DASHBOARD_CHAIN, DASHBOARD_PAGE_UID, DASHBOARD_PERMISSION, DASHBOARD_PROJECTION, DASHBOARD_ROUTE, DASHBOARD_SECTION_SEEDS } from "../domain/dashboard";
import {
  CORE_CHAIN,
  CORE_CONTROL_ACTIONS,
  CORE_PAGE_UID,
  CORE_PERMISSION,
  CORE_PROJECTION,
  CORE_ROUTE,
  CORE_VISIBLE_CONTROLS,
} from "../domain/core";
import {
  ASSET_CHAIN,
  ASSET_CONTROL_ACTIONS,
  ASSET_PAGE_UID,
  ASSET_PERMISSION,
  ASSET_PROJECTION,
  ASSET_ROUTE,
  ASSET_VISIBLE_CONTROLS,
} from "../domain/asset";
import {
  VIDEO_CHAIN,
  VIDEO_CONTROL_ACTIONS,
  VIDEO_PAGE_UID,
  VIDEO_PERMISSION,
  VIDEO_PROJECTION,
  VIDEO_ROUTE,
  VIDEO_VISIBLE_CONTROLS,
} from "../domain/video";
import {
  EDIT_CHAIN,
  EDIT_CONTROL_ACTIONS,
  EDIT_PAGE_UID,
  EDIT_PERMISSION,
  EDIT_PROJECTION,
  EDIT_ROUTE,
  EDIT_VISIBLE_CONTROLS,
} from "../domain/edit";
import {
  QA_CHAIN,
  QA_CONTROL_ACTIONS,
  QA_PAGE_UID,
  QA_PERMISSION,
  QA_PROJECTION,
  QA_ROUTE,
  QA_VISIBLE_CONTROLS,
} from "../domain/qa";
import {
  DB_CHAIN,
  DB_CONTROL_ACTIONS,
  DB_PAGE_UID,
  DB_PERMISSION,
  DB_PROJECTION,
  DB_ROUTE,
  DB_VISIBLE_CONTROLS,
} from "../domain/db";
import {
  STR_CHAIN,
  STR_CONTROL_ACTIONS,
  STR_PAGE_UID,
  STR_PERMISSION,
  STR_PROJECTION,
  STR_ROUTE,
  STR_VISIBLE_CONTROLS,
} from "../domain/str";
import {
  INFO_CHAIN,
  INFO_CONTROL_ACTIONS,
  INFO_PAGE_UID,
  INFO_PERMISSION,
  INFO_PROJECTION,
  INFO_ROUTE,
  INFO_VISIBLE_CONTROLS,
} from "../domain/info";
import {
  SYS_CHAIN,
  SYS_CONTROL_ACTIONS,
  SYS_PAGE_UID,
  SYS_PERMISSION,
  SYS_PROJECTION,
  SYS_ROUTE,
  SYS_VISIBLE_CONTROLS,
} from "../domain/sys";
import {
  IAM_CHAIN,
  IAM_CONTROL_ACTIONS,
  IAM_PAGE_UID,
  IAM_PERMISSION,
  IAM_PROJECTION,
  IAM_ROUTE,
  IAM_VISIBLE_CONTROLS,
} from "../domain/iam";
import {
  DEV_CHAIN,
  DEV_CONTROL_ACTIONS,
  DEV_PAGE_UID,
  DEV_PERMISSION,
  DEV_PROJECTION,
  DEV_ROUTE,
  DEV_VISIBLE_CONTROLS,
} from "../domain/dev";
import {
  SOC_CHAIN,
  SOC_CONTROL_ACTIONS,
  SOC_PAGE_UID,
  SOC_PERMISSION,
  SOC_PROJECTION,
  SOC_ROUTE,
  SOC_VISIBLE_CONTROLS,
} from "../domain/soc";
import {
  ERP_CHAIN,
  ERP_CONTROL_ACTIONS,
  ERP_PAGE_UID,
  ERP_PERMISSION,
  ERP_PROJECTION,
  ERP_ROUTE,
  ERP_VISIBLE_CONTROLS,
} from "../domain/erp";
import {
  AIAPI_CHAIN,
  AIAPI_CONTROL_ACTIONS,
  AIAPI_PAGE_UID,
  AIAPI_PERMISSION,
  AIAPI_PROJECTION,
  AIAPI_ROUTE,
  AIAPI_VISIBLE_CONTROLS,
} from "../domain/aiapi";
import {
  SG02_CHAIN,
  SG02_CONTROL_ACTIONS,
  SG02_PAGE_UID,
  SG02_PERMISSION,
  SG02_PROJECTION,
  SG02_ROUTE,
  SG02_VISIBLE_CONTROLS,
} from "../domain/sg02";
import {
  ADMIN_STR_CHAIN,
  ADMIN_STR_CONTROL_ACTIONS,
  ADMIN_STR_PAGE_UID,
  ADMIN_STR_PERMISSION,
  ADMIN_STR_PROJECTION,
  ADMIN_STR_ROUTE,
  ADMIN_STR_VISIBLE_CONTROLS,
} from "../domain/adminStr";
import {
  KB_CHAIN,
  KB_CONTROL_ACTIONS,
  KB_PAGE_UID,
  KB_PERMISSION,
  KB_PROJECTION,
  KB_ROUTE,
  KB_VISIBLE_CONTROLS,
} from "../domain/kb";
import { getSqlClient } from "./client";
import type {
  AssetFieldValue,
  AssetReadModel,
  CanonicalNavigationItem,
  CoreFieldValue,
  CoreReadModel,
  DashboardReadModel,
  DashboardSectionValue,
  DbFieldValue,
  DbReadModel,
  EditFieldValue,
  EditReadModel,
  NavigationEvent,
  PermissionAssignment,
  QaFieldValue,
  QaReadModel,
  InfoFieldValue,
  InfoReadModel,
  StrFieldValue,
  StrReadModel,
  SysFieldValue,
  SysReadModel,
  IamFieldValue,
  IamReadModel,
  DevFieldValue,
  DevReadModel,
  SocFieldValue,
  SocReadModel,
  ErpFieldValue,
  ErpReadModel,
  AiapiFieldValue,
  AiapiReadModel,
  Sg02FieldValue,
  Sg02ReadModel,
  AdminStrFieldValue,
  AdminStrReadModel,
  KbFieldValue,
  KbReadModel,
  VideoFieldValue,
  VideoReadModel,
} from "../domain/types";

interface AuthorityRow {
  navigation_uid: string;
  area: "FRONT" | "ADMIN";
  label_key: string;
  route: string;
  display_order: number;
  icon: string;
  aria_label_key: string;
}

interface AssignmentRow {
  navigation_uid: string;
}

interface AuditRow {
  event_uid: string;
  account_uid: string;
  area: "FRONT" | "ADMIN";
  navigation_uid: string;
  route: string;
  occurred_at: string;
}

interface SessionRow {
  session_uid: string;
  account_uid: string;
}

function toItem(row: AuthorityRow): CanonicalNavigationItem {
  return {
    uid: row.navigation_uid,
    area: row.area,
    labelKey: row.label_key,
    route: row.route,
    order: Number(row.display_order),
    icon: row.icon,
    ariaLabelKey: row.aria_label_key,
  };
}

export async function persistListItems(): Promise<CanonicalNavigationItem[]> {
  await seedScope("navigation");
  const rows = await getSqlClient().all<AuthorityRow>(
    "SELECT navigation_uid, area, label_key, route, display_order, icon, aria_label_key FROM ghsn_navigation_authority ORDER BY area, display_order",
  );
  return rows.map(toItem);
}

export async function persistGetItem(uid: string): Promise<CanonicalNavigationItem | undefined> {
  await seedScope("navigation");
  const rows = await getSqlClient().all<AuthorityRow>(
    "SELECT navigation_uid, area, label_key, route, display_order, icon, aria_label_key FROM ghsn_navigation_authority WHERE navigation_uid = ?",
    [uid],
  );
  return rows[0] ? toItem(rows[0]) : undefined;
}

export async function persistGetAssignment(accountUid: string): Promise<PermissionAssignment | undefined> {
  await seedScope("navigation");
  const rows = await getSqlClient().all<AssignmentRow>(
    "SELECT navigation_uid FROM ghsn_account_permission_assignment WHERE account_uid = ?",
    [accountUid],
  );
  if (rows.length === 0) return undefined;
  return {
    accountUid,
    grantedNavigationUids: rows.map((row) => row.navigation_uid),
  };
}

export async function persistRecordAuditEvent(event: NavigationEvent): Promise<NavigationEvent> {
  await getSqlClient().run(
    `INSERT INTO ghsn_navigation_audit_event (event_uid, account_uid, area, navigation_uid, route, occurred_at)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [event.eventUid, event.accountUid, event.area, event.itemUid, event.route, event.occurredAt],
  );
  return event;
}

export async function persistFindSession(sessionUid: string): Promise<SessionRow | undefined> {
  await seedScope("identity");
  const rows = await getSqlClient().all<SessionRow>(
    "SELECT session_uid, account_uid FROM ghsn_account_session WHERE session_uid = ?",
    [sessionUid],
  );
  return rows[0];
}

interface DashboardSectionRow {
  section_uid: string;
  control_uid: string;
  value_text: string | null;
  detail_text: string;
}

export async function persistHasDashboardPermission(accountUid: string): Promise<boolean> {
  await seedScope("dashboard");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_dashboard_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, DASHBOARD_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListDashboardSections(): Promise<DashboardSectionValue[]> {
  await seedScope("core");
  const fields = await persistListCoreFields();
  const byUid = new Map(fields.map((row) => [row.controlUid, row.value]));
  const live = projectDashboardFromCore((uid) => byUid.get(uid) ?? null);
  if (live.length > 0) return live;
  const rows = await getSqlClient().all<DashboardSectionRow>(
    "SELECT section_uid, control_uid, value_text, detail_text FROM ghsn_dashboard_section_projection",
  );
  return DASHBOARD_SECTION_SEEDS.map((seed) => {
    const row = rows.find((item) => item.section_uid === seed.sectionUid);
    return {
      sectionUid: seed.sectionUid,
      controlUid: seed.controlUid,
      value: row?.value_text === "" ? null : (row?.value_text ?? null),
      detail: row?.detail_text ?? "",
    };
  });
}

export async function persistGetDashboardReadModel(accountUid: string): Promise<DashboardReadModel> {
  const authorized = await persistHasDashboardPermission(accountUid);
  const sections = authorized ? await persistListDashboardSections() : [];
  return {
    projectionUid: DASHBOARD_PROJECTION,
    pageUid: DASHBOARD_PAGE_UID,
    route: DASHBOARD_ROUTE,
    permission: DASHBOARD_PERMISSION,
    chainUid: DASHBOARD_CHAIN,
    authorized,
    sections,
  };
}

export async function persistRecordSectionOpen(
  accountUid: string,
  sectionUid: string,
  controlUid: string,
): Promise<string> {
  await applyWorkbenchAction("dashboard", sectionUid, "SECTION_OPEN");
  const eventUid = `EVT-SECTION-OPEN-${Date.now()}-${sectionUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_dashboard_audit_event (event_uid, account_uid, section_uid, control_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, sectionUid, controlUid, new Date().toISOString()],
  );
  return eventUid;
}

interface CoreFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasCorePermission(accountUid: string): Promise<boolean> {
  await seedScope("core");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_core_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, CORE_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListCoreFields(): Promise<CoreFieldValue[]> {
  const rows = await getSqlClient().all<CoreFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_core_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return CORE_VISIBLE_CONTROLS.map((controlUid) => {
    const raw = byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null;
    if (controlUid === "CORE-01-CTL-TOPIC" || controlUid === "CORE-01-FLD-TOPIC-SCOPE") {
      return { controlUid, value: exactName(raw) || null };
    }
    if (controlUid === "CORE-01-BTN-TOPIC-CREATE") {
      return { controlUid, value: JSON.stringify(namedList(raw)) };
    }
    return { controlUid, value: raw };
  });
}

export async function persistGetCoreReadModel(accountUid: string): Promise<CoreReadModel> {
  const authorized = await persistHasCorePermission(accountUid);
  const fields = authorized ? await persistListCoreFields() : [];
  const byUid = new Map(fields.map((row) => [row.controlUid, row.value]));
  const project = namedCoreValue(byUid.get("CORE-01-CTL-PROJECT"));
  const topic = namedCoreValue(byUid.get("CORE-01-CTL-TOPIC"));
  const confirmed =
    byUid.get("CORE-01-BTN-PROJECT-CONFIRM") === "confirmed" ||
    byUid.get("CORE-01-BTN-PROJECT-LOCK") === project;
  const pageMode = project && confirmed && topic ? "TOPIC_PRODUCTION" : project ? "PROJECT_CORE" : null;
  return {
    projectionUid: CORE_PROJECTION,
    pageUid: CORE_PAGE_UID,
    route: CORE_ROUTE,
    permission: CORE_PERMISSION,
    chainUid: CORE_CHAIN,
    authorized,
    pageMode,
    fields,
  };
}

export function knownCoreAction(controlUid: string, actionUid: string): boolean {
  return CORE_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordCoreAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<string> {
  await applyWorkbenchAction("core", controlUid, actionUid, nextValue);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_core_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface AssetFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasAssetPermission(accountUid: string): Promise<boolean> {
  await seedScope("asset");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_asset_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, ASSET_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListAssetFields(): Promise<AssetFieldValue[]> {
  const rows = await getSqlClient().all<AssetFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_asset_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return [...ASSET_VISIBLE_CONTROLS, ASSET_CORRECTION_RESPONSE_UID].map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

function namedCoreValue(value: string | null | undefined): string {
  return exactName(value);
}

function overlayCoreNames(fields: AssetFieldValue[], coreFields: CoreFieldValue[]): AssetFieldValue[] {
  const core = new Map(coreFields.map((row) => [row.controlUid, row.value]));
  const inbound = resolveAssetInbound((uid) => core.get(uid) ?? null);
  if (!inbound.ready) {
    return fields.map((row) => ({ ...row, value: null }));
  }
  return fields.map((row) => {
    if (row.controlUid === "ASSET-01-CTL-PROJECT") return { ...row, value: inbound.project };
    if (row.controlUid === "ASSET-01-CTL-TOPIC") return { ...row, value: inbound.topic };
    if (row.controlUid === "ASSET-01-FLD-TASK") return { ...row, value: inbound.task };
    if (row.controlUid === "ASSET-01-FLD-BLUEPRINT") return { ...row, value: inbound.blueprint };
    if (row.controlUid === "ASSET-01-FLD-DNA") return { ...row, value: inbound.dna };
    if (row.controlUid === "ASSET-01-FLD-SCRIPT") return { ...row, value: inbound.script };
    if (row.controlUid === "ASSET-01-FLD-NAMING-AUTHORITY") return { ...row, value: inbound.naming };
    return row;
  });
}

export async function persistGetAssetReadModel(accountUid: string): Promise<AssetReadModel> {
  const authorized = await persistHasAssetPermission(accountUid);
  const fields = authorized
    ? overlayCoreNames(
        await persistListAssetFields(),
        await persistListCoreFields().catch(() => [] as CoreFieldValue[]),
      )
    : [];
  return {
    projectionUid: ASSET_PROJECTION,
    pageUid: ASSET_PAGE_UID,
    route: ASSET_ROUTE,
    permission: ASSET_PERMISSION,
    chainUid: ASSET_CHAIN,
    authorized,
    fields,
  };
}

export function knownAssetAction(controlUid: string, actionUid: string): boolean {
  return ASSET_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordAssetAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<string> {
  await applyWorkbenchAction("asset", controlUid, actionUid, nextValue);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_asset_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface VideoFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasVideoPermission(accountUid: string): Promise<boolean> {
  await seedScope("video");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_video_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, VIDEO_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListVideoFields(): Promise<VideoFieldValue[]> {
  const rows = await getSqlClient().all<VideoFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_video_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return [...VIDEO_VISIBLE_CONTROLS, VIDEO_CORRECTION_RESPONSE_UID].map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

function overlayUpstreamOntoVideo(
  fields: VideoFieldValue[],
  coreFields: CoreFieldValue[],
  assetFields: AssetFieldValue[],
): VideoFieldValue[] {
  const core = new Map(coreFields.map((row) => [row.controlUid, row.value]));
  const asset = new Map(assetFields.map((row) => [row.controlUid, row.value]));
  const inbound = resolveVideoInbound((uid) => core.get(uid) ?? null, (uid) => asset.get(uid) ?? null);
  const bound = [inbound.filename, inbound.checksum].filter(Boolean).join(" / ");
  return fields.map((row) => {
    if (row.controlUid === "VIDEO-01-FLD-PROJECT") return { ...row, value: inbound.ready ? inbound.project || null : null };
    if (row.controlUid === "VIDEO-01-FLD-TOPIC") return { ...row, value: inbound.ready ? inbound.topic || null : null };
    if (row.controlUid === "VIDEO-01-FLD-TASK") return { ...row, value: inbound.ready ? inbound.task || null : null };
    if (row.controlUid === "VIDEO-01-FLD-STATUS") return { ...row, value: inbound.ready ? row.value : null };
    if (row.controlUid === "VIDEO-01-FLD-BLUEPRINT-REF") return { ...row, value: inbound.ready ? inbound.blueprint || null : null };
    if (row.controlUid === "VIDEO-01-FLD-DNA-REFS") return { ...row, value: inbound.ready ? inbound.dna || null : null };
    if (row.controlUid === "VIDEO-01-FLD-SCRIPT-SECTION") return { ...row, value: inbound.ready ? inbound.script || null : null };
    if (row.controlUid === "VIDEO-01-FLD-ASSET-REFS") return { ...row, value: inbound.ready ? inbound.assetVersion || null : null };
    if (row.controlUid === "VIDEO-01-FLD-FILENAME-CHECKSUM") return { ...row, value: inbound.ready ? bound || null : null };
    if (row.controlUid === "VIDEO-01-FLD-RIGHTS") return { ...row, value: inbound.ready ? inbound.rights || null : null };
    if (row.controlUid === "VIDEO-01-FLD-INSTRUCTION") return { ...row, value: inbound.ready ? inbound.instruction || null : null };
    return row;
  });
}

export async function persistGetVideoReadModel(accountUid: string): Promise<VideoReadModel> {
  const authorized = await persistHasVideoPermission(accountUid);
  const fields = authorized
    ? overlayUpstreamOntoVideo(
        await persistListVideoFields(),
        await persistListCoreFields().catch(() => [] as CoreFieldValue[]),
        await persistListAssetFields().catch(() => [] as AssetFieldValue[]),
      )
    : [];
  return {
    projectionUid: VIDEO_PROJECTION,
    pageUid: VIDEO_PAGE_UID,
    route: VIDEO_ROUTE,
    permission: VIDEO_PERMISSION,
    chainUid: VIDEO_CHAIN,
    authorized,
    fields,
  };
}

export function knownVideoAction(controlUid: string, actionUid: string): boolean {
  return VIDEO_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordVideoAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<string> {
  await applyWorkbenchAction("video", controlUid, actionUid, nextValue);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_video_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface EditFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasEditPermission(accountUid: string): Promise<boolean> {
  await seedScope("edit");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_edit_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, EDIT_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListEditFields(): Promise<EditFieldValue[]> {
  const rows = await getSqlClient().all<EditFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_edit_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return EDIT_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

function overlayUpstreamOntoEdit(
  fields: EditFieldValue[],
  coreFields: CoreFieldValue[],
  assetFields: AssetFieldValue[],
  videoFields: VideoFieldValue[],
): EditFieldValue[] {
  const core = new Map(coreFields.map((row) => [row.controlUid, row.value]));
  const asset = new Map(assetFields.map((row) => [row.controlUid, row.value]));
  const video = new Map(videoFields.map((row) => [row.controlUid, row.value]));
  const edit = new Map(fields.map((row) => [row.controlUid, row.value]));
  const coreCurrent = (uid: string) => core.get(uid) ?? null;
  const inbound = resolveEditInbound(
    effectiveVideoCurrent(coreCurrent, (uid) => asset.get(uid) ?? null, (uid) => video.get(uid) ?? null),
    coreCurrent,
    (uid) => edit.get(uid) ?? null,
  );
  const pageReady = inbound.ready || inbound.standalone;
  const STAGE_FIELDS = new Set([
    "EDIT-01-LBL-PAGE-STATE",
    "EDIT-01-LBL-PENDING-TASK",
    "EDIT-01-LBL-STAGE-SCORE",
    "EDIT-01-LBL-EVAL-SUMMARY",
    "EDIT-01-LBL-RENDER-JOB",
    "EDIT-01-LBL-ERROR-STATE",
    "EDIT-01-BTN-FLOW-START",
    "EDIT-01-BTN-STAGE-CONFIRM",
    "EDIT-01-BTN-VERSION-SAVE",
    "EDIT-01-BTN-VERSION-LOCK",
    "EDIT-01-BTN-RENDER-EXECUTE",
    "EDIT-01-BTN-OUTPUT-SAVE",
    "EDIT-01-BTN-HANDOFF-2",
  ]);
  return fields.map((row) => {
    if (row.controlUid === "EDIT-01-FLD-PROJECT") return { ...row, value: inbound.ready ? inbound.project || null : null };
    if (row.controlUid === "EDIT-01-FLD-TOPIC") return { ...row, value: inbound.ready ? inbound.topic || null : null };
    if (row.controlUid === "EDIT-01-FLD-TASK") return { ...row, value: inbound.ready ? inbound.task || null : null };
    if (row.controlUid === "EDIT-01-FLD-SOURCE-VERSION") return { ...row, value: inbound.ready ? inbound.sourceVersion || null : null };
    if (row.controlUid === "EDIT-01-LBL-BINDING-FINGERPRINT") return { ...row, value: inbound.ready ? inbound.handoffContract || null : null };
    if (row.controlUid === "EDIT-01-LBL-CURRENT-SCRIPT-SECTION") return { ...row, value: inbound.ready ? inbound.script || null : null };
    if (STAGE_FIELDS.has(row.controlUid)) return { ...row, value: pageReady ? row.value : null };
    return row;
  });
}

export async function persistGetEditReadModel(accountUid: string): Promise<EditReadModel> {
  const authorized = await persistHasEditPermission(accountUid);
  const fields = authorized
    ? overlayUpstreamOntoEdit(
        await persistListEditFields(),
        await persistListCoreFields().catch(() => [] as CoreFieldValue[]),
        await persistListAssetFields().catch(() => [] as AssetFieldValue[]),
        await persistListVideoFields().catch(() => [] as VideoFieldValue[]),
      )
    : [];
  return {
    projectionUid: EDIT_PROJECTION,
    pageUid: EDIT_PAGE_UID,
    route: EDIT_ROUTE,
    permission: EDIT_PERMISSION,
    chainUid: EDIT_CHAIN,
    authorized,
    fields,
  };
}

export function knownEditAction(controlUid: string, actionUid: string): boolean {
  return EDIT_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordEditAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("edit", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_edit_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface QaFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasQaPermission(accountUid: string): Promise<boolean> {
  await seedScope("qa");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_qa_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, QA_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListQaFields(): Promise<QaFieldValue[]> {
  const rows = await getSqlClient().all<QaFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_qa_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return QA_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetQaReadModel(accountUid: string): Promise<QaReadModel> {
  const authorized = await persistHasQaPermission(accountUid);
  const fields = authorized ? await persistListQaFields() : [];
  return {
    projectionUid: QA_PROJECTION,
    pageUid: QA_PAGE_UID,
    route: QA_ROUTE,
    permission: QA_PERMISSION,
    chainUid: QA_CHAIN,
    authorized,
    fields,
  };
}

export function knownQaAction(controlUid: string, actionUid: string): boolean {
  return QA_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordQaAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("qa", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_qa_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface DbFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasDbPermission(accountUid: string): Promise<boolean> {
  await seedScope("db");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_db_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, DB_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListDbFields(): Promise<DbFieldValue[]> {
  const rows = await getSqlClient().all<DbFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_db_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return DB_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetDbReadModel(accountUid: string): Promise<DbReadModel> {
  const authorized = await persistHasDbPermission(accountUid);
  const fields = authorized ? await persistListDbFields() : [];
  return {
    projectionUid: DB_PROJECTION,
    pageUid: DB_PAGE_UID,
    route: DB_ROUTE,
    permission: DB_PERMISSION,
    chainUid: DB_CHAIN,
    authorized,
    fields,
  };
}

export function knownDbAction(controlUid: string, actionUid: string): boolean {
  return DB_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordDbAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("db", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_db_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface StrFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasStrPermission(accountUid: string): Promise<boolean> {
  await seedScope("str");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_str_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, STR_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListStrFields(): Promise<StrFieldValue[]> {
  const rows = await getSqlClient().all<StrFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_str_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return STR_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetStrReadModel(accountUid: string): Promise<StrReadModel> {
  const authorized = await persistHasStrPermission(accountUid);
  const fields = authorized ? await persistListStrFields() : [];
  return {
    projectionUid: STR_PROJECTION,
    pageUid: STR_PAGE_UID,
    route: STR_ROUTE,
    permission: STR_PERMISSION,
    chainUid: STR_CHAIN,
    authorized,
    fields,
  };
}

export function knownStrAction(controlUid: string, actionUid: string): boolean {
  return STR_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordStrAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("str", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_str_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface InfoFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasInfoPermission(accountUid: string): Promise<boolean> {
  await seedScope("info");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_info_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, INFO_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListInfoFields(): Promise<InfoFieldValue[]> {
  const rows = await getSqlClient().all<InfoFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_info_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return INFO_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetInfoReadModel(accountUid: string): Promise<InfoReadModel> {
  const authorized = await persistHasInfoPermission(accountUid);
  const fields = authorized ? await persistListInfoFields() : [];
  return {
    projectionUid: INFO_PROJECTION,
    pageUid: INFO_PAGE_UID,
    route: INFO_ROUTE,
    permission: INFO_PERMISSION,
    chainUid: INFO_CHAIN,
    authorized,
    fields,
  };
}

export function knownInfoAction(controlUid: string, actionUid: string): boolean {
  return INFO_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordInfoAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("info", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_info_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface SysFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasSysPermission(accountUid: string): Promise<boolean> {
  await seedScope("sys");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_sys_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, SYS_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListSysFields(): Promise<SysFieldValue[]> {
  const rows = await getSqlClient().all<SysFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_sys_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return SYS_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetSysReadModel(accountUid: string): Promise<SysReadModel> {
  const authorized = await persistHasSysPermission(accountUid);
  const fields = authorized ? await persistListSysFields() : [];
  return {
    projectionUid: SYS_PROJECTION,
    pageUid: SYS_PAGE_UID,
    route: SYS_ROUTE,
    permission: SYS_PERMISSION,
    chainUid: SYS_CHAIN,
    authorized,
    fields,
  };
}

export function knownSysAction(controlUid: string, actionUid: string): boolean {
  return SYS_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordSysAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("sys", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_sys_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface IamFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasIamPermission(accountUid: string): Promise<boolean> {
  await seedScope("iam");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_iam_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, IAM_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListIamFields(): Promise<IamFieldValue[]> {
  const rows = await getSqlClient().all<IamFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_iam_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return IAM_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetIamReadModel(accountUid: string): Promise<IamReadModel> {
  const authorized = await persistHasIamPermission(accountUid);
  const fields = authorized ? await persistListIamFields() : [];
  return {
    projectionUid: IAM_PROJECTION,
    pageUid: IAM_PAGE_UID,
    route: IAM_ROUTE,
    permission: IAM_PERMISSION,
    chainUid: IAM_CHAIN,
    authorized,
    fields,
  };
}

export function knownIamAction(controlUid: string, actionUid: string): boolean {
  return IAM_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordIamAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("iam", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_iam_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface DevFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasDevPermission(accountUid: string): Promise<boolean> {
  await seedScope("dev");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_dev_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, DEV_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListDevFields(): Promise<DevFieldValue[]> {
  const rows = await getSqlClient().all<DevFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_dev_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return DEV_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetDevReadModel(accountUid: string): Promise<DevReadModel> {
  const authorized = await persistHasDevPermission(accountUid);
  const fields = authorized ? await persistListDevFields() : [];
  return {
    projectionUid: DEV_PROJECTION,
    pageUid: DEV_PAGE_UID,
    route: DEV_ROUTE,
    permission: DEV_PERMISSION,
    chainUid: DEV_CHAIN,
    authorized,
    fields,
  };
}

export function knownDevAction(controlUid: string, actionUid: string): boolean {
  return DEV_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordDevAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("dev", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_dev_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface SocFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasSocPermission(accountUid: string): Promise<boolean> {
  await seedScope("soc");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_soc_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, SOC_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListSocFields(): Promise<SocFieldValue[]> {
  const rows = await getSqlClient().all<SocFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_soc_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return SOC_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetSocReadModel(accountUid: string): Promise<SocReadModel> {
  const authorized = await persistHasSocPermission(accountUid);
  const fields = authorized ? await persistListSocFields() : [];
  return {
    projectionUid: SOC_PROJECTION,
    pageUid: SOC_PAGE_UID,
    route: SOC_ROUTE,
    permission: SOC_PERMISSION,
    chainUid: SOC_CHAIN,
    authorized,
    fields,
  };
}

export function knownSocAction(controlUid: string, actionUid: string): boolean {
  return SOC_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordSocAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("soc", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_soc_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface ErpFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasErpPermission(accountUid: string): Promise<boolean> {
  await seedScope("erp");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_erp_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, ERP_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListErpFields(): Promise<ErpFieldValue[]> {
  const rows = await getSqlClient().all<ErpFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_erp_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return ERP_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetErpReadModel(accountUid: string): Promise<ErpReadModel> {
  const authorized = await persistHasErpPermission(accountUid);
  const fields = authorized ? await persistListErpFields() : [];
  return {
    projectionUid: ERP_PROJECTION,
    pageUid: ERP_PAGE_UID,
    route: ERP_ROUTE,
    permission: ERP_PERMISSION,
    chainUid: ERP_CHAIN,
    authorized,
    fields,
  };
}

export function knownErpAction(controlUid: string, actionUid: string): boolean {
  return ERP_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordErpAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("erp", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_erp_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface AiapiFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasAiapiPermission(accountUid: string): Promise<boolean> {
  await seedScope("aiapi");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_aiapi_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, AIAPI_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListAiapiFields(): Promise<AiapiFieldValue[]> {
  const rows = await getSqlClient().all<AiapiFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_aiapi_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  if (!byUid.get(AIAPI_REGISTRY_UID)) {
    const profiles = readProfiles((uid) => byUid.get(uid) ?? null);
    if (profiles.length) byUid.set(AIAPI_REGISTRY_UID, serializeProfiles(profiles));
  }
  const uids = new Set<string>([
    ...AIAPI_VISIBLE_CONTROLS,
    ...AIAPI_EXTRA_PROJECTION_KEYS,
    AIAPI_REGISTRY_UID,
    ...rows.map((row) => row.control_uid),
  ]);
  return [...uids].map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetAiapiReadModel(accountUid: string): Promise<AiapiReadModel> {
  const authorized = await persistHasAiapiPermission(accountUid);
  if (authorized) {
    await fillProtocolNotes();
    await refreshPublishedNotes();
  }
  const fields = authorized ? await persistListAiapiFields() : [];
  return {
    projectionUid: AIAPI_PROJECTION,
    pageUid: AIAPI_PAGE_UID,
    route: AIAPI_ROUTE,
    permission: AIAPI_PERMISSION,
    chainUid: AIAPI_CHAIN,
    authorized,
    fields,
  };
}

export function knownAiapiAction(controlUid: string, actionUid: string): boolean {
  return AIAPI_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordAiapiAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
  value?: string,
): Promise<{ eventUid: string; outcome: AiapiOutcome | null }> {
  const result = await applyWorkbenchAction("aiapi", controlUid, actionUid, value);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_aiapi_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return { eventUid, outcome: result ?? null };
}

interface Sg02FieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasSg02Permission(accountUid: string): Promise<boolean> {
  await seedScope("sg02");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_sg02_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, SG02_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListSg02Fields(): Promise<Sg02FieldValue[]> {
  const rows = await getSqlClient().all<Sg02FieldRow>(
    "SELECT control_uid, value_text FROM ghsn_sg02_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return SG02_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetSg02ReadModel(accountUid: string): Promise<Sg02ReadModel> {
  const authorized = await persistHasSg02Permission(accountUid);
  const fields = authorized ? await persistListSg02Fields() : [];
  return {
    projectionUid: SG02_PROJECTION,
    pageUid: SG02_PAGE_UID,
    route: SG02_ROUTE,
    permission: SG02_PERMISSION,
    chainUid: SG02_CHAIN,
    authorized,
    fields,
  };
}

export function knownSg02Action(controlUid: string, actionUid: string): boolean {
  return SG02_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordSg02Action(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("sg02", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_sg02_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface AdminStrFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasAdminStrPermission(accountUid: string): Promise<boolean> {
  await seedScope("adminStr");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_admin_str_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, ADMIN_STR_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListAdminStrFields(): Promise<AdminStrFieldValue[]> {
  const rows = await getSqlClient().all<AdminStrFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_admin_str_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return ADMIN_STR_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetAdminStrReadModel(accountUid: string): Promise<AdminStrReadModel> {
  const authorized = await persistHasAdminStrPermission(accountUid);
  const fields = authorized ? await persistListAdminStrFields() : [];
  return {
    projectionUid: ADMIN_STR_PROJECTION,
    pageUid: ADMIN_STR_PAGE_UID,
    route: ADMIN_STR_ROUTE,
    permission: ADMIN_STR_PERMISSION,
    chainUid: ADMIN_STR_CHAIN,
    authorized,
    fields,
  };
}

export function knownAdminStrAction(controlUid: string, actionUid: string): boolean {
  return ADMIN_STR_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordAdminStrAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("adminStr", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_admin_str_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

interface KbFieldRow {
  control_uid: string;
  value_text: string | null;
}

export async function persistHasKbPermission(accountUid: string): Promise<boolean> {
  await seedScope("kb");
  if (!pagePermissionEnforced()) return true;
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_kb_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, KB_PERMISSION],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

export async function persistListKbFields(): Promise<KbFieldValue[]> {
  const rows = await getSqlClient().all<KbFieldRow>(
    "SELECT control_uid, value_text FROM ghsn_kb_field_projection",
  );
  const byUid = new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text]));
  return KB_VISIBLE_CONTROLS.map((controlUid) => ({
    controlUid,
    value: byUid.has(controlUid) ? (byUid.get(controlUid) ?? null) : null,
  }));
}

export async function persistGetKbReadModel(accountUid: string): Promise<KbReadModel> {
  const authorized = await persistHasKbPermission(accountUid);
  const fields = authorized ? await persistListKbFields() : [];
  return {
    projectionUid: KB_PROJECTION,
    pageUid: KB_PAGE_UID,
    route: KB_ROUTE,
    permission: KB_PERMISSION,
    chainUid: KB_CHAIN,
    authorized,
    fields,
  };
}

export function knownKbAction(controlUid: string, actionUid: string): boolean {
  return KB_CONTROL_ACTIONS[controlUid] === actionUid;
}

export async function persistRecordKbAction(
  accountUid: string,
  controlUid: string,
  actionUid: string,
): Promise<string> {
  await applyWorkbenchAction("kb", controlUid, actionUid);
  const eventUid = `EVT-PAGE-ACTION-${Date.now()}-${controlUid}`;
  await getSqlClient().run(
    `INSERT INTO ghsn_kb_audit_event (event_uid, account_uid, control_uid, action_uid, occurred_at)
     VALUES (?, ?, ?, ?, ?)`,
    [eventUid, accountUid, controlUid, actionUid, new Date().toISOString()],
  );
  return eventUid;
}

export interface RuntimeAccountRow {
  account_uid: string;
  email: string;
  password_hash: string;
  status: string;
  disabled_at: string | null;
}

export interface AppUserRow {
  user_uid: string;
  email: string;
  display_name: string;
  account_uid: string;
  disabled_at: string | null;
}

export interface IdentitySessionRow {
  session_uid: string;
  account_uid: string;
  token_hash: string;
  expires_at: string;
  issued_at: string;
}

export async function persistFindRuntimeAccountByEmail(email: string): Promise<RuntimeAccountRow | undefined> {
  const rows = await getSqlClient().all<RuntimeAccountRow>(
    "SELECT account_uid, email, password_hash, status, disabled_at FROM ghsn_runtime_account WHERE lower(email) = lower(?)",
    [email],
  );
  return rows[0];
}

export async function persistFindAppUserByEmail(email: string): Promise<AppUserRow | undefined> {
  const rows = await getSqlClient().all<AppUserRow>(
    "SELECT user_uid, email, display_name, account_uid, disabled_at FROM ghsn_app_user WHERE lower(email) = lower(?)",
    [email],
  );
  return rows[0];
}

export async function persistCreateIdentitySession(row: IdentitySessionRow): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ghsn_identity_session (session_uid, account_uid, token_hash, expires_at, issued_at)
     VALUES (?, ?, ?, ?, ?)`,
    [row.session_uid, row.account_uid, row.token_hash, row.expires_at, row.issued_at],
  );
  await getSqlClient().run(
    `INSERT INTO ghsn_account_session (session_uid, account_uid, issued_at)
     VALUES (?, ?, ?)
     ON CONFLICT (session_uid) DO UPDATE SET account_uid = EXCLUDED.account_uid, issued_at = EXCLUDED.issued_at`,
    [row.session_uid, row.account_uid, row.issued_at],
  );
}

export async function persistFindIdentitySessionByTokenHash(tokenHash: string): Promise<IdentitySessionRow | undefined> {
  const rows = await getSqlClient().all<IdentitySessionRow>(
    "SELECT session_uid, account_uid, token_hash, expires_at, issued_at FROM ghsn_identity_session WHERE token_hash = ?",
    [tokenHash],
  );
  return rows[0];
}

export async function persistDeleteIdentitySession(sessionUid: string): Promise<void> {
  await getSqlClient().run("DELETE FROM ghsn_identity_session WHERE session_uid = ?", [sessionUid]);
  await getSqlClient().run("DELETE FROM ghsn_account_session WHERE session_uid = ?", [sessionUid]);
}
