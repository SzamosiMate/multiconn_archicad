import httpx
import threading

# Single shared client (like self.core.client)
shared_client = httpx.Client()


def fire_shared_request(name, command):
    try:
        resp = shared_client.post(
            "http://127.0.0.1:19723",
            json={"command": command, "parameters": {}}
        )
        print(f"{name} success: {resp.status_code}")
    except Exception as e:
        print(f"{name} failed: {e}")


def test_shared_client():
    print("Running Shared Client Test...")
    threads = []

    # Bombard the shared connection pool simultaneously
    for i in range(10):
        t1 = threading.Thread(target=fire_shared_request, args=(f"Thread-{i}A", "API.GetProductInfo"))
        t2 = threading.Thread(target=fire_shared_request, args=(f"Thread-{i}B", "API.IsAlive"))
        threads.extend([t1, t2])
        t1.start()
        t2.start()

    for t in threads:
        t.join()
    print("Shared Client Test Finished.")


if __name__ == "__main__":
    test_shared_client()