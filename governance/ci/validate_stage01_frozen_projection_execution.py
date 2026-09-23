#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "governance/test/ACTIVE_STATE.yaml"
SCOPE = ROOT / "governance/test/CURRENT_EXECUTION_SCOPE_MANIFEST.yaml"
ALLOWED_PROJECTION_DISPOSITIONS = {
    "SEMANTIC_SOURCE_NODE",
    "STRUCTURAL_SUPPORT",
    "NON_SEMANTIC_WITH_EVIDENCE",
}


def load(path: Path):
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    return obj if obj is not None else {}


def stable_hash_obj(obj) -> str:
    payload = yaml.safe_dump(obj, allow_unicode=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_without(doc: dict, key: str) -> str:
    cp = dict(doc)
    cp.pop(key, None)
    return stable_hash_obj(cp)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_rel(value: str, label: str) -> str:
    p = Path(str(value))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise RuntimeError(f"{label}_INVALID_PATH:{value}")
    return p.as_posix()


def resolve_current() -> tuple[dict, dict, Path]:
    state = load(STATE)
    scope = load(SCOPE)
    work = state.get("active_work_unit") or {}
    if work.get("primary_task_layer") != "PRODUCT_STAGE_EXECUTION":
        raise RuntimeError("ACTIVE_PRODUCT_WORK_UNIT_MISSING")
    if work.get("stage_uid") != "STAGE-01":
        raise RuntimeError("STAGE01_EXECUTION_SCANNER_REQUIRES_ACTIVE_STAGE01")
    if scope.get("work_unit_uid") != work.get("work_unit_uid"):
        raise RuntimeError("SCOPE_WORK_UNIT_DRIFT")
    if scope.get("included_units") != work.get("scope"):
        raise RuntimeError("SCOPE_INCLUDED_UNITS_DRIFT")
    root = ROOT / repo_rel(str(work.get("planned_run_root") or ""), "PLANNED_RUN_ROOT")
    return state, work, root


def projection_bindings(work: dict) -> list[dict]:
    adm = work.get("source_projection_admission") or {}
    if adm.get("applicability") != "REQUIRED":
        raise RuntimeError("STAGE01_FROZEN_PROJECTION_REQUIRED")
    rows = adm.get("bindings")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("STAGE01_PROJECTION_BINDING_SET_MISSING")
    return rows


def load_frozen_projection(binding: dict) -> tuple[dict, dict, Path]:
    required = (
        "source_uid",
        "freeze_receipt_ref",
        "pair_hash",
        "raw_source_sha256",
        "projection_uid",
        "projection_content_hash",
    )
    for key in required:
        if not binding.get(key):
            raise RuntimeError("PROJECTION_BINDING_FIELD_MISSING:" + key)

    freeze_path = ROOT / repo_rel(str(binding["freeze_receipt_ref"]), "FREEZE_RECEIPT_REF")
    if not freeze_path.is_file():
        raise RuntimeError("FREEZE_RECEIPT_MISSING:" + str(binding["source_uid"]))
    freeze = load(freeze_path)
    if freeze.get("artifact_type") != "SOURCE_PROJECTION_FREEZE_RECEIPT":
        raise RuntimeError("FREEZE_RECEIPT_TYPE_INVALID")
    if freeze.get("status") != "FROZEN_FOR_STAGE01" or freeze.get("lock_state") != "SOURCE_PAIR_FROZEN":
        raise RuntimeError("SOURCE_PAIR_NOT_FROZEN")
    if freeze.get("raw_source_writable") is not False or freeze.get("projection_writable") is not False:
        raise RuntimeError("SOURCE_PAIR_WRITABLE")
    for key in ("source_uid", "pair_hash", "raw_source_sha256", "projection_uid", "projection_content_hash"):
        if freeze.get(key) != binding.get(key):
            raise RuntimeError("FREEZE_BINDING_DRIFT:" + key)

    projection_path = freeze_path.parent / "CANONICAL_SOURCE_PROJECTION.yaml"
    if not projection_path.is_file():
        raise RuntimeError("CANONICAL_SOURCE_PROJECTION_MISSING")
    projection = load(projection_path)
    if projection.get("artifact_type") != "CANONICAL_SOURCE_PROJECTION":
        raise RuntimeError("CANONICAL_SOURCE_PROJECTION_TYPE_INVALID")
    if projection.get("artifact_uid") != binding.get("projection_uid"):
        raise RuntimeError("PROJECTION_UID_DRIFT")
    if hash_without(projection, "projection_content_hash") != binding.get("projection_content_hash"):
        raise RuntimeError("PROJECTION_CONTENT_HASH_MISMATCH")
    if projection.get("projection_content_hash") != binding.get("projection_content_hash"):
        raise RuntimeError("PROJECTION_DECLARED_HASH_DRIFT")
    sid = projection.get("source_identity") or {}
    if sid.get("source_uid") != binding.get("source_uid") or sid.get("source_sha256") != binding.get("raw_source_sha256"):
        raise RuntimeError("PROJECTION_SOURCE_IDENTITY_DRIFT")
    return freeze, projection, freeze_path.parent


def validate_frozen_binary_parts(projection: dict, frozen_root: Path, failures: list[str]) -> int:
    count = 0
    expected = set()
    for row in projection.get("package_parts") or []:
        part = str(row.get("package_part_path") or "")
        lower = part.lower()
        if lower.endswith(".xml") or lower.endswith(".rels"):
            continue
        digest = str(row.get("part_sha256") or "")
        suffix = Path(part).suffix.lower()
        target = frozen_root / "FROZEN_BINARY_PARTS" / (digest + suffix)
        expected.add(target.name)
        count += 1
        if not target.is_file():
            failures.append("FROZEN_BINARY_MISSING:" + part)
            continue
        if target.stat().st_size != row.get("size_bytes"):
            failures.append("FROZEN_BINARY_SIZE_MISMATCH:" + part)
        if file_sha(target) != digest:
            failures.append("FROZEN_BINARY_HASH_MISMATCH:" + part)
    actual_dir = frozen_root / "FROZEN_BINARY_PARTS"
    actual = {p.name for p in actual_dir.iterdir() if p.is_file()} if actual_dir.is_dir() else set()
    for name in sorted(actual - expected):
        failures.append("FROZEN_BINARY_UNEXPECTED:" + name)
    return count


def validate_workspace(workspace: Path, work: dict) -> dict:
    failures: list[str] = []
    bindings = projection_bindings(work)
    projection_by_source: dict[str, dict] = {}
    node_ids_by_source: dict[str, set[str]] = {}
    binary_count = 0

    for binding in bindings:
        _, projection, frozen_root = load_frozen_projection(binding)
        suid = str(binding["source_uid"])
        nodes = projection.get("source_nodes") or []
        ids = [str(x.get("source_node_uid") or "") for x in nodes if isinstance(x, dict)]
        if not ids or any(not x for x in ids):
            failures.append("PROJECTION_SOURCE_NODE_ID_MISSING:" + suid)
        if len(ids) != len(set(ids)):
            failures.append("PROJECTION_SOURCE_NODE_ID_DUPLICATE:" + suid)
        projection_by_source[suid] = projection
        node_ids_by_source[suid] = set(ids)
        binary_count += validate_frozen_binary_parts(projection, frozen_root, failures)

    if not workspace.is_dir():
        failures.append("STAGE01_WORKSPACE_MISSING:" + workspace.relative_to(ROOT).as_posix())
        return {
            "status": "FAIL",
            "failures": failures,
            "projection_source_node_count": sum(len(x) for x in node_ids_by_source.values()),
            "frozen_binary_part_count": binary_count,
        }

    struct_path = workspace / "00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml"
    seg_path = workspace / "00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml"
    required_files = [
        struct_path,
        seg_path,
        workspace / "00_SOURCE_INTAKE/SOURCE_CONTEXT_MANIFEST.yaml",
        workspace / "00_SOURCE_INTAKE/CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml",
        workspace / "00_SOURCE_INTAKE/SOURCE_DEPENDENCY_MAP.yaml",
    ]
    for path in required_files:
        if not path.is_file():
            failures.append("STAGE01_REQUIRED_OUTPUT_MISSING:" + path.relative_to(workspace).as_posix())
    if failures and (not struct_path.is_file() or not seg_path.is_file()):
        return {
            "status": "FAIL",
            "failures": failures,
            "projection_source_node_count": sum(len(x) for x in node_ids_by_source.values()),
            "frozen_binary_part_count": binary_count,
        }

    struct = load(struct_path)
    sources = {
        str(x.get("source_uid")): x
        for x in (struct.get("sources") or [])
        if isinstance(x, dict) and x.get("source_uid")
    }
    if set(sources) != set(projection_by_source):
        failures.append("SOURCE_STRUCTURE_PROJECTION_SOURCE_SET_MISMATCH")

    projection_to_structure: dict[str, dict[str, list[str]]] = {}
    structure_to_projection: dict[str, dict[str, set[str]]] = {}
    disposition_total = 0
    for suid, expected_ids in node_ids_by_source.items():
        src = sources.get(suid) or {}
        binding = next(x for x in bindings if str(x.get("source_uid")) == suid)
        if src.get("source_projection_uid") != binding.get("projection_uid"):
            failures.append("SOURCE_STRUCTURE_PROJECTION_UID_DRIFT:" + suid)
        if src.get("source_projection_content_hash") != binding.get("projection_content_hash"):
            failures.append("SOURCE_STRUCTURE_PROJECTION_HASH_DRIFT:" + suid)
        if src.get("source_projection_pair_hash") != binding.get("pair_hash"):
            failures.append("SOURCE_STRUCTURE_PAIR_HASH_DRIFT:" + suid)

        rows = src.get("projection_node_dispositions")
        if not isinstance(rows, list):
            failures.append("PROJECTION_DISPOSITION_SET_MISSING:" + suid)
            continue
        seen: set[str] = set()
        projection_to_structure[suid] = {}
        structure_to_projection[suid] = {}
        for row in rows:
            if not isinstance(row, dict):
                failures.append("PROJECTION_DISPOSITION_ROW_INVALID:" + suid)
                continue
            if list(row.keys()) != [
                "projection_source_node_uid",
                "disposition",
                "source_structure_node_uids",
                "evidence_ref",
            ]:
                failures.append("PROJECTION_DISPOSITION_SCHEMA_DRIFT:" + suid)
            uid = str(row.get("projection_source_node_uid") or "")
            if not uid or uid in seen:
                failures.append("PROJECTION_DISPOSITION_DUPLICATE_OR_MISSING:" + uid)
                continue
            seen.add(uid)
            disp = row.get("disposition")
            if disp not in ALLOWED_PROJECTION_DISPOSITIONS:
                failures.append("PROJECTION_DISPOSITION_INVALID:" + uid)
            structure_ids = [str(x) for x in (row.get("source_structure_node_uids") or []) if str(x)]
            if disp == "NON_SEMANTIC_WITH_EVIDENCE":
                ev = str(row.get("evidence_ref") or "")
                if not ev or not (workspace / ev).is_file():
                    failures.append("NON_SEMANTIC_DISPOSITION_EVIDENCE_MISSING:" + uid)
            elif not structure_ids:
                failures.append("PROJECTION_STRUCTURE_LINEAGE_MISSING:" + uid)
            projection_to_structure[suid][uid] = structure_ids
            for sid in structure_ids:
                structure_to_projection[suid].setdefault(sid, set()).add(uid)
        disposition_total += len(seen)
        if seen != expected_ids:
            failures.append(
                "PROJECTION_DISPOSITION_DENOMINATOR_MISMATCH:"
                + suid
                + ":missing="
                + str(len(expected_ids - seen))
                + ":extra="
                + str(len(seen - expected_ids))
            )

    segment_map = load(seg_path)
    segments = segment_map.get("source_segments") or []
    segment_by_uid = {}
    for seg in segments:
        if not isinstance(seg, dict):
            failures.append("SOURCE_SEGMENT_ROW_INVALID")
            continue
        seg_uid = str(seg.get("segment_uid") or "")
        suid = str(seg.get("source_uid") or "")
        structure_uid = str(seg.get("source_node_uid") or "")
        if not seg_uid or seg_uid in segment_by_uid:
            failures.append("SOURCE_SEGMENT_UID_DUPLICATE_OR_MISSING:" + seg_uid)
            continue
        segment_by_uid[seg_uid] = seg
        if suid not in structure_to_projection:
            failures.append("SOURCE_SEGMENT_SOURCE_UNKNOWN:" + seg_uid)
        elif structure_uid not in structure_to_projection[suid]:
            failures.append("SOURCE_SEGMENT_WITHOUT_PROJECTION_LINEAGE:" + seg_uid)

    classified_root = workspace / "01_CLASSIFIED"
    classified_count = 0
    for path in sorted(classified_root.rglob("*.yaml")) if classified_root.is_dir() else []:
        row = load(path)
        classified_count += 1
        for lineage in row.get("source_lineage") or []:
            suid = str(lineage.get("source_uid") or "")
            for seg_uid in lineage.get("source_segment_uids") or []:
                seg = segment_by_uid.get(str(seg_uid))
                if not seg:
                    failures.append("CLASSIFIED_ARTIFACT_UNKNOWN_SEGMENT:" + str(row.get("artifact_uid")))
                    continue
                structure_uid = str(seg.get("source_node_uid") or "")
                if suid not in structure_to_projection or structure_uid not in structure_to_projection[suid]:
                    failures.append("CLASSIFIED_ARTIFACT_WITHOUT_PROJECTION_LINEAGE:" + str(row.get("artifact_uid")))
    if classified_count == 0:
        failures.append("CLASSIFIED_ARTIFACT_SET_EMPTY")

    for rel in (
        "02_BASE_BLUEPRINT",
        "03_BLUEPRINT_BINDING",
    ):
        root = workspace / rel
        if not root.is_dir() or not any(root.rglob("*.yaml")):
            failures.append("STAGE01_OUTPUT_ROOT_EMPTY:" + rel)

    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "projection_source_node_count": sum(len(x) for x in node_ids_by_source.values()),
        "projection_disposition_count": disposition_total,
        "classified_artifact_count": classified_count,
        "frozen_binary_part_count": binary_count,
        "raw_word_accessed": False,
        "raw_docx_reparsed": False,
    }


def synthetic_self_test() -> dict:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        frozen = root / "frozen"
        frozen.mkdir(parents=True)
        binary = b"abc"
        digest = hashlib.sha256(binary).hexdigest()
        (frozen / "FROZEN_BINARY_PARTS").mkdir()
        (frozen / "FROZEN_BINARY_PARTS" / (digest + ".png")).write_bytes(binary)
        nodes = [
            {
                "source_node_uid": "P1",
                "source_node_kind": "TEXT",
                "projection_order_index": 1,
                "document_order_index": 1,
                "package_part_path": "word/document.xml",
                "xml_qname": "w:t",
                "xml_path": "/0",
                "parent_source_node_uid": None,
                "attributes_json": "{}",
                "direct_text": "x",
                "tail_text": "",
                "element_xml_sha256": "0" * 64,
                "node_content_sha256": "0" * 64,
                "projection_status": "PROJECTED",
                "unsupported_reason": None,
            }
        ]
        projection = {
            "artifact_uid": "PROJ-SYNTH",
            "artifact_type": "CANONICAL_SOURCE_PROJECTION",
            "source_identity": {"source_uid": "SRC-SYNTH", "source_sha256": "a" * 64},
            "package_parts": [
                {
                    "package_part_path": "word/media/a.png",
                    "content_type": "image/png",
                    "size_bytes": len(binary),
                    "part_sha256": digest,
                }
            ],
            "source_nodes": nodes,
            "projection_content_hash": None,
        }
        projection["projection_content_hash"] = hash_without(projection, "projection_content_hash")
        (frozen / "CANONICAL_SOURCE_PROJECTION.yaml").write_text(
            yaml.safe_dump(projection, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        freeze = {
            "artifact_type": "SOURCE_PROJECTION_FREEZE_RECEIPT",
            "source_uid": "SRC-SYNTH",
            "pair_hash": "b" * 64,
            "raw_source_sha256": "a" * 64,
            "projection_uid": "PROJ-SYNTH",
            "projection_content_hash": projection["projection_content_hash"],
            "status": "FROZEN_FOR_STAGE01",
            "lock_state": "SOURCE_PAIR_FROZEN",
            "raw_source_writable": False,
            "projection_writable": False,
        }
        (frozen / "SOURCE_PROJECTION_FREEZE_RECEIPT.yaml").write_text(
            yaml.safe_dump(freeze, sort_keys=False), encoding="utf-8"
        )
        workspace = root / "run"
        (workspace / "00_SOURCE_INTAKE/evidence").mkdir(parents=True)
        (workspace / "00_SOURCE_INTAKE/evidence/NONSEM.yaml").write_text("status: PASS\n", encoding="utf-8")
        struct = {
            "sources": [
                {
                    "source_uid": "SRC-SYNTH",
                    "source_projection_uid": "PROJ-SYNTH",
                    "source_projection_content_hash": projection["projection_content_hash"],
                    "source_projection_pair_hash": "b" * 64,
                    "projection_node_dispositions": [
                        {
                            "projection_source_node_uid": "P1",
                            "disposition": "SEMANTIC_SOURCE_NODE",
                            "source_structure_node_uids": ["N1"],
                            "evidence_ref": None,
                        }
                    ],
                }
            ]
        }
        (workspace / "00_SOURCE_INTAKE").mkdir(exist_ok=True)
        (workspace / "00_SOURCE_INTAKE/SOURCE_STRUCTURE_MANIFEST.yaml").write_text(yaml.safe_dump(struct, sort_keys=False), encoding="utf-8")
        seg = {"source_segments": [{"segment_uid": "S1", "source_uid": "SRC-SYNTH", "source_node_uid": "N1"}]}
        (workspace / "00_SOURCE_INTAKE/SOURCE_SEGMENT_MAP.yaml").write_text(yaml.safe_dump(seg, sort_keys=False), encoding="utf-8")
        for name, atype in (
            ("SOURCE_CONTEXT_MANIFEST.yaml", "SOURCE_CONTEXT_MANIFEST"),
            ("CONTENT_SUPERSESSION_CONFLICT_LEDGER.yaml", "CONTENT_SUPERSESSION_CONFLICT_LEDGER"),
            ("SOURCE_DEPENDENCY_MAP.yaml", "SOURCE_DEPENDENCY_MAP"),
        ):
            (workspace / "00_SOURCE_INTAKE" / name).write_text(yaml.safe_dump({"artifact_type": atype}), encoding="utf-8")
        (workspace / "01_CLASSIFIED").mkdir()
        artifact = {
            "artifact_uid": "A1",
            "source_lineage": [{"source_uid": "SRC-SYNTH", "source_segment_uids": ["S1"]}],
        }
        (workspace / "01_CLASSIFIED/A1.yaml").write_text(yaml.safe_dump(artifact, sort_keys=False), encoding="utf-8")
        (workspace / "02_BASE_BLUEPRINT").mkdir()
        (workspace / "02_BASE_BLUEPRINT/B.yaml").write_text("blueprint_uid: B1\n", encoding="utf-8")
        (workspace / "03_BLUEPRINT_BINDING").mkdir()
        (workspace / "03_BLUEPRINT_BINDING/X.yaml").write_text("binding_uid: X1\n", encoding="utf-8")

        original_root = globals()["ROOT"]
        try:
            globals()["ROOT"] = root
            binding = {
                "source_uid": "SRC-SYNTH",
                "freeze_receipt_ref": "frozen/SOURCE_PROJECTION_FREEZE_RECEIPT.yaml",
                "pair_hash": "b" * 64,
                "raw_source_sha256": "a" * 64,
                "projection_uid": "PROJ-SYNTH",
                "projection_content_hash": projection["projection_content_hash"],
            }
            work = {"source_projection_admission": {"applicability": "REQUIRED", "bindings": [binding]}}
            result = validate_workspace(workspace, work)
        finally:
            globals()["ROOT"] = original_root
        if result["status"] != "PASS":
            raise RuntimeError("STAGE01_FROZEN_PROJECTION_SCANNER_SELF_TEST_FAILED:" + json.dumps(result))
        return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        out = synthetic_self_test()
        print(json.dumps({"result": "PASS", "scanner_result": out}, ensure_ascii=False, indent=2))
        return
    _, work, default_workspace = resolve_current()
    workspace = Path(args.workspace).resolve() if args.workspace else default_workspace
    out = validate_workspace(workspace, work)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
