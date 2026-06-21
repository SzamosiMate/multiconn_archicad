import re
import subprocess
import sys
from pathlib import Path
from code_generation.tapir.paths import TapirApiPaths
from code_generation.official.paths import OfficialApiPaths


def run_ruff_formatter(paths: TapirApiPaths | OfficialApiPaths):
    """
    Orchestration function to clean docstrings, execute Ruff formatting,
    and post-process file structures for consistent, elegant layouts.
    """
    print("--- Starting Final Formatting Pipeline (Ruff + Post-Processing) ---")

    # Step 1: Collect existing target files
    files = _get_files_to_format(paths)
    if not files:
        print("   - No generated files found to format.")
        return

    print("   - Found the following files to process:")
    for path in files:
        print(f"     - {path}")

    # Step 2: Collapse multiline attribute and TypeAlias docstrings (Pre-processing)
    print("\n   - Pre-processing: Collapsing multiline attribute/TypeAlias docstrings...")
    for path in files:
        _collapse_multiline_docstrings(path)

    # Step 3: Run standard Ruff formatter
    print("\n   - Formatting: Running ruff format...")
    _run_ruff_format(files)

    # Step 4: Remove blank lines between docstrings and parameters/fields (Post-processing)
    print("\n   - Post-processing: Removing blank lines after nested docstrings...")
    for path in files:
        _remove_class_docstring_blank_lines(path)

    print("✅ Successfully formatted all generated files.")


def _get_files_to_format(paths: TapirApiPaths | OfficialApiPaths) -> list[Path]:
    """Collects and returns all existing target pipeline files."""
    targets = [
        paths.FINAL_PYDANTIC_TYPES,
        paths.FINAL_PYDANTIC_COMMANDS,
        paths.FINAL_TYPED_DICT_TYPES,
        paths.FINAL_TYPED_DICT_COMMANDS,
    ]
    return [p for p in targets if p.exists()]


def _collapse_multiline_docstrings(file_path: Path) -> None:
    """Collapses multiline docstrings containing a single line of text down to a single line."""
    try:
        content = file_path.read_text(encoding="utf-8")
        # Matches opening """, newline, optional indentation, single line of text, newline, indent, closing """
        pattern = re.compile(r'"""\s*\n\s*([^\n]+?)\s*\n\s*"""', re.MULTILINE)
        collapsed = pattern.sub(r'"""\1"""', content)
        if collapsed != content:
            file_path.write_text(collapsed, encoding="utf-8")
            print(f"     - Collapsed docstrings in: {file_path.name}")
    except Exception as e:
        print(f"     - Warning: Could not collapse docstrings in {file_path.name}: {e}")


def _remove_class_docstring_blank_lines(file_path: Path) -> None:
    """
    Surgically removes the empty line directly between a class-level docstring
    and its fields/methods, leaving all other module-level spacing (including TypeAliases)
    completely untouched.
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        # Matches:
        # Group 1: class Header(Inheritance): \n [indent] """Docstring"""
        # Followed by one or more blank lines
        # Group 2: [indent] (the class members)
        pattern = re.compile(r'(class\s+\w+(?:\([^)]*\))?\s*:\s*\n[ \t]*"""[^"\n]+""")\n\n+([ \t]+)', re.MULTILINE)

        # Replace the multiple newlines between Group 1 and Group 2 with a single newline
        cleaned = pattern.sub(r"\1\n\2", content)

        if cleaned != content:
            file_path.write_text(cleaned, encoding="utf-8")
            print(f"     - Removed class-nested blank lines in: {file_path.name}")
    except Exception as e:
        print(f"     - Warning: Could not strip blank lines in {file_path.name}: {e}")


def _run_ruff_format(file_paths: list[Path]) -> None:
    """Invokes Ruff formatter on target Python files."""
    file_paths_str = [str(p) for p in file_paths]
    command = ["ruff", "format", *file_paths_str]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        print("\n   - Ruff format stdout:")
        print(result.stdout or "   - (No output)")
    except FileNotFoundError:
        print("\n❌ Error: 'ruff' command not found.", file=sys.stderr)
        print("   Please ensure Ruff is installed and available in your system's PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("\n❌ Error: Ruff formatter failed.", file=sys.stderr)
        print(f"   Return Code: {e.returncode}", file=sys.stderr)
        print("\n--- Ruff stdout ---", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print("\n--- Ruff stderr ---", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)