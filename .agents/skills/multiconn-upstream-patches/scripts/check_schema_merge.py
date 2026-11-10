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


sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from code_generation.shared.schema_comparison import (  # noqa: E402
    check_references,
    child_path,
    differences,
    split_reference,
    unique_object,
)


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
