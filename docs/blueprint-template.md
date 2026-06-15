# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: C04-Day13 Team
- [REPO_URL]: https://github.com/thanhhiepvo/C04-Day13.git
- [MEMBERS]:
  - Member A: Thanh Hiep Vo | Role: Logging & PII
  - Member B: Thanh Hiep Vo | Role: Tracing & Enrichment
  - Member C: Thanh Hiep Vo | Role: SLO & Alerts
  - Member D: Thanh Hiep Vo | Role: Load Test & Dashboard
  - Member E: Thanh Hiep Vo | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 90+ (see docs/evidence/langfuse-summary.json)
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: docs/evidence/log-correlation-id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: docs/evidence/log-pii-redaction.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: docs/evidence/langfuse-trace-waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: The `run` generation span wraps RAG retrieval + LLM generation. Metadata includes `doc_count`, `query_preview`, and routed `model`. With `rag_slow` enabled, span latency increases ~2.5s from `time.sleep` in `mock_rag.py`.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: docs/evidence/dashboard-6-panels.png
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | ~155 ms (normal) / ~2660 ms (rag_slow) |
| Error Rate | < 2% | 28d | 0% |
| Cost Budget | < $2.5/day | 1d | < $0.05 (lab traffic) |
| Quality Avg | > 0.75 | 28d | ~0.88 |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: docs/evidence/alert-rules.png
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: Dashboard P95 and per-request latency spiked (~155ms → ~2660ms). Langfuse traces showed longer `run` span. Metrics error rate stayed 0%.
- [ROOT_CAUSE_PROVED_BY]: docs/evidence/incident-rag_slow.json — `/health` showed `rag_slow: true`; slow request correlation_id traceable in logs; `mock_rag.py` line 17-18 adds 2.5s sleep.
- [FIX_ACTION]: `python scripts/inject_incident.py --scenario rag_slow --disable`
- [PREVENTIVE_MEASURE]: Alert `high_latency_p95` (config/alert_rules.yaml) + runbook step 1: check incident toggles before deep debugging.

**Debug flow demonstrated:** Metrics (P95↑) → Traces (slow span) → Logs (correlation_id + latency_ms) → Health (incident flag)

---

## 5. Individual Contributions & Evidence

### Thanh Hiep Vo — Logging & PII (Member A)
- [TASKS_COMPLETED]:
  - Implemented `CorrelationIdMiddleware`: clear contextvars, generate/propagate `req-*` IDs, response headers
  - Enriched logs with `user_id_hash`, `session_id`, `feature`, `model`, `env` via `bind_contextvars`
  - PII patterns: email, phone_vn, cccd, credit_card, passport, address_vn
  - Registered `scrub_event` processor in structlog pipeline
  - Separate audit log to `data/audit.jsonl` (no raw user messages)
- [EVIDENCE_LINK]: `app/middleware.py`, `app/main.py`, `app/pii.py`, `app/logging_config.py`, `app/audit.py`, commit `feat: logging pipeline with correlation IDs, PII scrubbing, and audit logs`

**Oral depth:** Can explain regex PII patterns and why `clear_contextvars()` prevents cross-request leakage.

### Thanh Hiep Vo — Tracing & Enrichment (Member B)
- [TASKS_COMPLETED]:
  - Fixed Langfuse v3 SDK (`from langfuse import observe, get_client`)
  - Added `load_dotenv()` for automatic `.env` loading
  - Trace metadata: hashed user_id, session_id, tags, doc_count, token usage
  - Shutdown hook flushes pending traces
- [EVIDENCE_LINK]: `app/tracing.py`, `docs/evidence/langfuse-traces.png`, commit `feat: Langfuse v3 tracing integration`

**Oral depth:** Can walk through trace waterfall and explain span vs trace in Langfuse v3.

### Thanh Hiep Vo — SLO & Alerts (Member C)
- [TASKS_COMPLETED]:
  - Defined SLIs in `config/slo.yaml` (latency, error rate, cost, quality)
  - 3 alert rules with severity, condition, owner, runbook links
  - Runbooks in `docs/alerts.md` with mitigation steps
- [EVIDENCE_LINK]: `config/slo.yaml`, `config/alert_rules.yaml`, `docs/alerts.md`, `docs/evidence/alert-rules.png`

**Oral depth:** Can explain symptom-based vs cause-based alerts and when to use P1 vs P2.

### Thanh Hiep Vo — Load Test & Dashboard (Member D)
- [TASKS_COMPLETED]:
  - Load test script with `--concurrency` flag
  - In-memory metrics with P50/P95/P99 percentiles
  - Live 6-panel dashboard at `/dashboard` with SLO threshold lines and 30s refresh
  - Evidence export via `scripts/collect_evidence.py`
- [EVIDENCE_LINK]: `scripts/load_test.py`, `app/metrics.py`, `docs/dashboard.html`, `docs/evidence/dashboard-6-panels.png`

**Oral depth:** Can explain P95 calculation in `percentile()` and why tail latency matters for SLOs.

### Thanh Hiep Vo — Demo & Report (Member E)
- [TASKS_COMPLETED]:
  - Completed blueprint report with auto-verified scores
  - Demo script (`docs/demo-script.md`) and oral Q&A prep (`docs/mock-debug-qa.md`)
  - Incident demo automation in evidence collector
  - Cost optimization benchmark and documentation
- [EVIDENCE_LINK]: `docs/blueprint-template.md`, `docs/demo-script.md`, `scripts/collect_evidence.py`, `scripts/cost_benchmark.py`

**Oral depth:** Can deliver full 8-minute demo following metrics → traces → logs flow.

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: Route `summary` feature to `claude-haiku-4-5` instead of Sonnet — **73.3% cost reduction** on summary requests ($0.003249 → $0.000867). Evidence: `docs/evidence/cost-optimization.json` and `docs/evidence/cost-optimization.png`
- [BONUS_AUDIT_LOGS]: Separate audit trail at `data/audit.jsonl` for chat_request/chat_response/incident events without raw PII. Evidence: `docs/evidence/audit-log.png`
- [BONUS_CUSTOM_METRIC]: Automated grading evidence pipeline: `python scripts/collect_evidence.py` exports logs, traces, dashboard, incident, and cost evidence

---

## 7. Git Evidence Summary
| Commit | Scope |
|---|---|
| feat: logging pipeline | middleware, PII, audit, logging_config |
| feat: Langfuse v3 tracing | tracing.py, agent metadata |
| feat: dashboard and metrics | dashboard.html, metrics, main routes |
| feat: cost optimization | agent model routing, cost_benchmark |
| feat: evidence automation | collect_evidence, cost_benchmark scripts |
| docs: blueprint and demo | blueprint, demo-script, mock-debug-qa |

Run `git log --oneline` to verify commit history before submission.
