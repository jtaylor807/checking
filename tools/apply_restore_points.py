from pathlib import Path
import hashlib

PATH = Path('index.html')
EXPECTED_BLOB = '852cd76e3d2f4c895865720dce44f49a04d676ca'
raw = PATH.read_bytes()
actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
if actual != EXPECTED_BLOB:
    raise SystemExit(f'ABORT: index.html blob changed: expected {EXPECTED_BLOB}, got {actual}')
text = raw.decode('utf-8')

def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'ABORT: {label} expected once, found {count}')
    text = text.replace(old, new, 1)

replace_once('.filteredBalance{font-size:16px;color:#b9c6d8}', '.filteredBalance{font-size:16px;color:#b9c6d8}.restoreList{display:grid;gap:8px;max-height:55vh;overflow:auto}.restoreItem{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;border:1px solid var(--line);border-radius:12px;padding:10px;background:#08111f}.restoreMeta{font-size:12px;color:var(--muted);margin-top:3px}', 'restore CSS')

replace_once('<button id="btnBackup">Download Backup</button>', '<button id="btnBackup">Download Backup</button> <button id="btnCreateRestorePoint">Create Restore Point</button> <button id="btnRestorePoints">Restore Points</button>', 'settings buttons')

modal = '''<div class="modal" id="restorePointsModal"><div class="dialog"><h2>Restore Points</h2><p class="muted">All restore points are kept for 30 days. Older points are reduced to one per month.</p><div id="restorePointsList" class="restoreList"></div><div class="actions"><button data-close>Close</button></div></div></div>'''
replace_once('<script>\'use strict\';', modal + '<script>\'use strict\';', 'restore modal')

replace_once("const APP_VERSION='v0.6.5',LS_KEY='checkingLedgerState_v1',LS_SETTINGS='checkingLedgerSettings_v1',LS_LAST_VERSION='checkingLedgerLastVersion';", "const APP_VERSION='v0.7.0',LS_KEY='checkingLedgerState_v1',LS_SETTINGS='checkingLedgerSettings_v1',LS_LAST_VERSION='checkingLedgerLastVersion',LS_RESTORE_POINTS='checkingLedgerRestorePoints_v1';", 'constants/version')

replace_once("$('btnBackup').onclick=downloadBackup;", "$('btnBackup').onclick=downloadBackup;$('btnCreateRestorePoint').onclick=()=>createRestorePoint('Manual restore point',true);$('btnRestorePoints').onclick=openRestorePoints;", 'restore bindings')

replace_once("alert(\"v0.6.5\\nTop and Add row stay visible. Filters/sort stay frozen after edits until Refresh Filters. Cleared sets Paid. Add row saves on click-away. Modified shows local time with seconds. Filtered cleared balance appears in parentheses.\")", "alert(\"v0.7.0\\nAdds full application restore points. All points are kept for 30 days, then one per month indefinitely. A safety restore point is created automatically before every restore.\")", 'version notes')

restore_code = r'''function restoreUiSnapshot(ui){if(!ui)return;sortKey=ui.sortKey||'entered';sortDir=ui.sortDir||1;showAllTxn=!!ui.showAllTxn;accumOnly=!!ui.accumOnly;amountFilter=ui.amountFilter||'';amountUnpaidOnly=!!ui.amountUnpaidOnly;['searchBox','filterType','filterPaid','filterCleared','filterTax'].forEach(id=>{if($(id)&&ui[id]!==undefined)$(id).value=ui[id]});if($('quickAmount'))$('quickAmount').value=amountFilter;showScreen(ui.screen||'ledger')}function captureUiSnapshot(){let active=document.querySelector('.nav button[data-screen].active');return{sortKey,sortDir,showAllTxn,accumOnly,amountFilter,amountUnpaidOnly,screen:active?.dataset.screen||'ledger',searchBox:$('searchBox').value,filterType:$('filterType').value,filterPaid:$('filterPaid').value,filterCleared:$('filterCleared').value,filterTax:$('filterTax').value}}function readRestorePoints(){try{let p=JSON.parse(localStorage.getItem(LS_RESTORE_POINTS)||'[]');return Array.isArray(p)?p:[]}catch(e){return[]}}function writeRestorePoints(points){localStorage.setItem(LS_RESTORE_POINTS,JSON.stringify(points))}function pruneRestorePoints(points){let cutoff=Date.now()-30*24*60*60*1000,recent=[],monthly={};points.forEach(p=>{let t=new Date(p.createdAt).getTime();if(!Number.isFinite(t))return;if(t>=cutoff)recent.push(p);else{let k=p.createdAt.slice(0,7);if(!monthly[k]||p.createdAt>monthly[k].createdAt)monthly[k]=p}});return recent.concat(Object.values(monthly)).sort((a,b)=>b.createdAt.localeCompare(a.createdAt))}function createRestorePoint(label='Manual restore point',notify=false){try{let points=readRestorePoints();let point={id:'rp-'+Date.now()+'-'+Math.random().toString(36).slice(2,8),createdAt:new Date().toISOString(),label,appVersion:APP_VERSION,transactionCount:state.ledger.length,snapshot:{state:JSON.parse(JSON.stringify(state)),ui:captureUiSnapshot(),dirty}};points.unshift(point);points=pruneRestorePoints(points);writeRestorePoints(points);if(notify)alert('Restore point created.');return point}catch(e){alert('Restore point could not be created. Browser storage may be full.');return null}}function openRestorePoints(){renderRestorePoints();$('restorePointsModal').classList.add('show')}function renderRestorePoints(){let list=$('restorePointsList'),points=pruneRestorePoints(readRestorePoints());try{writeRestorePoints(points)}catch(e){}if(!points.length){list.innerHTML='<div class="muted">No restore points yet.</div>';return}list.innerHTML=points.map(p=>`<div class="restoreItem"><div><b>${esc(p.label||'Restore point')}</b><div class="restoreMeta">${esc(new Date(p.createdAt).toLocaleString())} · ${esc(p.appVersion||'')} · ${num(p.transactionCount)} transactions</div></div><button class="small" data-restore-id="${esc(p.id)}">Restore</button></div>`).join('');list.querySelectorAll('[data-restore-id]').forEach(b=>b.onclick=()=>restorePoint(b.dataset.restoreId))}function restorePoint(id){let point=readRestorePoints().find(p=>p.id===id);if(!point||!point.snapshot?.state)return alert('Restore point is invalid.');if(!confirm('Restore this application state? A safety restore point will be created first.'))return;let safety=createRestorePoint('Automatic safety point before restore');if(!safety)return;state=JSON.parse(JSON.stringify(point.snapshot.state));normalizeState();restoreUiSnapshot(point.snapshot.ui);dirty=point.snapshot.dirty!==false;saveLocal();refreshFilters();renderPaychecks();updateStatus('Restored '+new Date(point.createdAt).toLocaleString());closeModals()}'''
replace_once('function resetLocal(){', restore_code + 'function resetLocal(){', 'restore functions')

for old, new in [('v0.6.5','v0.7.0')]:
    text = text.replace(old, new)

required = ['btnCreateRestorePoint','btnRestorePoints','restorePointsModal','LS_RESTORE_POINTS','function createRestorePoint','function restorePoint']
for marker in required:
    if marker not in text:
        raise SystemExit(f'ABORT: missing marker {marker}')
if text.count('<script>') != text.count('</script>') or text.count('<div') != text.count('</div>'):
    raise SystemExit('ABORT: basic HTML tag balance failed')
PATH.write_text(text, encoding='utf-8', newline='')
print('Patched index.html safely')
