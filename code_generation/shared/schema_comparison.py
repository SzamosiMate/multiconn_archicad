"""Structural comparison for Tapir schema snapshots."""

import json


ANNOTATIONS = {"title", "description", "$comment", "examples"}
SCHEMA_MAPS = {"properties", "patternProperties", "definitions", "$defs", "dependentSchemas"}
SCHEMA_CHILDREN = {
    "items",
    "additionalItems",
    "additionalProperties",
    "propertyNames",
    "contains",
    "not",
    "if",
    "then",
    "else",
    "unevaluatedItems",
    "unevaluatedProperties",
    "allOf",
    "anyOf",
    "oneOf",
    "prefixItems",
}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def child_path(path, key):
    return f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}"


def schema_role(key):
    if key in SCHEMA_MAPS:
        return "map"
    return "schema" if key in SCHEMA_CHILDREN else "data"


def target_name(ref, common, path):
    if isinstance(ref, str) and ref.startswith("#/"):
        name = ref.removeprefix("#/$defs/") if ref.startswith("#/$defs/") else ref[2:]
        name = name.replace("~1", "/").replace("~0", "~")
        if name in common:
            return name
    raise ValueError(f"{path}: unresolved or unsupported Tapir reference {ref!r}")


def reference_sites(node, common, path, role="schema"):
    """Yield direct reference targets and their schema paths."""
    if isinstance(node, dict) and role != "data":
        for key, value in sorted(node.items()):
            subpath = child_path(path, key)
            if key == "$ref" and role == "schema":
                yield target_name(value, common, subpath), subpath
            else:
                yield from reference_sites(value, common, subpath, "schema" if role == "map" else schema_role(key))
    elif isinstance(node, list) and role == "schema":
        for index, value in enumerate(node):
            yield from reference_sites(value, common, child_path(path, index))


def check_references(node, common, path):
    for _ in reference_sites(node, common, path):
        pass


def normalized(schema):
    result = {key: value for key, value in schema.items() if key not in ANNOTATIONS}
    if result.get("required") == []:
        del result["required"]
    for keyword in ("oneOf", "anyOf"):
        branches = result.get(keyword)
        # Distribute Tapir's required-only selectors over their shared object fields.
        if (
            branches
            and result.get("type") == "object"
            and result.keys() <= {keyword, "type", "properties", "required", "additionalProperties"}
            and all(isinstance(branch, dict) and branch.keys() == {"required"} for branch in branches)
        ):
            shared = {key: value for key, value in result.items() if key not in {keyword, "required"}}
            required = result.get("required", [])
            return {
                keyword: [
                    {**shared, "required": list(dict.fromkeys(required + branch["required"]))} for branch in branches
                ]
            }
    return result


def schema_annotations(schema):
    return {key: schema[key] for key in sorted(schema.keys() & ANNOTATIONS)} if isinstance(schema, dict) else {}


def split_reference(schema, common, path, annotations=None):
    """Follow a reference chain and collect its constraint siblings."""
    visited = set()
    siblings = []
    while isinstance(schema, dict) and "$ref" in schema:
        if annotations is not None:
            notes = schema_annotations(schema)
            if notes:
                annotations.append(notes)
        keywords = normalized(schema)
        name = target_name(keywords.pop("$ref"), common, path)
        if name in visited:
            raise ValueError(f"{path}: reference cycle without a schema body at {name!r}")
        if keywords:
            siblings.append(keywords)
        visited.add(name)
        schema = common[name]
    return schema, siblings


def differences(before, after, base_defs, merge_defs, path, seen, role="schema", *, annotation_changes=None):
    # Keep the original objects alive because normalization can create temporary branches.
    key = id(before), id(after), role
    if key in seen:
        return
    seen[key] = before, after
    if role == "schema":
        a_notes = [] if annotation_changes is not None else None
        b_notes = [] if annotation_changes is not None else None
        a, a_siblings = split_reference(before, base_defs, path, a_notes)
        b, b_siblings = split_reference(after, merge_defs, path, b_notes)
        if a_notes != b_notes:
            annotation_changes.append(
                {"path": child_path(path, "$ref annotations"), "before": a_notes, "after": b_notes}
            )
        if a_siblings or b_siblings:
            yield from differences(
                a_siblings,
                b_siblings,
                base_defs,
                merge_defs,
                child_path(path, "$ref siblings"),
                seen,
                annotation_changes=annotation_changes,
            )
        if a is not before or b is not after:
            yield from differences(a, b, base_defs, merge_defs, path, seen, annotation_changes=annotation_changes)
            return
        if annotation_changes is not None:
            a_notes, b_notes = schema_annotations(a), schema_annotations(b)
            if a_notes != b_notes:
                annotation_changes.append({"path": path, "before": a_notes, "after": b_notes})
        before = normalized(before) if isinstance(before, dict) else before
        after = normalized(after) if isinstance(after, dict) else after
    if isinstance(before, dict) and isinstance(after, dict):
        for name in sorted(before.keys() - after.keys()):
            yield f"{child_path(path, name)}: missing from target"
        for name in sorted(after.keys() - before.keys()):
            yield f"{child_path(path, name)}: only in target"
        for name in sorted(before.keys() & after.keys()):
            child_role = "schema" if role == "map" else schema_role(name) if role == "schema" else "data"
            yield from differences(
                before[name],
                after[name],
                base_defs,
                merge_defs,
                child_path(path, name),
                seen,
                child_role,
                annotation_changes=annotation_changes,
            )
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            yield f"{path}: list length changed from {len(before)} to {len(after)}"
        for index, (a, b) in enumerate(zip(before, after)):
            yield from differences(
                a, b, base_defs, merge_defs, child_path(path, index), seen, role, annotation_changes=annotation_changes
            )
    elif type(before) is not type(after) or before != after:
        yield f"{path}: {json.dumps(before)} -> {json.dumps(after)}"
