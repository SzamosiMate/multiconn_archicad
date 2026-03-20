import httpx
import concurrent.futures

# Use a client with explicitly massive limits to overwhelm Archicad
limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
client = httpx.Client(limits=limits)

def fire_fast(req_id):
    try:
        resp = client.post("http://127.0.0.1:19723", json={"command": "API.IsAlive", "parameters": {}})
        print(f"Fast {req_id}: {resp.status_code}")
    except Exception as e:
        print(f"Fast {req_id} failed: {type(e).__name__} - {e}")

def test_pool_exhaustion():
    print("Starting Pool Exhaustion...")
    # Fire 200 requests as fast as possible on a massive pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
        executor.map(fire_fast, range(300))
    print("Pool Exhaustion Finished.")

if __name__ == "__main__":
    test_pool_exhaustion()