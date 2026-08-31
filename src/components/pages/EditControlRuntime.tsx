"use client";

import { createContext, useContext, useEffect, useMemo, useReducer, useState, type ReactNode } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { editText } from "@/i18n/editCatalog";
import { EDIT_CONTROL_BINDINGS, type EditControlUid } from "@/domain/edit/editControlBindings";
import { INITIAL_EDIT_CLIENT_STATE, reduceEditClientState, type EditClientState, type EditExecutionMode, type EditInspectorTab, type EditSourceMode } from "@/domain/edit/editClientState";
import { readEditProjection } from "@/domain/edit/editProjectionPort";
import { invokeGovernedEditAction, isEditActionInvokerBound } from "@/domain/edit/editActionPort";
import styles from "./EditVisual.module.css";

export type EditControlKind = "readonly"|"button"|"primary"|"select"|"search"|"segmented"|"list"|"range"|"timecode"|"toggle"|"overview"|"tab"|"number"|"textarea"|"preview";

type RuntimeContext = {
  state: EditClientState;
  dispatch: React.Dispatch<Parameters<typeof reduceEditClientState>[1]>;
  runtimeError: string|null;
  setRuntimeError: (value:string|null)=>void;
};

const Ctx=createContext<RuntimeContext|null>(null);

const TAB_BY_ID: Record<string,EditInspectorTab>={
  "EDIT-01-TAB-CLIP":"CLIP","EDIT-01-TAB-API":"API","EDIT-01-TAB-VOICE":"VOICE","EDIT-01-TAB-AUDIO":"AUDIO","EDIT-01-TAB-LIPSYNC":"LIPSYNC",
  "EDIT-01-TAB-SUBTITLE":"SUBTITLE","EDIT-01-TAB-EVALUATION":"EVALUATION","EDIT-01-TAB-VERSION":"VERSION","EDIT-01-TAB-OUTPUT":"OUTPUT",
};

function gatePass(state:EditClientState,gateUid:string|null|undefined){
  if(!gateUid)return false;
  if(gateUid==="EDIT-01-GATE-CONTEXT-MUTABLE")return state.resolved.page_state_uid!=="EDIT-01-ST-PAGE-LOCKED"&&state.resolved.page_state_uid!=="EDIT-01-ST-PAGE-HANDED_OFF";
  if(gateUid==="EDIT-01-GATE-STANDALONE")return state.source_mode==="STANDALONE_UPLOAD"&&state.resolved.gate_state[gateUid]===true;
  return state.resolved.gate_state[gateUid]===true;
}

function readonlyValue(id:string,state:EditClientState,runtimeError:string|null){
  if(id==="EDIT-01-LBL-PAGE-STATE")return state.resolved.page_state_uid??"—";
  if(id==="EDIT-01-LBL-CURRENT-STAGE")return state.resolved.current_stage_uid??"—";
  if(id==="EDIT-01-LBL-STAGE-SCORE")return state.resolved.current_stage_score===null?"—":String(state.resolved.current_stage_score);
  if(id==="EDIT-01-LBL-ERROR-STATE")return state.resolved.current_error_uid??runtimeError??"—";
  if(id==="EDIT-01-FLD-PROJECT")return state.resolved.project_id??"—";
  if(id==="EDIT-01-FLD-TOPIC")return state.resolved.topic_id??"—";
  if(id==="EDIT-01-FLD-TASK")return state.resolved.task_id??"—";
  if(id==="EDIT-01-FLD-TIMECODE")return state.playhead===null?"—":String(state.playhead);
  if(id==="EDIT-01-LBL-BINDING-FINGERPRINT")return state.resolved.input_fingerprint??"—";
  if(id==="EDIT-01-LBL-LIPSYNC-SYNC-BINDING"||id==="EDIT-01-LBL-SUB-SYNC-BINDING")return state.resolved.dialogue_timing_binding_ref??"—";
  return "—";
}

export function EditRuntimeProvider({children}:{children:ReactNode}){
  const [state,dispatch]=useReducer(reduceEditClientState,INITIAL_EDIT_CLIENT_STATE);
  const [runtimeError,setRuntimeError]=useState<string|null>(null);
  useEffect(()=>{
    const controller=new AbortController();
    void readEditProjection(controller.signal).then(result=>{
      if(result.ok){dispatch({type:"BIND_RESOLVED_CONTEXT",value:result.context});setRuntimeError(null);}
      else setRuntimeError(`${result.error_uid}: ${result.reason_code}`);
    });
    return()=>controller.abort();
  },[]);
  const value=useMemo(()=>({state,dispatch,runtimeError,setRuntimeError}),[state,runtimeError]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useEditRuntimeState(){
  const value=useContext(Ctx);
  if(!value)throw new Error("EDIT_RUNTIME_PROVIDER_REQUIRED");
  return value;
}

async function invokeFormalAction(id:EditControlUid,state:EditClientState,setRuntimeError:(v:string|null)=>void){
  const binding=EDIT_CONTROL_BINDINGS[id];
  if(!binding.action_uid){setRuntimeError("EDIT-01-ERR-CONTEXT-001: CONTROL_HAS_NO_ACTION");return;}
  if(!isEditActionInvokerBound()){setRuntimeError("EDIT-01-ERR-CONTEXT-001: EDIT_ACTION_CLIENT_ADAPTER_NOT_BOUND");return;}
  const result=await invokeGovernedEditAction({action_uid:binding.action_uid,source_mode:state.source_mode,state});
  if(result.ok)setRuntimeError(null);else setRuntimeError(`${result.error_uid}: ${result.reason_code}`);
}

export function EditRuntimeControl({controlId,kind,compact=false}:{controlId:string;kind:EditControlKind;compact?:boolean}){
  const runtime=useEditRuntimeState();
  const {state,dispatch,runtimeError,setRuntimeError}=runtime;
  const {locale}=useI18n();
  const id=controlId as EditControlUid;
  const binding=EDIT_CONTROL_BINDINGS[id];
  const label=editText(locale,controlId);
  const gateAllowed=Boolean(binding)&&gatePass(state,binding.gate_uid);
  const local=binding?.effect_type==="UI_ONLY"||binding?.effect_type==="CONTEXT_STATE";
  const executable=Boolean(binding?.action_uid);
  const formalReady=local||isEditActionInvokerBound();
  const enabled=executable&&gateAllowed&&formalReady;
  const disabledReason=!binding?"CONTROL_NOT_IN_AUTHORITY":!executable?"READ_ONLY":!gateAllowed?binding.gate_uid:!formalReady?"FORMAL_RUNTIME_ADAPTER_NOT_BOUND":undefined;
  const common={
    "data-control-id":controlId,
    "data-action-uid":binding?.action_uid??undefined,
    "data-gate-uid":binding?.gate_uid??undefined,
    "data-permission-uid":binding?.permission_uid??undefined,
    "data-effect-type":binding?.effect_type??undefined,
    "data-disabled-reason":disabledReason,
  };

  const localClick=()=>{
    switch(controlId){
      case"EDIT-01-BTN-PLAY":dispatch({type:"PLAY"});return true;
      case"EDIT-01-BTN-PAUSE":dispatch({type:"PAUSE"});return true;
      case"EDIT-01-BTN-CLEAR-RANGE":dispatch({type:"RANGE_CLEAR"});return true;
      case"EDIT-01-CTL-SNAP":dispatch({type:"SNAP"});return true;
      case"EDIT-01-BTN-ZOOM-IN":dispatch({type:"ZOOM_IN"});return true;
      case"EDIT-01-BTN-ZOOM-OUT":dispatch({type:"ZOOM_OUT"});return true;
      case"EDIT-01-BTN-ZOOM-FIT":dispatch({type:"ZOOM_FIT"});return true;
      case"EDIT-01-BTN-MUTE":dispatch({type:"MUTE"});return true;
      case"EDIT-01-CTL-LOOP":dispatch({type:"LOOP"});return true;
      case"EDIT-01-BTN-SET-IN":if(state.playhead!==null){dispatch({type:"RANGE_IN",value:state.playhead});return true;}setRuntimeError("EDIT-01-ERR-TIME-001: CANONICAL_PLAYHEAD_REQUIRED");return true;
      case"EDIT-01-BTN-SET-OUT":if(state.playhead!==null){dispatch({type:"RANGE_OUT",value:state.playhead});return true;}setRuntimeError("EDIT-01-ERR-TIME-001: CANONICAL_PLAYHEAD_REQUIRED");return true;
      case"EDIT-01-BTN-FULLSCREEN":{const el=document.querySelector('[data-component-uid="EDIT-01-CMP-PREVIEW"]');if(el instanceof HTMLElement&&el.requestFullscreen){void el.requestFullscreen().catch(()=>setRuntimeError("EDIT-01-ERR-CONTEXT-001: FULLSCREEN_REQUEST_FAILED"));}return true;}
      case"EDIT-01-CTL-SUBTITLE-TOGGLE":dispatch({type:"SUBTITLE_TOGGLE"});return true;
      default:return false;
    }
  };

  const click=()=>{
    if(localClick()){setRuntimeError(null);return;}
    if(local){setRuntimeError("EDIT-01-ERR-CONTEXT-001: LOCAL_CONTROL_REQUIRES_RESOLVED_SELECTION");return;}
    void invokeFormalAction(id,state,setRuntimeError);
  };

  if(kind==="readonly"||kind==="overview")return <div className={`${styles.readonly} ${compact?styles.compact:""}`} {...common}><span>{label}</span><strong>{readonlyValue(controlId,state,runtimeError)}</strong></div>;
  if(kind==="list")return <div className={styles.listControl} {...common}><span>{label}</span><div className={styles.listEmpty}>—</div></div>;
  if(kind==="preview")return <div className={styles.previewControl} {...common}><span>{label}</span><div>—</div></div>;
  if(kind==="segmented"){
    const source=controlId==="EDIT-01-CTL-SOURCE-MODE";
    const options=source?["PROJECT_TASK","STANDALONE_UPLOAD"]:["AUTO","MANUAL"];
    return <div className={styles.segmentedControl} {...common} aria-label={label}><span>{label}</span><div className={styles.segmentedButtons}>{options.map(option=><button key={option} type="button" disabled={!enabled} aria-pressed={source?state.source_mode===option:state.execution_mode===option} onClick={()=>source?dispatch({type:"SOURCE_MODE",value:option as EditSourceMode}):dispatch({type:"EXECUTION_MODE",value:option as EditExecutionMode})}>{option}</button>)}</div></div>;
  }
  if(kind==="tab"){
    const tab=TAB_BY_ID[controlId];
    return <button className={`${styles.tab} ${state.inspector_tab===tab?styles.selectedTab:""}`} type="button" disabled={!enabled} onClick={()=>tab&&dispatch({type:"INSPECTOR_TAB",value:tab})} {...common}>{label}</button>;
  }
  if(kind==="textarea"){
    const correction=controlId==="EDIT-01-FLD-API-INSTRUCTION";
    const value=correction?state.correction_instruction:"";
    return <label className={styles.fieldControl}><span>{label}</span><textarea {...common} disabled={!enabled} value={value} onChange={event=>correction&&dispatch({type:"CORRECTION_INSTRUCTION",value:event.target.value})} placeholder="—" /></label>;
  }
  if(kind==="select"){
    if(controlId==="EDIT-01-CTL-PLAYBACK-RATE")return <label className={styles.fieldControl}><span>{label}</span><select {...common} disabled={!enabled} value={state.playback_rate} onChange={event=>dispatch({type:"RATE",value:Number(event.target.value) as EditClientState["playback_rate"]})}>{[0.25,0.5,1,1.5,2].map(value=><option key={value} value={value}>{value}x</option>)}</select></label>;
    return <label className={styles.fieldControl}><span>{label}</span><select {...common} disabled defaultValue=""><option value="">—</option></select></label>;
  }
  if(kind==="search"||kind==="timecode"||kind==="number"){
    const mediaSearch=controlId==="EDIT-01-FLD-MEDIA-SEARCH";
    const timecode=controlId==="EDIT-01-FLD-TIMECODE";
    const value=mediaSearch?state.media_search:timecode?(state.playhead===null?"":String(state.playhead)):"";
    return <label className={styles.fieldControl}><span>{label}</span><input {...common} disabled={!enabled} value={value} onChange={event=>mediaSearch?dispatch({type:"MEDIA_SEARCH",value:event.target.value}):timecode?dispatch({type:"SEEK",value:event.target.value}):undefined} placeholder="—" inputMode={kind==="number"?"decimal":undefined}/></label>;
  }
  if(kind==="range"){
    const previewVolume=controlId==="EDIT-01-CTL-VOLUME";
    const value=previewVolume?Math.round(state.preview_volume*100):0;
    return <label className={styles.rangeControl}><span>{label}</span><input {...common} disabled={!enabled} type="range" min="0" max="100" value={value} onChange={event=>previewVolume&&dispatch({type:"PREVIEW_VOLUME",value:Number(event.target.value)/100})}/></label>;
  }
  return <button className={`${styles.button} ${kind==="primary"?styles.primary:""}`} type="button" disabled={!enabled} onClick={click} {...common}>{label}</button>;
}
