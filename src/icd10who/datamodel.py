from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.7.0"
version = "0.1.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'mondo_src',
     'default_range': 'string',
     'description': 'LinkML schema for ICD-10 WHO source for Mondo ingest.',
     'id': 'https://w3id.org/monarch-initiative/mondo-source-schema',
     'imports': ['linkml:types'],
     'name': 'mondo_source_schema',
     'prefixes': {'ICD10WHO': {'prefix_prefix': 'ICD10WHO',
                               'prefix_reference': 'https://icd.who.int/browse10/2019/en#/'},
                  'dcterms': {'prefix_prefix': 'dcterms',
                              'prefix_reference': 'http://purl.org/dc/terms/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'mondo_src': {'prefix_prefix': 'mondo_src',
                                'prefix_reference': 'https://w3id.org/monarch-initiative/mondo-source-schema/'},
                  'obo': {'prefix_prefix': 'obo',
                          'prefix_reference': 'http://purl.obolibrary.org/obo/'},
                  'oboInOwl': {'prefix_prefix': 'oboInOwl',
                               'prefix_reference': 'http://www.geneontology.org/formats/oboInOwl#'},
                  'owl': {'prefix_prefix': 'owl',
                          'prefix_reference': 'http://www.w3.org/2002/07/owl#'},
                  'rdfs': {'prefix_prefix': 'rdfs',
                           'prefix_reference': 'http://www.w3.org/2000/01/rdf-schema#'},
                  'skos': {'prefix_prefix': 'skos',
                           'prefix_reference': 'http://www.w3.org/2004/02/skos/core#'}},
     'source_file': 'linkml/mondo_source_schema.yaml'} )


class OntologyDocument(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'owl:Ontology',
         'from_schema': 'https://w3id.org/monarch-initiative/mondo-source-schema',
         'tree_root': True})

    title: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'rdfs:label'} })
    version: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument'], 'slot_uri': 'owl:versionInfo'} })
    terms: list[OntologyTerm] = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyDocument']} })


class OntologyTerm(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'owl:Class',
         'from_schema': 'https://w3id.org/monarch-initiative/mondo-source-schema'})

    id: str = Field(default=..., json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyTerm'], 'slot_uri': 'dcterms:identifier'} })
    label: str = Field(default=..., json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'rdfs:label'} })
    definition: Optional[str] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'obo:IAO_0000115'} })
    exact_synonyms: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasExactSynonym'} })
    related_synonyms: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasRelatedSynonym'} })
    narrow_synonyms: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasNarrowSynonym'} })
    broad_synonyms: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'oboInOwl:hasBroadSynonym'} })
    parents: Optional[list[str]] = Field(default=None, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'SubClassOf'}},
         'domain_of': ['OntologyTerm'],
         'slot_uri': 'rdfs:subClassOf'} })
    is_root: Optional[bool] = Field(default=False, json_schema_extra = { "linkml_meta": {'domain_of': ['OntologyTerm'], 'ifabsent': 'false'} })
    deprecated: Optional[bool] = Field(default=False, json_schema_extra = { "linkml_meta": {'annotations': {'owl': {'tag': 'owl', 'value': 'AnnotationAssertion'}},
         'domain_of': ['OntologyTerm'],
         'ifabsent': 'false',
         'slot_uri': 'owl:deprecated'} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
OntologyDocument.model_rebuild()
OntologyTerm.model_rebuild()
