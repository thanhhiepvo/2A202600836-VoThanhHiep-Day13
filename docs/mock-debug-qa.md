# Mock Debug Q&A — Oral Exam Prep

## Middleware & correlation ID
**Q: Why clear contextvars at the start of each request?**  
A: Structlog binds context per async task. Without clearing, a previous request's `correlation_id` or user fields could leak into the next request's logs.

**Q: What format is the correlation ID?**  
A: Client may send `x-request-id`; otherwise we generate `req-` + 8 hex chars from UUID4.

**Q: How does correlation_id reach logs?**  
A: Middleware calls `bind_contextvars(correlation_id=...)`. The logging pipeline uses `merge_contextvars` processor so every log line includes it automatically.

## PII scrubbing
**Q: Where is PII scrubbed?**  
A: Two layers: (1) `summarize_text()` before logging previews, (2) `scrub_event` processor in structlog pipeline for all payload strings.

**Q: Example regex for email?**  
A: `[\w\.-]+@[\w\.-]+\.\w+` → replaced with `[REDACTED_EMAIL]`.

**Q: Why audit log separately?**  
A: Audit log (`data/audit.jsonl`) records who did what (hashed user, session, cost) without raw message content — compliance-friendly trail distinct from debug logs.

## Metrics & SLO
**Q: How is P95 calculated?**  
A: In `app/metrics.py`, latencies are sorted; index = round((p/100)*n + 0.5) - 1, clamped to array bounds.

**Q: What are our SLOs?**  
A: P95 latency < 3000ms, error rate < 2%, daily cost < $2.5, quality avg > 0.75 (see `config/slo.yaml`).

## Tracing
**Q: Why did traces not appear initially?**  
A: Langfuse v3 uses `from langfuse import observe`, not `langfuse.decorators`. Also need `load_dotenv()` so keys load from `.env`.

**Q: What metadata do we attach?**  
A: Trace: `user_id` (hashed), `session_id`, tags `[lab, feature, model]`. Span: `doc_count`, `query_preview`, token usage.

## Incident debugging
**Q: rag_slow root cause?**  
A: `mock_rag.py` sleeps 2.5s when `STATE["rag_slow"]` is true. Visible in higher latency_ms in logs, higher P95 in metrics, longer trace span.

**Q: Debug flow?**  
A: Alert/metric symptom → drill into slow traces → find correlation_id → grep logs.jsonl for that ID → check `/health` incident toggles.

## Cost optimization
**Q: What optimization did you implement?**  
A: Route `summary` feature to `claude-haiku-4-5` (cheaper rates + shorter outputs) while `qa` stays on Sonnet. Evidence in `docs/evidence/cost-optimization.json`.
