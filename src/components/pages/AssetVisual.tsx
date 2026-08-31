"use client";

import { useMemo } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { assetText, ASSET_CONTROL_TEXT } from "@/i18n/assetCatalog";
import { AssetRuntimeControl, AssetRuntimeProvider, useAssetRuntimeState } from "./AssetControlRuntime";
import styles from "./AssetVisual.module.css";

type ControlKind = "readonly" | "button" | "primary" | "select" | "search" | "segmented" | "list";
type ControlSpec = { id: string; kind: ControlKind };

const CONTEXT: readonly ControlSpec[] = [
  { id: "ASSET-01-CTL-PROJECT", kind: "select" },{ id: "ASSET-01-CTL-TOPIC", kind: "select" },{ id: "ASSET-01-FLD-TASK", kind: "readonly" },{ id: "ASSET-01-FLD-TASK-STATUS", kind: "readonly" },{ id: "ASSET-01-CTL-MODE", kind: "segmented" },{ id: "ASSET-01-BTN-EXECUTE", kind: "primary" },{ id: "ASSET-01-FLD-STAGE", kind: "readonly" },
] as const;
const ASSET_LIST: readonly ControlSpec[] = [{ id: "ASSET-01-FLD-SEARCH", kind: "search" },{ id: "ASSET-01-CTL-FILTER", kind: "select" },{ id: "ASSET-01-LST-ASSET", kind: "list" }] as const;
const REUSE: readonly ControlSpec[] = [{ id: "ASSET-01-FLD-MANIFEST-REQUIRED", kind: "readonly" },{ id: "ASSET-01-FLD-MANIFEST-REUSE", kind: "readonly" },{ id: "ASSET-01-FLD-MANIFEST-MISSING", kind: "readonly" },{ id: "ASSET-01-FLD-MANIFEST-DEFERRED", kind: "readonly" }] as const;
const BINDING: readonly ControlSpec[] = [
  { id: "ASSET-01-FLD-BLUEPRINT", kind: "readonly" },{ id: "ASSET-01-FLD-SCRIPT", kind: "readonly" },{ id: "ASSET-01-FLD-DNA", kind: "readonly" },{ id: "ASSET-01-FLD-MANIFEST", kind: "readonly" },{ id: "ASSET-01-FLD-INPUT-FINGERPRINT", kind: "readonly" },{ id: "ASSET-01-FLD-NAMING-AUTHORITY", kind: "readonly" },{ id: "ASSET-01-FLD-CANONICAL-FILENAME", kind: "readonly" },{ id: "ASSET-01-FLD-OUTPUT-ID", kind: "readonly" },{ id: "ASSET-01-FLD-CHECKSUM", kind: "readonly" },{ id: "ASSET-01-FLD-RIGHTS", kind: "readonly" },{ id: "ASSET-01-FLD-INSTRUCTION", kind: "readonly" },{ id: "ASSET-01-BTN-BLUEPRINT", kind: "button" },{ id: "ASSET-01-BTN-SCRIPT", kind: "button" },
] as const;
const PREVIEW: readonly ControlSpec[] = [
  { id: "ASSET-01-BTN-SINGLE", kind: "button" },{ id: "ASSET-01-BTN-AB", kind: "button" },{ id: "ASSET-01-BTN-ABC", kind: "button" },{ id: "ASSET-01-BTN-ZOOM-OUT", kind: "button" },{ id: "ASSET-01-BTN-ZOOM-IN", kind: "button" },{ id: "ASSET-01-BTN-FIT", kind: "button" },{ id: "ASSET-01-BTN-REFERENCE", kind: "button" },{ id: "ASSET-01-LST-COMPARE-VERSIONS", kind: "list" },{ id: "ASSET-01-BTN-RESULT-DETAIL", kind: "button" },
] as const;
const CORRECTION: readonly ControlSpec[] = [{ id: "ASSET-01-BTN-CORRECTION-OPEN", kind: "button" },{ id: "ASSET-01-TXT-CORRECTION-REQUEST", kind: "search" },{ id: "ASSET-01-BTN-CORRECTION-GENERATE", kind: "button" },{ id: "ASSET-01-BTN-CORRECTION-APPROVE", kind: "button" },{ id: "ASSET-01-BTN-CORRECTION-EXECUTE", kind: "primary" }] as const;
const LAYER: readonly ControlSpec[] = [
  { id: "ASSET-01-BTN-LAYER-DOC-CREATE", kind: "button" },{ id: "ASSET-01-BTN-LAYER-DOC-UPDATE", kind: "button" },{ id: "ASSET-01-BTN-LAYER-ADD", kind: "button" },{ id: "ASSET-01-BTN-LAYER-DELETE", kind: "button" },{ id: "ASSET-01-BTN-LAYER-DUPLICATE", kind: "button" },{ id: "ASSET-01-BTN-LAYER-REORDER", kind: "button" },{ id: "ASSET-01-CTL-LAYER-PROPERTIES", kind: "select" },{ id: "ASSET-01-CTL-LAYER-MASK", kind: "select" },{ id: "ASSET-01-BTN-PATCH-CREATE", kind: "button" },{ id: "ASSET-01-BTN-PATCH-PREVIEW", kind: "button" },{ id: "ASSET-01-BTN-PATCH-ACCEPT", kind: "button" },{ id: "ASSET-01-BTN-PATCH-REJECT", kind: "button" },{ id: "ASSET-01-BTN-PATCH-REVISE", kind: "button" },
] as const;
const RUNTIME: readonly ControlSpec[] = [{ id: "ASSET-01-FLD-ROUTE", kind: "readonly" },{ id: "ASSET-01-FLD-PROVIDER", kind: "readonly" },{ id: "ASSET-01-FLD-JOB", kind: "readonly" },{ id: "ASSET-01-FLD-ATTEMPT", kind: "readonly" },{ id: "ASSET-01-FLD-CALLBACK", kind: "readonly" },{ id: "ASSET-01-FLD-RETRY-ELIGIBILITY", kind: "readonly" },{ id: "ASSET-01-FLD-TRACE", kind: "readonly" },{ id: "ASSET-01-BTN-RETRY", kind: "button" },{ id: "ASSET-01-BTN-RUNTIME-DETAIL", kind: "button" }] as const;
const DECISION: readonly ControlSpec[] = [{ id: "ASSET-01-FLD-CRITERIA", kind: "readonly" },{ id: "ASSET-01-FLD-DIMENSIONS", kind: "readonly" },{ id: "ASSET-01-FLD-OVERALL", kind: "readonly" },{ id: "ASSET-01-FLD-ISSUES", kind: "readonly" },{ id: "ASSET-01-BTN-EVALUATE", kind: "button" },{ id: "ASSET-01-BTN-CONFIRM", kind: "primary" },{ id: "ASSET-01-BTN-MODIFY", kind: "button" },{ id: "ASSET-01-BTN-VERSION-HISTORY", kind: "button" },{ id: "ASSET-01-BTN-RESTORE-AS-NEW", kind: "button" },{ id: "ASSET-01-BTN-LOCK", kind: "button" }] as const;
const HANDOFF: readonly ControlSpec[] = [{ id: "ASSET-01-FLD-HANDOFF-ASSET-VERSION", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-LAYER-COMPOSITE", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-BLUEPRINT", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-SCRIPT-HASH", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-DNA", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-CHECKSUM", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-SCORECARD", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-RIGHTS", kind: "readonly" },{ id: "ASSET-01-FLD-HANDOFF-CONTRACT-HASH", kind: "readonly" },{ id: "ASSET-01-BTN-HANDOFF", kind: "primary" }] as const;
const ALL_CONTROL_SPECS = [...CONTEXT,...ASSET_LIST,...REUSE,...BINDING,...PREVIEW,...CORRECTION,...LAYER,...RUNTIME,...DECISION,...HANDOFF] as const;
function Control({ spec }: { spec: ControlSpec }) { return <AssetRuntimeControl id={spec.id} kind={spec.kind} />; }
function SectionTitle({ text }: { text: string }) { return <h2 className={styles.sectionTitle}>{text}</h2>; }

function PreviewSurface(){
 const{state}=useAssetRuntimeState(),versions=state.projection?.candidate_versions??[],count=state.compare_mode==="ABC"?3:state.compare_mode==="AB"?2:1,shown=versions.slice(0,count);
 if(!shown.length)return <div className={styles.previewEmpty}>—</div>;
 return <div className={styles.previewEmpty} data-preview-count={shown.length} data-compare-mode={state.compare_mode} style={{gridTemplateColumns:`repeat(${shown.length}, minmax(0,1fr))`,gap:8,overflow:"hidden"}}>{shown.map(version=>version.media_kind==="IMAGE"?<img key={version.ref} data-asset-version-ref={version.ref} src={version.uri} alt={version.label} style={{maxWidth:"100%",maxHeight:342,objectFit:"contain",transform:`scale(${state.zoom})`,transformOrigin:"center"}}/>:version.media_kind==="AUDIO"?<audio key={version.ref} data-asset-version-ref={version.ref} controls src={version.uri}/>:<div key={version.ref}>{version.label}</div>)}</div>;
}

function AssetVisualBody() {
  const { locale } = useI18n();
  const { state } = useAssetRuntimeState();
  const registry = useMemo(() => new Set(ALL_CONTROL_SPECS.map((item) => item.id)), []);
  const catalogCount = Object.keys(ASSET_CONTROL_TEXT).length;
  const registryValid = registry.size === 85 && catalogCount === 85 && [...registry].every((id) => id in ASSET_CONTROL_TEXT);
  const correctionVisible=state.correction_open||state.projection?.page_state==="CORRECTION_REQUIRED";
  const layerVisible=state.projection?.gate_state["ASSET-01-GATE-LAYER-ELIGIBLE"]===true;
  return <div className={styles.page} data-page-uid="ASSET-01" data-vis-step="VIS-03" data-page-state={state.projection?.page_state ?? "EMPTY"} data-authority-sections="10" data-authority-components="16" data-authority-controls="85" data-registry-valid={registryValid ? "true" : "false"}>
    <section className={styles.contextBar} data-section-id="ASSET-01-SEC-01" data-visual-uid="ASSET-01-VIS-CONTEXT"><div className={styles.contextGrid} data-component-uid="ASSET-01-CMP-CONTEXT">{CONTEXT.map((spec) => <Control key={spec.id} spec={spec} />)}</div></section>
    <div className={styles.primaryGrid}>
      <div className={styles.leftColumn}><section className={styles.panel} data-section-id="ASSET-01-SEC-02" data-visual-uid="ASSET-01-VIS-LEFT"><SectionTitle text={assetText(locale, "assetList")} /><div className={styles.stack} data-component-uid="ASSET-01-CMP-ASSET-LIST">{ASSET_LIST.map((spec) => <Control key={spec.id} spec={spec} />)}</div></section></div>
      <div className={styles.centerColumn}>
        <section className={styles.panel} data-section-id="ASSET-01-SEC-03" data-visual-uid="ASSET-01-VIS-BINDING"><SectionTitle text={assetText(locale, "binding")} /><div className={styles.bindingGrid} data-component-uid="ASSET-01-CMP-BINDING">{BINDING.filter((spec) => spec.id !== "ASSET-01-BTN-SCRIPT").map((spec) => <Control key={spec.id} spec={spec} />)}</div><div className={styles.componentBridge} data-component-uid="ASSET-01-CMP-SCRIPT"><Control spec={BINDING.find((spec) => spec.id === "ASSET-01-BTN-SCRIPT")!} /></div></section>
        <section className={`${styles.panel} ${styles.previewPanel}`} data-section-id="ASSET-01-SEC-04" data-visual-uid="ASSET-01-VIS-PREVIEW"><div className={styles.titleRow}><SectionTitle text={assetText(locale, "preview")} /><div className={styles.compareToolbar} data-component-uid="ASSET-01-CMP-COMPARE">{PREVIEW.slice(0, 7).map((spec) => <Control key={spec.id} spec={spec} />)}</div></div><div className={styles.previewSurface} data-component-uid="ASSET-01-CMP-PREVIEW"><PreviewSurface/><div className={styles.previewFooter}>{PREVIEW.slice(7).map((spec) => <Control key={spec.id} spec={spec} />)}</div></div></section>
        <section className={styles.panel} data-section-id="ASSET-01-SEC-05" data-visual-uid="ASSET-01-VIS-REUSE"><SectionTitle text={assetText(locale, "reuse")} /><div className={styles.reuseGrid} data-component-uid="ASSET-01-CMP-REUSE">{REUSE.map((spec) => <Control key={spec.id} spec={spec} />)}</div></section>
        <section className={`${styles.panel} ${styles.conditionalPanel}`} data-section-id="ASSET-01-SEC-06" data-visual-uid="ASSET-01-VIS-CORRECTION"><SectionTitle text={assetText(locale, "correction")} /><div data-component-uid="ASSET-01-CMP-CORRECTION" data-conditional-controls={correctionVisible?CORRECTION.length:0}>{correctionVisible?<div className={styles.stack}>{CORRECTION.map((spec) => <Control key={spec.id} spec={spec} />)}</div>:<div className={styles.conditionNotice}>{assetText(locale, "conditionalModify")}</div>}</div></section>
        <section className={`${styles.panel} ${styles.conditionalPanel}`} data-section-id="ASSET-01-SEC-07" data-visual-uid="ASSET-01-VIS-LAYER"><SectionTitle text={assetText(locale, "layer")} /><div className={styles.layerCondition}>{layerVisible?<><div data-component-uid="ASSET-01-CMP-LAYER-STACK" /><div className={styles.stack} data-component-uid="ASSET-01-CMP-LAYER-INSPECTOR" data-conditional-controls="8">{LAYER.slice(0,8).map((spec) => <Control key={spec.id} spec={spec} />)}</div><div className={styles.stack} data-component-uid="ASSET-01-CMP-PATCH" data-conditional-controls="5">{LAYER.slice(8).map((spec) => <Control key={spec.id} spec={spec} />)}</div></>:<div className={styles.conditionNotice}>{assetText(locale, "conditionalLayer")}</div>}</div></section>
      </div>
      <aside className={styles.rightColumn}><section className={styles.panel} data-section-id="ASSET-01-SEC-09" data-visual-uid="ASSET-01-VIS-DECISION"><SectionTitle text={assetText(locale, "decision")} /><div className={styles.stack} data-component-uid="ASSET-01-CMP-SCORE">{DECISION.slice(0, 5).map((spec) => <Control key={spec.id} spec={spec} />)}</div><div className={styles.divider} /><div className={styles.stack} data-component-uid="ASSET-01-CMP-VERSION">{DECISION.slice(7, 9).map((spec) => <Control key={spec.id} spec={spec} />)}</div><div className={styles.divider} /><div className={styles.stack} data-component-uid="ASSET-01-CMP-DECISION">{DECISION.slice(5, 7).map((spec) => <Control key={spec.id} spec={spec} />}<Control spec={DECISION[9]} /></div></section></aside>
    </div>
    <section className={`${styles.panel} ${styles.fullWidth}`} data-section-id="ASSET-01-SEC-08" data-visual-uid="ASSET-01-VIS-RUNTIME"><SectionTitle text={assetText(locale, "runtime")} /><div className={styles.runtimeGrid} data-component-uid="ASSET-01-CMP-RUNTIME">{RUNTIME.map((spec) => <Control key={spec.id} spec={spec} />)}</div></section>
    <section className={`${styles.panel} ${styles.fullWidth}`} data-section-id="ASSET-01-SEC-10" data-visual-uid="ASSET-01-VIS-HANDOFF"><SectionTitle text={assetText(locale, "handoff")} /><div className={styles.handoffGrid} data-component-uid="ASSET-01-CMP-HANDOFF">{HANDOFF.map((spec) => <Control key={spec.id} spec={spec} />)}</div></section>
  </div>;
}
export function AssetVisual(){return <AssetRuntimeProvider><AssetVisualBody/></AssetRuntimeProvider>;}
