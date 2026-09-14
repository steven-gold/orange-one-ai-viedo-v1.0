#!/usr/bin/env python3
from pathlib import Path
import json,yaml,hashlib,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
REQUIRED_PROOF=['NOT_PROTECTED_CURRENT','NOT_IMMUTABLE_RAW_SOURCE','ZERO_CURRENT_OWNER_REFERENCE','ZERO_UNMIGRATED_REVERSE_DEPENDENCY','REPLACEMENT_VALID_IF_SUPERSEDED','CLEANUP_LEDGER_ENTRY','POST_DELETE_RESIDUAL_SCAN']
TERMINAL_STATE='CLOSED'

def load(p): return yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _references(root,rel):
    refs=[]
    skip={'CHECKSUMS.sha256','11_EVIDENCE/audit/CLEANUP_LEDGER.yaml'}
    for p in root.rglob('*'):
        if not p.is_file(): continue
        r=p.relative_to(root).as_posix()
        if r==rel or r in skip or '__pycache__' in p.parts: continue
        if p.suffix not in {'.yaml','.yml','.json','.md','.py','.txt'}: continue
        try: text=p.read_text(encoding='utf-8')
        except Exception: continue
        if rel in text: refs.append(r)
    return sorted(set(refs))
def _cleanup_event(ledger,event_uid,rel):
    for e in ledger.get('events') or []:
        if e.get('event_uid')!=event_uid: continue
        paths=set()
        for k in ['target_path','superseded_path']:
            if e.get(k): paths.add(e.get(k))
        paths.update(e.get('deleted_paths') or [])
        if rel in paths: return e
    return None

def _deletion_targets(event):
    out=[]
    for k in ('target_path','superseded_path'):
        if event.get(k): out.append(event[k])
    out += list(event.get('deleted_paths') or [])
    return sorted(set(x for x in out if x))

def _terminal_ledger_audit(root,ledger):
    failures=[]; audited=0
    for e in ledger.get('events') or []:
        targets=_deletion_targets(e)
        # Only events that have entered the two-phase delete state machine are terminally audited.
        state=e.get('delete_state')
        result=str(e.get('result') or '')
        entered=bool(state) or e.get('delete_executed') is True or 'POST_DELETE' in result or 'PHYSICAL_DELETE' in result
        if not targets or not entered: continue
        audited += 1
        if state!=TERMINAL_STATE: failures.append('cleanup_terminal_state_not_closed:'+str(e.get('event_uid'))+':'+str(state))
        if e.get('delete_executed') is not True: failures.append('cleanup_delete_not_recorded_executed:'+str(e.get('event_uid')))
        post=e.get('post_delete_residual_scan') if isinstance(e.get('post_delete_residual_scan'),dict) else {}
        if post.get('status')!='PASS': failures.append('cleanup_post_delete_scan_not_pass:'+str(e.get('event_uid'))+':'+str(post.get('status') or result))
        if post.get('validator')!='validate_cleanup_protection.py': failures.append('cleanup_post_delete_validator_invalid:'+str(e.get('event_uid')))
        if post.get('residual_reference_count')!=0: failures.append('cleanup_post_delete_ledger_residual_nonzero:'+str(e.get('event_uid')))
        if post.get('target_absent') is not True: failures.append('cleanup_post_delete_target_absence_not_proven:'+str(e.get('event_uid')))
        for rel in targets:
            if (root/rel).exists(): failures.append('cleanup_deleted_target_still_exists:'+str(e.get('event_uid'))+':'+rel)
            refs=_references(root,rel)
            if refs: failures.append('cleanup_post_delete_residual_references:'+str(e.get('event_uid'))+':'+rel+':'+','.join(refs[:8]))
    return audited,failures

def validate(root=ROOT, proposed_deletions=None):
    failures=[]
    pp=root/'10_REGISTRY/PROTECTED_CURRENT_ARTIFACT_REGISTRY.yaml'; mp=root/'10_REGISTRY/GOVERNANCE_ROOT_MANIFEST.yaml'; lp=root/'11_EVIDENCE/audit/CLEANUP_LEDGER.yaml'
    if not pp.exists(): return {'status':'FAIL','failures':['protected_registry_missing']}
    d=load(pp); paths=[x.get('path') for x in d.get('protected_paths',[])]; special=[x.get('path') for x in d.get('non_manifest_protected_assets',[])]
    all_protected=set(paths)|set(special)
    if len(paths)!=len(set(paths)): failures.append('duplicate_protected_path')
    for rel in all_protected:
        if not rel or not (root/rel).exists(): failures.append('protected_current_missing:'+str(rel))
    gate=d.get('delete_gate',{})
    if gate.get('default')!='DENY': failures.append('cleanup_default_not_deny')
    if gate.get('missing_proof')!='CLEANUP_DELETE_NOT_PROVEN_SAFE': failures.append('cleanup_missing_proof_not_fail_closed')
    if gate.get('proof_required')!=REQUIRED_PROOF: failures.append('cleanup_proof_contract_changed')
    if gate.get('evidence_backed_proof_required') is not True: failures.append('cleanup_evidence_backed_proof_not_required')
    if gate.get('string_only_proof')!='BLOCK': failures.append('cleanup_string_only_proof_not_blocked')
    if gate.get('two_phase_post_delete_verification') is not True: failures.append('cleanup_two_phase_post_delete_not_required')
    if gate.get('terminal_post_delete_state_required') is not True: failures.append('cleanup_terminal_post_delete_state_not_required')
    if gate.get('post_delete_fail_or_pending')!='BLOCK': failures.append('cleanup_post_delete_fail_pending_not_block')
    if mp.exists():
        m=load(mp); manifest_paths={rec.get('path') for g in ('current_artifacts','validators') for rec in m.get(g,[]) if rec.get('path')}
        if manifest_paths!=set(paths): failures.append('protected_manifest_exact_set_mismatch')
    ledger=load(lp) if lp.exists() else {}

    # Normal Pre-formal path: all delete transactions that reached execution must be terminally closed and recomputed clean.
    terminal_audited=0
    if proposed_deletions is None:
        terminal_audited,terminal_failures=_terminal_ledger_audit(root,ledger)
        failures += terminal_failures

    # Pre-delete authorization path: fail closed before destructive execution.
    for rec in proposed_deletions or []:
        rel=rec.get('path'); ev=rec.get('proof_evidence')
        if rel in all_protected: failures.append('attempt_delete_protected_current:'+str(rel))
        if not isinstance(ev,dict): failures.append('delete_without_evidence_backed_proof:'+str(rel)); continue
        missing=[k for k in REQUIRED_PROOF if k not in ev]
        if missing: failures.append('delete_without_full_evidence:'+str(rel)+':'+','.join(missing)); continue
        if not (root/str(rel)).exists(): failures.append('pre_delete_target_missing:'+str(rel))
        if rel in all_protected or (ev['NOT_PROTECTED_CURRENT'] or {}).get('recomputed') is not True: failures.append('not_protected_current_proof_invalid:'+str(rel))
        if str(rel).startswith('12_DOCS/mother-spec/') or (ev['NOT_IMMUTABLE_RAW_SOURCE'] or {}).get('recomputed') is not True: failures.append('immutable_raw_source_proof_invalid:'+str(rel))
        manifest_refs=[]
        if mp.exists(): manifest_refs=[x.get('path') for g in ('current_artifacts','validators') for x in load(mp).get(g,[]) if x.get('path')==rel]
        if manifest_refs or (ev['ZERO_CURRENT_OWNER_REFERENCE'] or {}).get('recomputed') is not True: failures.append('zero_current_owner_reference_proof_invalid:'+str(rel))
        refs=_references(root,rel)
        if refs or (ev['ZERO_UNMIGRATED_REVERSE_DEPENDENCY'] or {}).get('recomputed') is not True: failures.append('reverse_dependency_proof_invalid:'+str(rel)+':refs='+','.join(refs[:5]))
        event_uid=(ev['CLEANUP_LEDGER_ENTRY'] or {}).get('event_uid')
        event=_cleanup_event(ledger,event_uid,rel) if event_uid else None
        if not event: failures.append('cleanup_ledger_entry_proof_invalid:'+str(rel))
        repl=ev['REPLACEMENT_VALID_IF_SUPERSEDED'] or {}
        if event and event.get('replacement_path'):
            rp=root/event['replacement_path']
            if not rp.exists() or repl.get('replacement_path')!=event.get('replacement_path') or repl.get('replacement_sha256')!=sha(rp): failures.append('replacement_proof_invalid:'+str(rel))
        elif repl.get('not_applicable') is not True: failures.append('replacement_not_applicable_not_proven:'+str(rel))
        post=ev['POST_DELETE_RESIDUAL_SCAN'] or {}
        if post.get('required_after_delete') is not True or post.get('validator')!='validate_cleanup_protection.py': failures.append('post_delete_residual_scan_plan_invalid:'+str(rel))
    return {'status':'PASS' if not failures else 'FAIL','protected_count':len(all_protected),'terminal_delete_events_audited':terminal_audited,'failures':failures}

if __name__=='__main__':
    out=validate(); print(json.dumps(out,ensure_ascii=False,indent=2)); raise SystemExit(0 if out['status']=='PASS' else 1)
