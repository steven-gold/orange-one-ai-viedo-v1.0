"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { erpControlLabel, erpText } from "@/i18n/erpCatalog";
import styles from "./ErpVisual.module.css";

type ViewKey = "finance" | "connector" | "sync";
type ViewDef = { key: ViewKey; tabId: string; sectionId: string; fields: readonly string[]; actions: readonly string[]; primary?: string };

const CONTEXT = ["ERP-01-FLD-SCOPE", "ERP-01-FLD-SNAPSHOT", "ERP-01-FLD-FRESHNESS"] as const;
const TABS = ["ERP-01-BTN-TAB-FINANCE", "ERP-01-BTN-TAB-CONNECTOR", "ERP-01-BTN-TAB-SYNC"] as const;
const VIEWS: readonly ViewDef[] = [
  {
    key: "finance", tabId: "ERP-01-BTN-TAB-FINANCE", sectionId: "ERP-01-SEC-03",
    fields: ["ERP-01-FLD-FIN-COST", "ERP-01-FLD-FIN-REVENUE", "ERP-01-FLD-FIN-CASHFLOW", "ERP-01-FLD-FIN-CAPACITY", "ERP-01-FLD-FIN-FORECAST", "ERP-01-FLD-FIN-GUARDRAILS", "ERP-01-FLD-FIN-RECOMMENDATION-BOUNDARY"],
    actions: ["ERP-01-BTN-FACTPACK", "ERP-01-BTN-GUARDRAILS", "ERP-01-BTN-FORECAST", "ERP-01-BTN-EXPORT"],
  },
  {
    key: "connector", tabId: "ERP-01-BTN-TAB-CONNECTOR", sectionId: "ERP-01-SEC-04",
    fields: ["ERP-01-FLD-CONN-CONNECTOR-ID", "ERP-01-FLD-CONN-PROVIDER-KEY", "ERP-01-FLD-CONN-ADAPTER-KEY", "ERP-01-FLD-CONN-SECRET-REFERENCE-ID", "ERP-01-FLD-CONN-ENTITY-SCOPE", "ERP-01-FLD-CONN-CONNECTION-STATUS", "ERP-01-FLD-CONN-MAPPING-VERSION"],
    actions: ["ERP-01-BTN-CONNECTOR-CREATE", "ERP-01-BTN-CONNECTOR-UPDATE", "ERP-01-BTN-CONNECTOR-VALIDATE", "ERP-01-BTN-MAPPING-VALIDATE"],
    primary: "ERP-01-BTN-CONNECTOR-CREATE",
  },
  {
    key: "sync", tabId: "ERP-01-BTN-TAB-SYNC", sectionId: "ERP-01-SEC-05",
    fields: ["ERP-01-FLD-SYNC-SNAPSHOT-ID", "ERP-01-FLD-SYNC-FRESHNESS-AT", "ERP-01-FLD-SYNC-CURRENCY-TIMEZONE", "ERP-01-FLD-SYNC-COMPLETENESS", "ERP-01-FLD-SYNC-LAST-SYNC-STATUS", "ERP-01-FLD-SYNC-FAILURE-ID"],
    actions: ["ERP-01-BTN-SNAPSHOT-REFRESH", "ERP-01-BTN-SYNC-CREATE", "ERP-01-BTN-SYNC-STATUS", "ERP-01-BTN-SYNC-RETRY", "ERP-01-BTN-FAILURE-GET"],
  },
] as const;

export const ERP_CONTROL_REGISTRY = [
  ...CONTEXT,
  ...TABS,
  ...VIEWS.flatMap((view) => [...view.fields, ...view.actions]),
  "ERP-01-FLD-READINESS", "ERP-01-FLD-AUDIT-REF", "ERP-01-BTN-DETAIL",
] as const;

export function ErpVisual() {
  const { locale } = useI18n();
  const [activeView, setActiveView] = useState<ViewKey>("finance");
  const view = VIEWS.find((item) => item.key === activeView) ?? VIEWS[0];
  const label = (id: string) => erpControlLabel(locale, id);
  const t = (key: Parameters<typeof erpText>[1]) => erpText(locale, key);
  const boundary = activeView === "finance" ? t("financeBoundary") : activeView === "connector" ? t("secretBoundary") : t("missingBoundary");

  return (
    <div className={styles.page} data-page-uid="admin:ERP-01" data-vis-step="VIS-14" data-route-status="RESOLVED_USER_APPROVED_ADMIN_ROUTE" data-page-state="VISUAL_ONLY_NO_BUSINESS_DATA" data-authority-control-count={ERP_CONTROL_REGISTRY.length}>
      <section className={styles.contextBar} data-section-id="ERP-01-SEC-01">
        <div className={styles.identity}>
          <div className={styles.eyebrow}>ERP-01 · {t("pageName")}</div>
          <h1>{t("pageName")}</h1><p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextData}>
          {CONTEXT.map((id) => <div key={id} className={styles.contextCell} data-control-id={id}><span>{label(id)}</span><strong>—</strong></div>)}
        </div>
      </section>

      <section className={styles.viewBar} data-section-id="ERP-01-SEC-02" aria-label={t("pageName")}>
        {VIEWS.map((item) => <button key={item.key} type="button" className={`${styles.viewButton} ${activeView === item.key ? styles.viewActive : ""}`} data-control-id={item.tabId} aria-pressed={activeView === item.key} onClick={() => setActiveView(item.key)}>{label(item.tabId)}</button>)}
      </section>

      <div className={styles.workspaceGrid}>
        <main className={styles.mainWorkspace}>
          <section className={styles.panel} data-section-id={view.sectionId}>
            <div className={styles.panelHeader}><h2>{label(view.tabId)}</h2><span>{t("currentView")}</span></div>
            <div className={styles.table}>
              {view.fields.map((id) => <div key={id} className={styles.row} data-control-id={id}><div className={styles.label}>{label(id)}</div><div className={styles.value}>—</div></div>)}
            </div>
            <div className={styles.boundary}>{boundary}</div>
            <div className={styles.emptyNote}>{t("noRealData")}</div>
            <section className={styles.actionDock} data-section-id="ERP-01-SEC-07">
              <div className={styles.dockLabel}><span>{t("actionDock")}</span><strong>{label(view.tabId)}</strong></div>
              <div className={styles.dockActions}>
                {view.actions.map((id) => <button key={id} type="button" data-control-id={id} className={id === view.primary ? styles.primaryButton : styles.button} disabled>{label(id)}</button>)}
              </div>
            </section>
          </section>
        </main>

        <aside className={styles.rail} data-section-id="ERP-01-SEC-06">
          <div className={styles.railHeader}><h2>{t("governance")}</h2><span>{label(view.tabId)}</span></div>
          <div className={styles.railTable}>
            <div className={styles.railRow} data-control-id="ERP-01-FLD-READINESS"><span>{label("ERP-01-FLD-READINESS")}</span><strong>—</strong></div>
            <div className={styles.railRow} data-control-id="ERP-01-FLD-AUDIT-REF"><span>{label("ERP-01-FLD-AUDIT-REF")}</span><strong>—</strong></div>
          </div>
          <button type="button" className={`${styles.button} ${styles.detailButton}`} data-control-id="ERP-01-BTN-DETAIL" disabled>{label("ERP-01-BTN-DETAIL")}</button>
          <p className={styles.railNote}>{t("visualPhase")}</p>
          <aside className={styles.detailDrawer} data-section-id="ERP-01-SEC-08" data-state="CLOSED_EMPTY" aria-hidden="true"><h2>{t("detail")}</h2><p>{t("noRealData")}</p></aside>
        </aside>
      </div>
    </div>
  );
}
