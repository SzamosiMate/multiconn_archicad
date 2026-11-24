"""Python compatibility policies for conditional records, independent of schema patches."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


# The field groups below identify previously published helper constructors.
# Current validation rules always come from the current schema, not this table.
CONDITIONAL_OBJECT_MODELS = {
    "RoofLevel": {
        "RoofLevelWithLevelHeight": ("levelHeight", "levelAngle"),
        "RoofLevelWithHeight": ("height", "angle"),
    },
    "ElementPropertyValue": {
        "ElementPropertyValueWithValue": ("propertyValue",),
        "ElementPropertyValueWithStatus": ("valueStatus",),
    },
}

_ANNOTATIONS = {"title", "description", "$comment", "examples"}


def _without_annotations(value):
    if isinstance(value, dict):
        return {key: _without_annotations(child) for key, child in value.items() if key not in _ANNOTATIONS}
    if isinstance(value, list):
        return [_without_annotations(child) for child in value]
    return value


def _resolve(node, definitions, seen=frozenset()):
    if not isinstance(node, dict):
        raise ValueError("Expected an object schema")
    if "$ref" not in node:
        return deepcopy(node)
    if set(node) - {"$ref", *_ANNOTATIONS}:
        raise ValueError("Conditional model references with constraint siblings need review")
    ref = node["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        raise ValueError(f"Unsupported conditional model reference: {ref!r}")
    name = ref[8:].replace("~1", "/").replace("~0", "~")
    if name in seen:
        raise ValueError(f"Recursive conditional model reference: {name}")
    result = _resolve(definitions[name], definitions, seen | {name})
    result.update({key: value for key, value in node.items() if key in _ANNOTATIONS})
    return result


@dataclass
class ConditionalObjectContract:
    schema: dict[str, Any]
    groups: tuple[tuple[str, ...], ...]


def conditional_object_contract(definitions, name):
    """Accept equivalent inline and referenced required-only anyOf records."""
    root = _resolve(definitions[name], definitions)
    variants = root.get("anyOf")
    if not isinstance(variants, list) or not variants or "oneOf" in root or "allOf" in root:
        raise ValueError(f"{name}: expected required-field alternatives in anyOf; review compatibility policy")
    shared = {key: value for key, value in root.items() if key != "anyOf"}
    if all(isinstance(branch, dict) and set(branch) == {"required"} for branch in variants):
        branches = [
            {**deepcopy(shared), "required": [*shared.get("required", []), *branch["required"]]} for branch in variants
        ]
    elif set(shared) <= _ANNOTATIONS | {"type"}:
        if "type" in shared and shared["type"] != "object":
            raise ValueError(f"{name}: conditional record must be an object")
        branches = [_resolve(branch, definitions) for branch in variants]
    else:
        raise ValueError(f"{name}: unsupported anyOf siblings; review compatibility policy")
    common = {key: value for key, value in branches[0].items() if key != "required"}
    if common.get("type") != "object" or not isinstance(common.get("properties"), dict):
        raise ValueError(f"{name}: expected an object with declared properties")
    if any(key in common for key in ("anyOf", "oneOf", "allOf", "if", "then", "else")):
        raise ValueError(f"{name}: nested object conditions need review")
    for branch in branches:
        other = {key: value for key, value in branch.items() if key != "required"}
        if _without_annotations(other) != _without_annotations(common):
            raise ValueError(f"{name}: alternatives differ beyond required fields; cannot merge safely")
        required = branch.get("required", [])
        if (
            not isinstance(required, list)
            or any(not isinstance(key, str) for key in required)
            or not set(required) <= common["properties"].keys()
        ):
            raise ValueError(f"{name}: invalid required-field alternative")
    required = set.intersection(*(set(branch.get("required", [])) for branch in branches))
    common["required"] = [key for key in common["properties"] if key in required]
    common.update({key: value for key, value in shared.items() if key in _ANNOTATIONS})
    groups = tuple(tuple(key for key in branch.get("required", []) if key not in required) for branch in branches)
    return ConditionalObjectContract(common, groups)


def conditional_object_variants(definitions, name, helpers):
    """Name every current branch, retaining the published constructor names."""
    contract = conditional_object_contract(definitions, name)
    for helper, fields in helpers.items():
        if not any(set(fields) == set(group) for group in contract.groups):
            raise ValueError(f"{name}: published helper {helper} no longer matches a current alternative")
    variants = {}
    for group in contract.groups:
        matches = [helper for helper, fields in helpers.items() if set(fields) == set(group)]
        helper = matches[0] if matches else name + "With" + "And".join(field[0].upper() + field[1:] for field in group)
        if helper in variants:
            raise ValueError(f"{name}: duplicate required-field alternative")
        variants[helper] = group
    if len(variants) < 2:
        raise ValueError(f"{name}: expected at least two distinct alternatives")
    return variants


def prepare_model_schema(schema, *, pydantic, policies=None):
    """Project Python representation without changing the released/patched wire schema."""
    result = deepcopy(schema)
    definitions = result["$defs"]
    for name, helpers in (CONDITIONAL_OBJECT_MODELS if policies is None else policies).items():
        contract = conditional_object_contract(definitions, name)
        for helper, fields in conditional_object_variants(definitions, name, helpers).items():
            expected = deepcopy(contract.schema)
            expected["required"] = [*expected["required"], *fields]
            if helper in definitions:
                actual = _resolve(definitions[helper], definitions)
                if set(actual.get("required", [])) != set(expected["required"]) or _without_annotations(
                    {k: v for k, v in actual.items() if k != "required"}
                ) != _without_annotations({k: v for k, v in expected.items() if k != "required"}):
                    raise ValueError(f"{name}: published helper {helper} conflicts with current schema")
            else:
                definitions[helper] = expected
        if pydantic:
            definitions[name] = contract.schema
    return result
