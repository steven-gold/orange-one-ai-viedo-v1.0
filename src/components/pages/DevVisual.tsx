"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { devText, type DevTranslationKey } from "@/i18n/devCatalog";
import { DevGovernedButton, DevRuntimeProvider, useDevGate, useDevRuntimeState } from "./DevControlRuntime";
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


function ProjectionCell({ label, wide = false }: { label: string; wide?: boolean }) {
  return <div className={`${styles.projectionCell} ${wide ? styles.wideCell : ""}`}><span>{label}</span><strong>—</strong></div>;
}

function DevVisualBody() {
  const { locale } = useI18n();
  const { projection, runtimeError } = useDevRuntimeState();
  const discoveryRunning = useDevGate("DEV-01-GATE-DISCOVERY-RUNNING");
  const discoveryPaused = useDevGate("DEV-01-GATE-DISCOVERY-PAUSED");
  const mergePreviewAvailable = useDevGate("DEV-01-GATE-MERGE");
  const mergeConfirmAvailable = useDevGate("DEV-01-GATE-MERGE-CONFIRM");
  const candidateReviewAvailable = useDevGate("DEV-01-GATE-MESSAGE-REVIEW");
  const campaignApprovalAvailable = useDevGate("DEV-01-GATE-CAMPAIGN-APPROVAL");
  const approvedCampaignAvailable = useDevGate("DEV-01-GATE-DISPATCH");
  const killSwitchApplicable = useDevGate("DEV-01-GATE-KILL-SWITCH");
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
              <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-DISCOVERY-START">{t("start")}</DevGovernedButton>
              {discoveryRunning && <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-DISCOVERY-PAUSE">{t("pause")}</DevGovernedButton>}
              {discoveryPaused && <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-DISCOVERY-RESUME">{t("resume")}</DevGovernedButton>}
              {discoveryRunning && <DevGovernedButton className={styles.dangerButton} controlId="DEV-01-BTN-DISCOVERY-STOP">{t("stop")}</DevGovernedButton>}
            </>
          )}
          {key === "directory" && (
            <>
              <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-DIRECTORY-SEARCH">{t("searchCompany")}</DevGovernedButton>
              {mergePreviewAvailable && <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-MERGE-PREVIEW">{t("previewMerge")}</DevGovernedButton>}
              {mergeConfirmAvailable && <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-MERGE">{t("confirmMerge")}</DevGovernedButton>}
              <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-EXPORT">{t("export")}</DevGovernedButton>
            </>
          )}
          {key === "message" && (
            <>
              <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-CANDIDATE-CREATE">{t("createCandidate")}</DevGovernedButton>
              {candidateReviewAvailable && <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-CANDIDATE-DECIDE">{t("reviewCandidate")}</DevGovernedButton>}
              {candidateReviewAvailable && <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-CR-CREATE">{t("requestChange")}</DevGovernedButton>}
            </>
          )}
          {key === "campaign" && (
            <>
              <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-CAMPAIGN-SEARCH">{t("searchAudience")}</DevGovernedButton>
              <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-CAMPAIGN-CREATE">{t("createCampaign")}</DevGovernedButton>
              {campaignApprovalAvailable && <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-CAMPAIGN-APPROVE">{t("approveCampaign")}</DevGovernedButton>}
            </>
          )}
          {key === "delivery" && (
            <>
              {approvedCampaignAvailable && <DevGovernedButton className={styles.primaryButton} controlId="DEV-01-BTN-EMAIL-DISPATCH">{t("dispatch")}</DevGovernedButton>}
              <DevGovernedButton className={styles.button} controlId="DEV-01-BTN-REFRESH">{t("refresh")}</DevGovernedButton>
              {killSwitchApplicable && (
                <span data-component-id="DEV-01-CMP-KILL-SWITCH">
                  <DevGovernedButton className={styles.dangerButton} controlId="DEV-01-BTN-KILL-SWITCH">{t("killSwitch")}</DevGovernedButton>
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
        <p className={styles.phaseNote}>{runtimeError??projection?.page_state??t("noRealData")}</p>
      </aside>
    );
  }

  return (
    <div className={styles.page} data-page-uid="admin:DEV-01" data-vis-step="VIS-12" data-route-status="RESOLVED_USER_APPROVED_ADMIN_ROUTE" data-page-state={projection?.page_state??"READ_ONLY"}>
      <section className={styles.contextBar} data-section-id="DEV-01-SEC-01" data-component-id="DEV-01-CMP-CONTEXT">
        <div className={styles.contextIdentity}>
          <div className={styles.eyebrow}>DEV-01 · {t("pageName")}</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextStatus}>
          <div className={styles.statusCell}><span>{t("currentStage")}</span><strong>{t(stage.labelKey)}</strong></div>
          <div className={styles.statusCell}><span>{t("authorizedScope")}</span><strong>{projection?.authorized_scope??"—"}</strong></div>
          <div className={styles.statusCell}><span>{t("runStatus")}</span><strong>{runtimeError??projection?.run_status??"—"}</strong></div>
        </div>
      </section>

      <section className={styles.stageBar} data-section-id="DEV-01-SEC-02" data-component-id="DEV-01-CMP-STAGE-NAV" aria-label={t("pageName")}>
        {STAGES.map((item) => (
          <DevGovernedButton
            key={item.key}
            className={`${styles.stageButton} ${activeStage === item.key ? styles.stageButtonActive : ""}`}
            controlId={item.controlId}
            onUiClick={() => setActiveStage(item.key)}
          >
            {item.code} · {t(item.labelKey)}
          </DevGovernedButton>
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

export function DevVisual(){return <DevRuntimeProvider><DevVisualBody/></DevRuntimeProvider>}
