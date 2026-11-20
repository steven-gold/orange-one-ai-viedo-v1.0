"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TranslationKey } from "@/i18n/catalog";
import { useI18n } from "@/i18n/LocaleProvider";
import { Sg02ClientError, fetchSg02ReadModel, postSg02Action, type Sg02FieldValue } from "@/lib/client";
import { deriveSg02PageState, displaySg02Value } from "./sg02Format";
import {
  SG02_CONTROL_ACTIONS,
  SG02_LIFECYCLE_ROWS,
  SG02_TABLE_COLUMNS,
  SG02_VISIBLE_CONTROLS,
  SG02_STATE_APPROVALS_UID,
  SG02_STATE_AUDIT_UID,
  SG02_STATE_CHECKS_UID,
  SG02_STATE_CRITERIA_UID,
  SG02_STATE_DIMENSIONS_UID,
  SG02_STATE_ERROR_UID,
  SG02_STATE_IDEMPOTENCY_UID,
  SG02_STATE_MAPPINGS_UID,
  SG02_STATE_POLICIES_UID,
  SG02_STATE_RESOURCE_UID,
  SG02_STATE_THRESHOLDS_UID,
  type Sg02Drawer,
  type Sg02Surface,
} from "./sg02Controls";
import styles from "./Sg02Visual.module.css";

const DEFAULT_ACCOUNT = "ACC-DEMO";
const DEFAULT_SESSION = "sess-demo-001";

function Btn({
  uid,
  label,
  onAct,
  disabled,
  primary = false,
  warn = false,
}: {
  uid: string;
  label: string;
  onAct: (uid: string) => void;
  disabled: boolean;
  primary?: boolean;
  warn?: boolean;
}) {
  const className = [styles.btn, primary ? styles.btnPrimary : "", warn ? styles.btnWarn : ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={className} data-control-uid={uid} disabled={disabled} onClick={() => onAct(uid)}>
      {label}
    </button>
  );
}

function Kv({
  uid,
  label,
  value,
}: {
  uid: string;
  label: string;
  value: string;
}) {
  return (
    <div className={styles.kvRow} data-control-uid={uid}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function stateOf(state: string): (typeof SG02_LIFECYCLE_ROWS)[number] {
  return (SG02_LIFECYCLE_ROWS as readonly string[]).includes(state)
    ? (state as (typeof SG02_LIFECYCLE_ROWS)[number])
    : "DRAFT";
}

function stateClass(state: (typeof SG02_LIFECYCLE_ROWS)[number]): string {
  if (state === "DRAFT") return styles.stateDraft;
  if (state === "REVIEW") return styles.stateReview;
  if (state === "ACTIVE") return styles.stateActive;
  return styles.stateSuperseded;
}

export function Sg02Visual() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);
  const [configureAuthorized, setConfigureAuthorized] = useState(false);
  const [fields, setFields] = useState<Sg02FieldValue[]>([]);
  const [surface, setSurface] = useState<Sg02Surface>("main");
  const [drawer, setDrawer] = useState<Sg02Drawer | null>(null);
  const [modalUid, setModalUid] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const drawerRef = useRef<HTMLElement | null>(null);
  const modalRef = useRef<HTMLElement | null>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    if (tick === 0) setLoading(true);
    fetchSg02ReadModel(DEFAULT_ACCOUNT, DEFAULT_SESSION, controller.signal)
      .then((model) => {
        if (cancelled) return;
        setAuthorized(model.authorized);
        setConfigureAuthorized(model.configureAuthorized);
        setFields(model.fields.length ? model.fields : SG02_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
        setError(null);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setError(cause instanceof Sg02ClientError ? cause.code : "SG02_READ_UNAVAILABLE");
        setAuthorized(false);
        setFields(SG02_VISIBLE_CONTROLS.map((controlUid) => ({ controlUid, value: null })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [tick]);

  const act = useCallback(async (controlUid: string, payload?: string) => {
    const actionUid = SG02_CONTROL_ACTIONS[controlUid];
    if (!actionUid) return;
    try {
      await postSg02Action(DEFAULT_ACCOUNT, controlUid, actionUid, DEFAULT_SESSION, payload);
    } catch {
      // PAGE_ACTION remains fail-closed even if the audit post is unavailable.
    }
    setTick((n) => n + 1);
  }, []);

  const disabled = !authorized && !loading;
  const tx = (key: TranslationKey) => t(key);
  const dash = displaySg02Value(null, loading);
  const visibleUids = useMemo(() => new Set<string>(SG02_VISIBLE_CONTROLS), []);

  const openDrawer = (next: Sg02Drawer, uid: string) => {
    lastFocusedRef.current = document.activeElement as HTMLElement | null;
    setDrawer(next);
    void act(uid);
  };

  const openModal = (uid: string) => {
    // Exact contract form schemas; the modal posts one JSON payload per action.
    lastFocusedRef.current = document.activeElement as HTMLElement | null;
    setModalUid(uid);
    setFormValues(
      uid === "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE"
        ? { resource_type: "quality_criteria_version", resource_id: "", config_patch_json: "", reason: "" }
        : { resource_type: "quality_criteria_version", resource_id: "", rationale: "", expected_resource_version: "" },
    );
  };

  const submitModal = useCallback(async () => {
    if (!modalUid) return;
    setSubmitting(true);
    // Side-effect operations require idempotency_key per contract
    // required_backend_gates (idempotency_when_side_effect).
    const payload = { ...formValues, idempotency_key: `idem-${modalUid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` };
    await act(modalUid, JSON.stringify(payload));
    setSubmitting(false);
    setModalUid(null);
  }, [act, formValues, modalUid]);

  const valueOf = useCallback(
    (uid: string): string | null => {
      const field = fields.find((item) => item.controlUid === uid);
      return field?.value ?? null;
    },
    [fields],
  );

  const contractError = useMemo<{ code: string; detail: string; recovery?: string } | null>(() => {
    const raw = valueOf(SG02_STATE_ERROR_UID);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as { code: string; detail: string; recovery?: string };
    } catch {
      return null;
    }
  }, [valueOf]);

  const resource = useMemo<{ resourceType: string; resourceId: string; version: number; status: string; configPatch: string; updatedAt: string } | null>(() => {
    const raw = valueOf(SG02_STATE_RESOURCE_UID);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as { resourceType: string; resourceId: string; version: number; status: string; configPatch: string; updatedAt: string };
    } catch {
      return null;
    }
  }, [valueOf]);

  // Contract read-model registries (5 read_model_object fields) derived from
  // the runtime STATE projections; empty registry renders missing_value dash.
  const criteriaVersions = useMemo<Array<{ version: number; status: string; configPatch: string; updatedAt: string; supersededBy?: number }>>(() => {
    const raw = valueOf(SG02_STATE_CRITERIA_UID);
    if (!raw) return [];
    try {
      return JSON.parse(raw) as Array<{ version: number; status: string; configPatch: string; updatedAt: string; supersededBy?: number }>;
    } catch {
      return [];
    }
  }, [valueOf]);

  const parseEntries = useCallback((uid: string): Array<{ resourceId: string; version: number; configPatch: string; updatedAt: string }> => {
    const raw = valueOf(uid);
    if (!raw) return [];
    try {
      return JSON.parse(raw) as Array<{ resourceId: string; version: number; configPatch: string; updatedAt: string }>;
    } catch {
      return [];
    }
  }, [valueOf]);

  const dimensions = useMemo(() => parseEntries(SG02_STATE_DIMENSIONS_UID), [parseEntries]);
  const thresholds = useMemo(() => parseEntries(SG02_STATE_THRESHOLDS_UID), [parseEntries]);
  const mappings = useMemo(() => parseEntries(SG02_STATE_MAPPINGS_UID), [parseEntries]);
  const checks = useMemo(() => parseEntries(SG02_STATE_CHECKS_UID), [parseEntries]);
  const policies = useMemo(() => parseEntries(SG02_STATE_POLICIES_UID), [parseEntries]);
  const approvals = useMemo<Array<{ approvalId?: string; resourceType: string; resourceId: string; version: number; approvedAt: string }>>(() => {
    const raw = valueOf(SG02_STATE_APPROVALS_UID);
    if (!raw) return [];
    try {
      return JSON.parse(raw) as Array<{ approvalId?: string; resourceType: string; resourceId: string; version: number; approvedAt: string }>;
    } catch {
      return [];
    }
  }, [valueOf]);
  const idempotency = useMemo<Record<string, string>>(() => {
    const raw = valueOf(SG02_STATE_IDEMPOTENCY_UID);
    if (!raw) return {};
    try {
      return JSON.parse(raw) as Record<string, string>;
    } catch {
      return {};
    }
  }, [valueOf]);
  const auditLines = useMemo(() => {
    const raw = valueOf(SG02_STATE_AUDIT_UID);
    return raw ? raw.split("\n") : [];
  }, [valueOf]);

  const activeCriteria = criteriaVersions.filter((v) => v.status === "ACTIVE");
  const pageState = deriveSg02PageState({
    loading,
    fetchError: error,
    authorized,
    configureAuthorized,
    errorCode: contractError?.code ?? null,
    resourceStatus: resource?.status ?? null,
    hasRuntimeState: criteriaVersions.length > 0 || dimensions.length > 0 || thresholds.length > 0 || mappings.length > 0 || checks.length > 0 || policies.length > 0,
  });

  const openApproval = (uid: string) => {
    setSurface("approval");
    setDrawer("approval");
    void act(uid);
  };

  // Focus management (drawer_modal_contract): focus first focusable element
  // when drawer/modal opens; restore focus to the invoker on close.
  useEffect(() => {
    if (!drawer && !modalUid) return;
    const host = drawer ? drawerRef.current : modalRef.current;
    if (host) {
      const target = host.querySelector<HTMLElement>("input, textarea, button, select");
      if (target) target.focus();
    }
    return () => {
      const prior = lastFocusedRef.current;
      if (prior && document.contains(prior)) prior.focus();
    };
  }, [drawer, modalUid]);

  const drawerTitle = (key: Sg02Drawer): TranslationKey => {
    if (key === "criteria_table") return "sg02.drawer-criteria";
    if (key === "dimension_library") return "sg02.drawer-dimension";
    if (key === "thresholds") return "sg02.drawer-thresholds";
    if (key === "department_mapping") return "sg02.drawer-department";
    if (key === "required_checks") return "sg02.drawer-checks";
    if (key === "gate_policy") return "sg02.drawer-gate";
    if (key === "approval") return "sg02.drawer-approval";
    if (key === "impact") return "sg02.drawer-impact";
    return "sg02.drawer-nav";
  };

  return (
    <div
      className={styles.page}
      data-page-uid="admin:SG-02"
      data-page-state={pageState}
      data-ui-view={surface}
      data-component-count="9"
      data-control-count={visibleUids.size}
      aria-label={tx("sg02.title")}
    >
      {error ? (
        <div className={styles.error} role="alert">
          {tx("sg02.error")}
        </div>
      ) : null}

      {surface === "main" ? (
        <>
          <header className={styles.heading} data-component-uid="SG-02-CMP-CONTEXT" data-section-uid="SEC-ADMIN-SG-02-CRITERIA-TABLE">
            <h1 className={styles.headingTitle}>{tx("sg02.title")}</h1>
            <p className={styles.headingMeta}>{tx("sg02.meta")}</p>
          </header>

          <div className={styles.statusBar} data-section-uid="SEC-ADMIN-SG-02-CRITERIA-TABLE" data-component-uid="SG-02-CMP-STATUS">
            <div className={styles.statusItem}>
              <span>{tx("sg02.status-current")}</span>
              <strong className={styles.chip}>{activeCriteria.length ? `v${activeCriteria[activeCriteria.length - 1].version}` : dash}</strong>
            </div>
            <div className={styles.statusItem}>
              <span>{tx("sg02.status-lifecycle")}</span>
              <strong className={styles.chip}>{resource ? resource.status : dash}</strong>
            </div>
            <button
              type="button"
              className={styles.statusItem}
              data-control-uid="CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN"
              disabled={disabled}
              onClick={() => openDrawer("department_mapping", "CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN")}
            >
              <span>{tx("sg02.status-department")}</span>
              <strong className={styles.chip}>{mappings.length ? `${mappings.length} mappings` : dash}</strong>
            </button>
            <button
              type="button"
              className={styles.statusItem}
              data-control-uid="CTRL-ADMIN-SG-02-IMPACT-OPEN"
              disabled={disabled}
              onClick={() => openDrawer("impact", "CTRL-ADMIN-SG-02-IMPACT-OPEN")}
            >
              <span>{tx("sg02.status-impact")}</span>
              <strong className={styles.chip}>{criteriaVersions.length + dimensions.length + thresholds.length + policies.length + checks.length > 0 ? `${criteriaVersions.length + dimensions.length + thresholds.length + policies.length + checks.length} governed` : dash}</strong>
            </button>
            <Btn
              uid="CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN"
              label={tx("sg02.btn-create")}
              onAct={(uid) => openDrawer("nav", uid)}
              disabled={disabled}
              primary
            />
          </div>

          <div className={styles.cols}>
            <section className={styles.workspace} data-section-uid="SEC-ADMIN-SG-02-CRITERIA-TABLE" data-component-uid="SG-02-CMP-TABLE">
              <h2>{tx("sg02.table-title")}</h2>
              <p className={styles.note}>{tx("sg02.table-hint")}</p>
              <div className={styles.tableWrap}>
                <table className={styles.table} data-control-uid="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN">
                  <thead>
                    <tr>
                    {SG02_TABLE_COLUMNS.map((col) =>
                      col === "sg02.col-threshold" ? (
                        <th key={col}>
                          <button
                            type="button"
                            className={styles.headerBtn}
                            data-control-uid="CTRL-ADMIN-SG-02-GATE-POLICY-OPEN"
                            disabled={disabled}
                            onClick={() => openDrawer("gate_policy", "CTRL-ADMIN-SG-02-GATE-POLICY-OPEN")}
                          >
                            {tx(col)}
                          </button>
                        </th>
                      ) : (
                        <th key={col}>{tx(col)}</th>
                      ),
                    )}
                    </tr>
                  </thead>
                  <tbody>
                    {criteriaVersions.length ? (
                      criteriaVersions.map((version) => (
                        <tr key={version.version}>
                          <td>{`v${version.version}${version.supersededBy ? ` -> v${version.supersededBy}` : ""}`}</td>
                          <td className={stateClass(stateOf(version.status))}>{version.status}</td>
                          <td>{dimensions.length ? `${dimensions.length} dimensions` : dash}</td>
                          <td>{thresholds.length ? `${thresholds.length} thresholds` : dash}</td>
                          <td>{mappings.length ? `${mappings.length} departments` : dash}</td>
                          <td>{approvals.some((a) => a.version === version.version) ? "APPROVED" : dash}</td>
                          <td>{version.configPatch.length > 0 ? dash : dash}</td>
                        </tr>
                      ))
                    ) : (
                      SG02_LIFECYCLE_ROWS.map((state) => (
                        <tr key={state}>
                          <td>{dash}</td>
                          <td className={stateClass(state)}>{state}</td>
                          <td>{dash}</td>
                          <td>{dash}</td>
                          <td>{dash}</td>
                          <td>{dash}</td>
                          <td>{dash}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className={styles.cardGrid}>
                <div className={styles.card} data-section-uid="SEC-ADMIN-SG-02-DIMENSION-LIBRARY">
                  <h3>{tx("sg02.card-dimension")}</h3>
                  <p className={styles.note}>{tx("sg02.card-dimension-hint")}</p>
                  <Btn uid="CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN" label={tx("sg02.btn-drawer")} onAct={(uid) => openDrawer("dimension_library", uid)} disabled={disabled} />
                </div>
                <div className={styles.card} data-section-uid="SEC-ADMIN-SG-02-THRESHOLDS">
                  <h3>{tx("sg02.card-thresholds")}</h3>
                  <p className={styles.note}>{tx("sg02.card-thresholds-hint")}</p>
                  <Btn uid="CTRL-ADMIN-SG-02-THRESHOLDS-OPEN" label={tx("sg02.btn-drawer")} onAct={(uid) => openDrawer("thresholds", uid)} disabled={disabled} />
                </div>
                <div className={styles.card} data-section-uid="SEC-ADMIN-SG-02-REQUIRED-CHECKS">
                  <h3>{tx("sg02.card-checks")}</h3>
                  <p className={styles.note}>{tx("sg02.card-checks-hint")}</p>
                  <Btn uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={tx("sg02.btn-drawer")} onAct={(uid) => openDrawer("required_checks", uid)} disabled={disabled} />
                </div>
              </div>
            </section>

            <aside className={styles.rail} data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK" data-component-uid="SG-02-CMP-RAIL">
              <h2>{tx("sg02.rail-title")}</h2>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-integrity")}</span>
                <strong className={contractError ? styles.required : undefined}>
                  {contractError ? contractError.code : dash}
                </strong>
              </div>
              <button
                type="button"
                className={styles.railCard}
                data-control-uid="CTRL-ADMIN-SG-02-APPROVAL-OPEN"
                disabled={disabled}
                onClick={() => openDrawer("approval", "CTRL-ADMIN-SG-02-APPROVAL-OPEN")}
              >
                <span>{tx("sg02.rail-approval")}</span>
                <strong>{resource ? `${resource.status} · v${resource.version}` : dash}</strong>
              </button>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-impact")}</span>
                <strong>{checks.length || mappings.length ? `${checks.length} checks · ${mappings.length} depts` : dash}</strong>
              </div>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-revalidation")}</span>
                <strong>{activeCriteria.length ? `${activeCriteria.length} active require revalidation` : dash}</strong>
              </div>
              <div className={styles.railCard}>
                <span>{tx("sg02.rail-history")}</span>
                <strong className={styles.required}>{criteriaVersions.length ? `${criteriaVersions.length} versions retained` : tx("sg02.rail-history-value")}</strong>
              </div>
              <h3>{tx("sg02.dock-title")}</h3>
              {contractError ? (
                <p className={styles.note} data-control-uid={SG02_STATE_ERROR_UID}>
                  {contractError.code} · {contractError.detail}
                  {contractError.recovery ? ` · ${contractError.recovery}` : ""}
                </p>
              ) : null}
              {resource ? (
                <div className={styles.railCard} data-control-uid={SG02_STATE_RESOURCE_UID}>
                  <span>{resource.resourceType}/{resource.resourceId}</span>
                  <strong>{resource.status} · v{resource.version}</strong>
                </div>
              ) : null}
              <div className={styles.actions}>
                <Btn uid="CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE" label={tx("sg02.btn-configure")} onAct={openModal} disabled={disabled} primary />
                <Btn uid="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE" label={tx("sg02.btn-approve")} onAct={openApproval} disabled={disabled} />
              </div>
            </aside>
          </div>
        </>
      ) : (
        <>
          <header className={styles.heading} data-component-uid="SG-02-CMP-APPROVAL-CONTEXT" data-section-uid="SEC-ADMIN-SG-02-APPROVAL">
            <h1 className={styles.headingTitle}>{tx("sg02.approval-title")}</h1>
            <p className={styles.headingMeta}>{tx("sg02.approval-meta")}</p>
          </header>

          <div className={styles.cols}>
            <section className={styles.workspace} data-section-uid="SEC-ADMIN-SG-02-APPROVAL" data-component-uid="SG-02-CMP-APPROVAL">
              <h2>{tx("sg02.selected-title")}</h2>
              <div className={styles.summary}>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.col-version")}</span>
                  <strong>{resource ? `v${resource.version}` : dash}</strong>
                </div>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.col-state")}</span>
                  <strong className={resource?.status === "REVIEW" ? styles.stateReview : styles.stateDraft}>
                    {resource ? resource.status : tx("sg02.state-review")}
                  </strong>
                </div>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.field-scope")}</span>
                  <strong>{resource ? resource.resourceType : dash}</strong>
                </div>
                <div className={styles.summaryItem}>
                  <span>{tx("sg02.field-base")}</span>
                  <strong>{resource ? resource.resourceId : dash}</strong>
                </div>
              </div>
              <h2>{tx("sg02.configure-title")}</h2>
              <div className={styles.kvList}>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-resource-type")}</span>
                  <div className={styles.formField}>{resource ? resource.resourceType : tx("sg02.field-resource-type-value")}</div>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-resource-id")}</span>
                  <div className={styles.formField}>{resource ? resource.resourceId : dash}</div>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-patch")}</span>
                  <div className={styles.formField}>{resource ? resource.configPatch : dash}</div>
                </div>
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-reason")}</span>
                  <div className={styles.formField}>{resource ? resource.updatedAt : dash}</div>
                </div>
              </div>
              <h2>{tx("sg02.impact-title")}</h2>
              <div className={styles.kvList}>
                <Kv uid="CTRL-ADMIN-SG-02-IMPACT-OPEN" label={tx("sg02.field-departments")} value={dash} />
                <Kv uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={tx("sg02.field-tasks")} value={dash} />
                <div className={styles.kvRow}>
                  <span>{tx("sg02.field-history")}</span>
                  <strong className={styles.required}>{tx("sg02.field-history-value")}</strong>
                </div>
              </div>
            </section>

            <aside className={styles.rail} data-section-uid="SEC-ADMIN-SG-02-APPROVAL" data-component-uid="SG-02-CMP-APPROVAL-RAIL">
              <h2>{tx("sg02.approval-drawer-title")}</h2>
              <p className={styles.note}>{tx("sg02.field-expected")}</p>
              <div className={styles.formField}>{resource ? `v${resource.version}` : dash}</div>
              <p className={styles.note}>{tx("sg02.field-rationale")}</p>
              <div className={`${styles.formField} ${styles.formArea}`}>{dash}</div>
              <h3>{tx("sg02.gate-title")}</h3>
              <div className={styles.gateList}>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-review")}
                </button>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-impact")}
                </button>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-version")}
                </button>
                <button type="button" className={`${styles.btn} ${styles.btnWarn}`} disabled>
                  {tx("sg02.gate-audit")}
                </button>
              </div>
              <div className={styles.actions}>
                <button type="button" className={styles.btn} disabled={disabled} onClick={() => setSurface("main")}>
                  {tx("sg02.btn-back")}
                </button>
                <Btn uid="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE" label={tx("sg02.btn-approve-version")} onAct={openModal} disabled={disabled} primary />
              </div>
              <p className={styles.note}>{tx("sg02.approval-hint")}</p>
            </aside>
          </div>
        </>
      )}

      {drawer ? (
        <section className={styles.drawer} data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK" data-component-uid="SG-02-CMP-DRAWER" ref={drawerRef}>
          <h3>{tx(drawerTitle(drawer))}</h3>
          <p className={styles.note}>{tx("sg02.drawer-hint")}</p>
          <div className={styles.kvList}>
            {drawer === "criteria_table" ? (
              criteriaVersions.length ? (
                criteriaVersions.map((version) => (
                  <Kv key={version.version} uid="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN" label={`v${version.version}`} value={`${version.status} · ${version.updatedAt.slice(0, 10)}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN" label={tx("sg02.col-version")} value={dash} />
              )
            ) : null}
            {drawer === "dimension_library" ? (
              dimensions.length ? (
                dimensions.map((entry) => (
                  <Kv key={`${entry.resourceId}-${entry.version}`} uid="CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN" label={entry.resourceId} value={`v${entry.version} · ${entry.configPatch.slice(0, 80)}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN" label={tx("sg02.card-dimension")} value={dash} />
              )
            ) : null}
            {drawer === "thresholds" ? (
              thresholds.length ? (
                thresholds.map((entry) => (
                  <Kv key={`${entry.resourceId}-${entry.version}`} uid="CTRL-ADMIN-SG-02-THRESHOLDS-OPEN" label={entry.resourceId} value={`v${entry.version} · ${entry.configPatch.slice(0, 80)}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-THRESHOLDS-OPEN" label={tx("sg02.col-threshold")} value={dash} />
              )
            ) : null}
            {drawer === "department_mapping" ? (
              mappings.length ? (
                mappings.map((entry) => (
                  <Kv key={`${entry.resourceId}-${entry.version}`} uid="CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN" label={entry.resourceId} value={`v${entry.version} · ${entry.configPatch.slice(0, 80)}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN" label={tx("sg02.col-department")} value={dash} />
              )
            ) : null}
            {drawer === "required_checks" ? (
              checks.length ? (
                checks.map((entry) => (
                  <Kv key={`${entry.resourceId}-${entry.version}`} uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={entry.resourceId} value={`v${entry.version} · ${entry.configPatch.slice(0, 80)}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={tx("sg02.card-checks")} value={dash} />
              )
            ) : null}
            {drawer === "gate_policy" ? (
              policies.length ? (
                policies.map((entry) => (
                  <Kv key={`${entry.resourceId}-${entry.version}`} uid="CTRL-ADMIN-SG-02-GATE-POLICY-OPEN" label={entry.resourceId} value={`v${entry.version} · ${entry.configPatch.slice(0, 80)}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-GATE-POLICY-OPEN" label={tx("sg02.col-threshold")} value={dash} />
              )
            ) : null}
            {drawer === "approval" ? (
              approvals.length ? (
                approvals.map((entry) => (
                  <Kv key={String(entry.approvalId ?? entry.resourceId)} uid="CTRL-ADMIN-SG-02-APPROVAL-OPEN" label={String(entry.approvalId ?? dash)} value={`${entry.resourceType}/${entry.resourceId} · v${entry.version}`} />
                ))
              ) : (
                <Kv uid="CTRL-ADMIN-SG-02-APPROVAL-OPEN" label={tx("sg02.rail-approval")} value={resource ? `${resource.status} · v${resource.version}` : dash} />
              )
            ) : null}
            {drawer === "impact" ? (
              <>
                <Kv uid="CTRL-ADMIN-SG-02-IMPACT-OPEN" label={tx("sg02.field-departments")} value={mappings.length ? `${mappings.length} mappings` : dash} />
                <Kv uid="CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN" label={tx("sg02.field-tasks")} value={checks.length ? `${checks.length} checks` : dash} />
              </>
            ) : null}
            {drawer === "nav" ? (
              <Kv uid="CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN" label={tx("sg02.table-title")} value={activeCriteria.length ? `ACTIVE v${activeCriteria[activeCriteria.length - 1].version}` : dash} />
            ) : null}
          </div>
          <button type="button" className={styles.btn} onClick={() => setDrawer(null)}>
            {tx("global.common.close")}
          </button>
        </section>
      ) : null}

      {modalUid ? (
        <section
          className={styles.modal}
          data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK"
          data-component-uid="SG-02-CMP-MODAL"
          data-control-uid={modalUid}
          role="dialog"
          aria-modal="true"
          tabIndex={-1}
          ref={modalRef}
        >
          <h3>{tx("sg02.modal-title")}</h3>
          <p className={styles.note}>{tx("sg02.modal-hint")}</p>
          <div className={styles.kvList}>
            <div className={styles.kvRow}>
              <span>{tx("sg02.field-resource-type")}</span>
              <div className={styles.formField}>
                <input
                  value={formValues.resource_type ?? ""}
                  onChange={(event) => setFormValues((prev) => ({ ...prev, resource_type: event.target.value }))}
                />
              </div>
            </div>
            <div className={styles.kvRow}>
              <span>{tx("sg02.field-resource-id")}</span>
              <div className={styles.formField}>
                <input
                  value={formValues.resource_id ?? ""}
                  onChange={(event) => setFormValues((prev) => ({ ...prev, resource_id: event.target.value }))}
                />
              </div>
            </div>
            {modalUid === "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE" ? (
              <div className={styles.kvRow}>
                <span>{tx("sg02.field-patch")}</span>
                <div className={styles.formField}>
                  <textarea
                    value={formValues.config_patch_json ?? ""}
                    onChange={(event) => setFormValues((prev) => ({ ...prev, config_patch_json: event.target.value }))}
                  />
                </div>
              </div>
            ) : (
              <div className={styles.kvRow}>
                <span>{tx("sg02.field-expected")}</span>
                <div className={styles.formField}>
                  <input
                    value={formValues.expected_resource_version ?? ""}
                    onChange={(event) => setFormValues((prev) => ({ ...prev, expected_resource_version: event.target.value }))}
                  />
                </div>
              </div>
            )}
            <div className={styles.kvRow}>
              <span>{modalUid === "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE" ? tx("sg02.field-reason") : tx("sg02.field-rationale")}</span>
              <div className={`${styles.formField} ${styles.formArea}`}>
                <textarea
                  value={formValues[modalUid === "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE" ? "reason" : "rationale"] ?? ""}
                  onChange={(event) =>
                    setFormValues((prev) => ({
                      ...prev,
                      [modalUid === "CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE" ? "reason" : "rationale"]: event.target.value,
                    }))
                  }
                />
              </div>
            </div>
          </div>
          <div className={styles.actions}>
            <button type="button" className={styles.btn} onClick={() => setModalUid(null)}>
              {tx("global.common.close")}
            </button>
            <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} disabled={submitting} onClick={() => void submitModal()}>
              {tx("sg02.modal-submit")}
            </button>
          </div>
        </section>
      ) : null}

      <div className={styles.statusBar} data-section-uid="SEC-ADMIN-SG-02-ACTION-DOCK" data-component-uid="SG-02-CMP-STATUS-STATE">
        <div className={styles.statusItem}>
          <span>audit</span>
          <strong className={styles.chip}>{auditLines.length ? `${auditLines.length} events · ${auditLines[0].slice(0, 40)}` : dash}</strong>
        </div>
        <div className={styles.statusItem}>
          <span>idempotency registry</span>
          <strong className={styles.chip}>{Object.keys(idempotency).length ? `${Object.keys(idempotency).length} keys` : dash}</strong>
        </div>
        <div className={styles.statusItem}>
          <span>approvals</span>
          <strong className={styles.chip}>{approvals.length ? `${approvals.length} approved` : dash}</strong>
        </div>
        <div className={styles.statusItem}>
          <span>page state</span>
          <strong className={styles.chip}>{pageState}</strong>
        </div>
      </div>
    </div>
  );
}
