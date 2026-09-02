"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { erpControlLabel, erpText } from "@/i18n/erpCatalog";
import { ErpGovernedButton, ErpRuntimeProvider, ErpValue, useErpRuntimeState } from "./ErpControlRuntime";
import { ERP_CONTROL_BINDINGS } from "@/domain/erp/erpControlBindings";
import { isErpCommandAdapterBound } from "@/domain/erp/erpCommandPort";
import styles from "./ErpVisual.module.css";

type ViewKey = "finance" | "connector" | "sync";
type ActionDef = { id: string; primary?: boolean; needsForm?: boolean };
type FieldDef = { key: string; label: string; type: "text" | "number" | "select"; options?: readonly string[] };
type ViewDef = { key: ViewKey; tabId: string; sectionId: string; fields: readonly string[]; actions: readonly ActionDef[]; primary?: string };

const CONTEXT = ["ERP-01-FLD-SCOPE", "ERP-01-FLD-SNAPSHOT", "ERP-01-FLD-FRESHNESS"] as const;
const TABS = ["ERP-01-BTN-TAB-FINANCE", "ERP-01-BTN-TAB-CONNECTOR", "ERP-01-BTN-TAB-SYNC"] as const;
const VIEWS: readonly ViewDef[] = [
  {
    key: "finance", tabId: "ERP-01-BTN-TAB-FINANCE", sectionId: "ERP-01-SEC-03",
    fields: ["ERP-01-FLD-FIN-COST", "ERP-01-FLD-FIN-REVENUE", "ERP-01-FLD-FIN-CASHFLOW", "ERP-01-FLD-FIN-CAPACITY", "ERP-01-FLD-FIN-FORECAST", "ERP-01-FLD-FIN-GUARDRAILS", "ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY"],
    actions: [
      { id: "ERP-01-BTN-FACTPACK" },
      { id: "ERP-01-BTN-GUARDRAILS" },
      { id: "ERP-01-BTN-FORECAST" },
      { id: "ERP-01-BTN-EXPORT", needsForm: true },
    ],
  },
  {
    key: "connector", tabId: "ERP-01-BTN-TAB-CONNECTOR", sectionId: "ERP-01-SEC-04",
    fields: ["ERP-01-FLD-CONN-CONNECTOR-ID", "ERP-01-FLD-CONN-PROVIDER-KEY", "ERP-01-FLD-CONN-ADAPTER-KEY", "ERP-01-FLD-CONN-SECRET-REFERENCE-ID", "ERP-01-FLD-CONN-ENTITY-SCOPE", "ERP-01-FLD-CONN-CONNECTION-STATUS", "ERP-01-FLD-CONN-MAPPING-VERSION"],
    actions: [
      { id: "ERP-01-BTN-CONNECTOR-CREATE", primary: true, needsForm: true },
      { id: "ERP-01-BTN-CONNECTOR-UPDATE", needsForm: true },
      { id: "ERP-01-BTN-CONNECTOR-VALIDATE" },
      { id: "ERP-01-BTN-MAPPING-VALIDATE" },
    ],
  },
  {
    key: "sync", tabId: "ERP-01-BTN-TAB-SYNC", sectionId: "ERP-01-SEC-05",
    fields: ["ERP-01-FLD-SYNC-SNAPSHOT-ID", "ERP-01-FLD-SYNC-FRESHNESS-AT", "ERP-01-FLD-SYNC-CURRENCY-TIMEZONE", "ERP-01-FLD-SYNC-COMPLETENESS", "ERP-01-FLD-SYNC-LAST-SYNC-STATUS", "ERP-01-FLD-SYNC-FAILURE-ID"],
    actions: [
      { id: "ERP-01-BTN-SNAPSHOT-REFRESH", needsForm: true },
      { id: "ERP-01-BTN-SYNC-CREATE", needsForm: true },
      { id: "ERP-01-BTN-SYNC-STATUS" },
      { id: "ERP-01-BTN-SYNC-RETRY" },
      { id: "ERP-01-BTN-FAILURE-GET" },
    ],
  },
] as const;

export const ERP_CONTROL_REGISTRY = [
  ...CONTEXT,
  ...TABS,
  ...VIEWS.flatMap((view) => [...view.fields, ...view.actions.map((action) => action.id)]),
  "ERP-01-FLD-READINESS", "ERP-01-FLD-AUDIT-REF", "ERP-01-BTN-DETAIL",
] as const;

function formFieldsFor(actionId: string, label: (id: string) => string, t: (key: Parameters<typeof erpText>[1]) => string): readonly FieldDef[] {
  switch (actionId) {
    case "ERP-01-BTN-CONNECTOR-CREATE":
      return [
        { key: "provider_key", label: t("fieldProviderKey"), type: "text" },
        { key: "adapter_key", label: t("fieldAdapterKey"), type: "text" },
        { key: "secret_reference_id", label: t("fieldSecretReferenceId"), type: "text" },
        { key: "entity_scope", label: t("fieldEntityScope"), type: "text" },
        { key: "mapping_version", label: t("fieldMappingVersion"), type: "number" },
        { key: "mapping_entity_name", label: t("fieldMappingEntityName"), type: "text" },
        { key: "mapping_source_schema", label: t("fieldMappingSourceSchema"), type: "text" },
        { key: "mapping_target_schema", label: t("fieldMappingTargetSchema"), type: "text" },
        { key: "mapping_transform_spec", label: t("fieldMappingTransformSpec"), type: "text" },
        { key: "data_classification", label: t("fieldDataClassification"), type: "text" },
      ];
    case "ERP-01-BTN-CONNECTOR-UPDATE":
      return [
        { key: "entity_scope", label: t("fieldEntityScope"), type: "text" },
        { key: "mapping_version", label: t("fieldMappingVersion"), type: "number" },
        { key: "mapping_entity_name", label: t("fieldMappingEntityName"), type: "text" },
        { key: "mapping_source_schema", label: t("fieldMappingSourceSchema"), type: "text" },
        { key: "mapping_target_schema", label: t("fieldMappingTargetSchema"), type: "text" },
        { key: "mapping_transform_spec", label: t("fieldMappingTransformSpec"), type: "text" },
        { key: "data_classification", label: t("fieldDataClassification"), type: "text" },
      ];
    case "ERP-01-BTN-SNAPSHOT-REFRESH":
      return [{ key: "requested_scope", label: t("fieldRequestedScope"), type: "text" }];
    case "ERP-01-BTN-SYNC-CREATE":
      return [
        { key: "requested_scope", label: t("fieldRequestedScope"), type: "text" },
        { key: "data_classification", label: t("fieldDataClassification"), type: "text" },
        { key: "snapshot_type", label: t("fieldSnapshotType"), type: "select", options: ["delta", "full"] },
        { key: "snapshot_document", label: t("fieldSnapshotDocument"), type: "text" },
        { key: "records_payload", label: t("fieldRecordsPayload"), type: "text" },
        { key: "completeness", label: t("fieldCompleteness"), type: "text" },
        { key: "external_result_verified", label: t("fieldExternalResultVerified"), type: "select", options: ["false", "true"] },
        { key: "external_evidence_refs", label: t("fieldExternalEvidenceRefs"), type: "text" },
      ];
    case "ERP-01-BTN-EXPORT":
      return [{ key: "scope", label: t("fieldExportScope"), type: "text" }];
    default:
      return [];
  }
}

function ErpVisualBody() {
  const { locale } = useI18n();
  const { projection, runtimeError, pending, invoke } = useErpRuntimeState();
  const [activeView, setActiveView] = useState<ViewKey>("finance");
  const [drawerAction, setDrawerAction] = useState<ActionDef | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const view = VIEWS.find((item) => item.key === activeView) ?? VIEWS[0];
  const label = (id: string) => erpControlLabel(locale, id);
  const t = (key: Parameters<typeof erpText>[1]) => erpText(locale, key);
  const boundary = activeView === "finance" ? t("financeBoundary") : activeView === "connector" ? t("secretBoundary") : t("missingBoundary");

  const actionEnabled = (action: ActionDef) => {
    const binding = ERP_CONTROL_BINDINGS[action.id as keyof typeof ERP_CONTROL_BINDINGS];
    const allowed = Boolean(binding) && projection?.gate_state[binding.gate_uid] === true;
    const stateAllowed = action.id === "ERP-01-BTN-CONNECTOR-CREATE" ? !(projection?.selected.connector_id) : action.id === "ERP-01-BTN-CONNECTOR-UPDATE" ? Boolean(projection?.selected.connector_id) : true;
    return allowed && stateAllowed && (binding?.effect_type === "UI_CONTEXT_STATE" || isErpCommandAdapterBound()) && !pending;
  };
  const openForm = (action: ActionDef) => { setFormValues({}); setDetailOpen(false); setDrawerAction(action); };
  const submitForm = () => {
    if (!drawerAction) return;
    const binding = ERP_CONTROL_BINDINGS[drawerAction.id as keyof typeof ERP_CONTROL_BINDINGS];
    void invoke(binding.action_uid, drawerAction.id, formValues).then(() => setDrawerAction(null));
  };

  const drawerState = drawerAction ? "OPEN_FORM" : detailOpen ? "OPEN_DETAIL" : "CLOSED_EMPTY";
  const drawerFields = drawerAction ? formFieldsFor(drawerAction.id, label, t) : [];
  const statusLine = pending ? t("waitingForData") : runtimeError ?? projection?.page_state ?? t("noRealData");

  return (
    <div className={styles.page} data-page-uid="admin:ERP-01" data-vis-step="VIS-14" data-route-status="RESOLVED_USER_APPROVED_ADMIN_ROUTE" data-page-state={runtimeError?"ERROR":projection?.page_state??"READ_ONLY"} data-authority-control-count={ERP_CONTROL_REGISTRY.length}>
      <section className={styles.contextBar} data-section-id="ERP-01-SEC-01">
        <div className={styles.identity}>
          <div className={styles.eyebrow}>ERP-01 · {t("pageName")}</div>
          <h1>{t("pageName")}</h1><p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextData}>
          {CONTEXT.map((id) => <div key={id} className={styles.contextCell} data-control-id={id}><span>{label(id)}</span><strong><ErpValue controlId={id}/></strong></div>)}
        </div>
      </section>

      <section className={styles.viewBar} data-section-id="ERP-01-SEC-02" aria-label={t("pageName")}>
        {VIEWS.map((item) => <ErpGovernedButton key={item.key} className={`${styles.viewButton} ${activeView === item.key ? styles.viewActive : ""}`} controlId={item.tabId} onUiClick={() => setActiveView(item.key)}>{label(item.tabId)}</ErpGovernedButton>)}
      </section>

      <div className={styles.workspaceGrid}>
        <main className={styles.mainWorkspace}>
          <section className={styles.panel} data-section-id={view.sectionId}>
            <div className={styles.panelHeader}><h2>{label(view.tabId)}</h2><span>{t("currentView")}</span></div>
            <div className={styles.table}>
              {view.fields.map((id) => <div key={id} className={styles.row} data-control-id={id}><div className={styles.label}>{label(id)}</div><div className={styles.value}><ErpValue controlId={id}/></div></div>)}
            </div>
            <div className={styles.boundary}>{boundary}</div>
            <div className={styles.emptyNote}>{t("noRealData")}</div>
            <section className={styles.actionDock} data-section-id="ERP-01-SEC-07">
              <div className={styles.dockLabel}><span>{t("actionDock")}</span><strong>{label(view.tabId)}</strong></div>
              <div className={styles.dockActions}>
                {view.actions.map((action) => {
                  if (action.needsForm) {
                    const binding = ERP_CONTROL_BINDINGS[action.id as keyof typeof ERP_CONTROL_BINDINGS];
                    const enabled = actionEnabled(action);
                    return (
                      <button key={action.id} type="button" className={action.primary ? styles.primaryButton : styles.button} data-control-id={action.id} data-action-uid={binding?.action_uid} data-gate-uid={binding?.gate_uid} data-permission-uid={binding?.permission_uid} data-disabled-reason={enabled ? undefined : binding?.gate_uid} disabled={!enabled} onClick={() => openForm(action)}>
                        {label(action.id)}
                      </button>
                    );
                  }
                  return <ErpGovernedButton key={action.id} controlId={action.id} className={action.primary ? styles.primaryButton : styles.button}>{label(action.id)}</ErpGovernedButton>;
                })}
              </div>
            </section>
          </section>
        </main>

        <aside className={styles.rail} data-section-id="ERP-01-SEC-06">
          <div className={styles.railHeader}><h2>{t("governance")}</h2><span>{label(view.tabId)}</span></div>
          <div className={styles.railTable}>
            <div className={styles.railRow} data-control-id="ERP-01-FLD-READINESS"><span>{label("ERP-01-FLD-READINESS")}</span><strong><ErpValue controlId="ERP-01-FLD-READINESS"/></strong></div>
            <div className={styles.railRow} data-control-id="ERP-01-FLD-AUDIT-REF"><span>{label("ERP-01-FLD-AUDIT-REF")}</span><strong><ErpValue controlId="ERP-01-FLD-AUDIT-REF"/></strong></div>
          </div>
          <ErpGovernedButton className={`${styles.button} ${styles.detailButton}`} controlId="ERP-01-BTN-DETAIL" onUiClick={() => { setDrawerAction(null); setDetailOpen((prev) => !prev); }}>{label("ERP-01-BTN-DETAIL")}</ErpGovernedButton>
          <p className={styles.railNote} data-projection-ref="RUNTIME" data-wait-state={pending ? "PENDING" : "IDLE"}>{statusLine}</p>
          <aside className={styles.detailDrawer} data-section-id="ERP-01-SEC-08" aria-hidden={drawerState === "CLOSED_EMPTY"} data-state={drawerState}>
            {drawerAction ? (
              <div className={styles.drawerForm} data-drawer-form={drawerAction.id}>
                <h2>{t("formTitle")} · {label(drawerAction.id)}</h2>
                {drawerFields.map((field) => (
                  <label className={styles.drawerField} key={field.key}>
                    <span>{field.label}</span>
                    {field.type === "select" ? (
                      <select value={formValues[field.key] ?? (field.options?.[0] ?? "")} onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))} disabled={pending}>
                        {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
                      </select>
                    ) : (
                      <input type={field.type === "number" ? "number" : "text"} value={formValues[field.key] ?? ""} onChange={(event) => setFormValues((prev) => ({ ...prev, [field.key]: event.target.value }))} disabled={pending} />
                    )}
                  </label>
                ))}
                <div className={styles.drawerActions}>
                  <button type="button" className={styles.button} onClick={() => setDrawerAction(null)} disabled={pending}>{t("cancel")}</button>
                  <button type="button" className={styles.primaryButton} onClick={submitForm} disabled={pending}>{t("submitAction")}</button>
                </div>
              </div>
            ) : (
              <>
                <h2>{t("detail")}</h2>
                {detailOpen ? (
                  <div className={styles.drawerDetail} data-drawer-form="ERP-01-DETAIL">
                    {view.fields.map((controlId) => (
                      <div className={styles.row} key={controlId} data-control-id={controlId}>
                        <div className={styles.label}>{label(controlId)}</div>
                        <div className={styles.value}><ErpValue controlId={controlId}/></div>
                      </div>
                    ))}
                    <div className={styles.row} data-control-id="ERP-01-FLD-AUDIT-REF">
                      <div className={styles.label}>{label("ERP-01-FLD-AUDIT-REF")}</div>
                      <div className={styles.value}><ErpValue controlId="ERP-01-FLD-AUDIT-REF"/></div>
                    </div>
                  </div>
                ) : <p>{t("noRealData")}</p>}
              </>
            )}
          </aside>
        </aside>
      </div>
    </div>
  );
}

export function ErpVisual(){return <ErpRuntimeProvider><ErpVisualBody/></ErpRuntimeProvider>}
