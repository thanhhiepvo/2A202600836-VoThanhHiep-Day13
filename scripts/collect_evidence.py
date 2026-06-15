#!/usr/bin/env python3
"""Collect grading evidence into docs/evidence/."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"
LOG_PATH = ROOT / "data" / "logs.jsonl"
AUDIT_PATH = ROOT / "data" / "audit.jsonl"


def langfuse_traces(limit: int = 100) -> list[dict]:
    load_dotenv(ROOT / ".env")
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    sk = os.environ.get("LANGFUSE_SECRET_KEY", "")
    if not pk or not sk:
        return []
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{host}/api/public/traces", headers=headers, params={"limit": limit})
        r.raise_for_status()
        return r.json().get("data", [])


def pick_log_lines() -> dict[str, str]:
    if not LOG_PATH.exists():
        return {}
    lines = [json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    correlation = next((l for l in lines if l.get("correlation_id") and l.get("correlation_id") != "MISSING"), None)
    pii = next(
        (l for l in lines if "REDACTED_EMAIL" in json.dumps(l) or "REDACTED_CREDIT_CARD" in json.dumps(l)),
        None,
    )
    return {
        "correlation_id": json.dumps(correlation, indent=2) if correlation else "",
        "pii_redaction": json.dumps(pii, indent=2) if pii else "",
    }


def screenshot_dashboard() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return render_dashboard_png()

    url = "http://127.0.0.1:8000/dashboard"
    out = EVIDENCE / "dashboard-6-panels.png"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(2000)
            page.screenshot(path=str(out), full_page=True)
            browser.close()
        return out.exists()
    except Exception:
        return render_dashboard_png()


def render_dashboard_png() -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    metrics = json.loads((EVIDENCE / "metrics.json").read_text(encoding="utf-8"))
    if "error" in metrics:
        return False

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle("Day 13 Observability Dashboard (6 Panels)", fontsize=14, fontweight="bold")

    latency = [metrics["latency_p50"], metrics["latency_p95"], metrics["latency_p99"]]
    axes[0, 0].bar(["P50", "P95", "P99"], latency, color=["#22c55e", "#f59e0b", "#ef4444"])
    axes[0, 0].set_title("1. Latency (ms)")
    axes[0, 0].axhline(3000, color="#fbbf24", linestyle="--", label="SLO 3000ms")
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].bar(["Traffic"], [metrics["traffic"]], color="#38bdf8")
    axes[0, 1].set_title("2. Traffic (requests)")

    total_errors = sum((metrics.get("error_breakdown") or {}).values())
    error_rate = (total_errors / metrics["traffic"] * 100) if metrics["traffic"] else 0
    axes[0, 2].bar(["Error %"], [error_rate], color="#ef4444")
    axes[0, 2].set_title("3. Error Rate (%)")
    axes[0, 2].axhline(2, color="#fbbf24", linestyle="--", label="SLO 2%")
    axes[0, 2].legend(fontsize=8)

    axes[1, 0].bar(["Total Cost"], [metrics["total_cost_usd"]], color="#a855f7")
    axes[1, 0].set_title("4. Cost (USD)")

    axes[1, 1].bar(["In", "Out"], [metrics["tokens_in_total"], metrics["tokens_out_total"]], color=["#6366f1", "#a855f7"])
    axes[1, 1].set_title("5. Tokens In/Out")

    axes[1, 2].bar(["Quality"], [metrics["quality_avg"]], color="#22c55e")
    axes[1, 2].set_title("6. Quality Score (avg)")
    axes[1, 2].set_ylim(0, 1)
    axes[1, 2].axhline(0.75, color="#fbbf24", linestyle="--", label="SLO 0.75")
    axes[1, 2].legend(fontsize=8)

    plt.tight_layout()
    out = EVIDENCE / "dashboard-6-panels.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out.exists()


def render_text_png(filename: str, title: str, content: str) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left")
    ax.text(0.02, 0.95, content, transform=ax.transAxes, fontsize=9, va="top", family="monospace")
    out = EVIDENCE / filename
    fig.savefig(out, dpi=120, bbox_inches="tight", facecolor="#1e293b")
    plt.close(fig)
    return out.exists()


def pick_audit_lines(limit: int = 5) -> str:
    if not AUDIT_PATH.exists():
        return ""
    lines = [line for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def run_incident_demo(client: httpx.Client) -> dict:
    baseline = client.get("http://127.0.0.1:8000/metrics", timeout=10.0).json()
    payload = {
        "user_id": "u99",
        "session_id": "s99",
        "feature": "qa",
        "message": "Explain monitoring policy",
    }
    normal = client.post("http://127.0.0.1:8000/chat", json=payload, timeout=30.0)
    client.post("http://127.0.0.1:8000/incidents/rag_slow/enable", timeout=10.0)
    slow = client.post("http://127.0.0.1:8000/chat", json=payload, timeout=30.0)
    client.post("http://127.0.0.1:8000/incidents/rag_slow/disable", timeout=10.0)
    after = client.get("http://127.0.0.1:8000/metrics", timeout=10.0).json()
    return {
        "baseline_metrics": baseline,
        "normal_latency_ms": normal.json().get("latency_ms"),
        "slow_latency_ms": slow.json().get("latency_ms"),
        "after_metrics": after,
        "normal_correlation_id": normal.json().get("correlation_id"),
        "slow_correlation_id": slow.json().get("correlation_id"),
    }


def fetch_trace_detail(trace_id: str) -> dict:
    load_dotenv(ROOT / ".env")
    pk = os.environ["LANGFUSE_PUBLIC_KEY"]
    sk = os.environ["LANGFUSE_SECRET_KEY"]
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{host}/api/public/traces/{trace_id}", headers=headers)
        r.raise_for_status()
        return r.json()


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "load_test.py"), "--concurrency", "5"],
        cwd=ROOT,
        check=False,
    )

    validate = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_logs.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    (EVIDENCE / "validate_logs.txt").write_text(validate.stdout, encoding="utf-8")

    try:
        metrics = httpx.get("http://127.0.0.1:8000/metrics", timeout=10.0).json()
    except Exception as exc:
        metrics = {"error": str(exc)}
    (EVIDENCE / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    shutil.copy(ROOT / "config" / "alert_rules.yaml", EVIDENCE / "alert_rules.yaml")

    log_snippets = pick_log_lines()
    (EVIDENCE / "log-correlation-id.json").write_text(log_snippets.get("correlation_id", ""), encoding="utf-8")
    (EVIDENCE / "log-pii-redaction.json").write_text(log_snippets.get("pii_redaction", ""), encoding="utf-8")

    traces = langfuse_traces()
    (EVIDENCE / "langfuse-traces.json").write_text(json.dumps(traces[:20], indent=2), encoding="utf-8")
    trace_summary = {
        "total_traces_fetched": len(traces),
        "sample_trace_ids": [t.get("id") for t in traces[:10]],
        "langfuse_url": os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    }
    (EVIDENCE / "langfuse-summary.json").write_text(json.dumps(trace_summary, indent=2), encoding="utf-8")

    if traces:
        detail = fetch_trace_detail(traces[0]["id"])
        (EVIDENCE / "langfuse-trace-waterfall.json").write_text(json.dumps(detail, indent=2), encoding="utf-8")
        waterfall_text = json.dumps(
            {
                "trace_id": detail.get("id"),
                "name": detail.get("name"),
                "latency_s": detail.get("latency"),
                "observations": [
                    {
                        "name": o.get("name"),
                        "type": o.get("type"),
                        "latency_ms": o.get("latency"),
                    }
                    for o in (detail.get("observations") or [])[:5]
                ],
            },
            indent=2,
        )
        render_text_png("langfuse-trace-waterfall.png", "Langfuse Trace Waterfall", waterfall_text)

    render_text_png("log-correlation-id.png", "Correlation ID in JSON Logs", log_snippets.get("correlation_id", ""))
    render_text_png("log-pii-redaction.png", "PII Redaction in JSON Logs", log_snippets.get("pii_redaction", ""))
    alert_text = (ROOT / "config" / "alert_rules.yaml").read_text(encoding="utf-8")
    render_text_png("alert-rules.png", "Alert Rules (config/alert_rules.yaml)", alert_text)
    if traces:
        trace_list = "\n".join(
            f"- {t.get('id')} | {t.get('name')} | {t.get('latency')}s" for t in traces[:15]
        )
        render_text_png(
            "langfuse-traces.png",
            f"Langfuse Traces ({len(traces)} total, showing 15)",
            trace_list,
        )

    audit_sample = pick_audit_lines()
    if audit_sample:
        (EVIDENCE / "audit-log-sample.jsonl").write_text(audit_sample + "\n", encoding="utf-8")
        render_text_png("audit-log.png", "Audit Log (data/audit.jsonl)", audit_sample)

    subprocess.run([sys.executable, str(ROOT / "scripts" / "cost_benchmark.py")], cwd=ROOT, check=False)
    cost_path = EVIDENCE / "cost-optimization.json"
    if cost_path.exists():
        cost_text = cost_path.read_text(encoding="utf-8")
        render_text_png("cost-optimization.png", "Cost Optimization Before/After", cost_text)

    try:
        with httpx.Client(timeout=60.0) as client:
            incident = run_incident_demo(client)
        (EVIDENCE / "incident-rag_slow.json").write_text(json.dumps(incident, indent=2), encoding="utf-8")
        render_text_png(
            "incident-rag_slow.png",
            "Incident Demo: rag_slow",
            json.dumps(
                {
                    "normal_latency_ms": incident.get("normal_latency_ms"),
                    "slow_latency_ms": incident.get("slow_latency_ms"),
                    "normal_correlation_id": incident.get("normal_correlation_id"),
                    "slow_correlation_id": incident.get("slow_correlation_id"),
                },
                indent=2,
            ),
        )
    except Exception as exc:
        (EVIDENCE / "incident-rag_slow.json").write_text(json.dumps({"error": str(exc)}, indent=2), encoding="utf-8")

    dashboard_ok = screenshot_dashboard()
    print(f"Evidence written to {EVIDENCE}")
    print(f"Traces in Langfuse: {len(traces)}")
    print(f"Dashboard screenshot: {'OK' if dashboard_ok else 'skipped (install playwright + run server)'}")
    print(f"Validate logs score: see {EVIDENCE / 'validate_logs.txt'}")


if __name__ == "__main__":
    main()
