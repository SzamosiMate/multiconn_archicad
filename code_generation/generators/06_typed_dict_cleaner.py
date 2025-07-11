import re
from pathlib import Path

# --- Configuration ---
INPUT_TYPED_DICTS_PATH = Path("../temp_models/input_typed_dicts.py")
FINAL_TYPED_DICTS_PATH = Path("../temp_models/typed_dicts.py")

### Main Cleaning Pipeline ###

def main():
    """
    Performs a final, surgical cleaning of the generated TypedDict models.
    This script addresses known artifacts from the datamodel-codegen process
    to produce a clean, valid, and usable TypedDict models file for static analysis.
    """
    print(f"--- Starting definitive cleaning of {INPUT_TYPED_DICTS_PATH} ---")

    try:
        content = INPUT_TYPED_DICTS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {INPUT_TYPED_DICTS_PATH} not found. Please generate it first.")
        return

    # The order of these operations is critical for success.

    print("Step 1: Correcting known type mapping errors (e.g., Any -> float)...")
    content = fix_known_type_errors(content)

    print("Step 2: Removing known incomplete duplicate TypedDicts...")
    content = remove_specific_duplicates(content)

    print("Step 3: Consolidating suffixed TypedDicts (e.g., 'Hole4' -> 'Hole')...")
    content = promote_suffixed_classes(content)

    # <--- NEW STEP: Fix ordering of forward-referencing TypeAliases like 'Hotlinks'.
    print("Step 4: Reordering forward-referencing TypeAliases...")
    content = fix_forward_reference_aliases(content)

    print("Step 5: Assembling and formatting the final file...")
    content = assemble_final_file(content)

    FINAL_TYPED_DICTS_PATH.write_text(content, encoding="utf-8")
    print(f"✅ Successfully created final, clean TypedDict models at: {FINAL_TYPED_DICTS_PATH}")


### Cleaning Logic Functions (in execution order) ###

def fix_known_type_errors(content: str) -> str:
    """Corrects specific, known type mapping errors from the generator."""
    if "rotation: Any" in content:
        content = content.replace("rotation: Any", "rotation: float")
        print("    - Fixed 'rotation: Any' to 'rotation: float'.")
    return content


def remove_specific_duplicates(content: str) -> str:
    """
    Removes specific, known-to-be-incomplete TypedDict definitions that
    the generator creates before creating the correct, suffixed version.
    """
    duplicate_doc_rev_pattern = re.compile(
        r"class DocumentRevision\(TypedDict\):\n    revisionId: DocumentRevisionId\n",
        re.MULTILINE
    )
    if duplicate_doc_rev_pattern.search(content):
        content = duplicate_doc_rev_pattern.sub("", content)
        print("    - Removed incomplete 'DocumentRevision' TypedDict.")

    original_hole_pattern = re.compile(
        r"class Hole\(TypedDict\):\s*\n    polygonOutline:.*\n(?:    .*\n)*",
        re.MULTILINE
    )
    if original_hole_pattern.search(content):
        content = original_hole_pattern.sub("", content)
        print("    - Removed 'Hole' TypedDict with 'polygonOutline'.")

    return content.strip()


def promote_suffixed_classes(content: str) -> str:
    """
    Finds all TypedDict definitions ending with numbers and renames all occurrences
    of those specific class names to their base name (e.g., Hole4 -> Hole).
    """
    # <--- CHANGE: Regex now finds one or more digits (\d+) instead of just '1'.
    suffixed_class_pattern = re.compile(r"class\s+(\w+\d+)\s*\((?:TypedDict)?\):")
    suffixed_class_names = sorted(list(set(suffixed_class_pattern.findall(content))), key=len, reverse=True)

    if not suffixed_class_names:
        print("    - No suffixed TypedDicts found to consolidate.")
        return content

    print(f"    - Found suffixed TypedDicts to consolidate: {', '.join(suffixed_class_names)}")

    for suffixed_name in suffixed_class_names:
        # <--- CHANGE: Logic now correctly removes any trailing digits.
        base_name = re.sub(r'\d+$', '', suffixed_name)
        print(f"    - Renaming all instances of '{suffixed_name}' to '{base_name}'...")
        content = re.sub(r'\b' + re.escape(suffixed_name) + r'\b', base_name, content)

    return content


def fix_forward_reference_aliases(content: str) -> str:
    """
    Finds patterns like `Alias = List[Class]` defined before `class Class(TypedDict)`
    and swaps them to ensure correct definition order.
    """
    # <--- NEW FUNCTION: This regex finds the problematic alias and class definition blocks.
    # It uses a backreference `(?P=class_name)` to ensure it matches the correct class.
    pattern = re.compile(
        r"^(?P<alias_block>(?P<alias_name>\w+)\s*=\s*List\[(?P<class_name>\w+)\])\n+(?P<class_block>class\s+(?P=class_name)\(TypedDict\):(?:\n(?:    .*))+)",
        re.MULTILINE
    )

    # The replacement function swaps the captured groups.
    def replacer(match):
        print(f"    - Reordered '{match.group('alias_name')}' to be after '{match.group('class_name')}'.")
        return f"{match.group('class_block')}\n\n\n{match.group('alias_block')}"

    # Substitute all occurrences found in the content.
    content, num_replacements = pattern.subn(replacer, content)

    if num_replacements == 0:
        print("    - No forward-reference aliases needed reordering.")

    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, imports, and performs final formatting."""
    content = content.replace("TapirMasterModels = Any", "")

    body_lines = [
        line for line in content.splitlines()
        if line.strip()
        and not line.strip().startswith(("#", "from __future__", "from typing"))
    ]

    header = [
        "from __future__ import annotations",
        "",
        "from typing import Any, List, Literal, TypedDict, Union",
        "",
        "from typing_extensions import NotRequired",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]

    final_content = "\n".join(header + [""] + body_lines)

    # Standardize spacing between definitions for readability.
    final_content = re.sub(r'\n(class |[A-Z]\w+\s*=)', r'\n\n\n\1', final_content)
    # Clean up excessive newlines that might be introduced during processing.
    final_content = re.sub(r'\n{4,}', '\n\n\n', final_content)

    return final_content.strip() + "\n"


if __name__ == "__main__":
    main()