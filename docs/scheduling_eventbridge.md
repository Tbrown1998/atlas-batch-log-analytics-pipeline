# EventBridge Scheduling

![alt text](<../images/Event bridge.png>)

EventBridge controls **when** Atlas runs and **which date** is processed.

---

## Daily Scheduling

A scheduled EventBridge rule:
- runs once per day (midnight UTC)
- injects `process_date = yesterday`
- starts a new Step Functions execution

This enables fully automated daily processing.

---

## Manual Runs & Backfills

Manual executions can override scheduling by supplying:

```json
{ "process_date": "YYYY-MM-DD" }
```

This allows:
- historical backfills
- reprocessing corrected data
- targeted reruns

---

## Why EventBridge Owns Time

Keeping time logic in EventBridge:
- centralizes scheduling
- avoids duplicated logic
- keeps Glue jobs deterministic

Processing jobs never compute dates themselves.

---

# Process Date & Time Handling

Time handling is one of the most critical aspects of This pipeline.

## Explicit Date Contract

Every batch run operates on a single explicit date:

```text
process_date = YYYY-MM-DD
```

All reads and writes are scoped to this date.

---

## Why This Matters

This design enables:
- reproducible results
- safe reprocessing
- predictable analytics

Without explicit dates, pipelines become fragile and error-prone.

---

## Common Scenarios

- **Late data**: re-run the affected date  
- **Corrected data**: overwrite analytics for that date  
- **Multiple runs per day**: results remain deterministic  
