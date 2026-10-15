import ast
import json
import re
from code_generation.tapir.paths import tapir_paths


def main():
    print(f"--- Starting the cleaning of {tapir_paths.RAW_PYDANTIC_MODELS} ---")
    try:
        content = tapir_paths.RAW_PYDANTIC_MODELS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {tapir_paths.RAW_PYDANTIC_MODELS} not found. Please generate it first.")
        return

    # Apply the necessary cleaning steps.
    content = fix_root_model_unions_to_type_alias(content)
    content = restore_collapsed_named_unions(content)
    content = remove_guid_pattern(content)
    content = remove_redundant_model_configs(content)
    content = assemble_final_file(content)

    tapir_paths.CLEANED_PYDANTIC_MODELS.write_text(content, encoding="utf-8")
    print(f"Created final, clean models at: {tapir_paths.CLEANED_PYDANTIC_MODELS}")


def fix_root_model_unions_to_type_alias(content: str) -> str:
    print("Step 2: Converting remaining `RootModel` classes to `TypeAlias`...")

    lookahead = r"(?=\n\n+(class |[A-Z]\w+\s*[:=])|\Z)"

    # 1. We allow whitespace (\s*) inside the class header to handle multiline signatures.
    # 2. We capture the name and the inner type.
    # 3. We consume everything until the lookahead (the entire class body).
    pattern = re.compile(
        r"class\s+(\w+)\s*\(\s*RootModel\s*\[\s*(.+?)\s*\]\s*\)\s*:.*?" + lookahead, flags=re.DOTALL | re.MULTILINE
    )

    def replacer(match):
        name = match.group(1)
        inner_type = re.sub(r"\s+", " ", match.group(2)).strip()
        return f"{name}: TypeAlias = {inner_type}"

    content, num_replacements = pattern.subn(replacer, content)

    print(f"    - Converted {num_replacements} models to TypeAlias.")
    return content


def restore_collapsed_named_unions(content: str) -> str:
    """Restore public aliases that datamodel-codegen collapses into their use sites."""
    schema = json.loads(tapir_paths.MASTER_SCHEMA_OUTPUT.read_text(encoding="utf-8"))
    existing_names = set(re.findall(r"^(?:class\s+)?([A-Z]\w+)\s*(?:\(|:\s*TypeAlias\s*=)", content, re.MULTILINE))
    aliases = []

    for name, definition in schema.get("$defs", {}).items():
        if name in existing_names or not isinstance(definition, dict):
            continue
        union_keys = [key for key in ("oneOf", "anyOf") if key in definition]
        if len(union_keys) != 1 or set(definition) != {union_keys[0]}:
            continue
        variants = definition[union_keys[0]]
        if not isinstance(variants, list) or not variants:
            continue
        refs = [variant.get("$ref") for variant in variants if isinstance(variant, dict) and set(variant) == {"$ref"}]
        if len(refs) != len(variants) or not all(isinstance(ref, str) and ref.startswith("#/$defs/") for ref in refs):
            continue
        aliases.append(f"{name}: TypeAlias = {' | '.join(ref.rsplit('/', 1)[-1] for ref in refs)}")

    if aliases:
        print(f"    - Restored {len(aliases)} collapsed named union aliases.")
        content = content.rstrip() + "\n\n\n" + "\n\n\n".join(aliases) + "\n"
    else:
        print("    - No collapsed named union aliases needed restoring.")
    return content


def remove_guid_pattern(code: str) -> str:
    """Remove string patterns from UUID fields in either supported Field syntax."""
    print("Step 3: Removing conflicting 'pattern' from all UUID Fields...")

    def is_uuid(annotation: ast.expr) -> bool:
        if isinstance(annotation, ast.Name):
            return annotation.id == "UUID"
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            left, right = annotation.left, annotation.right
            return (isinstance(left, ast.Constant) and left.value is None and is_uuid(right)) or (
                isinstance(right, ast.Constant) and right.value is None and is_uuid(left)
            )
        return False

    # AST columns are UTF-8 byte offsets, including when descriptions contain Unicode.
    source = code.encode("utf-8")
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    edits = []
    for field in ast.walk(ast.parse(code)):
        if not isinstance(field, ast.AnnAssign):
            continue
        annotation = field.annotation
        candidates = [field.value]
        if (
            isinstance(annotation, ast.Subscript)
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id == "Annotated"
            and isinstance(annotation.slice, ast.Tuple)
        ):
            annotation, *metadata = annotation.slice.elts
            candidates.extend(metadata)
        if not is_uuid(annotation):
            continue
        for call in candidates:
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "Field":
                continue
            for keyword in call.keywords:
                if keyword.arg != "pattern":
                    continue
                start = offsets[keyword.lineno - 1] + keyword.col_offset
                end = offsets[keyword.end_lineno - 1] + keyword.end_col_offset
                following = end
                while source[following : following + 1].isspace():
                    following += 1
                if source[following : following + 1] == b",":
                    end = following + 1
                else:
                    preceding = start - 1
                    while preceding >= 0 and source[preceding : preceding + 1].isspace():
                        preceding -= 1
                    if preceding >= 0 and source[preceding : preceding + 1] == b",":
                        start = preceding
                edits.append((start, end))

    for start, end in sorted(edits, reverse=True):
        source = source[:start] + source[end:]
    code = re.sub(r"(?m)^[ \t]+(?=\r?$)", "", source.decode("utf-8"))
    num_replacements = len(edits)

    if num_replacements > 0:
        print(f"    - Removed {num_replacements} conflicting 'pattern' arguments from UUID fields.")
    else:
        print("    - No conflicting 'pattern' arguments found in UUID fields.")

    return code


def remove_redundant_model_configs(content: str) -> str:
    """
    Finds and removes the boilerplate `model_config` dicts as it is handled by the APIModel base model
    """
    print("    - Removing redundant `model_config` blocks...")

    config_only_classes = {
        node.body[0].lineno
        for node in ast.walk(ast.parse(content))
        if isinstance(node, ast.ClassDef)
        and len(node.body) == 1
        and isinstance(node.body[0], ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "model_config" for target in node.body[0].targets)
    }
    pattern = re.compile(r'^[ \t]+model_config = ConfigDict\(\s*extra="forbid",?\s*\)[ \t]*(?:\r?\n|$)', re.MULTILINE)

    def replace_config(match):
        line = content.count("\n", 0, match.start()) + 1
        return "    pass\n" if line in config_only_classes else ""

    cleaned_content, num_replacements = pattern.subn(replace_config, content)

    if num_replacements > 0:
        print(f"      - Successfully removed {num_replacements} redundant config blocks.")
    else:
        print("      - Warning: No redundant config blocks were found to remove.")

    return cleaned_content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, removes the old one, and performs final formatting."""
    print("    - Step 3: Assembling final file with standard header...")

    # Remove the original datamodel-codegen header and all import lines
    body = re.sub(r"^#.*?\n\n", "", content, flags=re.DOTALL)
    body = re.sub(r"^(from|import).*\n", "", body, flags=re.MULTILINE)

    pydantic_import = "from pydantic import Field"
    if re.search(r"\bRootModel\b", body):
        pydantic_import += ", RootModel"

    header = [
        "from __future__ import annotations",
        "from typing import Any, Literal, Annotated, TypeAlias",
        "from uuid import UUID",
        "from enum import Enum",
        pydantic_import,
        "",
        "from multiconn_archicad.models.base import APIModel",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]
    final_header = "\n".join(header)

    # Reassemble the file with the new header and standardize spacing
    full_content = final_header + "\n\n\n" + body.strip()
    full_content = re.sub(r"\n+(?=(class |[A-Z]\w+\s*:\s*TypeAlias))", "\n\n\n", full_content)
    full_content = re.sub(r"\n{4,}", "\n\n\n", full_content)

    return full_content.strip() + "\n"


if __name__ == "__main__":
    main()
