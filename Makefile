# ICD10WHO preprocessed build
#
# Pipeline:
#   make acquire        — fetch ICD-10 WHO from WHO API → tmp/icd10who_raw.ttl
#   make build          — ROBOT preprocessing → icd10who.owl
#   make build-release  — build + transform → validate → verify → LinkML OWL
#
# Requires: ROBOT (≥ 1.9), obolibrary/odkfull Docker image for CI, uv for Python.
# Auth: set CLIENT_ID and CLIENT_SECRET in env/.env (see env/.env.example).
# CI should run `make dependencies` after `uv sync` so linkml/linkml-runtime match
# the mondo-source-ingest workaround (main-branch linkml-runtime; linkml-owl 0.5.0).

ROBOT       ?= robot
ROBOT_PLUGINS_DIRECTORY ?= /home/$(USER)/.robot/plugins
PYTHON      ?= python3
UV          ?= uv
UV_RUN      ?= uv run --no-sync
CONFIG_DIR  := config
SCRIPTS_DIR := scripts
SPARQL_DIR  := sparql
TMP_DIR     := tmp
OUTPUT_OWL  := icd10who.owl
OUTPUT_OWL_LINKML := icd10who_from_linkml.owl
MIRROR_OWL  := $(TMP_DIR)/mirror-icd10who.owl
RAW_TTL     := $(TMP_DIR)/icd10who_raw.ttl
YAML_OUT    := icd10who.linkml.yaml
SCHEMA      := linkml/mondo_source_schema.yaml
ONTOLOGY_IRI := https://github.com/monarch-initiative/icd10who/releases/latest/download/icd10who.owl
URIBASE     := http://purl.obolibrary.org/obo
TODAY       ?= $(shell date +%Y-%m-%d)

.PHONY: all build build-release acquire clean dependencies verify

all: build

$(TMP_DIR):
	mkdir -p $(TMP_DIR)

# ── Acquire: WHO API → Turtle ─────────────────────────────────────────────────
$(RAW_TTL): | $(TMP_DIR)
	$(UV_RUN) python $(SCRIPTS_DIR)/acquire.py --output $@
	@echo "Acquired: $@"

acquire: $(RAW_TTL)

# ── Mirror: merge + normalize ─────────────────────────────────────────────────
$(MIRROR_OWL): $(RAW_TTL) | $(TMP_DIR)
	ROBOT_PLUGINS_DIRECTORY=$(ROBOT_PLUGINS_DIRECTORY) \
	$(ROBOT) merge -i $(RAW_TTL) \
		odk:normalize --add-source true \
		-o $@
	@echo "Built $@"

# ── Component: normalize xrefs, add exact synonyms, strip non-allowlisted props ─
$(OUTPUT_OWL): $(MIRROR_OWL) \
		$(CONFIG_DIR)/properties.txt \
		$(SPARQL_DIR)/fix_xref_prefixes.ru \
		$(SPARQL_DIR)/exact_syn_from_label.ru
	$(ROBOT) merge -i $(MIRROR_OWL) \
		query \
			--update $(SPARQL_DIR)/fix_xref_prefixes.ru \
		query \
			--update $(SPARQL_DIR)/exact_syn_from_label.ru \
		remove -T $(CONFIG_DIR)/properties.txt --select complement --select properties --trim true \
		annotate \
			--ontology-iri $(URIBASE)/mondo/sources/icd10who.owl \
			--version-iri $(URIBASE)/mondo/sources/$(TODAY)/icd10who.owl \
		-o $@
	@echo "Built $@"

build: $(OUTPUT_OWL)
	@echo "Build complete: $(OUTPUT_OWL)"

# Pin linkml-owl + main-branch linkml/linkml-runtime (comma-in-synonym workaround).
dependencies:
	$(UV) pip install linkml-owl==0.5.0 \
		"linkml @ git+https://github.com/linkml/linkml.git@main#subdirectory=packages/linkml" \
		"linkml-runtime @ git+https://github.com/linkml/linkml.git@main#subdirectory=packages/linkml_runtime"

# ── Release: build + LinkML transform + validate + verify + data2owl ───────────
build-release: build
	$(UV_RUN) python $(SCRIPTS_DIR)/transform.py \
		--input $(OUTPUT_OWL) --schema $(SCHEMA) --output $(YAML_OUT)
	$(UV_RUN) python -m linkml.validator.cli \
		--schema $(SCHEMA) --target-class OntologyDocument $(YAML_OUT)
	$(UV_RUN) python $(SCRIPTS_DIR)/verify.py --yaml $(YAML_OUT)
	$(UV_RUN) python -m linkml_owl.dumpers.owl_dumper \
		--schema $(SCHEMA) -o $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	@echo "Build complete: $(YAML_OUT), $(OUTPUT_OWL) (ROBOT), $(OUTPUT_OWL_LINKML) (LinkML)"

verify:
	$(UV_RUN) python $(SCRIPTS_DIR)/verify.py --yaml $(YAML_OUT)

clean:
	rm -f $(OUTPUT_OWL) $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	rm -rf $(TMP_DIR)
