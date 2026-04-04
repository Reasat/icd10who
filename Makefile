# ICD10WHO preprocessed build
#
# Pipeline:
#   make acquire        — fetch ICD-10 WHO from WHO API → tmp/icd10who_raw.ttl
#   make build          — ROBOT preprocessing → icd10who.owl
#   make build-release  — build + transform → validate → LinkML OWL
#
# Requires: ROBOT (≥ 1.9), obolibrary/odkfull Docker image for CI, uv for Python.
# Auth: set CLIENT_ID and CLIENT_SECRET in env/.env (see env/.env.example).

ROBOT       ?= robot
ROBOT_PLUGINS_DIRECTORY ?= /home/$(USER)/.robot/plugins
PYTHON      ?= python3
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

.PHONY: all build build-release acquire clean

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

# ── Component: add exact synonyms, strip non-allowlisted properties, annotate ─
$(OUTPUT_OWL): $(MIRROR_OWL) \
		$(CONFIG_DIR)/properties.txt \
		$(SPARQL_DIR)/exact_syn_from_label.ru
	$(ROBOT) merge -i $(MIRROR_OWL) \
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

# ── Release: build + LinkML transform + validate + data2owl ──────────────────
build-release: build
	$(UV_RUN) python $(SCRIPTS_DIR)/transform.py \
		--input $(OUTPUT_OWL) --schema $(SCHEMA) --output $(YAML_OUT)
	$(UV_RUN) python -m linkml.validator.cli \
		--schema $(SCHEMA) --target-class OntologyDocument $(YAML_OUT)
	$(UV_RUN) python -m linkml_owl.dumpers.owl_dumper \
		--schema $(SCHEMA) -o $(OUTPUT_OWL_LINKML) $(YAML_OUT) 2>/dev/null
	@echo "Build complete: $(YAML_OUT), $(OUTPUT_OWL) (ROBOT), $(OUTPUT_OWL_LINKML) (LinkML)"

clean:
	rm -f $(OUTPUT_OWL) $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	rm -rf $(TMP_DIR)
