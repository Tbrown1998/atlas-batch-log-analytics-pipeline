## Architectural Overview

At a high level, Atlas follows a layered data lake architecture:

```mermaid
flowchart LR
    Raw[Raw Logs (S3)]
    Lambda[Ingestion Lambda]
    Validated[Validated Zone (S3)]
    Glue1[Glue Job 1 - Normalization]
    Processed[Processed Zone (S3)]
    Glue2[Glue Job 2 - Aggregation]
    Analytics[Analytics Zone (S3)]
    Catalota [Catalog]

    Raw -->|S3 Event| Lambda
    Lambda --> Validated
    Validated -->|process_date| Glue1
    Glue1 --> Processed
    Processed -->|process_date| Glue2
    Glue2 --> Analytics
    Processed --> Catalog
    Analytics --> Catalog
```

Each arrow represents a clear contract between components, not an implicit dependency.

---

## Core Architectural Principles

### 1. Separation of Concerns

Each service in Atlas has a single, well-defined responsibility:

| Component | Responsibility |
|---------|---------------|
| S3 | Durable storage |
| Lambda | File-level ingestion & routing |
| Glue Job 1 | Record-level normalization |
| Glue Job 2 | Business-level aggregation |
| Step Functions | Execution ordering & state |
| EventBridge | Time & scheduling |
| Glue Crawlers | Metadata discovery |
| Athena | Query & validation |

No component violates its boundary.

Examples:
- Lambda never parses records
- Glue never decides which date to process
- Crawlers never transform data

This separation keeps the system understandable and debuggable.

---

### 2. Batch-First Design (Intentional)

Atlas is explicitly **not** a streaming architecture.

This is intentional because:
- Logs may arrive late
- Logs may be corrected
- Business metrics must be reproducible
- Backfills must be safe

Batch processing allows:
- deterministic reprocessing
- overwrite semantics for analytics
- simpler operational recovery

Streaming ingestion can be layered on later if required, but correctness is prioritized.

---

### 3. Time Is Externalized from Processing

A critical architectural decision is that processing jobs do not infer time.

Glue jobs:
- do not look at latest partitions
- do not compute today or yesterday
- do not scan unbounded data

Instead:
- `process_date` is injected by orchestration
- all reads and writes are scoped to that date

This prevents:
- accidental double counting
- hidden time-based bugs
- non-reproducible results

---

## Component-by-Component Breakdown

### S3 (Storage Layer)

![alt text](<../images/S3 Buckets.png>)

S3 acts as the system of record for all data stages.

```
s3://atlas-log-analytics-pipeline/
│
├── raw/                         
│   ├── ndjson/
│   ├── json_gzip/
│   └── xml_errors/
│
├── validated/                   
│   ├── ndjson/
│   │   └── year=YYYY/month=MM/day=DD/
│   ├── json_gzip/
│   │   └── year=YYYY/month=MM/day=DD/
│   └── xml_errors/
│       └── year=YYYY/month=MM/day=DD/
│
├── processed/                   
│   └── logs/
│       └── log_type=access|error/
│           └── year=YYYY/month=MM/day=DD/
│               └── part-*.parquet
│
├── analytics/                   
│   └── daily_activity/
│       └── date=YYYY-MM-DD/
│           └── part-*.parquet
│
├── rejected/                    
│   ├── system/
│   │   ├── lambda/
│   │   └── glue/
│   └── data_quality/
│       └── year=YYYY/month=MM/day=DD/
│           └── part-*.parquet
│
└── archive/                     
    └── validated/
        └── ndjson|json_gzip|xml_errors/
            └── <original_filename>_<ingest_ts>_<run_id>
```

Key properties:
- Immutable storage
- Cheap at scale
- Naturally partitionable

---

### raw/ — Landing Zone
- Entry point for all external log producers
- Files are immutable
- No schema or partition guarantees
- Cleared once files are successfully ingested

---

### validated/ — File-Level Correctness
- Routed by Lambda
- Partitioned by event date (not upload date)
- Guaranteed correct format and placement
- Ready for batch processing

---

### processed/ — Silver Layer
- Output of Glue Job 1
- Canonical schema
- Parquet format
- Optimized for aggregation
- Duplicates may exist by design

---

### analytics/ — Gold Layer
- Output of Glue Job 2
- Aggregated overwrite-by-day datasets
- Authoritative source for reporting & dashboards

---

### rejected/ — Failure Transparency
- system/: infrastructure or job-level failures
- data_quality/: row-level validation failures
- Nothing is silently dropped

---

### archive/ — Lineage & Audit
- Preserves original filename
- Ingestion timestamp
- Pipeline run identifier
- Useful for audits and debugging

---

## Lambda (Ingestion Layer)

![alt text](<../images/Lambda layer.png>)

Lambda sits at the boundary between external systems and the data lake.

Responsibilities:
- Respond to S3 upload events
- Inspect file metadata and content
- Extract event timestamps
- Route files into date-based partitions

Lambda operates strictly at the file level.

Lambda does not:
- parse records
- deduplicate data
- enforce schemas

---

## Glue Job 1 — Normalization Layer

![alt text](<../images/Glue job1.png>)

Glue Job 1 is the schema normalization boundary.

It:
- reads validated files
- parses heterogeneous formats
- extracts consistent metadata
- enforces a canonical schema
- writes partitioned Parquet

Properties:
- rerunnable
- idempotent per day
- observable

---

## Glue Job 2 — Aggregation Layer

![alt text](<../images/Glue Job 2.png>)

Glue Job 2 produces authoritative analytics datasets.

It:
- reads processed data
- aggregates by day and dimensions
- overwrites analytics partitions deterministically

This ensures corrections are reflected and metrics remain accurate.

---

## Glue Crawlers & Data Catalog

![alt text](<../images/processed layer crawler.png>)

![alt text](<../images/Daily activity logs.png>)

Crawlers:
- discover new partitions
- infer schemas
- update Glue tables

They are:
- decoupled from Glue jobs
- orchestrated explicitly

Avoiding race conditions and partial metadata updates.

---

## Step Functions (Orchestration Layer)

![alt text](<../images/step function.png>)

Step Functions:
- coordinate Glue jobs and crawlers
- preserve `process_date`
- enforce execution order

They do not schedule runs or transform data.

---

## EventBridge (Scheduling Layer)

![alt text](<../images/Event bridge.png>)

EventBridge:
- triggers daily execution
- injects `process_date`
- supports cron scheduling
- allows manual backfills

Separates **when** something runs from **what** it does.

---

## Deterministic Reprocessing Example

- Initial run processes 50 records
- Corrected file adds 70 records
- Day is reprocessed
- Analytics layer overwrites the partition
- Final analytics count is 70, not 120

This behavior is intentional.

---

## Why This Architecture Works

### Strengths
- Deterministic outputs
- Safe reprocessing
- Clear ownership
- Easy debugging
- Scales with data volume

### Tradeoffs
- Not real-time
- Slightly higher latency
- Requires orchestration discipline

These tradeoffs are deliberate.

---

## Summary

Atlas reflects real production constraints:
- data is messy
- time is tricky
- correctness matters more than speed

By enforcing clear boundaries and deterministic behavior, the system remains reliable,
understandable, and extensible.