"use client";

import { useMemo } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { EDIT_CONTROL_TEXT, editText, editUiText } from "@/i18n/editCatalog";
import { EditRuntimeControl, EditRuntimeProvider, useEditRuntimeState } from "./EditControlRuntime";
import styles from "./EditVisual.module.css";

type Kind =
  | "readonly"
  | "button"
  | "primary"
  | "select"
  | "search"
  | "segmented"
  | "list"
  | "range"
  | "timecode"
  | "toggle"
  | "overview"
  | "tab"
  | "number"
  | "textarea"
  | "preview"
  | "dropzone"
  | "mode-select"
  | "timeline";

type Spec = { id: string; kind: Kind };

const CONTEXT: readonly Spec[] = [
  { id: "EDIT-01-CTL-SOURCE-MODE", kind: "segmented" },
  { id: "EDIT-01-FLD-PROJECT", kind: "select" },
  { id: "EDIT-01-FLD-TOPIC", kind: "select" },
  { id: "EDIT-01-FLD-TASK", kind: "select" },
  { id: "EDIT-01-CTL-EXECUTION-MODE", kind: "segmented" },
  { id: "EDIT-01-BTN-FLOW-START", kind: "primary" },
  { id: "EDIT-01-BTN-BLUEPRINT-VIEW", kind: "button" },
  { id: "EDIT-01-BTN-PACKAGE-VIEW", kind: "button" },
  { id: "EDIT-01-BTN-MANIFEST-VIEW", kind: "button" },
  { id: "EDIT-01-BTN-STAGE-CONFIRM", kind: "primary" },
  { id: "EDIT-01-BTN-STAGE-MODIFY", kind: "button" },
  { id: "EDIT-01-BTN-RETURN-BLUEPRINT", kind: "button" },
  { id: "EDIT-01-LBL-PENDING-TASK", kind: "readonly" },
  { id: "EDIT-01-LBL-CURRENT-STAGE", kind: "readonly" },
  { id: "EDIT-01-LBL-STAGE-SCORE", kind: "readonly" },
] as const;

const MEDIA: readonly Spec[] = [
  { id: "EDIT-01-FLD-MEDIA-SEARCH", kind: "search" },
  { id: "EDIT-01-CTL-MEDIA-TYPE-FILTER", kind: "select" },
  { id: "EDIT-01-BTN-ADD-MEDIA", kind: "button" },
  { id: "EDIT-01-LST-IMPORT-QUEUE", kind: "list" },
  { id: "EDIT-01-LST-MEDIA", kind: "list" },
  { id: "EDIT-01-CTL-DROP-TIMELINE", kind: "dropzone" },
  { id: "EDIT-01-BTN-UPLOAD-SPEC", kind: "button" },
] as const;

const PREVIEW: readonly Spec[] = [
  { id: "EDIT-01-BTN-PLAY", kind: "button" },
  { id: "EDIT-01-BTN-PAUSE", kind: "button" },
  { id: "EDIT-01-BTN-PREV-FRAME", kind: "button" },
  { id: "EDIT-01-BTN-NEXT-FRAME", kind: "button" },
  { id: "EDIT-01-FLD-TIMECODE", kind: "timecode" },
  { id: "EDIT-01-CTL-PLAYBACK-RATE", kind: "select" },
  { id: "EDIT-01-CTL-LOOP", kind: "toggle" },
  { id: "EDIT-01-CTL-VOLUME", kind: "range" },
  { id: "EDIT-01-BTN-MUTE", kind: "toggle" },
  { id: "EDIT-01-BTN-FULLSCREEN", kind: "button" },
] as const;

const RANGE: readonly Spec[] = [
  { id: "EDIT-01-BTN-SET-IN", kind: "button" },
  { id: "EDIT-01-BTN-SET-OUT", kind: "button" },
  { id: "EDIT-01-BTN-CLEAR-RANGE", kind: "button" },
  { id: "EDIT-01-BTN-MARKER", kind: "button" },
  { id: "EDIT-01-CTL-SNAP", kind: "toggle" },
  { id: "EDIT-01-BTN-ZOOM-OUT", kind: "button" },
  { id: "EDIT-01-BTN-ZOOM-IN", kind: "button" },
  { id: "EDIT-01-BTN-ZOOM-FIT", kind: "button" },
  { id: "EDIT-01-CTL-MINI-TIMELINE", kind: "timeline" },
  { id: "EDIT-01-CTL-RULER", kind: "timeline" },
  { id: "EDIT-01-CTL-PLAYHEAD", kind: "timeline" },
  { id: "EDIT-01-CTL-IN-OUT", kind: "range" },
  { id: "EDIT-01-CTL-MARKER-RAIL", kind: "timeline" },
] as const;

const TRACK: readonly Spec[] = [
  { id: "EDIT-01-CTL-TRACK-VISIBLE", kind: "toggle" },
  { id: "EDIT-01-CTL-TRACK-MUTE", kind: "toggle" },
  { id: "EDIT-01-CTL-TRACK-SOLO", kind: "toggle" },
  { id: "EDIT-01-CTL-TRACK-LOCK", kind: "toggle" },
] as const;

const MANUAL: readonly Spec[] = [
  { id: "EDIT-01-BTN-UNDO", kind: "button" },
  { id: "EDIT-01-BTN-REDO", kind: "button" },
  { id: "EDIT-01-TOOL-SELECT", kind: "button" },
  { id: "EDIT-01-TOOL-RAZOR", kind: "button" },
  { id: "EDIT-01-BTN-SPLIT", kind: "button" },
  { id: "EDIT-01-BTN-TRIM-START", kind: "button" },
  { id: "EDIT-01-BTN-TRIM-END", kind: "button" },
  { id: "EDIT-01-BTN-MOVE", kind: "button" },
  { id: "EDIT-01-BTN-REORDER", kind: "button" },
  { id: "EDIT-01-BTN-DELETE", kind: "button" },
  { id: "EDIT-01-BTN-DUPLICATE", kind: "button" },
  { id: "EDIT-01-BTN-REPLACE", kind: "button" },
  { id: "EDIT-01-CTL-TRANSITION", kind: "button" },
  { id: "EDIT-01-CTL-SPEED", kind: "button" },
  { id: "EDIT-01-CTL-CLIP-VOLUME", kind: "button" },
  { id: "EDIT-01-CTL-FADE", kind: "button" },
] as const;

const INSPECTOR: readonly Spec[] = [
  { id: "EDIT-01-TAB-CLIP", kind: "tab" },
  { id: "EDIT-01-TAB-API", kind: "tab" },
  { id: "EDIT-01-TAB-VOICE", kind: "tab" },
  { id: "EDIT-01-TAB-AUDIO", kind: "tab" },
  { id: "EDIT-01-TAB-LIPSYNC", kind: "tab" },
  { id: "EDIT-01-TAB-SUBTITLE", kind: "tab" },
  { id: "EDIT-01-TAB-EVALUATION", kind: "tab" },
  { id: "EDIT-01-TAB-VERSION", kind: "tab" },
  { id: "EDIT-01-TAB-OUTPUT", kind: "tab" },
  { id: "EDIT-01-FLD-CLIP-ID", kind: "readonly" },
  { id: "EDIT-01-FLD-SOURCE-VERSION", kind: "readonly" },
  { id: "EDIT-01-FLD-TRACK-ID", kind: "readonly" },
  { id: "EDIT-01-FLD-CLIP-IN", kind: "timecode" },
  { id: "EDIT-01-FLD-CLIP-OUT", kind: "timecode" },
  { id: "EDIT-01-FLD-CLIP-POSITION", kind: "timecode" },
  { id: "EDIT-01-FLD-CLIP-DURATION", kind: "readonly" },
  { id: "EDIT-01-FLD-INSPECTOR-SPEED", kind: "select" },
  { id: "EDIT-01-FLD-INSPECTOR-TRANSITION", kind: "select" },
  { id: "EDIT-01-FLD-INSPECTOR-VOLUME", kind: "number" },
  { id: "EDIT-01-FLD-INSPECTOR-FADE-IN", kind: "number" },
  { id: "EDIT-01-FLD-INSPECTOR-FADE-OUT", kind: "number" },
] as const;

const API: readonly Spec[] = [
  { id: "EDIT-01-FLD-API-PROVIDER", kind: "mode-select" },
  { id: "EDIT-01-FLD-API-MODEL", kind: "mode-select" },
  { id: "EDIT-01-FLD-API-SCOPE", kind: "select" },
  { id: "EDIT-01-FLD-API-INSTRUCTION", kind: "textarea" },
  { id: "EDIT-01-BTN-API-CANCEL", kind: "button" },
  { id: "EDIT-01-LBL-API-JOB", kind: "readonly" },
  { id: "EDIT-01-PNL-API-CANDIDATE", kind: "preview" },
  { id: "EDIT-01-BTN-API-COMPARE", kind: "button" },
  { id: "EDIT-01-BTN-API-APPLY", kind: "primary" },
  { id: "EDIT-01-BTN-API-DISCARD", kind: "button" },
  { id: "EDIT-01-LBL-CURRENT-SCRIPT-SECTION", kind: "readonly" },
  { id: "EDIT-01-LBL-BINDING-FINGERPRINT", kind: "readonly" },
  { id: "EDIT-01-BTN-CORR-GENERATE", kind: "primary" },
  { id: "EDIT-01-BTN-CORR-APPROVE", kind: "button" },
  { id: "EDIT-01-BTN-CORR-EXECUTE", kind: "primary" },
] as const;

const VOICE: readonly Spec[] = [
  { id: "EDIT-01-FLD-VOICE-SCRIPT", kind: "mode-select" },
  { id: "EDIT-01-FLD-VOICE-ASSET", kind: "mode-select" },
  { id: "EDIT-01-FLD-VOICE-PROVIDER", kind: "mode-select" },
  { id: "EDIT-01-FLD-VOICE-MODEL", kind: "mode-select" },
  { id: "EDIT-01-BTN-VOICE-GENERATE", kind: "primary" },
  { id: "EDIT-01-LST-VOICE-TAKES", kind: "list" },
  { id: "EDIT-01-BTN-VOICE-PREVIEW", kind: "button" },
  { id: "EDIT-01-BTN-VOICE-COMPARE", kind: "button" },
  { id: "EDIT-01-BTN-VOICE-APPLY", kind: "primary" },
] as const;

const AUDIO: readonly Spec[] = [
  { id: "EDIT-01-FLD-MUSIC-ASSET", kind: "mode-select" },
  { id: "EDIT-01-BTN-MUSIC-ADD", kind: "button" },
  { id: "EDIT-01-FLD-SFX-ASSET", kind: "mode-select" },
  { id: "EDIT-01-BTN-SFX-ADD", kind: "button" },
  { id: "EDIT-01-CTL-TRACK-LEVEL", kind: "range" },
  { id: "EDIT-01-CTL-MASTER-LEVEL", kind: "range" },
  { id: "EDIT-01-BTN-MIX-PREVIEW", kind: "button" },
  { id: "EDIT-01-BTN-MIX-EXECUTE", kind: "primary" },
] as const;

const LIPSYNC: readonly Spec[] = [
  { id: "EDIT-01-FLD-LIPSYNC-TARGET", kind: "select" },
  { id: "EDIT-01-BTN-LIPSYNC-EXECUTE", kind: "primary" },
  { id: "EDIT-01-BTN-LIPSYNC-PREVIEW", kind: "button" },
  { id: "EDIT-01-BTN-LIPSYNC-RETRY", kind: "button" },
  { id: "EDIT-01-BTN-LIPSYNC-MARK", kind: "button" },
  { id: "EDIT-01-LBL-LIPSYNC-SYNC-BINDING", kind: "readonly" },
] as const;

const SUBTITLE: readonly Spec[] = [
  { id: "EDIT-01-BTN-SUB-IMPORT", kind: "button" },
  { id: "EDIT-01-BTN-SUB-CREATE", kind: "button" },
  { id: "EDIT-01-FLD-SUB-TEXT", kind: "textarea" },
  { id: "EDIT-01-BTN-SUB-SPLIT", kind: "button" },
  { id: "EDIT-01-BTN-SUB-MERGE", kind: "button" },
  { id: "EDIT-01-FLD-SUB-TIMECODE", kind: "timecode" },
  { id: "EDIT-01-FLD-SUB-LANG", kind: "select" },
  { id: "EDIT-01-FLD-SUB-FORMAT", kind: "select" },
  { id: "EDIT-01-BTN-SUB-MANUAL-SYNC", kind: "button" },
  { id: "EDIT-01-BTN-SUB-API-SYNC", kind: "primary" },
  { id: "EDIT-01-LBL-SUB-SYNC-BINDING", kind: "readonly" },
] as const;

const EVALUATION: readonly Spec[] = [
  { id: "EDIT-01-LBL-EVAL-SUMMARY", kind: "readonly" },
  { id: "EDIT-01-LST-EVAL-ISSUES", kind: "list" },
  { id: "EDIT-01-BTN-EVAL-JUMP", kind: "button" },
  { id: "EDIT-01-BTN-EVAL-EVIDENCE", kind: "button" },
  { id: "EDIT-01-BTN-EVAL-LOAD-RANGE", kind: "button" },
  { id: "EDIT-01-BTN-EVAL-RECHECK-SELECTED", kind: "primary" },
  { id: "EDIT-01-BTN-EVAL-RECHECK-FULL", kind: "button" },
] as const;

const VERSION: readonly Spec[] = [
  { id: "EDIT-01-BTN-VERSION-SAVE", kind: "primary" },
  { id: "EDIT-01-LST-VERSION-HISTORY", kind: "list" },
  { id: "EDIT-01-BTN-VERSION-COMPARE", kind: "button" },
  { id: "EDIT-01-BTN-VERSION-RESTORE", kind: "button" },
  { id: "EDIT-01-BTN-VERSION-LOCK", kind: "primary" },
] as const;

const OUTPUT: readonly Spec[] = [
  { id: "EDIT-01-PNL-FINAL-PREVIEW", kind: "preview" },
  { id: "EDIT-01-CTL-SUBTITLE-TOGGLE", kind: "toggle" },
  { id: "EDIT-01-CTL-AUDIO-MONITOR", kind: "select" },
  { id: "EDIT-01-BTN-RENDER-SETTINGS", kind: "button" },
  { id: "EDIT-01-BTN-RENDER-EXECUTE", kind: "primary" },
  { id: "EDIT-01-LBL-RENDER-JOB", kind: "readonly" },
  { id: "EDIT-01-BTN-RENDER-CANCEL", kind: "button" },
  { id: "EDIT-01-BTN-OUTPUT-SAVE", kind: "button" },
  { id: "EDIT-01-BTN-DOWNLOAD", kind: "primary" },
  { id: "EDIT-01-BTN-HANDOFF-2", kind: "primary" },
] as const;

const STATUS: readonly Spec[] = [
  { id: "EDIT-01-LBL-PAGE-STATE", kind: "readonly" },
  { id: "EDIT-01-LST-JOB-STATUS", kind: "list" },
  { id: "EDIT-01-LBL-ERROR-STATE", kind: "readonly" },
] as const;

const ALL = [...CONTEXT, ...MEDIA, ...PREVIEW, ...RANGE, ...TRACK, ...MANUAL, ...INSPECTOR, ...API, ...VOICE, ...AUDIO, ...LIPSYNC, ...SUBTITLE, ...EVALUATION, ...VERSION, ...OUTPUT, ...STATUS] as const;

const TRACKS = [
  { uid: "EDIT-01-TRACK-VIDEO", label: "VIDEO", controls: ["EDIT-01-CTL-TRACK-VISIBLE", "EDIT-01-CTL-TRACK-LOCK"] },
  { uid: "EDIT-01-TRACK-OVERLAY", label: "OVERLAY", controls: ["EDIT-01-CTL-TRACK-VISIBLE", "EDIT-01-CTL-TRACK-LOCK"] },
  { uid: "EDIT-01-TRACK-VOICE", label: "VOICE", controls: ["EDIT-01-CTL-TRACK-MUTE", "EDIT-01-CTL-TRACK-SOLO", "EDIT-01-CTL-TRACK-LOCK"] },
  { uid: "EDIT-01-TRACK-MUSIC", label: "MUSIC", controls: ["EDIT-01-CTL-TRACK-MUTE", "EDIT-01-CTL-TRACK-SOLO", "EDIT-01-CTL-TRACK-LOCK"] },
  { uid: "EDIT-01-TRACK-SFX", label: "SFX", controls: ["EDIT-01-CTL-TRACK-MUTE", "EDIT-01-CTL-TRACK-SOLO", "EDIT-01-CTL-TRACK-LOCK"] },
  { uid: "EDIT-01-TRACK-SUBTITLE", label: "SUBTITLE", controls: ["EDIT-01-CTL-TRACK-VISIBLE", "EDIT-01-CTL-TRACK-LOCK"] },
  { uid: "EDIT-01-TRACK-LIPSYNC", label: "LIP_SYNC", controls: ["EDIT-01-CTL-TRACK-VISIBLE", "EDIT-01-CTL-TRACK-LOCK"] },
] as const;

const STAGES = ["EDIT-01-STAGE-01-ASSEMBLY", "EDIT-01-STAGE-02-AUDIO", "EDIT-01-STAGE-03-SYNC", "EDIT-01-STAGE-04-FINALIZE", "EDIT-01-STAGE-05-QA-HANDOFF"] as const;

function specById(id: string) { return ALL.find((spec) => spec.id === id); }

function Control({ spec, compact = false, scopeRef }: { spec: Spec; compact?: boolean; scopeRef?: string }) {
  return <EditRuntimeControl controlId={spec.id} kind={spec.kind} compact={compact} scopeRef={scopeRef} />;
}

function Title({ text, meta }: { text: string; meta?: string }) {
  return <div className={styles.titleRow}><h2>{text}</h2>{meta ? <span>{meta}</span> : null}</div>;
}

export function EditVisual() { return <EditRuntimeProvider><EditVisualBody /></EditRuntimeProvider>; }

function EditVisualBody() {
  const { state } = useEditRuntimeState();
  const { locale } = useI18n();
  const registryValid = useMemo(() => {
    const ids = new Set(ALL.map((spec) => spec.id));
    return ids.size === 160 && Object.keys(EDIT_CONTROL_TEXT).length === 160 && [...ids].every((id) => id in EDIT_CONTROL_TEXT);
  }, []);

  const contextMain = CONTEXT.slice(0, 12);
  const contextStatus = CONTEXT.slice(12);
  const mediaVisible = MEDIA.filter((spec) => ["EDIT-01-FLD-MEDIA-SEARCH", "EDIT-01-CTL-MEDIA-TYPE-FILTER", "EDIT-01-LST-MEDIA", "EDIT-01-CTL-DROP-TIMELINE"].includes(spec.id));
  const mediaConditional = MEDIA.filter((spec) => !mediaVisible.includes(spec));
  const toolbarVisible = MANUAL.filter((spec) => !["EDIT-01-BTN-REPLACE", "EDIT-01-CTL-CLIP-VOLUME", "EDIT-01-CTL-FADE"].includes(spec.id));
  const inspectorTabs = INSPECTOR.slice(0, 9);
  const inspectorFields = INSPECTOR.slice(9);
  const apiVisible = API.filter((spec) => ["EDIT-01-LBL-CURRENT-SCRIPT-SECTION", "EDIT-01-LBL-BINDING-FINGERPRINT"].includes(spec.id));
  const apiConditional = API.filter((spec) => !apiVisible.includes(spec));

  return <div className={styles.page} data-page-uid="EDIT-01" data-vis-step="VIS-05" data-page-state={state.resolved.page_state_uid ?? "EDIT-01-ST-PAGE-EMPTY"} data-current-stage={state.resolved.current_stage_uid ?? undefined} data-stage-phase={state.resolved.current_stage_phase ?? undefined} data-authority-controls="160" data-registry-valid={registryValid ? "true" : "false"}>
    <section className={styles.contextBar} data-section-id="EDIT-01-SEC-01" data-visual-uid="EDIT-01-VIS-CONTEXT" data-component-uid="EDIT-01-CMP-SOURCE-BAR">
      <div className={styles.contextGrid}>{contextMain.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
      <div className={styles.contextStatus}>{contextStatus.map((spec) => <Control key={spec.id} spec={spec} compact />)}</div>
    </section>

    <div className={styles.primaryGrid}>
      <section className={`${styles.panel} ${styles.assetPanel}`} data-section-id="EDIT-01-SEC-02" data-visual-uid="EDIT-01-VIS-ASSET-BIND" data-component-uid="EDIT-01-CMP-MEDIA-BIN">
        <Title text={editUiText(locale, "assetBinding")} meta="20%" />
        <div className={styles.stack}>{mediaVisible.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        <div className={styles.bindingCards}><div className={styles.bindingCard}><span>Blueprint</span><strong>{state.resolved.locked_blueprint_ref ?? "—"}</strong></div><div className={styles.bindingCard}><span>Production Package</span><strong>{state.resolved.production_package_ref ?? "—"}</strong></div><div className={styles.bindingCard}><span>Input Manifest</span><strong>{state.resolved.input_manifest_ref ?? "—"}</strong></div><div className={styles.bindingCard}><span>Input Fingerprint</span><strong>{state.resolved.input_fingerprint ?? "—"}</strong></div><div className={styles.bindingCard}><span>Binding Status</span><strong>{state.resolved.gate_state["EDIT-01-GATE-BINDING-INTEGRITY"] ? "BOUND" : "—"}</strong></div></div>
        <div className={styles.emptyNote}>{editUiText(locale, "noBoundInput")}</div>
        <div className={state.source_mode === "STANDALONE_UPLOAD" ? styles.stack : styles.hiddenRegistry} aria-hidden={state.source_mode === "STANDALONE_UPLOAD" ? undefined : "true"}>{mediaConditional.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
      </section>

      <div className={styles.productionStack}>
        <section className={`${styles.panel} ${styles.previewPanel}`} data-section-id="EDIT-01-SEC-03" data-visual-uid="EDIT-01-VIS-PREVIEW">
          <Title text={editUiText(locale, "preview")} meta="16:9" />
          <div className={styles.viewer} data-component-uid="EDIT-01-CMP-PREVIEW" data-preview-ref={state.resolved.preview_uri ?? undefined}>{state.resolved.preview_uri ?? "—"}</div>
          <div className={styles.transport} data-component-uid="EDIT-01-CMP-TRANSPORT">{PREVIEW.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        </section>

        <section className={`${styles.panel} ${styles.toolbarPanel}`} data-section-id="EDIT-01-SEC-06" data-visual-uid="EDIT-01-VIS-TOOLBAR" data-component-uid="EDIT-01-CMP-MANUAL-TOOLS">
          <Title text={editUiText(locale, "generalToolbar")} />
          <div className={styles.horizontalToolbar}>{toolbarVisible.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
          <div className={styles.hiddenRegistry} aria-hidden="true">{MANUAL.filter((spec) => !toolbarVisible.includes(spec)).map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        </section>

        <section className={`${styles.panel} ${styles.rangePanel}`} data-section-id="EDIT-01-SEC-04" data-visual-uid="EDIT-01-VIS-RANGE" data-component-uid="EDIT-01-CMP-PRECISION">
          <Title text={editUiText(locale, "rangeMarker")} />
          <div className={styles.horizontalToolbar}>{RANGE.slice(0, 8).map((spec) => <Control key={spec.id} spec={spec} />)}</div>
          <div className={styles.timelineNavigation}>
            <div data-component-uid="EDIT-01-CMP-MINI-TIMELINE"><Control spec={RANGE[8]} /></div>
            <div data-component-uid="EDIT-01-CMP-RULER"><Control spec={RANGE[9]} /></div>
            <Control spec={RANGE[10]} /><Control spec={RANGE[11]} />
            <div data-component-uid="EDIT-01-CMP-MARKER-RAIL"><Control spec={RANGE[12]} /></div>
          </div>
        </section>

        <section className={`${styles.panel} ${styles.timelinePanel}`} data-section-id="EDIT-01-SEC-05" data-visual-uid="EDIT-01-VIS-TIMELINE" data-component-uid="EDIT-01-CMP-TIMELINE">
          <Title text={editUiText(locale, "timeline")} meta="min-height 320px" />
          <div className={styles.timelineRuler}><span>00:00:00:00</span><span>—</span><span>00:00:00:00</span></div>
          <div className={styles.trackStack}>{TRACKS.map((track) => <div className={styles.trackRow} key={track.uid} data-track-type-uid={track.uid}><div className={styles.trackHeader}><strong>{track.label}</strong><div className={styles.trackControls}>{track.controls.map((id) => { const spec = specById(id); return spec ? <Control key={`${track.uid}-${id}`} spec={spec} compact scopeRef={track.uid} /> : null; })}</div></div><div className={styles.trackLane}>—</div></div>)}</div>
          <div className={styles.dialogueGuard} data-section-id="EDIT-01-SEC-11" data-component-uid="EDIT-01-CMP-DIALOGUE-BINDING"><span>{editUiText(locale, "dialogueGuard")}</span><strong>—</strong></div>
        </section>
      </div>
    </div>

    <div className={styles.adjustmentRow}>
      <section className={`${styles.panel} ${styles.semanticPanel}`} data-section-id="EDIT-01-SEC-08" data-visual-uid="EDIT-01-VIS-SEMANTIC" data-component-uid="EDIT-01-CMP-API">
        <Title text={editUiText(locale, "semantic")} meta="38%" />
        <div className={styles.semanticContext}>{apiVisible.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        {state.resolved.gate_state["EDIT-01-GATE-CORRECTION"] ? null : <div className={styles.conditionNotice}>{editUiText(locale, "correctionUnavailable")}</div>}
        <div className={state.resolved.gate_state["EDIT-01-GATE-CORRECTION"] ? styles.stack : styles.hiddenRegistry} aria-hidden={state.resolved.gate_state["EDIT-01-GATE-CORRECTION"] ? undefined : "true"}>{apiConditional.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        <div className={styles.evaluationBox} data-section-id="EDIT-01-SEC-13" data-component-uid="EDIT-01-CMP-STAGE-EVALUATION"><div data-component-uid="EDIT-01-CMP-QA">{EVALUATION.map((spec) => <Control key={spec.id} spec={spec} />)}</div></div>
      </section>

      <section className={`${styles.panel} ${styles.microPanel}`} data-section-id="EDIT-01-SEC-06" data-visual-uid="EDIT-01-VIS-MICRO" data-component-uid="EDIT-01-CMP-MICRO-ADJUSTMENT">
        <Title text={editUiText(locale, "micro")} meta="62%" />
        <div className={styles.microSequence}>{editUiText(locale, "microHint")}</div>
        <div className={styles.microGrid}>{inspectorFields.slice(3, 12).map((spec) => <Control key={spec.id} spec={spec} />)}</div>
      </section>
    </div>

    <div className={styles.bottomRow}>
      <section className={`${styles.panel} ${styles.inspectorPanel}`} data-section-id="EDIT-01-SEC-07" data-visual-uid="EDIT-01-VIS-INSPECTOR" data-component-uid="EDIT-01-CMP-INSPECTOR">
        <Title text={editUiText(locale, "inspector")} meta="34%" />
        <div className={styles.tabs}>{inspectorTabs.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        <div className={styles.inspectorGrid}>{inspectorFields.slice(0, 3).map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        <section className={state.inspector_tab === "VOICE" ? styles.inspectorGrid : styles.hiddenRegistry} aria-hidden={state.inspector_tab === "VOICE" ? undefined : "true"} data-section-id="EDIT-01-SEC-09" data-component-uid="EDIT-01-CMP-VOICE">{VOICE.map((spec) => <Control key={spec.id} spec={spec} />)}</section>
        <section className={state.inspector_tab === "AUDIO" ? styles.inspectorGrid : styles.hiddenRegistry} aria-hidden={state.inspector_tab === "AUDIO" ? undefined : "true"} data-section-id="EDIT-01-SEC-10" data-component-uid="EDIT-01-CMP-AUDIO">{AUDIO.map((spec) => <Control key={spec.id} spec={spec} />)}</section>
        <section className={state.inspector_tab === "LIPSYNC" ? styles.inspectorGrid : styles.hiddenRegistry} aria-hidden={state.inspector_tab === "LIPSYNC" ? undefined : "true"} data-section-id="EDIT-01-SEC-11" data-component-uid="EDIT-01-CMP-LIPSYNC">{LIPSYNC.map((spec) => <Control key={spec.id} spec={spec} />)}</section>
        <section className={state.inspector_tab === "SUBTITLE" ? styles.inspectorGrid : styles.hiddenRegistry} aria-hidden={state.inspector_tab === "SUBTITLE" ? undefined : "true"} data-section-id="EDIT-01-SEC-12" data-component-uid="EDIT-01-CMP-SUBTITLE">{SUBTITLE.map((spec) => <Control key={spec.id} spec={spec} />)}</section>
      </section>

      <section className={`${styles.panel} ${styles.comparePanel}`} data-section-id="EDIT-01-SEC-14" data-visual-uid="EDIT-01-VIS-COMPARE" data-component-uid="EDIT-01-CMP-VERSION">
        <Title text={editUiText(locale, "compare")} meta="34%" /><div className={styles.stack}>{VERSION.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
      </section>

      <section className={`${styles.panel} ${styles.outputPanel}`} data-section-id="EDIT-01-SEC-15" data-visual-uid="EDIT-01-VIS-OUTPUT" data-component-uid="EDIT-01-CMP-OUTPUT">
        <Title text={editUiText(locale, "output")} meta="32%" />
        <div className={styles.outputGrid}>{OUTPUT.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
        <div className={styles.stageRail} data-section-id="EDIT-01-SEC-16" data-component-uid="EDIT-01-CMP-STAGE-RAIL">{STAGES.map((stage, index) => <div key={stage} data-stage-uid={stage} data-stage-active={state.resolved.current_stage_uid === stage ? "true" : undefined}><span>{index + 1}</span><strong>{stage.replace("EDIT-01-STAGE-", "")}</strong><em>{state.resolved.current_stage_uid === stage ? state.resolved.current_stage_phase ?? "—" : "—"}</em></div>)}</div>
        <div className={styles.statusRail} data-component-uid="EDIT-01-CMP-STATUS">{STATUS.map((spec) => <Control key={spec.id} spec={spec} />)}</div>
      </section>
    </div>
  </div>;
}
