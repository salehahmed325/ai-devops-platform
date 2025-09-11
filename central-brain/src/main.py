import os
import logging
import base64
import hashlib
from decimal import Decimal
from typing import Any, Dict, List
from dataclasses import dataclass
import json

import boto3
import httpx


# Import types for boto3 for better static analysis
from mypy_boto3_dynamodb.service_resource import (
    DynamoDBServiceResource,
    Table,
)


# --- Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
API_KEY = os.getenv("API_KEY", "dev-test-key-123")

DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "ai-devops-platform-data")
DYNAMODB_LOGS_TABLE_NAME = os.getenv(
    "DYNAMODB_LOGS_TABLE_NAME", "ai-devops-platform-logs"
)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
)

# --- Logging Setup ---
# AWS Lambda automatically configures a logger, so we can just get it
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.info(f"Lambda API Key: {API_KEY}")

# --- DynamoDB Setup ---
dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
table: Table = dynamodb.Table(DYNAMODB_TABLE_NAME)
logs_table: Table = dynamodb.Table(DYNAMODB_LOGS_TABLE_NAME)
alert_configs_table: Table = dynamodb.Table(
    os.getenv(
        "DYNAMODB_ALERT_CONFIGS_TABLE_NAME", "ai-devops-platform-alert-configs"
    )
)


# --- Data Models ---
@dataclass
class Metric:
    metric: Dict[str, str]
    value: List[Any]


# --- Helper Functions ---
def convert_floats_to_decimals(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(elem) for elem in obj]
    return obj


# --- Main Lambda Handler ---
def handler(event, context):
    try:
        # --- Security Check ---
        headers = event.get("headers", {})
        logger.info(f"Received headers: {headers}")
        api_key_received = headers.get("x-api-key")
        logger.info(f"API Key received from headers: {api_key_received}")
        if api_key_received != API_KEY:
            logger.warning("Invalid or missing API Key.")
            return {"statusCode": 403, "body": "Forbidden: Invalid API Key"}

        # --- Request Body Processing ---
        body = event.get("body", "")
        
        if not body:
            logger.warning("Request body is empty.")
            return {"statusCode": 400, "body": "Bad Request: Empty body"}

        try:
            parsed_json_body = json.loads(body)
            logger.info(f"Received JSON body: {parsed_json_body}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON body: {e}")
            return {"statusCode": 400, "body": "Bad Request: Invalid JSON body"}

        # --- Data Transformation and Storage ---
        metrics_for_anomaly_detection: List[Metric] = []
        cluster_id = "unknown_cluster"

        with table.batch_writer() as batch:
            for ts_data in parsed_json_body.get("timeseries", []):
                labels = ts_data.get("labels", {})
                metric_name = labels.get("__name__", "")

                if "cluster_id" in labels:
                    cluster_id = labels["cluster_id"]

                for sample_data in ts_data.get("samples", []):
                    timestamp_sec = sample_data.get("timestamp_ms", 0) / 1000.0
                    metric_value = sample_data.get("value", 0.0)

                    metric_obj = Metric(
                        metric=labels, value=[timestamp_sec, metric_value]
                    )
                    metrics_for_anomaly_detection.append(metric_obj)
                    logger.info(f"Created metric_obj: {metric_obj}")
                    

                    labels_str = "-".join(
                        sorted([f"{k}={v}" for k, v in labels.items()])
                    )
                    labels_hash = hashlib.sha256(labels_str.encode()).hexdigest()
                    metric_identifier = (
                        f"{timestamp_sec}-{metric_name}-{labels_hash}"
                    )

                    item = {
                        "cluster_id": labels.get(
                            "cluster_id", "unknown_cluster"
                        ),
                        "metric_identifier": metric_identifier,
                        "timestamp": Decimal(str(timestamp_sec)),
                        "metric_name": metric_name,
                        "metric_labels": convert_floats_to_decimals(labels),
                        "metric_value": convert_floats_to_decimals(
                            [timestamp_sec, metric_value]
                        ),
                        "instance": labels.get("instance", "unknown"),
                        "job": labels.get("job", "unknown"),
                    }
                    logger.info(f"Putting item into batch: {item}")
                    batch.put_item(Item=item)

        logger.info(
            (
                f"Successfully processed and stored "
                f"{len(parsed_json_body.get('timeseries', []))} metric samples for cluster: {cluster_id}."
            )
        )

        return {"statusCode": 200, "body": "Success"}

    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}

# Small change to trigger CI/CD pipeline.