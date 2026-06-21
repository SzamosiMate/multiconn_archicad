from code_generation.official.paths import official_paths
from code_generation.shared.format import run_ruff_formatter


def main():
    """Run the ruff formatting and post-processing steps."""
    run_ruff_formatter(official_paths)


if __name__ == "__main__":
    main()