# Duplicates, Rejects & Corrections

Atlas assumes data is imperfect.

---

## Duplicates

Duplicates may occur due to:
- repeated file uploads
- retries
- ingestion failures

They are tolerated in processed data.

---

## Corrections

When corrected data arrives:
- reprocess the affected date
- analytics layer overwrites previous results

This ensures business metrics remain correct.

---

## Summary

Correctness is enforced at the analytics layer, not ingestion.
