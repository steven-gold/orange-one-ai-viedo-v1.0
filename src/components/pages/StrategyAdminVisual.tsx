"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import {
  strategyActionLabel,
  strategyResponsibility,
  strategyText,
  strategyViewCopy,
  type StrategyViewKey,
} from "@/i18n/strategyAdminCatalog";
import {
  StrategyAdminRuntimeProvider,
  useStrategyAdminRuntime,
} from "./StrategyAdminRuntime";
import styles from "./StrategyAdminVisual.module.css";

type ViewSpec = {
  key: StrategyViewKey;
  uid: string;
  responsibilities: readonly string[];
  actions: readonly string[];
  operations: readonly string[];
  owner: string;
};

const VIEWS: readonly ViewSpec[] = [
  {
    key: "overview",
    uid: "STR-CURRENT-VIEW-OVERVIEW",
    responsibilities: [
      "Intelligence Summary",
      "Source Health",
      "Fact Quality",
      "Watchlist",
      "Risk Alert",
      "Candidate Queue",
    ],
    actions: ["ACT-SEARCH", "ACT-REFRESH", "ACT-NAV-OPEN"],
    operations: ["getUiProjection", "refreshProjection", "searchProjection"],
    owner: "StrategyService / StrategyFactPackService",
  },
  {
    key: "intelligence",
    uid: "STR-CURRENT-VIEW-INTELLIGENCE-FACT",
    responsibilities: [
      "Source Registry",
      "Watchlist",
      "Scope Policy",
      "Source Quality",
      "Retention",
      "Fact Registry",
      "Cohort Builder",
      "Market Map",
      "Completeness",
      "Confidence",
      "Citation",
    ],
    actions: [
      "ACT-CONFIGURE",
      "ACT-APPROVE",
      "ACT-SEARCH",
      "ACT-EXPORT",
      "ACT-NAV-OPEN",
    ],
    operations: [
      "approveGovernedResource",
      "configureGovernedResource",
      "exportProjection",
      "getUiProjection",
      "searchProjection",
    ],
    owner: "StrategyService / StrategyFactPackService",
  },
  {
    key: "playbook",
    uid: "STR-CURRENT-VIEW-PLAYBOOK",
    responsibilities: [
      "Platform Profile",
      "Account Scope",
      "Playbook",
      "Hypothesis",
      "Evidence",
      "Version History",
      "Approval",
    ],
    actions: ["ACT-DRAFT-SAVE", "ACT-APPROVE", "ACT-NAV-OPEN"],
    operations: ["approveGovernedResource", "getUiProjection", "saveDraft"],
    owner: "StrategyService",
  },
  {
    key: "opportunity",
    uid: "STR-CURRENT-VIEW-OPPORTUNITY",
    responsibilities: [
      "Trend Engine",
      "Momentum Engine",
      "Forecast Engine",
      "Opportunity Queue",
      "Confidence",
      "Evidence",
      "Review",
    ],
    actions: ["ACT-CANDIDATE-CREATE", "ACT-APPROVE", "ACT-NAV-OPEN"],
    operations: ["approveGovernedResource", "createCandidate", "getUiProjection"],
    owner: "StrategyService / StrategyFactPackService",
  },
  {
    key: "decision",
    uid: "STR-CURRENT-VIEW-DECISION",
    responsibilities: [
      "Decision Context",
      "Option Comparison",
      "Evidence",
      "Risk / Cost / Capacity",
      "Decision Gate",
      "Core Review Handoff",
      "Audit",
    ],
    actions: [
      "ACT-CANDIDATE-COMPARE",
      "ACT-CANDIDATE-DECIDE",
      "ACT-ADOPT-CONTEXT",
      "ACT-NAV-OPEN",
    ],
    operations: [
      "adoptAsContextCandidate",
      "compareCandidates",
      "getUiProjection",
      "rejectStrategyCandidate",
    ],
    owner: "StrategyService",
  },
] as const;

function StrategyAdminContent() {
  const { locale } = useI18n();
  const { projection, runtimeError, invoke, canInvoke } = useStrategyAdminRuntime();
  const [activeKey, setActiveKey] = useState<StrategyViewKey>("overview");
  const active = VIEWS.find((view) => view.key === activeKey) || VIEWS[0];
  const copy = strategyViewCopy(locale, active.key);
  const summary = active.responsibilities.slice(0, 4);
  const valueFor = (item: string) => projection?.values[item] ?? "—";
  const evidenceFor = (item: string) => projection?.evidence[item] ?? "—";
  const stateFor = (item: string) => projection?.states[item] ?? "—";

  return (
    <div
      className={styles.page}
      data-page-uid="admin:STR-01"
      data-vis-step="VIS-17"
      data-static-ui-spec-ready="true"
      data-effectful-runtime-ready="false"
      data-remap-state="IMPLEMENTATION_REQUIRED_NOT_EXECUTED"
      data-application-implementation="NOT_EXECUTED"
      data-runtime-binding-validation="NOT_EXECUTED"
      data-e2e-validation="NOT_EXECUTED"
      data-data-classification={
        projection?.test_metadata?.data_classification ?? "—"
      }
      data-production-eligible={
        projection?.test_metadata
          ? String(projection.test_metadata.production_eligible)
          : "—"
      }
      data-page-state={
        projection?.page_state ?? (runtimeError ? "ERROR" : "LOADING")
      }
    >
      <section className={styles.contextBar} aria-label="STR-01 Context">
        <div className={styles.identity}>
          <div className={styles.eyebrow}>ADMIN · STR-01 · STRATEGY GOVERNANCE</div>
          <h1>{strategyText(locale, "pageName")}</h1>
          <p>{strategyText(locale, "pageRole")}</p>
        </div>
        <div className={styles.state}>
          {strategyText(locale, "statusLine")} ·{" "}
          {runtimeError ?? strategyText(locale, "runtimeBlocked")}
        </div>
      </section>

      <nav className={styles.tabs} aria-label={strategyText(locale, "currentView")}>
        {VIEWS.map((view) => {
          const selected = view.key === active.key;
          return (
            <button
              key={view.uid}
              type="button"
              className={`${styles.tab} ${selected ? styles.tabActive : ""}`}
              data-view-uid={view.uid}
              aria-pressed={selected}
              onClick={() => setActiveKey(view.key)}
            >
              {strategyViewCopy(locale, view.key).label}
            </button>
          );
        })}
      </nav>

      <section
        className={styles.summary}
        aria-label={`${copy.label} ${strategyText(locale, "summaryLabel")}`}
      >
        {summary.map((item) => (
          <article key={item} className={styles.summaryCard}>
            <span>{strategyResponsibility(locale, item)}</span>
            <strong>{valueFor(item)}</strong>
          </article>
        ))}
      </section>

      <div className={styles.layout}>
        <section
          className={styles.mainPanel}
          data-current-view={active.uid}
          aria-label={copy.label}
        >
          <div className={styles.panelHead}>
            <div>
              <h2>{copy.label}</h2>
              <p>{strategyText(locale, "projection")}</p>
            </div>
          </div>
          <div
            className={styles.projectionTable}
            role="table"
            aria-label={`${copy.label} ${strategyText(locale, "projectionTable")}`}
          >
            <div className={styles.tableHeader} role="row">
              <span>{strategyText(locale, "projection")}</span>
              <span>{strategyText(locale, "value")}</span>
              <span>{strategyText(locale, "evidence")}</span>
              <span>{strategyText(locale, "state")}</span>
            </div>
            {active.responsibilities.map((item) => (
              <div key={item} className={styles.tableRow} role="row">
                <strong>{strategyResponsibility(locale, item)}</strong>
                <span>{valueFor(item)}</span>
                <span className={styles.muted}>{evidenceFor(item)}</span>
                <span className={styles.muted}>{stateFor(item)}</span>
              </div>
            ))}
          </div>
          <div className={styles.truthNote}>
            {strategyText(locale, "realDataOnly")}
          </div>
        </section>

        <aside
          className={styles.infoPanel}
          aria-label={strategyText(locale, "professionalInfo")}
        >
          <h2>{strategyText(locale, "professionalInfo")}</h2>
          <div className={styles.infoBody}>
            <p className={styles.description}>{copy.description}</p>
            <div className={styles.metaBlock}>
              <span>{strategyText(locale, "owner")}</span>
              <div className={styles.metaValue}>{active.owner}</div>
            </div>
            <div className={styles.metaBlock}>
              <span>{strategyText(locale, "permission")}</span>
              <div className={styles.metaValue}>ADMIN-L1-STRATEGY</div>
            </div>
            <div className={styles.metaBlock}>
              <span>{strategyText(locale, "operations")}</span>
              <div className={styles.chipWrap}>
                {active.operations.map((operation) => (
                  <span className={styles.chip} key={operation}>
                    {operation}
                  </span>
                ))}
              </div>
            </div>
            <div className={styles.metaBlock}>
              <span>{strategyText(locale, "actions")}</span>
              <div className={styles.chipWrap}>
                {active.actions.map((actionId) => (
                  <span className={styles.chip} key={actionId}>
                    {actionId}
                  </span>
                ))}
              </div>
            </div>
            <div className={styles.metaBlock}>
              <span>{strategyText(locale, "boundaries")}</span>
              <div className={styles.boundary}>{copy.boundary}</div>
            </div>
          </div>
        </aside>
      </div>

      <section
        className={styles.dock}
        aria-label={`${copy.label} ${strategyText(locale, "governedActionsLabel")}`}
      >
        <div className={styles.dockInfo}>
          <strong>{copy.label}</strong>
          <span>{runtimeError ?? strategyText(locale, "runtimeBlocked")}</span>
        </div>
        <div className={styles.actions}>
          {active.actions.map((actionId, index) => {
            const unresolved = actionId === "ACT-CANDIDATE-DECIDE";
            const navOnly = actionId === "ACT-NAV-OPEN";
            const enabled = canInvoke(actionId);
            const bindingState =
              unresolved || navOnly
                ? "AUTHORITY_BINDING_UNRESOLVED"
                : enabled
                  ? "REGISTERED_OPERATION_ADAPTER"
                  : "IMPLEMENTATION_REQUIRED_NOT_EXECUTED";
            const title = unresolved
              ? strategyText(locale, "bindingUnresolved")
              : navOnly
                ? strategyText(locale, "detailBindingRequired")
                : enabled
                  ? undefined
                  : strategyText(locale, "operationAdapterNotReady");

            return (
              <button
                key={actionId}
                type="button"
                className={`${styles.action} ${index === 0 ? styles.actionPrimary : ""}`}
                data-action-id={actionId}
                data-operation-binding={bindingState}
                data-disabled-reason={!enabled ? bindingState : undefined}
                disabled={!enabled}
                title={title}
                onClick={() => void invoke(actionId, active.key)}
              >
                {strategyActionLabel(locale, actionId)}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export function StrategyAdminVisual() {
  return (
    <StrategyAdminRuntimeProvider>
      <StrategyAdminContent />
    </StrategyAdminRuntimeProvider>
  );
}
