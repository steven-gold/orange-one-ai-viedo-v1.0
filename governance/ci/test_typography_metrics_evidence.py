#!/usr/bin/env python3
from copy import deepcopy
from validate_typography_metrics_evidence import validate
def row(uid,size=14):
    return {"target_uid":uid,"typography_authority_ref":"TOKEN-TYPE-BODY","expected":{"font_family":"Inter","font_size_px":size,"font_weight":400,"line_height_px":20,"letter_spacing_px":0,"text_container_min_width_px":120,"text_container_max_width_px":420,"wrap_rule":"WRAP_ALLOWED","truncation_rule":"NO_TRUNCATION"},"actual":{"font_family":"Inter, sans-serif","font_size_px":size,"font_weight":400,"line_height_px":20,"letter_spacing_px":0,"text_container_width_px":240,"text_container_height_px":40,"scroll_width_px":240,"scroll_height_px":40,"rendered_line_count":2,"wrap_state":"WRAPPED","truncation_state":"NONE","clipping":False,"overflow":False},"tolerance":{"font_size_px":0.01,"line_height_px":0.01,"letter_spacing_px":0.01,"container_width_px":1},"result":"PASS"}
def ev(scope,n):
    return {"artifact_type":"TYPOGRAPHY_COMPUTED_METRICS_EVIDENCE","scope_uid":scope,"viewport_uid":"DESKTOP","language":"en","theme":"DEFAULT","targets":[row(f"T-{i}") for i in range(n)]}
for x in (ev("CATALOG",2),ev("BILLING",7)):assert validate(x)["result"]=="PASS"
bad=ev("OPS",1);del bad["targets"][0]["actual"]["line_height_px"];assert validate(bad)["result"]=="BLOCKED"
bad=ev("KNOWLEDGE",1);bad["targets"][0]["actual"]["clipping"]=True;assert any(x["code"]=="TEXT_CLIPPING" for x in validate(bad)["failures"])
bad=ev("SUPPORT",1);bad["targets"][0]["actual"]["font_size_px"]=18;assert any(x["code"]=="TYPOGRAPHY_TOLERANCE_EXCEEDED" for x in validate(bad)["failures"])
print("PASS: typography computed metrics validator is product-neutral, denominator-dynamic, and fail-closed")
