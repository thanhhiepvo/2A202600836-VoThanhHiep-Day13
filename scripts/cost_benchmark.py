#!/usr/bin/env python3
"""Compare LLM cost before/after feature-based model routing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.audit import estimate_cost  # noqa: E402
from app.agent import LabAgent  # noqa: E402

BASE_URL = "http://127.0.0.1:8000"
SUMMARY_PAYLOADS = [
    {"user_id": "u01", "session_id": "s01", "feature": "summary", "message": "Summarize the monitoring policy for production logging"},
    {"user_id": "u06", "session_id": "s06", "feature": "summary", "message": "Give me a short summary of the observability workflow"},
    {"user_id": "u03", "session_id": "s03", "feature": "summary", "message": "Summarize refund and policy handling"},
]


def run_summary_requests() -> list[dict]:
    results = []
    with httpx.Client(timeout=30.0) as client:
        for payload in SUMMARY_PAYLOADS:
            r = client.post(f"{BASE_URL}/chat", json=payload)
            r.raise_for_status()
            body = r.json()
            results.append(body)
    return results


def benchmark_offline() -> dict:
    agent = LabAgent()
    rows = []
    for payload in SUMMARY_PAYLOADS:
        result = agent.run(
            user_id=payload["user_id"],
            feature=payload["feature"],
            session_id=payload["session_id"],
            message=payload["message"],
        )
        sonnet_cost = estimate_cost(LabAgent.DEFAULT_MODEL, result.tokens_in, result.tokens_out)
        rows.append(
            {
                "feature": payload["feature"],
                "tokens_in": result.tokens_in,
                "tokens_out": result.tokens_out,
                "before_usd": sonnet_cost,
                "after_usd": result.cost_usd,
                "model_after": result.model,
            }
        )
    before_total = round(sum(r["before_usd"] for r in rows), 6)
    after_total = round(sum(r["after_usd"] for r in rows), 6)
    savings_pct = round((1 - after_total / before_total) * 100, 1) if before_total else 0.0
    return {
        "optimization": "Route summary feature to claude-haiku-4-5 instead of claude-sonnet-4-5",
        "requests_tested": len(rows),
        "before_total_usd": before_total,
        "after_total_usd": after_total,
        "savings_usd": round(before_total - after_total, 6),
        "savings_pct": savings_pct,
        "rows": rows,
    }


def main() -> None:
    out_dir = ROOT / "docs" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        live = run_summary_requests()
        live_total = round(sum(r["cost_usd"] for r in live), 6)
    except Exception as exc:
        live = {"error": str(exc)}
        live_total = None

    offline = benchmark_offline()
    report = {"live_summary_cost_usd": live_total, **offline}
    out = out_dir / "cost-optimization.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
