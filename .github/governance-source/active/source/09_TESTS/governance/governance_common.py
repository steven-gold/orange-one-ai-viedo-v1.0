from __future__ import annotations
from pathlib import Path
import hashlib, re, yaml

SOURCE_DOCS = [
    ("WEB-GOV-01", "12_DOCS/mother-spec/01_BLUEPRINT_DESIGN_GOVERNANCE.md"),
    ("WEB-GOV-02", "12_DOCS/mother-spec/02_IMPLEMENTATION_DELIVERY_STANDARD.md"),
    ("WEB-GOV-03", "12_DOCS/mother-spec/03_EXECUTION_CONTROL_STANDARD.md"),
    ("WEB-GOV-04", "12_DOCS/mother-spec/04_AUDIT_PROGRESS_STANDARD.md"),
]

AUTO_VALIDATORS = {
    "governance_source_integrity",
    "baseline_compilation_coverage",
    "parser_guard",
    "mapping_schema_guard",
    "naming_registry_schema_guard",
    "current_revision_guard",
    "current_state_ledger_guard",
    "audit_binding_guard",
    "duplicate_guard",
    "residual_guard",
    "authority_manifest_guard",
    "source_truth_guard",
    "functional_chain_guard",
    "visual_geometry_guard",
    "production_render_identity_guard",
    "cross_page_flow_guard",
    "validation_run_freshness_guard",
    "execution_cycle_guard",
    "repository_boundary_guard",
    "design_approval_timing_guard",
    "deployment_applicability_guard",
    "state_transition_guard",
    "field_identity_guard",
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())

def normalize_clause(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end]) or {}

def classify_validator(clause: str, section: str) -> str:
    t = (clause + " " + section).lower()
    if "source-to-target" in t or "mapping" in t or "preservation" in t or "classification" in t:
        return "mapping_schema_guard"
    if "naming registry" in t or "canonical name" in t or "alias" in t or "deprecated name" in t:
        return "naming_registry_schema_guard"
    if "current revision" in t or "reverify_required" in t or "old pass" in t:
        return "current_revision_guard"
    if "current state" in t or "active work unit" in t or "resume point" in t or "execution ledger" in t:
        return "current_state_ledger_guard"
    if "audit baseline" in t or "acceptance matrix" in t or "evidence" in t or "pass" in t and "audit" in t:
        return "audit_binding_guard"
    if "duplicate" in t:
        return "duplicate_guard"
    if "residual" in t or "backup" in t or "temp" in t or "dead file" in t or "orphan" in t:
        return "residual_guard"
    if "authority" in t or "owner" in t:
        return "authority_manifest_guard"
    if "source truth" in t or "source contamination" in t or "污染" in t or "source_intake" in t:
        return "source_truth_guard"
    if "functional chain" in t or "功能鏈" in t or "auto_remediable" in t or "implementation_gap" in t:
        return "functional_chain_guard"
    if "visual geometry" in t or "geometry baseline" in t or "擠壓" in t or "bounding box" in t:
        return "visual_geometry_guard"
    if "production stale" in t or "render identity" in t or "build_identity_manifest" in t or "正式網址" in t:
        return "production_render_identity_guard"
    if "cross-page" in t or "跨頁" in t or "flow uid" in t or "slice" in t:
        return "cross_page_flow_guard"
    if "run_uid" in t or "current-run" in t or "freshness" in t or "stale-pass" in t:
        return "validation_run_freshness_guard"
    if "execution cycle" in t:
        return "execution_cycle_guard"
    if "repository boundary" in t or "repository-boundary" in t:
        return "repository_boundary_guard"
    if "design approval" in t or "approval timing" in t:
        return "design_approval_timing_guard"
    if "deployment applicability" in t or "applicability coherence" in t:
        return "deployment_applicability_guard"
    if "state transition" in t or "stage transition" in t:
        return "state_transition_guard"
    if "field identity" in t or "canonical field" in t:
        return "field_identity_guard"
    if "yaml" in t or "json" in t or "parse" in t:
        return "parser_guard"
    return "manual_semantic_guard"

def extract_requirements(root: Path) -> tuple[list[dict], list[dict]]:
    reqs: list[dict] = []
    sources: list[dict] = []
    for doc_id, rel in SOURCE_DOCS:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        sources.append({
            "document_id": doc_id,
            "path": rel,
            "sha256": sha256_file(path),
            "version": str(meta.get("version", "")),
            "status": meta.get("status"),
            "permanent_inheritance": bool(meta.get("permanent_inheritance")),
        })
        lines = text.splitlines()
        heading = ""
        in_code = False
        seq = {"MUST": 0, "MUST_NOT": 0}
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if s.startswith("#"):
                heading = s.lstrip("#").strip()
                continue
            if heading.startswith("1. 規範關鍵字"):
                continue
            modalities = []
            if "MUST_NOT" in s:
                modalities.append("MUST_NOT")
            # avoid matching MUST inside MUST_NOT
            masked = s.replace("MUST_NOT", "")
            if re.search(r"(?<![A-Z_])MUST(?![A-Z_])", masked):
                modalities.append("MUST")
            if not modalities:
                continue
            # Capture immediate list as one composite requirement, but only store hashes/counts in baseline.
            children = []
            if s.endswith(":") or s.endswith("："):
                j = idx
                while j < len(lines):
                    nxt = lines[j].strip()
                    if not nxt:
                        j += 1
                        continue
                    if nxt.startswith("#") or nxt.startswith("```"):
                        break
                    if re.match(r"^(?:[-*]|\d+\.)\s+", nxt):
                        children.append(normalize_clause(nxt))
                        j += 1
                        continue
                    break
            for modality in modalities:
                seq[modality] += 1
                clause = normalize_clause(s)
                material = clause + "\n" + "\n".join(children)
                validator_id = classify_validator(clause, heading)
                reqs.append({
                    "requirement_id": f"{doc_id.replace('WEB-GOV-', 'GOV')}-{modality}-{seq[modality]:03d}",
                    "source": doc_id,
                    "section": heading,
                    "line": idx,
                    "modality": modality,
                    "clause_hash": sha256_bytes(material.encode("utf-8")),
                    "clause_excerpt": clause[:180],
                    "list_item_count": len(children),
                    "list_hash": sha256_bytes("\n".join(children).encode("utf-8")) if children else None,
                    "validator_id": validator_id,
                    "automation": "AUTO" if validator_id in AUTO_VALIDATORS else "MANUAL_EVIDENCE",
                    "blocking": True,
                })
    return reqs, sources
