from pathlib import Path
p=Path('index.html')
s=p.read_text()
old='<section class="hero"><div class="eyebrow">ELECTION NIGHT COVERAGE</div><h1>2026 Election Center</h1><p id="hero-copy">Florida primary results with county, statewide and districtwide coverage.</p></section>'
new='<section class="hero"><div class="eyebrow" id="election-status-label">POST-ELECTION RESULTS</div><h1>2026 Election Center</h1><p id="hero-copy">Florida primary results with county, statewide and districtwide coverage.</p></section>'
assert old in s
s=s.replace(old,new,1)
old_notice='<div class="notice" id="notice"><b>LIVE RESULTS:</b> Results refresh automatically. Where a county feed cannot be normalized, IRC Media links directly to that county\'s official election-night results so every Florida county remains available.</div>'
new_notice='<div class="notice" id="notice"><b>POST-ELECTION RESULTS:</b> The August 18 primary is frozen in post-election mode. Validated county-local results may still be added from authoritative county sources.</div>'
assert old_notice in s
s=s.replace(old_notice,new_notice,1)
old_timer='setInterval(loadAll,60000)'
assert old_timer in s
new_timer="fetch('data/election-config.json?ts='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(cfg=>{const c=cfg.currentElection||{};const label=document.getElementById('election-status-label');const notice=document.getElementById('notice');if(label&&c.resultsLabel)label.textContent=c.resultsLabel;if(notice&&c.notice)notice.innerHTML='<b>'+esc(c.resultsLabel||'ELECTION RESULTS')+':</b> '+esc(c.notice);if(c.liveRefresh===true)setInterval(loadAll,Number(c.refreshIntervalMs)||60000)}).catch(()=>{})"
s=s.replace(old_timer,new_timer,1)
p.write_text(s)
print('Election lifecycle patch applied')
