import socket
from urllib.parse import urlparse

def is_port_listening(address: str, port: int, timeout: float = 0.1) -> bool:
    host = urlparse(address).hostname if "://" in address else address

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False