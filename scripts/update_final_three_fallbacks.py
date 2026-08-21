#!/usr/bin/env python3
import json
from pathlib import Path
p=Path('data/manifest.json')
m=json.loads(p.read_text())
updates={
 'Martin':('https://www.martinvotes.gov/','Awaiting county-owned certified/static local results; statewide and district results remain available from Florida DOS.'),
 'Osceola':('https://www.voteosceola.gov/en-us/election-results/2026-election-results/','Awaiting county certification/static local results; statewide and district results remain available from Florida DOS.'),
 'Pinellas':('https://www.votepinellas.gov/375/August-18-2026-Primary-Election-Informat','Awaiting county-owned certified/static local results; statewide and district results remain available from Florida DOS.')
}
for county,(url,msg) in updates.items():
    e=m['counties'][county]
    e['sourceUrl']=url
    e['error']=msg
    e['connected']=False
p.write_text(json.dumps(m,indent=2)+'\n')
print('Updated final three official fallback destinations')
