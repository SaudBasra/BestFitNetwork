import requests
import json

url = "http://localhost:11434/api/generate"

payload = {
    "model": "llama3.2",
    "prompt": "What is the capital of France?",
}

try:
    # Stream response
    response = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, stream=True)

    if response.status_code == 200:
        print("✅ Success! Response from Ollama:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # Each line is a JSON object
                data = json.loads(decoded_line)
                print(data.get("response", ""), end="", flush=True)  # Print streaming response
        print()  # Finish line
    else:
        print(f"❌ Error: Status code {response.status_code}")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"🚫 Request failed: {e}")
