#!/usr/bin/env python3
"""
Fetch ICD-10 WHO from the WHO ICD API and serialize to Turtle.

Auth: WHO OAuth2 client credentials — set CLIENT_ID and CLIENT_SECRET in env/.env.
The token is valid for ~1 hour; this script re-authenticates automatically if it
expires mid-run.

The WHO API is traversed breadth-first, with every response cached to
tmp/cache/<encoded-uri>/response.json. If the run is interrupted, re-running with
an existing cache will resume without re-fetching already-cached nodes.

Usage:
    python scripts/acquire.py --output tmp/icd10who_raw.ttl
    python scripts/acquire.py --output tmp/icd10who_raw.ttl --release 2019
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef
from rdflib.namespace import SKOS
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

disable_warnings(InsecureRequestWarning)

# ── Constants ──────────────────────────────────────────────────────────────────

TOKEN_ENDPOINT = "https://icdaccessmanagement.who.int/connect/token"
RELEASES_ENDPOINT = "https://id.who.int/icd/release/10"
ICD10WHO_NS = Namespace("https://icd.who.int/browse10/2019/en#/")

ENV_FILE = Path(__file__).parent.parent / "env" / ".env"
DEFAULT_CACHE_DIR = Path(__file__).parent.parent / "tmp" / "cache"

# ── Auth ───────────────────────────────────────────────────────────────────────


def _get_token(client_id: str, client_secret: str) -> str:
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "icdapi_access",
        "grant_type": "client_credentials",
    }
    r = requests.post(TOKEN_ENDPOINT, data=payload, verify=False, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _make_headers(token: str, language: str = "en", api_version: str = "v2") -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Language": language,
        "API-Version": api_version,
    }


# ── Release resolution ─────────────────────────────────────────────────────────


def _resolve_release_uri(headers: dict, release: str) -> str:
    r = requests.get(RELEASES_ENDPOINT, headers=headers, verify=False, timeout=30)
    r.raise_for_status()
    data = r.json()
    if release == "latest":
        return data["latestRelease"]
    year_map = {url.rsplit("/", 1)[-1]: url for url in data["release"]}
    if release not in year_map:
        raise ValueError(f"Release '{release}' not found. Available: {list(year_map)}")
    return year_map[release]


# ── Caching helpers ────────────────────────────────────────────────────────────


def _cache_path(uri: str, cache_dir: Path) -> Path:
    safe = quote(uri, safe="")[:200]
    return cache_dir / safe / "response.json"


def _fetch_node(uri: str, headers: dict, cache_dir: Path, use_cache: bool) -> dict:
    path = _cache_path(uri, cache_dir)
    if use_cache and path.exists():
        with open(path) as f:
            return json.load(f)
    r = requests.get(uri, headers=headers, verify=False, timeout=30)
    if r.status_code == 401:
        raise PermissionError("WHO API token expired")
    r.raise_for_status()
    data = r.json()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)
    return data


# ── BFS traversal ──────────────────────────────────────────────────────────────


def _traverse(
    root_uri: str,
    client_id: str,
    client_secret: str,
    cache_dir: Path,
    use_cache: bool,
    language: str,
    api_version: str,
) -> dict[str, dict]:
    """BFS traversal of ICD-10 WHO API. Returns {uri: node_data} for all nodes."""
    token = _get_token(client_id, client_secret)
    headers = _make_headers(token, language, api_version)
    token_fetched_at = time.time()

    results: dict[str, dict] = {}
    queue: list[str] = [root_uri]
    visited: set[str] = set()
    total = 0

    print(f"Starting BFS from {root_uri}", file=sys.stderr)

    while queue:
        uri = queue.pop(0)
        if uri in visited:
            continue
        visited.add(uri)

        # Re-authenticate if token is near expiry (55 min threshold)
        if time.time() - token_fetched_at > 55 * 60:
            print("Refreshing WHO API token...", file=sys.stderr)
            token = _get_token(client_id, client_secret)
            headers = _make_headers(token, language, api_version)
            token_fetched_at = time.time()

        try:
            data = _fetch_node(uri, headers, cache_dir, use_cache)
        except PermissionError:
            print("Token expired mid-run — re-authenticating...", file=sys.stderr)
            token = _get_token(client_id, client_secret)
            headers = _make_headers(token, language, api_version)
            token_fetched_at = time.time()
            data = _fetch_node(uri, headers, cache_dir, use_cache)

        results[uri] = data
        total += 1
        if total % 500 == 0:
            print(f"  {total} nodes fetched...", file=sys.stderr)

        for child_uri in data.get("child", []):
            if child_uri not in visited:
                queue.append(child_uri)

    print(f"Traversal complete: {total} nodes", file=sys.stderr)
    return results


# ── RDF serialization ──────────────────────────────────────────────────────────


def _code_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _build_graph(nodes: dict[str, dict], release_uri: str) -> Graph:
    g = Graph()
    g.namespace_manager.bind("ICD10WHO", ICD10WHO_NS)
    g.namespace_manager.bind("owl", OWL)
    g.namespace_manager.bind("rdfs", RDFS)
    g.namespace_manager.bind("skos", SKOS)

    ont_node = URIRef(str(ICD10WHO_NS))
    g.add((ont_node, RDF.type, OWL.Ontology))
    g.add((ont_node, RDFS.label, Literal("ICD10WHO")))
    g.add(
        (ont_node, RDFS.comment, Literal(f"Created from ICD-10 WHO API release: {release_uri}"))
    )

    # collect valid node URIs for parent resolution
    valid_uris: set[str] = set(nodes)

    for uri, data in nodes.items():
        code = _code_from_uri(uri)
        cls = ICD10WHO_NS[code]

        title = data.get("title", {})
        label = title.get("@value") if isinstance(title, dict) else str(title)
        if not label:
            continue

        parent_uris: list[str] = data.get("parent", [])

        g.add((cls, RDF.type, OWL.Class))
        g.add((cls, RDFS.label, Literal(label)))
        g.add((cls, SKOS.notation, Literal(code)))
        g.add((cls, RDFS.seeAlso, Literal(uri)))

        # Use owl:Thing for top-level categories (parent is the release root)
        icd_parents = [p for p in parent_uris if p in valid_uris]
        if icd_parents:
            for parent_uri in icd_parents:
                parent_code = _code_from_uri(parent_uri)
                g.add((cls, RDFS.subClassOf, ICD10WHO_NS[parent_code]))
        else:
            g.add((cls, RDFS.subClassOf, OWL.Thing))

    return g


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire ICD-10 WHO from WHO API → Turtle")
    parser.add_argument("--output", type=Path, required=True, help="Output TTL path")
    parser.add_argument(
        "--release", default="latest", help="Release year (e.g. 2019) or 'latest'"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Ignore existing cache and re-fetch all nodes"
    )
    parser.add_argument("--language", default="en")
    parser.add_argument("--api-version", default="v2")
    args = parser.parse_args()

    load_dotenv(ENV_FILE)
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    if not client_id or not client_secret:
        print(
            f"Error: CLIENT_ID and CLIENT_SECRET must be set in {ENV_FILE}", file=sys.stderr
        )
        sys.exit(1)

    use_cache = not args.no_cache
    cache_dir = DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Resolve release URI
    print("Resolving ICD-10 release URI...", file=sys.stderr)
    token = _get_token(client_id, client_secret)
    headers = _make_headers(token, args.language, args.api_version)
    release_uri = _resolve_release_uri(headers, args.release)
    print(f"Release URI: {release_uri}", file=sys.stderr)

    # Traverse
    nodes = _traverse(
        root_uri=release_uri,
        client_id=client_id,
        client_secret=client_secret,
        cache_dir=cache_dir,
        use_cache=use_cache,
        language=args.language,
        api_version=args.api_version,
    )

    # Remove the release root node itself (not a disease class)
    nodes.pop(release_uri, None)

    # Build and serialize RDF graph
    print("Serializing RDF graph...", file=sys.stderr)
    g = _build_graph(nodes, release_uri)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(args.output), format="turtle")
    print(f"Written: {args.output} ({len(g)} triples)", file=sys.stderr)


if __name__ == "__main__":
    main()
