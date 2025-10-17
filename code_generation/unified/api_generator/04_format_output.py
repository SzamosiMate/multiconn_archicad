import subprocess
import sys
import pathlib
import argparse

def main():
    """
    Runs the Ruff formatter on the final generated API package directory to ensure
    consistent style and formatting.
    """
    parser = argparse.ArgumentParser(description="Stage 4: Format the generated API package.")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=pathlib.Path,
        help="The final output directory of the generated API package to format.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    if not output_dir.is_dir():
        print(f"❌ Error: Output directory not found at: {output_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"--- Starting Final Formatting Step (Ruff) on: {output_dir} ---")

    command = ["ruff", "format", str(output_dir)]

    try:
        # `check=True` will raise a CalledProcessError if ruff fails.
        # `capture_output=True` and `text=True` store stdout/stderr.
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )
        print("\n   - Ruff stdout:")
        print(result.stdout or "   - (No output)")
        print(f"✅ Successfully formatted all files in {output_dir}.")

    except FileNotFoundError:
        print("\n❌ Error: 'ruff' command not found.", file=sys.stderr)
        print("   Please ensure Ruff is installed and in your system's PATH.", file=sys.stderr)
        sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("\n❌ Error: Ruff formatter failed.", file=sys.stderr)
        print(f"   Return Code: {e.returncode}", file=sys.stderr)
        print("\n--- Ruff stdout ---", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print("\n--- Ruff stderr ---", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()