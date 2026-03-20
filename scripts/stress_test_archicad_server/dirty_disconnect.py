import socket
import struct
import time
import concurrent.futures


def dirty_disconnect(req_id):
    # Raw HTTP POST request
    http_request = (
        "POST / HTTP/1.1\r\n"
        "Host: 127.0.0.1:19723\r\n"
        "Content-Length: 65\r\n"
        "Content-Type: application/json\r\n\r\n"
        "{\"command\": \"API.GetProductInfo\", \"parameters\": {}}"
    ).encode('utf-8')

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 19723))
        s.sendall(http_request)

        # Do NOT wait for a response.
        # Force a TCP RST (Reset) packet instead of a graceful FIN closure.
        # This simulates a hard network crash or a violently killed Python thread.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        s.close()
        print(f"Dirty disconnect {req_id} sent.")
    except Exception as e:
        print(f"Dirty disconnect {req_id} failed to connect: {e}")


def test_dirty_disconnects():
    print("Starting Dirty Disconnects...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        executor.map(dirty_disconnect, range(50))
    print("Dirty Disconnects Finished.")


if __name__ == "__main__":
    test_dirty_disconnects()