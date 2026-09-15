#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "governance/ci/run_current_stage2_actual_test.py"

OLD = """        err = action.get('error_uid')
        if err:
            if err not in errors:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'ACTION_ERROR_REF_MISSING', aid, str(err))
            elif not errors[err].get('recovery'):
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RECOVERY_CONTRACT_MISSING', aid, str(err))
        elif not any((transitions.get(tid) or {}).get('recovery') for tid in transitions_by_action.get(aid, [])):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FAILURE_STATE_ERROR_BINDING_MISSING', aid, 'no exact action->error/recovery or transition recovery binding')

        explicit_trigger = present(action, 'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') or bool(transitions_by_action.get(aid))
        if not controls_by_action.get(aid) and not explicit_trigger:
            add(gaps, page, 'ARCHITECTURE_GAP', 'ACTION_WITHOUT_CONTROL_OR_TRIGGER', aid, 'no registered control or exact transition/system trigger')

        rb = action.get('runtime_binding') or {}
        kind = rb.get('binding_kind')
"""

NEW = """        rb = action.get('runtime_binding') or {}
        kind = rb.get('binding_kind')
        failure_recovery_not_applicable = (
            not is_effectful
            and kind == 'CLIENT_STATE_OR_VIEW_NO_API_REQUIRED'
            and rb.get('api_required') is False
            and not transitions_by_action.get(aid)
        )
        err = action.get('error_uid')
        if err:
            if err not in errors:
                add(gaps, page, 'IMPLEMENTATION_GAP', 'ACTION_ERROR_REF_MISSING', aid, str(err))
            elif not errors[err].get('recovery'):
                add(gaps, page, 'IMPLEMENTATION_GAP', 'RECOVERY_CONTRACT_MISSING', aid, str(err))
        elif not failure_recovery_not_applicable and not any((transitions.get(tid) or {}).get('recovery') for tid in transitions_by_action.get(aid, [])):
            add(gaps, page, 'ARCHITECTURE_GAP', 'FAILURE_STATE_ERROR_BINDING_MISSING', aid, 'no exact action->error/recovery or transition recovery binding')

        explicit_trigger = present(action, 'trigger_event_uid', 'trigger_uid', 'invocation', 'system_trigger', 'trigger_kind') or bool(transitions_by_action.get(aid))
        if not controls_by_action.get(aid) and not explicit_trigger:
            add(gaps, page, 'ARCHITECTURE_GAP', 'ACTION_WITHOUT_CONTROL_OR_TRIGGER', aid, 'no registered control or exact transition/system trigger')
"""

if not SCANNER.is_file():
    print(f"BLOCK: missing scanner {SCANNER.relative_to(ROOT)}", file=sys.stderr)
    raise SystemExit(1)
text = SCANNER.read_text(encoding="utf-8")
if NEW in text and OLD not in text:
    print("PASS: R29 scanner correction already applied")
    raise SystemExit(0)
count = text.count(OLD)
if count != 1:
    print(f"BLOCK: R29 exact source block denominator expected=1 actual={count}", file=sys.stderr)
    raise SystemExit(1)
SCANNER.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print("PASS: R29 applied exact failure/recovery applicability correction to canonical fresh scanner")
print("PASS: explicit error_uid validation preserved; only exact non-effectful client/no-api/no-transition actions become N/A")
