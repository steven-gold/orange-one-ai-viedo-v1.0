"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { devText, type DevTranslationKey } from "@/i18n/devCatalog";
import styles from "./DevVisual.module.css";

type StageKey = "discovery" | "directory" | "message" | "campaign" | "delivery";

type StageDefinition = {
  key: StageKey;
  controlId: string;
  labelKey: DevTranslationKey;
  code: string;
};

const STAGES: readonly StageDefinition[] = [
  { key: "discovery", controlId: "DEV-01-BTN-STAGE-1", labelKey: "discovery", code: "01" },
  { key: "directory", controlId: "DEV-01-BTN-STAGE-2", labelKey: "directory", code: "02" },
  { key: "message", controlId: "DEV-01-BTN-STAGE-3", labelKey: "message", code: "03" },
  { key: "campaign", controlId: "DEV-01-BTN-STAGE-4", labelKey: "campaign", code: "04" },
  { key: "delivery", controlId: "DEV-01-BTN-STAGE-5", labelKey: "delivery", code: "05" },
] as const;

const EMPTY_VISUAL_STATE = {
  discoveryRunning: false,
  discoveryPaused: false,
  mergePreviewAvailable: false,
  mergeConfirmAvailable: false,
  candidateReviewAvailable: false,
  campaignApprovalAvailable: false,
  approvedCampaignAvailable: false,
  killSwitchApplicable: false,
} as const;

function ProjectionCell({ label, wide = false }: { label: string; wide?: boolean }) {
  return <div className={`${styles.projectionCell} ${wide ? styles.wideCell : ""}`}><span>{label}</span><strong>—</strong></div>;
}

export function DevVisual() {
  const { locale } = useI18n();
  const [activeStage, setActiveStage] = useState<StageKey>("discovery");
  const t = (key: DevTranslationKey) => devText(locale, key);
  const stage = STAGES.find((item) => item.key === activeStage) ?? STAGES[0];

  function renderActionDock(key: StageKey) {
    return (
      <div className={styles.actionDock} data-component-id={key === "discovery" ? "DEV-01-CMP-DISCOVERY-ACTION" : undefined}>
        <div className={styles.dockLabel}><span>{t("currentStage")}</span><strong>{t(stage.labelKey)}</strong></div>
        <div className={styles.dockActions}>
          {key === "discovery" && (
            <>
              <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-DISCOVERY-START" disabled>{t("start")}</button>
              {EMPTY_VISUAL_STATE.discoveryRunning && <button className={styles.button} type="button" data-control-id="DEV-01-BTN-DISCOVERY-PAUSE" disabled>{t("pause")}</button>}
              {EMPTY_VISUAL_STATE.discoveryPaused && <button className={styles.button} type="button" data-control-id="DEV-01-BTN-DISCOVERY-RESUME" disabled>{t("resume")}</button>}
              {EMPTY_VISUAL_STATE.discoveryRunning && <button className={styles.dangerButton} type="button" data-control-id="DEV-01-BTN-DISCOVERY-STOP" disabled>{t("stop")}</button>}
            </>
          )}
          {key === "directory" && (
            <>
              <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-DIRECTORY-SEARCH" disabled>{t("searchCompany")}</button>
              {EMPTY_VISUAL_STATE.mergePreviewAvailable && <button className={styles.button} type="button" data-control-id="DEV-01-BTN-MERGE-PREVIEW" disabled>{t("previewMerge")}</button>}
              {EMPTY_VISUAL_STATE.mergeConfirmAvailable && <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-MERGE" disabled>{t("confirmMerge")}</button>}
              <button className={styles.button} type="button" data-control-id="DEV-01-BTN-EXPORT" disabled>{t("export")}</button>
            </>
          )}
          {key === "message" && (
            <>
              <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-CANDIDATE-CREATE" disabled>{t("createCandidate")}</button>
              {EMPTY_VISUAL_STATE.candidateReviewAvailable && <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-CANDIDATE-DECIDE" disabled>{t("reviewCandidate")}</button>}
              {EMPTY_VISUAL_STATE.candidateReviewAvailable && <button className={styles.button} type="button" data-control-id="DEV-01-BTN-CR-CREATE" disabled>{t("requestChange")}</button>}
            </>
          )}
          {key === "campaign" && (
            <>
              <button className={styles.button} type="button" data-control-id="DEV-01-BTN-CAMPAIGN-SEARCH" disabled>{t("searchAudience")}</button>
              <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-CAMPAIGN-CREATE" disabled>{t("createCampaign")}</button>
              {EMPTY_VISUAL_STATE.campaignApprovalAvailable && <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-CAMPAIGN-APPROVE" disabled>{t("approveCampaign")}</button>}
            </>
          )}
          {key === "delivery" && (
            <>
              {EMPTY_VISUAL_STATE.approvedCampaignAvailable && <button className={styles.primaryButton} type="button" data-control-id="DEV-01-BTN-EMAIL-DISPATCH" disabled>{t("dispatch")}</button>}
              <button className={styles.button} type="button" data-control-id="DEV-01-BTN-REFRESH" disabled>{t("refresh")}</button>
              {EMPTY_VISUAL_STATE.killSwitchApplicable && (
                <span data-component-id="DEV-01-CMP-KILL-SWITCH">
                  <button className={styles.dangerButton} type="button" data-control-id="DEV-01-BTN-KILL-SWITCH" disabled>{t("killSwitch")}</button>
                </span>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  function renderStageWorkspace() {
    if (activeStage === "discovery") {
      return (
        <section className={styles.panel} data-section-id="DEV-01-SEC-03" data-component-id="DEV-01-CMP-DISCOVERY-SETUP">
          <div className={styles.panelHeader}><h2>{t("discoverySetup")}</h2><span>{stage.code} · {t("currentStage")}</span></div>
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
          <div className={styles.panelHeader}><h2>{t("companyList")}</h2><span>{stage.code} · {t("currentStage")}</span></div>
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
          <div className={styles.panelHeader}><h2>{t("messageCandidate")}</h2><span>{stage.code} · {t("currentStage")}</span></div>
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
          <div className={styles.panelHeader}><h2>{t("campaign")}</h2><span>{stage.code} · {t("currentStage")}</span></div>
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
        <div className={styles.panelHeader}><h2>{t("delivery")}</h2><span>{stage.code} · {t("currentStage")}</span></div>
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
  }

  function renderGovernance() {
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
  }

  return (
    <div className={styles.page} data-page-uid="admin:DEV-01" data-vis-step="VIS-12" data-route-status="RESOLVED_USER_APPROVED_ADMIN_ROUTE" data-page-state="VISUAL_ONLY_NO_BUSINESS_DATA">
      <section className={styles.contextBar} data-section-id="DEV-01-SEC-01" data-component-id="DEV-01-CMP-CONTEXT">
        <div className={styles.contextIdentity}>
          <div className={styles.eyebrow}>DEV-01 · {t("pageName")}</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextStatus}>
          <div className={styles.statusCell}><span>{t("currentStage")}</span><strong>{t(stage.labelKey)}</strong></div>
          <div className={styles.statusCell}><span>{t("authorizedScope")}</span><strong>—</strong></div>
          <div className={styles.statusCell}><span>{t("runStatus")}</span><strong>—</strong></div>
        </div>
      </section>

      <section className={styles.stageBar} data-section-id="DEV-01-SEC-02" data-component-id="DEV-01-CMP-STAGE-NAV" aria-label={t("pageName")}>
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
          <div className={styles.drawerCell}><span>{t("evidence")}</span><strong>—</strong></div>
          <div className={styles.drawerCell}><span>{t("audit")}</span><strong>—</strong></div>
          <div className={styles.drawerCell}><span>{t("version")}</span><strong>—</strong></div>
          <div className={styles.drawerCell}><span>{t("errorCorrelation")}</span><strong>—</strong></div>
        </div>
      </aside>
    </div>
  );
}
