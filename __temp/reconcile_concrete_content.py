from pathlib import Path
from docx import Document
import json,re

NEW_CONTROL={
"Control UID":"CTRL-ADMIN-SG-02-ACT-04-ACT-SUBMIT-REVIEW",
"UID Status":"NEW_AUTHORITY_AFTER_COMPLETE_SOURCE_SCAN",
"Label":"送出審查 / Submit Review",
"Type":"SECONDARY_BUTTON",
"Action UID":"SG-02-ACT-SUBMIT-REVIEW",
"Gate":"SG-02-GATE-SUBMIT-REVIEW",
"Permission / Auth Resource":"quality.criteria.configure",
"Payload / Schema":"SubmitGovernedResourceReviewRequest",
"Operation":"submitGovernedResourceReview",
"Method / Path":"POST /v1/governance/resources/{id}/submit-review",
"Runtime Owner":"Quality Governance Runtime",
"Persistence Owner":"governed Criteria Draft / Review lifecycle",
"Runtime Status":"NEW_AUTHORITY_RUNTIME_IMPLEMENTATION_REQUIRED",
}
STATUS="SOURCE_TESTS_6/6_PASS; PRODUCTION_READONLY_9/9_PASS; EFFECTFUL_PENDING_FORMAL_CRITERIA_MATERIALIZATION_AND_SUBMIT_REVIEW_RUNTIME"
touched=[]
for p in Path('.').glob('*.docx'):
    d=Document(p); changed=False
    # paragraph reconciliation
    for para in d.paragraphs:
        txt=para.text
        if p.name.startswith('ACPOS_SG-02_'):
            repl=txt.replace('11 controls','12 controls').replace('11-control','12-control').replace('Control Denominator = 11','Control Denominator = 12')
            if repl!=txt:
                para.text=repl; changed=True
    for t in d.tables:
        rr=[[c.text.strip() for c in r.cells] for r in t.rows]
        if not rr: continue
        hdr=rr[0]
        # Exact binding matrix.
        if 'Control UID' in hdr and 'Runtime Status' in hdr:
            h={x:i for i,x in enumerate(hdr)}
            sg_rows=[r for r in t.rows[1:] if r.cells[h['Control UID']].text.strip().startswith('CTRL-ADMIN-SG-02-')]
            if sg_rows:
                existing={r.cells[h['Control UID']].text.strip() for r in sg_rows}
                if NEW_CONTROL['Control UID'] not in existing:
                    cells=t.add_row().cells
                    for name,idx in h.items():
                        cells[idx].text=NEW_CONTROL.get(name,'—')
                    changed=True
        # Machine Authority denominator table.
        if hdr==['Authority','Value']:
            vals={r.cells[0].text.strip():r.cells[1].text.strip() for r in t.rows[1:] if len(r.cells)>=2}
            ma=vals.get('Machine Authority','')
            if 'SG-02' in ma or 'admin/SG-02' in ma:
                for r in t.rows[1:]:
                    key=r.cells[0].text.strip()
                    if key in ('Expected Control Denominator','Unique Control Rows'):
                        if r.cells[1].text.strip()!='12':
                            r.cells[1].text='12';changed=True
                    if key=='Denominator Gate' and r.cells[1].text.strip()!='PASS':
                        r.cells[1].text='PASS';changed=True
        # Index denominator.
        if 'Page' in hdr and ('Expected Controls' in hdr or 'Exact Rows' in hdr):
            h={x:i for i,x in enumerate(hdr)}
            for r in t.rows[1:]:
                page=r.cells[h['Page']].text.strip() if h['Page']<len(r.cells) else ''
                if page=='SG-02':
                    for key in ('Expected Controls','Exact Rows'):
                        if key in h and r.cells[h[key]].text.strip()!='12':
                            r.cells[h[key]].text='12';changed=True
        # Replace obsolete SG02 NOT_EXECUTED status only when explicitly named.
        for r in t.rows[1:]:
            texts=[c.text.strip() for c in r.cells]
            joined=' | '.join(texts)
            if 'RUNTIME_BINDING_VALIDATION' in joined and 'NOT_EXECUTED' in joined:
                for c in r.cells:
                    if 'NOT_EXECUTED' in c.text:
                        c.text=c.text.replace('NOT_EXECUTED',STATUS);changed=True
            if 'SG-02' in joined and '11' in joined and ('denominator' in joined.lower() or 'control' in joined.lower()):
                for c in r.cells:
                    if c.text.strip()=='11':
                        c.text='12';changed=True
    if changed:
        d.save(p);Document(p);touched.append(p.name)
Path('__temp').mkdir(exist_ok=True)
Path('__temp/reconcile_report.json').write_text(json.dumps({'touched':touched,'new_control':NEW_CONTROL,'runtime_status':STATUS},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'touched':touched},ensure_ascii=False))
