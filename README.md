# icd10who

Preprocessed ICD-10 WHO source for Mondo ingest.

## Setup

1. Register at https://icd.who.int/icdapi to get API credentials
2. Copy `env/.env.example` → `env/.env` and fill in `CLIENT_ID` and `CLIENT_SECRET`
3. Install dependencies: `uv sync`
4. Align LinkML with the mondo-source-ingest pin (main-branch `linkml` / `linkml-runtime`, `linkml-owl` 0.5.0): `make dependencies`

## Run

```bash
make acquire       # fetch from WHO API → tmp/icd10who_raw.ttl  (~2.5 hrs, cached after first run)
make build         # ROBOT preprocessing → icd10who.owl
make build-release # LinkML YAML + validate + verify + derived OWL
make verify        # re-run structural checks on icd10who.linkml.yaml (after build-release)
```

## Outputs

| File | Description |
|---|---|
| `icd10who.linkml.yaml` | Primary artefact for Mondo ingest |
| `icd10who.owl` | ROBOT-preprocessed OWL |
| `icd10who_from_linkml.owl` | LinkML-derived OWL |

## Docs

| Doc | Contents |
|---|---|
| [`docs/plan.md`](docs/plan.md) | Pipeline architecture, field mappings, ID scheme |
| [`docs/release_notes.md`](docs/release_notes.md) | Ontology stats and verification results per release |
| [`docs/pipeline_incidents.md`](docs/pipeline_incidents.md) | Pipeline incidents: errors, deviations, resolutions |
