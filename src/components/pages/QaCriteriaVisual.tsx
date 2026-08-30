"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { qaCriteriaText, qaSectionLabel } from "@/i18n/qaCriteriaCatalog";
import styles from "./QaCriteriaVisual.module.css";

type SectionKey =
  | "criteria_table"
  | "dimension_library"
  | "thresholds"
  | "department_mapping"
  | "required_checks"
  | "gate_policy"
  | "approval"
  | "impact";

const SECTION_CONTROLS: ReadonlyArray<{ key: SectionKey; sectionId: string; controlId: string }> = [
  { key: "criteria_table", sectionId: "SEC-ADMIN-SG-02-CRITERIA-TABLE", controlId: "CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN" },
  { key: "dimension_library", sectionId: "SEC-ADMIN-SG-02-DIMENSION-LIBRARY", controlId: "CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN" },
  { key: "thresholds", sectionId: "SEC-ADMIN-SG-02-THRESHOLDS", controlId: "CTRL-ADMIN-SG-02-THRESHOLDS-OPEN" },
  { key: "department_mapping", sectionId: "SEC-ADMIN-SG-02-DEPARTMENT-MAPPING", controlId: "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN" },
  { key: "required_checks", sectionId: "SEC-ADMIN-SG-02-REQUIRED-CHECKS", controlId: "CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" },
  { key: "gate_policy", sectionId: "SEC-ADMIN-SG-02-GATE-POLICY", controlId: "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN" },
  { key: "approval", sectionId: "SEC-ADMIN-SG-02-APPROVAL", controlId: "CTRL-ADMIN-SG-02-APPROVAL-OPEN" },
  { key: "impact", sectionId: "SEC-ADMIN-SG-02-IMPACT", controlId: "CTRL-ADMIN-SG-02-IMPACT-OPEN" },
] as const;

export function QaCriteriaVisual() {
  const { locale } = useI18n();
  const [drawer, setDrawer] = useState<SectionKey | "governance" | null>(null);

  const openSection = (key: SectionKey) => setDrawer(key);

  return (
    <div
      className={styles.page}
      data-page-uid="admin:SG-02"
      data-vis-step="VIS-16"
      data-authority-section-count="9"
      data-authority-control-count="11"
      data-page-state="VISUAL_ONLY_NO_BUSINESS_DATA"
    >
      <section className={styles.contextBar} aria-label="SG-02 Context">
        <div className={styles.identity}>
          <div className={styles.eyebrow}>ADMIN · SG-02 · QUALITY GOVERNANCE</div>
          <h1>{qaCriteriaText(locale, "pageName")}</h1>
          <p>{qaCriteriaText(locale, "pageRole")}</p>
        </div>
        <div className={styles.state}>QualityGovernance · FINAL_LOCKED · Current-only · missing = — · historical criteria version must remain reproducible</div>
      </section>

      <div className={styles.layout}>
        <section
          className={styles.panel}
          data-section-id="SEC-ADMIN-SG-02-CRITERIA-TABLE"
          aria-label={qaCriteriaText(locale, "criteriaTable")}
        >
          <div className={styles.sectionHead}>
            <div>
              <h2>{qaCriteriaText(locale, "criteriaTable")}</h2>
              <p>criteria_versions · dimensions · policies · mappings · approvals</p>
            </div>
            <button
              type="button"
              className={styles.openButton}
              data-control-id="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN"
              onClick={() => openSection("criteria_table")}
            >
              {qaSectionLabel(locale, "criteria_table")} ↗
            </button>
          </div>

          <div className={styles.criteriaTable}>
            <div className={styles.tableHeader} role="row">
              <span>{qaCriteriaText(locale, "version")}</span>
              <span>{qaCriteriaText(locale, "dimension")}</span>
              <span>{qaCriteriaText(locale, "policy")}</span>
              <span>{qaCriteriaText(locale, "mapping")}</span>
              <span>{qaCriteriaText(locale, "approval")}</span>
            </div>
            <div className={styles.empty}>{qaCriteriaText(locale, "noData")}</div>
          </div>

          <div className={styles.truthNote}>
            DRAFT → REVIEW → APPROVED → ACTIVE → SUPERSEDED → RETIRED. Active criteria is immutable; any change requires a new approved version, Impact, Approval and affected-task revalidation. No threshold is hardcoded in this visual layer.
          </div>
        </section>

        <aside className={styles.rail} aria-label={qaCriteriaText(locale, "detailSections")}>
          <h2 className={styles.railTitle}>{qaCriteriaText(locale, "detailSections")}</h2>
          <div className={styles.railList}>
            {SECTION_CONTROLS.slice(1).map((section) => (
              <section key={section.key} data-section-id={section.sectionId}>
                <button
                  type="button"
                  className={styles.railButton}
                  data-control-id={section.controlId}
                  onClick={() => openSection(section.key)}
                >
                  <span>{qaSectionLabel(locale, section.key)}</span>
                  <span>DRAWER ↗</span>
                </button>
              </section>
            ))}
          </div>
        </aside>
      </div>

      <section className={styles.dock} data-section-id="SEC-ADMIN-SG-02-ACTION-DOCK" aria-label="SG-02 Action Dock">
        <div className={styles.dockInfo}>
          <strong>Quality Criteria / Gate Policy</strong>
          <span>{qaCriteriaText(locale, "visualPhase")}</span>
        </div>
        <div className={styles.dockActions}>
          <button
            type="button"
            className={styles.dockButton}
            data-control-id="CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE"
            disabled
            title="configureGovernedResource runtime not enabled in visual phase"
          >
            {qaCriteriaText(locale, "configure")}
          </button>
          <button
            type="button"
            className={`${styles.dockButton} ${styles.primary}`}
            data-control-id="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE"
            disabled
            title="approveGovernedResource runtime not enabled in visual phase"
          >
            {qaCriteriaText(locale, "approve")}
          </button>
          <button
            type="button"
            className={styles.dockButton}
            data-control-id="CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN"
            onClick={() => setDrawer("governance")}
          >
            {qaCriteriaText(locale, "navOpen")}
          </button>
        </div>
      </section>

      {drawer && (
        <>
          <button className={styles.drawerBackdrop} type="button" aria-label="Close detail drawer" onClick={() => setDrawer(null)} />
          <aside className={styles.drawer} data-detail-drawer="SG-02" aria-label="SG-02 Detail Drawer">
            <div className={styles.drawerHead}>
              <div>
                <h3>{drawer === "governance" ? qaCriteriaText(locale, "navOpen") : qaSectionLabel(locale, drawer)}</h3>
                <p>Registered SECTION_OPEN / getUiProjection visual detail surface</p>
              </div>
              <button type="button" className={styles.close} aria-label="Close" onClick={() => setDrawer(null)}>×</button>
            </div>
            <div className={styles.drawerBody}>
              <div className={styles.drawerRow}>
                <span>Authorized read-model projection</span>
                <strong>—</strong>
              </div>
              <div className={styles.drawerRow}>
                <span>Current version / state</span>
                <strong>—</strong>
              </div>
              <div className={styles.drawerRow}>
                <span>Audit / Impact / Approval reference</span>
                <strong>—</strong>
              </div>
              <div className={styles.warning}>{qaCriteriaText(locale, "drawerEmpty")}</div>
            </div>
          </aside>
        </>
      )}
    </div>
  );
}
