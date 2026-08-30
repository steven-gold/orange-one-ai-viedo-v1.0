from pathlib import Path
p=Path('preview/system.html')
s=p.read_text()

def r(old,new,label):
    global s
    c=s.count(old)
    if c!=1: raise RuntimeError(f'{label}: expected 1 got {c}')
    s=s.replace(old,new,1)

r('.primary-grid{display:grid;grid-template-columns:minmax(310px,.92fr) minmax(820px,2.4fr);gap:16px}', '.primary-grid{display:grid;grid-template-columns:minmax(290px,.72fr) minmax(880px,2.7fr);gap:16px}', 'grid')
r('.conversation{min-height:490px;display:flex;flex-direction:column}', '.conversation{min-height:610px;display:flex;flex-direction:column}', 'conversation height')
r('.conversation-body{flex:1;min-height:330px;', '.conversation-body{flex:1;min-height:360px;', 'body height')
r('@media(max-width:1439px){.primary-grid{grid-template-columns:310px minmax(0,1fr)}', '@media(max-width:1439px){.primary-grid{grid-template-columns:290px minmax(0,1fr)}', 'responsive grid')
composer_css='.composer{min-height:112px;display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:end;gap:10px;margin-top:10px;padding:10px;border:1px solid var(--border);border-radius:10px;background:rgba(7,11,29,.94)}.composer textarea{width:100%;min-height:82px;max-height:220px;resize:vertical;border:1px solid var(--sub);border-radius:10px;background:var(--input);color:var(--text);padding:10px 12px;font:inherit;font-size:12px;line-height:1.5;outline:none}.composer textarea:focus{border-color:var(--ba);box-shadow:0 0 0 2px rgba(139,92,255,.12)}.composer-actions{display:flex;align-items:center;gap:7px}.composer-actions .btn{min-height:40px;min-width:64px}.composer-actions .primary{min-width:76px}'
r('.secondary-grid{display:grid;', composer_css+'.secondary-grid{display:grid;', 'composer css')
old='<div class="context-strip"><div class="mini"><span>conversation_id</span><strong>—</strong></div><div class="mini"><span>thread_id</span><strong>—</strong></div><div class="mini"><span>branch_id</span><strong>—</strong></div><div class="mini"><span>context_snapshot_ref</span><strong>—</strong></div></div></section></div>'
new='<div class="context-strip"><div class="mini"><span>conversation_id</span><strong>—</strong></div><div class="mini"><span>thread_id</span><strong>—</strong></div><div class="mini"><span>branch_id</span><strong>—</strong></div><div class="mini"><span>context_snapshot_ref</span><strong>—</strong></div></div><div class="composer" data-component-uid="SYS-01-CMP-CONVERSATION-COMPOSER" data-visual-uid="SYS-01-VIS-CONVERSATION-COMPOSER"><textarea id="SYS-01-INP-MESSAGE" data-control-id="SYS-01-INP-MESSAGE" rows="3" placeholder="輸入系統設計、維護或變更問題…" aria-label="AI 對話輸入"></textarea><div class="composer-actions"><button class="btn" data-control-id="SYS-01-BTN-ATTACH" disabled>附件</button><button class="btn" data-control-id="SYS-01-BTN-STOP" disabled>停止</button><button class="btn primary" data-control-id="SYS-01-BTN-SEND" disabled>送出</button></div></div></section></div>'
r(old,new,'composer html')
p.write_text(s)
