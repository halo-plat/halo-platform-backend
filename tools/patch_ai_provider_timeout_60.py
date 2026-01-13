from pathlib import Path
import re

p = Path("app/ai_provider.py")
txt = p.read_text(encoding="utf-8")

pat = r"httpx\.AsyncClient\(timeout=25\)"
rep = 'httpx.AsyncClient(timeout=float(os.getenv("HALO_AI_UPSTREAM_TIMEOUT_SEC") or "60"))'

new = re.sub(pat, rep, txt)
if new == txt:
    raise SystemExit("No changes applied. Pattern not found (timeout=25).")

p.write_text(new, encoding="utf-8")
print("OK: ai_provider.py patched: timeout=25 -> env(HALO_AI_UPSTREAM_TIMEOUT_SEC) default 60")