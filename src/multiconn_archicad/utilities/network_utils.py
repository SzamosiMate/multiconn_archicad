import asyncio
import logging
from urllib.parse import urlparse

log = logging.getLogger(__name__)

async def is_port_listening(address: str, port: int, timeout: float = 0.1) -> bool:
    """
    Performs a raw TCP handshake (Knock) to verify if a port is open.

    Args:
        address: The host string (e.g., "http://127.0.0.1" or "127.0.0.1").
        port: The port number to check.
        timeout: How long to wait for the handshake in seconds.

    Returns:
        bool: True if the port is open and listening, False otherwise.
    """
    if "://" in address:
        host = urlparse(address).hostname or "127.0.0.1"
    else:
        host = address

    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )

        writer.close()
        await writer.wait_closed()
        return True

    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
        log.debug(f"Port {port} on {host} is not responding: {type(e).__name__}")
        return False
    except Exception as e:
        log.error(f"Unexpected error checking port {port} on {host}: {e}")
        return False