# app/services/validation/__init__.py

from .count_validator import CountValidator
from .aggregate_validator import AggregateValidator

def run_count_and_aggregate(source_connector, target_connector, numeric_fields) -> dict:
    """
    Helper function for the report generator to run post-migration validation checks.
    """
    return {
        "counts": CountValidator.validate(source_connector.estimate_counts(), target_connector.estimate_counts()),
        "aggregates": AggregateValidator.validate(source_connector, target_connector, numeric_fields),
    }
