import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import *

# ========== Job setup ===========
args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "process_date",
        "database",
        "table",
        "analytics_base"
    ]
)

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

process_date = args["process_date"]
database = args["database"]
table = args["table"]
ANALYTICS_BASE = args["analytics_base"]

year, month, day = [int(x) for x in process_date.split("-")]

# ========== Read processed path data for ONE DAY ONLY ===========
df_day = (
    spark.table(f"{database}.{table}")
    .filter(
        (F.col("year") == year) &
        (F.col("month") == month) &
        (F.col("day") == day)
    )
)

# ========== Split access vs error ===========
df_access = df_day.filter(F.col("log_type") == "access")
df_error = df_day.filter(F.col("log_type") == "error")

# ========== Core metrics ===========
total_requests = df_access.count()
total_errors = df_error.count()

unique_ips = (
    df_day
    .select("ip_address")
    .where(F.col("ip_address").isNotNull())
    .distinct()
    .count()
)

# ========== Requests by device (MAP) ===========
requests_by_device = (
    df_access
    .groupBy("device")
    .count()
    .where(F.col("device").isNotNull())
    .agg(
        F.map_from_entries(
            F.collect_list(
                F.struct(F.col("device"), F.col("count"))
            )
        )
    )
    .first()[0]
)

# ========== Requests by request_type (MAP) ===========
requests_by_type = (
    df_day
    .groupBy("request_type")
    .count()
    .where(F.col("request_type").isNotNull())
    .agg(
        F.map_from_entries(
            F.collect_list(
                F.struct(F.col("request_type"), F.col("count"))
            )
        )
    )
    .first()[0]
)

# ========== Final aggregated dataframe (ONE ROW per day) ===========
df_agg = spark.createDataFrame(
    [
        (
            process_date,
            total_requests,
            total_errors,
            unique_ips,
            requests_by_device,
            requests_by_type,
            year,
            month,
            day
        )
    ],
    schema="""
        activity_date STRING,
        total_requests BIGINT,
        total_errors BIGINT,
        unique_ips BIGINT,
        requests_by_device MAP<STRING, BIGINT>,
        requests_by_type MAP<STRING, BIGINT>,
        year INT,
        month INT,
        day INT
    """
)

# ========== Write analytics (OVERWRITE BY DAY) ===========
(
    df_agg
    .write
    .mode("overwrite")
    .partitionBy("year", "month", "day")
    .parquet(ANALYTICS_BASE)
)

job.commit()
