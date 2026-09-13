import argparse
import importlib
import pathlib
import re
import sys
import time

project_root = pathlib.Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from code_generation.tapir.paths import tapir_paths  # noqa: E402
from multiconn_archicad.constants import SUPPORTED_TAPIR_VERSION  # noqa: E402


CONSTANTS_FILE = getattr(tapir_paths, "CONSTANTS_FILE", project_root / "src" / "multiconn_archicad" / "constants.py")


# Sequence of modules to execute
STEPS = [
    ("Schema Generator", "code_generation.tapir.model_generators.01_schema_generator", {}),
    ("Code Generator", "code_generation.tapir.model_generators.02_generate_dicts_and_models", {}),
    ("Model Cleaner (Pydantic)", "code_generation.tapir.model_generators.03_model_cleaner", {}),
    ("Model Splitter (Pydantic)", "code_generation.tapir.model_generators.04_split_models", {}),
    ("Model Cleaner (TypedDicts)", "code_generation.tapir.model_generators.06_typed_dict_cleaner", {}),
    ("Model Splitter (TypedDicts)", "code_generation.tapir.model_generators.07_split_typed_dicts", {}),
    ("Generate Model Tests", "code_generation.tapir.model_generators.08_generate_model_tests", {}),
    ("Ruff Formatting Pipeline", "code_generation.tapir.model_generators.09_run_formatter", {}),
    ("Generation Audit", "code_generation.tapir.generation_audit", {"strict": True}),
]


def run_pipeline() -> None:
    args = parse_arguments()
    tapir_version = resolve_and_sync_tapir_version(args.tapir_version)
    tapir_paths.tapir_version = tapir_version
    update_readme_badge(tapir_version)

    print("==================================================")
    print("Starting Master Tapir Generation Pipeline")
    print(f"Target Tapir Version: {tapir_version}")
    print("==================================================")

    pipeline_start = time.time()
    run_pipeline_steps()
    if args.check_reproducibility:
        check_reproducibility()
    total_elapsed = time.time() - pipeline_start

    print("\n==================================================")
    print(f"Pipeline complete. Total execution time: {total_elapsed:.2f}s")
    print("==================================================")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tapir API Code Generation Pipeline")
    parser.add_argument(
        "--tapir-version",
        type=str,
        default=None,
        help="New Tapir version to pin. Defaults to constants.py.",
    )
    parser.add_argument(
        "--check-reproducibility",
        action="store_true",
        help="Run the generation steps twice and fail if the second run changes any generated output.",
    )
    return parser.parse_args()


def resolve_and_sync_tapir_version(requested_version: str | None) -> str:
    """
    Use a requested Tapir version and persist it, or use the current supported version.
    """
    if requested_version:
        version = requested_version.strip()
        update_constants_file(version)
        print(f"Using requested Tapir version: {version}")
        return version

    print(f"Using existing Tapir version from constants.py: {SUPPORTED_TAPIR_VERSION}")
    return SUPPORTED_TAPIR_VERSION


def update_constants_file(version: str) -> None:
    """Writes the new version directly into constants.py."""
    if not CONSTANTS_FILE.exists():
        raise FileNotFoundError(f"Could not find constants.py at: {CONSTANTS_FILE}")

    content = CONSTANTS_FILE.read_text(encoding="utf-8")

    # Matches: SUPPORTED_TAPIR_VERSION = "..."
    pattern = r'(SUPPORTED_TAPIR_VERSION\s*=\s*["\'])([^"\']+)(["\'])'
    new_content = re.sub(pattern, rf"\g<1>{version}\g<3>", content)

    if content != new_content:
        CONSTANTS_FILE.write_text(new_content, encoding="utf-8")
        print(f"Synced {CONSTANTS_FILE.name} with version {version}")


def update_readme_badge(version: str) -> None:
    """Automatically updates the Tapir version badge in the README."""
    readme_path = tapir_paths.PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        return

    content = readme_path.read_text(encoding="utf-8")

    # Matches: https://img.shields.io/badge/Tapir_Add--On-1.5.8-blue
    pattern = r"(https://img\.shields\.io/badge/Tapir_Add--On-)([^-]+)(-blue)"
    new_content = re.sub(pattern, rf"\g<1>{version}\g<3>", content)

    if content != new_content:
        readme_path.write_text(new_content, encoding="utf-8")
        print(f"Automatically updated README.md badge to {version}")


def run_pipeline_steps() -> None:
    for step_name, module_path, kwargs in STEPS:
        print(f"\nRunning: {step_name}")
        print("-" * 50)

        step_start = time.time()
        try:
            module = importlib.import_module(module_path)

            if hasattr(module, "main"):
                module.main(**kwargs)

            elapsed = time.time() - step_start
            print(f"{step_name} completed in {elapsed:.2f}s.")

        except Exception as e:
            print(f"Error executing {step_name} at module {module_path}: {e}")
            sys.exit(1)


def snapshot_generated_outputs() -> dict[pathlib.Path, bytes]:
    return {path: path.read_bytes() for path in tapir_paths.generated_outputs() if path.exists()}


def check_reproducibility() -> None:
    print("\nRunning reproducibility check")
    print("-" * 50)
    first_run = snapshot_generated_outputs()
    run_pipeline_steps()
    second_run = snapshot_generated_outputs()

    changed_paths = sorted(
        path for path in first_run.keys() | second_run.keys() if first_run.get(path) != second_run.get(path)
    )
    if changed_paths:
        changed = "\n".join(f"  - {path}" for path in changed_paths)
        raise SystemExit(f"Generation is not reproducible; the second run changed:\n{changed}")
    print("Reproducibility check passed.")


if __name__ == "__main__":
    run_pipeline()
