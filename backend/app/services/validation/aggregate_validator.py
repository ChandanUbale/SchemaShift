"""services/validation/aggregate_validator.py — Aggregate comparison (SUM/AVG) source vs target."""

from typing import Any


class AggregateValidator:

    @staticmethod
    def validate(
        source_connector,
        target_connector,
        numeric_fields: dict[str, list[str]],   # {table: [col1, col2]}
        tolerance: float = 0.001,
    ) -> dict[str, Any]:
        """
        Compare SUM and AVG of selected numeric columns between source and target.

        Args:
            source_connector: connected BaseConnector for the source
            target_connector: connected BaseConnector for the target
            numeric_fields:   which fields to aggregate per entity
            tolerance:        acceptable relative difference (default 0.1%)

        Returns:
            {
                "match": bool,
                "details": {
                    entity_name: {
                        field: {"source_sum": float, "target_sum": float, "match": bool}
                    }
                }
            }

        TODO: execute SUM/AVG queries via each connector, compare within tolerance.
        """
        raise NotImplementedError("TODO: implement AggregateValidator.validate")
