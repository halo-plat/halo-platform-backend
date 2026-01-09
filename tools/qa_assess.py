import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
        out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        return p.returncode, out.strip()
    except Exception as e:
        return 99, f"EXCEPTION: {type(e).__name__}: {e}"

def main() -> int:
    if len(sys.argv) != 6:
        print("usage: qa_assess.py <repo_root> <artifacts_dir> <security_md> <privacy_md> <links_json>")
        return 2

    repo = Path(sys.argv[1]).resolve()
    artifacts = Path(sys.argv[2]).resolve()
    out_sec = Path(sys.argv[3]).resolve()
    out_priv = Path(sys.argv[4]).resolve()
    links_json = Path(sys.argv[5]).resolve()

    artifacts.mkdir(parents=True, exist_ok=True)

    # Evidence hooks (SCA/SAST/Secrets)  esecuzione best-effort
    evidence = {"generated_at_utc": utc_now_iso(), "repo": str(repo), "tools": {}}

    # SCA: pip-audit
    rc, out = run_cmd(["pip-audit", "-f", "json"], cwd=repo)
    evidence["tools"]["pip_audit"] = {"rc": rc, "executed": (rc in (0,1)), "raw": out[:20000]}
    (artifacts / "pip_audit.json").write_text(out + "\n", encoding="utf-8") if out else None

    # SAST: bandit (scansione repo QA; in seguito potremo puntare a SUT repo)
    rc, out = run_cmd(["bandit", "-r", str(repo), "-f", "json", "-q"], cwd=repo)
    evidence["tools"]["bandit"] = {"rc": rc, "executed": (rc in (0,1)), "raw": out[:20000]}
    (artifacts / "bandit.json").write_text(out + "\n", encoding="utf-8") if out else None

    # Secrets: detect-secrets
    rc, out = run_cmd(["detect-secrets", "scan", str(repo)], cwd=repo)
    evidence["tools"]["detect_secrets"] = {"rc": rc, "executed": (rc in (0,1)), "raw": out[:20000]}
    (artifacts / "detect_secrets.json").write_text(out + "\n", encoding="utf-8") if out else None

    # SECURITY ASSESSMENT (template + evidence pointers)
    sec = []
    sec.append("# Security Assessment Report")
    sec.append("")
    sec.append(f"- Generated (UTC): {evidence['generated_at_utc']}")
    sec.append(f"- Scope: Halo Test Lab evidence pack + automated security tooling outputs (best-effort)")
    sec.append("")
    sec.append("## Reference standards (standard internazionali)")
    sec.append("- ISO/IEC 27001:2022  control mapping (high-level)")
    sec.append("- NIST CSF 2.0  functional coverage (high-level)")
    sec.append("- OWASP ASVS / OWASP API Security Top 10  application-layer expectations (high-level)")
    sec.append("")
    sec.append("## Evidence inventory (audit trail)")
    sec.append("- pip-audit (SCA): artifacts/pip_audit.json")
    sec.append("- bandit (SAST): artifacts/bandit.json")
    sec.append("- detect-secrets: artifacts/detect_secrets.json")
    sec.append("")
    sec.append("## Key controls (control objectives)")
    sec.append("Authentication/Authorization, Transport security, Application-layer crypto (pairing), Logging/Monitoring, Dependency risk management, Secrets management.")
    sec.append("")
    sec.append("## Findings & remediation plan")
    sec.append("Populate from tool outputs + triage. Current report is auto-generated; use engineering.json + CI logs as supporting evidence.")
    out_sec.write_text("\n".join(sec) + "\n", encoding="utf-8")

    # PRIVACY ASSESSMENT (DPIA-lite template + evidence pointers)
    priv = []
    priv.append("# Privacy Assessment Report")
    priv.append("")
    priv.append(f"- Generated (UTC): {evidence['generated_at_utc']}")
    priv.append("- Scope: test automation environment + pairing flows; DPIA-lite (high-level) for audit readiness.")
    priv.append("")
    priv.append("## Reference standards / frameworks")
    priv.append("- GDPR principles (lawfulness, fairness, transparency, minimization, retention, integrity/confidentiality)")
    priv.append("- ISO/IEC 27701  privacy information management (high-level)")
    priv.append("")
    priv.append("## Data categories (placeholders)")
    priv.append("- Device identifiers, pairing session identifiers, telemetry/logs. No special categories expected in this test scope.")
    priv.append("")
    priv.append("## Technical & organizational measures (TOMs)")
    priv.append("Encryption in transit + application-layer envelope, access controls, log hygiene, secrets scanning, dependency governance.")
    priv.append("")
    priv.append("## Evidence inventory")
    priv.append("- detect-secrets output: artifacts/detect_secrets.json (proxy evidence for credential leakage controls)")
    priv.append("- engineering.json + report.html: execution traceability")
    out_priv.write_text("\n".join(priv) + "\n", encoding="utf-8")

    # links for GUI
    links = {
        "reports": [
            {"label": "Security assessment (markdown)", "href": "security_assessment.md"},
            {"label": "Privacy assessment (markdown)", "href": "privacy_assessment.md"},
            {"label": "pip-audit (json)", "href": "pip_audit.json"},
            {"label": "bandit (json)", "href": "bandit.json"},
            {"label": "detect-secrets (json)", "href": "detect_secrets.json"},
        ]
    }
    links_json.write_text(json.dumps(links, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK_ASSESS_WRITTEN", str(out_sec), str(out_priv))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())