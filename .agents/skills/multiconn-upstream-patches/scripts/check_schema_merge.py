#!/usr/bin/env python3
"""Compare Tapir schemas generated from a base commit and a proposed merge."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory


ANNOTATIONS = {"title", "description", "$comment", "examples"}
SCHEMA_MAPS = {"properties", "patternProperties", "definitions", "$defs", "dependentSchemas"}
SCHEMA_CHILDREN = {
    "items", "additionalItems", "additionalProperties", "propertyNames", "contains",
    "not", "if", "then", "else", "unevaluatedItems", "unevaluatedProperties",
    "allOf", "anyOf", "oneOf", "prefixItems",
}


def run(command, repo, env=None):
    result = subprocess.run(command, cwd=repo, env=env, capture_output=True)
    if result.returncode:
        output = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
        raise ValueError(f"{' '.join(command)} failed ({result.returncode})\n{output}")
    return result.stdout


def git(repo, *args, env=None):
    return run(["git", *args], repo, env)


def merge_tree(repo, base, head, temporary):
    # Keep the synthetic merge objects in temporary storage as well as the snapshots.
    original = git(repo, "rev-parse", "--path-format=absolute", "--git-path", "objects")
    objects = temporary / "objects"
    objects.mkdir()
    env = os.environ.copy()
    env["GIT_OBJECT_DIRECTORY"] = str(objects)
    alternates = [original.decode("utf-8").strip(), env.get("GIT_ALTERNATE_OBJECT_DIRECTORIES", "")]
    env["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = os.pathsep.join(filter(None, alternates))
    tree = git(repo, "merge-tree", "--write-tree", base, head, env=env).decode().splitlines()[0]
    return tree, env


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def read_generated(path, variable):
    prefix = f"var {variable} = "
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith(prefix) or not text.endswith(";"):
        raise ValueError(f"Unexpected generated file format in {path}")
    return json.loads(text[len(prefix):-1], object_pairs_hook=unique_object)


def snapshot(repo, ref, directory, env):
    archive = git(repo, "archive", ref, "archicad-addon/Sources", "archicad-addon/devkits.json",
                  "tools/generate_addon_docs.py", env=env)
    with tarfile.open(fileobj=BytesIO(archive)) as tar:
        tar.extractall(directory, filter="data")
    docs = directory / "docs/archicad-addon"
    docs.mkdir(parents=True)
    run([sys.executable, "tools/generate_addon_docs.py"], directory)
    common = read_generated(docs / "common_schema_definitions.js", "gSchemaDefinitions")
    groups = read_generated(docs / "command_definitions.js", "gCommands")
    commands = {}
    for group in groups:
        for command in group["commands"]:
            name = command["name"]
            if name in commands:
                raise ValueError(f"Duplicate command {name!r} in {ref}")
            commands[name] = {"input": command["inputScheme"], "response": command["outputScheme"]}
    return common, commands


def child_path(path, key):
    return f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}"


def schema_role(key):
    if key in SCHEMA_MAPS:
        return "map"
    return "schema" if key in SCHEMA_CHILDREN else "data"


def target_name(ref, common, path):
    if not isinstance(ref, str) or not ref.startswith("#/") or ref[2:] not in common:
        raise ValueError(f"{path}: unresolved or unsupported Tapir reference {ref!r}")
    return ref[2:]


def check_references(node, common, path, role="schema"):
    if isinstance(node, dict) and role != "data":
        for key, value in node.items():
            subpath = child_path(path, key)
            if key == "$ref" and role == "schema":
                target_name(value, common, subpath)
            else:
                check_references(value, common, subpath, "schema" if role == "map" else schema_role(key))
    elif isinstance(node, list) and role == "schema":
        for index, value in enumerate(node):
            check_references(value, common, child_path(path, index))


def normalized(schema):
    result = {key: value for key, value in schema.items() if key not in ANNOTATIONS}
    if result.get("required") == []:
        del result["required"]
    for keyword in ("oneOf", "anyOf"):
        branches = result.get(keyword)
        # Distribute Tapir's required-only selectors over their shared object fields.
        if (branches and result.get("type") == "object"
                and result.keys() <= {keyword, "type", "properties", "required", "additionalProperties"}
                and all(isinstance(branch, dict) and branch.keys() == {"required"} for branch in branches)):
            shared = {key: value for key, value in result.items() if key not in {keyword, "required"}}
            required = result.get("required", [])
            return {keyword: [{**shared, "required": list(dict.fromkeys(required + branch["required"]))}
                              for branch in branches]}
    return result


def split_reference(schema, common, path):
    """Follow a reference chain and collect its constraint siblings."""
    visited = set()
    siblings = []
    while isinstance(schema, dict) and "$ref" in schema:
        keywords = normalized(schema)
        name = target_name(keywords.pop("$ref"), common, path)
        if name in visited:
            raise ValueError(f"{path}: reference cycle without a schema body at {name!r}")
        if keywords:
            siblings.append(keywords)
        visited.add(name)
        schema = common[name]
    return schema, siblings


def differences(before, after, base_defs, merge_defs, path, seen, role="schema"):
    # Keep the original objects alive because normalization can create temporary branches.
    key = id(before), id(after), role
    if key in seen:
        return
    seen[key] = before, after
    if role == "schema":
        a, a_siblings = split_reference(before, base_defs, path)
        b, b_siblings = split_reference(after, merge_defs, path)
        if a_siblings or b_siblings:
            yield from differences(a_siblings, b_siblings, base_defs, merge_defs,
                                   child_path(path, "$ref siblings"), seen)
        if a is not before or b is not after:
            yield from differences(a, b, base_defs, merge_defs, path, seen)
            return
        before = normalized(before) if isinstance(before, dict) else before
        after = normalized(after) if isinstance(after, dict) else after
    if isinstance(before, dict) and isinstance(after, dict):
        for name in sorted(before.keys() - after.keys()):
            yield f"{child_path(path, name)}: missing from merge"
        for name in sorted(after.keys() - before.keys()):
            yield f"{child_path(path, name)}: added in merge"
        for name in sorted(before.keys() & after.keys()):
            child_role = "schema" if role == "map" else schema_role(name) if role == "schema" else "data"
            yield from differences(before[name], after[name], base_defs, merge_defs,
                                   child_path(path, name), seen, child_role)
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            yield f"{path}: list length changed from {len(before)} to {len(after)}"
        for index, (a, b) in enumerate(zip(before, after)):
            yield from differences(a, b, base_defs, merge_defs, child_path(path, index), seen, role)
    elif type(before) is not type(after) or before != after:
        yield f"{path}: {json.dumps(before)} -> {json.dumps(after)}"


def check_snapshot(common, commands):
    for name, schema in common.items():
        path = child_path("/definitions", name)
        check_references(schema, common, path)
        split_reference(schema, common, path)
    for name, sides in commands.items():
        for side, schema in sides.items():
            check_references(schema, common, child_path(child_path("/commands", name), side))


def compare(base_snapshot, merge_snapshot):
    base_defs, base_commands = base_snapshot
    merge_defs, merge_commands = merge_snapshot
    check_snapshot(base_defs, base_commands)
    check_snapshot(merge_defs, merge_commands)
    for name in sorted(base_defs):
        path = child_path("/definitions", name)
        if name not in merge_defs:
            yield f"{path}: missing from merge"
        else:
            yield from differences(base_defs[name], merge_defs[name], base_defs, merge_defs, path, {})
    for name in sorted(base_commands.keys() | merge_commands.keys()):
        path = child_path("/commands", name)
        if name not in base_commands:
            yield f"{path}: added in merge"
        elif name not in merge_commands:
            yield f"{path}: missing from merge"
        else:
            for side in ("input", "response"):
                yield from differences(base_commands[name][side], merge_commands[name][side],
                                       base_defs, merge_defs, child_path(path, side), {})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="Tapir checkout")
    parser.add_argument("--base", required=True, help="fetched upstream base ref or commit")
    parser.add_argument("--head", default="HEAD", help="proposal ref or commit (default: HEAD)")
    parser.add_argument("--scratch", type=Path, help="existing writable directory for temporary files")
    args = parser.parse_args()
    try:
        base, head = [git(args.repo, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
                      .decode().strip() for ref in (args.base, args.head)]
        print(f"Base {base}\nHead {head}", flush=True)
        with TemporaryDirectory(prefix="tapir-schema-check-", dir=args.scratch) as directory:
            temporary = Path(directory)
            tree, env = merge_tree(args.repo, base, head, temporary)
            print(f"Merge tree {tree}\nGenerating both schema snapshots from source...", flush=True)
            with ThreadPoolExecutor(max_workers=2) as pool:
                before = pool.submit(snapshot, args.repo, base, temporary / "base", env)
                after = pool.submit(snapshot, args.repo, tree, temporary / "merge", env)
                baseline, merged = before.result(), after.result()
            changes = list(compare(baseline, merged))
        for change in changes:
            print(change)
        print(f"Compared {len(baseline[1])} base commands and {len(baseline[0])} base definitions. "
              f"Found {len(changes)} structural differences.")
        return 1 if changes else 0
    except (KeyError, OSError, RecursionError, ValueError, tarfile.TarError) as error:
        print(f"Schema check could not complete: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
