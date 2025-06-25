import re
from pathlib import Path

# The script will read this file and overwrite it with the cleaned version.
BASE_MODELS_INPUT_PATH = Path("input_base_models.py")
BASE_MODELS_OUTPUT_PATH = Path("base_models.py")


### Main Cleaning Pipeline ###

def main():
    """Main execution pipeline for the complete, multi-stage cleaning of base_models.py."""
    print(f"--- Starting COMPLETE cleaning of {BASE_MODELS_INPUT_PATH} ---")

    try:
        content = BASE_MODELS_INPUT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {BASE_MODELS_INPUT_PATH} not found. Please generate it first.")
        return

    # The order of these operations is critical for success.

    print("Step 1: Converting all RootModel definitions to TypeAlias...")
    content = convert_root_models_to_type_aliases(content)

    content = rename_implementation_classes(content)

    # print("Step 2: Removing known duplicate class definitions...")
    content = remove_known_duplicates(content)

    # print("Step 3: Consolidating '...Model' suffixed classes into base names...")
    content, type_map = consolidate_model_suffixed_classes(content)
    #
    # print("Step 4: Fixing all remaining ': Any' and 'List[Any]' type references...")
    content = fix_all_type_references(content, type_map)
    #
    # print("Step 5: Assembling and formatting the final, clean file...")
    content = assemble_final_file(content)

    # Overwrite the original file with the fully cleaned version
    BASE_MODELS_OUTPUT_PATH.write_text(content, encoding="utf-8")

    print(f"✅ Successfully performed all cleaning steps on {BASE_MODELS_OUTPUT_PATH}")


### Cleaning Logic Functions (in execution order) ###

def convert_root_models_to_type_aliases(content: str) -> str:
    """
    Finds Pydantic RootModel definitions that wrap ONLY a Literal type and
    converts them to simpler TypeAlias assignments. Other RootModels are left untouched.
    """
    # This improved regex specifically looks for `RootModel[Literal[...]`
    # It will not match `RootModel[SomeClass | Any]` or `RootModel[List[...]]`
    root_model_literal_pattern = re.compile(
        # Matches 'class MyType(RootModel[' and then specifically 'Literal['
        r"class\s+(\w+)\s*\(\s*RootModel\[\s*(Literal\[.+?\])\s*\]\s*\)\s*:\s*\n(?:    .+?\n)*",
        re.DOTALL
    )

    def replacement(match):
        class_name, type_hint = match.groups()
        # Remove the placeholder root model if it exists
        if "TapirBaseModels" in class_name: return ""
        # Create the TypeAlias
        return f"{class_name} = {type_hint.strip()}\n"

    return root_model_literal_pattern.sub(replacement, content)

def rename_implementation_classes(content: str) -> str:
    """Finds classes ending with '1' and renames them to their base name."""
    renamed_class_pattern = re.compile(r"\b(\w+)1\b")
    original_names = set(renamed_class_pattern.findall(content))
    for name in original_names:
        content = re.sub(r'\b' + re.escape(name) + r'1\b', name, content)
    return content


def remove_known_duplicates(content: str) -> str:
    """Removes the less-complete versions of known duplicated classes."""
    duplicate_doc_rev_pattern = re.compile(
        r"class DocumentRevision\(BaseModel\):\n(?:    .+\n)+?    revisionId: Any\n", re.MULTILINE
    )
    content = duplicate_doc_rev_pattern.sub("", content)

    duplicate_hole_pattern = re.compile(
        r"class Hole\(BaseModel\):\n\s+polygonOutline: List\[Any\].+\n\s+polygonArcs: List\[Any\].+\n", re.MULTILINE
    )
    content = duplicate_hole_pattern.sub("", content)
    return content


def consolidate_model_suffixed_classes(content: str) -> tuple[str, dict]:
    """
    Finds all `...Model` classes and type aliases, renames the class to the base name,
    and creates a map of all valid types for the next step.
    """
    type_map = {}

    for match in re.finditer(r"^(\w+)\s*=\s*(.+)", content, re.MULTILINE):
        type_map[match.group(1)] = match.group(2)

    class_pattern = re.compile(r"class\s+(\w+)\(BaseModel\):")
    model_suffix_map = {}

    for class_name in class_pattern.findall(content):
        if class_name.endswith('Model'):
            base_name = class_name[:-5]
            model_suffix_map[base_name] = class_name
            type_map[base_name] = base_name
        else:
            type_map[class_name] = class_name

    for base_name, suffixed_name in model_suffix_map.items():
        content = re.sub(r'\b' + re.escape(suffixed_name) + r'\b', base_name, content)
        content = re.sub(r"^\s*" + re.escape(base_name) + r"\s*=.+\n", "", content, flags=re.MULTILINE)

    return content, type_map


def fix_all_type_references(content: str, type_map: dict) -> str:
    """Uses the generated type_map to replace all ': Any' and fix broken List aliases."""

    # First, fix simple ': Any' types using a heuristic
    def fix_any(match):
        leading_whitespace, field_name, annotation = match.groups()
        inferred_type = ''.join(word.capitalize() for word in re.split('_|-', field_name))
        if inferred_type and not inferred_type[0].isupper():
            inferred_type = inferred_type[0].upper() + inferred_type[1:]

        if inferred_type in type_map:
            return f"{leading_whitespace}{field_name}: {inferred_type}"
        return match.group(0)

    content = re.sub(r"^(\s+)(\w+)(: Any)", fix_any, content, flags=re.MULTILINE)

    # Next, fix List aliases (e.g., Elements = List[Any])
    def fix_list_alias(match):
        alias_name, inner_type = match.groups()
        # Only fix if the inner type is 'Any' or self-referencing
        if inner_type == "Any" or inner_type == alias_name:
            singular_name = alias_name.rstrip('s')
            possible_inner = [f"{singular_name}ArrayItem", singular_name]
            for p in possible_inner:
                if p in type_map:
                    return f"{alias_name} = List[{p}]"
        return match.group(0)  # Return original if no fix is found or needed

    content = re.sub(r"^(\w+)\s*=\s*List\[(.+?)\]", fix_list_alias, content, flags=re.MULTILINE)

    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header and performs final formatting."""
    header = [
        "from __future__ import annotations",
        "from typing import Any, List, Literal, Union, TypeAlias",
        "from uuid import UUID",
        "from pydantic import BaseModel, ConfigDict, Field, RootModel",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###"
    ]

    body_lines = [
        line for line in content.splitlines()
        if not (
                line.startswith(("from ", "###", "# generated by")) or
                not line.strip()
        )
    ]

    final_content = "\n".join(header + body_lines)
    # Ensure consistent newlines between top-level definitions
    final_content = re.sub(r'\n(class |[A-Z]\w+\s*=)', r'\n\n\n\1', final_content)
    return final_content


if __name__ == "__main__":
    main()