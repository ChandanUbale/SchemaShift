# app/services/validation/__init__.py

from .count_validator import CountValidator
from .aggregate_validator import AggregateValidator


def _counts(connector):
    exact_counter = getattr(connector, "count_entities", None)
    if callable(exact_counter):
        return exact_counter()
    return connector.estimate_counts()


def run_count_and_aggregate(
    source_connector,
    target_connector,
    numeric_fields,
    source_counts=None,
    target_counts=None,
    entity_mapping=None,
    source_primary_keys=None,
    target_primary_keys=None,
    field_mappings=None,
) -> dict:
    """
    Helper function for the report generator to run post-migration validation checks.
    """
    return {
        "counts": CountValidator.validate(
            source_counts if source_counts is not None else _counts(source_connector),
            target_counts if target_counts is not None else _counts(target_connector),
        ),
        "aggregates": AggregateValidator.validate(
            source_connector,
            target_connector,
            numeric_fields,
            entity_mapping=entity_mapping,
            source_primary_keys=source_primary_keys,
            target_primary_keys=target_primary_keys,
            field_mappings=field_mappings,
        ),
    }
