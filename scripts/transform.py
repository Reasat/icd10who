#!/usr/bin/env python3
"""
Serialize ICD-10 WHO component OWL → schema-conformant YAML.

Reads rdfs:label, oboInOwl:hasExactSynonym (generated from label by SPARQL),
rdfs:subClassOf, skos:notation, and owl:deprecated from the ROBOT-processed OWL.

Input:  icd10who.owl (after make build)
Output: icd10who.linkml.yml  (conforms to linkml/mondo_source_schema.yaml)

Usage:
    python scripts/transform.py \\
        --input icd10who.owl \\
        --schema linkml/mondo_source_schema.yaml \\
        --output icd10who.linkml.yml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef
from rdflib.namespace import Namespace, SKOS

# ── Namespaces ─────────────────────────────────────────────────────────────────

OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
ICD10WHO_NS_PREFIX = "https://icd.who.int/browse10/"
ICD10WHO_CURIE_PREFIX = "ICD10WHO:"

# The exact namespace base written by acquire.py
ICD10WHO_NS = Namespace("https://icd.who.int/browse10/2019/en#/")


# ── IRI helpers ────────────────────────────────────────────────────────────────


def is_icd10who_iri(iri: str) -> bool:
    return iri.startswith(ICD10WHO_NS_PREFIX)


def iri_to_curie(iri: str) -> str:
    code = iri.rsplit("/", 1)[-1].lstrip("#")
    return f"{ICD10WHO_CURIE_PREFIX}{code}"


# ── Graph helpers ──────────────────────────────────────────────────────────────


def _literal_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out = [str(o) for o in g.objects(subj, pred) if isinstance(o, Literal)]
    return sorted(set(v for v in out if v.strip()))


def _get_parents(g: Graph, subj: URIRef) -> list[str]:
    parents = []
    for o in g.objects(subj, RDFS.subClassOf):
        if isinstance(o, URIRef) and is_icd10who_iri(str(o)):
            parents.append(iri_to_curie(str(o)))
    return sorted(parents)


# ── Extraction ─────────────────────────────────────────────────────────────────


def extract_terms(g: Graph) -> list[dict]:
    candidate_iris = sorted(
        str(s)
        for s in g.subjects(RDF.type, OWL.Class)
        if isinstance(s, URIRef) and is_icd10who_iri(str(s))
    )

    terms: list[dict] = []
    for iri in candidate_iris:
        subj = URIRef(iri)
        curie = iri_to_curie(iri)

        label_node = g.value(subj, RDFS.label)
        if label_node is None:
            continue
        label = str(label_node)

        dep_node = g.value(subj, OWL.deprecated)
        is_deprecated = dep_node is not None and str(dep_node).strip().lower() == "true"

        exact_syns = _literal_values(g, subj, OBOINOWL.hasExactSynonym)
        parent_curies = _get_parents(g, subj)
        has_thing_parent = OWL.Thing in g.objects(subj, RDFS.subClassOf)
        is_root = has_thing_parent or len(parent_curies) == 0

        term: dict = {"id": curie, "label": label}
        if is_deprecated:
            term["deprecated"] = True
        if exact_syns:
            term["exact_synonyms"] = exact_syns
        if is_root:
            term["is_root"] = True
        else:
            term["parents"] = parent_curies

        terms.append(term)

    return terms


# ── Main ───────────────────────────────────────────────────────────────────────


def transform(input_path: Path, output_path: Path) -> None:
    print(f"Parsing component OWL: {input_path}", file=sys.stderr)
    g = Graph()
    g.parse(str(input_path))

    terms = extract_terms(g)
    active = sum(1 for t in terms if not t.get("deprecated"))
    deprecated = sum(1 for t in terms if t.get("deprecated"))
    print(
        f"Extracted {len(terms)} ICD10WHO terms ({active} active, {deprecated} deprecated)",
        file=sys.stderr,
    )

    doc = {
        "title": "ICD10WHO",
        "version": "2019",
        "terms": terms,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        yaml.dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Written: {output_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serialize ICD10WHO component OWL → schema YAML")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not args.schema.exists():
        print(f"Error: schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)

    transform(args.input, args.output)


if __name__ == "__main__":
    main()
