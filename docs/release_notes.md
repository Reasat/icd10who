# ICD10WHO Ingest — Release Notes

## Initial release

### Source
- WHO ICD-10 API, release 2019 (`http://id.who.int/icd/release/10/2019`)

### Ontology statistics
| Metric | Value |
|---|---|
| Total terms | 12,597 |
| Active terms | 12,597 |
| Deprecated terms | 0 |
| Root terms | 22 (one per ICD-10 chapter) |
| Exact synonyms generated | 12,597 (one per term, from label) |
| Definitions | 0 |

### Artefacts
| File | Description |
|---|---|
| `icd10who.yaml` | Primary LinkML YAML — ~2.2 MB |
| `icd10who.owl` | Final LinkML-derived OWL (Functional Syntax) — ~4.1 MB |

ROBOT-preprocessed OWL (`tmp/transformed-icd10who.owl`, ~12 MB) is a local/CI intermediate only, not a GitHub Release asset (mondo-source-ingest OWL-pipeline convention).

### Notes
- Term count (12,597) is significantly higher than the previously committed TTL from
  `monarch-initiative/icd10who` (4,894 terms). The difference is due to the old
  tool's Python recursion limit truncating the traversal mid-run. The new BFS-based
  `acquire.py` correctly traverses the full hierarchy.
- No deprecated terms exist in the 2019 ICD-10 WHO release.
- Exact synonyms are generated from labels via `sparql/exact_syn_from_label.ru`,
  following the same convention as ICD10CM and ORDO.
