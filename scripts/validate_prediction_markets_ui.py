#!/usr/bin/env python3
"""Static fail-closed checks for the prediction-markets interface."""

from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")

REQUIRED = [
    'id="markets-nav" href="#prediction-markets" hidden',
    'id="prediction-markets" hidden',
    "function predictionMarketsDisplaySafe(",
    "readiness?.publicDisplayEnabled!==true",
    "readiness?.automatedPublishingEnabled===true",
    "Date.now()-generated.getTime()>86400000",
    "Number(outcome.askPct)-Number(outcome.bidPct)<=5",
    "Number(outcome.volumeContracts)>=1000",
    "function loadPredictionMarkets(",
    "setCenterView('markets')",
    "document.body.classList.toggle('markets-view'",
    "element.hidden=centerView!=='results'",
    ".results-view #prediction-markets",
    ".polling-view #prediction-markets",
    ".markets-view #national-polling",
    ".markets-view #county-note",
    "predictionMarketsData.disclosure",
    "await Promise.all([loadAll(),loadPolling(),loadPredictionMarkets()])",
    "Live market, rules and source",
]

missing = [token for token in REQUIRED if token not in INDEX]
if missing:
    raise SystemExit(
        "Prediction-markets UI validation failed closed; missing: "
        + ", ".join(missing)
    )

if 'id="markets-nav" href="#prediction-markets">Prediction Markets</a>' in INDEX:
    raise SystemExit("Prediction-markets navigation must remain hidden by default.")

script = INDEX.split("<script>", 1)[1].split("</script>", 1)[0]
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
    handle.write(script)
    handle.flush()
    check = subprocess.run(
        ["node", "--check", handle.name],
        capture_output=True,
        text=True,
        check=False,
    )
if check.returncode:
    raise SystemExit("Election Center JavaScript syntax check failed:\n" + check.stderr)

print("Prediction-markets UI fail-closed checks passed.")
