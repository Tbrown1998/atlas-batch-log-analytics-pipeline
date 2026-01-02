# Querying with Amazon Athena

![alt text](<../images/athena queries.png>)

Athena is the primary query engine for Atlas.  
It provides serverless, SQL-based access to both processed (silver) and
analytics (gold) datasets stored in S3 and registered in the Glue Data Catalog.

Atlas is designed so that:

- Processed tables are used for debugging and validation
- Analytics tables are used for reporting and dashboards

---

## Athena Databases & Tables

| Database | Table | Layer | Purpose |
|--------|------|------|---------|
| log_analytics_db | logs | Processed (Silver) | Normalized log records |
| log_analytics_db | daily_activity | Analytics (Gold) | Aggregated daily metrics |

---

## When to Query Which Table

### Query `logs` (Processed) when:
- Debugging ingestion issues
- Validating raw vs processed counts
- Investigating specific IPs, errors, or requests

### Query `daily_activity` (Analytics) when:
- Building dashboards
- Reporting KPIs
- Answering business questions

---

## Sample Athena Queries

### 1️⃣ Validate Processed Data for a Day

Check how many records were processed for a specific date.

```sql
SELECT
    log_type,
    COUNT(*) AS record_count
FROM log_analytics_db.logs
WHERE year = 2024
  AND month = 11
  AND day = 29
GROUP BY log_type;
```

**Use case:**  
Confirm Glue Job 1 output matches SNS summary counts.

---

### 2️⃣ Inspect Raw Error Logs (Silver Layer)

Find error logs and their status codes.

```sql
SELECT
    event_timestamp,
    ip_address,
    app_name,
    status_code
FROM log_analytics_db.logs
WHERE log_type = 'error'
  AND year = 2024
  AND month = 11
  AND day = 29
ORDER BY event_timestamp DESC
LIMIT 50;
```

**Use case:**  
Debug error spikes or validate XML parsing.

---

### 3️⃣ Requests per Application (Silver)

Quick exploratory analysis before aggregation.

```sql
SELECT
    app_name,
    COUNT(*) AS total_requests
FROM log_analytics_db.logs
WHERE log_type = 'access'
  AND year = 2024
  AND month = 11
  AND day = 29
GROUP BY app_name
ORDER BY total_requests DESC;
```

---

### 4️⃣ Daily Activity Metrics (Gold)

Query the authoritative analytics dataset.

```sql
SELECT
    date,
    total_requests,
    error_count
FROM log_analytics_db.daily_activity
WHERE date = DATE '2024-11-29';
```

**Use case:**  
Power dashboards or scheduled reports.

---

### 5️⃣ Trend Analysis (Gold Layer)

Analyze request volume over time.

```sql
SELECT
    date,
    total_requests
FROM log_analytics_db.daily_activity
ORDER BY date;
```

---

### 6️⃣ Error Rate Calculation (Gold)

Compute daily error rates.

```sql
SELECT
    date,
    error_count,
    total_requests,
    CAST(error_count AS DOUBLE) / total_requests AS error_rate
FROM log_analytics_db.daily_activity
ORDER BY date;
```

---

## Partition Pruning (Performance Tip)

Atlas tables are partitioned by date.  
Always include partition filters to reduce scan cost:

```sql
WHERE year = 2024 AND month = 11 AND day = 29
```

or

```sql
WHERE date = DATE '2024-11-29'
```

This is critical for performance and cost efficiency.

---

## Why Athena Fits Atlas Well

- Serverless (no cluster management)
- Tight integration with Glue Catalog
- Pay-per-query pricing
- Ideal for batch analytics and validation

Athena complements Atlas’s batch-first, deterministic design philosophy.

---

## Summary

Athena provides the analytical surface for Atlas:

- **Silver tables** → operational debugging & validation  
- **Gold tables** → business analytics & reporting  

All analytics consumers should treat the gold layer as the single source of truth.
