from pathlib import Path
import subprocess, re, html

subprocess.run(['git','fetch','origin','new'],check=True)

def show(path):
    return subprocess.check_output(['git','show',f'origin/new:{path}'],text=True)

auth=show('authority/pages/workspace/INFO-01/ACPOS_INFO-01_FINAL_LOCKED_ENCODING.yaml')
block=auth.split('  controls:\n',1)[1].split('  integration_ports:\n',1)[0]
controls=[]
for chunk in re.split(r'(?m)^  - control_uid: ',block)[1:]:
    uid=chunk.splitlines()[0].strip()
    def get(k):
        m=re.search(rf'(?m)^    {re.escape(k)}: (.+)$',chunk)
        return m.group(1).strip() if m else ''
    controls.append({'id':uid,'section':get('section_uid'),'component':get('component_uid'),'visual':get('visual_uid'),'type':get('type'),'label':get('label')})
if len(controls)!=66 or len({x['id'] for x in controls})!=66:
    raise SystemExit(f'INFO control registry mismatch: {len(controls)}')
if len({x['section'] for x in controls})!=12 or len({x['component'] for x in controls})!=20 or len({x['visual'] for x in controls})!=12:
    raise SystemExit('INFO binding dimensions mismatch')

sections={
'INFO-01-SEC-01':'Context / Projection Control','INFO-01-SEC-02':'Scope / Source Health','INFO-01-SEC-03':'Alert Feed',
'INFO-01-SEC-04':'Fact Pack Explorer','INFO-01-SEC-05':'Fact / Inference Detail','INFO-01-SEC-06':'Evidence / Source Metadata',
'INFO-01-SEC-07':'Freshness / Completeness / Confidence','INFO-01-SEC-08':'Research Queue / Runs','INFO-01-SEC-09':'Context Candidate Review',
'INFO-01-SEC-10':'Citation','INFO-01-SEC-11':'Action Dock','INFO-01-SEC-12':'Audit / Status'}

def bysec(s): return [x for x in controls if x['section']==s]

def render(x):
    label=html.escape(x['label'])
    attrs=f'data-control-id="{x["id"]}" data-component-uid="{x["component"]}" data-visual-uid="{x["visual"]}"'
    t=x['type']
    if t=='READONLY': return f'<div class="field" {attrs}><span>{label}</span><strong>—</strong></div>'
    if t=='LIST': return f'<div class="ctl" {attrs}><span>{label}</span><div class="list">—</div></div>'
    if t=='FILTER': return f'<label class="ctl" {attrs}><span>{label}</span><select disabled><option>—</option></select></label>'
    if t=='TAB': return f'<button class="btn tab" {attrs} disabled>{label}</button>'
    return f'<button class="btn {"primary" if t=="PRIMARY_BUTTON" else ""}" {attrs} disabled>{label}</button>'

def panel(sec,body=None,extra=''):
    xs=bysec(sec); visual=xs[0]['visual'] if xs else ''
    if body is None: body='<div class="stack">'+''.join(render(x) for x in xs)+'</div>'
    return f'<section class="panel {extra}" data-section-id="{sec}" data-visual-uid="{visual}"><div class="title-row"><h2>{sections[sec]}</h2></div>{body}</section>'

nav='''<nav class="nav">
<a href="index.html#/"> <span class="ico">▦</span><span class="nav-label"><span class="tw">儀表板</span><span class="cn">仪表板</span><span class="en">Dashboard</span></span></a>
<a href="index.html#/core"><span class="ico">▰</span><span class="nav-label"><span class="tw">專案 / 專題</span><span class="cn">项目 / 专题</span><span class="en">Project / Topic</span></span></a>
<a href="index.html#/assets"><span class="ico">▧</span><span class="nav-label"><span class="tw">素材</span><span class="cn">素材</span><span class="en">Assets</span></span></a>
<a href="index.html#/video"><span class="ico">▶</span><span class="nav-label"><span class="tw">影片</span><span class="cn">影片</span><span class="en">Video</span></span></a>
<a href="edit.html"><span class="ico">≋</span><span class="nav-label"><span class="tw">剪輯配音</span><span class="cn">剪辑配音</span><span class="en">Editing & Voice</span></span></a>
<a href="qa.html"><span class="ico">✓</span><span class="nav-label">QA</span></a>
<a href="db.html"><span class="ico">◉</span><span class="nav-label"><span class="tw">資料庫</span><span class="cn">数据库</span><span class="en">Database</span></span></a>
<a href="strategy.html"><span class="ico">◎</span><span class="nav-label"><span class="tw">戰略中心</span><span class="cn">战略中心</span><span class="en">Strategy Center</span></span></a>
<a href="info.html" class="active"><span class="ico">ⓘ</span><span class="nav-label"><span class="tw">最新資訊</span><span class="cn">最新资讯</span><span class="en">Latest Information</span></span></a>
</nav>'''

sec1=bysec('INFO-01-SEC-01')
ctx='<div class="context-grid">'+''.join(render(x) for x in sec1[:4])+'</div><div class="actions">'+''.join(render(x) for x in sec1[4:])+'</div>'
sec5=bysec('INFO-01-SEC-05')
fact=[x for x in sec5 if x['component']=='INFO-01-CMP-FACT']
inf=[x for x in sec5 if x['component']=='INFO-01-CMP-INFERENCE']
tabs=''.join(render(x) for x in sec5 if x['type']=='TAB')
factbody=f'<div class="tabs">{tabs}</div><div class="fact-split"><div class="fact-box"><b>FACT</b>{"".join(render(x) for x in fact if x["type"]!="TAB")}</div><div class="infer-box"><b>INFERENCE / RECOMMENDATION</b>{"".join(render(x) for x in inf if x["type"]!="TAB")}</div></div>'
research=panel('INFO-01-SEC-08','<div class="stack">'+''.join(render(x) for x in bysec('INFO-01-SEC-08'))+'</div><div class="notice"><span class="tw">Research Queue / Run 僅顯示唯讀狀態；不提供 Start / Cancel Research。</span><span class="cn">Research Queue / Run 仅显示只读状态；不提供 Start / Cancel Research。</span><span class="en">Research Queue / Run is read-only here; no Start / Cancel Research action is exposed.</span></div>')

body=f'''<section class="context" data-section-id="INFO-01-SEC-01" data-visual-uid="INFO-01-VIS-CONTEXT">{ctx}</section>
<div class="primary-grid"><aside class="rail">{panel('INFO-01-SEC-02')}{panel('INFO-01-SEC-03')}</aside><main class="center">{panel('INFO-01-SEC-04')}{panel('INFO-01-SEC-05',factbody)}{panel('INFO-01-SEC-06')}</main><aside class="rail">{panel('INFO-01-SEC-07')}{research}</aside></div>
{panel('INFO-01-SEC-09','<div class="candidate-grid">'+''.join(render(x) for x in bysec('INFO-01-SEC-09'))+'</div>','lower')}
{panel('INFO-01-SEC-10','<div class="four-grid">'+''.join(render(x) for x in bysec('INFO-01-SEC-10'))+'</div>','lower')}
{panel('INFO-01-SEC-11','<div class="actions">'+''.join(render(x) for x in bysec('INFO-01-SEC-11'))+'</div>','lower')}
{panel('INFO-01-SEC-12','<div class="status-grid">'+''.join(render(x) for x in bysec('INFO-01-SEC-12'))+'</div><div class="notice"><span class="tw">Knowledge Firewall：Fact / Inference / Recommendation 不可直接修改 Canon、Lock、Priority、Budget、Task、Release 或 Publish。</span><span class="cn">Knowledge Firewall：Fact / Inference / Recommendation 不可直接修改 Canon、Lock、Priority、Budget、Task、Release 或 Publish。</span><span class="en">Knowledge Firewall: Fact / Inference / Recommendation cannot directly modify Canon, Lock, Priority, Budget, Task, Release, or Publish.</span></div>','lower')}'''

css='''
:root{color-scheme:dark;--bg:#050816;--surface:#0c1026;--surface2:#111936;--input:#0a0f24;--purple:#8b5cff;--purple2:#6e35ff;--active:rgba(139,92,255,.28);--hover:rgba(139,92,255,.18);--border:rgba(142,112,255,.28);--sub:rgba(142,112,255,.18);--text:#f3f5ff;--text2:#aeb7d9;--muted:#7f88a8}*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif}body{overflow:hidden}button,input,select{font:inherit;color:inherit}button:disabled,select:disabled{opacity:.46}.shell{width:100vw;height:100vh;min-width:1024px}.header{position:fixed;z-index:100;inset:0 0 auto;height:58px;display:flex;align-items:center;justify-content:space-between;padding:0 16px 0 30px;background:rgba(5,5,20,.94);border-bottom:1px solid var(--border)}.brand{width:104px;height:48px;display:flex;align-items:center}.brand img{width:100%;max-height:48px;object-fit:contain;filter:brightness(0) invert(1)}.head-actions{display:flex;gap:8px;align-items:center}.head-btn,.lang{height:36px;border:1px solid var(--sub);border-radius:10px;background:var(--surface2);padding:0 11px;color:var(--text2)}.lang-wrap{position:relative}.lang{width:72px}.lang-menu{display:none;position:absolute;right:0;top:44px;width:190px;padding:6px;border:1px solid var(--border);border-radius:12px;background:#0b1027}.lang-menu.open{display:block}.lang-menu button{width:100%;height:40px;border:0;background:transparent;text-align:left}.sidebar{position:fixed;z-index:90;left:0;top:58px;bottom:0;width:64px;padding:16px 10px;background:transparent;overflow:visible;transition:width .12s}.sidebar:hover,.sidebar:focus-within{width:221px;padding-left:15px;padding-right:15px}.side-bg{position:absolute;z-index:-1;inset:0 auto 0 0;width:221px;opacity:0;background:rgba(5,7,24,.94);border-right:1px solid var(--border);transition:opacity .12s}.sidebar:hover .side-bg,.sidebar:focus-within .side-bg{opacity:1}.nav{display:flex;flex-direction:column;gap:8px;width:44px}.sidebar:hover .nav,.sidebar:focus-within .nav{width:191px}.nav a{height:44px;width:44px;display:flex;align-items:center;gap:12px;padding:0 12px;border:1px solid transparent;border-radius:10px;color:var(--text2);text-decoration:none;overflow:hidden;white-space:nowrap}.sidebar:hover .nav a,.sidebar:focus-within .nav a{width:191px}.nav a:hover{background:var(--hover);color:var(--text)}.nav .active{background:var(--active);border-color:rgba(179,140,255,.46);color:var(--text)}.ico{width:20px;flex:0 0 20px;text-align:center}.nav-label{opacity:0;transition:.1s}.sidebar:hover .nav-label,.sidebar:focus-within .nav-label{opacity:1}.workspace{position:fixed;left:78px;top:68px;right:16px;bottom:16px;overflow:auto}.page{min-width:1280px;display:grid;gap:16px;padding:0 0 16px}.panel,.context{min-width:0;border:1px solid var(--sub);border-radius:12px;background:var(--surface)}.panel{padding:16px}.context{min-height:56px;padding:16px;display:grid;grid-template-columns:minmax(0,1fr) max-content;gap:8px;align-items:end}.context-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.actions{display:flex;gap:8px;align-items:end;flex-wrap:wrap}.primary-grid{display:grid;grid-template-columns:minmax(280px,1fr) minmax(720px,3fr) minmax(300px,1fr);gap:16px;align-items:start}.rail,.center,.stack{display:grid;gap:16px;min-width:0}.stack{gap:8px}.title-row{margin-bottom:10px}.title-row h2{font-size:14px;margin:0}.field,.ctl{display:grid;gap:5px;min-width:0}.field span,.ctl span{font-size:10px;color:var(--muted)}.field strong,.ctl select{height:40px;width:100%;display:flex;align-items:center;padding:0 10px;border:1px solid var(--sub);border-radius:10px;background:var(--input);color:var(--text2)}.list{min-height:150px;display:grid;place-items:center;border:1px solid var(--sub);border-radius:10px;background:var(--input);color:var(--muted)}.btn{min-height:40px;min-width:88px;border:1px solid var(--border);border-radius:10px;background:var(--surface2);color:var(--text2);padding:0 12px}.primary{min-width:120px;background:linear-gradient(135deg,var(--purple2),var(--purple));color:var(--text)}.tabs{display:flex;gap:8px;margin-bottom:10px}.fact-split{display:grid;grid-template-columns:1fr 1fr;gap:16px}.fact-box,.infer-box{display:grid;gap:8px;padding:12px;border:1px solid var(--sub);border-radius:10px;background:var(--input)}.fact-box{border-top:2px solid #b38cff}.infer-box{border-top:2px solid var(--border)}.fact-box>b,.infer-box>b{font-size:11px;color:var(--text2)}.candidate-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.four-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.status-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;align-items:end}.notice{margin-top:10px;padding:12px;border:1px solid var(--sub);border-radius:10px;background:var(--input);color:var(--muted);font-size:12px;line-height:1.5}.cn,.en{display:none}.lang-cn .tw,.lang-cn .en{display:none}.lang-cn .cn{display:inline}.lang-en .tw,.lang-en .cn{display:none}.lang-en .en{display:inline}@media(max-width:1599px){.primary-grid{grid-template-columns:minmax(280px,1fr) minmax(0,3fr) minmax(300px,1fr)}}@media(max-width:1439px){.context-grid{grid-template-columns:repeat(4,minmax(180px,1fr))}.candidate-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
'''

info=f'''<!doctype html><html lang="zh-Hant-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ORANGE ONE — INFO-01 Preview</title><style>{css}</style></head><body><div class="shell"><header class="header"><div class="brand"><img alt="ORANGE ONE" src="https://raw.githubusercontent.com/steven-gold/orange-one-ai-viedo-v1.0/new/public/brand/orange-one-logo.png"></div><div class="head-actions"><button class="head-btn" disabled>◔ —</button><button class="head-btn" disabled>☑ —</button><button class="head-btn" disabled>◷ —</button><div class="lang-wrap"><button class="lang" id="langBtn">zh-TW</button><div class="lang-menu" id="langMenu"><button data-lang="zh-TW">繁體中文</button><button data-lang="zh-CN">简体中文</button><button data-lang="en">English</button></div></div><button class="head-btn" disabled>○ —⌄</button></div></header><aside class="sidebar"><div class="side-bg"></div>{nav}</aside><main class="workspace"><div class="page" data-page-uid="workspace:INFO-01" data-vis-step="VIS-09" data-authority-controls="66">{body}</div></main></div><script>let lang=localStorage.getItem('acpos.preview.lang')||'zh-TW';const root=document.documentElement,btn=document.getElementById('langBtn'),menu=document.getElementById('langMenu');function apply(){{root.classList.toggle('lang-cn',lang==='zh-CN');root.classList.toggle('lang-en',lang==='en');root.lang=lang==='zh-TW'?'zh-Hant-TW':lang==='zh-CN'?'zh-Hans-CN':'en';btn.textContent=lang}}apply();btn.onclick=()=>menu.classList.toggle('open');menu.querySelectorAll('button').forEach(b=>b.onclick=()=>{{lang=b.dataset.lang;localStorage.setItem('acpos.preview.lang',lang);menu.classList.remove('open');apply()}});</script></body></html>'''
Path('preview/info.html').write_text(info)

# Existing preview pages: append the 9th menu item only; preserve existing first 8 items exactly.
for name in ['edit.html','qa.html','db.html','strategy.html']:
    p=Path('preview')/name
    s=p.read_text()
    if 'href="info.html"' not in s:
        link='<a href="info.html"><span class="ico">ⓘ</span><span class="nav-label"><span class="tw">最新資訊</span><span class="en">Latest Information</span></span></a>\n'
        pos=s.find('</nav>')
        if pos<0: raise SystemExit(f'{name}: nav close missing')
        s=s[:pos]+link+s[pos:]
    p.write_text(s)

p=Path('preview/index.html'); s=p.read_text()
if 'href="info.html"' not in s:
    anchor='<a href="strategy.html"><span class="ico">◎</span><span class="nav-label" data-i="strategy">戰略中心</span></a>\n'
    if anchor not in s: raise SystemExit('index strategy anchor missing')
    s=s.replace(anchor,anchor+'<a href="info.html"><span class="ico">ⓘ</span><span class="nav-label" data-i="info">最新資訊</span></a>\n',1)
for old,new in [
    ("strategy:'戰略中心',no:","strategy:'戰略中心',info:'最新資訊',no:"),
    ("strategy:'战略中心',no:","strategy:'战略中心',info:'最新资讯',no:"),
    ("strategy:'Strategy Center',no:","strategy:'Strategy Center',info:'Latest Information',no:")]:
    if old in s: s=s.replace(old,new,1)
p.write_text(s)

# Exact static validation.
for name in ['index.html','edit.html','qa.html','db.html','strategy.html','info.html']:
    s=(Path('preview')/name).read_text()
    navblock=s[s.find('<nav'):s.find('</nav>')]
    count=len(re.findall(r'<(?:a|button)\b',navblock))
    if count!=9: raise SystemExit(f'{name}: nav count={count}')
    if 'info.html' not in navblock: raise SystemExit(f'{name}: INFO nav missing')
info_s=Path('preview/info.html').read_text()
ids=set(re.findall(r'data-control-id="(INFO-01-[^"]+)"',info_s))
if len(ids)!=66: raise SystemExit(f'info.html control count={len(ids)}')
if 'Start Research' in info_s.replace('no Start / Cancel Research action is exposed.','') or 'data-control-id="INFO-01-BTN-START' in info_s:
    raise SystemExit('unregistered Start Research exposed')
print('PREVIEW SYNC PASS: 6 pages, 9 nav items each, INFO controls=66')
