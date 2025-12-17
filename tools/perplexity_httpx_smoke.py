import os
import httpx

key = os.getenv("PERPLEXITY_API_KEY","")
model = os.getenv("PERPLEXITY_MODEL","sonar-pro")

print(f"key_len={len(key)} model={model}")

url = "https://api.perplexity.ai/chat/completions"
headers = {
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
    "User-Agent": "halo-mvp/0.1",
}

def run(msg: str):
    payload = {
        "model": model,
        "messages": [{"role":"user","content": msg}],
        "temperature": 0.2,
    }
    r = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    print("\nMSG=", msg)
    print("STATUS=", r.status_code)
    print("CT=", r.headers.get("content-type",""))
    print("BODY_HEAD=", (r.text or "")[:220].replace("\n"," "))

try:
    run("ping")
    run("use perplexity")
except Exception as e:
    print("EXC=", type(e).__name__, str(e))
