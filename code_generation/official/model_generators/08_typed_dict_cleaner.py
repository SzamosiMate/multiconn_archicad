import re
from code_generation.official.paths import official_paths


def main():
    """
    Performs a final, surgical cleaning of the generated TypedDict models
    for the Official Archicad API. This script focuses on renaming wrapper
    classes to improve readability and developer experience.
    """
    print(f"--- Starting definitive cleaning of {official_paths.RAW_TYPED_DICTS} ---")

    try:
        content = official_paths.RAW_TYPED_DICTS.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {official_paths.RAW_TYPED_DICTS} not found. Please generate it first.")
        return

    # The order of these operations is critical for success.
    content = surgically_fix_rename_navigator_item(content)
    content = surgically_fix_dash_or_line_item(content)
    content = rename_problematic_wrappers(content)
    content = assemble_final_file(content)

    official_paths.CLEANED_TYPED_DICTS.write_text(content, encoding="utf-8")
    print(f"\n✅ Successfully created final, clean TypedDict models at: {official_paths.CLEANED_TYPED_DICTS}")


### --- Cleaning Logic Functions --- ###


def surgically_fix_rename_navigator_item(content: str) -> str:
    """Surgically renames the ambiguous RenameNavigatorItemParameters TypedDicts."""
    print("⚙️  Step 1: Surgically renaming `RenameNavigatorItem...` TypedDicts...")

    # Rename the class definitions first to be specific
    content = content.replace(
        "class RenameNavigatorItemParameters1(TypedDict):", "class RenameNavigatorItemByName(TypedDict):", 1
    )
    content = content.replace(
        "class RenameNavigatorItemParameters2(TypedDict):", "class RenameNavigatorItemById(TypedDict):", 1
    )
    content = content.replace(
        "class RenameNavigatorItemParameters3(TypedDict):", "class RenameNavigatorItemByNameAndId(TypedDict):", 1
    )

    # Then, update all references (primarily in the final union)
    content = content.replace("RenameNavigatorItemParameters1", "RenameNavigatorItemByName", -1)
    content = content.replace("RenameNavigatorItemParameters2", "RenameNavigatorItemById", -1)
    content = content.replace("RenameNavigatorItemParameters3", "RenameNavigatorItemByNameAndId", -1)

    print("    - Successfully renamed TypedDicts and updated the union.")
    return content


def surgically_fix_dash_or_line_item(content: str) -> str:
    """
    Surgically renames the DashOrLineItem1/2 wrappers to be more descriptive,
    preserving the necessary data structure for validation.
    """
    print("⚙️  Step 2: Surgically renaming `DashOrLineItem...` TypedDicts...")

    content = content.replace("class DashOrLineItem1(TypedDict):", "class DashItemWrapperItem(TypedDict):", 1)
    content = content.replace("class DashOrLineItem2(TypedDict):", "class LineItemWrapperItem(TypedDict):", 1)

    content = content.replace("DashOrLineItem1", "DashItemWrapperItem", -1)
    content = content.replace("DashOrLineItem2", "LineItemWrapperItem", -1)

    print("    - Successfully renamed wrappers to 'DashItemWrapperItem' and 'LineItemWrapperItem'.")
    return content


def rename_problematic_wrappers(content: str) -> str:
    """
    Finds all remaining wrapper classes ending in problematic suffixes (e.g., '1', 'OrError1')
    and renames them globally to a consistent '...WrapperItem' convention.
    """
    print("⚙️  Step 3: Renaming all remaining problematic wrapper TypedDicts...")

    pattern = re.compile(r"class\s+(?P<full_name>(?P<base_name>\w+?)(?:1|OrError1|OrErrorItem1))\(TypedDict\):")
    matches = list(pattern.finditer(content))

    # Sort by length (desc) to rename '...Item1' before '...1' if such cases exist.
    sorted_matches = sorted(matches, key=lambda m: len(m.group("full_name")), reverse=True)

    if not sorted_matches:
        print("    - No problematic wrapper classes found to rename.")
        return content

    num_renamed = 0
    for match in sorted_matches:
        old_name = match.group("full_name")
        base_name = match.group("base_name")
        new_name = f"{base_name}WrapperItem"

        # Check if we are accidentally re-renaming something we already fixed
        if "WrapperItem" in old_name:
            continue

        content = content.replace(old_name, new_name)
        num_renamed += 1
        print(f"    - Renamed {old_name} -> {new_name}")

    print(f"    - Renamed a total of {num_renamed} generic wrapper TypedDicts.")
    return content


def assemble_final_file(content: str) -> str:
    """Adds a standard header, removes the old one, and performs final formatting."""
    print("⚙️  Step 4: Assembling final file...")

    # Remove the placeholder model and all original import/header lines
    body = re.sub(r"^#.*?\n\n", "", content, flags=re.DOTALL)
    body = re.sub(r"^(from|import).*\n", "", body, flags=re.MULTILINE)
    body = re.sub(r"^OfficialArchicadApiMasterModels\s*=\s*Any\n*", "", body, flags=re.MULTILINE)

    header = [
        "from __future__ import annotations",
        "",
        "from typing import Any, List, Literal, TypedDict, Union",
        "",
        "from typing_extensions import NotRequired",
        "",
        "### This file is automatically generated and surgically cleaned. Do not edit directly. ###",
    ]
    final_header = "\n".join(header)

    full_content = final_header + "\n\n\n" + body.strip()

    # Standardize spacing to be 3 newlines between definitions
    full_content = re.sub(r"\n+(?=(class |[A-Z]\w+\s*=\s*))", "\n\n\n", full_content)
    full_content = re.sub(r"\n{4,}", "\n\n\n", full_content)

    return full_content.strip() + "\n"


if __name__ == "__main__":
    main()
