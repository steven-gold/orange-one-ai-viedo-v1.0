#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml
def load(p):
    p=Path(p)
    if not p.is_file() or p.stat().st_size<=0: raise SystemExit("BLOCK:MISSING_OR_EMPTY:"+str(p))
    d=yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(d,dict): raise SystemExit("BLOCK:MAPPING_REQUIRED:"+str(p))
    return d
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",required=True); ap.add_argument("--validator-uid",required=True); ap.add_argument("--work-unit",required=True); ap.add_argument("--product-root",required=True)
    a=ap.parse_args(); root=Path(a.product_root).resolve(); wp=root/Path(a.work_unit); wd=wp.parent; work=load(wp); state=load(wd/"EXECUTION_STATE.yaml"); matrix=load(wd/"NORMATIVE_EXECUTION_MATRIX.yaml")
    if str(work.get("stage_uid"))!=a.stage or str(state.get("stage_uid"))!=a.stage: raise SystemExit("BLOCK:DECLARED_VALIDATOR_STAGE_DRIFT")
    if str(state.get("current_operation"))!="COMPLETE": raise SystemExit("BLOCK:DECLARED_VALIDATOR_OPERATIONS_INCOMPLETE")
    if matrix.get("status")!="PASS": raise SystemExit("BLOCK:DECLARED_VALIDATOR_MATRIX_NOT_PASS")
    sb=work.get("scanner_bindings") or {}
    if not sb: raise SystemExit("BLOCK:DECLARED_VALIDATOR_SCANNER_BINDINGS_EMPTY")
    for dim,b in sb.items():
        d=load(root/str((b or {}).get("result_ref") or ""))
        if d.get("status")!="PASS" or str(d.get("scanner_dimension") or "")!=str(dim) or (d.get("gaps") or []): raise SystemExit("BLOCK:DECLARED_VALIDATOR_SCANNER_NOT_PASS:"+str(dim))
    print("PASS:",a.validator_uid,a.stage,work.get("work_unit_uid"))
if __name__=="__main__": main()
