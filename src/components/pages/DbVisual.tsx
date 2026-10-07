"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { DbClientError, fetchDbReadModel, postDbAction, type DbFieldValue } from "@/lib/client";
import { displayDbValue } from "./dbFormat";
import { DB_CONTROL_ACTIONS, DB_VISIBLE_CONTROLS } from "./dbControls";
import styles from "./DbVisual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

type DbSurface = "SCHEMA" | "TRACE" | "INTEGRITY" | "CONFLICT";

const ENTITY_GROUPS = ["CANON", "TOPIC_PRODUCTION", "RUNTIME", "GOVERNANCE", "SYSTEM"] as const;

const LINEAGE_CHIPS = [
  "db.chip-source",
  "db.chip-project",
  "db.chip-mother",
  "db.chip-topic",
  "db.chip-child",
  "db.chip-boundary",
  "db.chip-bridge",
  "db.chip-input",
  "db.chip-task",
  "db.chip-output",
  "db.chip-qa",
  "db.chip-release",
] as const;

const TRACE_PATH_CHIPS = [
  "db.chip-project",
  "db.chip-mother-version",
  "db.chip-production-topic",
  "db.chip-child-version",
  "db.chip-boundary",
  "db.chip-continuity-bridge",
  "db.chip-script-dna",
  "db.chip-dept-task",
  "db.chip-provider-job",
  "db.chip-output-version",
  "db.chip-qa-review",
  "db.chip-release",
] as const;

const CHANGE_ROUTE_CHIPS = [
  "db.chip-finding",
  "db.chip-owner-lifecycle",
  "db.chip-change-sandbox",
  "db.chip-human-approval",
  "db.chip-migration-service",
  "db.chip-reinspect",
] as const;

function Field({
  uid,
  label,
  value,
  loading,
  onAct,
  disabled,
  className,
}: {
  uid: string;
  label: string;
  value: string | null;
  loading: boolean;
  onAct: (uid: string) => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <button type="button" className={`${styles.field} ${className ?? ""}`} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{displayDbValue(value, loading)}</span>
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
  const classes = [styles.btn, primary ? styles.btnPrimary : "", className ?? ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={classes} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

export function DbVisual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [fields, setFields] = useState<DbFieldValue[]>([]);
  const [surface, setSurface] = useState<DbSurface>("SCHEMA");

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true);
    fetchDbReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setFields(model.fields.length ? model.fields : DB_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof DbClientError ? cause.code : "DB_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(DB_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
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
    const actionUid = DB_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postDbAction(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
  }, []);

  const disabled = !authorized && !loading;
  const pageState = loading ? "LOADING" : error ? "ERROR" : authorized ? "READY" : "DENIED";
  const tx = (key: TranslationKey) => t(key);
  const v = (uid: string) => valueOf(uid);

  const go = (next: DbSurface, uid?: string) => {
    setSurface(next);
    if (uid) void act(uid);
  };

  const visibleUids = useMemo(() => {
    const uids = new Set<string>();
    if (surface === "SCHEMA") {
      [
        "DB-01-FLD-ENV",
        "DB-01-FLD-SCHEMA-HEAD",
        "DB-01-FLD-MIGRATION-HEAD",
        "DB-01-FLD-SCOPE",
        "DB-01-FLD-HEALTH",
        "DB-01-BTN-REFRESH",
        "DB-01-INP-SEARCH",
        "DB-01-SEL-DOMAIN",
        "DB-01-SEL-ENTITY-TYPE",
        "DB-01-LIST-ENTITIES",
        "DB-01-FLD-ENTITY",
        "DB-01-FLD-TABLE",
        "DB-01-FLD-OWNER",
        "DB-01-FLD-CLASSIFICATION",
        "DB-01-FLD-PK",
        "DB-01-FLD-VERSION-RULE",
        "DB-01-TBL-COLUMNS",
        "DB-01-TOGGLE-RELATION-VIEW",
        "DB-01-GRAPH-RELATIONS",
        "DB-01-FLD-REF-INTEGRITY",
        "DB-01-FLD-ORPHAN",
        "DB-01-FLD-IMMUTABLE",
        "DB-01-FLD-TRACE-COMPLETE",
        "DB-01-FLD-MIGRATION-INTEGRITY",
        "DB-01-BTN-INTEGRITY-REFRESH",
        "DB-01-VIEW-TRACE-PATH",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "TRACE") {
      [
        "DB-01-SEL-TRACE-TYPE",
        "DB-01-INP-TRACE-ID",
        "DB-01-BTN-TRACE",
        "DB-01-TOGGLE-RELATION-VIEW",
        "DB-01-GRAPH-RELATIONS",
        "DB-01-FLD-REF-INTEGRITY",
        "DB-01-FLD-IMMUTABLE",
        "DB-01-FLD-ORPHAN",
        "DB-01-FLD-SCOPE",
        "DB-01-FLD-TRACE-COMPLETE",
        "DB-01-VIEW-TRACE-PATH",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "INTEGRITY") {
      [
        "DB-01-SEL-FINDING-TYPE",
        "DB-01-LIST-FINDINGS",
        "DB-01-INP-MIGRATION-SEARCH",
        "DB-01-BTN-INTEGRITY-REFRESH",
        "DB-01-FLD-FINDING-REASON",
        "DB-01-FLD-FINDING-AFFECTED",
        "DB-01-FLD-FINDING-EVIDENCE",
        "DB-01-FLD-FINDING-OWNER",
        "DB-01-TBL-MIGRATIONS",
        "DB-01-INP-AUDIT-ID",
        "DB-01-BTN-AUDIT",
        "DB-01-VIEW-AUDIT",
      ].forEach((uid) => uids.add(uid));
    }
    if (surface === "CONFLICT") {
      [
        "DB-01-FLD-PAGE-STATE",
        "DB-01-FLD-DISABLED",
        "DB-01-FLD-CHANGE-OWNER",
        "DB-01-BTN-SYSTEM-LIFECYCLE",
        "DB-01-FLD-VERSION-RULE",
        "DB-01-FLD-ENTITY",
        "DB-01-FLD-MIGRATION-INTEGRITY",
        "DB-01-FLD-IMMUTABLE",
        "DB-01-FLD-SOURCE-SYNC",
      ].forEach((uid) => uids.add(uid));
    }
    return uids;
  }, [surface]);

  const relationGraph = (
    <div className={styles.relation} data-control-uid="DB-01-GRAPH-RELATIONS">
      <button type="button" className={styles.chip} disabled={disabled} onClick={() => void act("DB-01-GRAPH-RELATIONS")}>{tx("db.chip-source-ref")}</button>
      <div className={styles.line} />
      <button type="button" className={styles.chip} disabled={disabled} onClick={() => void act("DB-01-GRAPH-RELATIONS")}>{tx("db.chip-exact-entity")}</button>
      <div className={styles.line} />
      <button type="button" className={styles.chip} disabled={disabled} onClick={() => void act("DB-01-GRAPH-RELATIONS")}>{tx("db.chip-version-ref")}</button>
    </div>
  );

  return (
    <div
      className={styles.page}
      data-page-uid="admin:DB-01"
      data-page-state={pageState}
      data-db-surface={surface}
      data-component-count="12"
      data-control-count="49"
      aria-label={tx("db.title")}
    >
      {error ? <div className={styles.error} role="alert">{tx("db.error")}</div> : null}

      <header className={styles.head}>
        <h1 className={styles.title}>{tx("db.title")}</h1>
        <p className={styles.subtitle}>{tx("db.subtitle")}</p>
      </header>

      {surface === "SCHEMA" ? (
        <>
          <section className={styles.panel} data-component-uid="DB-01-CMP-CONTEXT" data-section-uid="DB-01-SEC-01">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.context")}</h2>
              <span className={styles.panelMeta}>DB-01-SEC-01</span>
            </div>
            <div className={styles.row}>
              <Field uid="DB-01-FLD-ENV" label={tx("db.fld-env")} value={v("DB-01-FLD-ENV")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-SCHEMA-HEAD" label={tx("db.fld-schema-head")} value={v("DB-01-FLD-SCHEMA-HEAD")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-MIGRATION-HEAD" label={tx("db.fld-migration-head")} value={v("DB-01-FLD-MIGRATION-HEAD")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-SCOPE" label={tx("db.fld-scope")} value={v("DB-01-FLD-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-HEALTH" label={tx("db.fld-health")} value={v("DB-01-FLD-HEALTH")} loading={loading} onAct={act} disabled={disabled} />
              <Btn uid="DB-01-BTN-REFRESH" label={tx("db.btn-refresh")} onAct={act} disabled={disabled} primary />
            </div>
          </section>

          <div className={styles.grid3}>
            <aside className={`${styles.panel} ${styles.col}`} data-component-uid="DB-01-CMP-EXPLORER" data-section-uid="DB-01-SEC-02">
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.explorer")}</h2>
                <span className={styles.panelMeta}>{tx("db.explorer-meta")}</span>
              </div>
              <button type="button" className={styles.search} data-control-uid="DB-01-INP-SEARCH" disabled={disabled} onClick={() => void act("DB-01-INP-SEARCH")}>
                {tx("db.inp-search")}
              </button>
              <div className={styles.pair}>
                <Btn uid="DB-01-SEL-DOMAIN" label={tx("db.sel-domain")} onAct={act} disabled={disabled} />
                <Btn uid="DB-01-SEL-ENTITY-TYPE" label={tx("db.sel-entity-type")} onAct={act} disabled={disabled} />
              </div>
              <div className={styles.list} data-control-uid="DB-01-LIST-ENTITIES">
                {ENTITY_GROUPS.map((group) => (
                  <button
                    key={group}
                    type="button"
                    className={styles.listItem}
                    disabled={disabled}
                    onClick={() => go("TRACE", "DB-01-LIST-ENTITIES")}
                  >
                    {group}
                    <span>›</span>
                  </button>
                ))}
              </div>
            </aside>

            <section className={`${styles.panel} ${styles.col}`} data-component-uid="DB-01-CMP-SCHEMA" data-section-uid="DB-01-SEC-03">
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.schema")}</h2>
                <span className={styles.panelMeta}>{tx("db.schema-meta")}</span>
              </div>
              <div className={styles.metaGrid}>
                <Field uid="DB-01-FLD-ENTITY" label={tx("db.fld-entity")} value={v("DB-01-FLD-ENTITY")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="DB-01-FLD-TABLE" label={tx("db.fld-table")} value={v("DB-01-FLD-TABLE")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="DB-01-FLD-OWNER" label={tx("db.fld-owner")} value={v("DB-01-FLD-OWNER")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="DB-01-FLD-CLASSIFICATION" label={tx("db.fld-classification")} value={v("DB-01-FLD-CLASSIFICATION")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="DB-01-FLD-PK" label={tx("db.fld-pk")} value={v("DB-01-FLD-PK")} loading={loading} onAct={act} disabled={disabled} />
                <Field uid="DB-01-FLD-VERSION-RULE" label={tx("db.fld-version-rule")} value={v("DB-01-FLD-VERSION-RULE")} loading={loading} onAct={act} disabled={disabled} />
              </div>
              <div className={styles.table} data-component-uid="DB-01-CMP-COLUMNS" data-control-uid="DB-01-TBL-COLUMNS">
                <h3>{tx("db.tbl-columns")}</h3>
                <div className={styles.thead}>
                  <span>{tx("db.col-column")}</span>
                  <span>{tx("db.col-type")}</span>
                  <span>{tx("db.col-nullable")}</span>
                  <span>{tx("db.col-default")}</span>
                </div>
                <div className={styles.trow}>
                  <span>{tx("db.no-entity")}</span>
                  <span />
                  <span />
                  <span />
                </div>
              </div>
              <div className={styles.panelHead} data-component-uid="DB-01-CMP-RELATIONS" data-section-uid="DB-01-SEC-04">
                <h3 className={styles.panelTitle}>{tx("db.relation")}</h3>
                <Btn uid="DB-01-TOGGLE-RELATION-VIEW" label={tx("db.toggle-relation")} onAct={act} disabled={disabled} />
              </div>
              {relationGraph}
            </section>

            <aside className={`${styles.panel} ${styles.col}`} data-component-uid="DB-01-CMP-INTEGRITY" data-section-uid="DB-01-SEC-06">
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.integrity")}</h2>
                <span className={styles.panelMeta}>{tx("db.integrity-meta")}</span>
              </div>
              <Field uid="DB-01-FLD-REF-INTEGRITY" label={tx("db.fld-ref-integrity")} value={v("DB-01-FLD-REF-INTEGRITY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-ORPHAN" label={tx("db.fld-orphan")} value={v("DB-01-FLD-ORPHAN")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-IMMUTABLE" label={tx("db.fld-immutable")} value={v("DB-01-FLD-IMMUTABLE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-TRACE-COMPLETE" label={tx("db.fld-trace-complete")} value={v("DB-01-FLD-TRACE-COMPLETE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-MIGRATION-INTEGRITY" label={tx("db.fld-migration-integrity")} value={v("DB-01-FLD-MIGRATION-INTEGRITY")} loading={loading} onAct={act} disabled={disabled} />
              <Btn uid="DB-01-BTN-INTEGRITY-REFRESH" label={tx("db.btn-integrity-refresh")} onAct={(uid) => go("INTEGRITY", uid)} disabled={disabled} className={styles.fullBtn} />
              <div className={styles.warn}>{tx("db.mutation-forbidden")}</div>
            </aside>
          </div>

          <section className={styles.panel} data-component-uid="DB-01-CMP-TRACE-PATH" data-section-uid="DB-01-SEC-05">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.lineage")}</h2>
              <span className={styles.panelMeta}>{tx("db.lineage-meta")}</span>
            </div>
            <div className={styles.lineageTrack} data-control-uid="DB-01-VIEW-TRACE-PATH">
              {LINEAGE_CHIPS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={styles.lineageChip}
                  disabled={disabled}
                  onClick={() => go("TRACE", "DB-01-VIEW-TRACE-PATH")}
                >
                  {tx(key)}
                </button>
              ))}
            </div>
          </section>
        </>
      ) : null}

      {surface === "TRACE" ? (
        <>
          <section className={styles.panel} data-component-uid="DB-01-CMP-TRACE-INPUT" data-section-uid="DB-01-SEC-05">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.trace-source")}</h2>
              <span className={styles.panelMeta}>{tx("db.trace-source-meta")}</span>
            </div>
            <div className={styles.row}>
              <Field uid="DB-01-SEL-TRACE-TYPE" label={tx("db.sel-trace-type")} value={v("DB-01-SEL-TRACE-TYPE")} loading={loading} onAct={act} disabled={disabled} className={styles.narrow} />
              <Field uid="DB-01-INP-TRACE-ID" label={tx("db.inp-trace-id")} value={v("DB-01-INP-TRACE-ID")} loading={loading} onAct={act} disabled={disabled} />
              <Btn uid="DB-01-BTN-TRACE" label={tx("db.btn-trace")} onAct={act} disabled={disabled} primary />
            </div>
          </section>
          <div className={styles.split2}>
            <section className={`${styles.panel} ${styles.col}`} data-component-uid="DB-01-CMP-RELATIONS" data-section-uid="DB-01-SEC-04">
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.exact-relation")}</h2>
                <Btn uid="DB-01-TOGGLE-RELATION-VIEW" label={tx("db.toggle-relation")} onAct={act} disabled={disabled} />
              </div>
              {relationGraph}
              <p className={styles.emptyHint}>{tx("db.relation-empty")}</p>
            </section>
            <aside className={`${styles.panel} ${styles.col}`} data-component-uid="DB-01-CMP-INTEGRITY" data-section-uid="DB-01-SEC-06">
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.trace-integrity")}</h2>
                <span className={styles.panelMeta}>{tx("db.no-silent-repair")}</span>
              </div>
              <Field uid="DB-01-FLD-REF-INTEGRITY" label={tx("db.exact-ref-exists")} value={v("DB-01-FLD-REF-INTEGRITY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-IMMUTABLE" label={tx("db.version-immutable")} value={v("DB-01-FLD-IMMUTABLE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-ORPHAN" label={tx("db.no-orphan")} value={v("DB-01-FLD-ORPHAN")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-SCOPE" label={tx("db.scope-valid")} value={v("DB-01-FLD-SCOPE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-TRACE-COMPLETE" label={tx("db.audit-correlation")} value={v("DB-01-FLD-TRACE-COMPLETE")} loading={loading} onAct={act} disabled={disabled} />
              <div className={styles.danger}>{tx("db.broken-path")}</div>
            </aside>
          </div>
          <section className={styles.panel} data-component-uid="DB-01-CMP-TRACE-PATH">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.canonical-path")}</h2>
              <span className={styles.panelMeta}>{tx("db.canonical-path-meta")}</span>
            </div>
            <div className={styles.pathTrack} data-control-uid="DB-01-VIEW-TRACE-PATH">
              {TRACE_PATH_CHIPS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={styles.lineageChip}
                  disabled={disabled}
                  onClick={() => void act("DB-01-VIEW-TRACE-PATH")}
                >
                  {tx(key)}
                </button>
              ))}
            </div>
          </section>
        </>
      ) : null}

      {surface === "INTEGRITY" ? (
        <>
          <section className={styles.panel} data-component-uid="DB-01-CMP-FINDINGS" data-section-uid="DB-01-SEC-08">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.integrity-context")}</h2>
              <span className={styles.panelMeta}>{tx("db.no-production-repair")}</span>
            </div>
            <div className={styles.row}>
              <Field uid="DB-01-SEL-FINDING-TYPE" label={tx("db.sel-finding-type")} value={v("DB-01-SEL-FINDING-TYPE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-LIST-FINDINGS" label={tx("db.list-findings")} value={v("DB-01-LIST-FINDINGS")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-INP-MIGRATION-SEARCH" label={tx("db.inp-migration-search")} value={v("DB-01-INP-MIGRATION-SEARCH")} loading={loading} onAct={act} disabled={disabled} />
              <Btn uid="DB-01-BTN-INTEGRITY-REFRESH" label={tx("db.btn-integrity-refresh")} onAct={act} disabled={disabled} />
            </div>
          </section>
          <div className={styles.split2}>
            <section className={`${styles.panel} ${styles.col}`}>
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.finding-detail")}</h2>
                <span className={styles.panelMeta}>DB-01-SEC-08</span>
              </div>
              <Field uid="DB-01-FLD-FINDING-REASON" label={tx("db.fld-finding-reason")} value={v("DB-01-FLD-FINDING-REASON")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-FINDING-AFFECTED" label={tx("db.fld-finding-affected")} value={v("DB-01-FLD-FINDING-AFFECTED")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-FINDING-EVIDENCE" label={tx("db.fld-finding-evidence")} value={v("DB-01-FLD-FINDING-EVIDENCE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-FINDING-OWNER" label={tx("db.fld-finding-owner")} value={v("DB-01-FLD-FINDING-OWNER")} loading={loading} onAct={act} disabled={disabled} />
              <div className={styles.warn}>{tx("db.repair-route")}</div>
            </section>
            <section className={`${styles.panel} ${styles.col}`} data-component-uid="DB-01-CMP-MIGRATION" data-section-uid="DB-01-SEC-07">
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.migration")}</h2>
                <span className={styles.panelMeta}>{tx("db.migration-meta")}</span>
              </div>
              <div className={styles.migrationHead}>
                <span>{tx("db.mig-id")}</span>
                <span>{tx("db.mig-checksum")}</span>
                <span>{tx("db.mig-approval")}</span>
                <span>{tx("db.mig-dependency")}</span>
                <span>{tx("db.mig-applied")}</span>
                <span>{tx("db.mig-status")}</span>
              </div>
              <button type="button" className={styles.migrationRow} data-control-uid="DB-01-TBL-MIGRATIONS" disabled={disabled} onClick={() => void act("DB-01-TBL-MIGRATIONS")}>
                <span>{tx("db.no-migration")}</span>
              </button>
            </section>
          </div>
          <section className={styles.panel} data-component-uid="DB-01-CMP-AUDIT" data-section-uid="DB-01-SEC-09">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.audit")}</h2>
              <span className={styles.panelMeta}>{tx("db.audit-meta")}</span>
            </div>
            <div className={styles.row}>
              <Field uid="DB-01-INP-AUDIT-ID" label={tx("db.inp-audit-id")} value={v("DB-01-INP-AUDIT-ID")} loading={loading} onAct={act} disabled={disabled} />
              <Btn uid="DB-01-BTN-AUDIT" label={tx("db.btn-audit")} onAct={act} disabled={disabled} />
            </div>
            <div className={styles.auditTable} data-control-uid="DB-01-VIEW-AUDIT">
              <span>{tx("db.audit-timestamp")}</span>
              <span>{tx("db.audit-actor")}</span>
              <span>{tx("db.audit-event")}</span>
              <span>{tx("db.audit-entity")}</span>
              <span>{tx("db.audit-corr-col")}</span>
              <span>{tx("db.audit-before-after")}</span>
              <span>—</span>
              <span>—</span>
              <span>—</span>
              <span>—</span>
              <span>—</span>
              <span>—</span>
            </div>
            <button type="button" className={styles.field} style={{ marginTop: 10, minHeight: 56 }} disabled={disabled} onClick={() => go("CONFLICT")}>
              <span className={styles.label}>{tx("db.boundary")}</span>
              <span className={styles.value}>{tx("db.boundary-body")}</span>
            </button>
          </section>
        </>
      ) : null}

      {surface === "CONFLICT" ? (
        <>
          <section className={styles.panel} data-component-uid="DB-01-CMP-STATUS" data-section-uid="DB-01-SEC-10">
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.state-boundary")}</h2>
              <span className={styles.panelMeta}>DB-01-ST-CONFLICT · READ_ONLY</span>
            </div>
            <div className={styles.row}>
              <Field uid="DB-01-FLD-PAGE-STATE" label={tx("db.fld-page-state")} value={v("DB-01-FLD-PAGE-STATE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-DISABLED" label={tx("db.fld-disabled")} value={v("DB-01-FLD-DISABLED")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-CHANGE-OWNER" label={tx("db.fld-change-owner")} value={v("DB-01-FLD-CHANGE-OWNER")} loading={loading} onAct={act} disabled={disabled} />
              <Btn uid="DB-01-BTN-SYSTEM-LIFECYCLE" label={tx("db.btn-system-lifecycle")} onAct={act} disabled={disabled} primary />
            </div>
          </section>
          <div className={styles.split2}>
            <section className={`${styles.panel} ${styles.col}`}>
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.version-conflict")}</h2>
                <span className={styles.panelMeta}>{tx("db.no-overwrite")}</span>
              </div>
              <Field uid="DB-01-FLD-VERSION-RULE" label={tx("db.selected-version")} value={v("DB-01-FLD-VERSION-RULE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-ENTITY" label={tx("db.source-version-ref")} value={v("DB-01-FLD-ENTITY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-MIGRATION-INTEGRITY" label={tx("db.hash-checksum")} value={v("DB-01-FLD-MIGRATION-INTEGRITY")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-IMMUTABLE" label={tx("db.published-locked")} value={v("DB-01-FLD-IMMUTABLE")} loading={loading} onAct={act} disabled={disabled} />
              <Field uid="DB-01-FLD-SOURCE-SYNC" label={tx("db.conflict-reason")} value={v("DB-01-FLD-SOURCE-SYNC")} loading={loading} onAct={act} disabled={disabled} />
              <div className={styles.danger}>{tx("db.downstream-blocked")}</div>
            </section>
            <section className={`${styles.panel} ${styles.col}`}>
              <div className={styles.panelHead}>
                <h2 className={styles.panelTitle}>{tx("db.allowed-forbidden")}</h2>
                <span className={styles.panelMeta}>{tx("db.allowed-meta")}</span>
              </div>
              <div className={styles.allowGrid}>
                <div className={styles.ok}>{tx("db.allowed")}</div>
                <div className={styles.danger}>{tx("db.forbidden")}</div>
                <div>{tx("db.allow-inspect")}</div>
                <div>{tx("db.forbid-sql")}</div>
                <div>{tx("db.allow-trace")}</div>
                <div>{tx("db.forbid-edit")}</div>
                <div>{tx("db.allow-migration")}</div>
                <div>{tx("db.forbid-alter")}</div>
                <div>{tx("db.allow-integrity")}</div>
                <div>{tx("db.forbid-execute")}</div>
                <div>{tx("db.allow-audit")}</div>
                <div>{tx("db.forbid-repair")}</div>
              </div>
            </section>
          </div>
          <section className={styles.panel}>
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>{tx("db.change-route")}</h2>
              <span className={styles.panelMeta}>{tx("db.change-route-meta")}</span>
            </div>
            <div className={styles.pathTrack}>
              {CHANGE_ROUTE_CHIPS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={styles.lineageChip}
                  disabled={disabled}
                  onClick={() => void act("DB-01-BTN-SYSTEM-LIFECYCLE")}
                >
                  {tx(key)}
                </button>
              ))}
            </div>
          </section>
        </>
      ) : null}

      <div className={styles.inventory} aria-hidden="true">
        {DB_VISIBLE_CONTROLS.filter((uid) => !visibleUids.has(uid)).map((uid) => (
          <button
            key={uid}
            type="button"
            data-control-uid={uid}
            disabled={disabled}
            onClick={() => {
              if (uid === "DB-01-BTN-TRACE" || uid === "DB-01-SEL-TRACE-TYPE" || uid === "DB-01-INP-TRACE-ID") go("TRACE", uid);
              else if (uid === "DB-01-BTN-INTEGRITY-REFRESH" || uid === "DB-01-BTN-AUDIT" || uid === "DB-01-TBL-MIGRATIONS" || uid === "DB-01-BTN-MIGRATION-REFRESH") go("INTEGRITY", uid);
              else if (uid === "DB-01-BTN-SYSTEM-LIFECYCLE") go("CONFLICT", uid);
              else void act(uid);
            }}
          >
            {uid}
          </button>
        ))}
        {surface === "SCHEMA" ? null : (
          <>
            <div data-component-uid="DB-01-CMP-CONTEXT" />
            <div data-component-uid="DB-01-CMP-EXPLORER" />
            <div data-component-uid="DB-01-CMP-SCHEMA" />
            <div data-component-uid="DB-01-CMP-COLUMNS" />
          </>
        )}
        {surface === "TRACE" ? null : <div data-component-uid="DB-01-CMP-TRACE-INPUT" />}
        {surface === "INTEGRITY" ? null : (
          <>
            <div data-component-uid="DB-01-CMP-MIGRATION" />
            <div data-component-uid="DB-01-CMP-FINDINGS" />
            <div data-component-uid="DB-01-CMP-AUDIT" />
          </>
        )}
        {surface === "CONFLICT" ? null : <div data-component-uid="DB-01-CMP-STATUS" />}
        {surface === "SCHEMA" || surface === "TRACE" ? null : (
          <>
            <div data-component-uid="DB-01-CMP-RELATIONS" />
            <div data-component-uid="DB-01-CMP-TRACE-PATH" />
            <div data-component-uid="DB-01-CMP-INTEGRITY" />
          </>
        )}
      </div>
    </div>
  );
}
