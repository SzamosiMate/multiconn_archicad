from __future__ import annotations

from typing import TYPE_CHECKING
import psutil

from multiconn_archicad.conn_header import ConnHeader
from multiconn_archicad.errors import RequestError, ArchicadAPIError

if TYPE_CHECKING:
    from multiconn_archicad.multi_conn import MultiConn
    from multiconn_archicad.basic_types import Port

import logging

log = logging.getLogger(__name__)


def _find_process_using_port(port: int) -> int | None:
    """Find the PID of the process using the specified port."""
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return conn.pid
    return None


def _kill_process(pid: int) -> None:
    """Kill the process with the given PID."""
    try:
        p = psutil.Process(pid)
        p.terminate()  # Graceful termination
        try:
            p.wait(timeout=3)
            log.info(f"Process with PID {pid} terminated successfully.")
        except psutil.TimeoutExpired:  # Force termination
            log.warning(f"Process {pid} did not terminate in time. Force killing.")
            p.kill()
    except psutil.NoSuchProcess:
        log.info(f"No process found with PID {pid}. Already terminated?")
    except Exception as e:
        log.error(f"Error killing process PID {pid}: {e}", exc_info=True)


class QuitAndDisconnect:
    def __init__(self, multi_conn: MultiConn):
        self.multi_conn: MultiConn = multi_conn

    def from_ports(self, *args: Port, force_after: None | float = None) -> list[ConnHeader]:
        return self._execute_action(
            [
                self.multi_conn.open_port_headers[port]
                for port in args
                if port in self.multi_conn.open_port_headers.keys()
            ],
            force_after,
        )

    def from_headers(self, *args: ConnHeader, force_after: None | float = None) -> list[ConnHeader]:
        headers_to_process = [h for h in args if h.port is not None]
        if len(headers_to_process) != len(args):
            log.warning("Some headers provided to quit did not have an assigned port and were skipped.")
        return self._execute_action(headers_to_process, force_after)

    def all(self, force_after: None | float = None) -> list[ConnHeader]:
        return self._execute_action(list(self.multi_conn.open_port_headers.values()), force_after)

    def _execute_action(self, conn_headers: list[ConnHeader], force_after: None | float = None) -> list[ConnHeader]:
        processed_headers = []
        for conn_header in conn_headers:
            if conn_header.port is None:
                continue
            log.info(f"Sending Quit command to Archicad on port {conn_header.port} and unassigning header.")
            quit_successful = False
            try:
                conn_header.core.post_tapir_command("QuitArchicad", timeout=force_after)
                quit_successful = True
            except (RequestError, ArchicadAPIError) as e:
                log.error(f"Failed to gracefully quit Archicad: error: {e}")
                if force_after:
                    if process := _find_process_using_port(conn_header.port):
                        _kill_process(process)
                    else:
                        log.warning(f"Could not find process listening on port {conn_header.port} to force kill.")
                    quit_successful = True
            if quit_successful:
                processed_headers.append(conn_header)
                self.multi_conn.open_port_headers.pop(conn_header.port)
                conn_header.unassign()
        return processed_headers
