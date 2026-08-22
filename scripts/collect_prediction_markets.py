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


LONG_RANGE_EVENTS = (
    ("KXPRESNOMD-28", "2028 Democratic presidential nominee", "https://kalshi.com/markets/kxpresnomd/democratic-primary-winner/kxpresnomd-28", "Resolves according to the Democratic Party's official 2028 presidential nomination under Kalshi's published rules."),
    ("KXPRESNOMR-28", "2028 Republican presidential nominee", "https://kalshi.com/markets/kxpresnomr/republican-primary-winner/kxpresnomr-28", "Resolves according to the Republican Party's official 2028 presidential nomination under Kalshi's published rules."),
    ("KXPRESPERSON-28", "2028 U.S. Presidential Election winner", "https://kalshi.com/markets/kxpresperson/pres-person/kxpresperson-28", "Resolves according to the winner of the 2028 U.S. presidential election under Kalshi's published rules."),
    ("KXVPRESNOMD-28", "2028 Democratic vice-presidential nominee", "https://kalshi.com/markets/kxvpresnomd/democratic-vp-nom/kxvpresnomd-28", "Resolves according to the Democratic Party's official 2028 vice-presidential nomination."),
    ("KXVPRESNOMR-28", "2028 Republican vice-presidential nominee", "https://kalshi.com/markets/kxvpresnomr/republican-vp-nom/kxvpresnomr-28", "Resolves according to the Republican Party's official 2028 vice-presidential nomination."),
    ("KX2028DRUN-28", "Who will seek the 2028 Democratic nomination?", "https://kalshi.com/markets/kx2028drun/2028-d-running/kx2028drun-28", "Resolves separately for each listed person according to Kalshi's published candidacy criteria."),
    ("KX2028RRUN-28", "Who will seek the 2028 Republican nomination?", "https://kalshi.com/markets/kx2028rrun/2028-r-running/kx2028rrun-28", "Resolves separately for each listed person according to Kalshi's published candidacy criteria."),
    ("KXPRESOUTCOME-28NOV07", "2028 presidential race: exact outcome", "https://kalshi.com/markets/kxpresoutcome/2028-presidential-election-exact-outcome/kxpresoutcome-28nov07", "Resolves to the exact listed winner-and-defeated-candidate combination under Kalshi's published rules."),
    ("KXPRESMATCHUP-28NOV07", "2028 presidential nominee matchup", "https://kalshi.com/markets/kxpresmatchup/2028-presidential-matchup/kxpresmatchup-28nov07", "Resolves to the listed major-party presidential nominee matchup under Kalshi's published rules."),
    ("KXPRESPARTY-2028", "Party winning the 2028 presidency", "https://kalshi.com/markets/kxpresparty/party-winning-presidency/kxpresparty-2028", "Resolves according to the political party winning the 2028 U.S. presidential election."),
    ("POWER-28", "2028 presidency, House and Senate control", "https://kalshi.com/markets/power/party-power/power-28", "Resolves to the listed combination of presidential, House and Senate party control after the 2028 election."),
    ("POPVOTEMOV-28NOV07", "2028 popular-vote margin", "https://kalshi.com/markets/popvotemov/popular-vote-margin-of-victory/popvotemov-28nov07", "Resolves according to the national popular-vote margin range specified in each contract."),
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


def dynamic_outcome(market: dict) -> dict:
    ticker = str(market.get("ticker", "")).strip()
    label = str(
        market.get("yes_sub_title")
        or market.get("subtitle")
        or market.get("title")
        or ""
    ).strip()
    if not ticker or not label:
        raise ValueError("dynamic market lacks ticker or outcome label")
    return outcome_from_market(market, ticker, label)


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
                "eventTicker": event_ticker,
                "title": config["title"],
                "sourceId": "kalshi",
                "sourceUrl": config["sourceUrl"],
                "apiUrl": api_url,
                "resolutionSummary": config["resolutionSummary"],
                "outcomes": outcomes,
            }
        )

    long_range_events = []
    skipped_long_range = []
    for event_ticker, title, source_url, resolution in LONG_RANGE_EVENTS:
        api_url = f"{API_BASE}/events/{event_ticker}"
        try:
            payload = fetcher(api_url)
            event = payload.get("event")
            markets = payload.get("markets")
            if not isinstance(event, dict) or event.get("event_ticker") != event_ticker:
                raise ValueError("event identity failed")
            if not isinstance(markets, list):
                raise ValueError("response lacks markets")
            eligible = []
            labels: set[str] = set()
            for market in markets:
                if not isinstance(market, dict):
                    continue
                ticker = str(market.get("ticker", ""))
                if not ticker or ticker in seen_tickers:
                    continue
                try:
                    outcome = dynamic_outcome(market)
                except ValueError:
                    continue
                if outcome["label"] in labels:
                    continue
                labels.add(outcome["label"])
                eligible.append(outcome)
            eligible.sort(
                key=lambda outcome: (
                    -(outcome["bidPct"] + outcome["askPct"]) / 2,
                    -outcome["volumeContracts"],
                    outcome["label"],
                )
            )
            outcomes = eligible[:3]
            if len(outcomes) < 2:
                raise ValueError("fewer than two outcomes passed quote and liquidity gates")
            seen_tickers.update(outcome["ticker"] for outcome in outcomes)
            long_range_events.append(
                {
                    "eventId": "kalshi-" + event_ticker.lower(),
                    "eventTicker": event_ticker,
                    "title": title,
                    "sourceId": "kalshi",
                    "sourceUrl": source_url,
                    "apiUrl": api_url,
                    "resolutionSummary": resolution,
                    "outcomes": outcomes,
                }
            )
        except Exception as error:
            skipped_long_range.append(
                {"eventTicker": event_ticker, "reason": str(error)}
            )
    if len(long_range_events) < 6:
        raise ValueError(
            "fewer than six 2028 events passed live compatibility gates: "
            + json.dumps(skipped_long_range)
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
        "longRangeEvents": long_range_events,
        "collectionWarnings": skipped_long_range,
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
                "longRangeEvents": len(snapshot["longRangeEvents"]),
                "skippedLongRangeEvents": len(snapshot["collectionWarnings"]),
                "tickers": sum(
                    len(event["outcomes"])
                    for event in snapshot["events"] + snapshot["longRangeEvents"]
                ),
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
