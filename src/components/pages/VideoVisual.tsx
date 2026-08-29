"use client";

import { useMemo } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { VIDEO_CONTROL_TEXT, videoText } from "@/i18n/videoCatalog";
import styles from "./VideoVisual.module.css";

type Kind = "readonly" | "button" | "primary" | "select" | "search" | "segmented" | "list" | "range";
type Spec = { id: string; kind: Kind };

const CONTEXT: readonly Spec[] = [
  {id:"VIDEO-01-FLD-PROJECT",kind:"select"},{id:"VIDEO-01-FLD-TOPIC",kind:"select"},{id:"VIDEO-01-FLD-TASK",kind:"select"},{id:"VIDEO-01-FLD-STATUS",kind:"readonly"},
  {id:"VIDEO-01-CTL-MODE",kind:"segmented"},{id:"VIDEO-01-BTN-EXECUTE",kind:"primary"},{id:"VIDEO-01-BTN-BLUEPRINT",kind:"button"},{id:"VIDEO-01-BTN-PACKAGE",kind:"button"},
] as const;
const PRODUCTION: readonly Spec[] = [
  {id:"VIDEO-01-FLD-SEARCH",kind:"search"},{id:"VIDEO-01-CTL-FILTER",kind:"select"},{id:"VIDEO-01-CTL-SHOT-SELECT",kind:"list"},
] as const;
const BOUND: readonly Spec[] = [
  {id:"VIDEO-01-FLD-BLUEPRINT-REF",kind:"readonly"},{id:"VIDEO-01-FLD-INPUT-FINGERPRINT",kind:"readonly"},{id:"VIDEO-01-FLD-SCRIPT-SECTION",kind:"readonly"},{id:"VIDEO-01-FLD-DNA-REFS",kind:"readonly"},
  {id:"VIDEO-01-FLD-ASSET-REFS",kind:"readonly"},{id:"VIDEO-01-FLD-FILENAME-CHECKSUM",kind:"readonly"},{id:"VIDEO-01-FLD-RIGHTS",kind:"readonly"},{id:"VIDEO-01-FLD-INSTRUCTION",kind:"readonly"},
] as const;
const PREVIEW: readonly Spec[] = [
  {id:"VIDEO-01-BTN-PLAY",kind:"button"},{id:"VIDEO-01-CTL-SEEK",kind:"range"},{id:"VIDEO-01-FLD-TIMECODE",kind:"readonly"},{id:"VIDEO-01-BTN-VOLUME",kind:"button"},{id:"VIDEO-01-BTN-FULLSCREEN",kind:"button"},
] as const;
const COMPARE: readonly Spec[] = [
  {id:"VIDEO-01-CTL-COMPARE",kind:"button"},{id:"VIDEO-01-CTL-VERSION-A",kind:"select"},{id:"VIDEO-01-CTL-VERSION-B",kind:"select"},
] as const;
const DECISION: readonly Spec[] = [
  {id:"VIDEO-01-FLD-CURRENT-VERSION",kind:"readonly"},{id:"VIDEO-01-FLD-CANDIDATE-VERSION",kind:"readonly"},{id:"VIDEO-01-FLD-OVERALL-SCORE",kind:"readonly"},{id:"VIDEO-01-FLD-ISSUE-SUMMARY",kind:"readonly"},{id:"VIDEO-01-FLD-CRITERIA-VERSION",kind:"readonly"},
  {id:"VIDEO-01-BTN-SCORE-DETAIL",kind:"button"},{id:"VIDEO-01-BTN-CONFIRM",kind:"primary"},{id:"VIDEO-01-BTN-MODIFY",kind:"button"},{id:"VIDEO-01-BTN-LOCK",kind:"button"},{id:"VIDEO-01-BTN-HANDOFF",kind:"button"},
] as const;
const CORRECTION_SCOPE: readonly Spec[] = [
  {id:"VIDEO-01-FLD-SCENE",kind:"select"},{id:"VIDEO-01-FLD-SHOT",kind:"select"},{id:"VIDEO-01-FLD-START-TC",kind:"readonly"},{id:"VIDEO-01-FLD-END-TC",kind:"readonly"},{id:"VIDEO-01-FLD-TARGET-OBJECT",kind:"select"},{id:"VIDEO-01-FLD-TARGET-LAYER",kind:"select"},{id:"VIDEO-01-FLD-ISSUE-REF",kind:"readonly"},{id:"VIDEO-01-BTN-CONTEXT-BUILD",kind:"button"},
] as const;
const AI_CORRECTION: readonly Spec[] = [
  {id:"VIDEO-01-TXT-CORRECTION",kind:"search"},{id:"VIDEO-01-BTN-GEN-CORRECTION",kind:"button"},{id:"VIDEO-01-BTN-APPROVE-CORRECTION",kind:"button"},{id:"VIDEO-01-BTN-EXEC-CORRECTION",kind:"primary"},{id:"VIDEO-01-BTN-COMPARE-CORRECTION",kind:"button"},
] as const;
const RUNTIME: readonly Spec[] = [
  {id:"VIDEO-01-FLD-ROUTE",kind:"readonly"},{id:"VIDEO-01-FLD-PROVIDER",kind:"readonly"},{id:"VIDEO-01-FLD-JOB-STATE",kind:"readonly"},{id:"VIDEO-01-FLD-ATTEMPT",kind:"readonly"},{id:"VIDEO-01-FLD-RETRY",kind:"readonly"},{id:"VIDEO-01-FLD-CORRELATION",kind:"readonly"},{id:"VIDEO-01-BTN-RETRY",kind:"button"},{id:"VIDEO-01-BTN-RUNTIME-DETAIL",kind:"button"},
] as const;
const EVALUATION: readonly Spec[] = [
  {id:"VIDEO-01-FLD-SCORE-SCRIPT",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-IDENTITY",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-MOTION",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-CAMERA",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-SCENE",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-TIMING",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-TECH",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-ASSET",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-RIGHTS",kind:"readonly"},
  {id:"VIDEO-01-BTN-EVALUATE",kind:"button"},{id:"VIDEO-01-BTN-FINDING",kind:"button"},{id:"VIDEO-01-BTN-ISSUE-OPEN",kind:"button"},
] as const;
const MANIFEST: readonly Spec[] = [
  {id:"VIDEO-01-FLD-VIDEO-VERSION",kind:"readonly"},{id:"VIDEO-01-FLD-SHOT-VERSIONS",kind:"readonly"},{id:"VIDEO-01-FLD-LAYER-VERSIONS",kind:"readonly"},{id:"VIDEO-01-FLD-SCRIPT-HASH",kind:"readonly"},{id:"VIDEO-01-FLD-ASSET-FINGERPRINT",kind:"readonly"},{id:"VIDEO-01-FLD-OUTPUT-URI",kind:"readonly"},{id:"VIDEO-01-FLD-CHECKSUM",kind:"readonly"},{id:"VIDEO-01-FLD-SCORECARD",kind:"readonly"},{id:"VIDEO-01-FLD-EVIDENCE",kind:"readonly"},{id:"VIDEO-01-FLD-HANDOFF-CONTRACT",kind:"readonly"},
] as const;
const STATUS: readonly Spec[] = [
  {id:"VIDEO-01-FLD-PAGE-STATE",kind:"readonly"},{id:"VIDEO-01-FLD-TASK-STATE",kind:"readonly"},{id:"VIDEO-01-FLD-ERROR",kind:"readonly"},{id:"VIDEO-01-FLD-DISABLED-REASON",kind:"readonly"},{id:"VIDEO-01-FLD-AUDIT",kind:"readonly"},
] as const;
const ALL = [...CONTEXT,...PRODUCTION,...BOUND,...PREVIEW,...COMPARE,...DECISION,...CORRECTION_SCOPE,...AI_CORRECTION,...RUNTIME,...EVALUATION,...MANIFEST,...STATUS] as const;

function Readonly({id,label}:{id:string;label:string}) { return <div className={styles.readonly} data-control-id={id}><span>{label}</span><strong>—</strong></div>; }
function Control({spec}:{spec:Spec}) {
  const {locale}=useI18n(); const label=videoText(locale,spec.id);
  if(spec.kind==="readonly") return <Readonly id={spec.id} label={label}/>;
  if(spec.kind==="list") return <div className={styles.listControl} data-control-id={spec.id}><span>{label}</span><div className={styles.listEmpty}>—</div></div>;
  if(spec.kind==="select") return <label className={styles.inputControl}><span>{label}</span><select data-control-id={spec.id} disabled defaultValue=""><option value="">—</option></select></label>;
  if(spec.kind==="search") return <label className={styles.inputControl}><span>{label}</span><input data-control-id={spec.id} disabled placeholder="—"/></label>;
  if(spec.kind==="range") return <label className={styles.rangeControl}><span>{label}</span><input data-control-id={spec.id} type="range" min="0" max="100" value="0" readOnly disabled/></label>;
  if(spec.kind==="segmented") return <div className={styles.segmented} data-control-id={spec.id} aria-label={label}><button disabled className={styles.activeSegment}>AUTO</button><button disabled>MANUAL</button></div>;
  return <button className={`${styles.button} ${spec.kind==="primary"?styles.primary:""}`} data-control-id={spec.id} disabled type="button">{label}</button>;
}
function Title({children}:{children:string}) { return <h2 className={styles.sectionTitle}>{children}</h2>; }

export function VideoVisual(){
  const {locale}=useI18n();
  const registry=useMemo(()=>new Set(ALL.map(x=>x.id)),[]);
  const registryValid=registry.size===85 && Object.keys(VIDEO_CONTROL_TEXT).length===85 && [...registry].every(id=>id in VIDEO_CONTROL_TEXT);
  return <div className={styles.page} data-page-uid="VIDEO-01" data-vis-step="VIS-04" data-page-state="EMPTY" data-authority-controls="85" data-registry-valid={registryValid?"true":"false"}>
    <section className={styles.contextBar} data-section-id="VIDEO-01-SEC-01" data-component-uid="VIDEO-01-CMP-CONTEXT" data-visual-uid="VIDEO-01-VIS-CONTEXT">
      <div className={styles.contextGrid}>{CONTEXT.map(s=><Control key={s.id} spec={s}/>)}</div>
    </section>

    <div className={styles.primaryGrid}>
      <section className={`${styles.panel} ${styles.leftPanel}`} data-section-id="VIDEO-01-SEC-02" data-visual-uid="VIDEO-01-VIS-LEFT">
        <Title>{videoText(locale,"production")}</Title>
        <div className={styles.stack} data-component-uid="VIDEO-01-CMP-PRODUCTION-LIST">{PRODUCTION.map(s=><Control key={s.id} spec={s}/>)}</div>
        <div className={styles.divider}/>
        <div className={styles.boundGroups}>
          <div data-component-uid="VIDEO-01-CMP-BLUEPRINT-BIND">{BOUND.slice(0,2).map(s=><Control key={s.id} spec={s}/>)}</div>
          <div data-component-uid="VIDEO-01-CMP-SCRIPT-BIND">{BOUND.slice(2,3).map(s=><Control key={s.id} spec={s}/>)}</div>
          <div data-component-uid="VIDEO-01-CMP-DNA-BIND">{BOUND.slice(3,4).map(s=><Control key={s.id} spec={s}/>)}</div>
          <div data-component-uid="VIDEO-01-CMP-ASSET-BIND">{BOUND.slice(4).map(s=><Control key={s.id} spec={s}/>)}</div>
        </div>
      </section>

      <section className={`${styles.panel} ${styles.previewPanel}`} data-section-id="VIDEO-01-SEC-03" data-visual-uid="VIDEO-01-VIS-PREVIEW">
        <div className={styles.titleRow}><Title>{videoText(locale,"preview")}</Title><div className={styles.compareControls} data-component-uid="VIDEO-01-CMP-COMPARE" data-conditional-controls="1"><Control spec={COMPARE[0]}/><Control spec={COMPARE[1]}/><span className={styles.candidateNote}>{videoText(locale,"noCandidateCompare")}</span></div></div>
        <div className={styles.previewComponent} data-component-uid="VIDEO-01-CMP-PREVIEW">
          <div className={styles.viewerScreen} data-viewer-count="1">—</div>
          <div className={styles.transport}>{PREVIEW.map(s=><Control key={s.id} spec={s}/>)}</div>
        </div>
      </section>

      <section className={`${styles.panel} ${styles.rightPanel}`} data-section-id="VIDEO-01-SEC-04" data-visual-uid="VIDEO-01-VIS-RIGHT">
        <Title>{videoText(locale,"decision")}</Title>
        <div className={styles.stack} data-component-uid="VIDEO-01-CMP-VERSION">{[DECISION[0],DECISION[1],DECISION[4]].map(s=><Control key={s.id} spec={s}/>)}</div>
        <div className={styles.divider}/>
        <div className={styles.stack} data-component-uid="VIDEO-01-CMP-SCORE">{[DECISION[2],DECISION[3]].map(s=><Control key={s.id} spec={s}/>)}</div>
        <div className={styles.divider}/>
        <div className={styles.stack} data-component-uid="VIDEO-01-CMP-DECISION">{DECISION.slice(5).map(s=><Control key={s.id} spec={s}/>)}</div>
      </section>
    </div>

    <section className={`${styles.panel} ${styles.conditional}`} data-section-id="VIDEO-01-SEC-05" data-visual-uid="VIDEO-01-VIS-CORRECTION">
      <Title>{videoText(locale,"correctionScope")}</Title><div data-component-uid="VIDEO-01-CMP-CORRECTION-SCOPE" data-conditional-controls={CORRECTION_SCOPE.length}><div className={styles.conditionNotice}>{videoText(locale,"conditionalCorrection")}</div></div>
    </section>

    <div className={styles.correctionRuntimeGrid}>
      <section className={`${styles.panel} ${styles.conditional}`} data-section-id="VIDEO-01-SEC-06" data-visual-uid="VIDEO-01-VIS-AI-REVISION">
        <Title>{videoText(locale,"aiCorrection")}</Title><div data-component-uid="VIDEO-01-CMP-AI-REVISION" data-conditional-controls={AI_CORRECTION.length}><div className={styles.conditionNotice}>{videoText(locale,"conditionalCorrection")}</div></div>
      </section>
      <section className={styles.panel} data-section-id="VIDEO-01-SEC-07" data-visual-uid="VIDEO-01-VIS-RUNTIME">
        <Title>{videoText(locale,"runtime")}</Title><div className={styles.runtimeGrid} data-component-uid="VIDEO-01-CMP-PROVIDER-RUNTIME">{RUNTIME.map(s=><Control key={s.id} spec={s}/>)}</div>
      </section>
    </div>

    <section className={styles.panel} data-section-id="VIDEO-01-SEC-08" data-visual-uid="VIDEO-01-VIS-EVAL">
      <Title>{videoText(locale,"evaluation")}</Title><div className={styles.evaluationGrid} data-component-uid="VIDEO-01-CMP-EVALUATION">{EVALUATION.map(s=><Control key={s.id} spec={s}/>)}</div>
    </section>

    <section className={styles.panel} data-section-id="VIDEO-01-SEC-09" data-visual-uid="VIDEO-01-VIS-OUTPUT">
      <Title>{videoText(locale,"manifest")}</Title><div className={styles.manifestGrid} data-component-uid="VIDEO-01-CMP-MANIFEST">{MANIFEST.map(s=><Control key={s.id} spec={s}/>)}</div>
    </section>

    <section className={`${styles.panel} ${styles.statusPanel}`} data-section-id="VIDEO-01-SEC-10">
      <Title>{videoText(locale,"status")}</Title><div className={styles.statusGrid} data-component-uid="VIDEO-01-CMP-STATUS">{STATUS.map(s=><Control key={s.id} spec={s}/>)}</div>
    </section>
  </div>;
}
