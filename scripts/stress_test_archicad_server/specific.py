import httpx
import time


def test_traceback_sequence():
    print("Running Traceback Sequence Test...")

    # We use a single client to mimic MultiConn's shared Keep-Alive socket
    with httpx.Client() as client:
        url = "http://127.0.0.1:19723"

        try:
            # 1. Background Worker: GetProductInfo
            print("Sending GetProductInfo...")
            client.post(url, json={"command": "API.GetProductInfo", "parameters": {}})

            # 2. Background Worker: GetProjectInfo
            print("Sending GetProjectInfo...")
            client.post(url, json={
                "command": "API.ExecuteAddOnCommand",
                "parameters": {"addOnCommandId": {"commandNamespace": "TapirCommand", "commandName": "GetProjectInfo"}}
            })

            # 3. Background Worker: GetArchicadLocation
            print("Sending GetArchicadLocation...")
            client.post(url, json={
                "command": "API.ExecuteAddOnCommand",
                "parameters": {
                    "addOnCommandId": {"commandNamespace": "TapirCommand", "commandName": "GetArchicadLocation"}}
            })

            # ZERO DELAY - mimic the new thread lock releasing instantly

            # 4. Main Thread: GetPropertyIds (The crash point)
            print("Sending GetPropertyIds...")

            # Replace these with the actual Layer User ID payload your app uses if you know it,
            # or just use a generic BuiltIn property to test the endpoint.
            payload = {
                "command": "API.GetPropertyIds",
                "parameters": {
                    "properties": [
                        {"type": "BuiltIn", "nonLocalizedName": "Layer"}
                    ]
                }
            }

            resp = client.post(url, json=payload)
            print(f"GetPropertyIds success: {resp.status_code}")

        except Exception as e:
            print(f"\nCRASH TRIGGERED! {type(e).__name__}: {e}")


if __name__ == "__main__":
    # Run it 10 times in a row to ensure we catch race conditions
    for i in range(10):
        print(f"\n--- Iteration {i + 1} ---")
        test_traceback_sequence()