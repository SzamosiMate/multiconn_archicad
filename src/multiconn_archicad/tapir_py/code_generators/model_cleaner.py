import re
from pathlib import Path

# Path to the newly generated (imperfect) models from datamodel-codegen
INPUT_MODELS_PATH = Path("input_base_models.py")
# Final, clean output path
FINAL_MODELS_PATH = Path("base_models.py")


### Main Cleaning Pipeline ###

def main():
    """
    Performs a final, surgical cleaning of the generated Pydantic models.
    This script addresses all known artifacts from the datamodel-codegen process
    to produce a clean, valid, and highly usable models file.
    """
    print(f"--- Starting DEFINITIVE cleaning of {INPUT_MODELS_PATH} ---")

    try:
        content = INPUT_MODELS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {INPUT_MODELS_PATH} not found. Please generate it first.")
        return

    # The order of these operations is critical for success.

    # Step 1: Convert RootModels wrapping a Literal into a simple TypeAlias.
    print("Step 1: Converting RootModel[Literal[...]] to TypeAlias...")
    content = convert_root_model_literals_to_type_alias(content)

    # Step 2: Convert RootModels wrapping a Union (A | B) into a simple TypeAlias.
    # This regex is now more specific and will NOT affect RootModel[List[...]].
    print("Step 2: Converting RootModel[Union[...]] to TypeAlias...")
    content = convert_root_model_unions_to_type_alias(content)

    # Step 3: Remove known incomplete or duplicate class definitions.
    print("Step 3: Removing known incomplete duplicate classes...")
    content = remove_specific_duplicates(content)

    # Step 4: Promote "...1" suffixed classes to their base name.
    print("Step 4: Consolidating suffixed classes (e.g., 'Hole1' -> 'Hole')...")
    content = promote_suffixed_classes(content)

    # Step 5: Assemble the final file with a clean header and formatting.
    print("Step 5: Assembling and formatting the final file...")
    content = assemble_final_file(content)

    FINAL_MODELS_PATH.write_text(content, encoding="utf-8")
    print(f"✅ Successfully created final, clean models at: {FINAL_MODELS_PATH}")


### Cleaning Logic Functions (in execution order) ###

def convert_root_model_literals_to_type_alias(content: str) -> str:
    """Converts `class MyType(RootModel[Literal[...]]): ...` to `MyType = Literal[...]`"""
    pattern = re.compile(
        r"class\s+(\w+)\s*\(\s*RootModel\[\s*(Literal\[.+?\])\s*\]\s*\)\s*:\s*\n(?:    .+?\n)+",
        re.DOTALL
    )

    def replacement(match):
        class_name, type_hint = match.groups()
        return f"{class_name} = {type_hint.strip()}"

    return pattern.sub(replacement, content)


def convert_root_model_unions_to_type_alias(content: str) -> str:
    """
    Converts `class MyType(RootModel[A | B]): ...` to `MyType = A | B`.
    """
    pattern = re.compile(
        (
            r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\("  # 1. Capture the class name (group 1)
            r"\s*RootModel\["
            r"([^\]]*)"                              # 2. Capture the union types (group 2)
            r"\]\s*\)\s*:"
            r"\s+root\s*:\s*"
            # This non-capturing group precisely matches the root type, with or without parentheses.
            r"(?:"
                r"\(\s*\2\s*\)"                      # Case A: Matches ( TypeA | TypeB ) with internal whitespace
                r"|"                                 # OR
                r"\2"                                # Case B: Matches TypeA | TypeB without parentheses
            r")"
            # THE CRUCIAL FIX: This is a positive lookahead.
            # It ensures the match ends here and is followed by a newline or
            # the end of the file, but it DOES NOT CONSUME the newline.
            r"(?=\s*\n|\s*$)"
        ),
        re.DOTALL, # No re.VERBOSE here, as we use Python string concatenation for comments
    )

    def replacer(match: re.Match) -> str:
        """
        This function is called for each match found by re.sub.
        It constructs the replacement string.
        """
        class_name = match.group(1)
        union_types_with_whitespace = match.group(2)

        # Clean up the captured types string for consistent output
        types = [t.strip() for t in union_types_with_whitespace.split('|')]
        cleaned_union_types = " | ".join(type for type in types if type)  # filter out empty strings

        return f"{class_name} = {cleaned_union_types}"

    return pattern.sub(replacer, content)


def remove_specific_duplicates(content: str) -> str:
    """Removes known, less-complete class definitions before renaming."""
    duplicate_doc_rev_pattern = re.compile(
        r"class DocumentRevision\(BaseModel\):\n(?:    .+\n)+?    revisionId: DocumentRevisionId\n",
        re.MULTILINE
    )
    content = duplicate_doc_rev_pattern.sub("", content)

    original_hole_pattern = re.compile(
        r"class Hole\(BaseModel\):\n    polygonOutline: List\[Field2DCoordinate\].+\n(?:    .+\n)+",
        re.MULTILINE
    )
    content = original_hole_pattern.sub("", content)

    return content


def promote_suffixed_classes(content: str) -> str:
    """Finds all classes ending with '1' and renames them to their base name."""
    suffixed_class_pattern = re.compile(r"\b(\w+)1\b")
    base_names = sorted(list(set(suffixed_class_pattern.findall(content))), key=len, reverse=True)

    for base_name in base_names:
        content = re.sub(r'\b' + re.escape(base_name) + r'1\b', base_name, content)

    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, imports, and performs final formatting."""
    master_model_pattern = re.compile(r"class TapirMasterModels\(RootModel\[Any\]\):(?:\n.+)+")
    content = master_model_pattern.sub("", content)

    header = [
        "from __future__ import annotations",
        "from typing import Any, List, Literal, Union, TypeAlias",
        "from uuid import UUID",
        "",
        "from pydantic import BaseModel, ConfigDict, Field, RootModel",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###"
    ]

    body_lines = [
        line for line in content.splitlines()
        if line.strip() and not line.startswith(("from ", "# generated"))
    ]

    final_content = "\n".join(header + [""] + body_lines)

    final_content = re.sub(r'\n(class |[A-Z]\w+\s*=)', r'\n\n\n\1', final_content)
    final_content = final_content.replace('\n\n\n\n', '\n\n')

    return final_content.strip() + "\n"


if __name__ == "__main__":
    main()