import subprocess
import sys
import pathlib


# --- Path Setup ---
PIPELINE_ROOT = pathlib.Path(__file__).parent.parent.resolve()
BUILD_DIR = PIPELINE_ROOT / "temp_files"
PIPELINE_DIR = PIPELINE_ROOT / "api_generator"
PROJECT_ROOT = PIPELINE_ROOT.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "src" / "multiconn_archicad" / "unified_api"

# Define intermediate file paths
ORGANIZED_COMMANDS_PATH = BUILD_DIR / "01_organized_commands.json"
COMMANDS_WITH_CODE_PATH = BUILD_DIR / "02_commands_with_code.json"


def run_stage(script_name: str, args: list[str]):
    """Helper function to run a pipeline stage as a subprocess."""
    script_path = PIPELINE_DIR / script_name
    command = [sys.executable, str(script_path)] + args

    print(f"\n--- Running Stage: {script_name} ---")
    result = subprocess.run(command, check=False)  # check=False to handle errors manually

    if result.returncode != 0:
        print(f"❌ Error in stage {script_name}. Halting pipeline.", file=sys.stderr)
        sys.exit(1)
    print(f"✅ Stage {script_name} completed successfully.")


def main():
    """Runs the full API generation pipeline step-by-step."""
    print("--- Starting Unified API Generation Pipeline ---")

    # Ensure the build directory exists and is clean
    BUILD_DIR.mkdir(exist_ok=True)
    if ORGANIZED_COMMANDS_PATH.exists():
        ORGANIZED_COMMANDS_PATH.unlink()
    if COMMANDS_WITH_CODE_PATH.exists():
        COMMANDS_WITH_CODE_PATH.unlink()

    # Run Stage 1: Organize Commands
    run_stage("01_organize_commands.py", ["--output-file", str(ORGANIZED_COMMANDS_PATH)])

    # Run Stage 2: Generate Method Code Strings
    run_stage(
        "02_generate_method_code.py",
        ["--input-file", str(ORGANIZED_COMMANDS_PATH), "--output-file", str(COMMANDS_WITH_CODE_PATH)],
    )

    # Run Stage 3: Assemble the final Python files
    run_stage(
        "03_assemble_api_files.py", ["--input-file", str(COMMANDS_WITH_CODE_PATH), "--output-dir", str(OUTPUT_DIR)]
    )

    # Run Stage 4: Format the generated output
    run_stage("04_format_output.py", ["--output-dir", str(OUTPUT_DIR)])

    print("\n✅✅✅ Unified API Generation Pipeline finished successfully! ✅✅✅")


if __name__ == "__main__":
    main()