"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { devText, type DevTranslationKey } from "@/i18n/devCatalog";
import styles from "./DevVisual.module.css";

type StageKey = "discovery" | "directory" | "message" | "campaign" | "delivery";

type StageDefinition = {
  key: StageKey;
  controlId: string;
  sectionId: string;
  labelKey: DevTranslationKey;
  code: string;
};

const STAGES: readonly StageDefinition[] = [
  { key: "discovery", controlId: "DEV-01-BTN-STAGE-1", sectionId: "DEV-01-SEC-03", labelKey: "discovery", code: "01" },
  { key: "directory", controlId: "DEV-01-BTN-STAGE-2", sectionId: "DEV-01-SEC-04", labelKey: "directory", code: "02" },
  { key: "message", controlId: "DEV-01-BTN-STAGE-3", sectionId: "DEV-01-SEC-05", labelKey: "message", code: "03" },
  { key: "campaign", controlId: "DEV-01-BTN-STAGE-4", sectionId: "DEV-01-SEC-06", labelKey: "campaign", code: "04" },
  { key: "delivery", controlId: "DEV-01-BTN-STAGE-5", sectionId: "DEV-01-SEC-07", labelKey: "delivery", code: "05" },
] as const;

function ProjectionCell({ label, wide = false }: { label: string; wide?: boolean }) {
  return <div className={`${styles.projectionCell} ${wide ? styles.wideCell : ""}`}><span>{label}</span><strong>—</strong></div>;
}

export function DevVisual() {
  const { locale } = useI18n();
  const [activeStage, setActiveStage] = useState<StageKey>("discovery");
  const t = (key: DevTranslationKey) => devText(locale, key);
  const stage = STAGES.find((item) => item.key === activeStage) ?? STAGES[0];

  const renderStageWorkspace = () => {
    if (activeStage === "discovery") {
      return (
        <section className={styles.panel} data-section-id="DEV-01-SEC-03" data-component-id="DEV-01-CMP-DISCOVERY-SETUP">
          <div className={styles.panelHeader}><h2>{t("discoverySetup")}</h2><span>DISCOVERY · CURRENT STAGE</span></div>
          <div className={styles.workspaceBody}>
            <div className={styles.projectionGrid}>
              <ProjectionCell label={t("mode")} />
              <ProjectionCell label={t("searchScope")} />
              <ProjectionCell label={t("allowedSources")} wide />
            </div>
            <div className={styles.schemaBlock}>{t("exactSchemaOnly")}</div>
            <div className={styles.emptyBlock} data-component-id="DEV-01-CMP-DISCOVERY-RUNTIME"><strong>{t("discoveryRuntime")}</strong><span>{t("noRealData")}</span></div>
          </div>
          {renderActionDock("discovery")}
        </section>
      );
    }

    if (activeStage === "directory") {
      return (
        <section className={styles.panel} data-section-id="DEV-01-SEC-04" data-component-id="DEV-01-CMP-DIRECTORY">
          <div className={styles.panelHeader}><h2>{t("companyList")}</h2><span>DIRECTORY · CURRENT STAGE</span></div>
          <div className={styles.workspaceBody}>
            <div className={styles.projectionGrid}>
              <ProjectionCell label={t("directorySearch")} wide />
              <ProjectionCell label={t("registrationIdentity")} />
              <ProjectionCell label={t("aliasesContacts")} />
              <ProjectionCell label={t("mergeReview")} />
              <ProjectionCell label={t("deliveryHistory")} />
            </div>
            <div className={styles.emptyBlock}><strong>{t("companyList")}</strong><span>{t("noRealData")}</span></div>
            <div className={styles.schemaBlock} data-component-id="DEV-01-CMP-MERGE">{t("exactSchemaOnly")}</div>
          </div>
          {renderActionDock("directory")}
        </section>
      );
    }

    if (activeStage === "message") {
      return (
        <section className={styles.panel} data-section-id="DEV-01-SEC-05" data-component-id="DEV-01-CMP-MESSAGE">
          <div className={styles.panelHeader}><h2>{t("messageCandidate")}</h2><span>MESSAGE · CURRENT STAGE</span></div>
          <div className={styles.workspaceBody}>
            <div className={styles.projectionGrid}>
              <ProjectionCell label={t("audienceContext")} wide />
              <ProjectionCell label={t("personalization")} />
              <ProjectionCell label={t("policyCheck")} />
              <ProjectionCell label={t("humanReview")} />
              <ProjectionCell label={t("versionAudit")} />
            </div>
            <div className={styles.emptyBlock} data-component-id="DEV-01-CMP-MESSAGE-REVIEW"><strong>{t("messageCandidate")}</strong><span>{t("noRealData")}</span></div>
            <div className={styles.boundaryBlock}>{t("messageNoSend")}</div>
          </div>
          {renderActionDock("message")}
        </section>
      );
    }

    if (activeStage === "campaign") {
      return (
        <section className={styles.panel} data-section-id="DEV-01-SEC-06" data-component-id="DEV-01-CMP-CAMPAIGN">
          <div className={styles.panelHeader}><h2>{t("campaign")}</h2><span>CAMPAIGN · CURRENT STAGE</span></div>
          <div className={styles.workspaceBody}>
            <div className={styles.projectionGrid}>
              <ProjectionCell label={t("audienceFilter")} />
              <ProjectionCell label={t("recipientPreview")} />
              <ProjectionCell label={t("campaignConfig")} />
              <ProjectionCell label={t("approval")} />
            </div>
            <div className={styles.emptyBlock} data-component-id="DEV-01-CMP-CAMPAIGN-REVIEW"><strong>{t("recipientPreview")}</strong><span>{t("noRealData")}</span></div>
            <div className={styles.boundaryBlock}>{t("campaignBoundary")}</div>
          </div>
          {renderActionDock("campaign")}
        </section>
      );
    }

    return (
      <section className={styles.panel} data-section-id="DEV-01-SEC-07" data-component-id="DEV-01-CMP-DELIVERY">
        <div className={styles.panelHeader}><h2>{t("delivery")}</h2><span>DELIVERY · CURRENT STAGE</span></div>
        <div className={styles.workspaceBody}>
          <div className={styles.projectionGrid}>
            <ProjectionCell label={t("deliveryPolicy")} />
            <ProjectionCell label={t("rateQuota")} />
            <ProjectionCell label={t("deliveryQueue")} />
            <ProjectionCell label={t("bounceReply")} />
          </div>
          <div className={styles.emptyBlock}><strong>{t("deliveryQueue")}</strong><span>{t("noRealData")}</span></div>
          <div className={styles.boundaryBlock}>{t("oneRecipient")}</div>
        </div>
        {renderActionDock("delivery")}
      </section>
    );
  };

  const renderGovernance = () => {
    const stageSpecific = activeStage === "discovery" ? t("connectorHealth") : activeStage === "campaign" || activeStage === "delivery" ? t("approvalState") : t("policyGate");
    return (
      <aside className={styles.rail} data-section-id="DEV-01-SEC-08" data-component-id="DEV-01-CMP-GOVERNANCE">
        <div className={styles.railHeader}><h2>{t("governance")}</h2><span>{stage.code}</span></div>
        <div className={styles.railList}>
          <div className={styles.railItem}><span>{t("permissionGate")}</span><strong>—</strong></div>
          <div className={styles.railItem}><span>{t("policyGate")}</span><strong>—</strong></div>
          <div className={styles.railItem}><span>{stageSpecific}</span><strong>—</strong></div>
          <div className={styles.railItem}><span>{t("blockerStatus")}</span><strong>—</strong></div>
        </div>
        <p className={styles.railNote}>{t("noRealData")}</p>
        <p className={styles.phaseNote}>{t("visualPhase")}</p>
      </aside>
    );
  };

  function renderActionDock(key: StageKey) {
    return (
      <div className={styles.actionDock} data-component-id={key === "discovery" ? "DEV-01-CMP-DISCOVERY-ACTION" : undefined}>
        <div className={styles.dockLabel}><span>STAGE ACTION DOCK</span><strong>{t(stage.labelKey)}</strong></div>
        <div className={styles.dockActions}>
          {key === "discovery" && <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-DISCOVERY-START" disabled>{t("start")}</button>}
          {key === "directory" && <><button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-DIRECTORY-SEARCH" disabled>{t("searchCompany")}</button><button className={styles.button} type="button" data-control-id="DEV-01-BTN-EXPORT" disabled>{t("export")}</button></>}
          {key === "message" && <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-CANDIDATE-CREATE" disabled>{t("createCandidate")}</button>}
          {key === "campaign" && <><button className={styles.button} type="button" data-control-id="DEV-01-BTN-CAMPAIGN-SEARCH" disabled>{t("searchAudience")}</button><button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-CAMPAIGN-CREATE" disabled>{t("createCampaign")}</button></>}
          {key === "delivery" && <button className={styles.button} type="button" data-control-id="DEV-01-BTN-REFRESH" disabled>{t("refresh")}</button>}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page} data-page-uid="admin:DEV-01" data-vis-step="VIS-12" data-route-status="BLOCKED_AUTHORITY_GAP" data-page-state="VISUAL_ONLY_NO_BUSINESS_DATA">
      <section className={styles.contextBar} data-section-id="DEV-01-SEC-01" data-component-id="DEV-01-CMP-CONTEXT">
        <div className={styles.contextIdentity}>
          <div className={styles.eyebrow}>DEV-01 · ENTERPRISE AUTOMATION</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextStatus}>
          <div className={styles.statusCell}><span>{t("currentStage")}</span><strong>{t(stage.labelKey)}</strong></div>
          <div className={styles.statusCell}><span>{t("authorizedScope")}</span><strong>—</strong></div>
          <div className={styles.statusCell}><span>{t("runStatus")}</span><strong>—</strong></div>
        </div>
      </section>

      <section className={styles.stageBar} data-section-id="DEV-01-SEC-02" data-component-id="DEV-01-CMP-STAGE-NAV" aria-label="Enterprise Automation Workflow">
        {STAGES.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`${styles.stageButton} ${activeStage === item.key ? styles.stageButtonActive : ""}`}
            data-control-id={item.controlId}
            aria-pressed={activeStage === item.key}
            onClick={() => setActiveStage(item.key)}
          >
            {item.code} · {t(item.labelKey)}
          </button>
        ))}
      </section>

      <div className={styles.workspaceGrid}>
        <main className={styles.mainWorkspace}>{renderStageWorkspace()}</main>
        {renderGovernance()}
      </div>

      <aside className={styles.detailDrawer} aria-hidden="true" data-section-id="DEV-01-SEC-09" data-component-id="DEV-01-CMP-DETAIL-DRAWER" data-state="CLOSED_EMPTY">
        <h2>{t("detailDrawer")}</h2>
        <p>{t("noRealData")}</p>
        <div className={styles.drawerGrid}>
          <div className={styles.drawerCell}><span>Evidence</span><strong>—</strong></div>
          <div className={styles.drawerCell}><span>Audit</span><strong>—</strong></div>
          <div className={styles.drawerCell}><span>Version</span><strong>—</strong></div>
          <div className={styles.drawerCell}><span>Error / Correlation</span><strong>—</strong></div>
        </div>
      </aside>
    </div>
  );
}
