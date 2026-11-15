"""Project wire responses onto the values returned by CoreCommands."""

from copy import deepcopy
from functools import reduce
from operator import or_
from types import UnionType
from typing import Any, Union, get_args, get_origin

from multiconn_archicad.models.tapir import types as tapir_types


COMMAND_ERROR_TYPES = (tapir_types.ErrorItem, tapir_types.FailedExecutionResult)
COMMAND_ERROR_REFS = {f"#/$defs/{model.__name__}" for model in COMMAND_ERROR_TYPES}


def reachable_response_type(annotation: Any, source: str) -> Any:
    """Remove only Tapir's root error variants; nested item errors remain data."""
    if source != "tapir":
        return annotation
    if get_origin(annotation) not in (Union, UnionType):
        return annotation
    branches = get_args(annotation)
    reachable = tuple(branch for branch in branches if branch not in COMMAND_ERROR_TYPES)
    if reachable == branches:
        return annotation
    if not reachable:
        raise ValueError("Tapir response has no returnable branch after command errors are raised")
    return reduce(or_, reachable)


def reachable_response_schema(schema: dict, definitions: dict, source: str) -> dict:
    """Constrain mocked core responses without changing shared wire definitions."""
    if source != "tapir":
        return deepcopy(schema)

    def narrow(node: dict, seen: frozenset[str]) -> dict | None:
        ref = node.get("$ref")
        if ref in COMMAND_ERROR_REFS:
            return None
        if ref and ref.startswith("#/$defs/") and ref not in seen:
            definition = definitions[ref.removeprefix("#/$defs/")]
            narrowed = narrow(definition, seen | {ref})
            if narrowed is None:
                return None
            if narrowed != definition:
                # Keep ref siblings (such as descriptions) on the projected root.
                return {**narrowed, **{key: value for key, value in node.items() if key != "$ref"}}

        result = deepcopy(node)
        for keyword in ("oneOf", "anyOf", "allOf"):
            if keyword not in result:
                continue
            branches = [narrow(branch, seen) for branch in result[keyword]]
            if keyword == "allOf" and any(branch is None for branch in branches):
                return None
            result[keyword] = [branch for branch in branches if branch is not None]
            if not result[keyword]:
                return None

        # Some responses model failure with an optional field instead of a union.
        # A truthy root error never gets past post_tapir_command, including dry runs.
        properties = result.get("properties", {})
        if "error" in properties and "error" not in result.get("required", []):
            properties["error"] = {"type": "null"}
        return result

    reachable = narrow(schema, frozenset())
    if reachable is None:
        raise ValueError("Tapir response schema has no returnable branch after command errors are raised")
    return reachable
