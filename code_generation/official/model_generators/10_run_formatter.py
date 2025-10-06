from code_generation.official.paths import official_paths
from code_generation.shared.format import run_ruff_formatter


if __name__ == "__main__":
    run_ruff_formatter(official_paths)
