"use client";

import { useMemo } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { assetText, ASSET_CONTROL_TEXT } from "@/i18n/assetCatalog";
import { AssetRuntimeControl, AssetRuntimeProvider, useAssetRuntimeState } from "./AssetControlRuntime";
import styles from "./AssetVisual.module.css";

type ControlKind = "readonly" | "button" | "primary" | "select" | "search" | "segmented" | "list";
type ControlSpec = { id: string; kind: ControlKind };

const CONTEXT: readonly ControlSpec[] = [
  { id: "ASSET-01-CTL-PROJECT", kind: "select" },
  { id: "ASSET-01-CTL-TOPIC", kind: "select" },
  { id: "ASSET-01-FLD-TASK", kind: "readonly" },
  { id: "ASSET-01-FLD-TASK-STATUS", kind: "readonly" },
  { id: "ASSET-01-CTL-MODE", kind: "segmented" },
  { id: "ASSET-01-BTN-EXECUTE", kind: "primary" },
  { id: "ASSET-01-FLD-STAGE", kind: "readonly" },
] as const;

const ASSET_LIST: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-SEARCH", kind: "search" },
  { id: "ASSET-01-CTL-FILTER", kind: "select" },
  { id: "ASSET-01-LST-ASSET", kind: "list" },
] as const;

const REUSE: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-MANIFEST-REQUIRED", kind: "readonly" },
  { id: "ASSET-01-FLD-MANIFEST-REUSE", kind: "readonly" },
  { id: "ASSET-01-FLD-MANIFEST-MISSING", kind: "readonly" },
  { id: "ASSET-01-FLD-MANIFEST-DEFERRED", kind: "readonly" },
] as const;

const BINDING: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-BLUEPRINT", kind: "readonly" },
  { id: "ASSET-01-FLD-SCRIPT", kind: "readonly" },
  { id: "ASSET-01-FLD-DNA", kind: "readonly" },
  { id: "ASSET-01-FLD-MANIFEST", kind: "readonly" },
  { id: "ASSET-01-FLD-INPUT-FINGERPRINT", kind: "readonly" },
  { id: "ASSET-01-FLD-NAMING-AUTHORITY", kind: "readonly" },
  { id: "ASSET-01-FLD-CANONICAL-FILENAME", kind: "readonly" },
  { id: "ASSET-01-FLD-OUTPUT-ID", kind: "readonly" },
  { id: "ASSET-01-FLD-CHECKSUM", kind: "readonly" },
  { id: "ASSET-01-FLD-RIGHTS", kind: "readonly" },
  { id: "ASSET-01-FLD-INSTRUCTION", kind: "readonly" },
  { id: "ASSET-01-BTN-BLUEPRINT", kind: "button" },
  { id: "ASSET-01-BTN-SCRIPT", kind: "button" },
] as const;

const PREVIEW: readonly ControlSpec[] = [
  { id: "ASSET-01-BTN-SINGLE", kind: "button" },
  { id: "ASSET-01-BTN-AB", kind: "button" },
  { id: "ASSET-01-BTN-ABC", kind: "button" },
  { id: "ASSET-01-BTN-ZOOM-OUT", kind: "button" },
  { id: "ASSET-01-BTN-ZOOM-IN", kind: "button" },
  { id: "ASSET-01-BTN-FIT", kind: "button" },
  { id: "ASSET-01-BTN-REFERENCE", kind: "button" },
  { id: "ASSET-01-LST-COMPARE-VERSIONS", kind: "list" },
  { id: "ASSET-01-BTN-RESULT-DETAIL", kind: "button" },
] as const;

const CORRECTION: readonly ControlSpec[] = [
  { id: "ASSET-01-BTN-CORRECTION-OPEN", kind: "button" },
  { id: "ASSET-01-TXT-CORRECTION-REQUEST", kind: "search" },
  { id: "ASSET-01-BTN-CORRECTION-GENERATE", kind: "button" },
  { id: "ASSET-01-BTN-CORRECTION-APPROVE", kind: "button" },
  { id: "ASSET-01-BTN-CORRECTION-EXECUTE", kind: "primary" },
] as const;

const LAYER: readonly ControlSpec[] = [
  { id: "ASSET-01-BTN-LAYER-DOC-CREATE", kind: "button" },
  { id: "ASSET-01-BTN-LAYER-DOC-UPDATE", kind: "button" },
  { id: "ASSET-01-BTN-LAYER-ADD", kind: "button" },
  { id: "ASSET-01-BTN-LAYER-DELETE", kind: "button" },
  { id: "ASSET-01-BTN-LAYER-DUPLICATE", kind: "button" },
  { id: "ASSET-01-BTN-LAYER-REORDER", kind: "button" },
  { id: "ASSET-01-CTL-LAYER-PROPERTIES", kind: "select" },
  { id: "ASSET-01-CTL-LAYER-MASK", kind: "select" },
  { id: "ASSET-01-BTN-PATCH-CREATE", kind: "button" },
  { id: "ASSET-01-BTN-PATCH-PREVIEW", kind: "button" },
  { id: "ASSET-01-BTN-PATCH-ACCEPT", kind: "button" },
  { id: "ASSET-01-BTN-PATCH-REJECT", kind: "button" },
  { id: "ASSET-01-BTN-PATCH-REVISE", kind: "button" },
] as const;

const RUNTIME: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-ROUTE", kind: "readonly" },
  { id: "ASSET-01-FLD-PROVIDER", kind: "readonly" },
  { id: "ASSET-01-FLD-JOB", kind: "readonly" },
  { id: "ASSET-01-FLD-ATTEMPT", kind: "readonly" },
  { id: "ASSET-01-FLD-CALLBACK", kind: "readonly" },
  { id: "ASSET-01-FLD-RETRY-ELIGIBILITY", kind: "readonly" },
  { id: "ASSET-01-FLD-TRACE", kind: "readonly" },
  { id: "ASSET-01-BTN-RETRY", kind: "button" },
  { id: "ASSET-01-BTN-RUNTIME-DETAIL", kind: "button" },
] as const;

const DECISION: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-CRITERIA", kind: "readonly" },
  { id: "ASSET-01-FLD-DIMENSIONS", kind: "readonly" },
  { id: "ASSET-01-FLD-OVERALL", kind: "readonly" },
  { id: "ASSET-01-FLD-ISSUES", kind: "readonly" },
  { id: "ASSET-01-BTN-EVALUATE", kind: "button" },
  { id: "ASSET-01-BTN-CONFIRM", kind: "primary" },
  { id: "ASSET-01-BTN-MODIFY", kind: "button" },
  { id: "ASSET-01-BTN-VERSION-HISTORY", kind: "button" },
  { id: "ASSET-01-BTN-RESTORE-AS-NEW", kind: "button" },
  { id: "ASSET-01-BTN-LOCK", kind: "button" },
] as const;

const HANDOFF: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-HANDOFF-ASSET-VERSION", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-BLUEPRINT", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-SCRIPT-HASH", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-DNA", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-CHECKSUM", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-SCORECARD", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-RIGHTS", kind: "readonly" },
  { id: "ASSET-01-FLD-HANDOFF-CONTRACT-HASH", kind: "readonly" },
  { id: "ASSET-01-BTN-HANDOFF", kind: "primary" },
] as const;

const ALL_CONTROL_SPECS = [
  ...CONTEXT,
  ...ASSET_LIST,
  ...REUSE,
  ...BINDING,
  ...PREVIEW,
  ...CORRECTION,
  ...LAYER,
  ...RUNTIME,
  ...DECISION,
  ...HANDOFF,
] as const;

function Control({ spec }: { spec: ControlSpec }) {
  return <AssetRuntimeControl id={spec.id} kind={spec.kind} />;
}

function SectionTitle({ text }: { text: string }) {
  return <h2 className={styles.sectionTitle}>{text}</h2>;
}

function PreviewSurface() {
  const { state } = useAssetRuntimeState();
  const versions = state.projection?.candidate_versions ?? [];
  const count = state.compare_mode === "ABC" ? 3 : state.compare_mode === "AB" ? 2 : 1;
  const shown = versions.slice(0, count);

  if (!shown.length) {
    return <div className={styles.previewEmpty}>—</div>;
  }

  return (
    <div
      className={styles.previewEmpty}
      data-preview-count={shown.length}
      data-compare-mode={state.compare_mode}
      data-reference-overlay={state.reference_overlay ? "true" : "false"}
      style={{ gridTemplateColumns: `repeat(${shown.length}, minmax(0,1fr))`, gap: 8, overflow: "hidden" }}
    >
      {shown.map((version) => {
        if (version.media_kind === "IMAGE") {
          return (
            <img
              key={version.ref}
              data-asset-version-ref={version.ref}
              src={version.uri}
              alt={version.label}
              style={{
                maxWidth: "100%",
                maxHeight: 342,
                objectFit: "contain",
                transform: `scale(${state.zoom})`,
                transformOrigin: "center",
              }}
            />
          );
        }
        if (version.media_kind === "AUDIO") {
          return <audio key={version.ref} data-asset-version-ref={version.ref} controls src={version.uri} />;
        }
        return <div key={version.ref}>{version.label}</div>;
      })}
      {state.reference_overlay ? (
        <div data-reference-overlay-panel="true">
          {state.projection?.values["ASSET-01-FLD-DNA"] ?? "—"}
        </div>
      ) : null}
    </div>
  );
}

function AssetVisualBody() {
  const { locale } = useI18n();
  const { state } = useAssetRuntimeState();
  const registry = useMemo(() => new Set(ALL_CONTROL_SPECS.map((item) => item.id)), []);
  const catalogCount = Object.keys(ASSET_CONTROL_TEXT).length;
  const registryValid = registry.size === 85 && catalogCount === 85 && [...registry].every((id) => id in ASSET_CONTROL_TEXT);
  const pageState = state.projection?.page_state ?? "EMPTY";
  const currentStage = String(state.projection?.values["ASSET-01-FLD-STAGE"] ?? "");
  const correctionVisible = state.correction_open || pageState === "CORRECTION_REQUIRED";
  const bindingVisible = pageState === "READY" || ["ASSET-01-ACT-BINDING-VIEW","ASSET-01-ACT-BLUEPRINT-VIEW","ASSET-01-ACT-SCRIPT-VIEW"].includes(state.active_view_action ?? "");
  const reuseVisible = pageState === "READY";
  const layerVisible = state.projection?.gate_state["ASSET-01-GATE-LAYER-ELIGIBLE"] === true && currentStage.includes("STAGE-03");
  const runtimeVisible = pageState === "EXECUTING" || pageState === "ERROR" || state.active_view_action === "ASSET-01-ACT-RUNTIME-VIEW";
  const handoffVisible = pageState === "LOCKED" || pageState === "HANDOFF";
  const stagePrimarySpec =
    correctionVisible ? CORRECTION[4]
    : handoffVisible ? HANDOFF[11]
    : currentStage.includes("STAGE-04") || pageState === "REVIEW" ? DECISION[5]
    : CONTEXT[5];

  return (
    <div
      className={styles.page}
      data-page-uid="ASSET-01"
      data-vis-step="VIS-03"
      data-page-state={state.projection?.page_state ?? "EMPTY"}
      data-authority-sections="10"
      data-authority-components="16"
      data-authority-controls="85"
      data-registry-valid={registryValid ? "true" : "false"}
      data-data-classification={state.projection?.test_metadata?.data_classification}
      data-production-eligible={state.projection?.test_metadata ? String(state.projection.test_metadata.production_eligible) : undefined}
    >
      <section className={styles.contextBar} data-section-id="ASSET-01-SEC-01" data-visual-uid="ASSET-01-VIS-CONTEXT">
        <div className={styles.contextGrid} data-component-uid="ASSET-01-CMP-CONTEXT">
          {CONTEXT.filter((spec) => spec.id !== "ASSET-01-BTN-EXECUTE").map((spec) => <Control key={spec.id} spec={spec} />)}
        </div>
      </section>

      <div className={styles.primaryGrid} data-layout-grid="workspace-three-column">
        <div className={styles.leftColumn} data-layout-column="left">
          <section className={styles.panel} data-section-id="ASSET-01-SEC-02" data-visual-uid="ASSET-01-VIS-LEFT">
            <SectionTitle text={assetText(locale, "assetList")} />
            <div className={styles.stack} data-component-uid="ASSET-01-CMP-ASSET-LIST">
              {ASSET_LIST.map((spec) => <Control key={spec.id} spec={spec} />)}
            </div>
          </section>
        </div>

        <div className={styles.centerColumn} data-layout-column="center">
          {bindingVisible ? <section className={styles.panel} data-section-id="ASSET-01-SEC-03" data-visual-uid="ASSET-01-VIS-BINDING" data-stage-surface="input-readiness">
            <SectionTitle text={assetText(locale, "binding")} />
            <div className={styles.bindingGrid} data-component-uid="ASSET-01-CMP-BINDING">
              {BINDING.slice(0, 11).map((spec) => <Control key={spec.id} spec={spec} />)}
            </div>
          </section> : <section className={styles.stageAnchor} data-section-id="ASSET-01-SEC-03" data-stage-surface="input-readiness-collapsed" aria-hidden="true" />}

          <section className={`${styles.panel} ${styles.previewPanel}`} data-section-id="ASSET-01-SEC-04" data-visual-uid="ASSET-01-VIS-PREVIEW">
            <div className={styles.titleRow}>
              <SectionTitle text={assetText(locale, "preview")} />
              <div className={styles.compareToolbar} data-component-uid="ASSET-01-CMP-COMPARE">
                {PREVIEW.slice(0, 7).map((spec) => <Control key={spec.id} spec={spec} />)}
              </div>
            </div>
            <div className={styles.previewSurface} data-component-uid="ASSET-01-CMP-PREVIEW">
              <PreviewSurface />
              <div className={styles.previewFooter}>
                {PREVIEW.slice(7).map((spec) => <Control key={spec.id} spec={spec} />)}
              </div>
            </div>
          </section>

          {reuseVisible ? <section className={styles.panel} data-section-id="ASSET-01-SEC-05" data-visual-uid="ASSET-01-VIS-REUSE" data-stage-surface="reuse-missing">
            <SectionTitle text={assetText(locale, "reuse")} />
            <div className={styles.reuseGrid} data-component-uid="ASSET-01-CMP-REUSE">
              {REUSE.map((spec) => <Control key={spec.id} spec={spec} />)}
            </div>
          </section> : null}

          {correctionVisible ? <section className={`${styles.panel} ${styles.conditionalPanel} ${styles.correctionConversation}`} data-section-id="ASSET-01-SEC-06" data-visual-uid="ASSET-01-VIS-CORRECTION" data-stage-surface="correction-conversation" data-correction-ui="full-conversation">
            <div className={styles.correctionHeader}><SectionTitle text={assetText(locale, "correction")} /><Control spec={CORRECTION[0]} /></div>
            <div data-component-uid="ASSET-01-CMP-CORRECTION" data-conditional-controls={CORRECTION.length}>
              <div className={styles.correctionContext} data-correction-region="context">
                <span>{assetText(locale, "binding")}</span>
                <strong>{String(state.projection?.output_version_id ?? "—")} · {String(state.projection?.values["ASSET-01-FLD-ISSUES"] ?? "—")}</strong>
              </div>
              <div className={styles.correctionHistory} data-correction-region="history"><span>{assetText(locale, "correction")}</span><strong>{String(state.projection?.correction_request_id ?? "—")}</strong></div>
              <div className={styles.correctionCandidate} data-correction-region="candidate"><span>{String(state.projection?.correction_candidate_id ?? "—")} · {String(state.projection?.approved_correction_candidate_id ?? "—")}</span><Control spec={CORRECTION[2]} /><Control spec={CORRECTION[3]} /></div>
              <div className={styles.correctionComposer} data-correction-region="composer"><Control spec={CORRECTION[1]} /></div>
            </div>
          </section> : null}

          {layerVisible ? <section className={`${styles.panel} ${styles.conditionalPanel}`} data-section-id="ASSET-01-SEC-07" data-visual-uid="ASSET-01-VIS-LAYER" data-stage-surface="layer-composite">
            <SectionTitle text={assetText(locale, "layer")} />
            <div className={styles.layerCondition} data-layer-runtime-visible="true">
              <div data-component-uid="ASSET-01-CMP-LAYER-STACK" />
              <div className={styles.stack} data-component-uid="ASSET-01-CMP-LAYER-INSPECTOR" data-conditional-controls="8">{LAYER.slice(0, 8).map((spec) => <Control key={spec.id} spec={spec} />)}</div>
              <div className={styles.stack} data-component-uid="ASSET-01-CMP-PATCH" data-conditional-controls="5">{LAYER.slice(8).map((spec) => <Control key={spec.id} spec={spec} />)}</div>
            </div>
          </section> : null}
        </div>

        <aside className={styles.rightColumn} data-layout-column="right">
          <section className={styles.panel} data-section-id="ASSET-01-SEC-09" data-visual-uid="ASSET-01-VIS-DECISION">
            <SectionTitle text={assetText(locale, "decision")} />
            <div className={styles.stack} data-component-uid="ASSET-01-CMP-SCORE">
              {DECISION.slice(0, 5).map((spec) => <Control key={spec.id} spec={spec} />)}
            </div>
            <div className={styles.divider} />
            <div className={styles.stack} data-component-uid="ASSET-01-CMP-VERSION">
              {DECISION.slice(7, 9).map((spec) => <Control key={spec.id} spec={spec} />)}
            </div>
            <div className={styles.divider} />
            <div className={styles.stack} data-component-uid="ASSET-01-CMP-DECISION">
              {DECISION.slice(5, 7).filter((spec) => spec.id !== "ASSET-01-BTN-CONFIRM").map((spec) => <Control key={spec.id} spec={spec} />)}
              <Control spec={DECISION[9]} />
            </div>
            <div className={styles.divider} />
            <div className={styles.technicalActions} data-stage-surface="detail-triggers">
              <Control spec={BINDING[11]} />
              <Control spec={BINDING[12]} />
              <Control spec={RUNTIME[8]} />
            </div>
            {handoffVisible ? <div className={styles.stageHandoff} data-component-uid="ASSET-01-CMP-HANDOFF" data-stage-surface="finalize-handoff">
              {HANDOFF.filter((spec) => spec.id !== "ASSET-01-BTN-HANDOFF").map((spec) => <Control key={spec.id} spec={spec} />)}
            </div> : null}
          </section>
        </aside>
      </div>

      {runtimeVisible ? <section className={`${styles.panel} ${styles.fullWidth}`} data-section-id="ASSET-01-SEC-08" data-visual-uid="ASSET-01-VIS-RUNTIME" data-detail-surface="runtime">
        <SectionTitle text={assetText(locale, "runtime")} />
        <div className={styles.runtimeGrid} data-component-uid="ASSET-01-CMP-RUNTIME">
          {RUNTIME.slice(0, 8).map((spec) => <Control key={spec.id} spec={spec} />)}
        </div>
      </section> : null}
      {handoffVisible ? <section className={styles.stageAnchor} data-section-id="ASSET-01-SEC-10" data-stage-surface="handoff-materialized" aria-hidden="true" /> : null}
      <section className={styles.stageActionDock} data-current-stage-action-dock="true" data-current-stage={currentStage || pageState}>
        <div className={styles.stageSummary}><span>{assetText(locale, "ASSET-01-FLD-STAGE")}</span><strong>{currentStage || pageState}</strong></div>
        <div className={styles.stagePrimary}>{stagePrimarySpec ? <Control spec={stagePrimarySpec} /> : null}</div>
      </section>
    </div>
  );
}

export function AssetVisual() {
  return (
    <AssetRuntimeProvider>
      <AssetVisualBody />
    </AssetRuntimeProvider>
  );
}
