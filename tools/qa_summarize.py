import json
import sys
from pathlib import Path
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def main() -> int:
    if len(sys.argv) != 6:
        print("usage: qa_summarize.py <report.json> <executive.md> <engineering.json> <index.html> <links.json>")
        return 2

    report_json = Path(sys.argv[1])
    out_exec = Path(sys.argv[2])
    out_eng = Path(sys.argv[3])
    out_html = Path(sys.argv[4])
    links_json = Path(sys.argv[5])

    if not report_json.exists():
        print("ERR: report.json not found:", str(report_json))
        return 3

    data = json.loads(report_json.read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    tests = data.get("tests") or []
    duration = float(data.get("duration") or 0.0)
    created = data.get("created") or utc_now_iso()

    passed = int(summary.get("passed") or 0)
    failed = int(summary.get("failed") or 0)
    skipped = int(summary.get("skipped") or 0)
    total = passed + failed + skipped + int(summary.get("xfailed") or 0) + int(summary.get("xpassed") or 0)

    failures = []
    for t in tests:
        if t.get("outcome") != "failed":
            continue
        call = t.get("call") or {}
        nodeid = t.get("nodeid")
        longrepr = call.get("longrepr") or call.get("crash") or "no longrepr"
        failures.append({"nodeid": nodeid, "when": call.get("when"), "duration": call.get("duration"), "longrepr": longrepr})

    pass_rate = (passed / total * 100.0) if total else 0.0

    exec_md = []
    exec_md.append("# Halo Test Lab  Executive Report")
    exec_md.append("")
    exec_md.append(f"- Run timestamp (UTC): {created}")
    exec_md.append(f"- Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    exec_md.append(f"- Duration (s): {duration:.2f}")
    exec_md.append("")
    exec_md.append("## KPI (Key Performance Indicator, indicatore chiave di performance)")
    exec_md.append(f"- Pass rate: {pass_rate:.1f}%")
    exec_md.append(f"- Failure count: {failed}")
    exec_md.append("")
    exec_md.append("## Evidenze")
    exec_md.append("- Report engineering: report.html / engineering.json / junit.xml / report.json")
    exec_md.append("- Security assessment: security_assessment.md (se generato)")
    exec_md.append("- Privacy assessment: privacy_assessment.md (se generato)")
    out_exec.write_text("\n".join(exec_md) + "\n", encoding="utf-8")

    eng = {
        "generated_at_utc": utc_now_iso(),
        "created": created,
        "duration_s": duration,
        "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
        "failures": failures,
        "artifacts": {
            "pytest_html": "report.html",
            "junit_xml": "junit.xml",
            "pytest_json": "report.json",
            "executive_md": "executive.md",
        },
    }
    out_eng.write_text(json.dumps(eng, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    links = {"reports": []}
    if links_json.exists():
        links = json.loads(links_json.read_text(encoding="utf-8"))

    li = "\n".join([f'<li><a href="{r["href"]}">{r["label"]}</a></li>' for r in links.get("reports", [])])

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Halo QA Control Room</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .kpi {{ display:flex; gap:16px; flex-wrap:wrap; }}
    .card {{ padding:12px 14px; border:1px solid #ddd; border-radius:10px; min-width:140px; }}
    a {{ text-decoration:none; }}
  </style>
</head>
<body>
  <h1>Halo QA Control Room (GUI)</h1>
  <p><b>Run (UTC)</b>: {created}</p>
  <div class="kpi">
    <div class="card"><b>Total</b><br/>{total}</div>
    <div class="card"><b>Passed</b><br/>{passed}</div>
    <div class="card"><b>Failed</b><br/>{failed}</div>
    <div class="card"><b>Skipped</b><br/>{skipped}</div>
    <div class="card"><b>Duration (s)</b><br/>{duration:.2f}</div>
    <div class="card"><b>Pass rate</b><br/>{pass_rate:.1f}%</div>
  </div>

  <h2>Reports</h2>
  <ul>
    <li><a href="report.html">Engineering HTML report (pytest-html)</a></li>
    <li><a href="executive.md">Executive report (markdown)</a></li>
    <li><a href="engineering.json">Engineering report (json)</a></li>
    <li><a href="junit.xml">JUnit XML</a></li>
    <li><a href="report.json">Pytest JSON report</a></li>
    {li}
  </ul>
</body>
</html>
"""
    out_html.write_text(html, encoding="utf-8")

    print("OK_SUMMARY_WRITTEN", str(out_exec), str(out_eng), str(out_html))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())