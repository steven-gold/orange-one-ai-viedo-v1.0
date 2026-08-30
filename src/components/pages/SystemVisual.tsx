"use client";

import { useI18n } from "@/i18n/LocaleProvider";
import { systemText } from "@/i18n/systemCatalog";
import styles from "./SystemVisual.module.css";

const DASH = "—";

function DataRow({ label, value = DASH }: { label: string; value?: string }) {
  return (
    <div className={styles.dataRow}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Section({ id, title, children, className = "" }: { id: string; title: string; children: React.ReactNode; className?: string }) {
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

export function SystemVisual() {
  const { locale } = useI18n();
  const t = (key: Parameters<typeof systemText>[1]) => systemText(locale, key);

  return (
    <div className={styles.page} data-page-uid="admin:SYS-01" data-vis-step="VIS-10" data-page-state="EMPTY">
      <header className={styles.contextBar}>
        <div>
          <div className={styles.eyebrow}>SYS-01 · SYSTEM LIFECYCLE AI</div>
          <h1>{t("pageName")}</h1>
          <p>{t("pageRole")}</p>
        </div>
        <div className={styles.contextMeta}>
          <span>SYSTEM_CHANGE_ID</span>
          <strong>{DASH}</strong>
        </div>
      </header>

      <div className={styles.primaryGrid}>
        <Section id="SEC-ADMIN-SYS-01-SYSTEM-CONTEXT" title={t("systemContext")}>
          <div className={styles.subheading}>{t("currentTruth")}</div>
          <DataRow label={t("systemVersion")} />
          <DataRow label={t("authority")} />
          <DataRow label={t("services")} />
          <DataRow label={t("runtime")} />
          <div className={styles.divider} />
          <div className={styles.subheading}>{t("activeChange")}</div>
          <DataRow label={t("systemChangeId")} />
          <DataRow label={t("goal")} />
          <DataRow label={t("scope")} />
          <DataRow label={t("candidateRef")} />
        </Section>

        <Section id="SEC-ADMIN-SYS-01-CONVERSATION" title={t("conversation")} className={styles.conversationPanel}>
          <div className={styles.modeHeader} data-component-uid="SYS-01-CMP-DESIGN-CONVERSATION-HEADER" data-visual-uid="SYS-01-VIS-DESIGN-CONVERSATION-HEADER">
            <div className={styles.segmentGroup} aria-label="AI Mode">
              <button id="SYS-01-BTN-SINGLE-AI" data-control-id="SYS-01-BTN-SINGLE-AI" className={`${styles.segment} ${styles.segmentActive}`} type="button" aria-pressed="true" disabled>{t("singleAi")}</button>
              <button id="SYS-01-BTN-MULTI-AI" data-control-id="SYS-01-BTN-MULTI-AI" className={styles.segment} type="button" aria-pressed="false" disabled>{t("multiAi")}</button>
            </div>
            <div className={styles.segmentGroup} aria-label="Council Mode" hidden>
              <button id="SYS-01-BTN-COUNCIL-DISCUSSION" data-control-id="SYS-01-BTN-COUNCIL-DISCUSSION" className={`${styles.segment} ${styles.segmentActive}`} type="button" aria-pressed="true" disabled>{t("discussion")}</button>
              <button id="SYS-01-BTN-COUNCIL-PARALLEL" data-control-id="SYS-01-BTN-COUNCIL-PARALLEL" className={styles.segment} type="button" aria-pressed="false" disabled>{t("parallel")}</button>
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
            <DataRow label="conversation_id" />
            <DataRow label="thread_id" />
            <DataRow label="branch_id" />
            <DataRow label="context_snapshot_ref" />
          </div>

          <div
            className={styles.composer}
            data-component-uid="SYS-01-CMP-CONVERSATION-COMPOSER"
            data-visual-uid="SYS-01-VIS-CONVERSATION-COMPOSER"
          >
            <textarea
              id="SYS-01-INP-MESSAGE"
              data-control-id="SYS-01-INP-MESSAGE"
              className={styles.composerInput}
              aria-label={t("messageInput")}
              placeholder={t("messagePlaceholder")}
              rows={3}
            />
            <div className={styles.composerActions}>
              <button id="SYS-01-BTN-ATTACH" data-control-id="SYS-01-BTN-ATTACH" className={styles.composerButton} type="button" disabled>{t("attach")}</button>
              <button id="SYS-01-BTN-STOP" data-control-id="SYS-01-BTN-STOP" className={styles.composerButton} type="button" disabled>{t("stop")}</button>
              <button id="SYS-01-BTN-SEND" data-control-id="SYS-01-BTN-SEND" className={`${styles.composerButton} ${styles.composerSend}`} type="button" disabled>{t("send")}</button>
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
            <strong>{DASH}</strong>
          </div>
          <button
            id="SYS-01-BTN-NAV-OPEN"
            data-control-id="SYS-01-BTN-NAV-OPEN"
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
            <button id="SYS-01-BTN-CANDIDATE-CREATE" data-control-id="SYS-01-BTN-CANDIDATE-CREATE" className={styles.primaryButton} type="button" disabled>{t("candidateCreate")}</button>
            <button id="SYS-01-BTN-CR-CREATE" data-control-id="SYS-01-BTN-CR-CREATE" className={styles.secondaryButton} type="button" disabled>{t("changeRequestCreate")}</button>
          </div>
          <p className={styles.phaseNote}>{t("disabledVisual")}</p>
        </Section>

        <Section id="SEC-ADMIN-SYS-01-EXECUTION-PANEL" title={t("executionPanel")}>
          <div className={styles.executionLine} data-component-uid="SYS-01-CMP-EXECUTION-PANEL" data-visual-uid="SYS-01-VIS-EXECUTION-PANEL">
            <div>
              <span>{t("validation")}</span>
              <strong>{DASH}</strong>
            </div>
            <button id="SYS-01-BTN-SANDBOX-TEST" data-control-id="SYS-01-BTN-SANDBOX-TEST" className={styles.secondaryButton} type="button" disabled>{t("sandboxTest")}</button>
          </div>
          <p className={styles.phaseNote}>{t("disabledVisual")}</p>
        </Section>
      </div>
    </div>
  );
}
