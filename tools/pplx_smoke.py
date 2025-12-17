import os, time, json
import httpx

def main():
    key = (os.getenv("PERPLEXITY_API_KEY") or "").strip()
    model = (os.getenv("PERPLEXITY_MODEL") or "sonar-pro").strip()

    print(f"PERPLEXITY_API_KEY={'SET' if key else 'MISSING'} len={len(key)}")
    print(f"PERPLEXITY_MODEL={model}")

    if not key:
        raise SystemExit("Missing PERPLEXITY_API_KEY in this shell/process.")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": "halo-mvp/0.1",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0.2,
    }

    timeout = httpx.Timeout(60.0, connect=20.0, read=60.0, write=20.0, pool=20.0)

    t0 = time.time()
    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        dt = time.time() - t0
        print(f"STATUS={r.status_code} elapsed={dt:.2f}s CT={r.headers.get('content-type')}")
        print(r.text[:400].replace("\n"," ") )
    except Exception as e:
        dt = time.time() - t0
        print(f"EXC={type(e).__name__} elapsed={dt:.2f}s msg={e}")

if __name__ == "__main__":
    main()
