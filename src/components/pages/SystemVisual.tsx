"use client";

import { useEffect, useReducer, useState, type ReactNode } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { systemText } from "@/i18n/systemCatalog";
import { INITIAL_SYSTEM_CLIENT_STATE, reduceSystemClientState } from "@/domain/system/systemClientState";
import {
  SYS_AUTHORITY_STATUS,
  SYS_CURRENT_CONTROL_COUNT,
  SYS_IMPLEMENTATION_STATUS,
  SYS_SECTION_COUNT,
  getSystemControlTrace,
} from "@/domain/system/systemRuntimeContract";
import { readSystemProjection } from "@/domain/system/systemProjectionPort";
import styles from "./SystemVisual.module.css";

const DASH = "—";

type ProjectionState =
  | { status: "LOADING"; reason_code: null; correlation_id: null }
  | { status: "READY"; reason_code: null; correlation_id: string | null }
  | { status: "BLOCKED"; reason_code: string; correlation_id: string | null };

function DataRow({ label, value = DASH }: { label: string; value?: string }) {
  return (
    <div className={styles.dataRow}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Section({ id, title, children, className = "" }: { id: string; title: string; children: ReactNode; className?: string }) {
  return (
    <section className={`${styles.panel} ${className}`} data-section-id={id}>
      <div className={styles.panelHeader}>
        <h2>{title}</h2>
        <span className={styles.statusDot} aria-hidden="true" />
      </div>
      {children}
    </section>
  );
}

function controlTraceProps(control_uid: string) {
  const trace = getSystemControlTrace(control_uid);
  return {
    "data-control-id": trace.control_uid,
    "data-action-uid": trace.action_uid,
    "data-gate-uid": trace.gate_uid ?? undefined,
    "data-permission-uid": trace.permission_uid,
    "data-runtime-binding": trace.runtime_binding ?? (trace.service_operation ? "NOT_EXECUTED" : "NOT_BOUND"),
    "data-service-operation": trace.service_operation ?? undefined,
    "data-enabled-in-visual-phase": trace.enabled_in_visual_phase ? "true" : "false",
  };
}

export function SystemVisual() {
  const { locale } = useI18n();
  const t = (key: Parameters<typeof systemText>[1]) => systemText(locale, key);
  const [state, dispatch] = useReducer(reduceSystemClientState, INITIAL_SYSTEM_CLIENT_STATE);
  const [projection, setProjection] = useState<ProjectionState>({ status: "LOADING", reason_code: null, correlation_id: null });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void readSystemProjection(controller.signal).then((result) => {
      if (!active) return;
      if (result.ok) {
        setProjection({ status: "READY", reason_code: null, correlation_id: result.correlation_id });
        return;
      }
      setProjection({ status: "BLOCKED", reason_code: result.reason_code, correlation_id: result.correlation_id });
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  const multi = state.ai_mode === "MULTI_AI";
  const systemContextResolved = projection.status === "READY" && Boolean(state.system_change_id);
  const activeConversationContextResolved = systemContextResolved && Boolean(state.conversation_id);
  const modeGateReady = systemContextResolved && activeConversationContextResolved;
  const multiAiRouteReady = false;
  const multiAiGateReady = modeGateReady && multiAiRouteReady;
  const councilGateReady = multi && multiAiGateReady;
  const projectionReason = projection.reason_code ?? (projection.status === "READY" ? "READY" : "LOADING");

  return (
    <div
      className={styles.page}
      data-page-uid="admin:SYS-01"
      data-vis-step="VIS-10"
      data-page-state="EMPTY"
      data-ai-mode={state.ai_mode}
      data-council-mode={state.council_mode}
      data-authority-status={SYS_AUTHORITY_STATUS}
      data-authority-sections={SYS_SECTION_COUNT}
      data-authority-controls={SYS_CURRENT_CONTROL_COUNT}
      data-implementation-status={SYS_IMPLEMENTATION_STATUS}
      data-projection-status={projection.status}
      data-projection-reason={projection.reason_code ?? undefined}
      data-correlation-id={projection.correlation_id ?? undefined}
      data-system-context-resolved={String(systemContextResolved)}
      data-active-conversation-context-resolved={String(activeConversationContextResolved)}
      data-mode-gate-ready={String(modeGateReady)}
      data-multi-ai-route-ready={String(multiAiRouteReady)}
      data-effectful-runtime-ready="false"
    >
      <header className={styles.contextBar}>
        <div>
          <div className={styles.eyebrow}>SYS-01 · SYSTEM LIFECYCLE AI</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextMeta}>
          <span>SYSTEM_CHANGE_ID</span>
          <strong>{state.system_change_id ?? DASH}</strong>
        </div>
      </header>

      <div className={styles.primaryGrid}>
        <Section id="SEC-ADMIN-SYS-01-SYSTEM-CONTEXT" title={t("systemContext")}>
          <div className={styles.subheading}>{t("currentTruth")}</div>
          <DataRow label={t("systemVersion")} />
          <DataRow label={t("authority")} value={SYS_AUTHORITY_STATUS} />
          <DataRow label={t("services")} value={SYS_IMPLEMENTATION_STATUS} />
          <DataRow label={t("runtime")} value={projectionReason} />
          <div className={styles.divider} />
          <div className={styles.subheading}>{t("activeChange")}</div>
          <DataRow label={t("systemChangeId")} value={state.system_change_id ?? DASH} />
          <DataRow label={t("goal")} />
          <DataRow label={t("scope")} />
          <DataRow label={t("candidateRef")} />
        </Section>

        <Section id="SEC-ADMIN-SYS-01-CONVERSATION" title={t("conversation")} className={styles.conversationPanel}>
          <div className={styles.modeHeader} data-component-uid="SYS-01-CMP-DESIGN-CONVERSATION-HEADER" data-visual-uid="SYS-01-VIS-DESIGN-CONVERSATION-HEADER">
            <div className={styles.segmentGroup} aria-label="AI Mode">
              <button
                id="SYS-01-BTN-SINGLE-AI"
                {...controlTraceProps("SYS-01-BTN-SINGLE-AI")}
                className={`${styles.segment} ${!multi ? styles.segmentActive : ""}`}
                type="button"
                aria-pressed={!multi}
                disabled={!modeGateReady}
                data-current-gate-ready={String(modeGateReady)}
                data-blocked-error-uid={!modeGateReady ? "SYS-01-ERR-AI-MODE-CONTEXT" : undefined}
                onClick={() => dispatch({ type: "AI_MODE_SINGLE" })}
              >
                {t("singleAi")}
              </button>
              <button
                id="SYS-01-BTN-MULTI-AI"
                {...controlTraceProps("SYS-01-BTN-MULTI-AI")}
                className={`${styles.segment} ${multi ? styles.segmentActive : ""}`}
                type="button"
                aria-pressed={multi}
                disabled={!multiAiGateReady}
                data-current-gate-ready={String(multiAiGateReady)}
                data-blocked-error-uid={!modeGateReady ? "SYS-01-ERR-AI-MODE-CONTEXT" : !multiAiRouteReady ? "SYS-01-ERR-MULTI-AI-ROUTE" : undefined}
                onClick={() => dispatch({ type: "AI_MODE_MULTI" })}
              >
                {t("multiAi")}
              </button>
            </div>
            <div className={styles.segmentGroup} aria-label="Council Mode" hidden={!multi}>
              <button
                id="SYS-01-BTN-COUNCIL-DISCUSSION"
                {...controlTraceProps("SYS-01-BTN-COUNCIL-DISCUSSION")}
                className={`${styles.segment} ${state.council_mode === "DISCUSSION" ? styles.segmentActive : ""}`}
                type="button"
                aria-pressed={state.council_mode === "DISCUSSION"}
                disabled={!councilGateReady}
                data-current-gate-ready={String(councilGateReady)}
                data-blocked-error-uid={!councilGateReady ? "SYS-01-ERR-COUNCIL-MODE" : undefined}
                onClick={() => dispatch({ type: "COUNCIL_DISCUSSION" })}
              >
                {t("discussion")}
              </button>
              <button
                id="SYS-01-BTN-COUNCIL-PARALLEL"
                {...controlTraceProps("SYS-01-BTN-COUNCIL-PARALLEL")}
                className={`${styles.segment} ${state.council_mode === "PARALLEL" ? styles.segmentActive : ""}`}
                type="button"
                aria-pressed={state.council_mode === "PARALLEL"}
                disabled={!councilGateReady}
                data-current-gate-ready={String(councilGateReady)}
                data-blocked-error-uid={!councilGateReady ? "SYS-01-ERR-COUNCIL-MODE" : undefined}
                onClick={() => dispatch({ type: "COUNCIL_PARALLEL" })}
              >
                {t("parallel")}
              </button>
            </div>
          </div>

          <div className={styles.conversationBody}>
            <div className={styles.assistantBadge}>{t("assistant")}</div>
            <div className={styles.emptyConversation}>
              <div className={styles.emptyGlyph}>◇</div>
              <strong>{t("noData")}</strong>
              <p>{t("emptyConversation")}</p>
            </div>
          </div>
          <div className={styles.contextStrip}>
            <DataRow label="conversation_id" value={state.conversation_id ?? DASH} />
            <DataRow label="thread_id" value={state.thread_id ?? DASH} />
            <DataRow label="branch_id" value={state.branch_id ?? DASH} />
            <DataRow label="context_snapshot_ref" />
          </div>

          <div className={styles.composer} data-component-uid="SYS-01-CMP-CONVERSATION-COMPOSER" data-visual-uid="SYS-01-VIS-CONVERSATION-COMPOSER">
            <textarea
              id="SYS-01-INP-MESSAGE"
              {...controlTraceProps("SYS-01-INP-MESSAGE")}
              className={styles.composerInput}
              aria-label={t("messageInput")}
              placeholder={t("messagePlaceholder")}
              rows={3}
              value={state.draft}
              onChange={(event) => dispatch({ type: "DRAFT", value: event.target.value })}
            />
            <div className={styles.composerActions}>
              <button id="SYS-01-BTN-ATTACH" {...controlTraceProps("SYS-01-BTN-ATTACH")} className={styles.composerButton} type="button" disabled>
                {t("attach")}
              </button>
              <button id="SYS-01-BTN-STOP" {...controlTraceProps("SYS-01-BTN-STOP")} className={styles.composerButton} type="button" disabled>
                {t("stop")}
              </button>
              <button id="SYS-01-BTN-SEND" {...controlTraceProps("SYS-01-BTN-SEND")} className={`${styles.composerButton} ${styles.composerSend}`} type="button" disabled>
                {t("send")}
              </button>
            </div>
          </div>
        </Section>
      </div>

      <div className={styles.secondaryGrid}>
        <Section id="SEC-ADMIN-SYS-01-CANDIDATE-CHANGE" title={t("candidateChange")}>
          <DataRow label="requirement" />
          <DataRow label="decision" />
          <DataRow label="design" />
          <DataRow label="authority_changes" />
          <DataRow label="implementation" />
        </Section>
        <Section id="SEC-ADMIN-SYS-01-SOURCE-REFS" title={t("sourceRefs")}>
          <div className={styles.referenceBox}>
            <span>{t("sourceTypes")}</span>
            <strong>{state.selected_reference_ref ?? DASH}</strong>
          </div>
          <button
            id="SYS-01-BTN-NAV-OPEN"
            {...controlTraceProps("SYS-01-BTN-NAV-OPEN")}
            data-component-uid="SYS-01-CMP-SOURCE-REFS"
            data-visual-uid="SYS-01-VIS-SOURCE-REFS"
            className={styles.secondaryButton}
            type="button"
            disabled
          >
            {t("openReference")}
          </button>
        </Section>
        <Section id="SEC-ADMIN-SYS-01-IMPACT-PREVIEW" title={t("impactPreview")}>
          <div className={styles.referenceBox}>
            <span>{t("affectedTypes")}</span>
            <strong>{DASH}</strong>
          </div>
          <DataRow label="dependency_graph_ref" />
          <DataRow label="latest_context_fingerprint" />
        </Section>
      </div>

      <div className={styles.bottomGrid}>
        <Section id="SEC-ADMIN-SYS-01-AUDIT" title={t("audit")}>
          <div className={styles.referenceBox}>
            <span>{t("auditTrail")}</span>
            <strong>{DASH}</strong>
          </div>
          <DataRow label="confirmed_decision_refs" />
          <DataRow label="unresolved_failure_refs" />
        </Section>
        <Section id="SEC-ADMIN-SYS-01-ACTION-DOCK" title={t("actionDock")}>
          <div className={styles.actionRow} data-component-uid="SYS-01-CMP-ACTION-DOCK" data-visual-uid="SYS-01-VIS-ACTION-DOCK">
            <button id="SYS-01-BTN-CANDIDATE-CREATE" {...controlTraceProps("SYS-01-BTN-CANDIDATE-CREATE")} className={styles.primaryButton} type="button" disabled>
              {t("candidateCreate")}
            </button>
            <button id="SYS-01-BTN-CR-CREATE" {...controlTraceProps("SYS-01-BTN-CR-CREATE")} className={styles.secondaryButton} type="button" disabled>
              {t("changeRequestCreate")}
            </button>
          </div>
          <p className={styles.phaseNote}>{t("disabledVisual")}</p>
        </Section>
        <Section id="SEC-ADMIN-SYS-01-EXECUTION-PANEL" title={t("executionPanel")}>
          <div className={styles.executionLine} data-component-uid="SYS-01-CMP-EXECUTION-PANEL" data-visual-uid="SYS-01-VIS-EXECUTION-PANEL">
            <div>
              <span>{t("validation")}</span>
              <strong>{DASH}</strong>
            </div>
            <button id="SYS-01-BTN-SANDBOX-TEST" {...controlTraceProps("SYS-01-BTN-SANDBOX-TEST")} className={styles.secondaryButton} type="button" disabled>
              {t("sandboxTest")}
            </button>
          </div>
          <p className={styles.phaseNote}>{t("disabledVisual")}</p>
        </Section>
      </div>
    </div>
  );
}
