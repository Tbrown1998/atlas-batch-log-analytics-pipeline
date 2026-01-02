# Glue Crawlers & Data Catalog

Glue Crawlers are used to keep the Glue Data Catalog in sync with the data lake.

They provide the metadata layer that enables Athena querying and schema discovery.

---

## Why Crawlers Are Needed

S3 itself has no schema awareness.
Without crawlers:
- partitions are invisible to query engines
- schema changes are not reflected
- analytics access becomes fragile

Crawlers solve this by scanning S3 and updating table metadata.

---

## Crawler Placement in the Pipeline

Atlas uses two crawlers:
- **Processed crawler** (after Glue Job 1)
- **Analytics crawler** (after Glue Job 2)

They are orchestrated explicitly via Step Functions.

---

## Responsibilities

Crawlers:
- discover new partitions
- infer column schemas
- update Glue tables

They do **not**:
- transform data
- validate business logic
- correct errors

---

## Schema Evolution

If new fields appear:
- crawlers detect them
- tables evolve naturally
- downstream queries can adapt

This allows Atlas to handle changing log formats over time.

---

## Summary

Crawlers bridge the gap between storage and analytics.
They are essential for discoverability, not computation.
