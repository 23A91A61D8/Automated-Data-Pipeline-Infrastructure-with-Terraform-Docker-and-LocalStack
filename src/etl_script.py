"""
Automated Data Pipeline - Python ETL Application
Extracts raw data from S3, transforms with Pandas, and loads processed data back to S3.
Configured for LocalStack AWS emulation and production AWS parity.
"""

import io
import logging
import os
import sys
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import pandas as pd

# Load local .env if present
load_dotenv()

# ==============================================================================
# Logging Configuration
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ETL-Pipeline")


# ==============================================================================
# Configuration Loader
# ==============================================================================
def get_config():
    """
    Retrieves and validates pipeline configuration from environment variables.
    Ensures environment-agnostic execution across LocalStack, Docker, CI/CD, and AWS.
    """
    config = {
        "endpoint_url": os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566"),
        "bucket_name": os.environ.get("S3_BUCKET_NAME", "my-pipeline-bucket"),
        "raw_key": os.environ.get("RAW_DATA_KEY", "raw/input.csv"),
        "processed_key": os.environ.get("PROCESSED_DATA_KEY", "processed/output.csv"),
        "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        "aws_region": os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1")),
    }

    logger.info("=== Pipeline Configuration Loaded ===")
    logger.info(f"  Target S3 Bucket    : {config['bucket_name']}")
    logger.info(f"  Raw S3 Key Path     : {config['raw_key']}")
    logger.info(f"  Processed S3 Key    : {config['processed_key']}")
    logger.info(f"  AWS Endpoint URL    : {config['endpoint_url']}")
    logger.info(f"  AWS Region          : {config['aws_region']}")

    return config


# ==============================================================================
# Boto3 S3 Client Builder
# ==============================================================================
def get_s3_client(config):
    """
    Creates and returns a configured Boto3 S3 client.
    Supports both custom LocalStack endpoints and standard AWS endpoints.
    """
    endpoint_url = config.get("endpoint_url")
    if endpoint_url and endpoint_url.lower() in ("none", "", "aws"):
        endpoint_url = None

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=config["aws_access_key_id"],
        aws_secret_access_key=config["aws_secret_access_key"],
        region_name=config["aws_region"],
    )


# ==============================================================================
# Extract Step
# ==============================================================================
def extract_data(s3_client, bucket_name: str, raw_key: str) -> pd.DataFrame:
    """
    Extracts raw CSV dataset from the specified S3 bucket and key.
    Reads file contents directly into memory for robust LocalStack parsing.
    """
    logger.info(f"Step 1: Extracting raw data from s3://{bucket_name}/{raw_key}...")
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=raw_key)
        raw_bytes = response["Body"].read()
        df = pd.read_csv(io.BytesIO(raw_bytes))
        logger.info(f"Successfully extracted {len(df)} rows and {len(df.columns)} columns.")
        logger.debug(f"Raw DataFrame columns: {list(df.columns)}")
        return df
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"Failed to fetch object from S3: {error_code} - {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while extracting raw data: {e}")
        raise


# ==============================================================================
# Transform Step
# ==============================================================================
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies programmatic business transformations and data enrichment using Pandas:
      - Validates and sanitizes column names
      - Drops duplicate records and filters null/invalid rows
      - Computes derived metrics (e.g. adjusted values, total amounts, percentage increases)
      - Attaches transformation metadata (processing timestamps, status flags)
    """
    logger.info("Step 2: Applying transformations to raw dataset...")
    df_transformed = df.copy()

    # Normalize column names (strip whitespace and lowercase)
    df_transformed.columns = [col.strip().lower() for col in df_transformed.columns]
    logger.info(f"Normalized schema columns: {list(df_transformed.columns)}")

    # Record initial count
    initial_row_count = len(df_transformed)

    # 1. Clean data: Remove exact duplicate rows
    df_transformed = df_transformed.drop_duplicates()

    # 2. Dynamic transformation based on available columns:
    # Scenario A: Standard CI/CD benchmark schema (id, value)
    if "value" in df_transformed.columns:
        # Ensure numeric type
        df_transformed["value"] = pd.to_numeric(df_transformed["value"], errors="coerce")
        # Filter out NaN/invalid values and negative numbers
        df_transformed = df_transformed.dropna(subset=["value"])
        df_transformed = df_transformed[df_transformed["value"] >= 0]

        # Computed columns:
        # e.g. Tax/Surcharge calculation (10%), Total Value, and Category
        df_transformed["surcharge_amount"] = (df_transformed["value"] * 0.10).round(2)
        df_transformed["total_amount"] = (df_transformed["value"] + df_transformed["surcharge_amount"]).round(2)
        df_transformed["tier"] = df_transformed["value"].apply(
            lambda v: "HIGH" if v >= 500 else ("MEDIUM" if v >= 150 else "STANDARD")
        )

    # Scenario B: NYC Taxi / Trip Records (trip_distance, fare_amount, etc.)
    elif "trip_distance" in df_transformed.columns or "fare_amount" in df_transformed.columns:
        if "fare_amount" in df_transformed.columns:
            df_transformed["fare_amount"] = pd.to_numeric(df_transformed["fare_amount"], errors="coerce")
            df_transformed = df_transformed[df_transformed["fare_amount"] > 0]
            df_transformed["tip_estimated"] = (df_transformed["fare_amount"] * 0.15).round(2)
            df_transformed["total_amount"] = (df_transformed["fare_amount"] + df_transformed["tip_estimated"]).round(2)

    # Scenario C: Generic tabular fallback
    else:
        # Add index-based row identifier if missing
        if "id" not in df_transformed.columns:
            df_transformed.insert(0, "id", range(1, len(df_transformed) + 1))
        df_transformed["record_length"] = df_transformed.astype(str).sum(axis=1).str.len()

    # 3. Add global auditing metadata columns
    df_transformed["pipeline_status"] = "PROCESSED"
    df_transformed["processed_at_utc"] = datetime.utcnow().isoformat()

    final_row_count = len(df_transformed)
    logger.info(f"Transformation complete. Retained {final_row_count}/{initial_row_count} records.")
    logger.info(f"Sample transformed record:\n{df_transformed.head(2).to_dict(orient='records')}")

    return df_transformed


# ==============================================================================
# Load Step
# ==============================================================================
def load_data(s3_client, df: pd.DataFrame, bucket_name: str, processed_key: str) -> None:
    """
    Serializes transformed DataFrame to CSV in memory and uploads to destination S3 key.
    """
    logger.info(f"Step 3: Loading processed data into s3://{bucket_name}/{processed_key}...")
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue().encode("utf-8")

        s3_client.put_object(
            Bucket=bucket_name,
            Key=processed_key,
            Body=csv_data,
            ContentType="text/csv",
        )
        logger.info(
            f"Successfully uploaded processed CSV ({len(csv_data)} bytes) to "
            f"s3://{bucket_name}/{processed_key}"
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"Failed to upload processed object to S3: {error_code} - {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during load step: {e}")
        raise


# ==============================================================================
# Main Orchestration Loop
# ==============================================================================
def run_pipeline() -> None:
    """
    Main execution pipeline entry point.
    Coordinates Extract -> Transform -> Load stages with complete telemetry.
    """
    start_time = datetime.utcnow()
    logger.info("==================================================")
    logger.info("Starting Automated Data Pipeline ETL Execution")
    logger.info("==================================================")

    config = get_config()
    s3_client = get_s3_client(config)

    try:
        # Extract
        raw_df = extract_data(s3_client, config["bucket_name"], config["raw_key"])

        # Transform
        processed_df = transform_data(raw_df)

        # Load
        load_data(s3_client, processed_df, config["bucket_name"], config["processed_key"])

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info("==================================================")
        logger.info(f"ETL Pipeline execution completed successfully in {elapsed:.2f}s!")
        logger.info("==================================================")

    except Exception as e:
        logger.critical(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
