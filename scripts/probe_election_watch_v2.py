#!/usr/bin/env python3
"""Discover current-election Florida Election Watch routes from a known-good primary contest page."""
from __future__ import annotations

import json
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ANCHOR = "https://floridaelectionwatch.gov/ContestResultsByCounty/140091"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IRC-Media-Election-Center/2.0; +https://www.ircmedia.net/)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TARGET_TERMS = (
    "united states senator",
    "governor",
    "chief financial officer",
    "commissioner of agriculture",
    "state offices",
    "contest results",
)


def main() -> int:
    response = requests.get(ANCHOR, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        text = " ".join(a.stripped_strings).strip()
        href = urljoin(response.url, a["href"])
        hay = f"{text} {href}".lower()
        if any(term in hay for term in TARGET_TERMS) or "floridaelectionwatch.gov" in href.lower():
            links.append({"text": text, "href": href})

    forms = []
    for form in soup.find_all("form"):
        forms.append(
            {
                "action": urljoin(response.url, form.get("action") or ""),
                "method": (form.get("method") or "get").lower(),
                "inputs": [
                    {"name": i.get("name"), "value": i.get("value"), "type": i.get("type")}
                    for i in form.find_all("input")
                    if i.get("name")
                ],
                "selects": [
                    {
                        "name": s.get("name"),
                        "options": [
                            {"value": o.get("value"), "text": " ".join(o.stripped_strings).strip()}
                            for o in s.find_all("option")
                        ],
                    }
                    for s in form.find_all("select")
                ],
            }
        )

    payload = {
        "anchor": response.url,
        "title": soup.title.get_text(" ", strip=True) if soup.title else None,
        "pageMarkers": [x for x in ["2026 Primary Election", "Representative in Congress, District 9", "Republican"] if x.lower() in " ".join(soup.stripped_strings).lower()],
        "links": links,
        "forms": forms,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
