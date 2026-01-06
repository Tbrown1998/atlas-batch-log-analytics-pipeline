# Glue Job 1 - Normalization

Glue Job 1 is responsible for transforming validated log files into a
canonical, analytics-friendly dataset.

This job represents the **schema boundary** of the pipeline.

---

## Inputs

- Validated NDJSON access logs
- Validated GZIP JSON access logs
- Validated XML error logs

All inputs are partitioned by event date.

---

## Responsibilities

Glue Job 1:
- parses heterogeneous formats
- extracts shared metadata fields
- normalizes records into a single schema
- filters invalid records
- writes partitioned Parquet output

---

## Canonical Schema

The canonical schema includes:
- event timestamp
- IP address
- device or user agent
- request type
- status code
- application name
- log type
- partition columns (year, month, day)

This schema is designed for downstream aggregation and querying.

---

## Handling Data Quality

Invalid records are filtered out.
Counts before and after filtering are:
- computed during execution
- included in SNS summary notifications

This makes data loss explicit rather than hidden.

---

## Output

Output is written to the processed (silver) layer:
- partitioned by log type and date
- in Parquet format

Duplicates may exist at this stage by design.

---

## Summary

Glue Job 1 converts raw logs into structured data.
It does not produce business metrics, it prepares data for them.

