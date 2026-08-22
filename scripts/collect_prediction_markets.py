#!/usr/bin/env python3
"""Collect a validated Kalshi snapshot for IRC Media Prediction Markets."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

API_BASE = "https://external-api.kalshi.com/trade-api/v2"
USER_AGENT = "IRC-Media-Election-Center/1.0 (prediction markets collector)"
DISCLOSURE = (
    "Market prices reflect traders' expectations and are not a representative "
    "public-opinion poll, an IRC Media projection or an election result."
)
EVENTS = (
    {
        "eventTicker": "CONTROLH-2026",
        "eventId": "kalshi-controlh-2026",
        "title": "Which party will control the U.S. House?",
        "sourceUrl": "https://kalshi.com/markets/controlh",
        "resolutionSummary": (
            "Resolved by 2026 House control, ordinarily determined by the party "
            "identification of the Speaker on February 1, 2027, with possible early "
            "determination from a consensus of media calls."
        ),
        "outcomes": (
            ("CONTROLH-2026-D", "Democratic Party"),
            ("CONTROLH-2026-R", "Republican Party"),
        ),
    },
    {
        "eventTicker": "CONTROLS-2026",
        "eventId": "kalshi-controls-2026",
        "title": "Which party will control the U.S. Senate?",
        "sourceUrl": "https://kalshi.com/markets/controls",
        "resolutionSummary": (
            "Resolved by 2026 Senate control, ordinarily determined by the party "
            "identification of the President pro tempore on February 1, 2027, with "
            "possible early determination from a consensus of media calls."
        ),
        "outcomes": (
            ("CONTROLS-2026-D", "Democratic Party"),
            ("CONTROLS-2026-R", "Republican Party"),
        ),
    },
)


def fetch_json(url: str) -> dict:
    error: Exception | None = None
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("API response is not an object")
                return payload
        except Exception as current:
            error = current
            if attempt < 2:
                time.sleep(2**attempt)
    raise RuntimeError(f"Kalshi request failed for {url}: {error}")


def number(value: object, field: str) -> float:
    try:
        parsed = float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} is not numeric") from None
    if parsed < 0:
        raise ValueError(f"{field} cannot be negative")
    return round(parsed, 2)


def price_pct(market: dict, dollars_field: str, cents_field: str) -> float:
    if market.get(dollars_field) is not None:
        return round(number(market[dollars_field], dollars_field) * 100, 2)
    if market.get(cents_field) is not None:
        return number(market[cents_field], cents_field)
    raise ValueError(f"market {market.get('ticker')} lacks {dollars_field}")


def fixed_number(market: dict, fp_field: str, legacy_field: str) -> float:
    if market.get(fp_field) is not None:
        return number(market[fp_field], fp_field)
    if market.get(legacy_field) is not None:
        return number(market[legacy_field], legacy_field)
    raise ValueError(f"market {market.get('ticker')} lacks {fp_field}")


def outcome_from_market(market: dict, ticker: str, label: str) -> dict:
    if market.get("ticker") != ticker:
        raise ValueError(f"ticker mismatch for {ticker}")
    status = str(market.get("status", "")).lower()
    if status in {"closed", "settled", "finalized"}:
        raise ValueError(f"{ticker} is no longer an active market")
    bid = price_pct(market, "yes_bid_dollars", "yes_bid")
    ask = price_pct(market, "yes_ask_dollars", "yes_ask")
    last = price_pct(market, "last_price_dollars", "last_price")
    volume = fixed_number(market, "volume_fp", "volume")
    volume_24h = fixed_number(market, "volume_24h_fp", "volume_24h")
    open_interest = fixed_number(market, "open_interest_fp", "open_interest")
    if not 0 <= bid <= ask <= 100 or ask - bid > 5:
        raise ValueError(f"{ticker} failed the maximum five-point spread gate")
    if volume < 1000 or open_interest < 100:
        raise ValueError(f"{ticker} failed liquidity gates")
    return {
        "ticker": ticker,
        "label": label,
        "bidPct": bid,
        "askPct": ask,
        "lastTradePct": last,
        "volumeContracts": volume,
        "volume24hContracts": volume_24h,
        "openInterestContracts": open_interest,
    }


def build_snapshot(fetcher=fetch_json) -> dict:
    events = []
    seen_tickers: set[str] = set()
    for config in EVENTS:
        event_ticker = config["eventTicker"]
        api_url = f"{API_BASE}/events/{event_ticker}"
        payload = fetcher(api_url)
        event = payload.get("event")
        markets = payload.get("markets")
        if not isinstance(event, dict) or event.get("event_ticker") != event_ticker:
            raise ValueError(f"{event_ticker} event identity failed")
        if not isinstance(markets, list):
            raise ValueError(f"{event_ticker} response lacks markets")
        by_ticker = {
            market.get("ticker"): market
            for market in markets
            if isinstance(market, dict) and market.get("ticker")
        }
        outcomes = []
        for ticker, label in config["outcomes"]:
            if ticker in seen_tickers:
                raise ValueError(f"duplicate configured ticker: {ticker}")
            seen_tickers.add(ticker)
            if ticker not in by_ticker:
                raise ValueError(f"{event_ticker} response lacks required market {ticker}")
            outcomes.append(outcome_from_market(by_ticker[ticker], ticker, label))
        events.append(
            {
                "eventId": config["eventId"],
                "title": config["title"],
                "sourceId": "kalshi",
                "sourceUrl": config["sourceUrl"],
                "apiUrl": api_url,
                "resolutionSummary": config["resolutionSummary"],
                "outcomes": outcomes,
            }
        )
    return {
        "schemaVersion": 1,
        "status": "published",
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceAttribution": [
            {
                "sourceId": "kalshi",
                "name": "Kalshi",
                "url": "https://kalshi.com/markets/controlh",
            }
        ],
        "disclosure": DISCLOSURE,
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/prediction-markets.json")
    args = parser.parse_args()
    snapshot = build_snapshot()
    output = Path(args.output)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(
        json.dumps(
            {
                "generatedAt": snapshot["generatedAt"],
                "events": len(snapshot["events"]),
                "tickers": sum(len(event["outcomes"]) for event in snapshot["events"]),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
