import sys
import time
import importlib


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


def run_pipeline():
    print("==================================================")
    print("🔥 Starting Master Tapir Generation Pipeline 🔥")
    print("==================================================")

    pipeline_start = time.time()

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

    total_elapsed = time.time() - pipeline_start
    print("\n==================================================")
    print(f"🎉 Pipeline Complete! Total execution time: {total_elapsed:.2f}s")
    print("==================================================")


if __name__ == "__main__":
    run_pipeline()
