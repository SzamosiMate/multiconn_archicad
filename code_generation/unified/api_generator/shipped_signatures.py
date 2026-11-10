"""Extract the positional and keyword-only parameters from a shipped Unified API."""

import argparse
import ast
import json
from pathlib import Path
import subprocess


BASELINE_PATH = Path(__file__).with_name("shipped_signatures.json")
API_PATH = "src/multiconn_archicad/clients/unified_api"
CORE_METHODS = {"tapir": "post_tapir_command", "official": "post_command"}


def extract_signatures(source_text: str, core_method: str) -> dict[str, list[str]]:
    signatures = {}
    for node in ast.parse(source_text).body:
        if not isinstance(node, ast.ClassDef):
            continue
        for method in node.body:
            if not isinstance(method, ast.FunctionDef) or method.name.startswith("_"):
                continue
            calls = [
                call.args[0].value
                for call in ast.walk(method)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == core_method
                and call.args
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            ]
            args = method.args
            if len(calls) != 1 or args.posonlyargs or args.vararg or args.kwarg:
                raise ValueError(f"Unsupported shipped method signature or command call: {method.name}")
            command = calls[0]
            if command in signatures:
                raise ValueError(f"Duplicate shipped command: {command}")
            params = [arg.arg for arg in args.args[1:]]
            if args.kwonlyargs:
                params.extend(["*", *(arg.arg for arg in args.kwonlyargs)])
            signatures[command] = params
    return signatures


def load_shipped_signatures() -> dict[str, dict[str, list[str]]]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["commands"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", help="Git tag of the shipped MultiConn release")
    release = parser.parse_args().release
    root = Path(__file__).resolve().parents[3]

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, encoding="utf-8")

    revision = git("rev-parse", "--verify", f"refs/tags/{release}^{{commit}}").strip()
    sources = {}
    for source, core_method in CORE_METHODS.items():
        signatures: dict[str, list[str]] = {}
        for path in git("ls-tree", "-r", "--name-only", revision, f"{API_PATH}/{source}").splitlines():
            if not path.endswith(".py"):
                continue
            extracted = extract_signatures(git("show", f"{revision}:{path}"), core_method)
            if signatures.keys() & extracted.keys():
                raise ValueError(f"Duplicate shipped commands in {path}")
            signatures.update(extracted)
        if not signatures:
            raise ValueError(f"No shipped {source} signatures found in {release}")
        sources[source] = dict(sorted(signatures.items()))

    # Keep one line per command so updates to the baseline are easy to review.
    lines = ["{", f'  "release": {json.dumps(release)},', f'  "revision": "{revision}",', '  "commands": {']
    blocks = []
    for source, signatures in sources.items():
        entries = ",\n".join(f"      {json.dumps(name)}: {json.dumps(args)}" for name, args in signatures.items())
        blocks.append(f'    "{source}": {{\n{entries}\n    }}')
    lines.extend([",\n".join(blocks), "  }", "}"])
    BASELINE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
