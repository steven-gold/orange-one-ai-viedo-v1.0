from pathlib import Path
from docx import Document
import hashlib, json, re

FILES={
"SOC":("ACPOS_SOC-01_社群發布_Mother_Basic_Design_OPTIMIZED.docx","154ca20b3592728f11f475ee8dc8c22466a02524"),
"EDIT":("ACPOS_EDIT-01_MOTHER_BASIC_DESIGN_TECH_PURPLE_v1.0.docx","334a37b3ca39f3356f6c9e83ef8572be409ba35b"),
"ADMIN_STR":("ACPOS_admin_STR-01_戰略中心後台_Mother_Basic_Design_OPTIMIZED.docx","c3993113999e839380498839a72797d28d671c2a"),
"S05":("05_ACPOS_Creative_Production_AI_ASSET_VIDEO_EDIT_VOICE_QA_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx","8e3c4e7c4ba36a094293bcbe0d56ee05c1d2e6b9"),
"S08":("08_ACPOS_Strategy_Intelligence_MultiAI_Decision_System_Mother_Basic_Logic_Design_Normative_Contract_v1.0.docx","95102b7a6c4496355cdb6d2ce069d0125c0cb5ef"),
}

def git_blob_sha(path):
    b=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

for k,(fn,expected) in FILES.items():
    a=git_blob_sha(fn)
    assert a==expected,(k,a,expected)

patterns={
"SOC":[r"Publish",r"發布",r"QA",r"scorecard",r"criteria",r"checksum",r"required.check",r"blocking.find",r"eligib"],
"EDIT":[r"上傳媒體",r"取消.?Job",r"執行修正",r"產生修正腳本",r"Timeline",r"重檢",r"Lip.?Sync",r"退回.?Blueprint",r"Upload.?Spec",r"Standalone.?Voice",r"port",r"operation",r"owner",r"runtime",r"NO_PUBLIC_API",r"15.?ports",r"13.?operations"],
"ADMIN_STR":[r"STR-01",r"operation",r"操作",r"owner",r"runtime",r"persistence",r"authorization",r"permission",r"blocked"],
"S05":[r"EDIT",r"port",r"operation",r"OWNER_ORCHESTRATED",r"NO_PUBLIC_API",r"Timeline",r"Lip.?Sync",r"Voice"],
"S08":[r"STR-01",r"admin",r"operation",r"runtime",r"persistence",r"authorization",r"permission",r"blocked"],
}

def rows(doc):
    for ti,t in enumerate(doc.tables):
        for ri,r in enumerate(t.rows):
            vals=[c.text.replace("\n"," | ").strip() for c in r.cells]
            yield ("TABLE",ti,ri," || ".join(vals))
    for pi,p in enumerate(doc.paragraphs):
        s=p.text.strip()
        if s: yield ("PARA",pi,None,s)

for k,(fn,_) in FILES.items():
    d=Document(fn)
    rx=re.compile("|".join(patterns[k]),re.I)
    hits=[]
    for kind,a,b,s in rows(d):
        if rx.search(s):
            hits.append({"kind":kind,"a":a,"b":b,"text":s[:1800]})
    print("===== "+k+" :: "+fn+" =====")
    for h in hits[:220]:
        print(json.dumps(h,ensure_ascii=False))
    print("HIT_COUNT",len(hits))
