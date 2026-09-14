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
    """
    Surgically removes the 'pattern=...' argument from any field defined as
    'Annotated[UUID, Field(...)]'. This is necessary because Pydantic V2
    cannot apply a string pattern to a UUID object after validation.
    """
    print("Step 3: Removing conflicting 'pattern' from all UUID Fields...")

    pattern = re.compile(
        # --- Group 1: Capture the part BEFORE the pattern argument ---
        r"("
        # Match any field name like 'guid:' or 'stampMainGuid:'
        r"\w+:\s*Annotated\[\s*UUID\s*,\s*Field\("
        # Non-greedily match any characters (including newlines) up to the pattern arg.
        r".*?"
        r")"
        # --- The part to DISCARD ---
        # Match an optional comma, the pattern argument, and its value.
        r'(?:,\s*)?pattern\s*=\s*".*?"'
        # --- Group 2: Capture the part AFTER the pattern argument ---
        r"("
        # Non-greedily match any remaining characters until the end of the annotation.
        r".*?"
        r"\)\s*\]"
        r")",
        flags=re.DOTALL,  # The DOTALL flag makes '.' match newlines, simplifying the regex.
    )

    replacement = r"\1\2"

    num_replacements = 0
    while True:
        code, count = pattern.subn(replacement, code, count=1)
        if count == 0:
            break
        num_replacements += 1

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

    pattern = re.compile(r"\s*model_config = ConfigDict\(\s*extra=\"forbid\",?\s*\)\s*", re.MULTILINE)

    cleaned_content, num_replacements = pattern.subn("\n    ", content)

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
