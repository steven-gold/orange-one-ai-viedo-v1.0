"use client";

import { useEffect, useState } from "react";
import { readAiApiProjection, type AiApiProjection } from "@/domain/aiApi/aiApiRuntimePort";
import { useI18n } from "@/i18n/LocaleProvider";
import { AIAPI_PRO_FIELDS, aiApiProLabel, aiApiText } from "@/i18n/aiApiCatalog";
import styles from "./AiApiVisual.module.css";

type ViewKey = "overview" | "provider" | "routing" | "operations";
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
const PROVIDER_ACTIONS = [
  ["查看", "getProviderModelProfile"], ["編輯", "updateProviderModelProfile"], ["測試", "testProviderModelProfile"],
  ["退役", "retireProviderModelProfile"], ["設定金鑰", "setProviderModelCredential"], ["刪除金鑰", "deleteProviderModelCredential"],
] as const;
const ROUTING_ACTIONS = [
  ["Candidate Group", "createProviderCandidateGroup"], ["Quarantine", "getProviderQuarantine"], ["Restore", "restoreProviderFromQuarantine"],
  ["Sandbox", "runSandboxTest"], ["Route", "executeProviderRoute"], ["Decision", "getProviderRouteDecision"],
] as const;
const OPERATIONS_ACTIONS = [["Kill Switch", "setKillSwitch"], ["Configure", "configureGovernedResource"], ["Approve", "approveGovernedResource"]] as const;

function ProjectionList({ rows, value }: { rows: readonly string[]; value: (key: string) => string }) {
  return <div className={styles.list}>{rows.map((row) => <div className={styles.listRow} key={row}><span>{row}</span><strong>{value(row)}</strong></div>)}</div>;
}
function BlockedOperations({ actions }: { actions: readonly (readonly [string,string])[] }) {
  return <div className={styles.blockedActions} data-effectful-runtime="BLOCKED">{actions.map(([label, operation]) => (
    <button key={operation} type="button" disabled data-operation-id={operation} data-disabled-reason="REMAP_REQUIRED_NOT_EXECUTED">{label}</button>
  ))}</div>;
}

export function AiApiVisual() {
  const { locale } = useI18n();
  const [activeView, setActiveView] = useState<ViewKey>("provider");
  const [projection, setProjection] = useState<AiApiProjection | null>(null);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [correlationId, setCorrelationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const t = (key: Parameters<typeof aiApiText>[1]) => aiApiText(locale, key);
  const selected = VIEWS.find((view) => view.key === activeView) ?? VIEWS[1];

  useEffect(() => {
    const controller = new AbortController();
    void readAiApiProjection(controller.signal).then((result) => {
      setCorrelationId(result.correlation_id);
      if (result.ok) { setProjection(result.projection); setRuntimeError(null); }
      else { setProjection(null); setRuntimeError(result.reason_code); }
      setLoading(false);
    });
    return () => controller.abort();
  }, []);

  const value = (key: string) => projection?.values[key] ?? "—";
  const pageState = loading ? "LOADING" : runtimeError ? "ERROR" : projection?.page_state ?? "READ_ONLY";
  const statusText = loading ? t("loading") : runtimeError ? `${runtimeError} · ${t("effectfulBlocked")}` : `${projection?.page_state ?? "READ_ONLY"} · ${t("projectionBound")} · ${t("remapBlocked")}`;

  const renderMain = () => {
    if (activeView === "overview") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-OVERVIEW">
        <div className={styles.panelHeader}><h2>{t("overviewSummary")}</h2><span>{selected.uid}</span></div>
        <div className={styles.summaryGrid}>{OVERVIEW_GROUPS.map((row) => <div className={styles.summaryBox} key={row}><span>{row}</span><strong>{value(row)}</strong></div>)}</div>
        {!projection && <p className={styles.note}>{runtimeError ?? (loading ? t("loading") : t("noData"))}</p>}
      </section>
    );
    if (activeView === "routing") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-ROUTING-TEST">
        <div className={styles.panelHeader}><h2>{t("routingWorkspace")}</h2><span>{selected.uid}</span></div>
        <ProjectionList rows={ROUTING_GROUPS} value={value}/><BlockedOperations actions={ROUTING_ACTIONS}/>
        <p className={styles.note}>{runtimeError ?? t("effectfulBlocked")}</p>
      </section>
    );
    if (activeView === "operations") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-OPERATIONS">
        <div className={styles.panelHeader}><h2>{t("operationsWorkspace")}</h2><span>{selected.uid}</span></div>
        <ProjectionList rows={OPERATIONS_GROUPS} value={value}/><BlockedOperations actions={OPERATIONS_ACTIONS}/>
        {!projection && <p className={styles.note}>{runtimeError ?? (loading ? t("loading") : t("noData"))}</p>}
      </section>
    );
    return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-PROVIDER-API">
        <div className={styles.panelHeader}><h2>{t("providerTable")}</h2><span>{selected.uid}</span></div>
        <div className={styles.table} data-provider-table="true" data-operation-id="listProviderModelProfiles">
          <div className={styles.tableHeader}>{PROVIDER_COLUMNS.map((col) => <span key={col}>{col}</span>)}</div>
          {projection?.provider_rows.length ? projection.provider_rows.map((row) => (
            <div className={styles.tableRow} key={`${row.provider_id}:${row.model_id}`} data-provider-id={row.provider_id} data-model-id={row.model_id} data-selected={projection.selected_resource_id === row.provider_id ? "true" : "false"}>
              <span>{row.provider_name}</span><span>{row.model_name}</span><span>{row.capability}</span><span>{row.adapter}</span><span>{row.base_url}</span>
              <span>{row.endpoint}</span><span>{row.timeout}</span><span>{row.enabled}</span><span data-credential-status="true">{row.credential_status}</span><span>{row.last_test}</span>
              <span className={styles.rowActions}>{PROVIDER_ACTIONS.map(([label, operation]) => <button key={operation} type="button" disabled data-operation-id={operation} data-disabled-reason="REMAP_REQUIRED_NOT_EXECUTED">{label}</button>)}</span>
            </div>
          )) : <div className={styles.empty}>{runtimeError ?? (loading ? t("loading") : t("noData"))}</div>}
        </div>
        <BlockedOperations actions={[["新增 Provider", "createProviderModelProfile"]]}/>
        <p className={styles.note}>{t("effectfulBlocked")}</p><p className={styles.secretNote}>{t("secretRule")}</p>
      </section>
    );
  };

  const providerSplit = activeView === "provider";
  return (
    <div className={styles.page} data-page-uid="admin:AIAPI-01" data-vis-step="VIS-15" data-route-status="RESOLVED_CURRENT_ADMIN_ROUTE"
      data-page-state={pageState} data-current-ui-binding-status="REMAP_REQUIRED_NOT_EXECUTED"
      data-data-classification={projection?.test_metadata?.data_classification}
      data-production-eligible={projection?.test_metadata ? String(projection.test_metadata.production_eligible) : undefined}>
      <section className={styles.contextBar}>
        <div className={styles.identity}><div className={styles.eyebrow}>AIAPI-01 · {t("pageName")}</div><h1>{t("pageName")}</h1><p>{t("pageRole")}</p></div>
        <div className={styles.status} data-operation-id="getUiProjection"><strong>{statusText}</strong><span>{t("correlation")}: {correlationId ?? "—"}</span></div>
      </section>
      <section className={styles.viewBar} aria-label={t("pageName")}>
        {VIEWS.map((view) => <button key={view.uid} type="button" className={`${styles.viewButton} ${activeView === view.key ? styles.viewActive : ""}`} data-view-switch={view.uid} aria-pressed={activeView === view.key} onClick={() => setActiveView(view.key)}>{t(view.label)}</button>)}
      </section>
      <div className={providerSplit ? styles.workGrid : styles.workGridSingle}>
        {renderMain()}
        {providerSplit && (
          <aside className={styles.infoPanel} data-panel-uid="AIAPI-01-PANEL-API-PROFESSIONAL-DESCRIPTION">
            <div className={styles.infoHeader}><h2>{t("professional")}</h2><span>READ ONLY</span></div>
            <p className={styles.note}>{projection?.selected_resource_id ? value("provider.selected") : runtimeError ?? t("selectGuidance")}</p>
            <div className={styles.infoList}>{AIAPI_PRO_FIELDS.map(([uid, entry]) => <div className={styles.infoRow} key={uid} data-pro-field-uid={uid}><span>{aiApiProLabel(locale, entry)}</span><strong>{value(uid)}</strong></div>)}</div>
          </aside>
        )}
      </div>
    </div>
  );
}
