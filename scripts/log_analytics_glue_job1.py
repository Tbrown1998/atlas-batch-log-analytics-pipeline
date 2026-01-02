import sys
import json
import boto3
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.sql.functions import regexp_extract, col, trim, split, explode, lit

# ========== Job setup ===========
args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "process_date",
        "validated_base",
        "processed_base",
        "sns_topic_arn"
    ]
)

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

process_date = args["process_date"]
VALIDATED_BASE = args["validated_base"]
PROCESSED_BASE = args["processed_base"]
SNS_TOPIC_ARN = args["sns_topic_arn"]

year, month, day = process_date.split("-")

sns_client = boto3.client("sns")

# ========== Canonical column order ===========
canonical_cols = [
    "log_id",
    "event_timestamp",
    "ip_address",
    "device",
    "request_type",
    "status_code",
    "app_name",
    "log_type",
    "raw_format",
    "year",
    "month",
    "day"
]

# ========== NDJSON logs ===========
df_ndjson = (
    spark.read.json(
        f"{VALIDATED_BASE}/ndjson/year={year}/month={month}/day={day}/"
    )
    .withColumn("log_id", F.expr("uuid()"))
    .withColumn("event_timestamp", F.to_timestamp("timestamp"))
    .withColumnRenamed("ip", "ip_address")
    .withColumnRenamed("user_agent", "device")
    .withColumn("status_code", F.col("status").cast("int"))
    .withColumn("app_name", F.lit("web_app_1"))
    .withColumn("log_type", F.lit("access"))
    .withColumn("raw_format", F.lit("ndjson"))
)

# ========== GZIP JSON logs ===========
df_gzip = (
    spark.read.json(
        f"{VALIDATED_BASE}/json_gzip/year={year}/month={month}/day={day}/"
    )
    .withColumn("log_id", F.expr("uuid()"))
    .withColumn("event_timestamp", F.to_timestamp("timestamp"))
    .withColumnRenamed("ip", "ip_address")
    .withColumnRenamed("user_agent", "device")
    .withColumn("status_code", F.col("status").cast("int"))
    .withColumn("app_name", F.lit("api_service"))
    .withColumn("log_type", F.lit("access"))
    .withColumn("raw_format", F.lit("json_gzip"))
)

# ========== XML error logs ===========
df_xml_text = spark.read.text(
    f"{VALIDATED_BASE}/xml_errors/year={year}/month={month}/day={day}/",
    wholetext=True
)

total_error_tags = (
    df_xml_text
    .withColumn("error_count", F.size(F.split(col("value"), "<error>")) - 1)
    .agg(F.sum("error_count").alias("total"))
    .collect()[0]["total"]
)

df_xml_split = (
    df_xml_text
    .withColumn(
        "error_records",
        F.split(col("value"), r'(?=<error>)|(?<=</error>)')
    )
    .withColumn("error_record", explode(col("error_records")))
    .filter(col("error_record").contains("<errorTime>"))
)

df_xml_extracted = (
    df_xml_split
    .withColumn("log_id", F.expr("uuid()"))
    .withColumn(
        "event_timestamp",
        F.to_timestamp(
            regexp_extract(col("error_record"), r'<errorTime>(.*?)</errorTime>', 1),
            "yyyy-MM-dd'T'HH:mm:ss'Z'"
        )
    )
    .withColumn(
        "ip_address",
        trim(regexp_extract(col("error_record"), r'<clientIp>(.*?)</clientIp>', 1))
    )
    .withColumn("device", F.lit(None).cast(StringType()))
    .withColumn("request_type", F.lit("ERROR"))
    .withColumn(
        "status_code",
        regexp_extract(col("error_record"), r'<errorCode>(.*?)</errorCode>', 1).cast("int")
    )
    .withColumn(
        "app_name",
        trim(regexp_extract(col("error_record"), r'<service>(.*?)</service>', 1))
    )
    .withColumn("log_type", F.lit("error"))
    .withColumn("raw_format", F.lit("xml"))
)

df_xml = (
    df_xml_extracted
    .filter(
        col("event_timestamp").isNotNull() &
        col("ip_address").isNotNull() &
        col("status_code").isNotNull()
    )
    .select(
        "log_id",
        "event_timestamp",
        "ip_address",
        "device",
        "request_type",
        "status_code",
        "app_name",
        "log_type",
        "raw_format"
    )
)

records_after_filtering = df_xml.count()

# ========== Union & partitioning ===========
df_all = (
    df_ndjson
    .unionByName(df_gzip, allowMissingColumns=True)
    .unionByName(df_xml, allowMissingColumns=True)
)

df_final = (
    df_all
    .withColumn("year", F.lit(int(year)))
    .withColumn("month", F.lit(int(month)))
    .withColumn("day", F.lit(int(day)))
    .select(*canonical_cols)
)

# ========== PROCESSED counts ===========
access_count = df_final.filter(F.col("log_type") == "access").count()
error_count = df_final.filter(F.col("log_type") == "error").count()
total_count = access_count + error_count

# ========== RAW (VALIDATED) counts ===========
ndjson_raw_count = df_ndjson.count()
gzip_raw_count = df_gzip.count()
xml_raw_count = total_error_tags
total_raw_count = ndjson_raw_count + gzip_raw_count + xml_raw_count

# ========== Write output ===========
(
    df_final
    .write
    .mode("append")
    .partitionBy("log_type", "year", "month", "day")
    .parquet(PROCESSED_BASE)
)

# ========== SNS summary ===========
sns_message = f"""
Glue Job: log_parse_normalize_job
Process Date: {process_date}
Status: SUCCESS

================ VALIDATED INPUT COUNTS ================
NDJSON records: {ndjson_raw_count}
GZIP JSON records: {gzip_raw_count}
XML <error> tags: {xml_raw_count}
TOTAL VALIDATED RECORDS: {total_raw_count}

================ PROCESSED OUTPUT COUNTS ================
Access logs written: {access_count}
Error logs written: {error_count}
TOTAL PROCESSED RECORDS: {total_count}

================ XML QUALITY METRICS ================
XML records after filtering: {records_after_filtering}
XML records dropped: {xml_raw_count - records_after_filtering}
XML success rate: {(records_after_filtering / xml_raw_count * 100):.2f}%

Output location:
{PROCESSED_BASE}
""".strip()

sns_client.publish(
    TopicArn=SNS_TOPIC_ARN,
    Subject="Glue Log Pipeline – Daily Summary",
    Message=sns_message
)

job.commit()
