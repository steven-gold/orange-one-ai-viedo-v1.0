"use client";

import { useMemo } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { DB_CONTROL_TEXT, dbText, dbUiText } from "@/i18n/dbCatalog";
import { DbRuntimeControl, DbRuntimeProvider, useDbRuntimeState } from "./DbControlRuntime";
import styles from "./DbVisual.module.css";

type Kind="readonly"|"button"|"primary"|"search"|"select"|"list"|"table"|"toggle"|"graph"|"reference"|"trace";
type Spec={id:string;kind:Kind};
const s=(id:string,kind:Kind):Spec=>({id,kind});

const CONTEXT=[s("DB-01-FLD-ENV","readonly"),s("DB-01-FLD-SCHEMA-HEAD","readonly"),s("DB-01-FLD-MIGRATION-HEAD","readonly"),s("DB-01-FLD-SCOPE","readonly"),s("DB-01-FLD-HEALTH","readonly"),s("DB-01-BTN-REFRESH","button")];
const EXPLORER=[s("DB-01-INP-SEARCH","search"),s("DB-01-SEL-DOMAIN","select"),s("DB-01-SEL-ENTITY-TYPE","select"),s("DB-01-LIST-ENTITIES","list")];
const SCHEMA=[s("DB-01-FLD-ENTITY","readonly"),s("DB-01-FLD-TABLE","readonly"),s("DB-01-FLD-OWNER","readonly"),s("DB-01-FLD-CLASSIFICATION","readonly"),s("DB-01-FLD-PK","readonly"),s("DB-01-FLD-VERSION-RULE","readonly"),s("DB-01-TBL-COLUMNS","table"),s("DB-01-TBL-CONSTRAINTS","table"),s("DB-01-BTN-SCHEMA-REFRESH","button")];
const RELATIONS=[s("DB-01-TOGGLE-RELATION-VIEW","toggle"),s("DB-01-GRAPH-RELATIONS","graph"),s("DB-01-LIST-RELATIONS","list")];
const TRACE=[s("DB-01-SEL-TRACE-TYPE","select"),s("DB-01-INP-TRACE-ID","reference"),s("DB-01-BTN-TRACE","primary"),s("DB-01-VIEW-TRACE-PATH","trace")];
const INTEGRITY=[s("DB-01-FLD-REF-INTEGRITY","readonly"),s("DB-01-FLD-ORPHAN","readonly"),s("DB-01-FLD-IMMUTABLE","readonly"),s("DB-01-FLD-TRACE-COMPLETE","readonly"),s("DB-01-FLD-MIGRATION-INTEGRITY","readonly"),s("DB-01-BTN-INTEGRITY-REFRESH","button")];
const MIGRATION=[s("DB-01-INP-MIGRATION-SEARCH","search"),s("DB-01-TBL-MIGRATIONS","table"),s("DB-01-BTN-MIGRATION-REFRESH","button")];
const FINDINGS=[s("DB-01-SEL-FINDING-TYPE","select"),s("DB-01-LIST-FINDINGS","list"),s("DB-01-FLD-FINDING-REASON","readonly"),s("DB-01-FLD-FINDING-AFFECTED","readonly"),s("DB-01-FLD-FINDING-EVIDENCE","readonly"),s("DB-01-FLD-FINDING-OWNER","readonly")];
const AUDIT=[s("DB-01-INP-AUDIT-ID","reference"),s("DB-01-BTN-AUDIT","button"),s("DB-01-VIEW-AUDIT","trace")];
const STATUS=[s("DB-01-FLD-PAGE-STATE","readonly"),s("DB-01-FLD-SOURCE-SYNC","readonly"),s("DB-01-FLD-DISABLED","readonly"),s("DB-01-FLD-CHANGE-OWNER","readonly"),s("DB-01-BTN-SYSTEM-LIFECYCLE","button")];
const ALL=[...CONTEXT,...EXPLORER,...SCHEMA,...RELATIONS,...TRACE,...INTEGRITY,...MIGRATION,...FINDINGS,...AUDIT,...STATUS];

function Control({spec}:{spec:Spec}){return <DbRuntimeControl id={spec.id} kind={spec.kind}/>;}
function Title({text,meta}:{text:string;meta?:string}){return <div className={styles.titleRow}><h2>{text}</h2>{meta?<span>{meta}</span>:null}</div>}

function DbVisualBody(){
  const {locale}=useI18n();
  const {projection,runtimeError}=useDbRuntimeState();
  const registryValid=useMemo(()=>{const ids=new Set(ALL.map(x=>x.id));return ids.size===49&&Object.keys(DB_CONTROL_TEXT).length===49&&[...ids].every(id=>id in DB_CONTROL_TEXT)},[]);
  return <div className={styles.page} data-page-uid="admin:DB-01" data-vis-step="VIS-07" data-page-state={runtimeError?"ERROR":projection?.page_state??"LOADING"} data-runtime-reason={runtimeError??undefined} data-authority-controls="49" data-registry-valid={registryValid?"true":"false"}>
    <section className={styles.contextBar} data-section-id="DB-01-SEC-01" data-visual-uid="DB-01-VIS-CONTEXT" data-component-uid="DB-01-CMP-CONTEXT"><div className={styles.contextGrid}>{CONTEXT.slice(0,5).map(x=><Control key={x.id} spec={x}/>)}</div><Control spec={CONTEXT[5]}/></section>
    <div className={styles.primaryGrid}>
      <aside className={`${styles.panel} ${styles.explorerPanel}`} data-section-id="DB-01-SEC-02" data-visual-uid="DB-01-VIS-LEFT" data-component-uid="DB-01-CMP-EXPLORER"><Title text={dbUiText(locale,"explorer")} meta="20% / min 280px"/><div className={styles.stack}>{EXPLORER.slice(0,3).map(x=><Control key={x.id} spec={x}/>)}</div><Control spec={EXPLORER[3]}/><div className={styles.notice}>{dbUiText(locale,"readOnly")}</div></aside>
      <main className={styles.centerStack}>
        <section className={styles.panel} data-section-id="DB-01-SEC-03" data-visual-uid="DB-01-VIS-SCHEMA"><Title text={dbUiText(locale,"schema")} meta="60% / highest priority"/><div data-component-uid="DB-01-CMP-SCHEMA" className={styles.schemaMeta}>{SCHEMA.slice(0,6).map(x=><Control key={x.id} spec={x}/>)}</div><div data-component-uid="DB-01-CMP-COLUMNS" className={styles.dualGrid}>{SCHEMA.slice(6,8).map(x=><Control key={x.id} spec={x}/>)}</div><div className={styles.actionRow}><Control spec={SCHEMA[8]}/></div></section>
        <section className={styles.panel} data-section-id="DB-01-SEC-04" data-visual-uid="DB-01-VIS-RELATION" data-component-uid="DB-01-CMP-RELATIONS"><Title text={dbUiText(locale,"relations")}/><Control spec={RELATIONS[0]}/><div className={styles.relationGrid}><Control spec={RELATIONS[1]}/><div className={styles.registryOnly}><Control spec={RELATIONS[2]}/></div></div></section>
      </main>
      <aside className={`${styles.panel} ${styles.integrityPanel}`} data-section-id="DB-01-SEC-06" data-visual-uid="DB-01-VIS-RIGHT" data-component-uid="DB-01-CMP-INTEGRITY"><Title text={dbUiText(locale,"integrity")} meta="20% / min 300px"/><div className={styles.stack}>{INTEGRITY.map(x=><Control key={x.id} spec={x}/>)}</div></aside>
    </div>
    <section className={styles.lowerPanel} data-section-id="DB-01-SEC-05" data-visual-uid="DB-01-VIS-TRACE"><Title text={dbUiText(locale,"trace")}/><div className={styles.traceGrid}><div data-component-uid="DB-01-CMP-TRACE-INPUT" className={styles.traceInput}>{TRACE.slice(0,3).map(x=><Control key={x.id} spec={x}/>)}</div><div data-component-uid="DB-01-CMP-TRACE-PATH"><Control spec={TRACE[3]}/></div></div></section>
    <section className={styles.lowerPanel} data-section-id="DB-01-SEC-07" data-visual-uid="DB-01-VIS-MIGRATION" data-component-uid="DB-01-CMP-MIGRATION"><Title text={dbUiText(locale,"migration")}/><div className={styles.toolRow}><Control spec={MIGRATION[0]}/><Control spec={MIGRATION[2]}/></div><Control spec={MIGRATION[1]}/></section>
    <section className={styles.lowerPanel} data-section-id="DB-01-SEC-08" data-visual-uid="DB-01-VIS-FINDING" data-component-uid="DB-01-CMP-FINDINGS"><Title text={dbUiText(locale,"findings")}/><div className={styles.findingGrid}><div className={styles.stack}><Control spec={FINDINGS[0]}/><Control spec={FINDINGS[1]}/></div><div className={styles.detailGrid}>{FINDINGS.slice(2).map(x=><Control key={x.id} spec={x}/>)}</div></div></section>
    <section className={styles.lowerPanel} data-section-id="DB-01-SEC-09" data-visual-uid="DB-01-VIS-AUDIT" data-component-uid="DB-01-CMP-AUDIT"><Title text={dbUiText(locale,"audit")}/><div className={styles.toolRow}><Control spec={AUDIT[0]}/><Control spec={AUDIT[1]}/></div><Control spec={AUDIT[2]}/></section>
    <section className={styles.lowerPanel} data-section-id="DB-01-SEC-10" data-visual-uid="DB-01-VIS-STATUS" data-component-uid="DB-01-CMP-STATUS"><Title text={dbUiText(locale,"status")}/><div className={styles.statusGrid}>{STATUS.map(x=><Control key={x.id} spec={x}/>)}</div></section>
  </div>;
}
export function DbVisual(){return <DbRuntimeProvider><DbVisualBody/></DbRuntimeProvider>;}
