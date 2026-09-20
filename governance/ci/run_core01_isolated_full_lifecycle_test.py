#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import yaml

STAGES = [
    ("STAGE-01", "SOURCE_INTAKE"),
    ("STAGE-02", "PAGE_FUNCTIONAL_CONTRACT"),
    ("STAGE-03", "VISUAL_DESIGN"),
    ("STAGE-04", "FOUNDATION_FREEZE"),
    ("STAGE-05", "IMPLEMENTATION"),
    ("STAGE-06", "VERIFICATION_QA"),
    ("STAGE-07", "BUILD_RELEASE_CANDIDATE"),
    ("STAGE-08", "STAGING"),
    ("STAGE-09", "PRODUCTION_CUTOVER_FAIL_CLOSED_CONTRACT"),
    ("STAGE-10", "PRODUCTION_ACCEPTANCE_FAIL_CLOSED_CONTRACT"),
    ("STAGE-11", "CLOSURE_OPERATIONS"),
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def run(cmd, cwd: Path, env=None, expect=0, label="command", timeout=1800):
    merged = os.environ.copy()
    if env:
        merged.update({k: str(v) for k, v in env.items()})
    print("RUN", label, "::", " ".join(cmd), flush=True)
    p = subprocess.Popen(cmd, cwd=cwd, env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
    lines = []
    started = time.time()
    try:
        assert p.stdout is not None
        for line in p.stdout:
            print(line, end="", flush=True)
            lines.append(line)
            if len(lines) > 4000:
                lines = lines[-4000:]
            if time.time() - started > timeout:
                p.kill()
                raise RuntimeError(label + "_TIMEOUT")
        rc = p.wait()
    finally:
        if p.poll() is None:
            p.kill()
    if rc != expect:
        raise RuntimeError(label + "_EXIT_" + str(rc) + "_EXPECTED_" + str(expect))
    return "".join(lines)

def run_capture(cmd, cwd: Path, env=None, timeout=180):
    merged = os.environ.copy()
    if env:
        merged.update({k: str(v) for k, v in env.items()})
    p = subprocess.run(cmd, cwd=cwd, env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    print(p.stdout, end="", flush=True)
    return p.returncode, p.stdout

def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)

def unique(rows, key):
    vals = [str(x.get(key)) for x in rows if isinstance(x, dict)]
    return len(vals) == len(set(vals)) and all(v not in ("", "None") for v in vals)

AUTHORIZED_PATCH_REL = "tests/release/authority.test.mjs"
AUTHORIZED_PATCH_BLOB = "a91ab5d3300d92799abaf8cef0a6790317127c09"

def tracked_clean(root: Path):
    out = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True)
    lines = [line for line in out.splitlines() if line.strip()]
    unexpected = [line for line in lines if not line.endswith(" " + AUTHORIZED_PATCH_REL)]
    require(not unexpected, "TRACKED_SOURCE_MUTATED:" + "|".join(unexpected))
    if lines:
        require(len(lines) == 1 and lines[0].endswith(" " + AUTHORIZED_PATCH_REL), "AUTHORIZED_PATCH_WRITESET_DRIFT:" + "|".join(lines))
        actual = subprocess.check_output(["git", "hash-object", AUTHORIZED_PATCH_REL], cwd=root, text=True).strip()
        require(actual == AUTHORIZED_PATCH_BLOB, "AUTHORIZED_PATCH_BLOB_DRIFT:" + actual)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox-root", required=True)
    ap.add_argument("--product-root", required=True)
    ap.add_argument("--source-head", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--content-report", required=True)
    args = ap.parse_args()

    sandbox = Path(args.sandbox_root).resolve()
    product = Path(args.product_root).resolve()
    report_path = Path(args.report).resolve()
    content_report_path = Path(args.content_report).resolve()
    receipts = sandbox / "stage-receipts"
    receipts.mkdir(parents=True, exist_ok=True)

    report = {
        "artifact_type": "NON_NORMATIVE_CORE01_ISOLATED_FULL_LIFECYCLE_EXECUTION_REPORT",
        "page_uid": "CORE-01",
        "source_provider_head": args.source_head,
        "stage_denominator": 11,
        "stages": [],
        "product_stage_credit": 0,
        "formal_production_deployment_performed": False,
        "formal_production_database_migration_performed": False,
        "formal_production_acceptance_credit": 0,
        "sandbox_root": str(sandbox),
        "sandbox_cleanup_performed_by_workflow_after_report": True,
        "result": "IN_PROGRESS",
    }
    predecessor_hash = None
    freeze = {}

    def stage(uid, name, fn):
        nonlocal predecessor_hash, freeze
        idx = len(report["stages"]) + 1
        expected_uid, expected_name = STAGES[idx - 1]
        require(uid == expected_uid and name == expected_name, "STAGE_ORDER_DRIFT")
        if idx > 1:
            require(predecessor_hash is not None, uid + "_PREDECESSOR_RECEIPT_MISSING")
        started = time.time()
        row = {
            "stage_uid": uid,
            "stage_name": name,
            "ordinal": idx,
            "predecessor_receipt_sha256": predecessor_hash,
            "status": "RUNNING",
            "product_credit": 0,
        }
        report["stages"].append(row)
        try:
            diagnostic_only = report.get("lifecycle_blocked_at") is not None
            detail = fn() or {}
            special_status = detail.pop("_stage_status", None) if isinstance(detail, dict) else None
            row["detail"] = detail
            if special_status == "BLOCKED":
                row["status"] = "BLOCKED"
                report.setdefault("lifecycle_blocked_at", uid)
                for finding in detail.get("findings", []) if isinstance(detail, dict) else []:
                    report.setdefault("findings", []).append(finding)
            elif diagnostic_only:
                row["status"] = "PASS_DIAGNOSTIC_ONLY"
                row["diagnostic_only_due_to_predecessor_block"] = True
            else:
                row["status"] = "PASS"
        except Exception as exc:
            row["status"] = "BLOCKED"
            row["error"] = str(exc)
            report["result"] = "BLOCKED"
            report["blocked_stage_uid"] = uid
            write_json(report_path, report)
            receipt = receipts / (uid + ".json")
            write_json(receipt, row)
            print("BLOCK", uid, str(exc), flush=True)
            raise
        row["duration_seconds"] = round(time.time() - started, 3)
        receipt = receipts / (uid + ".json")
        write_json(receipt, row)
        predecessor_hash = sha256(receipt)
        row["receipt_sha256"] = predecessor_hash
        write_json(report_path, report)
        print(row["status"], uid, name, "receipt_sha256=" + predecessor_hash, flush=True)

    authority_file = product / "authority/pages/workspace/CORE-01/CORE_PAGE_VISUAL_AUTHORITY_FINAL_SCRIPT_CONTENT_CLOSED.yaml"
    visual_file = product / "authority/pages/workspace/CORE-01/CORE_CURRENT_CANONICAL_VISUAL_FINAL_LOCKED_V1.0.yaml"
    core_visual = product / "src/components/pages/CoreVisual.tsx"
    core_css = product / "src/components/pages/CoreVisual.module.css"
    production_runtime = product / "src/server/core/productionCoreGovernedRuntime.ts"
    test_runtime = product / "src/server/testing/controlledCoreTestRuntime.ts"
    runtime_contract = product / "src/domain/core/coreRuntimeContract.ts"

    def s1():
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=product, text=True).strip()
        require(head == args.source_head, "SOURCE_PROVIDER_HEAD_MISMATCH:" + head)
        tracked_clean(product)
        for p in (authority_file, visual_file, core_visual, production_runtime, test_runtime, runtime_contract):
            require(p.is_file(), "SOURCE_REQUIRED_FILE_MISSING:" + str(p.relative_to(product)))
        authority = yaml.safe_load(authority_file.read_text(encoding="utf-8")) or {}
        meta = authority.get("authority") or {}
        require(meta.get("page_uid") == "CORE-01", "SOURCE_PAGE_UID_MISMATCH")
        require(meta.get("status") == "FINAL_LOCKED", "SOURCE_AUTHORITY_NOT_FINAL_LOCKED")
        require(meta.get("current_only") is True, "SOURCE_AUTHORITY_NOT_CURRENT_ONLY")
        require(str(meta.get("route")) == "/core", "SOURCE_ROUTE_MISMATCH")
        require("BLOCK" in str(meta.get("undefined_behavior")), "SOURCE_UNDEFINED_BEHAVIOR_NOT_FAIL_CLOSED")
        return {
            "source_head": head,
            "authority_sha256": sha256(authority_file),
            "visual_sha256": sha256(visual_file),
            "source_classification": "TEST_ONLY_SOURCE_PROVIDER_WITH_AUTHORIZED_SANDBOX_TEST_PATCH",
            "authorized_test_patch": {
                "path": AUTHORIZED_PATCH_REL,
                "postimage_blob_sha1": AUTHORIZED_PATCH_BLOB,
            },
        }

    def s2():
        authority = yaml.safe_load(authority_file.read_text(encoding="utf-8")) or {}
        regs = authority.get("registries") or {}
        sections = regs.get("sections") or []
        visuals = regs.get("visuals") or []
        components = regs.get("components") or []
        permissions = regs.get("permissions") or []
        gates = regs.get("gates") or []
        errors = regs.get("errors") or []
        require(len(sections) >= 10, "FUNCTIONAL_SECTION_DENOMINATOR_UNDERFLOW")
        require(len(components) >= 10, "FUNCTIONAL_COMPONENT_DENOMINATOR_UNDERFLOW")
        require(len(permissions) >= 10, "FUNCTIONAL_PERMISSION_DENOMINATOR_UNDERFLOW")
        require(len(gates) >= 20, "FUNCTIONAL_GATE_DENOMINATOR_UNDERFLOW")
        require(len(errors) >= 10, "FUNCTIONAL_ERROR_DENOMINATOR_UNDERFLOW")
        require(unique(sections, "section_uid"), "DUPLICATE_OR_EMPTY_SECTION_UID")
        require(unique(visuals, "visual_uid"), "DUPLICATE_OR_EMPTY_VISUAL_UID")
        require(unique(components, "component_uid"), "DUPLICATE_OR_EMPTY_COMPONENT_UID")
        require(unique(permissions, "permission_uid"), "DUPLICATE_OR_EMPTY_PERMISSION_UID")
        require(unique(gates, "gate_uid"), "DUPLICATE_OR_EMPTY_GATE_UID")
        require(unique(errors, "error_uid"), "DUPLICATE_OR_EMPTY_ERROR_UID")
        section_ids = {str(x.get("section_uid")) for x in sections}
        visual_ids = {str(x.get("visual_uid")) for x in visuals}
        for row in sections:
            require(str(row.get("visual_uid")) in visual_ids, "SECTION_VISUAL_BINDING_MISSING:" + str(row.get("section_uid")))
        for row in components:
            require(str(row.get("section_uid")) in section_ids, "COMPONENT_SECTION_BINDING_MISSING:" + str(row.get("component_uid")))
        text = authority_file.read_text(encoding="utf-8")
        for token in ("CORE_PROJECT_WRITE", "CORE_CONVERSATION", "CORE_LOCK_REQUEST", "CORE-01-GATE-MESSAGE", "CORE-01-ERR-PERM-001"):
            require(token in text, "FUNCTIONAL_AUTHORITY_TOKEN_MISSING:" + token)
        validator = Path(__file__).with_name("validate_core01_source_content_integrity.py")
        content_rc, _ = run_capture(
            [sys.executable, str(validator), "--product-root", str(product), "--report", str(content_report_path)],
            product,
            timeout=300,
        )
        require(content_report_path.is_file(), "CONTENT_INTEGRITY_REPORT_NOT_MATERIALIZED")
        content_result = json.loads(content_report_path.read_text(encoding="utf-8"))
        detail = {
            "sections": len(sections),
            "visuals": len(visuals),
            "components": len(components),
            "permissions": len(permissions),
            "gates": len(gates),
            "errors": len(errors),
            "referential_integrity": "PASS",
            "content_integrity": {
                "result": content_result.get("result"),
                "content_complete": content_result.get("content_complete"),
                "check_total": content_result.get("check_total"),
                "pass_total": content_result.get("pass_total"),
                "blocker_total": content_result.get("blocker_total"),
                "content_denominators": content_result.get("content_denominators"),
                "bidirectional_set_differences": content_result.get("bidirectional_set_differences"),
            },
            "findings": content_result.get("findings") or [],
        }
        if content_rc != 0 or content_result.get("content_complete") is not True:
            detail["_stage_status"] = "BLOCKED"
        return detail

    def s3():
        authority = yaml.safe_load(authority_file.read_text(encoding="utf-8")) or {}
        meta = authority.get("authority") or {}
        code = core_visual.read_text(encoding="utf-8")
        css = core_css.read_text(encoding="utf-8")
        visual = yaml.safe_load(visual_file.read_text(encoding="utf-8")) or {}
        require(meta.get("global_shell") == "GLOBAL_HOME_SHELL_TEMPLATE_AUTHORITY@V1.9", "GLOBAL_SHELL_REF_DRIFT")
        require(meta.get("global_visual") == "GLOBAL_WEB_VISUAL_SYSTEM_AUTHORITY@V1.0", "GLOBAL_VISUAL_REF_DRIFT")
        for token in ("CORE-01", "workspace-three-column", "data-page-uid", "data-runtime-binding", "data-control-id", 'role="dialog"', "visibleThreads", "conversation_id"):
            require(token in code, "VISUAL_IMPLEMENTATION_BINDING_MISSING:" + token)
        require("grid" in css.lower(), "VISUAL_GRID_CSS_MISSING")
        require(bool(visual), "CANONICAL_VISUAL_EMPTY")
        return {
            "authority_visual_ref": meta.get("global_visual"),
            "authority_shell_ref": meta.get("global_shell"),
            "core_visual_sha256": sha256(core_visual),
            "core_css_sha256": sha256(core_css),
            "visual_authority_sha256": sha256(visual_file),
            "static_binding": "PASS",
        }

    def s4():
        nonlocal freeze
        frozen_paths = [
            product / "authority/ACPOS_CURRENT_AUTHORITY_MANIFEST_FINAL_LOCKED.yaml",
            authority_file, visual_file, core_visual, core_css,
            product / "src/app/core/page.tsx",
            product / "src/server/core/coreRouteFactory.ts",
            product / "src/server/core/coreRuntime.ts",
            production_runtime, test_runtime, runtime_contract,
            product / "src/server/shared/identityPageCommandRuntime.ts",
            product / "03_api/operation_registry.yaml",
            product / "06_permission/account_permission_catalog.yaml",
            product / "database/migrations/0037_core_governed_runtime_permission_rls_closure.sql",
            product / "database/migrations/0038_core_conversation_thread_work_item_lineage.sql",
            product / "database/migrations/0047_canonical_script_version_runtime.sql",
            product / "tests/release/authority.test.mjs",
            product / "tests/release/core-governed-runtime-closure.test.mjs",
            product / "tests/release/core-lock-request-ui-runtime.test.mjs",
            product / "tests/release/canonical-script-version-runtime.test.mjs",
            product / "tests/release/lock-request-canonical-runtime.test.mjs",
        ]
        for route in sorted((product / "src/app/v1").rglob("route.ts")):
            source = route.read_text(encoding="utf-8")
            if "CORE-01-PORT-" in source or "getUiProjection" in source:
                frozen_paths.append(route)
        for p in frozen_paths:
            require(p.is_file(), "FOUNDATION_FREEZE_FILE_MISSING:" + str(p.relative_to(product)))
        freeze = {str(p.relative_to(product)): sha256(p) for p in frozen_paths}
        require(len(freeze) == len(frozen_paths), "FOUNDATION_FREEZE_DENOMINATOR_DRIFT")
        write_json(sandbox / "foundation-freeze.json", freeze)
        return {"frozen_file_count": len(freeze), "freeze_manifest_sha256": sha256(sandbox / "foundation-freeze.json")}

    def s5():
        run(["npm", "ci"], product, label="stage05_npm_ci")
        run(["npm", "run", "lint"], product, label="stage05_lint")
        run(["npm", "run", "typecheck"], product, label="stage05_typecheck")
        run(["node", "--test", "tests/release/core-governed-runtime-closure.test.mjs", "tests/release/core-lock-request-ui-runtime.test.mjs"], product, label="stage05_core_runtime_tests")
        tracked_clean(product)
        return {"lint": "PASS", "typecheck": "PASS", "core_runtime_tests": "PASS", "tracked_source_clean": True}

    def s6():
        full_rc, full_out = run_capture(["npm", "test"], product, timeout=900)
        findings = []
        if full_rc != 0:
            findings.append({
                "finding_uid": "CORE01-R2-STAGE06-RELEASE-SUITE",
                "category": "RELEASE_TEST_SUITE_FAILURE",
                "detail": "npm test returned non-zero after the denominator parser fix; Stage-06 remains blocked.",
                "return_code": full_rc,
                "tail": full_out[-4000:],
            })
        run(["npm", "audit", "--audit-level=high"], product, label="stage06_npm_audit")
        env = {"NEXT_PUBLIC_ACPOS_RUNTIME_MODE": "CONTROLLED_TEST"}
        run(["npm", "run", "build"], product, env=env, label="stage06_controlled_build")
        run(["npm", "install", "--no-save", "--package-lock=false", "playwright@1.62.1"], product, label="stage06_playwright_package")
        run(["npx", "playwright", "install", "--with-deps", "chromium"], product, label="stage06_playwright_chromium")
        browser_out = run(["npm", "run", "test:browser"], product, env=env, label="stage06_browser_e2e")
        controls_out = run(["npm", "run", "test:controls"], product, env=env, label="stage06_control_acceptance")
        tracked_clean(product)
        detail = {
            "release_tests": "PASS" if full_rc == 0 else "BLOCKED",
            "security_audit": "PASS",
            "browser_e2e": "PASS",
            "control_acceptance": "PASS",
            "browser_summary": next((line for line in browser_out.splitlines() if "RELEASE_BROWSER_E2E_PASS" in line), None),
            "control_summary": next((line for line in controls_out.splitlines() if "CONTROL_ACCEPTANCE_PASS" in line), None),
            "full_release_test_return_code": full_rc,
            "findings": findings,
        }
        if findings:
            detail["_stage_status"] = "BLOCKED"
        return detail

    def s7():
        shutil.rmtree(product / ".next", ignore_errors=True)
        run(["npm", "run", "build"], product, label="stage07_production_build")
        image = "acpos-core01-isolated-" + args.source_head[:12]
        run(["docker", "build", "-t", image, "."], product, label="stage07_standalone_docker_build", timeout=2400)
        return {"production_build": "PASS", "standalone_docker_build": "PASS", "image_tag": image}

    def s8():
        env = {"ACPOS_E2E_SKIP_BUILD": "1", "ACPOS_EXPECT_READY": "0"}
        run(["npm", "run", "test:e2e"], product, env=env, label="stage08_isolated_staging_http_e2e")
        return {"isolated_staging_http_e2e": "PASS", "formal_remote_staging": False}

    def s9():
        shutil.rmtree(product / ".next", ignore_errors=True)
        env_build = {"NEXT_PUBLIC_ACPOS_RUNTIME_MODE": "CONTROLLED_TEST"}
        run(["npm", "run", "build"], product, env=env_build, label="stage09_controlled_production_build")
        env = {
            "ACPOS_DEPLOYMENT_ENV": "production",
            "ACPOS_E2E_SKIP_BUILD": "1",
            "ACPOS_E2E_RUNTIME_MODE": "CONTROLLED_TEST",
            "ACPOS_EXPECT_CONTROLLED_BLOCK": "1",
        }
        run(["npm", "run", "test:e2e"], product, env=env, label="stage09_controlled_mode_production_fail_closed")
        return {
            "production_cutover_contract": "PASS_EXPECTED_FAIL_CLOSED",
            "controlled_test_not_production_ready": True,
            "formal_production_deployment_performed": False,
        }

    def s10():
        scripts = [
            "scripts/production-formal-readonly-acceptance.mjs",
            "scripts/post-deploy-auth-e2e.mjs",
            "scripts/post-deploy-control-acceptance.mjs",
        ]
        for p in scripts:
            run(["node", "--check", p], product, label="stage10_syntax_" + Path(p).name)
        base_env = {
            "ACPOS_PRODUCTION_E2E_EMAIL": "",
            "ACPOS_PRODUCTION_E2E_PASSWORD": "",
            "ACPOS_ACCEPTANCE_ROUTE_DECISION_ID": "",
            "ACPOS_DEPLOYMENT_URL": "http://127.0.0.1:9",
        }
        rc, out = run_capture(["node", "scripts/production-formal-readonly-acceptance.mjs"], product, env=base_env)
        require(rc != 0 and "FORMAL_READONLY_ACCEPTANCE_CREDENTIAL_NOT_CONFIGURED" in out, "FORMAL_ACCEPTANCE_DID_NOT_FAIL_CLOSED_WITHOUT_EVIDENCE")
        rc2, out2 = run_capture(["node", "scripts/post-deploy-control-acceptance.mjs"], product, env=base_env)
        require(rc2 != 0 and "POST_DEPLOY_CONTROL_ACCEPTANCE_CREDENTIAL_NOT_CONFIGURED" in out2, "CONTROL_ACCEPTANCE_DID_NOT_FAIL_CLOSED_WITHOUT_CREDENTIALS")
        rc3, out3 = run_capture(["node", "scripts/post-deploy-auth-e2e.mjs"], product, env=base_env)
        require(rc3 == 0 and "POST_DEPLOY_AUTH_E2E_BLOCKED" in out3, "AUTH_ACCEPTANCE_MISSING_BLOCKED_RECEIPT")
        return {
            "formal_production_acceptance": "BLOCKED_AS_REQUIRED",
            "credentials_and_route_evidence_missing": True,
            "formal_production_acceptance_credit": 0,
            "production_effectful_execution": False,
        }

    def s11():
        require(len(report["stages"]) == 11, "STAGE_DENOMINATOR_NOT_11")
        for rel, expected in freeze.items():
            p = product / rel
            require(p.is_file(), "FROZEN_FILE_DISAPPEARED:" + rel)
            require(sha256(p) == expected, "FROZEN_SOURCE_HASH_DRIFT:" + rel)
        tracked_clean(product)
        require((sandbox / "stage-receipts/STAGE-10.json").is_file(), "STAGE10_RECEIPT_MISSING")
        require(content_report_path.is_file(), "CONTENT_INTEGRITY_REPORT_MISSING_AT_CLOSURE")
        content_result = json.loads(content_report_path.read_text(encoding="utf-8"))
        return {
            "pre_cleanup_stage_receipts_present": 10,
            "frozen_source_hashes_unchanged": len(freeze),
            "tracked_source_clean": True,
            "content_integrity_result": content_result.get("result"),
            "content_complete": content_result.get("content_complete"),
            "content_blocker_total": content_result.get("blocker_total"),
            "content_denominators": content_result.get("content_denominators"),
            "cleanup_required_after_report": True,
            "formal_production_deployment_performed": False,
            "product_stage_credit": 0,
        }

    funcs = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11]
    try:
        for (uid, name), fn in zip(STAGES, funcs):
            stage(uid, name, fn)
        require(len(report["stages"]) == 11, "FINAL_STAGE_DENOMINATOR_DRIFT")
        report["all_11_stage_receipts"] = True
        report["final_receipt_sha256"] = predecessor_hash
        report["product_stage_credit"] = 0
        if report.get("lifecycle_blocked_at"):
            report["result"] = "BLOCKED_WITH_FULL_DIAGNOSTIC_CONTINUATION"
            report["all_stage_pass"] = False
        else:
            report["result"] = "PASS_PRE_CLEANUP"
            report["all_stage_pass"] = True
        write_json(report_path, report)
        print(json.dumps({
            "result": report["result"],
            "stage_denominator": len(report["stages"]),
            "all_stage_pass": report["all_stage_pass"],
            "lifecycle_blocked_at": report.get("lifecycle_blocked_at"),
            "finding_total": len(report.get("findings", [])),
            "formal_production_deployment_performed": False,
            "product_stage_credit": 0,
        }, indent=2), flush=True)
        if report.get("lifecycle_blocked_at"):
            raise SystemExit(2)
    except Exception:
        write_json(report_path, report)
        raise

if __name__ == "__main__":
    main()
