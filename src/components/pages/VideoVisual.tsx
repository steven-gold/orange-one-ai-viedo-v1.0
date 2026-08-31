"use client";

import { useMemo, useReducer, useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { VIDEO_CONTROL_TEXT, videoText } from "@/i18n/videoCatalog";
import { invokeVideoAction } from "@/domain/video/videoClientPort";
import { INITIAL_VIDEO_CLIENT_STATE, reduceVideoClientState, type VideoMode } from "@/domain/video/videoClientState";
import { VIDEO_CONTROL_ACTION } from "@/domain/video/videoControlRuntime";
import type { VideoActionUid } from "@/domain/video/videoRuntimeContract";
import styles from "./VideoVisual.module.css";

type Kind = "readonly" | "button" | "primary" | "select" | "search" | "segmented" | "list" | "range";
type Spec = { id: string; kind: Kind };
type PageState = "READY" | "ERROR";

const CONTEXT: readonly Spec[] = [
  {id:"VIDEO-01-FLD-PROJECT",kind:"select"},{id:"VIDEO-01-FLD-TOPIC",kind:"select"},{id:"VIDEO-01-FLD-TASK",kind:"select"},{id:"VIDEO-01-FLD-STATUS",kind:"readonly"},
  {id:"VIDEO-01-CTL-MODE",kind:"segmented"},{id:"VIDEO-01-BTN-EXECUTE",kind:"primary"},{id:"VIDEO-01-BTN-BLUEPRINT",kind:"button"},{id:"VIDEO-01-BTN-PACKAGE",kind:"button"},
] as const;
const PRODUCTION: readonly Spec[] = [{id:"VIDEO-01-FLD-SEARCH",kind:"search"},{id:"VIDEO-01-CTL-FILTER",kind:"select"},{id:"VIDEO-01-CTL-SHOT-SELECT",kind:"list"}] as const;
const BOUND: readonly Spec[] = [
  {id:"VIDEO-01-FLD-BLUEPRINT-REF",kind:"readonly"},{id:"VIDEO-01-FLD-INPUT-FINGERPRINT",kind:"readonly"},{id:"VIDEO-01-FLD-SCRIPT-SECTION",kind:"readonly"},{id:"VIDEO-01-FLD-DNA-REFS",kind:"readonly"},
  {id:"VIDEO-01-FLD-ASSET-REFS",kind:"readonly"},{id:"VIDEO-01-FLD-FILENAME-CHECKSUM",kind:"readonly"},{id:"VIDEO-01-FLD-RIGHTS",kind:"readonly"},{id:"VIDEO-01-FLD-INSTRUCTION",kind:"readonly"},
] as const;
const PREVIEW: readonly Spec[] = [{id:"VIDEO-01-BTN-PLAY",kind:"button"},{id:"VIDEO-01-CTL-SEEK",kind:"range"},{id:"VIDEO-01-FLD-TIMECODE",kind:"readonly"},{id:"VIDEO-01-BTN-VOLUME",kind:"button"},{id:"VIDEO-01-BTN-FULLSCREEN",kind:"button"}] as const;
const COMPARE: readonly Spec[] = [{id:"VIDEO-01-CTL-COMPARE",kind:"button"},{id:"VIDEO-01-CTL-VERSION-A",kind:"select"},{id:"VIDEO-01-CTL-VERSION-B",kind:"select"}] as const;
const DECISION: readonly Spec[] = [
  {id:"VIDEO-01-FLD-CURRENT-VERSION",kind:"readonly"},{id:"VIDEO-01-FLD-CANDIDATE-VERSION",kind:"readonly"},{id:"VIDEO-01-FLD-OVERALL-SCORE",kind:"readonly"},{id:"VIDEO-01-FLD-ISSUE-SUMMARY",kind:"readonly"},{id:"VIDEO-01-FLD-CRITERIA-VERSION",kind:"readonly"},
  {id:"VIDEO-01-BTN-SCORE-DETAIL",kind:"button"},{id:"VIDEO-01-BTN-CONFIRM",kind:"primary"},{id:"VIDEO-01-BTN-MODIFY",kind:"button"},{id:"VIDEO-01-BTN-LOCK",kind:"button"},{id:"VIDEO-01-BTN-HANDOFF",kind:"button"},
] as const;
const CORRECTION_SCOPE: readonly Spec[] = [
  {id:"VIDEO-01-FLD-SCENE",kind:"select"},{id:"VIDEO-01-FLD-SHOT",kind:"select"},{id:"VIDEO-01-FLD-START-TC",kind:"search"},{id:"VIDEO-01-FLD-END-TC",kind:"search"},{id:"VIDEO-01-FLD-TARGET-OBJECT",kind:"select"},{id:"VIDEO-01-FLD-TARGET-LAYER",kind:"select"},{id:"VIDEO-01-FLD-ISSUE-REF",kind:"readonly"},{id:"VIDEO-01-BTN-CONTEXT-BUILD",kind:"button"},
] as const;
const AI_CORRECTION: readonly Spec[] = [{id:"VIDEO-01-TXT-CORRECTION",kind:"search"},{id:"VIDEO-01-BTN-GEN-CORRECTION",kind:"button"},{id:"VIDEO-01-BTN-APPROVE-CORRECTION",kind:"button"},{id:"VIDEO-01-BTN-EXEC-CORRECTION",kind:"primary"},{id:"VIDEO-01-BTN-COMPARE-CORRECTION",kind:"button"}] as const;
const RUNTIME: readonly Spec[] = [{id:"VIDEO-01-FLD-ROUTE",kind:"readonly"},{id:"VIDEO-01-FLD-PROVIDER",kind:"readonly"},{id:"VIDEO-01-FLD-JOB-STATE",kind:"readonly"},{id:"VIDEO-01-FLD-ATTEMPT",kind:"readonly"},{id:"VIDEO-01-FLD-RETRY",kind:"readonly"},{id:"VIDEO-01-FLD-CORRELATION",kind:"readonly"},{id:"VIDEO-01-BTN-RETRY",kind:"button"},{id:"VIDEO-01-BTN-RUNTIME-DETAIL",kind:"button"}] as const;
const EVALUATION: readonly Spec[] = [
  {id:"VIDEO-01-FLD-SCORE-SCRIPT",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-IDENTITY",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-MOTION",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-CAMERA",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-SCENE",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-TIMING",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-TECH",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-ASSET",kind:"readonly"},{id:"VIDEO-01-FLD-SCORE-RIGHTS",kind:"readonly"},
  {id:"VIDEO-01-BTN-EVALUATE",kind:"button"},{id:"VIDEO-01-BTN-FINDING",kind:"button"},{id:"VIDEO-01-BTN-ISSUE-OPEN",kind:"button"},
] as const;
const MANIFEST: readonly Spec[] = [{id:"VIDEO-01-FLD-VIDEO-VERSION",kind:"readonly"},{id:"VIDEO-01-FLD-SHOT-VERSIONS",kind:"readonly"},{id:"VIDEO-01-FLD-LAYER-VERSIONS",kind:"readonly"},{id:"VIDEO-01-FLD-SCRIPT-HASH",kind:"readonly"},{id:"VIDEO-01-FLD-ASSET-FINGERPRINT",kind:"readonly"},{id:"VIDEO-01-FLD-OUTPUT-URI",kind:"readonly"},{id:"VIDEO-01-FLD-CHECKSUM",kind:"readonly"},{id:"VIDEO-01-FLD-SCORECARD",kind:"readonly"},{id:"VIDEO-01-FLD-EVIDENCE",kind:"readonly"},{id:"VIDEO-01-FLD-HANDOFF-CONTRACT",kind:"readonly"}] as const;
const STATUS: readonly Spec[] = [{id:"VIDEO-01-FLD-PAGE-STATE",kind:"readonly"},{id:"VIDEO-01-FLD-TASK-STATE",kind:"readonly"},{id:"VIDEO-01-FLD-ERROR",kind:"readonly"},{id:"VIDEO-01-FLD-DISABLED-REASON",kind:"readonly"},{id:"VIDEO-01-FLD-AUDIT",kind:"readonly"}] as const;
const ALL = [...CONTEXT,...PRODUCTION,...BOUND,...PREVIEW,...COMPARE,...DECISION,...CORRECTION_SCOPE,...AI_CORRECTION,...RUNTIME,...EVALUATION,...MANIFEST,...STATUS] as const;

function actionOf(id:string):VideoActionUid{return VIDEO_CONTROL_ACTION[id]??"VIDEO-01-ACT-NOOP-VIEW";}
function Title({children}:{children:string}) { return <h2 className={styles.sectionTitle}>{children}</h2>; }
type ControlProps={spec:Spec;value?:string|number;mode?:VideoMode;disabled?:boolean;onAction:(id:string)=>void;onValue:(id:string,value:string)=>void};
function Control({spec,value="",mode="AUTO",disabled=false,onAction,onValue}:ControlProps) {
  const {locale}=useI18n(); const label=videoText(locale,spec.id); const action=actionOf(spec.id);
  if(spec.kind==="readonly") return <div className={styles.readonly} data-control-id={spec.id} data-action-uid={action}><span>{label}</span><strong>{value||"—"}</strong></div>;
  if(spec.kind==="list") return <div className={styles.listControl} data-control-id={spec.id} data-action-uid={action}><span>{label}</span><div className={styles.listEmpty}>—</div></div>;
  if(spec.kind==="select") return <label className={styles.inputControl}><span>{label}</span><select data-control-id={spec.id} data-action-uid={action} value={String(value)} disabled={disabled} onChange={e=>onValue(spec.id,e.target.value)}><option value="">—</option></select></label>;
  if(spec.kind==="search") return <label className={styles.inputControl}><span>{label}</span><input data-control-id={spec.id} data-action-uid={action} disabled={disabled} value={String(value)} onChange={e=>onValue(spec.id,e.target.value)} placeholder="—"/></label>;
  if(spec.kind==="range") return <label className={styles.rangeControl}><span>{label}</span><input data-control-id={spec.id} data-action-uid={action} type="range" min="0" max="100" value={Number(value)||0} disabled={disabled} onChange={e=>onValue(spec.id,e.target.value)}/></label>;
  if(spec.kind==="segmented") return <div className={styles.segmented} data-control-id={spec.id} data-action-uid={action} aria-label={label}><button type="button" disabled={disabled} className={mode==="AUTO"?styles.activeSegment:""} onClick={()=>onValue(spec.id,"AUTO")}>AUTO</button><button type="button" disabled={disabled} className={mode==="MANUAL"?styles.activeSegment:""} onClick={()=>onValue(spec.id,"MANUAL")}>MANUAL</button></div>;
  return <button className={`${styles.button} ${spec.kind==="primary"?styles.primary:""}`} data-control-id={spec.id} data-action-uid={action} data-runtime-binding="ACTION_BOUND" disabled={disabled} type="button" onClick={()=>onAction(spec.id)}>{label}</button>;
}

export function VideoVisual(){
  const {locale}=useI18n();
  const registry=useMemo(()=>new Set(ALL.map(x=>x.id)),[]);
  const registryValid=registry.size===85 && Object.keys(VIDEO_CONTROL_TEXT).length===85 && [...registry].every(id=>id in VIDEO_CONTROL_TEXT);
  const [state,dispatch]=useReducer(reduceVideoClientState,INITIAL_VIDEO_CLIENT_STATE);
  const [pageState,setPageState]=useState<PageState>("READY");
  const [runtimeReason,setRuntimeReason]=useState<string|null>(null);
  const [busy,setBusy]=useState<VideoActionUid|null>(null);
  const block=(reason:string)=>{setPageState("ERROR");setRuntimeReason(reason);};
  const requireTask=()=>state.task_ref||(block("VIDEO-01-ERR-CONTEXT-001:REQUIRED_TASK_REF_MISSING"),null);
  const server=async(action_uid:VideoActionUid,path_params?:Record<string,string>,payload?:unknown)=>{if(busy)return;setBusy(action_uid);const result=await invokeVideoAction({action_uid,path_params,payload});setBusy(null);if(result.ok){setPageState("READY");setRuntimeReason(null);}else{setPageState("ERROR");setRuntimeReason(result.reason_code);}};

  const onValue=(id:string,value:string)=>{switch(actionOf(id)){
    case"VIDEO-01-ACT-PROJECT-SET":dispatch({action_uid:"VIDEO-01-ACT-PROJECT-SET",project_ref:value||null});break;
    case"VIDEO-01-ACT-TOPIC-SET":dispatch({action_uid:"VIDEO-01-ACT-TOPIC-SET",topic_ref:value||null});break;
    case"VIDEO-01-ACT-TASK-SET":dispatch({action_uid:"VIDEO-01-ACT-TASK-SET",task_ref:value||null});break;
    case"VIDEO-01-ACT-MODE-SET":dispatch({action_uid:"VIDEO-01-ACT-MODE-SET",mode:value as VideoMode});break;
    case"VIDEO-01-ACT-LIST-SEARCH":dispatch({action_uid:"VIDEO-01-ACT-LIST-SEARCH",search:value});break;
    case"VIDEO-01-ACT-LIST-FILTER":dispatch({action_uid:"VIDEO-01-ACT-LIST-FILTER",filter:value||null});break;
    case"VIDEO-01-ACT-COMPARE-A":dispatch({action_uid:"VIDEO-01-ACT-COMPARE-A",version_ref:value||null});break;
    case"VIDEO-01-ACT-COMPARE-B":dispatch({action_uid:"VIDEO-01-ACT-COMPARE-B",version_ref:value||null});break;
    case"VIDEO-01-ACT-PREVIEW-SEEK":dispatch({action_uid:"VIDEO-01-ACT-PREVIEW-SEEK",seek:Number(value)||0});break;
    case"VIDEO-01-ACT-CORRECTION-REQUEST-SET":dispatch({action_uid:"VIDEO-01-ACT-CORRECTION-REQUEST-SET",request:value});break;
    case"VIDEO-01-ACT-CORRECTION-SCOPE-SET":{const keys:Record<string,string>={"VIDEO-01-FLD-SCENE":"scene","VIDEO-01-FLD-SHOT":"shot","VIDEO-01-FLD-START-TC":"start_tc","VIDEO-01-FLD-END-TC":"end_tc","VIDEO-01-FLD-TARGET-OBJECT":"target_object","VIDEO-01-FLD-TARGET-LAYER":"target_layer"};const key=keys[id];if(key)dispatch({action_uid:"VIDEO-01-ACT-CORRECTION-SCOPE-SET",key,value:value||null});break;}
  }};
  const onAction=(id:string)=>{const action=actionOf(id);switch(action){
    case"VIDEO-01-ACT-PREVIEW-PLAY":dispatch({action_uid:action});return;
    case"VIDEO-01-ACT-PREVIEW-VOLUME":dispatch({action_uid:action});return;
    case"VIDEO-01-ACT-PREVIEW-FULLSCREEN":dispatch({action_uid:action,fullscreen:!state.fullscreen});return;
    case"VIDEO-01-ACT-COMPARE-TOGGLE":dispatch({action_uid:action});return;
    case"VIDEO-01-ACT-CORRECTION-OPEN":dispatch({action_uid:action});return;
    case"VIDEO-01-ACT-FLOW-START":{const taskId=requireTask();if(taskId)void server(action,{taskId},{mode:state.mode});return;}
    case"VIDEO-01-ACT-TASK-RETRY":{const taskId=requireTask();if(taskId)void server(action,{taskId});return;}
    case"VIDEO-01-ACT-CORRECTION-EXECUTE":{const taskId=requireTask();if(taskId)void server(action,{taskId},{scope:state.correction_scope,request:state.correction_request});return;}
    case"VIDEO-01-ACT-CORRECTION-GENERATE":case"VIDEO-01-ACT-CORRECTION-APPROVE":void server(action,undefined,{scope:state.correction_scope,request:state.correction_request});return;
    case"VIDEO-01-ACT-EVALUATE":{if(!requireTask())return;void server(action,undefined,{task_ref:state.task_ref});return;}
    case"VIDEO-01-ACT-CANDIDATE-CONFIRM":block("VIDEO-01-ERR-CANDIDATE-001:EXACT_OUTPUT_VERSION_ID_REQUIRED");return;
    case"VIDEO-01-ACT-FINDING-CREATE":block("VIDEO-01-ERR-CRITERIA-001:EXACT_FINDING_PAYLOAD_REQUIRED");return;
    case"VIDEO-01-ACT-HANDOFF":block("VIDEO-01-ERR-HANDOFF-001:EXACT_HANDOFF_PAYLOAD_REQUIRED");return;
    case"VIDEO-01-ACT-VERSION-LOCK":block("VIDEO-01-ERR-VERSION-001:EXACT_VIDEO_VERSION_REQUIRED");return;
    case"VIDEO-01-ACT-ISSUE-OPEN":dispatch({action_uid:action,issue_ref:state.issue_ref});return;
    default:block(`${action}:EXACT_RUNTIME_CONTEXT_REQUIRED`);
  }};
  const valueFor=(id:string):string|number=>{switch(id){
    case"VIDEO-01-FLD-PROJECT":return state.project_ref??"";case"VIDEO-01-FLD-TOPIC":return state.topic_ref??"";case"VIDEO-01-FLD-TASK":return state.task_ref??"";
    case"VIDEO-01-FLD-SEARCH":return state.search;case"VIDEO-01-CTL-FILTER":return state.filter??"";case"VIDEO-01-CTL-SEEK":return state.seek;case"VIDEO-01-FLD-TIMECODE":return String(state.seek);
    case"VIDEO-01-CTL-VERSION-A":return state.version_a??"";case"VIDEO-01-CTL-VERSION-B":return state.version_b??"";case"VIDEO-01-TXT-CORRECTION":return state.correction_request;
    case"VIDEO-01-FLD-SCENE":return state.correction_scope.scene??"";case"VIDEO-01-FLD-SHOT":return state.correction_scope.shot??"";case"VIDEO-01-FLD-START-TC":return state.correction_scope.start_tc??"";case"VIDEO-01-FLD-END-TC":return state.correction_scope.end_tc??"";case"VIDEO-01-FLD-TARGET-OBJECT":return state.correction_scope.target_object??"";case"VIDEO-01-FLD-TARGET-LAYER":return state.correction_scope.target_layer??"";
    case"VIDEO-01-FLD-PAGE-STATE":return pageState;case"VIDEO-01-FLD-ERROR":return runtimeReason??"";case"VIDEO-01-FLD-DISABLED-REASON":return runtimeReason??"";case"VIDEO-01-FLD-STATUS":return busy??pageState;
    default:return"";
  }};
  const control=(spec:Spec)=><Control key={spec.id} spec={spec} value={valueFor(spec.id)} mode={state.mode} disabled={busy!==null} onAction={onAction} onValue={onValue}/>;

  return <div className={styles.page} data-page-uid="VIDEO-01" data-vis-step="VIS-04" data-page-state={pageState} data-authority-controls="85" data-registry-valid={registryValid?"true":"false"} data-runtime-reason={runtimeReason??undefined}>
    <section className={styles.contextBar} data-section-id="VIDEO-01-SEC-01" data-component-uid="VIDEO-01-CMP-CONTEXT" data-visual-uid="VIDEO-01-VIS-CONTEXT"><div className={styles.contextGrid}>{CONTEXT.map(control)}</div></section>
    <div className={styles.primaryGrid}>
      <section className={`${styles.panel} ${styles.leftPanel}`} data-section-id="VIDEO-01-SEC-02" data-visual-uid="VIDEO-01-VIS-LEFT"><Title>{videoText(locale,"production")}</Title><div className={styles.stack} data-component-uid="VIDEO-01-CMP-PRODUCTION-LIST">{PRODUCTION.map(control)}</div><div className={styles.divider}/><div className={styles.boundGroups}><div data-component-uid="VIDEO-01-CMP-BLUEPRINT-BIND">{BOUND.slice(0,2).map(control)}</div><div data-component-uid="VIDEO-01-CMP-SCRIPT-BIND">{BOUND.slice(2,3).map(control)}</div><div data-component-uid="VIDEO-01-CMP-DNA-BIND">{BOUND.slice(3,4).map(control)}</div><div data-component-uid="VIDEO-01-CMP-ASSET-BIND">{BOUND.slice(4).map(control)}</div></div></section>
      <section className={`${styles.panel} ${styles.previewPanel}`} data-section-id="VIDEO-01-SEC-03" data-visual-uid="VIDEO-01-VIS-PREVIEW"><div className={styles.titleRow}><Title>{videoText(locale,"preview")}</Title><div className={styles.compareControls} data-component-uid="VIDEO-01-CMP-COMPARE" data-conditional-controls="1">{control(COMPARE[0])}{state.compare&&control(COMPARE[1])}{state.compare&&control(COMPARE[2])}{!state.compare&&<span className={styles.candidateNote}>{videoText(locale,"noCandidateCompare")}</span>}</div></div><div className={styles.previewComponent} data-component-uid="VIDEO-01-CMP-PREVIEW"><div className={styles.viewerScreen} data-viewer-count={state.compare?"2":"1"}>—</div><div className={styles.transport}>{PREVIEW.map(control)}</div></div></section>
      <section className={`${styles.panel} ${styles.rightPanel}`} data-section-id="VIDEO-01-SEC-04" data-visual-uid="VIDEO-01-VIS-RIGHT"><Title>{videoText(locale,"decision")}</Title><div className={styles.stack} data-component-uid="VIDEO-01-CMP-VERSION">{[DECISION[0],DECISION[1],DECISION[4]].map(control)}</div><div className={styles.divider}/><div className={styles.stack} data-component-uid="VIDEO-01-CMP-SCORE">{[DECISION[2],DECISION[3]].map(control)}</div><div className={styles.divider}/><div className={styles.stack} data-component-uid="VIDEO-01-CMP-DECISION">{DECISION.slice(5).map(control)}</div></section>
    </div>
    <section className={`${styles.panel} ${styles.conditional}`} data-section-id="VIDEO-01-SEC-05" data-visual-uid="VIDEO-01-VIS-CORRECTION"><Title>{videoText(locale,"correctionScope")}</Title><div data-component-uid="VIDEO-01-CMP-CORRECTION-SCOPE" data-conditional-controls={CORRECTION_SCOPE.length}>{state.correction_open?<div className={styles.stack}>{CORRECTION_SCOPE.map(control)}</div>:<div className={styles.conditionNotice}>{videoText(locale,"conditionalCorrection")}</div>}</div></section>
    <div className={styles.correctionRuntimeGrid}><section className={`${styles.panel} ${styles.conditional}`} data-section-id="VIDEO-01-SEC-06" data-visual-uid="VIDEO-01-VIS-AI-REVISION"><Title>{videoText(locale,"aiCorrection")}</Title><div data-component-uid="VIDEO-01-CMP-AI-REVISION" data-conditional-controls={AI_CORRECTION.length}>{state.correction_open?<div className={styles.stack}>{AI_CORRECTION.map(control)}</div>:<div className={styles.conditionNotice}>{videoText(locale,"conditionalCorrection")}</div>}</div></section><section className={styles.panel} data-section-id="VIDEO-01-SEC-07" data-visual-uid="VIDEO-01-VIS-RUNTIME"><Title>{videoText(locale,"runtime")}</Title><div className={styles.runtimeGrid} data-component-uid="VIDEO-01-CMP-PROVIDER-RUNTIME">{RUNTIME.map(control)}</div></section></div>
    <section className={styles.panel} data-section-id="VIDEO-01-SEC-08" data-visual-uid="VIDEO-01-VIS-EVAL"><Title>{videoText(locale,"evaluation")}</Title><div className={styles.evaluationGrid} data-component-uid="VIDEO-01-CMP-EVALUATION">{EVALUATION.map(control)}</div></section>
    <section className={styles.panel} data-section-id="VIDEO-01-SEC-09" data-visual-uid="VIDEO-01-VIS-OUTPUT"><Title>{videoText(locale,"manifest")}</Title><div className={styles.manifestGrid} data-component-uid="VIDEO-01-CMP-MANIFEST">{MANIFEST.map(control)}</div></section>
    <section className={`${styles.panel} ${styles.statusPanel}`} data-section-id="VIDEO-01-SEC-10"><Title>{videoText(locale,"status")}</Title><div className={styles.statusGrid} data-component-uid="VIDEO-01-CMP-STATUS">{STATUS.map(control)}</div></section>
  </div>;
}
