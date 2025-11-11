import re
from code_generation.tapir.paths import tapir_paths


def main():
    print(f"--- Starting the cleaning of {tapir_paths.RAW_PYDANTIC_MODELS} ---")
    try:
        content = tapir_paths.RAW_PYDANTIC_MODELS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {tapir_paths.RAW_PYDANTIC_MODELS} not found. Please generate it first.")
        return

    # Apply the two necessary cleaning steps.
    content = remove_master_model_definition(content)
    content = fix_root_model_unions_to_type_alias(content)
    content = remove_guid_pattern(content)
    content = remove_redundant_model_configs(content)
    content = assemble_final_file(content)

    tapir_paths.CLEANED_PYDANTIC_MODELS.write_text(content, encoding="utf-8")
    print(f"✅ Successfully created final, clean models at: {tapir_paths.CLEANED_PYDANTIC_MODELS}")


def remove_master_model_definition(content: str) -> str:
    """Finds and removes the boilerplate TapirMasterModels RootModel definition."""
    print("    - Step 1: Removing boilerplate `TapirMasterModels` RootModel...")

    pattern = re.compile(
        r"^class TapirMasterModels\(RootModel\[Any\]\):\n(?:    .*\n?)*",
        re.MULTILINE
    )

    cleaned_content, num_replacements = pattern.subn("", content, count=1)

    if num_replacements > 0:
        print("      - Successfully removed the definition.")
    else:
        print("      - Warning: `TapirMasterModels` definition not found.")

    return cleaned_content.strip()


def fix_root_model_unions_to_type_alias(content: str) -> str:
    print("⚙️  Step 2: Converting remaining `RootModel` classes to `TypeAlias`...")
    lookahead = r"(?=\n\n\n(class |[A-Z]\w+\s*:\s*TypeAlias)|\Z)"
    pattern = re.compile(
        r"class (\w+)\(RootModel\[(.+?)]\):.*?" + lookahead,
        flags=re.DOTALL
    )
    replacement = r"\1: TypeAlias = \2"

    num_replacements = 0
    while True:
        content, count = pattern.subn(replacement, content, count=1)
        if count == 0:
            break
        num_replacements += 1

    print(f"    - Converted {num_replacements} models.")
    return content


def remove_guid_pattern(code: str) -> str:
    """
    Surgically removes the 'pattern=...' argument from any field defined as
    'Annotated[UUID, Field(...)]'. This is necessary because Pydantic V2
    cannot apply a string pattern to a UUID object after validation.
    """
    print("⚙️  Step 3: Removing conflicting 'pattern' from all UUID Fields...")

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

    pattern = re.compile(
        r"\s*model_config = ConfigDict\(\s*extra=\"forbid\",?\s*\)\s*",
        re.MULTILINE
    )

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

    header = [
        "from __future__ import annotations",
        "from typing import Any, List, Literal, Annotated, TypeAlias",
        "from uuid import UUID",
        "from enum import Enum",
        "from pydantic import Field, RootModel",
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
