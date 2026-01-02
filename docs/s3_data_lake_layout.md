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

## Data Flow Within S3 Data Lake

```mermaid
flowchart TB
    subgraph RAW["raw/  (Landing Zone)"]
        R1[Raw Log Files<br/>(NDJSON / JSON.GZ / XML)]
    end

    subgraph VALIDATED["validated/  (File-Level Correctness)"]
        V1[validated/&lt;format&gt;/<br/>year=YYYY/month=MM/day=DD/]
    end

    subgraph PROCESSED["processed/  (Silver Layer)"]
        P1[processed/logs/<br/>log_type=access|error/<br/>year/month/day<br/>(Parquet)]
    end

    subgraph ANALYTICS["analytics/  (Gold Layer)"]
        A1[analytics/daily_activity/<br/>date=YYYY-MM-DD/]
    end

    subgraph REJECTED["rejected/"]
        RS[rejected/system/<br/>• ingestion failures<br/>• glue failures]
        RD[rejected/data_quality/<br/>• invalid rows<br/>• schema issues]
    end

    subgraph ARCHIVE["archive/"]
        AR[archive/validated/<br/>original_file_ts_runid]
    end

    R1 -->|file-level routing| V1
    R1 -->|ingestion failure| RS

    V1 -->|record-level parsing| P1
    V1 -->|job failure| RS

    P1 -->|daily aggregation| A1
    P1 -->|row-level rejects| RD

    V1 -->|optional retention| AR

    ```
Data moves through S3 in four maturity stages: raw files land untouched, validated files are partitioned by event date, processed data is normalized into Parquet, and analytics data is aggregated and overwrite-by-day. Rejects and archives provide transparency and auditability.
