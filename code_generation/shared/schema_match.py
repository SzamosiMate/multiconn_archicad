"""Find structurally matching definitions in MultiConn Tapir schema snapshots."""

import argparse
from collections import defaultdict
import json
from pathlib import Path

from code_generation.shared.schema_comparison import child_path, differences, reference_sites, unique_object


def load_definitions(path):
    definitions = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)["$defs"]
    if not isinstance(definitions, dict):
        raise ValueError(f"{path}: expected a $defs object")
    return definitions


def select_schema(definition, pointer):
    if pointer and not pointer.startswith("/"):
        raise ValueError("--path must be a JSON pointer relative to the definition")
    node = definition
    for segment in pointer.split("/")[1:]:
        key = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            node = node[key]
        elif isinstance(node, list) and key.isascii() and key.isdecimal():
            node = node[int(key)]
        else:
            raise ValueError(f"Invalid schema path {pointer!r}")
    if not isinstance(node, (dict, bool)):
        raise ValueError(f"Path {pointer!r} does not select a schema")
    return node


def match_definitions(source, target, name, pointer="", candidate=None):
    path = child_path("/$defs", name) + pointer
    query = select_schema(source[name], pointer)
    sites = defaultdict(list)
    for owner, schema in sorted(target.items()):
        for reference, site in reference_sites(schema, target, child_path("/$defs", owner)):
            sites[reference].append(site)

    matches = []
    candidates = [candidate] if candidate is not None else sorted(target)
    for other in candidates:
        if candidate is None and source is target and other == name and not pointer:
            continue
        annotations = []
        changes = list(differences(query, target[other], source, target, path, {}, annotation_changes=annotations))
        if not changes or candidate is not None:
            matches.append(
                {
                    "definition": other,
                    "structural_differences": changes,
                    "annotation_differences": annotations,
                    "reference_sites": sites[other],
                }
            )
    return {"query": path, "matches": matches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path, help="source JSON schema with $defs")
    parser.add_argument("definition", help="source definition name")
    parser.add_argument("--path", default="", help="JSON pointer relative to the source definition")
    parser.add_argument("--against", type=Path, help="candidate schema file (defaults to the source file)")
    parser.add_argument("--candidate", help="compare one definition even if its structure differs")
    args = parser.parse_args()
    try:
        source = load_definitions(args.schema)
        target = source
        if args.against is not None and args.against.resolve() != args.schema.resolve():
            target = load_definitions(args.against)
        report = match_definitions(source, target, args.definition, args.path, args.candidate)
    except (KeyError, IndexError, OSError, RecursionError, ValueError) as error:
        parser.exit(2, f"Schema match could not complete: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
