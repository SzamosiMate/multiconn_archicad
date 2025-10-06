import subprocess
import sys
from code_generation.tapir.paths import TapirApiPaths
from code_generation.official.paths import OfficialApiPaths


def run_ruff_formatter(paths: TapirApiPaths | OfficialApiPaths):
    """
    Runs the Ruff formatter on all generated Python files to ensure
    consistent style and formatting.
    """
    print("--- Starting Final Formatting Step (Ruff) ---")

    files_to_format = [
        paths.FINAL_PYDANTIC_TYPES,
        paths.FINAL_PYDANTIC_COMMANDS,
        paths.FINAL_TYPED_DICT_TYPES,
        paths.FINAL_TYPED_DICT_COMMANDS,
    ]

    file_paths_str = [str(p) for p in files_to_format]
    print("   - Found the following files to format:")
    for path in file_paths_str:
        print(f"     - {path}")

    command = ["ruff", "format", *file_paths_str]

    try:
        # `check=True` will raise a CalledProcessError if ruff fails.
        # `capture_output=True` and `text=True` store stdout/stderr.
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        print("\n   - Ruff stdout:")
        print(result.stdout or "   - (No output)")
        print("✅ Successfully formatted all generated files.")

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