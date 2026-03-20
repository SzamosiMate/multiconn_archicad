import httpx
import threading
import time


def fire_request(name, command):
    # Use a fresh client for every request (no shared keep-alive)
    with httpx.Client() as client:
        try:
            resp = client.post(
                "http://127.0.0.1:19723",
                json={"command": command, "parameters": {}}
            )
            print(f"{name} success: {resp.status_code}")
        except Exception as e:
            print(f"{name} failed: {e}")


def test_concurrency():
    print("Running Concurrency Test...")
    threads = []

    # Fire 10 simultaneous requests
    for i in range(10):
        t1 = threading.Thread(target=fire_request, args=(f"Thread-{i}A", "API.GetProductInfo"))
        t2 = threading.Thread(target=fire_request, args=(f"Thread-{i}B", "API.IsAlive"))
        threads.extend([t1, t2])
        t1.start()
        t2.start()

    for t in threads:
        t.join()
    print("Concurrency Test Finished.")


if __name__ == "__main__":
    test_concurrency()