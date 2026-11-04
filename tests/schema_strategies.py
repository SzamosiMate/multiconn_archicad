import json
from functools import cache

from hypothesis import strategies as st
from hypothesis_jsonschema import from_schema


@cache
def schema_strategy(schema_json: str) -> st.SearchStrategy:
    """Share the strategy for a schema and build it on its first draw."""
    return st.deferred(lambda: from_schema(json.loads(schema_json)))
