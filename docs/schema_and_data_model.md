# Schema & Data Model

Atlas enforces a canonical schema to unify heterogeneous log sources.

---

## Canonical Fields

Core fields include:
- event_timestamp
- ip_address
- device
- request_type
- status_code
- app_name
- log_type
- raw_format

Partition fields:
- year
- month
- day

---

## Why a Canonical Schema

A shared schema:
- simplifies aggregation
- standardizes analytics
- isolates format-specific logic upstream

All downstream processing assumes this schema.

---

## Summary

The schema is the contract between normalization and analytics.
