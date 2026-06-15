# Live Demo Script (20 pts)

Use this 8-minute flow during presentation.

## 0. Setup (before class)
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
python scripts/collect_evidence.py   # refresh evidence
```

## 1. Health & tracing (1 min)
- Open http://127.0.0.1:8000/health
- Say: **tracing_enabled=true** confirms Langfuse keys loaded via `.env`

## 2. Logging pipeline (2 min)
- Show `data/logs.jsonl` or `docs/evidence/log-correlation-id.png`
- Explain middleware flow:
  1. `clear_contextvars()` prevents leakage
  2. Read/generate `x-request-id` as `req-<hex>`
  3. `bind_contextvars(correlation_id=...)`
  4. Response headers echo ID + latency
- Show PII redaction: email/phone/credit card → `[REDACTED_*]`

## 3. Traces (2 min)
- Open Langfuse → Traces (90+ traces)
- Open one `run` trace waterfall
- Explain tags: `lab`, feature, model; metadata: `doc_count`, `query_preview`

## 4. Dashboard & SLO (2 min)
- Open http://127.0.0.1:8000/dashboard
- Point out 6 panels + SLO threshold lines (P95 < 3000ms, error < 2%, quality > 0.75, cost < $2.5/day)
- Show `config/slo.yaml` alignment

## 5. Incident response (2 min)
- Run:
  ```bash
  python scripts/inject_incident.py --scenario rag_slow
  python scripts/load_test.py
  ```
- Show latency spike on dashboard
- Debug path: **Metrics (P95 up) → Traces (slow span) → Logs (correlation_id + latency_ms) → /health (rag_slow=true)**
- Fix: `python scripts/inject_incident.py --scenario rag_slow --disable`

## 6. Alerts, audit, cost (1 min)
- Show `config/alert_rules.yaml` + runbook link `docs/alerts.md#1-high-latency-p95`
- Show `data/audit.jsonl` — separate from app logs, no raw PII
- Show `docs/evidence/cost-optimization.json` — summary requests routed to Haiku (~60% savings)

## Oral Q&A prep
See `docs/mock-debug-qa.md`.
