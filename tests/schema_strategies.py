import json
from functools import cache

from hypothesis import strategies as st
from hypothesis_jsonschema import from_schema


def _limit_test_examples(value: object) -> None:
    if isinstance(value, dict):
        if value.get("type") == "object" and value.get("properties"):
            # Exercise declared fields when the schema leaves extra keys unspecified.
            value.setdefault("additionalProperties", False)
        if value.get("type") == "array" and "maxItems" not in value:
            value["maxItems"] = max(2, value.get("minItems", 0))
        for child in value.values():
            _limit_test_examples(child)
    elif isinstance(value, list):
        for child in value:
            _limit_test_examples(child)


def _build_schema_strategy(schema_json: str) -> st.SearchStrategy:
    schema = json.loads(schema_json)
    # Keep synthetic batches within Hypothesis's entropy budget for every API.
    # Released/runtime schemas are unchanged; explicit size constraints win.
    _limit_test_examples(schema)
    return from_schema(schema)


@cache
def schema_strategy(schema_json: str) -> st.SearchStrategy:
    """Share the strategy for a schema and build it on its first draw."""
    return st.deferred(lambda: _build_schema_strategy(schema_json))
