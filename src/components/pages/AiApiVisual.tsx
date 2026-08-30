"use client";

import { useState } from "react";
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
const PROVIDER_COLUMNS = ["Provider", "Model", "Capability", "Adapter", "Base URL", "Endpoint", "Timeout", "Enabled", "Credential Status", "Last Test"] as const;

function ProjectionList({ rows }: { rows: readonly string[] }) {
  return <div className={styles.list}>{rows.map((row) => <div className={styles.listRow} key={row}><span>{row}</span><strong>—</strong></div>)}</div>;
}

export function AiApiVisual() {
  const { locale } = useI18n();
  const [activeView, setActiveView] = useState<ViewKey>("provider");
  const t = (key: Parameters<typeof aiApiText>[1]) => aiApiText(locale, key);
  const selected = VIEWS.find((view) => view.key === activeView) ?? VIEWS[1];

  const renderMain = () => {
    if (activeView === "overview") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-OVERVIEW">
        <div className={styles.panelHeader}><h2>{t("overviewSummary")}</h2><span>{selected.uid}</span></div>
        <div className={styles.summaryGrid}>{OVERVIEW_GROUPS.map((row) => <div className={styles.summaryBox} key={row}><span>{row}</span><strong>—</strong></div>)}</div>
        <p className={styles.note}>{t("noData")}</p>
      </section>
    );

    if (activeView === "routing") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-ROUTING-TEST">
        <div className={styles.panelHeader}><h2>{t("routingWorkspace")}</h2><span>{selected.uid}</span></div>
        <ProjectionList rows={ROUTING_GROUPS}/>
        <p className={styles.note}>{t("remapBlocked")}</p>
      </section>
    );

    if (activeView === "operations") return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-OPERATIONS">
        <div className={styles.panelHeader}><h2>{t("operationsWorkspace")}</h2><span>{selected.uid}</span></div>
        <ProjectionList rows={OPERATIONS_GROUPS}/>
        <p className={styles.note}>{t("noData")}</p>
      </section>
    );

    return (
      <section className={styles.panel} data-view-uid="AIAPI-01-VIEW-PROVIDER-API">
        <div className={styles.panelHeader}><h2>{t("providerTable")}</h2><span>{selected.uid}</span></div>
        <div className={styles.table} data-provider-table="true">
          <div className={styles.tableHeader}>{PROVIDER_COLUMNS.map((col) => <span key={col}>{col}</span>)}</div>
          <div className={styles.empty}>{t("noData")}</div>
        </div>
        <p className={styles.note}>{t("remapBlocked")}</p>
        <p className={styles.secretNote}>{t("secretRule")}</p>
      </section>
    );
  };

  const providerSplit = activeView === "provider";
  return (
    <div className={styles.page} data-page-uid="admin:AIAPI-01" data-vis-step="VIS-15" data-route-status="RESOLVED_USER_APPROVED_ADMIN_ROUTE" data-page-state="STATIC_UI_REMAP_BLOCKED" data-current-ui-binding-status="REMAP_REQUIRED_NOT_EXECUTED">
      <section className={styles.contextBar}>
        <div className={styles.identity}><div className={styles.eyebrow}>AIAPI-01 · {t("pageName")}</div><h1>{t("pageName")}</h1><p>{t("pageRole")}</p></div>
        <div className={styles.status}>{t("remapBlocked")}</div>
      </section>

      <section className={styles.viewBar} aria-label={t("pageName")}>
        {VIEWS.map((view) => <button key={view.uid} type="button" className={`${styles.viewButton} ${activeView === view.key ? styles.viewActive : ""}`} data-view-switch={view.uid} aria-pressed={activeView === view.key} onClick={() => setActiveView(view.key)}>{t(view.label)}</button>)}
      </section>

      <div className={providerSplit ? styles.workGrid : styles.workGridSingle}>
        {renderMain()}
        {providerSplit && (
          <aside className={styles.infoPanel} data-panel-uid="AIAPI-01-PANEL-API-PROFESSIONAL-DESCRIPTION">
            <div className={styles.infoHeader}><h2>{t("professional")}</h2><span>READ ONLY</span></div>
            <p className={styles.note}>{t("selectGuidance")}</p>
            <div className={styles.infoList}>{AIAPI_PRO_FIELDS.map(([uid, entry]) => <div className={styles.infoRow} key={uid} data-pro-field-uid={uid}><span>{aiApiProLabel(locale, entry)}</span><strong>—</strong></div>)}</div>
          </aside>
        )}
      </div>
    </div>
  );
}
