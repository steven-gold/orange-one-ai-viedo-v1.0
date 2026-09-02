"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/LocaleProvider";
import { qaCriteriaText, qaSectionLabel } from "@/i18n/qaCriteriaCatalog";
import { approveQaCriteriaResource, configureQaCriteriaResource, readQaCriteriaProjection, type QaCriteriaProjection } from "@/domain/qaCriteria/qaCriteriaRuntimePort";
import styles from "./QaCriteriaVisual.module.css";

type SectionKey = "criteria_table"|"dimension_library"|"thresholds"|"department_mapping"|"required_checks"|"gate_policy"|"approval"|"impact";
type DrawerKey = SectionKey|"governance"|"configure"|"approve";
const CONFIGURE_ID="CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE";
const APPROVE_ID="CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE";
const SECTION_CONTROLS: ReadonlyArray<{key:SectionKey;sectionId:string;controlId:string}>=[
{key:"criteria_table",sectionId:"SEC-ADMIN-SG-02-CRITERIA-TABLE",controlId:"CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN"},
{key:"dimension_library",sectionId:"SEC-ADMIN-SG-02-DIMENSION-LIBRARY",controlId:"CTRL-ADMIN-SG-02-DIMENSION-LIBRARY-OPEN"},
{key:"thresholds",sectionId:"SEC-ADMIN-SG-02-THRESHOLDS",controlId:"CTRL-ADMIN-SG-02-THRESHOLDS-OPEN"},
{key:"department_mapping",sectionId:"SEC-ADMIN-SG-02-DEPARTMENT-MAPPING",controlId:"CTRL-ADMIN-SG-02-DEPARTMENT-MAPPING-OPEN"},
{key:"required_checks",sectionId:"SEC-ADMIN-SG-02-REQUIRED-CHECKS",controlId:"CTRL-ADMIN-SG-02-REQUIRED-CHECKS-OPEN"},
{key:"gate_policy",sectionId:"SEC-ADMIN-SG-02-GATE-POLICY",controlId:"CTRL-ADMIN-SG-02-GATE-POLICY-OPEN"},
{key:"approval",sectionId:"SEC-ADMIN-SG-02-APPROVAL",controlId:"CTRL-ADMIN-SG-02-APPROVAL-OPEN"},
{key:"impact",sectionId:"SEC-ADMIN-SG-02-IMPACT",controlId:"CTRL-ADMIN-SG-02-IMPACT-OPEN"},
] as const;

export function QaCriteriaVisual(){
 const{locale}=useI18n();
 const[drawer,setDrawer]=useState<DrawerKey|null>(null);
 const[projection,setProjection]=useState<QaCriteriaProjection|null>(null);
 const[runtimeError,setRuntimeError]=useState<string|null>(null);
 const[correlationId,setCorrelationId]=useState<string|null>(null);
 const[resourceType,setResourceType]=useState("");
 const[resourceId,setResourceId]=useState("");
 const[configPatch,setConfigPatch]=useState("");
 const[reason,setReason]=useState("");
 const[rationale,setRationale]=useState("");
 const[expectedVersion,setExpectedVersion]=useState("");
 const[busy,setBusy]=useState(false);
 const syncProjection=async(signal?:AbortSignal)=>{const r=await readQaCriteriaProjection(signal);setCorrelationId(r.correlation_id);if(r.ok){setProjection(r.projection);setRuntimeError(null);return true}setRuntimeError(r.reason_code);return false};
 useEffect(()=>{const c=new AbortController();void readQaCriteriaProjection(c.signal).then(r=>{setCorrelationId(r.correlation_id);if(r.ok){setProjection(r.projection);setRuntimeError(null)}else setRuntimeError(r.reason_code)});return()=>c.abort()},[]);
 const value=(key:string)=>projection?.values[key]??"—";
 const enabled=(id:string)=>projection?.control_enabled[id]===true&&!busy;
 const pageState=runtimeError?"ERROR":projection?.page_state??"LOADING";
 const submitConfigure=async()=>{if(!enabled(CONFIGURE_ID)||!resourceType.trim()||!resourceId.trim()||!reason.trim()||!configPatch.trim())return;let parsed:unknown;try{parsed=JSON.parse(configPatch)}catch{setRuntimeError("SG02_CONFIG_PATCH_JSON_INVALID");return}setBusy(true);const r=await configureQaCriteriaResource({resource_type:resourceType.trim(),resource_id:resourceId.trim(),config_patch_json:parsed,reason:reason.trim()});setCorrelationId(r.correlation_id);if(!r.ok){setRuntimeError(r.reason_code);setBusy(false);return}const projectionSynced=await syncProjection();setBusy(false);if(projectionSynced)setDrawer("governance")};
 const submitApprove=async()=>{if(!enabled(APPROVE_ID)||!resourceType.trim()||!resourceId.trim()||!rationale.trim())return;setBusy(true);const r=await approveQaCriteriaResource({resource_type:resourceType.trim(),resource_id:resourceId.trim(),rationale:rationale.trim(),...(expectedVersion.trim()?{expected_resource_version:expectedVersion.trim()}: {})});setCorrelationId(r.correlation_id);if(!r.ok){setRuntimeError(r.reason_code);setBusy(false);return}const projectionSynced=await syncProjection();setBusy(false);if(projectionSynced)setDrawer("governance")};
 return <div className={styles.page} data-page-uid="admin:SG-02" data-vis-step="VIS-16" data-authority-section-count="9" data-authority-control-count="11" data-page-state={pageState}>
  <section className={styles.contextBar} aria-label="SG-02 Context"><div className={styles.identity}><div className={styles.eyebrow}>ADMIN · SG-02 · QUALITY GOVERNANCE</div><h1>{qaCriteriaText(locale,"pageName")}</h1><p>{qaCriteriaText(locale,"pageRole")}</p></div><div className={styles.state}>QualityGovernance · FINAL_LOCKED · {runtimeError??projection?.page_state??"LOADING"} · correlation {correlationId??"—"}</div></section>
  <div className={styles.layout}>
   <section className={styles.panel} data-section-id="SEC-ADMIN-SG-02-CRITERIA-TABLE" aria-label={qaCriteriaText(locale,"criteriaTable")}>
    <div className={styles.sectionHead}><div><h2>{qaCriteriaText(locale,"criteriaTable")}</h2><p>criteria_versions · dimensions · policies · mappings · approvals</p></div><button type="button" className={styles.openButton} data-control-id="CTRL-ADMIN-SG-02-CRITERIA-TABLE-OPEN" data-operation-id="getUiProjection" onClick={()=>setDrawer("criteria_table")}>{qaSectionLabel(locale,"criteria_table")} ↗</button></div>
    <div className={styles.criteriaTable}><div className={styles.tableHeader} role="row"><span>{qaCriteriaText(locale,"version")}</span><span>{qaCriteriaText(locale,"dimension")}</span><span>{qaCriteriaText(locale,"policy")}</span><span>{qaCriteriaText(locale,"mapping")}</span><span>{qaCriteriaText(locale,"approval")}</span></div><div className={styles.empty}>{projection?`${value("criteria_versions")} · ${value("dimensions")} · ${value("policies")} · ${value("mappings")} · ${value("approvals")}`:qaCriteriaText(locale,"noData")}</div></div>
    <div className={styles.truthNote}>DRAFT → REVIEW → APPROVED → ACTIVE → SUPERSEDED → RETIRED. Active criteria is immutable; any change requires a new approved version, Impact, Approval and affected-task revalidation. No threshold is hardcoded in this visual layer.</div>
   </section>
   <aside className={styles.rail} aria-label={qaCriteriaText(locale,"detailSections")}><h2 className={styles.railTitle}>{qaCriteriaText(locale,"detailSections")}</h2><div className={styles.railList}>{SECTION_CONTROLS.slice(1).map(section=><section key={section.key} data-section-id={section.sectionId}><button type="button" className={styles.railButton} data-control-id={section.controlId} data-operation-id="getUiProjection" onClick={()=>setDrawer(section.key)}><span>{qaSectionLabel(locale,section.key)}</span><span>DRAWER ↗</span></button></section>)}</div></aside>
  </div>
  <section className={styles.dock} data-section-id="SEC-ADMIN-SG-02-ACTION-DOCK" aria-label="SG-02 Action Dock"><div className={styles.dockInfo}><strong>Quality Criteria / Gate Policy</strong><span>{runtimeError??qaCriteriaText(locale,"visualPhase")}</span></div><div className={styles.dockActions}>
   <button type="button" className={styles.dockButton} data-control-id={CONFIGURE_ID} data-operation-id="configureGovernedResource" data-method-path="PATCH /v1/governance/resources/{id}" disabled={!enabled(CONFIGURE_ID)} onClick={()=>setDrawer("configure")}>{qaCriteriaText(locale,"configure")}</button>
   <button type="button" className={`${styles.dockButton} ${styles.primary}`} data-control-id={APPROVE_ID} data-operation-id="approveGovernedResource" data-method-path="POST /v1/governance/resources/{id}/approve" disabled={!enabled(APPROVE_ID)} onClick={()=>setDrawer("approve")}>{qaCriteriaText(locale,"approve")}</button>
   <button type="button" className={styles.dockButton} data-control-id="CTRL-ADMIN-SG-02-ACT-03-ACT-NAV-OPEN" data-operation-id="getUiProjection" onClick={()=>setDrawer("governance")}>{qaCriteriaText(locale,"navOpen")}</button>
  </div></section>
  {drawer&&<><button className={styles.drawerBackdrop} type="button" aria-label="Close detail drawer" onClick={()=>setDrawer(null)}/><aside className={styles.drawer} data-detail-drawer="SG-02" aria-label="SG-02 Detail Drawer"><div className={styles.drawerHead}><div><h3>{drawer==="governance"?qaCriteriaText(locale,"navOpen"):drawer==="configure"?qaCriteriaText(locale,"configure"):drawer==="approve"?qaCriteriaText(locale,"approve"):qaSectionLabel(locale,drawer)}</h3><p>{drawer==="configure"?"ConfigureGovernedResourceRequest":drawer==="approve"?"ApproveGovernedResourceRequest":"Registered SECTION_OPEN / getUiProjection detail surface"}</p></div><button type="button" className={styles.close} aria-label="Close" onClick={()=>setDrawer(null)}>×</button></div><div className={styles.drawerBody}>
   {drawer==="configure"&&<><label className={styles.drawerRow}><span>resource_type *</span><input value={resourceType} onChange={e=>setResourceType(e.target.value)}/></label><label className={styles.drawerRow}><span>resource_id *</span><input value={resourceId} onChange={e=>setResourceId(e.target.value)}/></label><label className={styles.drawerRow}><span>config_patch_json *</span><textarea value={configPatch} onChange={e=>setConfigPatch(e.target.value)} rows={8}/></label><label className={styles.drawerRow}><span>reason *</span><textarea value={reason} onChange={e=>setReason(e.target.value)} rows={3}/></label><button type="button" className={`${styles.dockButton} ${styles.primary}`} disabled={!enabled(CONFIGURE_ID)} onClick={()=>void submitConfigure()}>{qaCriteriaText(locale,"configure")}</button></>}
   {drawer==="approve"&&<><label className={styles.drawerRow}><span>resource_type *</span><input value={resourceType} onChange={e=>setResourceType(e.target.value)}/></label><label className={styles.drawerRow}><span>resource_id *</span><input value={resourceId} onChange={e=>setResourceId(e.target.value)}/></label><label className={styles.drawerRow}><span>rationale *</span><textarea value={rationale} onChange={e=>setRationale(e.target.value)} rows={4}/></label><label className={styles.drawerRow}><span>expected_resource_version</span><input value={expectedVersion} onChange={e=>setExpectedVersion(e.target.value)}/></label><button type="button" className={`${styles.dockButton} ${styles.primary}`} disabled={!enabled(APPROVE_ID)} onClick={()=>void submitApprove()}>{qaCriteriaText(locale,"approve")}</button></>}
   {drawer!=="configure"&&drawer!=="approve"&&<><div className={styles.drawerRow}><span>Authorized read-model projection</span><strong>{value(drawer==="governance"?"criteria_versions":drawer)}</strong></div><div className={styles.drawerRow}><span>Current version / state</span><strong>{projection?.page_state??"—"}</strong></div><div className={styles.drawerRow}><span>Audit / Impact / Approval reference</span><strong>{value("audit_ref")}</strong></div><div className={styles.warning}>{runtimeError??qaCriteriaText(locale,"drawerEmpty")}</div></>}
  </div></aside></>}
 </div>
}
