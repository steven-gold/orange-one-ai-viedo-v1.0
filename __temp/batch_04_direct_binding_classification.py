from pathlib import Path
from docx import Document
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import hashlib,json,re

MARK="ACPOS-20260921-BATCH-04-DIRECT-BINDING-CLASSIFICATION-V1"
TARGET="ACPOS_SYSTEM_LOGIC_GLOBAL_INTEGRATION_Mother_Basic_Design_OPTIMIZED.docx"
TARGET_SHA="18f9de4d5f8f6fd6b8569da72448333080d55fc9"

PAGES={
"AIAPI-01":("ACPOS_AIAPI-01_AI_API管理_Mother_Basic_Design_OPTIMIZED.docx","ef610d7f6f2bcc72890f1ba563c063f737cae60e"),
"ASSET-01":("ACPOS_ASSET-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","71c6c4b8b734a51db5f83b73fc76d455973b8775"),
"CORE-01":("ACPOS_CORE-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","a140edcba1d76d5d38b088ec856f6c2bd4692978"),
"DB-01":("ACPOS_DB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","741bd95a20b44252725732c0158d2439364cb83e"),
"DEV-01":("ACPOS_DEV-01_企業自動開發系統_Mother_Basic_Design_OPTIMIZED.docx","a98a7eedabcf27af1ecb7015591b2a7c85ecb8de"),
"EDIT-01":("ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","f478bbe5e80b4b26b73e131536db740724364003"),
"ERP-01":("ACPOS_ERP-01_ERP與財務_Mother_Basic_Design_OPTIMIZED.docx","87e3086adc0f705a8e13ac9c73dabb2b30cafa33"),
"IAM-01":("ACPOS_IAM-01_帳戶與權限_Mother_Basic_Design_OPTIMIZED.docx","e1845f6997cd87abf4f38a24a247a30d41cd065b"),
"INFO-01":("ACPOS_INFO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","9c8af306b835c49d7216824c82f420c0c4d8e5b1"),
"KB-01":("ACPOS_KB-01_知識庫_Mother_Basic_Design_OPTIMIZED.docx","e46ef542a5be7249f3b5f60ff308bdfd8e26bacb"),
"QA-01":("ACPOS_QA-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","dd5533f7ab0ffec491f2d6ab16c86c84cead8a7c"),
"SG-02":("ACPOS_SG-02_QA審查項目名單_Mother_Basic_Design_OPTIMIZED.docx","dc21e0b85a0058953d127b0f9b42c9b500fd19ba"),
"SOC-01":("ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx","82112c2a3759b4d5b3ebce4e1ed184198ac0d0b2"),
"STR-01":("ACPOS_STR-01_WORKSPACE_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","2273aa79858e3a0b4bb7c9ff99cd192d54220bc4"),
"SYS-01":("ACPOS_SYS-01_系統維護與生命週期工作區_Mother_Basic_Design_OPTIMIZED.docx","e2be8ed3fec0eed66fa53135d5bad5b4a963ff7a"),
"VIDEO-01":("ACPOS_VIDEO-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","5c524d869b8e255b1706fbc3faa05918d0ab9524"),
"WB-01":("ACPOS_WB-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","d262022d97d3138dae98b0c45c59bd859f3600fd"),
"ADMIN-STR-01":("ACPOS_admin_STR-01_戰略中心後台_Mother_Basic_Design_OPTIMIZED.docx","b1102528b53aa1a9230f610ac386fd208df0a916"),
}

def blob_sha(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

assert blob_sha(TARGET)==TARGET_SHA,(blob_sha(TARGET),TARGET_SHA)
for uid,(fn,sha) in PAGES.items():
    a=blob_sha(fn)
    assert a==sha,(uid,a,sha)

def norm(x):
    return re.sub(r"\s+"," ",x.replace("\n"," | ").strip())

def hfind(headers,*needles):
    hs=[norm(x).lower() for x in headers]
    for needle in needles:
        n=needle.lower()
        for i,h in enumerate(hs):
            if n in h:return i
    return None

def get(vals,i):
    if i is None or i>=len(vals):return ""
    return norm(vals[i])

def is_missing(v):
    return v in {"","—","-","SOURCE_NOT_DEFINED"}

DISPLAY_ONLY_TYPES={
"READONLY","LABEL","TEXT","BADGE","STATUS","METRIC","KPI","DIVIDER","ICON","PANEL","CARD","VIEW","LIST","TABLE","CHIP","TAG","DISPLAY"
}

def extract_controls(doc):
    best={}
    for ti,t in enumerate(doc.tables):
        if not t.rows: continue
        headers=[norm(c.text) for c in t.rows[0].cells]
        ci=hfind(headers,"control uid")
        if ci is None: continue
        idx={
          "uid":ci,
          "type":hfind(headers,"type"),
          "label":hfind(headers,"label","顯示名稱"),
          "action":hfind(headers,"action uid"),
          "gate":hfind(headers,"gate"),
          "permission":hfind(headers,"permission","auth resource"),
          "payload":hfind(headers,"payload","schema"),
          "operation":hfind(headers,"operation"),
          "method":hfind(headers,"method","path"),
          "runtime_owner":hfind(headers,"runtime owner"),
          "persistence_owner":hfind(headers,"persistence owner"),
          "runtime_status":hfind(headers,"runtime status"),
        }
        for r in t.rows[1:]:
            vals=[c.text for c in r.cells]
            uid=get(vals,idx["uid"])
            if not uid or uid in {"—","-"} or not re.search(r"[A-Za-z0-9]",uid): continue
            row={k:get(vals,v) for k,v in idx.items()}
            row["_table"]=ti+1
            score=sum(1 for k,v in row.items() if not k.startswith("_") and k!="uid" and v not in {"","—","-","SOURCE_NOT_DEFINED"})
            if uid not in best or score>best[uid]["_score"]:
                row["_score"]=score
                best[uid]=row
    for r in best.values(): r.pop("_score",None)
    return best

def type_is_display_only(row):
    typ=row.get("type","").upper()
    return typ in DISPLAY_ONLY_TYPES or any(x in typ for x in ["READONLY","LABEL","DISPLAY","METRIC","KPI","STATUS"])

def classify(field,row):
    val=row.get(field,"")
    status=row.get("runtime_status","")
    if not is_missing(val):
        return ("BOUND","Source row already contains an exact value.")
    if "UI_LOCAL_EXACT" in status:
        if field in {"operation","runtime_owner"}:
            return ("LEGITIMATE_NA_UI_LOCAL","UI_LOCAL_EXACT forbids creating a server write/runtime binding.")
        if field=="action" and type_is_display_only(row):
            return ("LEGITIMATE_NA_UI_LOCAL","Display-only local control has no effectful Action requirement.")
    if "OWNER_ORCHESTRATED_RUNTIME_EXACT_NO_PUBLIC_ROUTE" in status:
        if field=="operation":
            return ("CLOSED_BY_OWNER_LOCAL_COMMAND","Batch-02 contract uses existing Action UID as owner-orchestrated local command identity; public operation/API must not be invented.")
    if "READ_EXACT" in status and type_is_display_only(row):
        if field=="action":
            return ("LEGITIMATE_NA_READ_PRESENTATION","Display-only READ_EXACT control does not itself trigger an action.")
        if field=="operation" and not is_missing(row.get("runtime_owner","")):
            return ("READ_OWNER_BOUND_OPERATION_UNSPECIFIED","Read owner exists but operation cell is absent; classify separately rather than inventing an operation.")
    if field=="runtime_owner" and any(x in status for x in ["SPEC_EXACT_RUNTIME_BLOCKED","SPEC_EXACT_RUNTIME_NOT_EXECUTED","RUNTIME_IMPLEMENTATION_BLOCKED"]):
        return ("KNOWN_RUNTIME_BLOCKER","Runtime is explicitly blocked/not executed; owner must come from canonical source before enablement.")
    if val=="SOURCE_NOT_DEFINED":
        return ("SOURCE_RESOLUTION_REQUIRED","Canonical source does not define this field; do not guess.")
    return ("DEFINITION_BINDING_GAP","Required binding is absent and no current status/type rule proves it is N/A.")

fields=["action","gate","permission","operation","runtime_owner"]
class_rows=[]
counts={}
per_page={}
for page_uid,(fn,_) in PAGES.items():
    controls=extract_controls(Document(fn))
    pcount={}
    for uid in sorted(controls):
        row=controls[uid]
        for field in fields:
            if is_missing(row.get(field,"")):
                cls,reason=classify(field,row)
                rec=[
                    page_uid,uid,row.get("type",""),row.get("label",""),field,row.get(field,""),
                    cls,reason,row.get("action",""),row.get("gate",""),row.get("permission",""),
                    row.get("operation",""),row.get("runtime_owner",""),row.get("runtime_status",""),f"T{row.get('_table')}"
                ]
                class_rows.append(rec)
                counts[cls]=counts.get(cls,0)+1
                pcount[cls]=pcount.get(cls,0)+1
    per_page[page_uid]=pcount

assert class_rows, "NO_MISSING_FIELD_ROWS_FOUND"
assert counts.get("DEFINITION_BINDING_GAP",0)>0, counts

doc=Document(TARGET)
alltxt="\n".join([p.text for p in doc.paragraphs]+[c.text for t in doc.tables for r in t.rows for c in r.cells])
assert MARK not in alltxt,"ALREADY_CLASSIFIED"

s=doc.add_section(WD_SECTION.NEW_PAGE)
s.orientation=WD_ORIENT.LANDSCAPE
s.page_width,s.page_height=s.page_height,s.page_width
s.top_margin=Inches(.35);s.bottom_margin=Inches(.35);s.left_margin=Inches(.3);s.right_margin=Inches(.3)
doc.add_heading("Batch 04 · Direct Binding Classification / Conversion Integrity Guard",level=1)
p=doc.add_paragraph()
p.add_run(f"[{MARK}] ").bold=True
p.add_run("Raw missing cells are not auto-filled. Every absent Action/Gate/Permission/Operation/Runtime Owner is classified against exact control type + runtime status. Only DEFINITION_BINDING_GAP rows are eligible for later authority remediation; N/A/local/read-owner/known-runtime-blocker rows must not be converted into invented bindings.")

def repeat_header(row):
    trPr=row._tr.get_or_add_trPr();e=OxmlElement("w:tblHeader");e.set(qn("w:val"),"true");trPr.append(e)
def shade(cell,fill="EDE9FE"):
    tcPr=cell._tc.get_or_add_tcPr();e=OxmlElement("w:shd");e.set(qn("w:fill"),fill);tcPr.append(e)
def table(headers,rows,fs=4.7):
    t=doc.add_table(rows=1,cols=len(headers));t.style="Table Grid";repeat_header(t.rows[0])
    for i,h in enumerate(headers):t.rows[0].cells[i].text=str(h);shade(t.rows[0].cells[i])
    for row in rows:
        c=t.add_row().cells
        for i,v in enumerate(row):c[i].text=str(v)
    for row in t.rows:
        for cell in row.cells:
            for pp in cell.paragraphs:
                for rr in pp.runs:rr.font.size=Pt(fs)
    return t

doc.add_heading("Classification Semantics",level=2)
table(["Class","Meaning / permitted action"],[
["BOUND","Exact source row already defines the field; no remediation."],
["LEGITIMATE_NA_UI_LOCAL","UI_LOCAL_EXACT local behavior; do not invent server operation/runtime."],
["LEGITIMATE_NA_READ_PRESENTATION","Display-only READ_EXACT control has no effectful action."],
["CLOSED_BY_OWNER_LOCAL_COMMAND","Owner-orchestrated local command is the operation boundary; no public API/operation invention."],
["READ_OWNER_BOUND_OPERATION_UNSPECIFIED","Read owner is present but operation cell absent; preserve as a distinct source-definition question, not an invented operation."],
["KNOWN_RUNTIME_BLOCKER","Current authority explicitly blocks/not-executes runtime; keep disabled until canonical owner + implementation evidence exist."],
["SOURCE_RESOLUTION_REQUIRED","Source explicitly says SOURCE_NOT_DEFINED; requires canonical source decision."],
["DEFINITION_BINDING_GAP","No current rule proves N/A and required binding is absent; eligible for next remediation batch."],
],5.2)

summary_rows=[[k,counts[k]] for k in sorted(counts)]
doc.add_heading("Classification Totals",level=2)
table(["Classification","Count"],summary_rows,5.6)

page_summary=[]
for page_uid in PAGES:
    pc=per_page[page_uid]
    page_summary.append([page_uid]+[pc.get(k,0) for k in [
      "DEFINITION_BINDING_GAP","SOURCE_RESOLUTION_REQUIRED","KNOWN_RUNTIME_BLOCKER",
      "CLOSED_BY_OWNER_LOCAL_COMMAND","READ_OWNER_BOUND_OPERATION_UNSPECIFIED",
      "LEGITIMATE_NA_UI_LOCAL","LEGITIMATE_NA_READ_PRESENTATION"
    ]])
doc.add_heading("Per-page Missing-binding Classification",level=2)
table(["Page","Definition Gap","Source Resolution","Runtime Blocker","Owner Local","Read Op Unspecified","UI Local N/A","Read Presentation N/A"],page_summary,4.8)

doc.add_heading("Definition Binding Gap Rows / Next Remediation Denominator",level=2)
gap_rows=[r for r in class_rows if r[6] in {"DEFINITION_BINDING_GAP","SOURCE_RESOLUTION_REQUIRED","READ_OWNER_BOUND_OPERATION_UNSPECIFIED","KNOWN_RUNTIME_BLOCKER"}]
table(["Page","Control UID","Type","Label","Missing Field","Raw","Classification","Reason","Action","Gate","Permission","Operation","Runtime Owner","Runtime Status","Source"],gap_rows,3.8)

doc.add_heading("Mandatory Conversion Integrity Guard",level=2)
table(["Guard","Requirement"],[
["ENC-01 DOCX XML validity","Open produced DOCX with python-docx and parse all XML parts; invalid XML/encoding = FAIL."],
["ENC-02 Unicode replacement","U+FFFD replacement char, NUL, or undecodable text in DOCX/PDF extraction = FAIL."],
["ENC-03 Mojibake signatures","Known UTF-8/Latin-1 corruption signatures are forbidden. The executable guard owns the signature list; the normative Word records only the rule so the document itself cannot self-trigger the detector."],
["ENC-04 Source-to-PDF CJK retention","After removing whitespace, PDF-extracted CJK count must retain at least 97 percent of source DOCX CJK count; otherwise FAIL."],
["ENC-05 Critical phrase retention","Batch marker and declared canonical English/Chinese phrases must survive PDF extraction."],
["ENC-06 Conversion freshness","Run encoding integrity immediately after every DOCX-to-PDF conversion; prior PASS cannot be reused."],
["ENC-07 Fail closed","Any encoding/garble failure blocks scope validation and commit; layout PASS alone is insufficient."],
["ENC-08 Path encoding","Git scope checks MUST use raw UTF-8 paths via core.quotePath=false; do not parse quoted porcelain paths or hand-roll NUL splitting."],
],5.2)

payload={
 "marker":MARK,
 "total_missing_cells":len(class_rows),
 "classification_counts":counts,
 "per_page":per_page,
 "next_remediation_count":counts.get("DEFINITION_BINDING_GAP",0),
}
doc.add_paragraph("BATCH04_MACHINE_JSON="+json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")))
doc.save(TARGET)
Document(TARGET)
print(json.dumps(payload,ensure_ascii=False,indent=2))
