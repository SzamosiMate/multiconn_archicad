import re
from code_generation.official.paths import official_paths


def main():
    """
    Performs a final, surgical cleaning of the Pydantic models generated
    with the --use-annotated flag. This script focuses on structural issues
    that the generator cannot resolve on its own.
    """
    print(f"--- Starting definitive cleaning of {official_paths.RAW_PYDANTIC_MODELS} ---")

    try:
        content = official_paths.RAW_PYDANTIC_MODELS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Raw models file not found at {official_paths.RAW_PYDANTIC_MODELS}. Please generate it first.")
        return

    # Apply a series of cleaning functions in a specific order.
    content = remove_model_rebuild_calls(content)
    content = surgically_fix_rename_navigator_item(content)
    content = surgically_fix_dash_or_line_item(content)
    content = surgically_fix_numbering_style_enum(content)
    content = fix_root_model_unions_to_type_alias(content)
    content = rename_problematic_wrappers(content)
    content = assemble_final_file(content)

    official_paths.CLEANED_PYDANTIC_MODELS.write_text(content, encoding="utf-8")
    print(f"\n✅ Successfully created final, clean models at: {official_paths.CLEANED_PYDANTIC_MODELS}")


### --- Cleaning Logic Functions --- ###


def remove_model_rebuild_calls(content: str) -> str:
    cleaned_content = re.sub(r"^\w+\.model_rebuild\(\)\n?", "", content, flags=re.MULTILINE)
    print("✅ Step 1: Removed all `.model_rebuild()` calls.")
    return cleaned_content


def surgically_fix_rename_navigator_item(content: str) -> str:
    print("⚙️  Step 2: Surgically fixing `RenameNavigatorItemParameters`...")

    # FIX 1: Logic Correction
    # Start with the original content and chain the replacements,
    # ensuring the changes from each step are passed to the next.
    current_content = content.replace(
        "RenameNavigatorItemParameters1", "RenameNavigatorItemByName", -1 # Use -1 for global replace within the block
    )
    current_content = current_content.replace(
        "RenameNavigatorItemParameters2", "RenameNavigatorItemById", -1
    )
    current_content = current_content.replace(
        "RenameNavigatorItemParameters3", "RenameNavigatorItemByNameAndId", -1
    )

    # FIX 2: Regex Correction
    # This pattern is now robust. It finds the start of the class, then
    # non-greedily matches ALL content (`.*?`) until it finds the closing
    # parenthesis of the `root: (...)` block, making it immune to internal newlines.
    pattern = re.compile(
        r"class RenameNavigatorItemParameters\(\s*RootModel\[.*?\]\s*\):\s+root: \(.*?\)",
        re.DOTALL
    )
    replacement = "RenameNavigatorItemParameters: TypeAlias = RenameNavigatorItemByName | RenameNavigatorItemById | RenameNavigatorItemByNameAndId"

    # Operate on the `current_content` which has the renamed subclasses.
    final_content, num_replacements = pattern.subn(replacement, current_content, count=1)

    if num_replacements > 0:
        print("    - Successfully renamed wrapper classes and created a clean `TypeAlias`.")
    else:
        # This warning should no longer appear.
        print("    - ⚠️  Warning: `RenameNavigatorItemParameters` RootModel not found for replacement.")
        return current_content # Return the partially-modified content if the regex fails

    return final_content


def surgically_fix_dash_or_line_item(content: str) -> str:
    print("⚙️  Step 3: Surgically fixing `DashOrLineItem`...")
    lookahead = r"(?=\n\n\nclass|\Z)"
    pattern1 = re.compile(r"class DashOrLineItem1\(BaseModel\):.*?" + lookahead, flags=re.DOTALL)
    pattern2 = re.compile(r"class DashOrLineItem2\(BaseModel\):.*?" + lookahead, flags=re.DOTALL)

    content, count1 = pattern1.subn("", content, count=1)
    content, count2 = pattern2.subn("", content, count=1)
    content = content.replace("List[DashOrLineItem1 | DashOrLineItem2]", "List[DashItem | LineItem]")

    if count1 + count2 > 0:
        print("    - Successfully unwrapped to `List[DashItem | LineItem]` and removed wrapper classes.")
    return content


def surgically_fix_numbering_style_enum(content: str) -> str:
    """Renames the un-pythonic members of the NumberingStyle enum."""
    print("⚙️  Step 4: Surgically fixing `NumberingStyle` enum names...")

    content = content.replace("field_1 = '1'", "Style1 = '1'")
    content = content.replace("field_01 = '01'", "Style01 = '01'")
    content = content.replace("field_001 = '001'", "Style001 = '001'")
    content = content.replace("field_0001 = '0001'", "Style0001 = '0001'")

    return content


def fix_root_model_unions_to_type_alias(content: str) -> str:
    print("⚙️  Step 5: Converting remaining `RootModel` classes to `TypeAlias`...")
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


def rename_problematic_wrappers(content: str) -> str:
    """
    Finds all wrapper classes ending in problematic suffixes (e.g., '1', 'OrError1')
    and renames them globally to a consistent '...WrapperItem' convention.
    """
    print("⚙️  Step 6: Renaming all problematic wrapper classes...")

    pattern = re.compile(r"class\s+(?P<full_name>(?P<base_name>\w+?)(?:1|OrError1|OrErrorItem1))\(BaseModel\):")
    matches = list(pattern.finditer(content))
    sorted_matches = sorted(matches, key=lambda m: len(m.group("full_name")), reverse=True)

    if not sorted_matches:
        print("    - No problematic wrapper classes found to rename.")
        return content

    for match in sorted_matches:
        old_name = match.group("full_name")
        base_name = match.group("base_name")
        new_name = f"{base_name}WrapperItem"
        content = content.replace(old_name, new_name)
        print(f"    - Renamed {old_name} -> {new_name}")

    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, imports, and performs final formatting."""
    print("⚙️  Step 7: Assembling final file...")
    body = re.sub(r"^#.*?\n\n", "", content, flags=re.DOTALL)
    body = re.sub(r"^(from|import).*\n", "", body, flags=re.MULTILINE)
    body = re.sub(r"^OfficialArchicadApiMasterModels\s*:\s*TypeAlias = .*\n", "", body, flags=re.MULTILINE)

    header = [
        "from __future__ import annotations",
        "from typing import List, Literal, TypeAlias, Annotated, Any, Union, TypedDict",
        "from uuid import UUID",
        "from enum import Enum",
        "",
        "from pydantic import BaseModel, ConfigDict, Field, RootModel",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]
    final_header = "\n".join(header)

    full_content = final_header + "\n\n\n" + body.strip()

    full_content = re.sub(r"\n+(?=(class |[A-Z]\w+\s*:\s*TypeAlias))", "\n\n\n", full_content)
    full_content = re.sub(r"\n{4,}", "\n\n\n", full_content)

    return full_content.strip() + "\n"


if __name__ == "__main__":
    main()