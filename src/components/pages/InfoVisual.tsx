"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { InfoClientError, fetchInfoReadModel, postInfoAction, type InfoFieldValue } from "@/lib/client";
import { displayInfoValue } from "./infoFormat";
import { INFO_CONTROL_ACTIONS, INFO_VISIBLE_CONTROLS } from "./infoControls";
import styles from "./InfoVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type FactTab = "FACT" | "INFERENCE";

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
  className,
  row = false,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
  className?: string;
  row?: boolean;
}) {
  return (
    <button
      type="button"
      className={`${styles.field} ${row ? styles.fieldRow : ""} ${className ?? ""}`}
      data-control-uid={uid}
      disabled={disabled}
      onClick={() => onAct(uid)}
    >
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayInfoValue(value, loading)}</span>
    </button>
  );
}

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  className,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  className?: string;
}) {
  const resolved = [styles.btn, primary ? styles.btnPrimary : "", className ?? ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={resolved} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

function Kv({
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
    <button type="button" className={styles.kv} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.kvLabel}>{label}</span>
      <span className={styles.kvValue}>{displayInfoValue(value, loading)}</span>
    </button>
  );
}

export function InfoVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<InfoFieldValue[]>([]);
  const [tab, setTab] = useState<FactTab>("FACT");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchInfoReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : INFO_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof InfoClientError ? cause.code : "INFO_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(INFO_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = INFO_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postInfoAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const v = (uid: string) => valueOf(uid);
  const visibleUids = useMemo(() => new Set<string>(INFO_VISIBLE_CONTROLS), []);

  const selectTab = (next: FactTab) => {
    setTab(next);
    void act(next === "FACT" ? "INFO-01-TAB-FACT" : "INFO-01-TAB-INFERENCE");
  };

  return (
    <div
      className={styles.page}
      data-page-uid="workspace:INFO-01"
      data-page-state={pageState}
      data-fact-tab={tab}
      data-component-count="20"
      data-control-count="66"
      aria-label={tx("info.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("info.error")}</div> : null}

      <header className={styles.heading}>
        <h1 className={styles.headingTitle}>{tx("info.title")}</h1>
        <p className={styles.headingMeta}>{tx("info.meta")}</p>
      </header>

      <section className={`${styles.panel} ${styles.context}`} data-section-uid="INFO-01-SEC-01" data-component-uid="INFO-01-CMP-CONTEXT" data-visual-uid="INFO-01-VIS-CONTEXT">
        <Field uid="INFO-01-FLD-SCOPE" label={tx("info.fld-scope")} value={v("INFO-01-FLD-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="INFO-01-FLD-PROJECTION-VERSION" label={tx("info.fld-projection-version")} value={v("INFO-01-FLD-PROJECTION-VERSION")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="INFO-01-FLD-PAGE-STATE" label={tx("info.fld-page-state")} value={v("INFO-01-FLD-PAGE-STATE")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="INFO-01-FLD-LAST-REFRESH" label={tx("info.fld-last-refresh")} value={v("INFO-01-FLD-LAST-REFRESH")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.contextSpacer} />
        <div className={styles.contextActions}>
          <Btn uid="INFO-01-BTN-SEARCH" label={tx("info.btn-search")} onAct={act} disabled={disabled} />
          <Btn uid="INFO-01-BTN-REFRESH" label={tx("info.btn-refresh")} onAct={act} disabled={disabled} primary />
        </div>
      </section>

      <div className={styles.grid}>
        <aside className={styles.col}>
          <section className={styles.panel} data-section-uid="INFO-01-SEC-02" data-visual-uid="INFO-01-VIS-LEFT-SOURCE">
            <div className={styles.headRow}>
              <h2 className={styles.title}>{tx("info.source-health")}</h2>
              <span className={styles.hint}>{tx("info.source-hint")}</span>
            </div>
            <div className={styles.stack} data-component-uid="INFO-01-CMP-SCOPE">
              <Field uid="INFO-01-SEL-SCOPE" label={tx("info.sel-scope")} value={v("INFO-01-SEL-SCOPE")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
            <div className={styles.stack} data-component-uid="INFO-01-CMP-SOURCE-HEALTH">
              <Field uid="INFO-01-LST-SOURCES" label={tx("info.lst-sources")} value={v("INFO-01-LST-SOURCES")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-SOURCE-HEALTH" label={tx("info.fld-source-health")} value={v("INFO-01-FLD-SOURCE-HEALTH")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-SOURCE-REF" label={tx("info.fld-source-ref")} value={v("INFO-01-FLD-SOURCE-REF")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-SOURCE-TIME" label={tx("info.fld-source-time")} value={v("INFO-01-FLD-SOURCE-TIME")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-SOURCE-CLASS" label={tx("info.fld-source-class")} value={v("INFO-01-FLD-SOURCE-CLASS")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
          </section>

          <section className={styles.panel} data-section-uid="INFO-01-SEC-03" data-component-uid="INFO-01-CMP-ALERT" data-visual-uid="INFO-01-VIS-LEFT-ALERT">
            <div className={styles.headRow}>
              <h2 className={styles.title}>{tx("info.alerts")}</h2>
            </div>
            <div className={styles.stack}>
              <Field uid="INFO-01-LST-ALERTS" label={tx("info.lst-alerts")} value={v("INFO-01-LST-ALERTS")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-ALERT-REF" label={tx("info.fld-alert-ref")} value={v("INFO-01-FLD-ALERT-REF")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-ALERT-SCOPE" label={tx("info.fld-alert-scope")} value={v("INFO-01-FLD-ALERT-SCOPE")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-ALERT-SOURCE" label={tx("info.fld-alert-source")} value={v("INFO-01-FLD-ALERT-SOURCE")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-ALERT-STATUS" label={tx("info.fld-alert-status")} value={v("INFO-01-FLD-ALERT-STATUS")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
          </section>
        </aside>

        <main className={styles.col}>
          <section className={styles.panel} data-section-uid="INFO-01-SEC-04" data-visual-uid="INFO-01-VIS-FACTPACK">
            <div className={styles.headRow}>
              <h2 className={styles.title}>{tx("info.factpack")}</h2>
              <span className={styles.hint}>{tx("info.factpack-hint")}</span>
            </div>
            <div className={styles.headerFields} data-component-uid="INFO-01-CMP-FACTPACK-HEADER">
              <Field uid="INFO-01-FLD-FACTPACK-REF" label={tx("info.fld-factpack-ref")} value={v("INFO-01-FLD-FACTPACK-REF")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="INFO-01-FLD-FACTPACK-SCOPE" label={tx("info.fld-factpack-scope")} value={v("INFO-01-FLD-FACTPACK-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="INFO-01-FLD-FACTPACK-STATE" label={tx("info.fld-factpack-state")} value={v("INFO-01-FLD-FACTPACK-STATE")} loading={loading} onAct={act} disabled={disabled} />
            </div>
            <div data-component-uid="INFO-01-CMP-FACTPACK-LIST">
              <Field uid="INFO-01-LST-FACTPACKS" label={tx("info.lst-factpacks")} value={v("INFO-01-LST-FACTPACKS")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-FACTPACK-SOURCE-COUNT" label={tx("info.fld-factpack-source-count")} value={v("INFO-01-FLD-FACTPACK-SOURCE-COUNT")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
          </section>

          <section className={styles.panel} data-section-uid="INFO-01-SEC-05" data-visual-uid="INFO-01-VIS-FACT">
            <div className={styles.tabs}>
              <button
                type="button"
                className={`${styles.btn} ${styles.tab} ${tab === "FACT" ? styles.btnPrimary : ""}`}
                data-control-uid="INFO-01-TAB-FACT"
                data-component-uid="INFO-01-CMP-FACT"
                disabled={disabled}
                onClick={() => selectTab("FACT")}
              >
                {tx("info.tab-fact")}
              </button>
              <button
                type="button"
                className={`${styles.btn} ${styles.tab} ${tab === "INFERENCE" ? styles.btnPrimary : ""}`}
                data-control-uid="INFO-01-TAB-INFERENCE"
                data-component-uid="INFO-01-CMP-INFERENCE"
                disabled={disabled}
                onClick={() => selectTab("INFERENCE")}
              >
                {tx("info.tab-inference")}
              </button>
            </div>
            <div className={styles.selected}>
              <p className={styles.selectedTitle}>{tab === "FACT" ? tx("info.selected-item") : tx("info.inference-item")}</p>
              <Kv uid="INFO-01-LST-FACTS" label={tx("info.lst-facts")} value={v("INFO-01-LST-FACTS")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-LST-INFERENCES" label={tx("info.lst-inferences")} value={v("INFO-01-LST-INFERENCES")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-ITEM-CLASS" label={tx("info.fld-item-class")} value={v("INFO-01-FLD-ITEM-CLASS")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-ITEM-SCOPE" label={tx("info.fld-item-scope")} value={v("INFO-01-FLD-ITEM-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-ITEM-SOURCE-TIME" label={tx("info.fld-item-source-time")} value={v("INFO-01-FLD-ITEM-SOURCE-TIME")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-ITEM-EVIDENCE" label={tx("info.fld-item-evidence")} value={v("INFO-01-FLD-ITEM-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
            </div>
          </section>

          <section className={styles.panel} data-section-uid="INFO-01-SEC-06" data-visual-uid="INFO-01-VIS-EVIDENCE">
            <div className={styles.evidence}>
              <div className={styles.evidenceHead}>
                <h2 className={styles.title}>{tx("info.evidence")}</h2>
                <Btn uid="INFO-01-BTN-CITATION" label={tx("info.btn-citation")} onAct={act} disabled={disabled} />
              </div>
              <div data-component-uid="INFO-01-CMP-EVIDENCE">
                <Kv uid="INFO-01-LST-EVIDENCE" label={tx("info.lst-evidence")} value={v("INFO-01-LST-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
              </div>
              <div data-component-uid="INFO-01-CMP-SOURCE-META">
                <Kv uid="INFO-01-FLD-EVIDENCE-REF" label={tx("info.fld-evidence-ref")} value={v("INFO-01-FLD-EVIDENCE-REF")} loading={loading} onAct={act} disabled={disabled} />
                <Kv uid="INFO-01-FLD-EVIDENCE-SOURCE" label={tx("info.fld-evidence-source")} value={v("INFO-01-FLD-EVIDENCE-SOURCE")} loading={loading} onAct={act} disabled={disabled} />
                <Kv uid="INFO-01-FLD-EVIDENCE-TIME" label={tx("info.fld-evidence-time")} value={v("INFO-01-FLD-EVIDENCE-TIME")} loading={loading} onAct={act} disabled={disabled} />
                <Kv uid="INFO-01-FLD-EVIDENCE-SCOPE" label={tx("info.fld-evidence-scope")} value={v("INFO-01-FLD-EVIDENCE-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
                <Kv uid="INFO-01-FLD-EVIDENCE-CLASS" label={tx("info.fld-evidence-class")} value={v("INFO-01-FLD-EVIDENCE-CLASS")} loading={loading} onAct={act} disabled={disabled} />
              </div>
            </div>
          </section>
        </main>

        <aside className={styles.col}>
          <section className={styles.panel} data-section-uid="INFO-01-SEC-07" data-component-uid="INFO-01-CMP-QUALITY" data-visual-uid="INFO-01-VIS-RIGHT-QUALITY">
            <div className={styles.headRow}>
              <h2 className={styles.title}>{tx("info.quality")}</h2>
              <span className={styles.hint}>{tx("info.quality-hint")}</span>
            </div>
            <div className={styles.stack}>
              <Field uid="INFO-01-FLD-FRESHNESS" label={tx("info.fld-freshness")} value={v("INFO-01-FLD-FRESHNESS")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-COMPLETENESS" label={tx("info.fld-completeness")} value={v("INFO-01-FLD-COMPLETENESS")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-CONFIDENCE" label={tx("info.fld-confidence")} value={v("INFO-01-FLD-CONFIDENCE")} loading={loading} onAct={act} disabled={disabled} row />
              <Field uid="INFO-01-FLD-VERIFICATION-TIME" label={tx("info.fld-verification-time")} value={v("INFO-01-FLD-VERIFICATION-TIME")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
          </section>

          <section className={styles.panel} data-section-uid="INFO-01-SEC-08" data-component-uid="INFO-01-CMP-RESEARCH" data-visual-uid="INFO-01-VIS-RIGHT-RESEARCH">
            <h2 className={styles.title}>{tx("info.research")}</h2>
            <div className={styles.stack}>
              <Kv uid="INFO-01-LST-RESEARCH" label={tx("info.lst-research")} value={v("INFO-01-LST-RESEARCH")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-RESEARCH-REF" label={tx("info.fld-research-ref")} value={v("INFO-01-FLD-RESEARCH-REF")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-RESEARCH-STATE" label={tx("info.fld-research-state")} value={v("INFO-01-FLD-RESEARCH-STATE")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-RESEARCH-SCOPE" label={tx("info.fld-research-scope")} value={v("INFO-01-FLD-RESEARCH-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
              <Kv uid="INFO-01-FLD-RESEARCH-RESULT" label={tx("info.fld-research-result")} value={v("INFO-01-FLD-RESEARCH-RESULT")} loading={loading} onAct={act} disabled={disabled} />
            </div>
            <p className={styles.readonly}>{tx("info.research-readonly")}</p>
          </section>
        </aside>
      </div>

      <section className={styles.panel} data-section-uid="INFO-01-SEC-09" data-visual-uid="INFO-01-VIS-CANDIDATE">
        <div className={styles.headRow}>
          <h2 className={styles.title}>{tx("info.candidate")}</h2>
          <span className={styles.hint}>{tx("info.candidate-hint")}</span>
        </div>
        <div className={styles.headerFields}>
          <Field uid="INFO-01-FLD-CANDIDATE-ID" label={tx("info.fld-candidate-id")} value={v("INFO-01-FLD-CANDIDATE-ID")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="INFO-01-FLD-CANDIDATE-SCOPE" label={tx("info.fld-candidate-scope")} value={v("INFO-01-FLD-CANDIDATE-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="INFO-01-FLD-CANDIDATE-STATE" label={tx("info.fld-candidate-state")} value={v("INFO-01-FLD-CANDIDATE-STATE")} loading={loading} onAct={act} disabled={disabled} />
        </div>
        <div className={styles.candidateGrid}>
          <div className={styles.stack} data-component-uid="INFO-01-CMP-CANDIDATE-FACTS">
            <h2 className={styles.title}>{tx("info.fact-selection")}</h2>
            <Field uid="INFO-01-LST-CANDIDATES" label={tx("info.lst-candidates")} value={v("INFO-01-LST-CANDIDATES")} loading={loading} onAct={act} disabled={disabled} row />
            <Field uid="INFO-01-FLD-CANDIDATE-FACTS" label={tx("info.fld-candidate-facts")} value={v("INFO-01-FLD-CANDIDATE-FACTS")} loading={loading} onAct={act} disabled={disabled} row />
            <div className={styles.noteBox} data-component-uid="INFO-01-CMP-CANDIDATE-SCOPE">
              <p className={styles.selectedTitle}>{tx("info.selection-rule")}</p>
              <p className={styles.note}>{tx("info.selection-rule-1")}</p>
              <p className={styles.note}>{tx("info.selection-rule-2")}</p>
            </div>
          </div>
          <div className={styles.stack} data-component-uid="INFO-01-CMP-CANDIDATE-CITATION">
            <h2 className={styles.title}>{tx("info.citation-preview")}</h2>
            <Field uid="INFO-01-FLD-CANDIDATE-CITATIONS" label={tx("info.fld-candidate-citations")} value={v("INFO-01-FLD-CANDIDATE-CITATIONS")} loading={loading} onAct={act} disabled={disabled} row />
            <div data-component-uid="INFO-01-CMP-CANDIDATE-PREVIEW">
              <Field uid="INFO-01-FLD-CANDIDATE-PREVIEW" label={tx("info.fld-candidate-preview")} value={v("INFO-01-FLD-CANDIDATE-PREVIEW")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
            <div data-component-uid="INFO-01-CMP-ADOPTION-REVIEW">
              <Field uid="INFO-01-FLD-ADOPTION-REVIEW" label={tx("info.fld-adoption-review")} value={v("INFO-01-FLD-ADOPTION-REVIEW")} loading={loading} onAct={act} disabled={disabled} row />
            </div>
            <div className={styles.noteBox}>
              <p className={styles.selectedTitle}>{tx("info.adoption-boundary")}</p>
              <p className={`${styles.note} ${styles.ok}`}>{tx("info.adoption-ok")}</p>
              <p className={`${styles.note} ${styles.warn}`}>{tx("info.adoption-forbid")}</p>
            </div>
          </div>
          <div className={styles.stack} data-section-uid="INFO-01-SEC-11" data-component-uid="INFO-01-CMP-ACTIONS" data-visual-uid="INFO-01-VIS-ACTION">
            <div className={styles.headRow}>
              <h2 className={styles.title}>{tx("info.actions")}</h2>
              <span className={styles.hint}>{tx("info.actions-hint")}</span>
            </div>
            <Btn uid="INFO-01-BTN-EXPORT" label={tx("info.btn-export")} onAct={act} disabled={disabled} />
            <Btn uid="INFO-01-BTN-CANDIDATE-DECIDE" label={tx("info.btn-candidate-decide")} onAct={act} disabled={disabled} />
            <Btn uid="INFO-01-BTN-ADOPT-CONTEXT" label={tx("info.btn-adopt-context")} onAct={act} disabled={disabled} primary />
            <div className={styles.noteBox}>
              <p className={styles.selectedTitle}>{tx("info.gate-note")}</p>
              <p className={styles.note}>{tx("info.gate-note-1")}</p>
              <p className={styles.note}>{tx("info.gate-note-2")}</p>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.panel} data-section-uid="INFO-01-SEC-10" data-component-uid="INFO-01-CMP-CITATION" data-visual-uid="INFO-01-VIS-CITATION">
        <div className={styles.headRow}>
          <h2 className={styles.title}>{tx("info.citation")}</h2>
          <span className={styles.hint}>{tx("info.citation-hint")}</span>
        </div>
        <div className={styles.headerFields}>
          <Field uid="INFO-01-FLD-CITATION-REF" label={tx("info.fld-citation-ref")} value={v("INFO-01-FLD-CITATION-REF")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="INFO-01-FLD-CITATION-SOURCE" label={tx("info.fld-citation-source")} value={v("INFO-01-FLD-CITATION-SOURCE")} loading={loading} onAct={act} disabled={disabled} />
          <Field uid="INFO-01-FLD-CITATION-EVIDENCE" label={tx("info.fld-citation-evidence")} value={v("INFO-01-FLD-CITATION-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
        </div>
        <Field uid="INFO-01-FLD-CITATION-TIME" label={tx("info.fld-citation-time")} value={v("INFO-01-FLD-CITATION-TIME")} loading={loading} onAct={act} disabled={disabled} row />
        <p className={`${styles.note} ${styles.warn}`}>{tx("info.citation-rule")}</p>
      </section>

      <section className={`${styles.panel} ${styles.actionRow}`} data-section-uid="INFO-01-SEC-12" data-component-uid="INFO-01-CMP-STATUS" data-visual-uid="INFO-01-VIS-STATUS">
        <Field uid="INFO-01-FLD-FIREWALL" label={tx("info.fld-firewall")} value={v("INFO-01-FLD-FIREWALL")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="INFO-01-FLD-CORRELATION" label={tx("info.fld-correlation")} value={v("INFO-01-FLD-CORRELATION")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="INFO-01-FLD-SOURCE-SYNC" label={tx("info.fld-source-sync")} value={v("INFO-01-FLD-SOURCE-SYNC")} loading={loading} onAct={act} disabled={disabled} />
        <Field uid="INFO-01-FLD-DISABLED" label={tx("info.fld-disabled")} value={v("INFO-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
        <div className={styles.actionButtons}>
          <Btn uid="INFO-01-BTN-AUDIT" label={tx("info.btn-audit")} onAct={act} disabled={disabled} />
        </div>
      </section>

      <div className={styles.split}>
        <section className={styles.panel}>
          <div className={styles.headRow}>
            <h2 className={styles.title}>{tx("info.allowed")}</h2>
            <span className={styles.hint}>{tx("info.allowed-hint")}</span>
          </div>
          <div className={styles.stack}>
            <div className={styles.allow}>{tx("info.allow-1")}</div>
            <div className={styles.allow}>{tx("info.allow-2")}</div>
            <div className={styles.allow}>{tx("info.allow-3")}</div>
            <div className={styles.allow}>{tx("info.allow-4")}</div>
            <div className={styles.allow}>{tx("info.allow-5")}</div>
          </div>
        </section>
        <section className={styles.panel}>
          <div className={styles.headRow}>
            <h2 className={styles.title}>{tx("info.forbidden")}</h2>
            <span className={styles.hint}>{tx("info.forbidden-hint")}</span>
          </div>
          <div className={styles.stack}>
            <div className={styles.forbid}>{tx("info.forbid-1")}</div>
            <div className={styles.forbid}>{tx("info.forbid-2")}</div>
            <div className={styles.forbid}>{tx("info.forbid-3")}</div>
            <div className={styles.forbid}>{tx("info.forbid-4")}</div>
            <div className={styles.forbid}>{tx("info.forbid-5")}</div>
          </div>
        </section>
      </div>

      <section className={styles.panel}>
        <div className={styles.headRow}>
          <h2 className={styles.title}>{tx("info.ops")}</h2>
          <span className={styles.hint}>{tx("info.ops-hint")}</span>
        </div>
        <div className={styles.ops}>
          <div className={styles.op}>
            <span className={styles.opName}>{tx("info.op-refresh")}</span>
            <span className={styles.opScope}>projection.refresh</span>
            <span className={styles.opGate}>{tx("info.op-gate")}</span>
          </div>
          <div className={styles.op}>
            <span className={styles.opName}>{tx("info.op-search")}</span>
            <span className={styles.opScope}>projection.search</span>
            <span className={styles.opGate}>{tx("info.op-gate")}</span>
          </div>
          <div className={styles.op}>
            <span className={styles.opName}>{tx("info.op-export")}</span>
            <span className={styles.opScope}>projection.export</span>
            <span className={styles.opGate}>{tx("info.op-gate")}</span>
          </div>
          <div className={styles.op}>
            <span className={styles.opName}>{tx("info.op-adopt")}</span>
            <span className={styles.opScope}>knowledge.candidate.create</span>
            <span className={styles.opGate}>{tx("info.op-gate")}</span>
          </div>
          <div className={styles.op}>
            <span className={styles.opName}>{tx("info.op-decide")}</span>
            <span className={styles.opScope}>candidate.decide</span>
            <span className={styles.opGate}>{tx("info.op-gate")}</span>
          </div>
        </div>
      </section>

      <div className={styles.inventory} aria-hidden="true">
        {INFO_VISIBLE_CONTROLS.filter((uid) => !visibleUids.has(uid)).map((uid) => (
          <button key={uid} type="button" data-control-uid={uid} disabled={disabled} onClick={() => void act(uid)}>
            {uid}
          </button>
        ))}
      </div>
    </div>
  );
}
