"use client";

import { useCallback, useEffect, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { VideoClientError, fetchVideoReadModel, postVideoAction, type VideoFieldValue } from "@/lib/client";
import { displayVideoValue } from "./videoFormat";
import {
  VIDEO_CONTROL_ACTIONS,
  VIDEO_MANIFEST_FIELDS,
  VIDEO_RUNTIME_FIELDS,
  VIDEO_SCOPE_FIELDS,
  VIDEO_SCORE_FIELDS,
  VIDEO_STATUS_FIELDS,
  VIDEO_VISIBLE_CONTROLS,
} from "./videoControls";
import styles from "./VideoVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

const SCORE_IDS: Record<string, TranslationKey> = {
  "VIDEO-01-FLD-SCORE-SCRIPT": "video.score_id_script",
  "VIDEO-01-FLD-SCORE-IDENTITY": "video.score_id_identity",
  "VIDEO-01-FLD-SCORE-MOTION": "video.score_id_motion",
  "VIDEO-01-FLD-SCORE-CAMERA": "video.score_id_camera",
  "VIDEO-01-FLD-SCORE-SCENE": "video.score_id_scene",
  "VIDEO-01-FLD-SCORE-TIMING": "video.score_id_timing",
  "VIDEO-01-FLD-SCORE-TECH": "video.score_id_tech",
  "VIDEO-01-FLD-SCORE-ASSET": "video.score_id_asset",
  "VIDEO-01-FLD-SCORE-RIGHTS": "video.score_id_rights",
};

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
      <span className={styles.value}>{displayVideoValue(value, loading)}</span>
    </button>
  );
}

export function VideoVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<VideoFieldValue[]>([]);
  const [compareOn, setCompareOn] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchVideoReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : VIDEO_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof VideoClientError ? cause.code : "VIDEO_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(VIDEO_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = VIDEO_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postVideoAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const dash = displayVideoValue(null, loading);

  return (
    <div
      className={styles.page}
      data-page-uid="VIDEO-01"
      data-page-state={pageState}
      data-component-count="17"
      data-control-count="85"
      aria-label={tx("video.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("video.error")}</div> : null}

      <section className={`${styles.panel} ${styles.context}`} data-component-uid="VIDEO-01-CMP-CONTEXT">
        <Field uid="VIDEO-01-FLD-PROJECT" label={tx("video.project")} value={valueOf("VIDEO-01-FLD-PROJECT")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="VIDEO-01-FLD-TOPIC" label={tx("video.topic")} value={valueOf("VIDEO-01-FLD-TOPIC")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="VIDEO-01-FLD-TASK" label={tx("video.task")} value={valueOf("VIDEO-01-FLD-TASK")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="VIDEO-01-FLD-STATUS" label={tx("video.status")} value={valueOf("VIDEO-01-FLD-STATUS")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.modePair} data-control-uid="VIDEO-01-CTL-MODE">
          <button type="button" className={`${styles.btn} ${styles.active}`} disabled={disabled} onClick={() => void act("VIDEO-01-CTL-MODE")}>{tx("video.auto")}</button>
          <button type="button" className={styles.btn} disabled={disabled} onClick={() => void act("VIDEO-01-CTL-MODE")}>{tx("video.manual")}</button>
        </div>
        <div className={styles.stageChip}>
          <span className={styles.label}>{tx("video.current_stage")}</span>
          <span className={styles.value}>{tx("video.stage_generate")}</span>
        </div>
        <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-EXECUTE" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-EXECUTE")}>{tx("video.execute")}</button>
        <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-BLUEPRINT" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-BLUEPRINT")}>{tx("video.view_blueprint")}</button>
        <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-PACKAGE" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-PACKAGE")}>{tx("video.view_package")}</button>
      </section>

      <div className={styles.body}>
        <aside className={`${styles.panel} ${styles.left}`}>
          <section data-component-uid="VIDEO-01-CMP-PRODUCTION-LIST">
            <h2 className={styles.title}>{tx("video.production_list")}</h2>
            <div className={styles.searchRow}>
              <label className={styles.search}>
                <span className={styles.label}>{tx("video.search")}</span>
                <input data-control-uid="VIDEO-01-FLD-SEARCH" disabled={disabled} placeholder={tx("video.search")} defaultValue="" onBlur={() => void act("VIDEO-01-FLD-SEARCH")} />
              </label>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-CTL-FILTER" disabled={disabled} onClick={() => void act("VIDEO-01-CTL-FILTER")}>{tx("video.filter")}</button>
            </div>
            <div className={styles.list} data-control-uid="VIDEO-01-CTL-SHOT-SELECT">
              {[0, 1, 2, 3].map((index) => (
                <button
                  key={index}
                  type="button"
                  className={index === 0 ? `${styles.item} ${styles.itemActive}` : styles.item}
                  disabled={disabled}
                  onClick={() => void act("VIDEO-01-CTL-SHOT-SELECT")}
                >
                  <span>{tx("video.unbound_shot")}</span>
                  <span>{tx("video.shot_ref")} {dash}</span>
                </button>
              ))}
            </div>
          </section>
          <section data-component-uid="VIDEO-01-CMP-BLUEPRINT-BIND">
            <Field uid="VIDEO-01-FLD-BLUEPRINT-REF" label={tx("video.blueprint_ref")} value={valueOf("VIDEO-01-FLD-BLUEPRINT-REF")} loading={loading} onAct={act} disabled={disabled} />
          </section>
          <section data-component-uid="VIDEO-01-CMP-SCRIPT-BIND">
            <Field uid="VIDEO-01-FLD-SCRIPT-SECTION" label={tx("video.script_section")} value={valueOf("VIDEO-01-FLD-SCRIPT-SECTION")} loading={loading} onAct={act} disabled={disabled} />
          </section>
          <section data-component-uid="VIDEO-01-CMP-DNA-BIND">
            <Field uid="VIDEO-01-FLD-DNA-REFS" label={tx("video.dna_refs")} value={valueOf("VIDEO-01-FLD-DNA-REFS")} loading={loading} onAct={act} disabled={disabled} />
          </section>
          <section data-component-uid="VIDEO-01-CMP-ASSET-BIND">
            <Field uid="VIDEO-01-FLD-ASSET-REFS" label={tx("video.asset_refs")} value={valueOf("VIDEO-01-FLD-ASSET-REFS")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-FILENAME-CHECKSUM" label={tx("video.filename_checksum")} value={valueOf("VIDEO-01-FLD-FILENAME-CHECKSUM")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-INSTRUCTION" label={tx("video.instruction")} value={valueOf("VIDEO-01-FLD-INSTRUCTION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-RIGHTS" label={tx("video.rights")} value={valueOf("VIDEO-01-FLD-RIGHTS")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-INPUT-FINGERPRINT" label={tx("video.input_fingerprint")} value={valueOf("VIDEO-01-FLD-INPUT-FINGERPRINT")} loading={loading} onAct={act} disabled={disabled} />
          </section>
        </aside>

        <main className={`${styles.panel} ${styles.center}`}>
          <section data-component-uid="VIDEO-01-CMP-PREVIEW" className={styles.center}>
            <div className={styles.previewHead} data-component-uid="VIDEO-01-CMP-COMPARE">
              <h2 className={styles.title}>{tx("video.preview")}</h2>
              <button
                type="button"
                className={compareOn ? styles.btn : `${styles.btn} ${styles.active}`}
                data-control-uid="VIDEO-01-CTL-VERSION-A"
                disabled={disabled}
                onClick={() => { setCompareOn(false); void act("VIDEO-01-CTL-VERSION-A"); }}
              >
                {tx("video.single")}
              </button>
              <button
                type="button"
                className={compareOn ? `${styles.btn} ${styles.active}` : styles.btn}
                data-control-uid="VIDEO-01-CTL-COMPARE"
                disabled={disabled}
                onClick={() => { setCompareOn(true); void act("VIDEO-01-CTL-COMPARE"); }}
              >
                {tx("video.compare_toggle")}
              </button>
            </div>
            {compareOn ? (
              <div className={styles.compareGrid}>
                <div className={styles.comparePane}>
                  <p className={styles.previewTitle}>A · Current</p>
                  <span>{tx("video.exact_output_ref")} {dash}</span>
                </div>
                <button type="button" className={styles.comparePane} data-control-uid="VIDEO-01-CTL-VERSION-B" disabled={disabled} onClick={() => void act("VIDEO-01-CTL-VERSION-B")}>
                  <p className={styles.previewTitle}>B · Candidate</p>
                  <span>{tx("video.exact_output_ref")} {dash}</span>
                </button>
              </div>
            ) : (
              <div className={styles.preview}>
                <p className={styles.previewTitle}>{tx("video.preview_unbound")}</p>
                <span>{tx("video.exact_output_ref")} {dash}</span>
              </div>
            )}
            <div className={styles.toolbar}>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-PLAY" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-PLAY")}>{tx("video.play")}</button>
              <Field uid="VIDEO-01-FLD-TIMECODE" label={tx("video.timecode")} value={valueOf("VIDEO-01-FLD-TIMECODE")} loading={loading} onAct={act} disabled={disabled} />
              <input className={styles.seek} type="range" min="0" max="100" defaultValue="0" data-control-uid="VIDEO-01-CTL-SEEK" disabled={disabled} onChange={() => void act("VIDEO-01-CTL-SEEK")} />
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-VOLUME" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-VOLUME")}>{tx("video.volume")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-FULLSCREEN" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-FULLSCREEN")}>{tx("video.fullscreen")}</button>
            </div>
            {compareOn ? <p className={styles.note}>{tx("video.compare_note")}</p> : null}
          </section>
        </main>

        <aside className={`${styles.panel} ${styles.right}`}>
          <section data-component-uid="VIDEO-01-CMP-VERSION">
            <h2 className={styles.title}>{tx("video.version")}</h2>
            <Field uid="VIDEO-01-FLD-CURRENT-VERSION" label={tx("video.current_version")} value={valueOf("VIDEO-01-FLD-CURRENT-VERSION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-CANDIDATE-VERSION" label={tx("video.candidate_version")} value={valueOf("VIDEO-01-FLD-CANDIDATE-VERSION")} loading={loading} onAct={act} disabled={disabled} />
          </section>
          <section data-component-uid="VIDEO-01-CMP-SCORE">
            <Field uid="VIDEO-01-FLD-CRITERIA-VERSION" label={tx("video.criteria_version")} value={valueOf("VIDEO-01-FLD-CRITERIA-VERSION")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-OVERALL-SCORE" label={tx("video.overall_score")} value={valueOf("VIDEO-01-FLD-OVERALL-SCORE")} loading={loading} onAct={act} disabled={disabled} />
            <Field uid="VIDEO-01-FLD-ISSUE-SUMMARY" label={tx("video.issue_summary")} value={valueOf("VIDEO-01-FLD-ISSUE-SUMMARY")} loading={loading} onAct={act} disabled={disabled} />
            <button type="button" className={styles.statusBadge} data-control-uid="VIDEO-01-BTN-SCORE-DETAIL" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-SCORE-DETAIL")}>{tx("video.score_detail")}</button>
          </section>
          <section data-component-uid="VIDEO-01-CMP-DECISION">
            <div className={styles.decisionGrid}>
              <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-CONFIRM" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-CONFIRM")}>{tx("video.confirm")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-MODIFY" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-MODIFY")}>{tx("video.modify")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-LOCK" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-LOCK")}>{tx("video.lock")}</button>
              <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-HANDOFF" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-HANDOFF")}>{tx("video.handoff_edit")}</button>
            </div>
          </section>
        </aside>
      </div>

      <section className={`${styles.panel} ${styles.runtime}`} data-component-uid="VIDEO-01-CMP-PROVIDER-RUNTIME">
        <h3 className={styles.sub}>{tx("video.runtime")}</h3>
        <div className={styles.runtimeRow}>
          {VIDEO_RUNTIME_FIELDS.map(([uid, key]) => (
            <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} />
          ))}
        </div>
        <div className={styles.runtimeActions}>
          <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-RETRY" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-RETRY")}>{tx("video.retry")}</button>
          <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-RUNTIME-DETAIL" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-RUNTIME-DETAIL")}>{tx("video.runtime_detail")}</button>
        </div>
      </section>

      <div className={styles.lower}>
        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-CORRECTION-SCOPE">
          <h3 className={styles.sub}>{tx("video.correction_scope")}</h3>
          <div className={styles.scopeRow}>
            {VIDEO_SCOPE_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} />
            ))}
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-CONTEXT-BUILD" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-CONTEXT-BUILD")}>{tx("video.context_build")}</button>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-AI-REVISION">
          <h3 className={styles.sub}>{tx("video.ai_revision")}</h3>
          <div className={styles.composer}>
            <span className={styles.label}>{tx("video.source_script")}</span>
            <span className={styles.value}>{dash}</span>
          </div>
          <label className={styles.composer}>
            <span className={styles.label}>{tx("video.correction_request")}</span>
            <textarea data-control-uid="VIDEO-01-TXT-CORRECTION" disabled={disabled} defaultValue="" placeholder={tx("video.correction_hint")} onBlur={() => void act("VIDEO-01-TXT-CORRECTION")} />
          </label>
          <div className={styles.corrActions}>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-GEN-CORRECTION" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-GEN-CORRECTION")}>{tx("video.correction_generate")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-APPROVE-CORRECTION" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-APPROVE-CORRECTION")}>{tx("video.correction_approve")}</button>
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-EXEC-CORRECTION" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-EXEC-CORRECTION")}>{tx("video.correction_execute")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-COMPARE-CORRECTION" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-COMPARE-CORRECTION")}>{tx("video.correction_compare")}</button>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-EVALUATION">
          <h3 className={styles.sub}>{tx("video.evaluation")}</h3>
          <div className={styles.scoreGrid}>
            {VIDEO_SCORE_FIELDS.map(([uid, key]) => (
              <button key={uid} type="button" className={styles.scoreCard} data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
                <strong>{tx(key)}</strong>
                <span className={styles.scoreId}>{tx(SCORE_IDS[uid])}</span>
                <span className={styles.scoreMeta}>{tx("video.score")}: {displayVideoValue(valueOf(uid), loading)} · {tx("video.evidence_short")}: {dash}</span>
                <span className={uid === "VIDEO-01-FLD-SCORE-RIGHTS" ? `${styles.scoreMeta} ${styles.warn}` : styles.scoreMeta}>
                  {uid === "VIDEO-01-FLD-SCORE-RIGHTS" ? tx("video.rights_hard") : `${tx("video.hard_block")}: ${dash}`}
                </span>
              </button>
            ))}
          </div>
          <div className={styles.evalActions}>
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} data-control-uid="VIDEO-01-BTN-EVALUATE" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-EVALUATE")}>{tx("video.evaluate")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-FINDING" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-FINDING")}>{tx("video.finding")}</button>
            <button type="button" className={styles.btn} data-control-uid="VIDEO-01-BTN-ISSUE-OPEN" disabled={disabled} onClick={() => void act("VIDEO-01-BTN-ISSUE-OPEN")}>{tx("video.issue_open")}</button>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-MANIFEST">
          <h3 className={styles.sub}>{tx("video.finalize_gate")}</h3>
          <div className={styles.gateRow}>
            <div className={styles.gateChip}>{tx("video.gate_confirm")}</div>
            <div className={styles.gateChip}>{tx("video.gate_score")}</div>
            <div className={styles.gateChip}>{tx("video.gate_hard")}</div>
            <div className={styles.gateChip}>{tx("video.gate_manifest")}</div>
            <div className={styles.gateChip}>{tx("video.gate_lock")}</div>
          </div>
          <h3 className={styles.sub}>{tx("video.manifest")}</h3>
          <div className={styles.manifestGrid}>
            {VIDEO_MANIFEST_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} />
            ))}
          </div>
          <div className={styles.crossBody}>
            <strong>{tx("video.cross_page")}</strong>
            <span>{tx("video.cross_page_body")}</span>
            <span>{tx("video.cross_page_edit")}</span>
            <span className={styles.warn}>{tx("video.cross_page_warn")}</span>
          </div>
        </section>

        <section className={styles.panel} data-component-uid="VIDEO-01-CMP-STATUS">
          <h3 className={styles.sub}>{tx("video.page_status")}</h3>
          <div className={styles.statusGrid}>
            {VIDEO_STATUS_FIELDS.map(([uid, key]) => (
              <Field key={uid} uid={uid} label={tx(key)} value={valueOf(uid)} loading={loading} onAct={act} disabled={disabled} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
