import sys
import time
import importlib


STEPS = [
#    ("Crawl Official Site", "code_generation.official.model_generators.01_crawl_site"),
    ("Assemble Master Schema", "code_generation.official.model_generators.02_generate_master_schema"),
    ("Command Details Generator", "code_generation.official.model_generators.03_generate_command_details"),
    ("Code Generator (Models & Dicts)", "code_generation.official.model_generators.04_generate_dicts_and_models"),
    ("Model Cleaner (Pydantic)", "code_generation.official.model_generators.05_model_cleaner"),
    ("Model Splitter (Pydantic)", "code_generation.official.model_generators.06_split_models"),
    ("Model Cleaner (TypedDicts)", "code_generation.official.model_generators.08_typed_dict_cleaner"),
    ("Model Splitter (TypedDicts)", "code_generation.official.model_generators.09_split_typed_dicts"),
    ("Generate Model Tests", "code_generation.official.model_generators.07_generate_model_tests"),
    ("Ruff Formatting Pipeline", "code_generation.official.model_generators.10_run_formatter"),
]


def main():
    print("==================================================")
    print("🔥 Starting Master Official Generation Pipeline 🔥")
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
            else:
                print(f"   - (Executed {step_name} via direct module load)")

            elapsed = time.time() - step_start
            print(f"⏱️  Finished {step_name} in {elapsed:.2f} seconds.")

        except ModuleNotFoundError as e:
            print(f"❌ Error: Could not find module for step '{step_name}' ({module_path}).")
            print(f"   Details: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: Pipeline failed at step '{step_name}'.")
            print(f"   Details: {e}")
            sys.exit(1)

    total_elapsed = time.time() - pipeline_start
    print("\n==================================================")
    print(f"🎉 Official Pipeline complete! Total time: {total_elapsed:.2f} seconds.")
    print("==================================================")


if __name__ == "__main__":
    main()