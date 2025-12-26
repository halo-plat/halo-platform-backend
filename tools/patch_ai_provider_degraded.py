import re
from pathlib import Path

TARGET = Path("app") / "ai_provider.py"

def sub(pattern: str, repl: str, text: str, label: str):
    new_text, n = re.subn(pattern, repl, text, flags=re.MULTILINE | re.DOTALL)
    return new_text, n, label

def main():
    if not TARGET.exists():
        raise SystemExit(f"[ERR] File not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    changes = []

    # --- OPENAI missing key ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*"fallback_missing_OPENAI_API_KEY"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=AIProviderId.OPENAI,\n'
        '                routing_note="degraded_missing_OPENAI_API_KEY",\n'
        '            )',
        text, "openai_missing_key"
    )
    changes.append((lbl, n))

    # --- OPENAI error ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*f"fallback_openai_error:\{type\(e\)\.__name__\}"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=AIProviderId.OPENAI,\n'
        '                routing_note=f"degraded_openai_error:{type(e).__name__}",\n'
        '            )',
        text, "openai_error"
    )
    changes.append((lbl, n))

    # --- GEMINI missing key ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*"fallback_missing_GEMINI_API_KEY"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=AIProviderId.CLOUD_AI,\n'
        '                routing_note="degraded_missing_GEMINI_API_KEY",\n'
        '            )',
        text, "gemini_missing_key"
    )
    changes.append((lbl, n))

    # --- GEMINI error ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*f"fallback_gemini_error:\{type\(e\)\.__name__\}"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=AIProviderId.CLOUD_AI,\n'
        '                routing_note=f"degraded_gemini_error:{type(e).__name__}",\n'
        '            )',
        text, "gemini_error"
    )
    changes.append((lbl, n))

    # --- OPENAI COMPAT missing config ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*f"fallback_missing_\{provider_name\.value\}_config"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=provider_name,\n'
        '                routing_note=f"degraded_missing_{provider_name.value}_config",\n'
        '            )',
        text, "openai_compat_missing_config"
    )
    changes.append((lbl, n))

    # --- OPENAI COMPAT error ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*f"fallback_\{provider_name\.value\}_error:\{type\(e\)\.__name__\}"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=provider_name,\n'
        '                routing_note=f"degraded_{provider_name.value}_error:{type(e).__name__}",\n'
        '            )',
        text, "openai_compat_error"
    )
    changes.append((lbl, n))

    # --- PERPLEXITY (necessario per sbloccare il tuo failing e2e: applied=echo) ---
    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*"fallback_missing_PERPLEXITY_API_KEY"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=AIProviderId.PERPLEXITY,\n'
        '                routing_note="degraded_missing_PERPLEXITY_API_KEY",\n'
        '            )',
        text, "perplexity_missing_key"
    )
    changes.append((lbl, n))

    text, n, lbl = sub(
        r'return\s+ProviderResult\(\s*f"ECHO:\s*\{user_utterance\}"\s*,\s*AIProviderId\.ECHO\s*,\s*f"fallback_perplexity_error:\{type\(e\)\.__name__\}"\s*\)',
        'return ProviderResult(\n'
        '                reply_text=f"ECHO: {user_utterance}",\n'
        '                provider_applied=AIProviderId.PERPLEXITY,\n'
        '                routing_note=f"degraded_perplexity_error:{type(e).__name__}",\n'
        '            )',
        text, "perplexity_error"
    )
    changes.append((lbl, n))

    # Report
    print("== PATCH REPORT ==")
    total = 0
    for lbl, n in changes:
        print(f"{lbl}: {n}")
        total += n

    if total == 0:
        raise SystemExit("[ERR] No replacements applied. File format may differ from expected patterns.")

    TARGET.write_text(text, encoding="utf-8")
    print(f"[OK] Patched {TARGET} (total replacements: {total})")

if __name__ == "__main__":
    main()
