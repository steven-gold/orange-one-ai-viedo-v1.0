"use client";

import { useEffect, useState, type MouseEvent as ReactMouseEvent } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { readCoreProjection } from "@/domain/core/coreClientPort";
import type { CoreActionUid } from "@/domain/core/coreRuntimeContract";
import styles from "./CoreVisual.module.css";

type LabelKey = TranslationKey;
type PageState = "LOADING" | "READY" | "ERROR";

type ControlProps = {
  id: string;
  labelKey: LabelKey;
  primary?: boolean;
  compact?: boolean;
};

const CONTROL_ACTION_UID: Record<string, CoreActionUid> = {
  "CORE-01-CTL-PROJECT": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-BTN-PROJECT-CREATE": "CORE-01-ACT-PROJECT-CREATE",
  "CORE-01-CTL-TOPIC": "CORE-01-ACT-TOPIC-SELECT",
  "CORE-01-BTN-TOPIC-CREATE": "CORE-01-ACT-TOPIC-CREATE",
  "CORE-01-FLD-PAGE-MODE": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-FLD-NAMING-AUTHORITY": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-LST-WORK-ITEMS": "CORE-01-ACT-WORK-ITEM-SELECT",
  "CORE-01-BTN-NEW-THREAD": "CORE-01-ACT-THREAD-CREATE",
  "CORE-01-LST-THREADS": "CORE-01-ACT-THREAD-SELECT",
  "CORE-01-BTN-SINGLE-AI": "CORE-01-ACT-AI-MODE-SINGLE",
  "CORE-01-BTN-MULTI-AI": "CORE-01-ACT-AI-MODE-MULTI",
  "CORE-01-FLD-ASSIGNED-AI": "CORE-01-ACT-ASSISTANT-RECORD",
  "CORE-01-BTN-ASSISTANT-RECORD": "CORE-01-ACT-ASSISTANT-RECORD",
  "CORE-01-MENU-QUOTE": "CORE-01-ACT-MSG-QUOTE",
  "CORE-01-MENU-CONTINUE": "CORE-01-ACT-MSG-CONTINUE",
  "CORE-01-MENU-ANALYZE": "CORE-01-ACT-MSG-ANALYZE",
  "CORE-01-MENU-DECISION": "CORE-01-ACT-MSG-DECISION",
  "CORE-01-MENU-BRANCH": "CORE-01-ACT-MSG-BRANCH",
  "CORE-01-MENU-COPY": "CORE-01-ACT-MSG-COPY",
  "CORE-01-FLD-ASSISTANT-SUMMARY": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-FLD-EVALUATION": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-FLD-HUMAN-DECISION": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-FLD-STRUCTURED-DECISION": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-BTN-CANDIDATE-CREATE": "CORE-01-ACT-CANDIDATE-CREATE",
  "CORE-01-BTN-CANDIDATE-CONFIRM": "CORE-01-ACT-CANDIDATE-ACCEPT",
  "CORE-01-BTN-RETURN-MODIFY": "CORE-01-ACT-CANDIDATE-RETURN",
  "CORE-01-FLD-RUNTIME-STAGE": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-BTN-ATTACHMENT": "CORE-01-ACT-ATTACHMENT",
  "CORE-01-BTN-REFERENCE": "CORE-01-ACT-REFERENCE-ATTACH",
  "CORE-01-FLD-MESSAGE": "CORE-01-ACT-SEND",
  "CORE-01-BTN-SEND": "CORE-01-ACT-SEND",
  "CORE-01-BTN-PROJECT-VALIDATE": "CORE-01-ACT-PROJECT-VALIDATE",
  "CORE-01-BTN-PROJECT-CONFIRM": "CORE-01-ACT-PROJECT-CONFIRM",
  "CORE-01-BTN-STORY-CANDIDATE": "CORE-01-ACT-STORY-CANDIDATE",
  "CORE-01-BTN-DNA-LOCK": "CORE-01-ACT-DNA-LOCK-REQUEST",
  "CORE-01-BTN-CORE-REVIEW": "CORE-01-ACT-CORE-REVIEW-SUBMIT",
  "CORE-01-BTN-PROJECT-LOCK": "CORE-01-ACT-MOTHER-LOCK-REQUEST",
  "CORE-01-BTN-BLUEPRINT-CREATE": "CORE-01-ACT-BLUEPRINT-CREATE",
  "CORE-01-BTN-BLUEPRINT-VALIDATE": "CORE-01-ACT-BLUEPRINT-VALIDATE",
  "CORE-01-BTN-BLUEPRINT-APPROVE": "CORE-01-ACT-BLUEPRINT-APPROVE",
  "CORE-01-BTN-CHILD-LOCK": "CORE-01-ACT-CHILD-LOCK-REQUEST",
  "CORE-01-FLD-TOPIC-SCOPE": "CORE-01-ACT-TOPIC-SELECT",
  "CORE-01-BTN-CANONICAL-SCRIPT": "CORE-01-ACT-CANONICAL-SCRIPT-VIEW",
  "CORE-01-FLD-PACKAGE": "CORE-01-ACT-CANONICAL-SCRIPT-VIEW",
  "CORE-01-FLD-DOWNSTREAM-ASSET": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-FLD-DOWNSTREAM-VIDEO": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-FLD-DOWNSTREAM-EDIT": "CORE-01-ACT-PROJECT-SELECT",
  "CORE-01-BTN-CANDIDATE-COMPARE": "CORE-01-ACT-CANDIDATE-COMPARE",
  "CORE-01-FLD-VERSION-STATE": "CORE-01-ACT-CANDIDATE-COMPARE",
  "CORE-01-FLD-LOCK-REVIEW": "CORE-01-ACT-PROJECT-SELECT",
};

function actionUid(id: string): CoreActionUid {
  return CONTROL_ACTION_UID[id];
}

function DisabledButton({ id, labelKey, primary = false, compact = false }: ControlProps) {
  const { t } = useI18n();
  return (
    <button
      type="button"
      disabled
      data-control-id={id}
      data-action-uid={actionUid(id)}
      data-runtime-binding="BLOCKED_UNTIL_AUTHORIZED_CONTEXT"
      className={`${styles.button} ${primary ? styles.primaryButton : ""} ${compact ? styles.compactButton : ""}`}
    >
      {t(labelKey)}
    </button>
  );
}

function ReadonlyField({ id, labelKey }: ControlProps) {
  const { t } = useI18n();
  return (
    <div className={styles.readonlyField} data-control-id={id} data-action-uid={actionUid(id)}>
      <span className={styles.fieldLabel}>{t(labelKey)}</span>
      <span className={styles.fieldValue}>—</span>
    </div>
  );
}

function EmptyList({ id, labelKey }: ControlProps) {
  const { t } = useI18n();
  return (
    <div className={styles.listControl} data-control-id={id} data-action-uid={actionUid(id)}>
      <div className={styles.subheading}>{t(labelKey)}</div>
      <div className={styles.emptyValue}>—</div>
    </div>
  );
}

function PanelTitle({ labelKey }: { labelKey: LabelKey }) {
  const { t } = useI18n();
  return <h2 className={styles.panelTitle}>{t(labelKey)}</h2>;
}

const MESSAGE_MENU: readonly { id: string; key: LabelKey }[] = [
  { id: "CORE-01-MENU-QUOTE", key: "core01.control.quote" },
  { id: "CORE-01-MENU-CONTINUE", key: "core01.control.continue" },
  { id: "CORE-01-MENU-ANALYZE", key: "core01.control.analyze" },
  { id: "CORE-01-MENU-DECISION", key: "core01.control.decision_list" },
  { id: "CORE-01-MENU-BRANCH", key: "core01.control.branch" },
  { id: "CORE-01-MENU-COPY", key: "core01.control.copy" },
] as const;

export function CoreVisual() {
  const { t } = useI18n();
  const [menuOpen, setMenuOpen] = useState(false);
  const [pageState, setPageState] = useState<PageState>("LOADING");
  const [runtimeReason, setRuntimeReason] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void readCoreProjection(controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      if (result.ok) {
        setPageState("READY");
        setRuntimeReason(null);
      } else {
        setPageState("ERROR");
        setRuntimeReason(result.reason_code);
      }
    });
    return () => controller.abort();
  }, []);

  const openContextMenu = (event: ReactMouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    setMenuOpen(true);
  };

  return (
    <div
      className={styles.page}
      data-page-uid="CORE-01"
      data-vis-step="VIS-02"
      data-page-state={pageState}
      data-runtime-reason={runtimeReason ?? undefined}
      onClick={() => menuOpen && setMenuOpen(false)}
    >
      <section className={styles.contextBar} data-section-id="CORE-01-SEC-01" data-visual-id="CORE-01-VIS-CONTEXT">
        <div className={styles.contextComponent} data-component-uid="CORE-01-CMP-CONTEXT">
          <label className={styles.selectField}>
            <span>{t("core01.control.project")}</span>
            <select disabled data-control-id="CORE-01-CTL-PROJECT" data-action-uid={actionUid("CORE-01-CTL-PROJECT")} aria-label={t("core01.control.project")}><option>—</option></select>
          </label>
          <DisabledButton id="CORE-01-BTN-PROJECT-CREATE" labelKey="core01.control.create_project" primary />
          <label className={styles.selectField}>
            <span>{t("core01.control.topic")}</span>
            <select disabled data-control-id="CORE-01-CTL-TOPIC" data-action-uid={actionUid("CORE-01-CTL-TOPIC")} aria-label={t("core01.control.topic")}><option>—</option></select>
          </label>
          <DisabledButton id="CORE-01-BTN-TOPIC-CREATE" labelKey="core01.control.create_topic" primary />
          <ReadonlyField id="CORE-01-FLD-PAGE-MODE" labelKey="core01.control.page_mode" />
          <ReadonlyField id="CORE-01-FLD-NAMING-AUTHORITY" labelKey="core01.control.naming_authority" />
        </div>
      </section>

      <div className={styles.primaryGrid} data-layout="CORE-01-PRIMARY-GRID">
        <aside className={styles.leftRail}>
          <section className={styles.panel} data-section-id="CORE-01-SEC-02" data-visual-id="CORE-01-VIS-LEFT">
            <div data-component-uid="CORE-01-CMP-NAV"><EmptyList id="CORE-01-LST-WORK-ITEMS" labelKey="core01.control.work_items" /></div>
            <div className={styles.divider} />
            <div data-component-uid="CORE-01-CMP-THREADS">
              <div className={styles.threadHeader}>
                <PanelTitle labelKey="core01.group.conversation_threads" />
                <DisabledButton id="CORE-01-BTN-NEW-THREAD" labelKey="core01.control.new_thread" compact />
              </div>
              <div className={styles.threadListScroll}><EmptyList id="CORE-01-LST-THREADS" labelKey="core01.control.threads" /></div>
            </div>
          </section>
        </aside>

        <main className={styles.centerColumn}>
          <section className={`${styles.panel} ${styles.conversationHeader}`} data-section-id="CORE-01-SEC-03" data-visual-id="CORE-01-VIS-CENTER-HEADER">
            <div className={styles.conversationHeaderInner} data-component-uid="CORE-01-CMP-CONV-HEADER">
              <PanelTitle labelKey="core01.group.conversation" />
              <div className={styles.aiModeGroup}>
                <DisabledButton id="CORE-01-BTN-SINGLE-AI" labelKey="core01.control.single_ai" compact />
                <DisabledButton id="CORE-01-BTN-MULTI-AI" labelKey="core01.control.multi_ai" compact />
              </div>
              <ReadonlyField id="CORE-01-FLD-ASSIGNED-AI" labelKey="core01.control.assigned_ai" />
              <DisabledButton id="CORE-01-BTN-ASSISTANT-RECORD" labelKey="core01.control.assistant_record" compact />
            </div>
          </section>

          <section className={`${styles.panel} ${styles.messagesPanel}`} data-section-id="CORE-01-SEC-04" data-visual-id="CORE-01-VIS-MESSAGES">
            <div className={styles.messageWorkspace} data-component-uid="CORE-01-CMP-MESSAGES" onContextMenu={openContextMenu}>
              <PanelTitle labelKey="core01.group.message_workspace" />
              <div className={styles.messageEmpty}>—</div>
              {menuOpen && (
                <div className={styles.contextMenu} data-component-uid="CORE-01-CMP-MESSAGE-MENU" onClick={(event) => event.stopPropagation()}>
                  {MESSAGE_MENU.map((item) => (
                    <button key={item.id} type="button" disabled className={styles.contextMenuItem} data-control-id={item.id} data-action-uid={actionUid(item.id)} data-runtime-binding="BLOCKED_WITHOUT_EXACT_MESSAGE_REF">
                      {t(item.key)}
                    </button>
                  ))}
                </div>
              )}
              {!menuOpen && <div className={styles.menuComponentSentinel} data-component-uid="CORE-01-CMP-MESSAGE-MENU" aria-hidden="true" />}
            </div>
          </section>

          <section className={`${styles.panel} ${styles.decisionPanel}`} data-section-id="CORE-01-SEC-05" data-visual-id="CORE-01-VIS-DECISION">
            <PanelTitle labelKey="core01.group.decision" />
            <div className={styles.decisionGrid}>
              <div data-component-uid="CORE-01-CMP-SUMMARY"><ReadonlyField id="CORE-01-FLD-ASSISTANT-SUMMARY" labelKey="core01.control.assistant_summary" /></div>
              <div data-component-uid="CORE-01-CMP-EVALUATION"><ReadonlyField id="CORE-01-FLD-EVALUATION" labelKey="core01.control.evaluation" /></div>
              <div className={styles.humanDecision} data-component-uid="CORE-01-CMP-HUMAN-DECISION">
                <label className={styles.textareaField}>
                  <span>{t("core01.control.human_decision")}</span>
                  <textarea disabled data-control-id="CORE-01-FLD-HUMAN-DECISION" data-action-uid={actionUid("CORE-01-FLD-HUMAN-DECISION")} value="" readOnly aria-label={t("core01.control.human_decision")} />
                </label>
                <ReadonlyField id="CORE-01-FLD-STRUCTURED-DECISION" labelKey="core01.control.structured_decision" />
                <div className={styles.actionRow}>
                  <DisabledButton id="CORE-01-BTN-CANDIDATE-CREATE" labelKey="core01.control.create_candidate" primary />
                  <DisabledButton id="CORE-01-BTN-CANDIDATE-CONFIRM" labelKey="core01.control.confirm_candidate" primary />
                  <DisabledButton id="CORE-01-BTN-RETURN-MODIFY" labelKey="core01.control.return_modify" />
                </div>
              </div>
            </div>
          </section>

          <section className={styles.runtimeStrip} data-section-id="CORE-01-SEC-06" data-visual-id="CORE-01-VIS-RUNTIME">
            <div className={styles.runtimeComponent} data-component-uid="CORE-01-CMP-RUNTIME" data-control-id="CORE-01-FLD-RUNTIME-STAGE" data-action-uid={actionUid("CORE-01-FLD-RUNTIME-STAGE")}>
              <span>{t("core01.control.runtime_stage")}</span><strong>—</strong>
            </div>
          </section>

          <section className={`${styles.panel} ${styles.composerPanel}`} data-section-id="CORE-01-SEC-07" data-visual-id="CORE-01-VIS-COMPOSER">
            <div className={styles.composer} data-component-uid="CORE-01-CMP-COMPOSER">
              <div className={styles.composerTools}>
                <DisabledButton id="CORE-01-BTN-ATTACHMENT" labelKey="core01.control.attachment" compact />
                <DisabledButton id="CORE-01-BTN-REFERENCE" labelKey="core01.control.reference" compact />
              </div>
              <textarea disabled data-control-id="CORE-01-FLD-MESSAGE" data-action-uid={actionUid("CORE-01-FLD-MESSAGE")} aria-label={t("core01.control.message")} placeholder={t("core01.control.message")} />
              <DisabledButton id="CORE-01-BTN-SEND" labelKey="core01.control.send" primary />
            </div>
          </section>
        </main>

        <aside className={styles.rightRail}>
          <section className={styles.panel} data-section-id="CORE-01-SEC-08" data-visual-id="CORE-01-VIS-RIGHT-CORE">
            <div className={styles.stateBlock} data-component-uid="CORE-01-CMP-PROJECT-STATE">
              <PanelTitle labelKey="core01.group.project_core_state" />
              <div className={styles.stateValue}>—</div>
              <div className={styles.stackActions}>
                <DisabledButton id="CORE-01-BTN-PROJECT-VALIDATE" labelKey="core01.control.project_validate" />
                <DisabledButton id="CORE-01-BTN-PROJECT-CONFIRM" labelKey="core01.control.project_confirm" />
                <DisabledButton id="CORE-01-BTN-STORY-CANDIDATE" labelKey="core01.control.story_candidate" />
                <DisabledButton id="CORE-01-BTN-DNA-LOCK" labelKey="core01.control.dna_lock" />
                <DisabledButton id="CORE-01-BTN-CORE-REVIEW" labelKey="core01.control.core_review" />
                <DisabledButton id="CORE-01-BTN-PROJECT-LOCK" labelKey="core01.control.project_lock" />
              </div>
            </div>
            <div className={styles.divider} />
            <div className={styles.stateBlock} data-component-uid="CORE-01-CMP-BLUEPRINT-STATE">
              <PanelTitle labelKey="core01.group.blueprint_state" />
              <div className={styles.stateValue}>—</div>
              <div className={styles.stackActions}>
                <DisabledButton id="CORE-01-BTN-BLUEPRINT-CREATE" labelKey="core01.control.blueprint_create" />
                <DisabledButton id="CORE-01-BTN-BLUEPRINT-VALIDATE" labelKey="core01.control.blueprint_validate" />
                <DisabledButton id="CORE-01-BTN-BLUEPRINT-APPROVE" labelKey="core01.control.blueprint_approve" />
                <DisabledButton id="CORE-01-BTN-CHILD-LOCK" labelKey="core01.control.child_lock" />
              </div>
            </div>
          </section>

          <section className={styles.panel} data-section-id="CORE-01-SEC-09" data-visual-id="CORE-01-VIS-RIGHT-TOPIC">
            <div data-component-uid="CORE-01-CMP-TOPIC-PACKAGE">
              <PanelTitle labelKey="core01.group.topic_package" />
              <ReadonlyField id="CORE-01-FLD-TOPIC-SCOPE" labelKey="core01.control.topic_scope" />
              <DisabledButton id="CORE-01-BTN-CANONICAL-SCRIPT" labelKey="core01.control.canonical_script" />
              <ReadonlyField id="CORE-01-FLD-PACKAGE" labelKey="core01.control.package" />
            </div>
            <div className={styles.divider} />
            <div data-component-uid="CORE-01-CMP-DOWNSTREAM">
              <PanelTitle labelKey="core01.group.downstream" />
              <ReadonlyField id="CORE-01-FLD-DOWNSTREAM-ASSET" labelKey="core01.control.downstream_asset" />
              <ReadonlyField id="CORE-01-FLD-DOWNSTREAM-VIDEO" labelKey="core01.control.downstream_video" />
              <ReadonlyField id="CORE-01-FLD-DOWNSTREAM-EDIT" labelKey="core01.control.downstream_edit" />
            </div>
          </section>

          <section className={styles.panel} data-section-id="CORE-01-SEC-10" data-visual-id="CORE-01-VIS-RIGHT-VERSION">
            <div data-component-uid="CORE-01-CMP-VERSION">
              <PanelTitle labelKey="core01.group.version" />
              <DisabledButton id="CORE-01-BTN-CANDIDATE-COMPARE" labelKey="core01.control.candidate_compare" />
              <ReadonlyField id="CORE-01-FLD-VERSION-STATE" labelKey="core01.control.version_state" />
            </div>
            <div className={styles.divider} />
            <div data-component-uid="CORE-01-CMP-LOCK-REVIEW">
              <PanelTitle labelKey="core01.group.lock_review" />
              <ReadonlyField id="CORE-01-FLD-LOCK-REVIEW" labelKey="core01.control.lock_review" />
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}