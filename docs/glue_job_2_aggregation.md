# Glue Job 2 - Aggregation (Analytics Layer)

Glue Job 2 is responsible for producing the **final, authoritative analytics datasets**
from normalized log records. This job represents the **business metrics boundary** of Atlas.

Unlike Glue Job 1, which focuses on record correctness, Glue Job 2 focuses on
**metric correctness**.

---

## Inputs

- Processed (silver) logs produced by Glue Job 1
- Data is already:
  - schema-normalized
  - partitioned by log type and date
  - analytics-friendly

Glue Job 2 only reads data for the explicit `process_date`.

---

## Responsibilities

Glue Job 2:
- aggregates normalized logs by day
- computes daily activity metrics
- writes analytics datasets in Parquet format
- overwrites existing analytics partitions for the date

It does **not**:
- parse raw formats
- filter invalid records
- infer processing dates

---

## Aggregation Strategy

Aggregations are **day-scoped**.

Typical metrics include:
- total requests
- error counts
- requests per application
- status code distributions

The exact metrics are less important than the **overwrite semantics**.

---

## Overwrite-by-Day Semantics

For each `process_date`, Glue Job 2:
- deletes any existing analytics data for that date
- writes a fresh, complete result

This ensures:
- corrected data is reflected immediately
- duplicates upstream do not inflate metrics
- reruns are deterministic

This design is critical for production analytics correctness.

---

## Output

Output is written to the analytics (gold) layer:
- partitioned by year/month/day
- optimized for Athena queries
- considered the single source of truth

---

## Summary

Glue Job 2 converts normalized data into trustworthy analytics.
If dashboards are wrong, this is the first job to inspect.
