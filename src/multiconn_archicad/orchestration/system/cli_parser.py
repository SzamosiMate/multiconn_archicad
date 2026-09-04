import argparse
import sys
import logging
from typing import Optional

log = logging.getLogger(__name__)

_cli_parser = argparse.ArgumentParser(
    description="Multiconn-Archicad CLI options",
    allow_abbrev=False,
)
_cli_parser.add_argument(
    "--host",
    dest="host",
    type=str,
    default="http://127.0.0.1",
    help="Used to set the host for Archicad JSON API (default: http://127.0.0.1)"
)
_cli_parser.add_argument(
    "--port",
    dest="port",
    type=int,
    default=None,
    help="Used to set the port for Archicad JSON API (default: None)"
)

_parsed_cli_args_cache: Optional[argparse.Namespace] = None


def get_cli_args_once() -> argparse.Namespace:
    """
    Parses command-line arguments relevant to multiconn_archicad (--host, --port)
    once and caches the result. Ignores unknown arguments.
    Returns a namespace with defaults if parsing fails or if --host/--port are not provided.
    """
    global _parsed_cli_args_cache
    if _parsed_cli_args_cache is not None:
        return _parsed_cli_args_cache

    args_to_parse: list[str] = sys.argv[1:]

    try:
        parsed_args, unknown_args = _cli_parser.parse_known_args(args=args_to_parse)

        if unknown_args:
            log.debug(
                f"multiconn_archicad.cli_parser encountered unknown arguments: {unknown_args}. "
                "These will be ignored by multiconn_archicad."
            )
        _parsed_cli_args_cache = parsed_args
    except Exception as e:
        log.warning(
            f"Failed to parse CLI arguments for multiconn_archicad due to an error: {e}. "
            "Using default values for --host and --port."
        )
        # Create a namespace with default values
        _parsed_cli_args_cache = _cli_parser.parse_args([])

    return _parsed_cli_args_cache