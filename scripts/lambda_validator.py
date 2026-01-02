import json
import gzip
import boto3
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import unquote_plus

s3 = boto3.client("s3")

VALIDATED_BASE = "validated"
REJECTED_BASE = "rejected"

# ========== Helpers ===========
def parse_iso_date(ts: str):
    dt = datetime.fromisoformat(ts.replace("Z", ""))
    return dt.year, dt.month, dt.day

def extract_date_ndjson(text):
    for line in text.splitlines():
        if line.strip():
            obj = json.loads(line)
            ts = obj.get("timestamp")
            if ts:
                return parse_iso_date(ts)
    raise ValueError("No timestamp found in NDJSON")

def extract_date_json(text):
    records = json.loads(text)
    for obj in records:
        ts = obj.get("timestamp")
        if ts:
            return parse_iso_date(ts)
    raise ValueError("No timestamp found in JSON")

def extract_date_xml(text):
    root = ET.fromstring(text)
    for error in root.findall(".//error"):
        ts = error.findtext("errorTime")
        if ts:
            return parse_iso_date(ts)
    raise ValueError("No errorTime found in XML")

def move_object(bucket, src_key, dest_key):
    s3.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": src_key},
        Key=dest_key
    )
    s3.delete_object(Bucket=bucket, Key=src_key)

# ========== LAMBDA ENTRY POINT (DO NOT RENAME) ===========
def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        if not key.startswith("raw/"):
            continue

        filename = key.split("/")[-1]

        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            raw_bytes = obj["Body"].read()

            if key.endswith(".ndjson"):
                text = raw_bytes.decode("utf-8")
                year, month, day = extract_date_ndjson(text)
                fmt = "ndjson"

            elif key.endswith(".json.gz"):
                text = gzip.decompress(raw_bytes).decode("utf-8")
                year, month, day = extract_date_json(text)
                fmt = "json_gzip"

            elif key.endswith(".xml"):
                text = raw_bytes.decode("utf-8")
                year, month, day = extract_date_xml(text)
                fmt = "xml_errors"

            else:
                raise ValueError("Unsupported file type")

            dest_key = (
                f"{VALIDATED_BASE}/{fmt}/"
                f"year={year}/month={month:02d}/day={day:02d}/"
                f"{filename}"
            )

            move_object(bucket, key, dest_key)
            print(f"SUCCESS: {key} → {dest_key}")

        except Exception as e:
            print(f"FAILED: {key} | {e}")
            rejected_key = f"{REJECTED_BASE}/{filename}"
            move_object(bucket, key, rejected_key)
