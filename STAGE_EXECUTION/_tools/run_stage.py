#!/usr/bin/env python3
"""Fixed-pattern stage runner for every governed-unit page.

Encodes the cross-stage handoff fix as a deterministic, repeatable procedure:

  1. Ensure the CURRENT stage Work Unit exists (materialize it if absent).
  2. Ensure the SUCCESSOR stage Work Unit exists BEFORE running the current
     stage. The lifecycle orchestrator's `_materialize_cross_stage_handoff`
     resolves the successor's required input bindings from the successor Work
     Unit, so a missing successor blocks the current stage from reaching
     CLOSED_PASS (CROSS_STAGE_HANDOFF_INPUT_BINDING_UNRESOLVED).
  3. Invoke the authoritative orchestrator `--run-stage`.

Both scaffold materializations use the single canonical generator
`materialize_stage_work_unit.py`, driven by the master plan and the stage spec,
so every page and every stage follows the exact same pattern.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
GENERATOR = HERE / 'materialize_stage_work_unit.py'
DEFAULT_PLAN = Path('.github/governance-source/active/source/10_REGISTRY/STAGE_EXECUTION_MASTER_PLAN.yaml')
DEFAULT_ORCH = Path('/tmp/opencode/rebuild-v2.1.1/governance/ci/stage_lifecycle_orchestrator.py')


def stage_index(plan_path: Path) -> dict:
    with plan_path.open(encoding='utf-8') as fh:
        doc = yaml.safe_load(fh)
    raw = doc.get('stages')
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list):
        return {str(s.get('stage_uid')): s for s in raw if isinstance(s, dict) and s.get('stage_uid')}
    raise SystemExit('MASTER_PLAN_STAGES_UNRESOLVED')


def work_unit_path(root: Path, stage_uid: str, governed: str) -> Path:
    stage_dir = root / 'STAGE_EXECUTION' / stage_uid
    if stage_dir.is_dir():
        for d in sorted(stage_dir.iterdir()):
            if not d.is_dir() or d.name.startswith('_'):
                continue
            w = d / 'WORK_UNIT.yaml'
            if not w.is_file():
                continue
            try:
                wd = yaml.safe_load(w.read_text(encoding='utf-8')) or {}
            except yaml.YAMLError:
                continue
            if str(wd.get('stage_uid')) == stage_uid and str(wd.get('governed_unit_uid')) == governed:
                return w
    return None


def ensure_work_unit(root: Path, plan: Path, stage_uid: str, governed: str,
                     allow_pending: bool = False) -> Path:
    existing = work_unit_path(root, stage_uid, governed)
    if existing is not None:
        return existing
    cmd = [sys.executable, str(GENERATOR), '--stage', stage_uid,
           '--governed-unit', governed, '--product-root', str(root),
           '--master-plan', str(plan)]
    if allow_pending:
        cmd.append('--allow-pending-inputs')
    print(f'[run_stage] materializing {stage_uid} work unit for {governed}')
    subprocess.run(cmd, check=True)
    created = work_unit_path(root, stage_uid, governed)
    if created is None:
        raise SystemExit(f'WORK_UNIT_MATERIALIZATION_FAILED:{stage_uid}')
    return created


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--stage', required=True)
    p.add_argument('--governed-unit', required=True)
    p.add_argument('--product-root', default=str(REPO_ROOT))
    p.add_argument('--master-plan', default=None)
    p.add_argument('--orchestrator', default=str(DEFAULT_ORCH))
    a = p.parse_args()

    root = Path(a.product_root).resolve()
    plan = Path(a.master_plan) if a.master_plan else root / DEFAULT_PLAN
    stages = stage_index(plan)
    if a.stage not in stages:
        raise SystemExit(f'UNKNOWN_STAGE:{a.stage}')
    st = stages[a.stage]

    current = ensure_work_unit(root, plan, a.stage, a.governed_unit)

    next_stage = str(st.get('next_stage_uid') or '')
    if next_stage and next_stage in stages:
        # The successor's declared inputs are produced by the CURRENT stage (still
        # unexecuted here), so its bindings are allowed to be producer-pending;
        # the orchestrator refreshes them from the cross-stage handoff at closure.
        ensure_work_unit(root, plan, next_stage, a.governed_unit, allow_pending=True)

    orch = Path(a.orchestrator)
    if not orch.is_file():
        raise SystemExit(f'ORCHESTRATOR_MISSING:{orch}')
    rel = current.relative_to(root)
    cmd = [sys.executable, str(orch), '--run-stage', '--stage', a.stage,
           '--work-unit', str(rel), '--product-root', str(root)]
    print(f'[run_stage] orchestrating {a.stage} ({rel})')
    raise SystemExit(subprocess.run(cmd).returncode)


if __name__ == '__main__':
    main()
