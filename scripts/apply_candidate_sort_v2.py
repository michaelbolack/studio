#!/usr/bin/env python3
"""Apply the Election Center v2 candidate-ranking frontend patch.

Candidates render highest-to-lowest by votes. Equal vote totals use candidate name as
a deterministic tiebreaker so the UI does not jump unpredictably between refreshes.
"""
from pathlib import Path

PATH = Path("index.html")
OLD = "function card(r,d,scope,aggregate=false){let p=partyFor(r),cands=r.candidates||[],total=cands.reduce"
NEW = "function card(r,d,scope,aggregate=false){let p=partyFor(r),cands=[...(r.candidates||[])].sort((a,b)=>Number(b.votes||0)-Number(a.votes||0)||String(a.name||'').localeCompare(String(b.name||''))),total=cands.reduce"

text = PATH.read_text()
if NEW in text:
    print("Candidate sorting already applied")
    raise SystemExit(0)
if OLD not in text:
    raise SystemExit("Expected card renderer signature not found; refusing unsafe patch")
text = text.replace(OLD, NEW, 1)
PATH.write_text(text)
print("Applied highest-to-lowest candidate sorting with alphabetical tie break")
