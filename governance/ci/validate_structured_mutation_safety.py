#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
from validate_active_consumer_reference_integrity import (
    python_executable_refs,
    workflow_executable_refs,
)

class MutationSafetyError(RuntimeError):
    pass

def _assigned_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        out=set()
        for elt in node.elts:
            out.update(_assigned_names(elt))
        return out
    return set()

def _is_read_text_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "read_text"

def fragile_mutation_violations(source: str, label: str = "<memory>") -> list[str]:
    try:
        tree=ast.parse(source)
    except SyntaxError as exc:
        return [f"PYTHON_PARSE_ERROR:{label}:{exc.lineno}:{exc.msg}"]
    read_vars=set()
    has_write=False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value=node.value
            if _is_read_text_call(value):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                for target in targets:
                    read_vars.update(_assigned_names(target))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="write_text":
            has_write=True
    if not has_write or not read_vars:
        return []
    violations=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
            if isinstance(node.func.value,ast.Name) and node.func.value.id in read_vars and node.func.attr in {"replace","count"}:
                violations.append(f"UNBOUNDED_RAW_TEXT_{node.func.attr.upper()}:{label}:line={getattr(node,'lineno',0)}:var={node.func.value.id}")
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
            if isinstance(node.func.value,ast.Name) and node.func.value.id=="re" and node.func.attr in {"sub","subn"}:
                for arg in node.args:
                    if isinstance(arg,ast.Name) and arg.id in read_vars:
                        violations.append(f"UNBOUNDED_RAW_TEXT_REGEX_MUTATION:{label}:line={getattr(node,'lineno',0)}:var={arg.id}")
    return sorted(set(violations))

def active_reachable_python() -> tuple[set[str], dict[str,set[str]], list[str]]:
    refs=defaultdict(set)
    q=deque()
    errors=[]
    workflows=sorted([*WORKFLOW_ROOT.glob("*.yml"),*WORKFLOW_ROOT.glob("*.yaml")])
    for wf in workflows:
        text=wf.read_text(encoding="utf-8")
        for rel in workflow_executable_refs(text):
            refs[rel].add(wf.relative_to(ROOT).as_posix())
            q.append(rel)
    seen=set()
    while q:
        rel=q.popleft()
        if rel in seen:
            continue
        seen.add(rel)
        p=ROOT/rel
        if not p.is_file():
            errors.append(f"MISSING_ACTIVE_EXECUTABLE:{rel}<-{','.join(sorted(refs[rel]))}")
            continue
        text=p.read_text(encoding="utf-8")
        for child in python_executable_refs(text):
            refs[child].add(rel)
            if child not in seen:
                q.append(child)
    return seen,refs,errors

def run_self_test() -> int:
    fragile="""from pathlib import Path
p=Path('state.yaml')
body=p.read_text()
if body.count('authorization_uid') != 1:
    raise RuntimeError('drift')
p.write_text(body.replace('authorization_uid','authorization_uid_new'))
"""
    safe="""from pathlib import Path
import yaml
p=Path('state.yaml')
data=yaml.safe_load(p.read_text()) or {}
data['authorization_uid']='new'
p.write_text(yaml.safe_dump(data))
"""
    if not fragile_mutation_violations(fragile,"fragile.py"):
        print("FAIL: fragile raw-text mutation escaped",file=sys.stderr); return 1
    if fragile_mutation_violations(safe,"safe.py"):
        print("FAIL: structured YAML mutation falsely blocked",file=sys.stderr); return 1
    sample="python .github/governance-maintenance/missing.py"
    if ".github/governance-maintenance/missing.py" not in workflow_executable_refs(sample):
        print("FAIL: governance-maintenance workflow executable ref escaped",file=sys.stderr); return 1
    fixture="""sample = 'python .github/governance-maintenance/missing.py'\nprint(sample)\n"""
    if python_executable_refs(fixture):
        print("FAIL: non-executed Python fixture contaminated executable graph",file=sys.stderr); return 1
    print("PASS: structured mutation safety negative regression 4/4")
    return 0

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        return run_self_test()
    reachable,refs,errors=active_reachable_python()
    violations=[]
    for rel in sorted(reachable):
        p=ROOT/rel
        if not p.is_file():
            continue
        source=p.read_text(encoding="utf-8")
        violations.extend(fragile_mutation_violations(source,rel))
    errors.extend(violations)
    if errors:
        for x in errors:
            print("BLOCK:",x,file=sys.stderr)
        return 1
    print(f"PASS: structured mutation safety active_reachable_python={len(reachable)}")
    print("PASS: no active reachable structured mutator uses unbounded read_text raw replace/count/regex mutation")
    print("PASS: governance-maintenance executable paths are part of active reachability")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
