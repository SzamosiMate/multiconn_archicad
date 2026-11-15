"""Audit the wire-requiredness assumption behind defaulted Literal restoration."""

import argparse
import importlib
import json
from typing import Literal, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from code_generation.official.paths import official_paths
from code_generation.tapir.paths import tapir_paths


def _object_shape(node, definitions, seen=frozenset()):
    """Return properties and fields required in every applicable object branch."""
    if not isinstance(node, dict):
        return set(), set()
    properties = set(node.get("properties", {}))
    required = set(node.get("required", []))
    ref = node.get("$ref")
    if ref and ref.startswith("#/$defs/"):
        name = ref[8:].replace("~1", "/").replace("~0", "~")
        if name not in seen:
            p, r = _object_shape(definitions[name], definitions, seen | {name})
            properties |= p
            required |= r
    for branch in node.get("allOf", []):
        p, r = _object_shape(branch, definitions, seen)
        properties |= p
        required |= r
    for keyword in ("oneOf", "anyOf"):
        branches = node.get(keyword, [])
        if branches:
            shapes = [_object_shape(branch, definitions, seen) for branch in branches]
            properties |= set().union(*(p for p, _ in shapes))
            required |= set.intersection(*(r for _, r in shapes))
    # Conditional branches require a field only if both alternatives do.
    if "then" in node or "else" in node:
        a = _object_shape(node.get("then", {}), definitions, seen)
        b = _object_shape(node.get("else", {}), definitions, seen)
        properties |= a[0] | b[0]
        required |= a[1] & b[1]
    return properties, required


def audit_models(provider, definitions, models):
    findings = []
    for model in models:
        relevant = {
            name: field
            for name, field in model.model_fields.items()
            if field.default is not PydanticUndefined or field.default_factory is not None
        }
        if not relevant:
            continue
        schema = definitions.get(model.__name__)
        if schema is None:
            if any(get_origin(f.annotation) is Literal for f in relevant.values()):
                findings.append(
                    f"{provider}: {model.__name__}: no schema mapping for defaulted Literal; review mapping"
                )
            continue
        properties, required = _object_shape(schema, definitions)
        for name, field in relevant.items():
            keys = {name, field.alias, field.serialization_alias} - {None}
            matches = keys & properties
            protected = (
                get_origin(field.annotation) is Literal
                and field.default is not PydanticUndefined
                and field.default_factory is None
            )
            if len(matches) != 1:
                findings.append(
                    f"{provider}: {model.__name__}.{name}: missing or ambiguous wire mapping; review requiredness"
                )
                continue
            key = next(iter(matches))
            is_required = key in required
            if is_required and not protected:
                findings.append(
                    f"{provider}: {model.__name__}.{name}: wire-required field has a Python default but is not a protected Literal"
                )
            if protected and not is_required:
                findings.append(
                    f"{provider}: {model.__name__}.{name}: defaulted Literal is optional in the wire schema"
                )
            if protected and (
                type(field.default) not in (str, int, float, bool)
                or any(type(v) not in (str, int, float, bool) for v in get_args(field.annotation))
                or not any(type(field.default) is type(v) and field.default == v for v in get_args(field.annotation))
            ):
                findings.append(f"{provider}: {model.__name__}.{name}: unsupported Literal value representation")
    return findings


def audit_provider(provider):
    path = (tapir_paths if provider == "tapir" else official_paths).MASTER_SCHEMA_OUTPUT
    definitions = json.loads(path.read_text(encoding="utf-8-sig"))["$defs"]
    models = []
    for part in ("types", "commands"):
        module = importlib.import_module(f"multiconn_archicad.models.{provider}.{part}")
        models.extend(
            value
            for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, BaseModel) and value.__module__ == module.__name__
        )
    return audit_models(provider, definitions, models)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("tapir", "official", "both"), required=True)
    args = parser.parse_args()
    providers = ("tapir", "official") if args.provider == "both" else (args.provider,)
    findings = [finding for provider in providers for finding in audit_provider(provider)]
    if findings:
        print("\n".join(findings))
        raise SystemExit(1)
    print("Default policy audit passed: " + ", ".join(providers))


if __name__ == "__main__":
    main()
