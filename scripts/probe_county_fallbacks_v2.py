#!/usr/bin/env python3
"""Probe disconnected Florida county election-result pages for reusable v2 feed patterns.

Reads the existing manifest only to discover official destinations. It does not run or
reuse legacy recovery scripts and does not publish candidate totals. The output is a
compact diagnostic inventory used to design a small number of clean county adapters.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
DOWNLOAD_RE = re.compile(r"\.(?:csv|json|xml|txt|zip)(?:$|[?#])", re.I)
KEYWORDS = ("csv", "export", "download", "report", "results", "summary", "candidate")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def probe(county: str, url: str) -> dict:
    item = {"county": county, "sourceUrl": url, "reachable": False}
    try:
        response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        item.update({
            "httpStatus": response.status_code,
            "finalUrl": response.url,
            "contentType": response.headers.get("content-type", ""),
        })
        response.raise_for_status()
        item["reachable"] = True
    except Exception as exc:
        item["error"] = str(exc)
        return item

    soup = BeautifulSoup(response.text, "html.parser")
    item["title"] = clean(soup.title.get_text(" ", strip=True) if soup.title else "")
    links = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        text = clean(a.get_text(" ", strip=True))
        absolute = urljoin(response.url, href)
        haystack = f"{text} {href}".lower()
        if DOWNLOAD_RE.search(href) or any(k in haystack for k in KEYWORDS):
            links.append({"text": text[:140], "url": absolute})
    # de-duplicate while preserving order
    seen = set()
    deduped = []
    for link in links:
        key = link["url"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(link)
    item["candidateLinks"] = deduped[:40]

    scripts = []
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            scripts.append(urljoin(response.url, src))
    item["scriptSources"] = list(dict.fromkeys(scripts))[:30]

    tables = []
    for table in soup.find_all("table"):
        text = clean(table.get_text(" ", strip=True))
        if text:
            tables.append(text[:600])
    item["tableSamples"] = tables[:8]

    page_text = clean(soup.get_text(" ", strip=True))
    item["signals"] = {
        "hasCounty": "county" in page_text.lower(),
        "hasCandidate": "candidate" in page_text.lower(),
        "hasTotal": "total" in page_text.lower(),
        "hasPrecinct": "precinct" in page_text.lower(),
        "htmlTables": len(soup.find_all("table")),
        "candidateLinkCount": len(deduped),
        "scriptCount": len(scripts),
    }
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("build/county-fallback-probe-v2.json"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    counties = manifest.get("counties") or {}
    fallbacks = []
    for county in sorted(counties):
        entry = counties[county] or {}
        if entry.get("connected") is True:
            continue
        url = entry.get("sourceUrl")
        if not url:
            fallbacks.append({"county": county, "sourceUrl": None, "reachable": False, "error": "official sourceUrl missing"})
            continue
        fallbacks.append(probe(county, url))

    payload = {
        "status": "complete",
        "fallbackCount": len(fallbacks),
        "reachableCount": sum(1 for x in fallbacks if x.get("reachable")),
        "counties": fallbacks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"PROBED: {payload['fallbackCount']} fallbacks; {payload['reachableCount']} official pages reachable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
