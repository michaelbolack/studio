from pathlib import Path
p=Path('index.html')
s=p.read_text()
css='.upcoming-election{margin:16px 0 24px;padding:16px 18px;border:1px solid #31557a;background:#101a25;border-radius:14px;display:grid;grid-template-columns:1.35fr repeat(3,minmax(0,1fr));gap:14px;align-items:center}.upcoming-kicker{font-size:11px;font-weight:900;letter-spacing:1px;color:#89c2ff}.upcoming-name{font-size:20px;font-weight:900;margin-top:4px}.upcoming-count{font-size:12px;color:var(--gold);font-weight:800;margin-top:4px}.upcoming-item{border-left:1px solid var(--line);padding-left:14px}.upcoming-label{font-size:10px;font-weight:900;letter-spacing:.6px;color:var(--muted);text-transform:uppercase}.upcoming-value{margin-top:4px;font-weight:800;font-size:13px}@media(max-width:760px){.upcoming-election{grid-template-columns:1fr}.upcoming-item{border-left:0;border-top:1px solid var(--line);padding-left:0;padding-top:10px}}\n'
assert s.count(css)==2, s.count(css)
s=s.replace(css+css,css,1)
card='<div class="upcoming-election" id="upcoming-election"><div><div class="upcoming-kicker">UPCOMING ELECTION</div><div class="upcoming-name" id="next-election-name">2026 General Election</div><div class="upcoming-count" id="next-election-count"></div></div><div class="upcoming-item"><div class="upcoming-label">Election Day</div><div class="upcoming-value" id="next-election-date">November 3, 2026</div></div><div class="upcoming-item"><div class="upcoming-label">Register By</div><div class="upcoming-value" id="next-registration">October 5, 2026</div></div><div class="upcoming-item"><div class="upcoming-label">Early Voting / VBM</div><div class="upcoming-value" id="next-early-voting">Oct. 24–31</div><div class="county-note" id="next-vbm">VBM request deadline: Oct. 22</div></div></div>'
assert s.count(card)==2, s.count(card)
s=s.replace(card+card,card,1)
js="const n=cfg.nextElection||{};const fmt=d=>d?new Date(d+'T12:00:00').toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'}):'';const ne=document.getElementById('next-election-name'),nd=document.getElementById('next-election-date'),nr=document.getElementById('next-registration'),nev=document.getElementById('next-early-voting'),nv=document.getElementById('next-vbm'),nc=document.getElementById('next-election-count');if(ne&&n.name)ne.textContent=n.name;if(nd&&n.electionDate)nd.textContent=fmt(n.electionDate);if(nr&&n.registrationDeadline)nr.textContent=fmt(n.registrationDeadline);if(nev&&n.earlyVotingStart&&n.earlyVotingEnd)nev.textContent=fmt(n.earlyVotingStart).replace(', 2026','')+'–'+fmt(n.earlyVotingEnd).replace(', 2026','');if(nv&&n.voteByMailRequestDeadline)nv.textContent='VBM request deadline: '+fmt(n.voteByMailRequestDeadline);if(nc&&n.electionDate){const days=Math.max(0,Math.ceil((new Date(n.electionDate+'T23:59:59')-new Date())/86400000));nc.textContent=days+' days until Election Day'}"
assert s.count(js)==2, s.count(js)
s=s.replace(js+js,js,1)
assert s.count('id="upcoming-election"')==1
assert s.count('const n=cfg.nextElection||{}')==1
p.write_text(s)
print('Removed duplicate upcoming-election UI and JavaScript')
