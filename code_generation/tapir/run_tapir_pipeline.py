import sys
import pathlib

project_root = pathlib.Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import time
import importlib
import argparse
import re
from code_generation.tapir.paths import tapir_paths


# Sequence of modules to execute
STEPS = [
    ("Schema Generator", "code_generation.tapir.model_generators.01_schema_generator"),
    ("Code Generator", "code_generation.tapir.model_generators.02_generate_dicts_and_models"),
    ("Model Cleaner (Pydantic)", "code_generation.tapir.model_generators.03_model_cleaner"),
    ("Model Splitter (Pydantic)", "code_generation.tapir.model_generators.04_split_models"),
    ("Model Cleaner (TypedDicts)", "code_generation.tapir.model_generators.06_typed_dict_cleaner"),
    ("Model Splitter (TypedDicts)", "code_generation.tapir.model_generators.07_split_typed_dicts"),
    ("Generate Model Tests", "code_generation.tapir.model_generators.08_generate_model_tests"),
    ("Ruff Formatting Pipeline", "code_generation.tapir.model_generators.09_run_formatter"),
]


def run_pipeline() -> None:
    tapir_version = save_tapir_version()
    update_readme_badge(tapir_version)

    print("==================================================")
    print("🔥 Starting Master Tapir Generation Pipeline 🔥")
    print("==================================================")

    pipeline_start = time.time()
    run_pipeline_steps()
    total_elapsed = time.time() - pipeline_start

    print("\n==================================================")
    print(f"🎉 Pipeline Complete! Total execution time: {total_elapsed:.2f}s")
    print("==================================================")


def save_tapir_version() -> str:
    parser = argparse.ArgumentParser(description="Tapir API Code Generation Pipeline")
    parser.add_argument(
        "--tapir-version",
        type=str,
        required=True,
        help="Required: The Tapir tag/commit to pin against (e.g., 'v1.5.0'). Use 'main' for bleeding edge."
    )
    args = parser.parse_args()

    version_file = tapir_paths.PROJECT_ROOT / "TAPIR_VERSION"
    version_file.write_text(args.tapir_version, encoding="utf-8")
    print(f"📌 Pinned Tapir generation to version: {args.tapir_version}")
    return args.tapir_version


def update_readme_badge(version: str) -> None:
    """Automatically updates the Tapir version badge in the README."""
    readme_path = tapir_paths.PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        return

    content = readme_path.read_text(encoding="utf-8")

    # Matches: https://img.shields.io/badge/Tapir_Add--On-v1.2.3-blue
    pattern = r"(https://img\.shields\.io/badge/Tapir_Add--On-)([^-]+)(-blue)"
    new_content = re.sub(pattern, rf"\g<1>{version}\g<3>", content)

    if content != new_content:
        readme_path.write_text(new_content, encoding="utf-8")
        print(f"📝 Automatically updated README.md badge to {version}")


def run_pipeline_steps() -> None:
    for step_name, module_path in STEPS:
        print(f"\n🚀 Running: {step_name}")
        print("-" * 50)

        step_start = time.time()
        try:
            module = importlib.import_module(module_path)

            if hasattr(module, "main"):
                module.main()

            elapsed = time.time() - step_start
            print(f"✅ {step_name} completed in {elapsed:.2f}s.")

        except Exception as e:
            print(f"❌ Error executing {step_name} at module {module_path}: {e}")
            sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
