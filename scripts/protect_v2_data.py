#!/usr/bin/env python3
"""Preserve verified v2-owned election files while the legacy county publisher runs.

This is a transition bridge, not a new ingestion pipeline. It copies authoritative v2
aggregate files and any county explicitly marked with a v2 adapter from the current
live ref into the legacy publisher's generated data directory before publication.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

V2_AGGREGATES = (
    "data/statewide.json",
    "data/district-9.json",
    "data/congressional.json",
    "data/legislative.json",
)


def git_show(ref: str, path: str) -> bytes | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"{ref}:{path}"], stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return None


def load_json_bytes(raw: bytes | None, label: str) -> dict | None:
    if not raw:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected object JSON in {label}")
    return value


def verified_v2_aggregate(data: dict) -> bool:
    return (
        data.get("schemaVersion") == 2
        and data.get("coverageComplete") is True
        and data.get("displayStatus") != "withheld-incomplete"
        and isinstance(data.get("races"), list)
        and bool(data.get("races"))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-dir", type=Path, required=True)
    parser.add_argument("--live-ref", default="origin/main")
    args = parser.parse_args()

    generated = args.generated_dir
    generated.mkdir(parents=True, exist_ok=True)

    preserved_aggregates: list[str] = []
    for repo_path in V2_AGGREGATES:
        raw = git_show(args.live_ref, repo_path)
        if not raw:
            continue
        data = load_json_bytes(raw, f"{args.live_ref}:{repo_path}")
        if not data or not verified_v2_aggregate(data):
            raise RuntimeError(
                f"Refusing to preserve unverified v2 aggregate {args.live_ref}:{repo_path}"
            )
        target = generated / Path(repo_path).name
        target.write_bytes(raw)
        preserved_aggregates.append(repo_path)

    live_manifest = load_json_bytes(
        git_show(args.live_ref, "data/manifest.json"),
        f"{args.live_ref}:data/manifest.json",
    )
    generated_manifest_path = generated / "manifest.json"
    if not generated_manifest_path.exists():
        raise RuntimeError("Generated manifest missing")
    generated_manifest = json.loads(generated_manifest_path.read_text())

    preserved_counties: list[str] = []
    if live_manifest:
        for county, entry in (live_manifest.get("counties") or {}).items():
            if not isinstance(entry, dict):
                continue
            adapter = str(entry.get("adapter") or "").lower()
            if "v2" not in adapter:
                continue
            file_path = str(entry.get("file") or "")
            if not file_path.startswith("data/"):
                raise RuntimeError(f"Unsafe v2 county file path for {county}: {file_path!r}")
            raw = git_show(args.live_ref, file_path)
            if not raw:
                raise RuntimeError(f"Protected v2 county file missing for {county}: {file_path}")
            county_data = load_json_bytes(raw, f"{args.live_ref}:{file_path}")
            if not county_data or county_data.get("coverageComplete") is not True:
                raise RuntimeError(f"Protected v2 county is not coverage-complete: {county}")
            (generated / Path(file_path).name).write_bytes(raw)
            generated_manifest.setdefault("counties", {})[county] = entry
            preserved_counties.append(county)

    generated_manifest_path.write_text(json.dumps(generated_manifest, indent=2) + "\n")
    print(
        "Protected v2 data: "
        f"{len(preserved_aggregates)} aggregates; "
        f"{len(preserved_counties)} counties ({', '.join(preserved_counties) or 'none'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
