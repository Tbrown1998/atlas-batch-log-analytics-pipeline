# 🔐 IAM Roles & Access Model (Summary)

Atlas uses separate, least-privilege IAM roles for each service.  
No role is shared across services, and each role is scoped strictly to the actions  
required for its responsibility in the pipeline.

---

## IAM Role Overview

| IAM Role | Used By | Purpose |
|--------|--------|--------|
| atlas-lambda-ingestion-role | Lambda | File ingestion, validation, and routing |
| atlas-glue-etl-role | Glue Jobs | Log parsing, normalization, and aggregation |
| atlas-step-functions-role | Step Functions | Orchestration of Glue jobs and crawlers |
| atlas-eventbridge-role | EventBridge | Triggering scheduled pipeline executions |
| atlas-glue-crawler-role | Glue Crawlers | Metadata discovery and schema updates |

---

## Role Responsibilities & Permissions

### 1. Lambda Ingestion Role  
**Role:** `atlas-lambda-ingestion-role`  
**Used by:** Ingestion Lambda  

**Allows:**
- `s3:GetObject` on `raw/`
- `s3:PutObject` on `validated/`
- `s3:DeleteObject` on `raw/`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Purpose:**
- Read newly uploaded files  
- Route files into validated date partitions  
- Remove files from raw after successful ingestion  
- Emit operational logs  

---

### 2. Glue ETL Role  
**Role:** `atlas-glue-etl-role`  
**Used by:**  
- Glue Job 1 (Normalization – Silver)  
- Glue Job 2 (Aggregation – Gold)  

**Allows:**
- `s3:GetObject` on `validated/` and `processed/`
- `s3:PutObject` on `processed/` and `analytics/`
- `s3:PutObject` on `rejected/` (data quality & system failures)
- `sns:Publish` (job summaries & alerts)
- `logs:*` for Glue job logging
- `glue:GetTable`, `glue:GetDatabase`

**Purpose:**
- Parse and normalize logs  
- Write partitioned Parquet outputs  
- Aggregate analytics datasets  
- Publish processing summaries  

---

### 3. Step Functions Execution Role  
**Role:** `atlas-step-functions-role`  
**Used by:** AWS Step Functions  

**Allows:**
- `glue:StartJobRun`
- `glue:GetJobRun`
- `glue:StartCrawler`
- `glue:GetCrawler`
- `logs:*`

**Purpose:**
- Orchestrate Glue jobs and crawlers  
- Enforce execution order  
- Preserve `process_date` across steps  

---

### 4. EventBridge Invocation Role  
**Role:** `atlas-eventbridge-role`  
**Used by:** Amazon EventBridge  

**Allows:**
- `states:StartExecution` on the Step Function state machine  

**Purpose:**
- Trigger daily pipeline execution  
- Inject `process_date` for scheduled runs  

---

### 5. Glue Crawler Role  
**Role:** `atlas-glue-crawler-role`  
**Used by:** Glue Crawlers  

**Allows:**
- `s3:GetObject` on `processed/` and `analytics/`
- `glue:CreateTable`
- `glue:UpdateTable`
- `glue:GetDatabase`
- `logs:*`

**Purpose:**
- Discover new partitions  
- Update schemas in the Glue Data Catalog  
- Enable Athena querying  

---

## Security Principles Applied

- Least privilege: no wildcard permissions on critical actions  
- Role isolation: no service shares a role  
- No human access to ETL roles  
- Explicit stage boundaries in S3 access  

---

## Why This Matters

This IAM model:
- Prevents accidental cross-stage writes  
- Limits blast radius of failures  
- Makes audits and debugging straightforward  
- Reflects real production security practices
