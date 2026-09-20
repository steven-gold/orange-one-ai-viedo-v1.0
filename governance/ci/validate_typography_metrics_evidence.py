#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import yaml

REQUIRED_TOP={"artifact_type","scope_uid","viewport_uid","language","theme","targets"}
REQUIRED_TARGET={"target_uid","typography_authority_ref","expected","actual","tolerance","result"}
EXPECTED_FIELDS={"font_family","font_size_px","font_weight","line_height_px","letter_spacing_px","text_container_min_width_px","text_container_max_width_px","wrap_rule","truncation_rule"}
ACTUAL_FIELDS={"font_family","font_size_px","font_weight","line_height_px","letter_spacing_px","text_container_width_px","text_container_height_px","scroll_width_px","scroll_height_px","rendered_line_count","wrap_state","truncation_state","clipping","overflow"}
TOLERANCE_FIELDS={"font_size_px","line_height_px","letter_spacing_px","container_width_px"}

def load(path):
    p=Path(path);raw=p.read_text(encoding="utf-8")
    return json.loads(raw) if p.suffix.lower()==".json" else (yaml.safe_load(raw) or {})

def finite_number(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(float(v))

def validate(data):
    failures=[]
    missing=sorted(k for k in REQUIRED_TOP if k not in data or data.get(k) in (None,""))
    if missing:failures.append({"code":"TOP_LEVEL_REQUIRED_FIELD_MISSING","fields":missing})
    if data.get("artifact_type")!="TYPOGRAPHY_COMPUTED_METRICS_EVIDENCE":
        failures.append({"code":"ARTIFACT_TYPE_INVALID","actual":data.get("artifact_type")})
    rows=data.get("targets")
    if not isinstance(rows,list) or not rows:
        failures.append({"code":"TARGET_DENOMINATOR_EMPTY"});rows=[]
    seen=set()
    for idx,row in enumerate(rows):
        if not isinstance(row,dict):
            failures.append({"code":"TARGET_ROW_INVALID","index":idx});continue
        miss=sorted(k for k in REQUIRED_TARGET if k not in row or row.get(k) in (None,""))
        if miss:failures.append({"code":"TARGET_REQUIRED_FIELD_MISSING","target_uid":row.get("target_uid"),"fields":miss})
        uid=str(row.get("target_uid") or "")
        if not uid or uid in seen:failures.append({"code":"TARGET_UID_EMPTY_OR_DUPLICATE","target_uid":uid})
        seen.add(uid)
        exp=row.get("expected") if isinstance(row.get("expected"),dict) else {}
        act=row.get("actual") if isinstance(row.get("actual"),dict) else {}
        tol=row.get("tolerance") if isinstance(row.get("tolerance"),dict) else {}
        em=sorted(EXPECTED_FIELDS-set(exp));am=sorted(ACTUAL_FIELDS-set(act));tm=sorted(TOLERANCE_FIELDS-set(tol))
        if em:failures.append({"code":"EXPECTED_METRIC_MISSING","target_uid":uid,"fields":em})
        if am:failures.append({"code":"COMPUTED_METRIC_MISSING","target_uid":uid,"fields":am})
        if tm:failures.append({"code":"TOLERANCE_MISSING","target_uid":uid,"fields":tm})
        for key in ("font_size_px","line_height_px","letter_spacing_px"):
            if key in exp and key in act and key in tol and all(finite_number(x) for x in (exp[key],act[key],tol[key])):
                if abs(float(act[key])-float(exp[key]))>float(tol[key]):
                    failures.append({"code":"TYPOGRAPHY_TOLERANCE_EXCEEDED","target_uid":uid,"metric":key,"expected":exp[key],"actual":act[key],"tolerance":tol[key]})
        if exp.get("font_family") and act.get("font_family") and str(exp["font_family"]).lower() not in str(act["font_family"]).lower():
            failures.append({"code":"FONT_FAMILY_MISMATCH","target_uid":uid,"expected":exp["font_family"],"actual":act["font_family"]})
        if exp.get("font_weight") is not None and act.get("font_weight") is not None and str(exp["font_weight"])!=str(act["font_weight"]):
            failures.append({"code":"FONT_WEIGHT_MISMATCH","target_uid":uid,"expected":exp["font_weight"],"actual":act["font_weight"]})
        if act.get("clipping") is not False:failures.append({"code":"TEXT_CLIPPING","target_uid":uid})
        if act.get("overflow") is not False:failures.append({"code":"TEXT_OVERFLOW","target_uid":uid})
        if row.get("result")!="PASS":failures.append({"code":"TARGET_RESULT_NOT_PASS","target_uid":uid,"actual":row.get("result")})
    return {"artifact_type":"TYPOGRAPHY_COMPUTED_METRICS_VALIDATION_RESULT","scope_uid":data.get("scope_uid"),"target_total":len(rows),"failure_total":len(failures),"result":"PASS" if not failures else "BLOCKED","failures":failures,"product_stage_credit":0}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--evidence",required=True);ap.add_argument("--report");args=ap.parse_args()
    out=validate(load(args.evidence))
    if args.report:Path(args.report).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2));return 0 if out["result"]=="PASS" else 2
if __name__=="__main__":raise SystemExit(main())
