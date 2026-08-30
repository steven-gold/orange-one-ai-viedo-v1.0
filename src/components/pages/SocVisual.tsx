"use client";

import { useI18n } from "@/i18n/LocaleProvider";
import { socControlLabel, socText } from "@/i18n/socCatalog";
import styles from "./SocVisual.module.css";
import { useState } from "react";

type StageKey = "platform" | "account_target" | "content" | "publish" | "records";

type ActionDef = { id: string; primary?: boolean; danger?: boolean; conditional?: boolean };
type StageDef = {
  key: StageKey;
  tabId: string;
  sectionId: string;
  componentId: string;
  code: string;
  fields: readonly string[];
  searchId?: string;
  actions: readonly ActionDef[];
};

const CONTEXT_CONTROLS = ["SOC-01-FLD-CONTEXT", "SOC-01-FLD-CURRENT-STATE"] as const;
const STAGE_TABS = ["SOC-01-TAB-STAGE-1", "SOC-01-TAB-STAGE-2", "SOC-01-TAB-STAGE-3", "SOC-01-TAB-STAGE-4", "SOC-01-TAB-STAGE-5"] as const;

const STAGES: readonly StageDef[] = [
  {
    key: "platform", tabId: "SOC-01-TAB-STAGE-1", sectionId: "SOC-01-SEC-03", componentId: "SOC-01-CMP-PLATFORM", code: "01",
    fields: ["SOC-01-FLD-PLATFORM-LIST", "SOC-01-FLD-CAPABILITY", "SOC-01-FLD-POLICY", "SOC-01-FLD-HEALTH", "SOC-01-FLD-ENABLE-STATE"],
    actions: [
      { id: "SOC-01-BTN-PLATFORM-CONFIG", conditional: true },
      { id: "SOC-01-BTN-KILL", danger: true, conditional: true },
    ],
  },
  {
    key: "account_target", tabId: "SOC-01-TAB-STAGE-2", sectionId: "SOC-01-SEC-04", componentId: "SOC-01-CMP-ACCOUNT-TARGET", code: "02",
    fields: ["SOC-01-FLD-ACCOUNT-LIST", "SOC-01-FLD-CREDENTIAL-STATUS", "SOC-01-FLD-BINDING-VERIFY", "SOC-01-FLD-TARGET-DIRECTORY", "SOC-01-FLD-TARGET-CAPABILITY", "SOC-01-FLD-MANUAL-QUEUE"],
    searchId: "SOC-01-INP-TARGET-SEARCH",
    actions: [
      { id: "SOC-01-BTN-ACCOUNT-BIND" },
      { id: "SOC-01-BTN-CREDENTIAL-REVEAL", danger: true, conditional: true },
      { id: "SOC-01-BTN-ACCOUNT-UNBIND", conditional: true },
      { id: "SOC-01-BTN-TARGET-DISCOVERY" },
      { id: "SOC-01-BTN-TARGET-JOIN", conditional: true },
      { id: "SOC-01-BTN-MANUAL-COMPLETE", conditional: true },
    ],
  },
  {
    key: "content", tabId: "SOC-01-TAB-STAGE-3", sectionId: "SOC-01-SEC-05", componentId: "SOC-01-CMP-CONTENT", code: "03",
    fields: ["SOC-01-FLD-RELEASE-SOURCE", "SOC-01-FLD-PLATFORM-VARIANTS", "SOC-01-FLD-METADATA", "SOC-01-FLD-THUMBNAIL", "SOC-01-FLD-POLICY-CHECK", "SOC-01-FLD-APPROVAL", "SOC-01-FLD-VERSION-HISTORY"],
    actions: [
      { id: "SOC-01-BTN-CONTENT-SAVE" },
      { id: "SOC-01-BTN-CANDIDATE-DECIDE", conditional: true },
    ],
  },
  {
    key: "publish", tabId: "SOC-01-TAB-STAGE-4", sectionId: "SOC-01-SEC-06", componentId: "SOC-01-CMP-PUBLISH", code: "04",
    fields: ["SOC-01-FLD-TARGET-SELECTOR", "SOC-01-FLD-TARGET-CAPABILITY-STATUS", "SOC-01-FLD-MIN-INTERVAL", "SOC-01-FLD-DAILY-LIMIT", "SOC-01-FLD-WEEKLY-LIMIT", "SOC-01-FLD-SAME-COOLDOWN", "SOC-01-FLD-SIMILAR-COOLDOWN", "SOC-01-FLD-ALLOWED-WINDOW", "SOC-01-FLD-TARGET-RULE-NOTES", "SOC-01-FLD-CONTENT-PACKAGE", "SOC-01-FLD-CHANNEL-ACCOUNT", "SOC-01-FLD-SCHEDULE-AT", "SOC-01-FLD-AUTO-PUBLISH-POLICY", "SOC-01-FLD-HUMAN-APPROVAL-POLICY", "SOC-01-FLD-PUBLISH-QUEUE", "SOC-01-FLD-MANUAL-ASSIST-QUEUE"],
    actions: [
      { id: "SOC-01-BTN-POLICY-CONFIG" },
      { id: "SOC-01-BTN-PUBLISH", primary: true },
    ],
  },
  {
    key: "records", tabId: "SOC-01-TAB-STAGE-5", sectionId: "SOC-01-SEC-07", componentId: "SOC-01-CMP-RECORDS", code: "05",
    fields: ["SOC-01-FLD-POSTS", "SOC-01-FLD-TARGET-HISTORY", "SOC-01-FLD-POST-STATUS", "SOC-01-FLD-METRICS", "SOC-01-FLD-INTERACTIONS", "SOC-01-FLD-MANUAL-HISTORY", "SOC-01-FLD-CALLBACKS", "SOC-01-FLD-INCIDENTS", "SOC-01-FLD-WITHDRAWAL"],
    searchId: "SOC-01-INP-RECORD-SEARCH",
    actions: [{ id: "SOC-01-BTN-REFRESH" }],
  },
] as const;

export const SOC_CONTROL_REGISTRY = [
  ...CONTEXT_CONTROLS,
  ...STAGE_TABS,
  ...STAGES.flatMap((stage) => [...stage.fields, ...(stage.searchId ? [stage.searchId] : []), ...stage.actions.map((action) => action.id)]),
  "SOC-01-BTN-DETAIL",
  "SOC-01-FLD-BLOCKERS",
] as const;

const EMPTY_VISUAL_STATE = {
  exactGovernedPlatformBinding: false,
  highRiskOperationApplicable: false,
  accountBound: false,
  credentialRevealApplicable: false,
  targetJoinApplicable: false,
  manualActionPending: false,
  candidateReviewAvailable: false,
} as const;

export function SocVisual() {
  const { locale } = useI18n();
  const [activeStage, setActiveStage] = useState<StageKey>("platform");
  const stage = STAGES.find((item) => item.key === activeStage) ?? STAGES[0];
  const label = (id: string) => socControlLabel(locale, id);
  const t = (key: Parameters<typeof socText>[1]) => socText(locale, key);

  const actionVisible = (action: ActionDef) => {
    if (!action.conditional) return true;
    if (action.id === "SOC-01-BTN-PLATFORM-CONFIG") return EMPTY_VISUAL_STATE.exactGovernedPlatformBinding;
    if (action.id === "SOC-01-BTN-KILL") return EMPTY_VISUAL_STATE.highRiskOperationApplicable;
    if (action.id === "SOC-01-BTN-CREDENTIAL-REVEAL") return EMPTY_VISUAL_STATE.credentialRevealApplicable;
    if (action.id === "SOC-01-BTN-ACCOUNT-UNBIND") return EMPTY_VISUAL_STATE.accountBound;
    if (action.id === "SOC-01-BTN-TARGET-JOIN") return EMPTY_VISUAL_STATE.targetJoinApplicable;
    if (action.id === "SOC-01-BTN-MANUAL-COMPLETE") return EMPTY_VISUAL_STATE.manualActionPending;
    if (action.id === "SOC-01-BTN-CANDIDATE-DECIDE") return EMPTY_VISUAL_STATE.candidateReviewAvailable;
    return false;
  };

  return (
    <div className={styles.page} data-page-uid="admin:SOC-01" data-vis-step="VIS-13" data-route-status="RESOLVED_USER_APPROVED_ADMIN_ROUTE" data-page-state="VISUAL_ONLY_NO_BUSINESS_DATA" data-authority-control-count={SOC_CONTROL_REGISTRY.length}>
      <section className={styles.contextBar} data-section-id="SOC-01-SEC-01" data-component-id="SOC-01-CMP-CONTEXT">
        <div className={styles.identity}>
          <div className={styles.eyebrow}>SOC-01 · {t("pageName")}</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextData}>
          <div className={styles.contextCell} data-control-id="SOC-01-FLD-CONTEXT"><span>{label("SOC-01-FLD-CONTEXT")}</span><strong>—</strong></div>
          <div className={styles.contextCell} data-control-id="SOC-01-FLD-CURRENT-STATE"><span>{label("SOC-01-FLD-CURRENT-STATE")}</span><strong>—</strong></div>
        </div>
      </section>

      <section className={styles.stageBar} data-section-id="SOC-01-SEC-02" data-component-id="SOC-01-CMP-STAGES" aria-label={t("pageName")}>
        {STAGES.map((item) => (
          <button key={item.key} type="button" className={`${styles.stageButton} ${activeStage === item.key ? styles.stageActive : ""}`} data-control-id={item.tabId} aria-pressed={activeStage === item.key} onClick={() => setActiveStage(item.key)}>
            {item.code} · {label(item.tabId)}
          </button>
        ))}
      </section>

      <div className={styles.workspaceGrid}>
        <main className={styles.mainWorkspace}>
          <section className={styles.panel} data-section-id={stage.sectionId} data-component-id={stage.componentId}>
            <div className={styles.panelHeader}><h2>{label(stage.tabId)}</h2><span>{stage.code} · {t("currentStage")}</span></div>
            {stage.searchId && (
              <div className={styles.searchRow}>
                <label htmlFor={stage.searchId}>{label(stage.searchId)}</label>
                <input id={stage.searchId} className={styles.searchInput} data-control-id={stage.searchId} placeholder={t("searchPlaceholder")} disabled />
              </div>
            )}
            <div className={styles.table}>
              {stage.fields.map((controlId) => (
                <div className={styles.row} key={controlId} data-control-id={controlId}>
                  <div className={styles.label}>{label(controlId)}</div>
                  <div className={styles.value}>—</div>
                </div>
              ))}
            </div>
            <div className={styles.emptyNote}>{t("noRealData")}</div>
            <section className={styles.actionDock} data-section-id="SOC-01-SEC-09" data-component-id="SOC-01-CMP-ACTION-DOCK">
              <div className={styles.dockLabel}><span>{t("actionDock")}</span><strong>{label(stage.tabId)}</strong></div>
              <div className={styles.dockActions}>
                {stage.actions.filter(actionVisible).map((action) => (
                  <button key={action.id} type="button" data-control-id={action.id} className={action.primary ? styles.primaryButton : action.danger ? styles.dangerButton : styles.secondaryButton} disabled>
                    {label(action.id)}
                  </button>
                ))}
                {stage.actions.some((action) => action.conditional && !actionVisible(action)) && <span className={styles.conditionalNote}>{t("conditionalUnavailable")}</span>}
              </div>
            </section>
          </section>
        </main>

        <aside className={styles.rail} data-section-id="SOC-01-SEC-08" data-component-id="SOC-01-CMP-GOVERNANCE">
          <div className={styles.railHeader}><h2>{t("governance")}</h2><span>{stage.code}</span></div>
          <div className={styles.railTable}>
            <div className={styles.railRow} data-control-id="SOC-01-FLD-BLOCKERS"><span>{label("SOC-01-FLD-BLOCKERS")}</span><strong>—</strong></div>
            <div className={styles.railRow}><span>{t("currentStage")}</span><strong>{label(stage.tabId)}</strong></div>
          </div>
          <button className={`${styles.secondaryButton} ${styles.detailButton}`} type="button" data-control-id="SOC-01-BTN-DETAIL" disabled>{label("SOC-01-BTN-DETAIL")}</button>
          <p className={styles.railNote}>{t("visualPhase")}</p>
          <aside className={styles.detailDrawer} aria-hidden="true" data-state="CLOSED_EMPTY">
            <h2>{t("detail")}</h2><p>{t("noRealData")}</p>
          </aside>
        </aside>
      </div>
    </div>
  );
}
