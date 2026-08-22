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
    "Object.values(gates).every(value=>value===true)",
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
    "How to read this page",
    "Example: “YES” costs 60 cents",
    "If the event happens, it pays $1",
    "It does not mean 60% of voters support something",
    "The highest price a buyer is currently offering.",
    "The lowest price a seller is currently willing to accept.",
    "The number of contracts traded—not the number of people participating.",
    "2028 Election Markets",
    "View Full 2028 Category",
    "function renderLongRangeMarkets(",
    "predictionMarketsData.longRangeEvents||[]",
    "LIVE MARKET MIDPOINTS",
    "market-bar-track",
    "market-bar-fill",
    "market-midpoint",
    "market-mini-track",
    "market-mini-fill",
    "mid=Math.max(0,Math.min(100,(bid+ask)/2))",
    "Bar length shows the midpoint of the current bid–ask range.",
    "It is not a poll or IRC Media projection.",
    "Each bar is independent and may not add to 100%.",
    "longRange.length>=6",
    "Nominees, candidates and winners",
    "Matchups and tickets",
    "Election process and final results",
    "Current Events to Watch",
    "View this market on Kalshi",
    "Explore Prediction Markets on Kalshi",
    "Trading involves risk",
    "function hideExpiredCurrentMarkets()",
    "hideExpiredCurrentMarkets();setCenterView('results'",
    'id="home-nav" type="button">Election Center Home',
    "window.scrollTo({top:0,behavior:'smooth'})",
    "function renderStatewideLanding()",
    "document.getElementById('races').innerHTML=renderStatewideLanding()",
    ".markets-guide-lead,.markets-example p,.markets-not-poll,.markets-term,.markets-term b{font-size:16px",
    ".market-directory-live-price{font-size:14px}",
]

missing = [token for token in REQUIRED if token not in INDEX]
if missing:
    raise SystemExit(
        "Prediction-markets UI validation failed closed; missing: "
        + ", ".join(missing)
    )

if 'id="markets-nav" href="#prediction-markets">Prediction Markets</a>' in INDEX:
    raise SystemExit("Prediction-markets navigation must remain hidden by default.")

if "referral=" in INDEX or "utm_" in INDEX:
    raise SystemExit("Prediction-market links must remain direct and non-referral.")

if INDEX.count("data-kalshi-2028") < 15:
    raise SystemExit("The 2028 directory must retain most major Kalshi election markets.")

if INDEX.count("data-event-ticker=") < 10:
    raise SystemExit("Major 2028 directory items must support validated live summaries.")

market_guard = INDEX.split("function predictionMarketsDisplaySafe", 1)[1].split(
    "function compactContracts", 1
)[0]
if "readiness?.automatedPublishingEnabled===true" in market_guard:
    raise SystemExit("Approved isolated collection must not disable public display.")

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
