#!/usr/bin/env python3
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'governance/ci/build_stage_governance_load_receipt.py'
spec=importlib.util.spec_from_file_location('stage_load',P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
out=m.build(False)
cases=[
  ('current_build_pass',out.get('status')=='PASS'),
  ('producer_product_neutral', all(t not in P.read_text(encoding='utf-8') for t in ('CORE01','CORE-01','ASSET-01','VIDEO-01','EDIT-01','WU-STAGE01-CORE01'))),
  ('no_persist_during_test',out.get('persisted') is False),
  ('effective_normative_nonzero',int(out.get('effective_normative_count') or 0)>0),
  ('loaded_artifact_nonzero',int(out.get('loaded_artifact_count') or 0)>0),
]
result={'suite':'generic stage governance load producer','total':len(cases),'passed_expectations':sum(1 for _,ok in cases if ok),'results':[{'case':n,'ok':ok} for n,ok in cases]}
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed_expectations']==result['total'] else 1)
