import json
import sys
import argparse
from code_generation.tapir.paths import tapir_paths
from code_generation.official.paths import official_paths


def main():
    parser = argparse.ArgumentParser(description="Stage 1: Load and organize command details.")
    parser.add_argument("--output-file", required=True, help="Path to save the organized JSON.")
    args = parser.parse_args()

    try:
        with open(tapir_paths.COMMAND_DETAILS_OUTPUT, "r", encoding="utf-8") as f:
            tapir_details = json.load(f)
            for cmd in tapir_details:
                cmd["source"] = "tapir"

        with open(official_paths.COMMAND_DETAILS_OUTPUT, "r", encoding="utf-8") as f:
            official_details = json.load(f)
            for cmd in official_details:
                cmd["source"] = "official"

    except FileNotFoundError as e:
        print(f"❌ Error: {e.filename} not found. Run model generation first.", file=sys.stderr)
        sys.exit(1)

    organized = {"tapir": {}, "official": {}}
    for command in tapir_details + official_details:
        source = command["source"]
        group = command.get("group", "Miscellaneous")
        if group == "Developer Commands":
            continue
        if group not in organized[source]:
            organized[source][group] = []
        organized[source][group].append(command)

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(organized, f, indent=4)

    print(f"Organized data for {len(tapir_details) + len(official_details)} commands saved to {args.output_file}")


if __name__ == "__main__":
    main()
