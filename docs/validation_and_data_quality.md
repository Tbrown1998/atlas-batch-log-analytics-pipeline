# Validation & Data Quality

Validation in Atlas focuses on **detecting issues**, not silently correcting them.

---

## Validation Techniques

- Row count comparisons
- Partition completeness checks
- Schema inspection via Athena

Glue Job 1 emits SNS summaries showing:
- records read
- records written
- records dropped

---

## Philosophy

Atlas prefers:
- explicit visibility
- deterministic behavior
- human-in-the-loop decisions

Rather than automatic fixes that hide problems.

---

## Summary

Data quality is surfaced early and clearly.
