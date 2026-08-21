#!/usr/bin/env python3
"""Inspect election.js assets exposed by disconnected Florida ENR counties."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import requests

HEADERS={"User-Agent":"Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)"}


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--probe',type=Path,default=Path('validation-output/county-fallback-probe-v2.json'))
    p.add_argument('--output',type=Path,default=Path('build/enr-assets-v2.json'))
    a=p.parse_args()
    data=json.loads(a.probe.read_text())
    out=[]
    for county in data.get('counties') or []:
        urls=[u for u in county.get('scriptSources') or [] if u.lower().endswith('/election.js')]
        if not urls:
            continue
        url=urls[0]
        try:
            r=requests.get(url,headers=HEADERS,timeout=30)
            r.raise_for_status()
            text=r.text
            strings=re.findall(r'([A-Za-z_$][A-Za-z0-9_$]{2,})\s*[:=]',text)
            common=[]
            seen=set()
            for s in strings:
                if s not in seen:
                    seen.add(s);common.append(s)
            out.append({
                'county':county.get('county'),
                'url':url,
                'httpStatus':r.status_code,
                'bytes':len(r.content),
                'sha256':hashlib.sha256(r.content).hexdigest(),
                'symbols':common[:80],
                'signals':{
                    'containsCandidates':bool(re.search(r'candidate',text,re.I)),
                    'containsContests':bool(re.search(r'contest|race',text,re.I)),
                    'containsPrecincts':bool(re.search(r'precinct',text,re.I)),
                    'containsVotes':bool(re.search(r'votes?',text,re.I)),
                    'looksJson':text.lstrip().startswith(('{','[')),
                },
                'sample':text[:6000],
            })
        except Exception as exc:
            out.append({'county':county.get('county'),'url':url,'error':str(exc)})
    payload={'status':'complete','assetsFound':len(out),'assets':out}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,indent=2)+'\n')
    print(f"PROBED: {len(out)} ENR election.js assets")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
