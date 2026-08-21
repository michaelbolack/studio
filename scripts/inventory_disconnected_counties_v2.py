#!/usr/bin/env python3
# isolated diagnostic only; never writes production data
import json
from pathlib import Path

manifest=json.loads(Path('data/manifest.json').read_text())
rows=[]
for county,entry in sorted((manifest.get('counties') or {}).items()):
    if not entry.get('connected'):
        rows.append({
            'county':county,
            'sourceUrl':entry.get('sourceUrl'),
            'file':entry.get('file'),
            'adapter':entry.get('adapter'),
            'validationFailed':entry.get('validationFailed',False),
            'error':entry.get('error'),
        })
out={'generatedFrom':manifest.get('generatedAt'),'disconnectedCount':len(rows),'counties':rows}
Path('county-v2-inventory.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
