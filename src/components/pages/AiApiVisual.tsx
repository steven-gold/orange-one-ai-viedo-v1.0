"use client";

import { useEffect, useMemo, useState } from "react";
import {
  invokeAiApiCommand,
  type AiApiClientOperation,
  type AiApiCommandRefs,
} from "@/domain/aiApi/aiApiCommandPort";
import {
  readAiApiProjection,
  type AiApiProjection,
  type AiApiProviderRow,
} from "@/domain/aiApi/aiApiRuntimePort";
import { useI18n } from "@/i18n/LocaleProvider";
import { AIAPI_PRO_FIELDS, aiApiProLabel, aiApiText } from "@/i18n/aiApiCatalog";
import styles from "./AiApiVisual.module.css";

type ViewKey = "overview" | "provider" | "routing" | "operations";
type FieldKind = "text" | "number" | "textarea" | "select";
type FieldDef = {
  key: string;
  label: string;
  kind?: FieldKind;
  required?: boolean;
  options?: readonly string[];
};
type ActionDef = {
  label: string;
  operation: AiApiClientOperation;
  requiresProfile?: boolean;
  fields?: readonly FieldDef[];
  confirmationOnly?: boolean;
  prefillProfile?: boolean;
};

const CAPABILITIES = [
  "TEXT_CHAT","TEXT_TO_IMAGE","IMAGE_EDIT","TEXT_TO_VIDEO",
  "VIDEO_EDIT","TEXT_TO_VOICE","VOICE_TO_VOICE","EMBEDDING","OTHER",
] as const;

const VIEWS = [
  { key: "overview" as const, uid: "AIAPI-01-VIEW-OVERVIEW", label: "overview" as const },
  { key: "provider" as const, uid: "AIAPI-01-VIEW-PROVIDER-API", label: "provider" as const },
  { key: "routing" as const, uid: "AIAPI-01-VIEW-ROUTING-TEST", label: "routing" as const },
  { key: "operations" as const, uid: "AIAPI-01-VIEW-OPERATIONS", label: "operations" as const },
] as const;

const OVERVIEW_GROUPS = ["Provider summary", "Route summary", "Capability summary", "Job summary", "Cost summary", "Health summary", "Incident summary"] as const;
const ROUTING_GROUPS = ["Candidate Group", "Fallback / limits", "Preflight", "Instruction Compile Audit", "Sandbox", "Route Simulation", "Route Decision", "Quarantine / restore"] as const;
const OPERATIONS_GROUPS = ["Job", "Attempt", "Callback", "Artifact", "Cost", "Budget", "Degradation", "Incident", "Fallback Decision", "Kill Switch"] as const;
const PROVIDER_COLUMNS = ["Provider", "Model", "Capability", "Adapter", "Base URL", "Endpoint", "Timeout", "Enabled", "Credential Status", "Last Test", "Actions"] as const;

const PROFILE_FIELDS: readonly FieldDef[] = [
  { key: "provider_id", label: "Provider ID", required: true },
  { key: "model_id", label: "Model ID", required: true },
  { key: "capability_type", label: "Capability", kind: "select", required: true, options: CAPABILITIES },
  { key: "adapter_type", label: "Adapter", kind: "select", required: true, options: ["OPENAI_COMPATIBLE_CHAT","GENERIC_JSON_HTTP"] },
  { key: "base_url", label: "Base URL (HTTPS)", required: true },
  { key: "endpoint_path", label: "Endpoint Path", required: true },
  { key: "http_method", label: "HTTP Method", kind: "select", required: true, options: ["POST","GET"] },
  { key: "secret_env_ref", label: "Secret Env Reference", required: true },
  { key: "timeout_seconds", label: "Timeout Seconds", kind: "number", required: true },
  { key: "prompt_template", label: "Prompt Template", kind: "textarea", required: true },
  { key: "request_template_json", label: "Request Template JSON", kind: "textarea" },
  { key: "response_text_path", label: "Response Text Path", required: true },
  { key: "preferred_language", label: "Preferred Language" },
  { key: "max_context", label: "Max Context", kind: "number" },
  { key: "enabled", label: "Enabled", kind: "select", required: true, options: ["false","true"] },
];

const PROVIDER_ACTIONS: readonly ActionDef[] = [
  { label: "查看", operation: "getProviderModelProfile", requiresProfile: true },
  { label: "編輯", operation: "updateProviderModelProfile", requiresProfile: true, fields: PROFILE_FIELDS, prefillProfile: true },
  { label: "測試", operation: "testProviderModelProfile", requiresProfile: true },
  { label: "退役", operation: "retireProviderModelProfile", requiresProfile: true, confirmationOnly: true },
  { label: "設定金鑰", operation: "setProviderModelCredential", requiresProfile: true, fields: [{ key: "secret_env_ref", label: "Secret Env Reference", required: true }] },
  { label: "刪除金鑰", operation: "deleteProviderModelCredential", requiresProfile: true, confirmationOnly: true },
];

const CREATE_PROVIDER: ActionDef = {
  label: "新增 Provider",
  operation: "createProviderModelProfile",
  fields: PROFILE_FIELDS,
};

const ROUTING_ACTIONS: readonly ActionDef[] = [
  {
    label: "Candidate Group",
    operation: "createProviderCandidateGroup",
    fields: [
      { key: "name", label: "Group Name", required: true },
      { key: "use_case", label: "Use Case", required: true },
      { key: "profile_ids", label: "Profile IDs (comma separated)", required: true },
      { key: "data_classification", label: "Data Classification" },
      { key: "limits_json", label: "Limits JSON", kind: "textarea" },
      { key: "quality_tiers_json", label: "Quality Tiers JSON", kind: "textarea" },
    ],
  },
  { label: "Quarantine", operation: "getProviderQuarantine" },
  {
    label: "Restore",
    operation: "restoreProviderFromQuarantine",
    fields: [
      { key: "quarantine_id", label: "Quarantine ID", required: true },
      { key: "reason", label: "Reason", kind: "textarea", required: true },
    ],
  },
  {
    label: "Sandbox",
    operation: "runSandboxTest",
    requiresProfile: true,
    fields: [{ key: "canonical_instruction", label: "Canonical Instruction", kind: "textarea", required: true }],
  },
  {
    label: "Route",
    operation: "executeProviderRoute",
    fields: [
      { key: "candidate_group_id", label: "Candidate Group ID", required: true },
      { key: "required_capability", label: "Required Capability", kind: "select", required: true, options: CAPABILITIES },
      { key: "use_case", label: "Use Case" },
      { key: "data_classification", label: "Data Classification" },
      { key: "canonical_instruction", label: "Canonical Instruction", kind: "textarea", required: true },
    ],
  },
  {
    label: "Decision",
    operation: "getProviderRouteDecision",
    fields: [{ key: "route_decision_id", label: "Route Decision ID", required: true }],
  },
];

const OPERATIONS_ACTIONS: readonly ActionDef[] = [
  {
    label: "Kill Switch",
    operation: "setKillSwitch",
    fields: [
      { key: "target_type", label: "Target Type", kind: "select", required: true, options: ["PROFILE","GROUP"] },
      { key: "target_ref", label: "Target Ref", required: true },
      { key: "enabled", label: "Enabled", kind: "select", required: true, options: ["false","true"] },
      { key: "reason", label: "Reason", kind: "textarea", required: true },
      { key: "confirmation", label: "Confirmation", kind: "select", required: true, options: ["CONFIRM"] },
    ],
  },
  {
    label: "Configure",
    operation: "configureGovernedResource",
    fields: [
      { key: "resource_id", label: "Governed Resource ID", required: true },
      { key: "resource_type", label: "Resource Type", required: true },
      { key: "config_patch_json", label: "Config Patch JSON", kind: "textarea", required: true },
      { key: "reason", label: "Reason", kind: "textarea", required: true },
    ],
  },
  {
    label: "Approve",
    operation: "approveGovernedResource",
    fields: [
      { key: "resource_id", label: "Governed Resource ID", required: true },
      { key: "resource_type", label: "Resource Type", required: true },
      { key: "rationale", label: "Rationale", kind: "textarea", required: true },
      { key: "expected_resource_version", label: "Expected Resource Version", kind: "number", required: true },
    ],
  },
];

function ProjectionList({ rows, value }: { rows: readonly string[]; value: (key: string) => string }) {
  return <div className={styles.list}>{rows.map((row) => <div className={styles.listRow} key={row}><span>{row}</span><strong>{value(row)}</strong></div>)}</div>;
}

function parseJsonObject(value: string | undefined, field: string) {
  if (!value?.trim()) return {};
  try {
    const parsed: unknown = JSON.parse(value);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
    return parsed as Record<string, unknown>;
  } catch {
    throw new Error(`AIAPI_FIELD_INVALID:${field}`);
  }
}

function asNumber(value: string | undefined) {
  if (!value?.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function safeJson(value: unknown) {
  try { return JSON.stringify(value, null, 2); } catch { return String(value); }
}

function profileFormDefaults(value: unknown): Record<string, string> {
  const row = value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
  const requestTemplate = row.request_template && typeof row.request_template === "object" && !Array.isArray(row.request_template)
    ? row.request_template as Record<string, unknown>
    : {};
  const text = (key: string) => typeof row[key] === "string" ? String(row[key]) : "";
  return {
    provider_id: text("provider_id"),
    model_id: text("model_id"),
    capability_type: text("capability_type"),
    adapter_type: text("adapter_type"),
    base_url: text("base_url"),
    endpoint_path: text("endpoint_path"),
    http_method: text("http_method"),
    secret_env_ref: text("secret_env_ref"),
    timeout_seconds: row.timeout_seconds == null ? "" : String(row.timeout_seconds),
    prompt_template: typeof requestTemplate.prompt_template === "string" ? requestTemplate.prompt_template : "",
    request_template_json: Object.keys(requestTemplate).length ? safeJson(requestTemplate) : "",
    response_text_path: text("response_text_path"),
    preferred_language: text("preferred_language"),
    max_context: row.max_context == null ? "" : String(row.max_context),
    enabled: row.enabled === true ? "true" : "false",
  };
}

export function AiApiVisual() {
  const { locale } = useI18n();
  const [activeView, setActiveView] = useState<ViewKey>("provider");
  const [projection, setProjection] = useState<AiApiProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<ActionDef | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [lastResult, setLastResult] = useState<unknown>(null);

  const t = (key: Parameters<typeof aiApiText>[1]) => aiApiText(locale, key);
  const selected = VIEWS.find((view) => view.key === activeView) ?? VIEWS[1];

  const syncProjection = async (signal?: AbortSignal) => {
    const result = await readAiApiProjection(signal);
    setCorrelationId(result.correlation_id);
    if (result.ok) {
      setProjection(result.projection);
      setRuntimeError(null);
      setSelectedProfileId((current) => current && result.projection.provider_rows.some((row) => row.profile_id === current)
        ? current
        : result.projection.selected_resource_id);
    } else {
      setProjection(null);
      setRuntimeError(result.reason_code);
    }
    setLoading(false);
  };

  useEffect(() => {
    const controller = new AbortController();
    void syncProjection(controller.signal);
    return () => controller.abort();
  }, []);

  const selectedRow = useMemo(
    () => projection?.provider_rows.find((row) => row.profile_id === selectedProfileId) ?? null,
    [projection, selectedProfileId],
  );

  const projectionValue = (key: string) => projection?.values[key] ?? "—";
  const professionalValue = (key: string) => {
    const row = selectedRow;
    if (!row) return "—";
    switch (key) {
      case "AIAPI-01-PRO-DESC-IDENTITY": return `${row.provider_id} / ${row.model_id}`;
      case "AIAPI-01-PRO-DESC-POSITIONING": return row.capability;
      case "AIAPI-01-PRO-DESC-ACPOS-SCOPE": return row.capability_status;
      case "AIAPI-01-PRO-DESC-CAPABILITIES": return row.capability;
      case "AIAPI-01-PRO-DESC-INPUT": return row.adapter;
      case "AIAPI-01-PRO-DESC-OUTPUT": return row.adapter;
      case "AIAPI-01-PRO-DESC-LIMITS": return row.timeout;
      case "AIAPI-01-PRO-DESC-ENDPOINT": return `${row.base_url}${row.endpoint}`;
      case "AIAPI-01-PRO-DESC-AUTH": return row.credential_status;
      case "AIAPI-01-PRO-DESC-HEALTH": return row.health_status;
      case "AIAPI-01-PRO-DESC-LAST-TEST": return row.last_test;
      case "AIAPI-01-PRO-DESC-RECOMMENDED-USE": return row.capability_status === "APPROVED" ? row.capability : "—";
      case "AIAPI-01-PRO-DESC-RESTRICTIONS": return row.capability_status;
      default: return "—";
    }
  };

  const operationEnabled = (action: ActionDef) => {
    if (pending || loading || !projection) return false;
    if (action.requiresProfile && !selectedRow) return false;
    if (action.operation === "deleteProviderModelCredential" && selectedRow?.credential_status !== "SET") return false;
    const explicit = projection.control_enabled[action.operation];
    return explicit === undefined ? true : explicit;
  };

  const operationDisabledReason = (action: ActionDef) => {
    if (pending) return "AIAPI_COMMAND_PENDING";
    if (!projection) return runtimeError ?? "AIAPI_PROJECTION_NOT_READY";
    if (action.requiresProfile && !selectedRow) return "AIAPI_PROFILE_SELECTION_REQUIRED";
    if (action.operation === "deleteProviderModelCredential" && selectedRow?.credential_status !== "SET") return "AIAPI_CREDENTIAL_NOT_SET";
    if (projection.control_enabled[action.operation] === false) return `AIAPI_SERVER_GATE_BLOCKED:${action.operation}`;
    return null;
  };

  const execute = async (action: ActionDef, refs: AiApiCommandRefs, payload: unknown) => {
    setPending(true);
    setRuntimeError(null);
    try {
      const result = await invokeAiApiCommand(action.operation, refs, payload);
      setCorrelationId(result.correlation_id);
      if (!result.ok) {
        setRuntimeError(result.reason_code);
        setLastResult({ ok: false, status: result.status, reason_code: result.reason_code, correlation_id: result.correlation_id });
        return false;
      }
      setLastResult({ operation: action.operation, value: result.value, correlation_id: result.correlation_id });
      await syncProjection();
      return true;
    } finally {
      setPending(false);
    }
  };

  const openAction = async (action: ActionDef) => {
    if (!operationEnabled(action)) return;
    if (!action.fields?.length && !action.confirmationOnly) {
      const refs: AiApiCommandRefs = action.requiresProfile ? { profileId: selectedRow?.profile_id } : {};
      await execute(action, refs, {});
      return;
    }
    if (action.prefillProfile && selectedRow) {
      setPending(true);
      const detail = await invokeAiApiCommand("getProviderModelProfile", { profileId: selectedRow.profile_id }, {});
      setPending(false);
      setCorrelationId(detail.correlation_id);
      if (!detail.ok) {
        setRuntimeError(detail.reason_code);
        return;
      }
      setFormValues(profileFormDefaults(detail.value));
    } else if (action.confirmationOnly) {
      setFormValues({ confirmation: "" });
    } else {
      const initial: Record<string, string> = {};
      if (action.operation === "createProviderCandidateGroup" && selectedRow) initial.profile_ids = selectedRow.profile_id;
      if (action.operation === "setKillSwitch" && selectedRow) {
        initial.target_type = "PROFILE";
        initial.target_ref = selectedRow.profile_id;
      }
      setFormValues(initial);
    }
    setActiveAction(action);
  };

  const submitAction = async () => {
    const action = activeAction;
    if (!action) return;
    if (action.confirmationOnly) {
      if (formValues.confirmation !== "CONFIRM") {
        setRuntimeError("AIAPI_HIGH_RISK_CONFIRMATION_REQUIRED");
        return;
      }
      const ok = await execute(action, { profileId: selectedRow?.profile_id }, {});
      if (ok) { setActiveAction(null); setFormValues({}); }
      return;
    }

    for (const field of action.fields ?? []) {
      if (field.required && !formValues[field.key]?.trim()) {
        setRuntimeError(`AIAPI_FIELD_REQUIRED:${field.key}`);
        return;
      }
    }

    let refs: AiApiCommandRefs = {};
    let payload: Record<string, unknown> = { ...formValues };
    try {
      switch (action.operation) {
        case "createProviderModelProfile":
        case "updateProviderModelProfile": {
          const template = parseJsonObject(formValues.request_template_json, "request_template_json");
          if (formValues.prompt_template?.trim()) template.prompt_template = formValues.prompt_template.trim();
          payload = {
            provider_id: formValues.provider_id?.trim(),
            model_id: formValues.model_id?.trim(),
            capability_type: formValues.capability_type,
            adapter_type: formValues.adapter_type,
            base_url: formValues.base_url?.trim(),
            endpoint_path: formValues.endpoint_path?.trim(),
            http_method: formValues.http_method,
            secret_env_ref: formValues.secret_env_ref?.trim(),
            timeout_seconds: asNumber(formValues.timeout_seconds),
            request_template: template,
            response_text_path: formValues.response_text_path?.trim(),
            preferred_language: formValues.preferred_language?.trim() || null,
            max_context: asNumber(formValues.max_context) ?? null,
            enabled: formValues.enabled === "true",
            ...(action.operation === "updateProviderModelProfile" ? { expected_version: selectedRow?.version } : {}),
          };
          refs = action.operation === "updateProviderModelProfile" ? { profileId: selectedRow?.profile_id } : {};
          break;
        }
        case "setProviderModelCredential":
          refs = { profileId: selectedRow?.profile_id };
          payload = { secret_env_ref: formValues.secret_env_ref?.trim() };
          break;
        case "createProviderCandidateGroup":
          payload = {
            name: formValues.name?.trim(),
            use_case: formValues.use_case?.trim(),
            profile_ids: (formValues.profile_ids ?? "").split(",").map((item) => item.trim()).filter(Boolean),
            data_classification: formValues.data_classification?.trim() || null,
            limits: parseJsonObject(formValues.limits_json, "limits_json"),
            quality_tiers: formValues.quality_tiers_json?.trim() ? parseJsonObject(formValues.quality_tiers_json, "quality_tiers_json") : null,
          };
          break;
        case "restoreProviderFromQuarantine":
          refs = { quarantineId: formValues.quarantine_id };
          payload = { reason: formValues.reason?.trim() };
          break;
        case "runSandboxTest":
          payload = { profile_id: selectedRow?.profile_id, canonical_instruction: formValues.canonical_instruction?.trim() };
          break;
        case "executeProviderRoute":
          payload = {
            candidate_group_id: formValues.candidate_group_id?.trim(),
            required_capability: formValues.required_capability,
            use_case: formValues.use_case?.trim() || null,
            data_classification: formValues.data_classification?.trim() || "INTERNAL",
            canonical_instruction: formValues.canonical_instruction?.trim(),
          };
          break;
        case "getProviderRouteDecision":
          refs = { routeDecisionId: formValues.route_decision_id };
          payload = {};
          break;
        case "setKillSwitch":
          payload = {
            target_type: formValues.target_type,
            target_ref: formValues.target_ref?.trim(),
            enabled: formValues.enabled === "true",
            reason: formValues.reason?.trim(),
            confirmation: formValues.confirmation,
          };
          break;
        case "configureGovernedResource":
          refs = { resourceId: formValues.resource_id };
          payload = {
            resource_type: formValues.resource_type?.trim(),
            resource_id: formValues.resource_id?.trim(),
            config_patch_json: parseJsonObject(formValues.config_patch_json, "config_patch_json"),
            reason: formValues.reason?.trim(),
          };
          break;
        case "approveGovernedResource":
          refs = { resourceId: formValues.resource_id };
          payload = {
            resource_type: formValues.resource_type?.trim(),
            resource_id: formValues.resource_id?.trim(),
            rationale: formValues.rationale?.trim(),
            expected_resource_version: asNumber(formValues.expected_resource_version),
          };
          break;
        default:
          break;
      }
    } catch (error) {
      setRuntimeError(error instanceof Error ? error.message : "AIAPI_FORM_ADAPTER_FAILED");
      return;
    }

    const ok = await execute(action, refs, payload);
    if (ok) { setActiveAction(null); setFormValues({}); }
  };

  const pageState = loading ? "LOADING" : runtimeError ? "ERROR" : projection?.page_state ?? "READ_ONLY";
  const statusText = loading
    ? t("loading")
    : runtimeError
      ? runtimeError
      : `${projection?.page_state ?? "READ_ONLY"} · ${t("projectionBound")} · ${t("bindingReady")}`;

  const actionButtons = (actions: readonly ActionDef[]) => (
    <div className={styles.blockedActions} data-effectful-runtime="MATERIALIZED_CURRENT">
      {actions.map((action) => {
        const reason = operationDisabledReason(action);
        return (
          <button key={action.operation} type="button" disabled={!operationEnabled(action)}
            data-operation-id={action.operation} data-disabled-reason={reason ?? undefined}
            onClick={() => void openAction(action)}>{action.label}</button>
        );
      })}
    </div>
  );

  const renderMain = () => {
    if (activeView === "overview") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-OVERVIEW">
        <div className={styles.panelHeader}><h2>{t("overviewSummary")}</h2><span>{selected.uid}</span></div>
        <div className={styles.summaryGrid}>{OVERVIEW_GROUPS.map((row) => <div className={styles.summaryBox} key={row}><span>{row}</span><strong>{projectionValue(row)}</strong></div>)}</div>
        {!projection && <p className={styles.note}>{runtimeError ?? (loading ? t("loading") : t("noData"))}</p>}
      </section>
    );

    if (activeView === "routing") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-ROUTING-TEST">
        <div className={styles.panelHeader}><h2>{t("routingWorkspace")}</h2><span>{selected.uid}</span></div>
        <ProjectionList rows={ROUTING_GROUPS} value={projectionValue}/>
        {actionButtons(ROUTING_ACTIONS)}
        <p className={styles.note}>{runtimeError ?? t("bindingReady")}</p>
      </section>
    );

    if (activeView === "operations") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-OPERATIONS">
        <div className={styles.panelHeader}><h2>{t("operationsWorkspace")}</h2><span>{selected.uid}</span></div>
        <ProjectionList rows={OPERATIONS_GROUPS} value={projectionValue}/>
        {actionButtons(OPERATIONS_ACTIONS)}
        {!projection && <p className={styles.note}>{runtimeError ?? (loading ? t("loading") : t("noData"))}</p>}
      </section>
    );

    return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-PROVIDER-API">
        <div className={styles.panelHeader}><h2>{t("providerTable")}</h2><span>{selected.uid}</span></div>
        <div className={styles.table} data-provider-table="true" data-operation-id="listProviderModelProfiles">
          <div className={styles.tableHeader}>{PROVIDER_COLUMNS.map((col) => <span key={col}>{col}</span>)}</div>
          {projection?.provider_rows.length ? projection.provider_rows.map((row) => (
            <div className={styles.tableRow} key={row.profile_id}
              data-profile-id={row.profile_id} data-provider-id={row.provider_id} data-model-id={row.model_id}
              data-selected={selectedProfileId === row.profile_id ? "true" : "false"}
              onClick={() => setSelectedProfileId(row.profile_id)}>
              <span>{row.provider_name}</span><span>{row.model_name}</span><span>{row.capability}</span><span>{row.adapter}</span><span>{row.base_url}</span>
              <span>{row.endpoint}</span><span>{row.timeout}</span><span>{row.enabled}</span><span data-credential-status="true">{row.credential_status}</span><span>{row.last_test}</span>
              <span className={styles.rowActions}>
                {PROVIDER_ACTIONS.map((action) => {
                  const rowSelected = selectedProfileId === row.profile_id;
                  const reason = !rowSelected ? "AIAPI_PROFILE_SELECTION_REQUIRED" : operationDisabledReason(action);
                  return <button key={action.operation} type="button"
                    disabled={!rowSelected || !operationEnabled(action)}
                    data-operation-id={action.operation} data-disabled-reason={reason ?? undefined}
                    onClick={(event) => { event.stopPropagation(); setSelectedProfileId(row.profile_id); void openAction(action); }}>{action.label}</button>;
                })}
              </span>
            </div>
          )) : <div className={styles.empty}>{runtimeError ?? (loading ? t("loading") : t("noData"))}</div>}
        </div>
        {actionButtons([CREATE_PROVIDER])}
        <p className={styles.note}>{selectedRow ? `${t("selectedProvider")}: ${selectedRow.provider_id} / ${selectedRow.model_id}` : t("selectRequired")}</p>
        <p className={styles.secretNote}>{t("secretRule")} {t("noPlaintextSecret")}</p>
      </section>
    );
  };

  const providerSplit = activeView === "provider";

  return (
    <div className={styles.page} data-page-uid="admin:AIAPI-01" data-vis-step="VIS-15" data-route-status="RESOLVED_CURRENT_ADMIN_ROUTE"
      data-page-state={pageState} data-current-ui-binding-status="MATERIALIZED_CURRENT"
      data-data-classification={projection?.test_metadata?.data_classification}
      data-production-eligible={projection?.test_metadata ? String(projection.test_metadata.production_eligible) : undefined}>
      <section className={styles.contextBar}>
        <div className={styles.identity}><div className={styles.eyebrow}>AIAPI-01 · {t("pageName")}</div><h1>{t("pageName")}</h1><p>{t("pageRole")}</p></div>
        <div className={styles.status} data-operation-id="getUiProjection"><strong>{pending ? t("pending") : statusText}</strong><span>{t("correlation")}: {correlationId ?? "—"}</span></div>
      </section>

      <section className={styles.viewBar} aria-label={t("pageName")}>
        {VIEWS.map((view) => <button key={view.uid} type="button" className={`${styles.viewButton} ${activeView === view.key ? styles.viewActive : ""}`} data-view-switch={view.uid} aria-pressed={activeView === view.key} onClick={() => setActiveView(view.key)}>{t(view.label)}</button>)}
      </section>

      <div className={providerSplit ? styles.workGrid : styles.workGridSingle}>
        {renderMain()}
        {providerSplit && (
          <aside className={styles.infoPanel} data-panel-uid="AIAPI-01-PANEL-API-PROFESSIONAL-DESCRIPTION">
            <div className={styles.infoHeader}><h2>{t("professional")}</h2><span>READ ONLY</span></div>
            <p className={styles.note}>{selectedRow ? `${selectedRow.provider_id} / ${selectedRow.model_id}` : runtimeError ?? t("selectGuidance")}</p>
            <div className={styles.infoList}>{AIAPI_PRO_FIELDS.map(([uid, entry]) => <div className={styles.infoRow} key={uid} data-pro-field-uid={uid}><span>{aiApiProLabel(locale, entry)}</span><strong>{professionalValue(uid)}</strong></div>)}</div>
          </aside>
        )}
      </div>

      {activeAction && (
        <div className={styles.modalBackdrop} role="presentation" onMouseDown={() => !pending && setActiveAction(null)}>
          <section className={styles.formModal} role="dialog" aria-modal="true" aria-label={t("operationForm")} onMouseDown={(event) => event.stopPropagation()}>
            <div className={styles.modalHeader}><div><span>{t("operationForm")}</span><h2>{activeAction.label}</h2></div><button type="button" onClick={() => setActiveAction(null)} disabled={pending}>{t("close")}</button></div>
            {activeAction.confirmationOnly ? (
              <label className={styles.formField}>
                <span>Confirmation</span>
                <select value={formValues.confirmation ?? ""} onChange={(event) => setFormValues({ confirmation: event.target.value })} disabled={pending}>
                  <option value="">—</option><option value="CONFIRM">CONFIRM</option>
                </select>
              </label>
            ) : (
              <div className={styles.formGrid}>
                {(activeAction.fields ?? []).map((field) => (
                  <label className={field.kind === "textarea" ? styles.formFieldWide : styles.formField} key={field.key} data-required={field.required ? "true" : "false"}>
                    <span>{field.label}{field.required ? " *" : ""}</span>
                    {field.kind === "select" ? (
                      <select value={formValues[field.key] ?? ""} onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))} disabled={pending}>
                        <option value="">—</option>{field.options?.map((option) => <option value={option} key={option}>{option}</option>)}
                      </select>
                    ) : field.kind === "textarea" ? (
                      <textarea value={formValues[field.key] ?? ""} onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))} disabled={pending}/>
                    ) : (
                      <input type={field.kind === "number" ? "number" : "text"} value={formValues[field.key] ?? ""} onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))} disabled={pending}/>
                    )}
                  </label>
                ))}
              </div>
            )}
            {activeAction.operation === "setProviderModelCredential" && <p className={styles.secretNote}>{t("noPlaintextSecret")}</p>}
            {runtimeError && <p className={styles.errorNote}>{runtimeError}</p>}
            <div className={styles.modalActions}>
              <button type="button" onClick={() => { setActiveAction(null); setFormValues({}); }} disabled={pending}>{t("cancel")}</button>
              <button type="button" className={styles.primaryButton} onClick={() => void submitAction()} disabled={pending}>{t("submitAction")}</button>
            </div>
          </section>
        </div>
      )}

      {lastResult !== null && (
        <aside className={styles.resultPanel} data-aiapi-command-result="true">
          <div className={styles.resultHeader}><strong>{t("operationResult")}</strong><button type="button" onClick={() => setLastResult(null)}>{t("close")}</button></div>
          <pre>{safeJson(lastResult)}</pre>
        </aside>
      )}
    </div>
  );
}
