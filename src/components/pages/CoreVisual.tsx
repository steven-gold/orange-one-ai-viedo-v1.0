"use client";

import { useCallback, useEffect, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { CoreClientError, fetchCoreReadModel, postCoreAction, type CoreFieldValue } from "@/lib/client";
import { displayCoreValue } from "./coreFormat";
import {
  CORE_CONTROL_ACTIONS,
  CORE_MESSAGE_ACTIONS,
  CORE_VISIBLE_CONTROLS,
  PROJECT_WORK_ITEMS,
  TOPIC_WORK_ITEMS,
} from "./coreControls";
import styles from "./CoreVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
}) {
  return (
    <button type="button" className={styles.field} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayCoreValue(value, loading)}</span>
    </button>
  );
}

export function CoreVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [pageMode, setPageMode] = useState<"PROJECT_CORE" | "TOPIC_PRODUCTION" | null>(null);
  const [fields, setFields] = useState<CoreFieldValue[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchCoreReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setPageMode(model.pageMode);
        setFields(model.fields.length ? model.fields : CORE_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof CoreClientError ? cause.code : "CORE_READ_UNAVAILABLE");
        setAuthorized(false);
        setPageMode(null);
        setFields(CORE_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const valueOf = useCallback(
    (controlUid: string) => fields.find((row) => row.controlUid === controlUid)?.value ?? null,
    [fields],
  );

  const act = useCallback(async (controlUid: string) => {
    const actionUid = CORE_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postCoreAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const topicMode = pageMode === "TOPIC_PRODUCTION";
  const workItems = topicMode ? TOPIC_WORK_ITEMS : PROJECT_WORK_ITEMS;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);

  return (
    <div
      className={styles.page}
      data-page-uid="CORE-01"
      data-page-state={pageState}
      data-component-count="17"
      data-control-count="44"
      aria-label={tx("core.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("core.error")}</div> : null}

      <section className={styles.context} data-component-uid="CORE-01-CMP-CONTEXT">
        <Field uid="CORE-01-CTL-PROJECT" label={tx("core.project")} value={valueOf("CORE-01-CTL-PROJECT")} loading={loading} onAct={act} disabled={disabled} />
        <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="CORE-01-BTN-PROJECT-CREATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-PROJECT-CREATE")}>{tx("core.create_project")}</button>
        <Field uid="CORE-01-CTL-TOPIC" label={tx("core.topic")} value={valueOf("CORE-01-CTL-TOPIC")} loading={loading} onAct={act} disabled={disabled} />
        <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-TOPIC-CREATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-TOPIC-CREATE")}>{tx("core.create_topic")}</button>
        <button type="button" className={topicMode ? `${styles.btn} ${styles.active}` : styles.btn} data-control-uid="CORE-01-FLD-PAGE-MODE" disabled={disabled} onClick={() => void act("CORE-01-FLD-PAGE-MODE")}>
          {displayCoreValue(valueOf("CORE-01-FLD-PAGE-MODE"), loading)}
        </button>
        <Field uid="CORE-01-FLD-NAMING-AUTHORITY" label={tx("core.naming")} value={valueOf("CORE-01-FLD-NAMING-AUTHORITY")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.field}>
          <span className={styles.label}>{tx("core.current_context")}</span>
          <span className={styles.value}>{tx("core.current_context_value")}</span>
        </div>
      </section>

      <div className={styles.body}>
        <aside className={styles.nav} data-component-uid="CORE-01-CMP-NAV">
          <h2 className={styles.title}>{tx("core.work_item_thread")}</h2>
          <div className={styles.workList} data-control-uid="CORE-01-LST-WORK-ITEMS">
            {workItems.map((item, index) => (
              <button key={item} type="button" className={index === 0 ? `${styles.workItem} ${styles.active}` : styles.workItem} disabled={disabled} onClick={() => void act("CORE-01-LST-WORK-ITEMS")}>
                {item}
                <span>{displayCoreValue(null, loading)}</span>
              </button>
            ))}
          </div>
          <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-NEW-THREAD" disabled={disabled} onClick={() => void act("CORE-01-BTN-NEW-THREAD")}>{tx("core.new_thread")}</button>
          <div data-component-uid="CORE-01-CMP-THREADS">
            <div className={styles.threadsLabel}>{tx("core.threads")}</div>
            <div className={styles.threadList} data-control-uid="CORE-01-LST-THREADS">
              {["1", "2", "3"].map((n) => (
                <button key={n} type="button" className={styles.thread} disabled={disabled} onClick={() => void act("CORE-01-LST-THREADS")}>
                  <span>{`<ThreadRef ${n}>`}</span>
                  <small>{tx("core.current_work_item")}</small>
                </button>
              ))}
            </div>
          </div>
          <section className={styles.integrity}>
            <h3>{tx("core.integrity")}</h3>
            <div className={styles.integrityRow}><span>{tx("core.project_topic")}</span><span className={styles.ok}>{tx("core.exact_refs")}</span></div>
            <div className={styles.integrityRow}><span>{tx("core.work_item_thread")}</span><span className={styles.warn}>{tx("core.scoped")}</span></div>
            <div className={styles.integrityRow}><span>{tx("core.cross_mix")}</span><span className={styles.danger}>{tx("core.forbidden")}</span></div>
          </section>
        </aside>

        <main className={styles.center}>
          <section className={styles.convHeader} data-component-uid="CORE-01-CMP-CONV-HEADER">
            <div className={styles.headerRow}>
              <div>
                <div className={styles.label}>{tx("core.conv_header")}</div>
                <strong>{topicMode ? "PRODUCTION_SCRIPT" : "STORY"}</strong>
              </div>
              <div className={styles.headerControls}>
                <button type="button" className={`${styles.btn} ${styles.active}`} data-control-uid="CORE-01-BTN-SINGLE-AI" disabled={disabled} onClick={() => void act("CORE-01-BTN-SINGLE-AI")}>{tx("core.single_ai")}</button>
                <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-MULTI-AI" disabled={disabled} onClick={() => void act("CORE-01-BTN-MULTI-AI")}>{tx("core.multi_ai")}</button>
                <Field uid="CORE-01-FLD-ASSIGNED-AI" label={tx("core.assigned_ai")} value={valueOf("CORE-01-FLD-ASSIGNED-AI")} loading={loading} onAct={act} disabled={disabled} />
                <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-ASSISTANT-RECORD" disabled={disabled} onClick={() => void act("CORE-01-BTN-ASSISTANT-RECORD")}>{tx("core.assistant_record")}</button>
              </div>
            </div>
          </section>

          <section className={styles.messages} data-component-uid="CORE-01-CMP-MESSAGES">
            <div className={styles.messagesHead}>
              <h2 className={styles.title}>{tx("core.messages")}</h2>
              <span>{tx("core.right_click_only")}</span>
            </div>
            <article className={styles.bubble}>
              <div className={styles.bubbleRole}>USER</div>
              <p>{tx("core.user_placeholder")}</p>
            </article>
            <article className={`${styles.bubble} ${styles.bubbleAlt}`}>
              <div className={styles.bubbleRole}>AI RESPONSE</div>
              <p>{tx("core.ai_placeholder")}</p>
            </article>
            <article className={`${styles.bubble} ${styles.bubbleAlt}`}>
              <div className={styles.bubbleRole}>SYSTEM / ASSISTANT RECORD</div>
              <p>{tx("core.system_placeholder")} {displayCoreValue(null, loading)}</p>
            </article>
            <div data-component-uid="CORE-01-CMP-MESSAGE-MENU" hidden>
              {CORE_MESSAGE_ACTIONS.map((uid) => <span key={uid} data-action-uid={uid} />)}
            </div>
          </section>

          <section className={styles.eval} hidden={topicMode}>
            <h2 className={styles.title}>{tx("core.evaluation_title")}</h2>
            <div className={styles.evalGrid}>
              <div className={styles.evalBox} data-component-uid="CORE-01-CMP-SUMMARY" data-control-uid="CORE-01-FLD-ASSISTANT-SUMMARY">
                <h3>{tx("core.assistant_summary")}</h3>
                <p>{displayCoreValue(valueOf("CORE-01-FLD-ASSISTANT-SUMMARY"), loading)}</p>
                <span className={styles.meta}>read-only</span>
              </div>
              <div className={styles.evalBox} data-component-uid="CORE-01-CMP-EVALUATION" data-control-uid="CORE-01-FLD-EVALUATION">
                <h3>{tx("core.evaluation")}</h3>
                <p>{tx("core.evaluation_meta")} {displayCoreValue(valueOf("CORE-01-FLD-EVALUATION"), loading)}</p>
                <span className={styles.meta}>read-only</span>
              </div>
              <div className={styles.evalBox} data-component-uid="CORE-01-CMP-HUMAN-DECISION" data-control-uid="CORE-01-FLD-HUMAN-DECISION">
                <h3>{tx("core.human_decision")}</h3>
                <p>{displayCoreValue(valueOf("CORE-01-FLD-HUMAN-DECISION"), loading)}</p>
                <span className={styles.meta}>editable</span>
              </div>
            </div>
            <div className={styles.structuredRow}>
              <button type="button" className={`${styles.btn} ${styles.structured}`} data-control-uid="CORE-01-FLD-STRUCTURED-DECISION" disabled={disabled} onClick={() => void act("CORE-01-FLD-STRUCTURED-DECISION")}>
                {tx("core.structured_decision")} {displayCoreValue(valueOf("CORE-01-FLD-STRUCTURED-DECISION"), loading)} {tx("core.no_self_approve")}
              </button>
            </div>
            <div className={styles.candidateRow}>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-CANDIDATE-CREATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANDIDATE-CREATE")}>{tx("core.create_candidate")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-CANDIDATE-CONFIRM" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANDIDATE-CONFIRM")}>{tx("core.confirm_candidate")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-RETURN-MODIFY" disabled={disabled} onClick={() => void act("CORE-01-BTN-RETURN-MODIFY")}>{tx("core.return_modify")}</button>
              <span className={styles.hint}>{tx("core.decision_flow")}</span>
            </div>
          </section>

          <section className={styles.eval} hidden={!topicMode}>
            <h2 className={styles.title}>{tx("core.topic_discussion")}</h2>
            <div className={styles.evalGridTwo}>
              <div className={styles.evalBox} data-control-uid="CORE-01-FLD-TOPIC-SCOPE">
                <h3>{tx("core.topic_scope")}</h3>
                <p>{displayCoreValue(valueOf("CORE-01-FLD-TOPIC-SCOPE"), loading)}</p>
              </div>
              <div className={styles.evalBox}>
                <h3>{tx("core.canonical_script")}</h3>
                <p>{tx("core.canonical_hint")}</p>
              </div>
            </div>
            <div className={styles.evalBox} style={{ marginTop: 10 }}>
              <h3>{tx("core.discussion_constraint")}</h3>
              <p>{tx("core.discussion_constraint_body")}</p>
            </div>
          </section>

          <section className={`${styles.runtime} ${styles.composerBar}`} data-component-uid="CORE-01-CMP-RUNTIME" data-control-uid="CORE-01-FLD-RUNTIME-STAGE">
            {["AI_RESPONSES", "ASSISTANT_SUMMARY", "CORE_EVALUATION", "HUMAN_DECISION", "CANDIDATE"].map((stage, index) => (
              <button key={stage} type="button" className={index === 0 ? `${styles.btn} ${styles.runtimeBtn} ${styles.active}` : `${styles.btn} ${styles.runtimeBtn}`} disabled={disabled} onClick={() => void act("CORE-01-FLD-RUNTIME-STAGE")}>
                {stage}
              </button>
            ))}
          </section>

          <section className={styles.composerBar} data-component-uid="CORE-01-CMP-COMPOSER">
            <div className={styles.composer}>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-ATTACHMENT" disabled={disabled} onClick={() => void act("CORE-01-BTN-ATTACHMENT")}>{tx("core.attachment")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-REFERENCE" disabled={disabled} onClick={() => void act("CORE-01-BTN-REFERENCE")}>{tx("core.reference")}</button>
              <label className={styles.composerInput}>
                <span className={styles.label}>{tx("core.message")}</span>
                <input data-control-uid="CORE-01-FLD-MESSAGE" disabled={disabled} placeholder={tx("core.message_placeholder")} defaultValue="" />
              </label>
              <button type="button" className={`${styles.btn} ${styles.btnSend}`} data-control-uid="CORE-01-BTN-SEND" disabled={disabled} onClick={() => void act("CORE-01-BTN-SEND")}>{tx("core.send")}</button>
            </div>
          </section>
        </main>

        <aside className={styles.rail}>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-PROJECT-STATE" hidden={topicMode}>
            <h2 className={styles.title}>{tx("core.project_rail")}</h2>
            <h3>{tx("core.project_state")}</h3>
            <div className={styles.kv}><span>ProjectVersionRef</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv}><span>Story / Chapter / World</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv}><span>DNAVersion</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv}><span>Core Review</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.railActions}>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-PROJECT-VALIDATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-PROJECT-VALIDATE")}>{tx("core.validate_project")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-PROJECT-CONFIRM" disabled={disabled} onClick={() => void act("CORE-01-BTN-PROJECT-CONFIRM")}>{tx("core.confirm_project")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-STORY-CANDIDATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-STORY-CANDIDATE")}>{tx("core.story_candidate")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-DNA-LOCK" disabled={disabled} onClick={() => void act("CORE-01-BTN-DNA-LOCK")}>{tx("core.dna_lock")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-CORE-REVIEW" disabled={disabled} onClick={() => void act("CORE-01-BTN-CORE-REVIEW")}>{tx("core.core_review")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-PROJECT-LOCK" disabled={disabled} onClick={() => void act("CORE-01-BTN-PROJECT-LOCK")}>{tx("core.project_lock")}</button>
            </div>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-BLUEPRINT-STATE" hidden={topicMode}>
            <h3>{tx("core.blueprint_state")}</h3>
            <div className={styles.kv}><span>BlueprintVersionRef</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv}><span>State</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.railActions}>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-BLUEPRINT-CREATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-BLUEPRINT-CREATE")}>{tx("core.create_blueprint")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-BLUEPRINT-VALIDATE" disabled={disabled} onClick={() => void act("CORE-01-BTN-BLUEPRINT-VALIDATE")}>{tx("core.validate_blueprint")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-BLUEPRINT-APPROVE" disabled={disabled} onClick={() => void act("CORE-01-BTN-BLUEPRINT-APPROVE")}>{tx("core.approve_blueprint")}</button>
              <button type="button" className={styles.btn} data-control-uid="CORE-01-BTN-CHILD-LOCK" disabled={disabled} onClick={() => void act("CORE-01-BTN-CHILD-LOCK")}>{tx("core.child_lock")}</button>
            </div>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-TOPIC-PACKAGE" hidden={!topicMode}>
            <h2 className={styles.title}>{tx("core.topic_package_title")}</h2>
            <h3>{tx("core.topic_package")}</h3>
            <div className={styles.kv}><span>{tx("core.topic_scope")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-TOPIC-SCOPE"), loading)}</span></div>
            <div className={styles.kv} data-control-uid="CORE-01-FLD-PACKAGE"><span>Blueprint</span><span>{displayCoreValue(valueOf("CORE-01-FLD-PACKAGE"), loading)}</span></div>
            <div className={styles.kv}><span>DNA</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.canonical_script")}</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.naming")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-NAMING-AUTHORITY"), loading)}</span></div>
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="CORE-01-BTN-CANONICAL-SCRIPT" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANONICAL-SCRIPT")}>{tx("core.view_canonical")}</button>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-DOWNSTREAM" hidden={!topicMode}>
            <h3>{tx("core.downstream")}</h3>
            <div className={styles.kv}><span>ASSET</span><button type="button" className={styles.btn} data-control-uid="CORE-01-FLD-DOWNSTREAM-ASSET" disabled={disabled} onClick={() => void act("CORE-01-FLD-DOWNSTREAM-ASSET")}>{displayCoreValue(valueOf("CORE-01-FLD-DOWNSTREAM-ASSET"), loading)}</button></div>
            <div className={styles.kv}><span>VIDEO</span><button type="button" className={styles.btn} data-control-uid="CORE-01-FLD-DOWNSTREAM-VIDEO" disabled={disabled} onClick={() => void act("CORE-01-FLD-DOWNSTREAM-VIDEO")}>{displayCoreValue(valueOf("CORE-01-FLD-DOWNSTREAM-VIDEO"), loading)}</button></div>
            <div className={styles.kv}><span>EDIT</span><button type="button" className={styles.btn} data-control-uid="CORE-01-FLD-DOWNSTREAM-EDIT" disabled={disabled} onClick={() => void act("CORE-01-FLD-DOWNSTREAM-EDIT")}>{displayCoreValue(valueOf("CORE-01-FLD-DOWNSTREAM-EDIT"), loading)}</button></div>
          </section>
          <section className={styles.railBlock} data-component-uid="CORE-01-CMP-VERSION">
            <h3>{tx("core.version_lock")}</h3>
            <div className={styles.kv} data-control-uid="CORE-01-FLD-VERSION-STATE"><span>{tx("core.current_candidate")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-VERSION-STATE"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.confirmed_version")}</span><span>{displayCoreValue(null, loading)}</span></div>
            <div className={styles.kv} data-component-uid="CORE-01-CMP-LOCK-REVIEW" data-control-uid="CORE-01-FLD-LOCK-REVIEW"><span>{tx("core.lock_review")}</span><span>{displayCoreValue(valueOf("CORE-01-FLD-LOCK-REVIEW"), loading)}</span></div>
            <div className={styles.kv}><span>{tx("core.block_reason")}</span><span>{displayCoreValue(null, loading)}</span></div>
            <button type="button" className={`${styles.btn} ${styles.btnWide}`} data-control-uid="CORE-01-BTN-CANDIDATE-COMPARE" disabled={disabled} onClick={() => void act("CORE-01-BTN-CANDIDATE-COMPARE")}>{tx("core.compare_candidate")}</button>
          </section>
        </aside>
      </div>
    </div>
  );
}
