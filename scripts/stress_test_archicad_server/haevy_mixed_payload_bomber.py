import httpx
import concurrent.futures

# A massive payload to stress Archicad's JSON parser and memory allocator
HEAVY_PAYLOAD = {
    "command": "API.GetPropertyIds",
    "parameters": {
        "properties":[{"name": f"FakeProperty_{i}", "type": "BuiltIn"} for i in range(2000)]
    }
}

TAPIR_PAYLOAD = {
    "command": "API.ExecuteAddOnCommand",
    "parameters": {"addOnCommandId": {"commandNamespace": "TapirCommand", "commandName": "GetProjectInfo"}}
}

client = httpx.Client()

def fire_heavy(req_id):
    try:
        # Alternate between heavy core commands and Tapir commands
        payload = HEAVY_PAYLOAD if req_id % 2 == 0 else TAPIR_PAYLOAD
        resp = client.post("http://127.0.0.1:19723", json=payload, timeout=5.0)
        print(f"Req {req_id} ({payload['command']}): {resp.status_code}")
    except Exception as e:
        print(f"Req {req_id} failed: {type(e).__name__} - {e}")

def test_heavy_bombardment():
    print("Starting Heavy Bombardment...")
    # Blast 100 heavy requests concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(fire_heavy, range(100))
    print("Heavy Bombardment Finished.")

if __name__ == "__main__":
    test_heavy_bombardment()