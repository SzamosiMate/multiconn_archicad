from code_generation.tapir.paths import tapir_paths
from code_generation.shared.format import run_ruff_formatter


def main():
    """Run the ruff formatting and post-processing steps."""
    run_ruff_formatter(tapir_paths)


if __name__ == "__main__":
    main()
