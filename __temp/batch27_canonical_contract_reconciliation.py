from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import json,re,collections,hashlib,subprocess

MARK="ACPOS-20260922-BATCH-27-CANONICAL-CONTRACT-RECONCILIATION-V1"
BASE_HEAD="1a2df5ab734707cb7a03f96a883ee4c25c5425d3"
S08="08_ACPOS_Strategy_Intelligence_MultiAI_Decision_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx"
S09="09_ACPOS_AI_System_Engineer_Self_Inspection_Evolution_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx"
IAM="ACPOS_IAM-01_帳戶與權限_Mother_Basic_Design_OPTIMIZED.docx"
STR="ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx"
LOGIC="ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx"
EXPECTED_SHA={
S08:"cd12a154a70d9338d46a96568710bf1e8a554a14",
S09:"5753584e25067569e3e6978e41241774e3de543d",
IAM:"b93e6de3d11794e479775d56806c7c818f8196da",
STR:"a7c94a517b4f9a5132472ce1f4d68e60383650d7",
LOGIC:"1072638fca6abdc9002b0f218d1168bc52026281",
}
PAGES={
"AIAPI-01":"ACPOS_AIAPI-01_AI_API管理_Mother_Basic_Design_OPTIMIZED.docx",
"ASSET-01":"ACPOS_ASSET-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"CORE-01":"ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"DB-01":"ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"DEV-01":"ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx",
"EDIT-01":"ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"ERP-01":"ACPOS_ERP-01_ERP與財務_Mother_Basic_Design_OPTIMIZED.docx",
"IAM-01":IAM,
"INFO-01":"ACPOS_INFO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"KB-01":"ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx",
"QA-01":"ACPOS_QA-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"SG-02":"ACPOS_SG-02_QA審查項目名單_Mother_Basic_Design_OPTIMIZED.docx",
"SOC-01":"ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx",
"STR-01":STR,
"SYS-01":"ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx",
"VIDEO-01":"ACPOS_VIDEO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"WB-01":"ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx",
"ADMIN-STR-01":"ACPOS_admin_STR-01_戰略中心後台_Mother_Basic_Design_OPTIMIZED.docx",
}
FIELDS=["control","type","label","action","gate","permission","payload_schema","operation","method_path","runtime_owner","persistence_owner","runtime_status"]

TARGETS={
("IAM-01-BTN-AUDIT","runtime_status"):"READ_EXACT",
("IAM-01-BTN-AUDIT","method_path"):"GET /v1/ui-projections/{pageUid}",
("STR-01-TBL-COMPARE","runtime_status"):"READ_EXACT",
("STR-01-TBL-COMPARE","method_path"):"GET /v1/candidates/compare",
("STR-01-TBL-COMPARE","payload_schema"):"No-form read contract",
("STR-01-BTN-COMPARE","runtime_status"):"READ_EXACT",
("STR-01-BTN-COMPARE","method_path"):"GET /v1/candidates/compare",
("STR-01-BTN-COMPARE","payload_schema"):"No-form read contract",
("STR-01-BTN-ADOPT","method_path"):"POST /v1/state-commands/strategycandidate/adoptascontextcandidate",
("STR-01-BTN-ADOPT","payload_schema"):"AdoptAsContextCandidateRequest",
}

def norm(x):return re.sub(r"\s+"," ",(x or "").replace("\n"," | ").strip())
def missing(v):return v in {"","—","-","SOURCE_NOT_DEFINED"}
def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None
def exact_index(headers,name):
    n=name.lower()
    for i,h in enumerate(headers):
        if norm(h).lower()==n:return i
    return None
def parse_controls(path):
    d=Document(path);out=[]
    for ti,t in enumerate(d.tables):
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells];ci=hfind(h,"control uid")
        if ci is None:continue
        idx={"control":ci,"type":hfind(h,"type"),"label":hfind(h,"label","顯示名稱"),
          "action":hfind(h,"action uid"),"gate":hfind(h,"gate uid","gate"),
          "permission":hfind(h,"permission","auth resource"),
          "payload_schema":hfind(h,"payload / schema","payload","schema"),
          "operation":hfind(h,"operation"),"method_path":hfind(h,"method / path","method","path"),
          "runtime_owner":hfind(h,"runtime owner"),"persistence_owner":hfind(h,"persistence owner"),
          "runtime_status":hfind(h,"runtime status")}
        for ri,row in enumerate(t.rows[1:],2):
            vals=[norm(c.text) for c in row.cells];uid=vals[ci] if ci<len(vals) else ""
            if not uid or uid in {"—","-"}:continue
            rec={k:(vals[i] if i is not None and i<len(vals) else "") for k,i in idx.items()}
            rec.update({"file":path,"table":ti+1,"row":ri});out.append(rec)
    return out
def compose(rows):
    g=collections.defaultdict(list)
    for r in rows:g[r["control"]].append(r)
    out={}
    for uid,rs in g.items():
        base=max(rs,key=lambda r:sum(not missing(r.get(f,"")) for f in FIELDS[1:])).copy()
        fv={}
        for f in FIELDS[1:]:
            vals=sorted(set(r.get(f,"") for r in rs if not missing(r.get(f,""))))
            fv[f]=vals
            if missing(base.get(f,"")) and len(vals)==1:base[f]=vals[0]
        base["_field_values"]=fv;base["_rows"]=rs;out[uid]=base
    return out
def blob(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
for f,s in EXPECTED_SHA.items():
    got=blob(f);assert got==s,(f,got,s)
assert len(list(Path(".").glob("*.docx")))==31
assert subprocess.check_output(["git","diff","--name-only",BASE_HEAD,"HEAD","--","*.docx"],text=True).strip()==""

pre_s08=parse_controls(S08);pre_s09=parse_controls(S09)
def unique_op_value(rows,op,field):
    vals=sorted(set(r.get(field,"") for r in rows if r.get("operation")==op and not missing(r.get(field,""))))
    return vals
assert unique_op_value(pre_s09,"getUiProjection","method_path")==["GET /v1/ui-projections/{pageUid}"]
assert unique_op_value(pre_s08,"compareCandidates","method_path")==["GET /v1/candidates/compare"]
assert unique_op_value(pre_s08,"compareCandidates","payload_schema")==["No-form read contract"]
assert unique_op_value(pre_s08,"adoptAsContextCandidate","method_path")==["POST /v1/state-commands/strategycandidate/adoptascontextcandidate"]
assert unique_op_value(pre_s08,"adoptAsContextCandidate","payload_schema")==["AdoptAsContextCandidateRequest"]

pre_iam=compose(parse_controls(IAM));pre_str=compose(parse_controls(STR));pre_o8=compose(pre_s08);pre_o9=compose(pre_s09)
assert pre_iam["IAM-01-BTN-AUDIT"]["runtime_status"]=="EFFECTFUL_EXACT"
assert pre_o9["IAM-01-BTN-AUDIT"]["runtime_status"]=="EFFECTFUL_EXACT"
for u in ["STR-01-TBL-COMPARE","STR-01-BTN-COMPARE","STR-01-BTN-ADOPT"]:
    assert pre_str[u]["runtime_status"]=="EFFECTFUL_EXACT",(u,pre_str[u]["runtime_status"])
    assert pre_o8[u]["runtime_status"]=="EFFECTFUL_EXACT",(u,pre_o8[u]["runtime_status"])

def patch(path,bindings):
    d=Document(path);hits=collections.Counter()
    for t in d.tables:
        if not t.rows:continue
        h=[norm(c.text) for c in t.rows[0].cells];ci=exact_index(h,"Control UID")
        if ci is None:continue
        idx={
          "runtime_status":hfind(h,"runtime status"),
          "method_path":hfind(h,"method / path","method","path"),
          "payload_schema":hfind(h,"payload / schema","payload","schema"),
        }
        for row in t.rows[1:]:
            vals=[norm(c.text) for c in row.cells]
            if ci>=len(vals):continue
            uid=vals[ci]
            for field,value in bindings.get(uid,{}).items():
                fi=idx[field]
                if fi is None or fi>=len(row.cells):continue
                old=norm(row.cells[fi].text)
                if field=="runtime_status":
                    if old==value:
                        hits[(uid,field)]+=1;continue
                    assert old=="EFFECTFUL_EXACT",(path,uid,field,old)
                else:
                    if old==value:
                        hits[(uid,field)]+=1;continue
                    assert missing(old),(path,uid,field,old,value)
                row.cells[fi].text=value;hits[(uid,field)]+=1
    expected={(u,f) for u,fs in bindings.items() for f in fs}
    assert set(hits)==expected,(path,"PATCH_MISMATCH",sorted(expected-set(hits)),dict(hits))
    d.save(path);Document(path)
    return {f"{u}:{f}":n for (u,f),n in hits.items()}

iam_bind={
"IAM-01-BTN-AUDIT":{
"runtime_status":"READ_EXACT",
"method_path":"GET /v1/ui-projections/{pageUid}",
}}
str_bind={
"STR-01-TBL-COMPARE":{"runtime_status":"READ_EXACT","method_path":"GET /v1/candidates/compare","payload_schema":"No-form read contract"},
"STR-01-BTN-COMPARE":{"runtime_status":"READ_EXACT","method_path":"GET /v1/candidates/compare","payload_schema":"No-form read contract"},
"STR-01-BTN-ADOPT":{"method_path":"POST /v1/state-commands/strategycandidate/adoptascontextcandidate","payload_schema":"AdoptAsContextCandidateRequest"},
}
patches={
"IAM_PAGE":patch(IAM,iam_bind),
"S09_OWNER":patch(S09,iam_bind),
"STR_PAGE":patch(STR,str_bind),
"S08_OWNER":patch(S08,str_bind),
}

def add_landscape(doc):
    sec=doc.add_section(WD_SECTION.NEW_PAGE);sec.orientation=WD_ORIENT.LANDSCAPE
    sec.page_width,sec.page_height=sec.page_height,sec.page_width
    sec.top_margin=Inches(.33);sec.bottom_margin=Inches(.33);sec.left_margin=Inches(.28);sec.right_margin=Inches(.28)
def repeat_header(row):
    trPr=row._tr.get_or_add_trPr();e=OxmlElement("w:tblHeader");e.set(qn("w:val"),"true");trPr.append(e)
def shade(cell,fill="EDE9FE"):
    tcPr=cell._tc.get_or_add_tcPr();e=OxmlElement("w:shd");e.set(qn("w:fill"),fill);tcPr.append(e)
def add_table(doc,headers,rows,fs=4.4):
    t=doc.add_table(rows=1,cols=len(headers));t.style="Table Grid";repeat_header(t.rows[0])
    for i,h in enumerate(headers):t.rows[0].cells[i].text=str(h);shade(t.rows[0].cells[i])
    for rr in rows:
        cells=t.add_row().cells
        for i,v in enumerate(rr):cells[i].text=str(v)
    for row in t.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0)
                for run in p.runs:run.font.size=Pt(fs)
    return t

# Canonical owner amendments.
d=Document(S09);add_landscape(d);d.add_heading("Batch 27 · IAM Audit Read Contract Reconciliation",level=1)
p=d.add_paragraph();p.add_run(f"[{MARK}::SYSTEM09] ").bold=True
p.add_run("IAM-01-BTN-AUDIT uses getUiProjection, page.view and the existing GET /v1/ui-projections/{pageUid} contract. The prior EFFECTFUL_EXACT status contradicts the operation's read-only contract and is superseded by READ_EXACT. No mutation or persistence owner is applicable.")
add_table(d,["Control UID","Operation","Runtime Status","Method / Path","Persistence Semantics"],[["IAM-01-BTN-AUDIT","getUiProjection","READ_EXACT","GET /v1/ui-projections/{pageUid}","N/A - read-only projection"]],4.2)
d.save(S09);Document(S09)

d=Document(S08);add_landscape(d);d.add_heading("Batch 27 · Strategy Compare / Adopt Contract Reconciliation",level=1)
p=d.add_paragraph();p.add_run(f"[{MARK}::SYSTEM08] ").bold=True
p.add_run("compareCandidates is reconciled as a read-only comparison contract because the existing owner contract is GET /v1/candidates/compare, uses a no-form read contract, and explicitly expects no mutation. adoptAsContextCandidate remains EFFECTFUL_EXACT and reuses the existing POST + AdoptAsContextCandidateRequest contract. Runtime execution is not asserted by this Word closure.")
add_table(d,["Control UID","Operation","Runtime Status","Method / Path","Payload / Schema","Persistence Semantics"],[
["STR-01-TBL-COMPARE","compareCandidates","READ_EXACT","GET /v1/candidates/compare","No-form read contract","N/A - no mutation"],
["STR-01-BTN-COMPARE","compareCandidates","READ_EXACT","GET /v1/candidates/compare","No-form read contract","N/A - no mutation"],
["STR-01-BTN-ADOPT","adoptAsContextCandidate","EFFECTFUL_EXACT","POST /v1/state-commands/strategycandidate/adoptascontextcandidate","AdoptAsContextCandidateRequest","Still requires explicit persistence-owner remediation if no exact owner is defined"],
],3.9)
d.save(S08);Document(S08)

# Page ledgers.
for page,path,rows in [
("IAM-01",IAM,[["IAM-01-BTN-AUDIT","getUiProjection","READ_EXACT","GET /v1/ui-projections/{pageUid}","Read-only projection; no persistence owner required"]]),
("STR-01",STR,[
["STR-01-TBL-COMPARE","compareCandidates","READ_EXACT","GET /v1/candidates/compare","No-form read; persistence owner non-applicable"],
["STR-01-BTN-COMPARE","compareCandidates","READ_EXACT","GET /v1/candidates/compare","No-form read; persistence owner non-applicable"],
["STR-01-BTN-ADOPT","adoptAsContextCandidate","EFFECTFUL_EXACT","POST /v1/state-commands/strategycandidate/adoptascontextcandidate","Payload=AdoptAsContextCandidateRequest"],
])]:
    d=Document(path);add_landscape(d);d.add_heading("Batch 27 · Canonical Contract Reconciliation Ledger",level=1)
    p=d.add_paragraph();p.add_run(f"[{MARK}::PAGE::{page}] ").bold=True
    p.add_run("Bindings below are synchronized from the matching Canonical Owner amendment. Read-only controls do not acquire a Persistence Owner. Runtime execution remains outside this Word evidence.")
    add_table(d,["Control UID","Operation","Runtime Status","Method / Path","Result"],rows,4.0)
    d.save(path);Document(path)

post_iam=compose(parse_controls(IAM));post_str=compose(parse_controls(STR));post_o8=compose(parse_controls(S08));post_o9=compose(parse_controls(S09))
for m in [post_iam,post_o9]:
    r=m["IAM-01-BTN-AUDIT"];assert r["runtime_status"]=="READ_EXACT";assert r["method_path"]=="GET /v1/ui-projections/{pageUid}"
for m in [post_str,post_o8]:
    for u in ["STR-01-TBL-COMPARE","STR-01-BTN-COMPARE"]:
        r=m[u];assert r["runtime_status"]=="READ_EXACT";assert r["method_path"]=="GET /v1/candidates/compare";assert r["payload_schema"]=="No-form read contract"
    r=m["STR-01-BTN-ADOPT"];assert r["runtime_status"]=="EFFECTFUL_EXACT";assert r["method_path"]=="POST /v1/state-commands/strategycandidate/adoptascontextcandidate";assert r["payload_schema"]=="AdoptAsContextCandidateRequest"

# Recompute the unresolved contract-cell denominator.
page_maps={p:compose(parse_controls(fn)) for p,fn in PAGES.items()}
remaining=[]
for page,m in page_maps.items():
    for uid,r in m.items():
        st=r.get("runtime_status","");op=r.get("operation","")
        if st in {"EFFECTFUL_EXACT","READ_EXACT"} and not missing(op) and missing(r.get("method_path","")):
            remaining.append(("method_path",page,uid))
        if st=="EFFECTFUL_EXACT" and not missing(op) and missing(r.get("payload_schema","")):
            remaining.append(("payload_schema",page,uid))
        if st=="EFFECTFUL_EXACT" and not missing(op) and missing(r.get("persistence_owner","")):
            remaining.append(("persistence_owner",page,uid))
rc=collections.Counter(f for f,_,_ in remaining)
assert len(remaining)==324,len(remaining)
assert rc=={"method_path":71,"payload_schema":132,"persistence_owner":121},rc

logic=Document(LOGIC);add_landscape(logic);logic.add_heading("Batch 27 · Runtime/Contract Semantic Reconciliation",level=1)
p=logic.add_paragraph();p.add_run(f"[{MARK}] ").bold=True
p.add_run("Batch 26 proved all four exact UID owner rows matched the page Runtime Status, but their same-operation contract evidence exposed two semantic inconsistencies: getUiProjection and compareCandidates are read-only contracts while the exact UID rows were marked EFFECTFUL_EXACT. This batch corrects those owner/page statuses to READ_EXACT, binds their existing GET contracts, and materializes the existing adoptAsContextCandidate POST/payload contract without claiming runtime execution.")
add_table(logic,["Resolution","Cells retired from denominator","Result"],[
["IAM audit: EFFECTFUL_EXACT -> READ_EXACT + GET route",3,"Method/Path closed; Payload/Schema + Persistence Owner become non-applicable under READ_EXACT"],
["STR compare x2: EFFECTFUL_EXACT -> READ_EXACT + GET route + no-form read payload",6,"Method/Payload bound; persistence non-applicable"],
["STR adopt: retain EFFECTFUL_EXACT + POST route + request schema",2,"Method/Payload bound"],
["Total previously isolated mismatch cells resolved",9,"All nine Batch-26 mismatch cells resolved"],\n["Additional applicability cells retired",2,"IAM read reclassification retires previously required Payload/Schema + Persistence Owner"],\n["Total contract cells retired",11,"335 -> 324"],
],4.2)
machine={
"marker":MARK,"base_head":BASE_HEAD,"pre_contract_cells":335,"runtime_authority_mismatch_resolved":9,
"runtime_status_corrections":3,"read_contracts_reconciled":3,"effectful_adopt_contract_bound":1,
"post_contract_cells":324,"remaining_method_path":71,"remaining_payload_schema":132,
"remaining_persistence_owner":121,"additional_read_applicability_retired":2,"contract_cells_retired":11,"runtime_execution_claimed":False,
}
logic.add_paragraph("BATCH27_MACHINE_JSON="+json.dumps(machine,ensure_ascii=False,sort_keys=True,separators=(",",":")))
logic.save(LOGIC);Document(LOGIC)

changed=[S08,S09,IAM,STR,LOGIC]
report={"machine":machine,"patches":patches,"changed_docs":changed,"output_blob_sha":{f:blob(f) for f in changed}}
Path("__batch27_remediation_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("BATCH27="+json.dumps(machine,ensure_ascii=False,sort_keys=True))
