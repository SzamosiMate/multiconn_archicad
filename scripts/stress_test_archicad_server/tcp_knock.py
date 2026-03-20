import socket
import time

def test_tcp_knock():
    print("Running TCP Knock Test...")
    for i in range(500):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                s.connect(("127.0.0.1", 19723))
                # Instantly close without sending an HTTP GET
        except Exception as e:
            print(f"Failed at knock {i}: {e}")
            break
    print("TCP Knock Test Finished.")

if __name__ == "__main__":
    test_tcp_knock()