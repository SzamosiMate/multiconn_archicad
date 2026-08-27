from __future__ import annotations

import logging
import time
from typing import Iterable
import psutil

log = logging.getLogger(__name__)


def find_pid_by_port(port: int) -> int | None:
    """Find the PID of the process listening on the specified port."""
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                return conn.pid
    except (psutil.AccessDenied, psutil.NoSuchProcess, Exception) as e:
        log.debug(f"Failed to query network connections for port {port}: {e}")
    return None


def find_port_by_pid(
    pid: int,
    allowed_ports: Iterable[int],
    timeout: float | None = None,
    poll_interval: float = 1.0,
) -> int | None:
    """
    Polls a process until it opens a listening socket on one of the allowed ports.
    If timeout is None, polls indefinitely until a listening port is found or the process dies.
    """
    allowed_set = set(allowed_ports)
    start_time = time.monotonic()

    psutil_process = psutil.Process(pid)

    while True:
        try:
            connections = psutil_process.net_connections(kind="inet")
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN and conn.laddr.port in allowed_set:
                    log.debug(f"Detected Archicad listening on port {conn.laddr.port}")
                    return conn.laddr.port
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            log.warning(f"Process PID {pid} terminated while waiting for listening port.")
            return None
        except psutil.AccessDenied as e:
            log.debug(f"Access denied querying network connections for PID {pid}: {e}")

        if timeout is not None and (time.monotonic() - start_time) >= timeout:
            log.error(f"Timed out after {timeout}s waiting for PID {pid} to listen on allowed ports.")
            return None

        time.sleep(poll_interval)


def get_process_rss_bytes(pid: int) -> int | None:
    """Returns the current Resident Set Size (RSS) memory in bytes for the given PID."""
    try:
        return psutil.Process(pid).memory_info().rss
    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
        return None
    except Exception as e:
        log.debug(f"Error querying memory for PID {pid}: {e}")
        return None


def terminate_process(pid: int, graceful_timeout: float = 60.0) -> None:
    """Gracefully terminates a process, falling back to force-kill if it exceeds the timeout."""
    try:
        p = psutil.Process(pid)
        p.terminate()  # Graceful termination
        try:
            p.wait(timeout=graceful_timeout)
            log.info(f"Process with PID {pid} terminated successfully.")
        except psutil.TimeoutExpired:
            log.warning(f"Process {pid} did not terminate in time. Force killing.")
            p.kill()
    except psutil.NoSuchProcess:
        log.info(f"No process found with PID {pid}. Already terminated?")
    except Exception as e:
        log.error(f"Error killing process PID {pid}: {e}", exc_info=True)