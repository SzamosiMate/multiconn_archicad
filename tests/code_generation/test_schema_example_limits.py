import json

import pytest

from tests import schema_strategies

pytestmark = pytest.mark.unit


def test_fixture_batches_are_bounded_without_mutating_input(monkeypatch):
    root = "OrdinaryResult"
    schema = {"$ref": f"#/$defs/{root}", "$defs": {root: {"type": "array", "items": {"type": "integer"}}}}
    monkeypatch.setattr(schema_strategies, "from_schema", lambda value: value)
    prepared = schema_strategies._build_schema_strategy(json.dumps(schema))
    assert prepared["$defs"][root]["maxItems"] == 2
    assert "maxItems" not in schema["$defs"][root]


def test_fixture_limits_preserve_explicit_bounds_and_minimum_sizes(monkeypatch):
    schema = {
        "$ref": "#/$defs/ResolveNamesResult",
        "$defs": {
            "ResolveNamesResult": {
                "type": "object",
                "properties": {
                    "explicit": {"type": "array", "minItems": 1, "maxItems": 8, "items": {"type": "integer"}},
                    "minimum": {"type": "array", "minItems": 5, "items": {"type": "integer"}},
                },
                "additionalProperties": True,
            }
        },
    }
    monkeypatch.setattr(schema_strategies, "from_schema", lambda value: value)
    prepared = schema_strategies._build_schema_strategy(json.dumps(schema))
    properties = prepared["$defs"]["ResolveNamesResult"]["properties"]
    assert properties["explicit"]["maxItems"] == 8
    assert properties["minimum"]["minItems"] == properties["minimum"]["maxItems"] == 5
    assert prepared["$defs"]["ResolveNamesResult"]["additionalProperties"] is True
