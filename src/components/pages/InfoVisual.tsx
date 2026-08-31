"use client";
import { useMemo, useReducer, type Dispatch, type ReactNode } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { INFO_CONTROLS, INFO_CONTROL_COUNT, infoText, infoPageText, type InfoControlSpec } from "@/i18n/infoCatalog";
import { INITIAL_INFO_CLIENT_STATE, reduceInfoClientState, type InfoClientAction, type InfoClientState } from "@/domain/info/infoClientState";
import styles from "./InfoVisual.module.css";

const SECTION_TITLES: Record<string,string> = {
  "INFO-01-SEC-01":"Context / Projection Control","INFO-01-SEC-02":"Scope / Source Health","INFO-01-SEC-03":"Alert Feed",
  "INFO-01-SEC-04":"Fact Pack Explorer","INFO-01-SEC-05":"Fact / Inference Detail","INFO-01-SEC-06":"Evidence / Source Metadata",
  "INFO-01-SEC-07":"Freshness / Completeness / Confidence","INFO-01-SEC-08":"Research Queue / Runs","INFO-01-SEC-09":"Context Candidate Review",
  "INFO-01-SEC-10":"Citation","INFO-01-SEC-11":"Action Dock","INFO-01-SEC-12":"Audit / Status"
};
const bySection=(id:string)=>INFO_CONTROLS.filter(x=>x.section===id);
type ControlProps={item:InfoControlSpec;state:InfoClientState;dispatch:Dispatch<InfoClientAction>};
function Control({item,state,dispatch}:ControlProps){
  const {locale}=useI18n(); const label=infoText(locale,item);
  const isFact=item.id==="INFO-01-TAB-FACT",isInference=item.id==="INFO-01-TAB-INFERENCE",isAudit=item.id==="INFO-01-BTN-AUDIT";
  const local=isFact||isInference||isAudit;
  const common={"data-control-id":item.id,"data-component-uid":item.component,"data-visual-uid":item.visual,"data-disabled-reason":local?undefined:"Gate not satisfied"};
  if(item.type==="READONLY") return <div className={styles.readonly} {...common}><span>{label}</span><strong>{item.id==="INFO-01-FLD-SOURCE-REF"?(state.source_ref??"—"):item.id==="INFO-01-FLD-ALERT-REF"?(state.alert_ref??"—"):item.id==="INFO-01-FLD-FACTPACK-REF"?(state.fact_pack_ref??"—"):item.id==="INFO-01-FLD-EVIDENCE-REF"?(state.evidence_ref??"—"):item.id==="INFO-01-FLD-RESEARCH-REF"?(state.research_ref??"—"):item.id==="INFO-01-FLD-CANDIDATE-ID"?(state.candidate_ref??"—"):"—"}</strong></div>;
  if(item.type==="LIST") return <div className={styles.listControl} {...common}><span>{label}</span><div className={styles.listView}>—</div></div>;
  if(item.type==="FILTER") return <label className={styles.fieldControl} {...common}><span>{label}</span><select disabled defaultValue=""><option value="">—</option></select></label>;
  if(item.type==="TAB") return <button type="button" className={styles.tab} {...common} aria-pressed={isFact?state.fact_view==="FACT":state.fact_view==="INFERENCE"} onClick={()=>dispatch({type:"FACT_VIEW",value:isFact?"FACT":"INFERENCE"})}>{label}</button>;
  return <button type="button" disabled={!isAudit} onClick={isAudit?()=>dispatch({type:"AUDIT",value:!state.audit_open}):undefined} className={`${styles.button} ${item.type==="PRIMARY_BUTTON"?styles.primary:""}`} {...common}>{label}</button>;
}
function Panel({id,children,className=""}:{id:string;children?:ReactNode;className?:string}){const items=bySection(id);return <section className={`${styles.panel} ${className}`} data-section-id={id} data-visual-uid={items[0]?.visual}><div className={styles.titleRow}><h2>{SECTION_TITLES[id]}</h2></div>{children}</section>;}
export function InfoVisual(){
  const {locale}=useI18n();const[state,dispatch]=useReducer(reduceInfoClientState,INITIAL_INFO_CLIENT_STATE);
  const valid=useMemo(()=>INFO_CONTROL_COUNT===66&&new Set(INFO_CONTROLS.map(x=>x.id)).size===66&&new Set(INFO_CONTROLS.map(x=>x.section)).size===12&&new Set(INFO_CONTROLS.map(x=>x.component)).size===20,[]);
  const sec1=bySection("INFO-01-SEC-01"),sec5=bySection("INFO-01-SEC-05"),sec9=bySection("INFO-01-SEC-09"),sec10=bySection("INFO-01-SEC-10"),sec11=bySection("INFO-01-SEC-11"),sec12=bySection("INFO-01-SEC-12");
  const fact=sec5.filter(x=>x.component==="INFO-01-CMP-FACT"),inference=sec5.filter(x=>x.component==="INFO-01-CMP-INFERENCE");
  const C=({item}:{item:InfoControlSpec})=><Control item={item} state={state} dispatch={dispatch}/>;
  return <div className={styles.page} data-page-uid="workspace:INFO-01" data-vis-step="VIS-09" data-page-state="EMPTY" data-authority-sections="12" data-authority-visuals="12" data-authority-components="20" data-authority-controls="66" data-registry-valid={valid?"true":"false"} data-fact-view={state.fact_view} data-audit-open={state.audit_open?"true":"false"}>
    <section className={styles.contextBar} data-section-id="INFO-01-SEC-01" data-visual-uid="INFO-01-VIS-CONTEXT"><div className={styles.contextGrid}>{sec1.slice(0,4).map(x=><C key={x.id} item={x}/>)}</div><div className={styles.contextActions}>{sec1.slice(4).map(x=><C key={x.id} item={x}/>)}</div></section>
    <div className={styles.primaryGrid}><aside className={styles.rail}><Panel id="INFO-01-SEC-02"><div className={styles.stack}>{bySection("INFO-01-SEC-02").map(x=><C key={x.id} item={x}/>)}</div></Panel><Panel id="INFO-01-SEC-03"><div className={styles.stack}>{bySection("INFO-01-SEC-03").map(x=><C key={x.id} item={x}/>)}</div></Panel></aside><main className={styles.center}><Panel id="INFO-01-SEC-04"><div className={styles.stack}>{bySection("INFO-01-SEC-04").map(x=><C key={x.id} item={x}/>)}</div></Panel><Panel id="INFO-01-SEC-05"><div className={styles.factTabs}>{sec5.filter(x=>x.type==="TAB").map(x=><C key={x.id} item={x}/>)}</div><div className={styles.factSplit}><div className={styles.factBox}><div className={styles.classLabel}>{infoPageText(locale,"fact")}</div>{state.fact_view==="FACT"?fact.filter(x=>x.type!=="TAB").map(x=><C key={x.id} item={x}/>):null}</div><div className={styles.inferenceBox}><div className={styles.classLabel}>{infoPageText(locale,"inference")}</div>{state.fact_view==="INFERENCE"?inference.filter(x=>x.type!=="TAB").map(x=><C key={x.id} item={x}/>):null}</div></div></Panel><Panel id="INFO-01-SEC-06"><div className={styles.stack}>{bySection("INFO-01-SEC-06").map(x=><C key={x.id} item={x}/>)}</div></Panel></main><aside className={styles.rail}><Panel id="INFO-01-SEC-07"><div className={styles.stack}>{bySection("INFO-01-SEC-07").map(x=><C key={x.id} item={x}/>)}</div></Panel><Panel id="INFO-01-SEC-08"><div className={styles.stack}>{bySection("INFO-01-SEC-08").map(x=><C key={x.id} item={x}/>)}</div><div className={styles.notice}>{infoPageText(locale,"readOnly")}</div></Panel></aside></div>
    <Panel id="INFO-01-SEC-09" className={styles.lower}><div className={styles.candidateGrid}>{sec9.map(x=><C key={x.id} item={x}/>)}</div></Panel>
    <Panel id="INFO-01-SEC-10" className={styles.lower}><div className={styles.citationGrid}>{sec10.map(x=><C key={x.id} item={x}/>)}</div></Panel>
    <Panel id="INFO-01-SEC-11" className={styles.lower}><div className={styles.actionDock}>{sec11.map(x=><C key={x.id} item={x}/>)}</div></Panel>
    <Panel id="INFO-01-SEC-12" className={styles.lower}><div className={styles.statusGrid}>{sec12.map(x=><C key={x.id} item={x}/>)}</div><div className={styles.notice}>{infoPageText(locale,"firewall")}</div></Panel>
  </div>;
}
