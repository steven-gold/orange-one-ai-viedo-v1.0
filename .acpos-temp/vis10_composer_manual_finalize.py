from pathlib import Path
p=Path('docs/construction/ACPOS_WEBSITE_CONSTRUCTION_PROGRESS.yaml')
s=p.read_text()
old='''          manual_visual_inspection: PENDING_ARTIFACT_REVIEW_BEFORE_MERGE
'''
new='''          manual_visual_inspection: PASS
          manual_evidence_pack_run_id: 33298242805
          manual_evidence_artifact_id: 9728086389
          manual_evidence_sha256: f8364aead388ca8e0539a8d435bafaa2332c1e81c51f6c2d5ede58a50c208346
          manual_visual_inspection_basis: Composer top, expanded overlay, and corrected workspace-bottom screenshots were directly inspected; textarea/action alignment, panel sizing, sidebar overlay, and lower sections had no unintended clipping, overlap, or reflow.
'''
if s.count(old)!=1:
    raise RuntimeError(f'expected one pending manual marker, got {s.count(old)}')
s=s.replace(old,new,1)
p.write_text(s)
