from code_generation.tapir.paths import tapir_paths
from code_generation.shared.format import run_ruff_formatter

if __name__ == "__main__":
    run_ruff_formatter(tapir_paths)
