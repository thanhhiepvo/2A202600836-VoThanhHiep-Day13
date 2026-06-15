# Evidence Collection Sheet

Re-generate all grading artifacts:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload          # terminal 1
python scripts/collect_evidence.py       # terminal 2
```

## Required screenshots (`docs/evidence/`)

| Requirement | File |
|---|---|
| Langfuse traces (90+) | `langfuse-traces.png` |
| Trace waterfall | `langfuse-trace-waterfall.png` |
| Correlation ID in logs | `log-correlation-id.png` |
| PII redaction | `log-pii-redaction.png` |
| Dashboard 6 panels | `dashboard-6-panels.png` |
| Alert rules + runbook | `alert-rules.png` |
| Audit log (bonus) | `audit-log.png` |
| Cost optimization (bonus) | `cost-optimization.png` |
| Incident demo | `incident-rag_slow.png` |

## Live demo
- Script: `docs/demo-script.md`
- Oral Q&A: `docs/mock-debug-qa.md`
- Dashboard: http://127.0.0.1:8000/dashboard
- Langfuse: https://cloud.langfuse.com

## Validation
- `docs/evidence/validate_logs.txt` → target 100/100
- `docs/evidence/langfuse-summary.json` → traces ≥ 10
- `docs/evidence/metrics.json` → current snapshot
