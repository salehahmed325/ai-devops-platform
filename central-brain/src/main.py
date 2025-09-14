import os
import logging
import base64
import hashlib
from decimal import Decimal
from typing import Any, Dict, List
from dataclasses import dataclass
import json
import statistics

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
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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

@dataclass
class Anomaly:
    metric_name: str
    instance: str
    job: str
    value: float
    timestamp: float
    reason: str


# --- Helper Functions ---
def convert_floats_to_decimals(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(elem) for elem in obj]
    return obj

def detect_anomalies(
    metrics: List[Metric], threshold: float = 3.5
) -> List[Anomaly]:
    anomalies: List[Anomaly] = []
    
    # Group metrics by their name
    metrics_by_name: Dict[str, List[Metric]] = {}
    for m in metrics:
        metric_name = m.metric.get("__name__", "unknown")
        if metric_name not in metrics_by_name:
            metrics_by_name[metric_name] = []
        metrics_by_name[metric_name].append(m)

    # Calculate anomalies for each group using Median Absolute Deviation (MAD)
    for metric_name, metric_group in metrics_by_name.items():
        values = [m.value[1] for m in metric_group]
        
        if len(values) < 3: # Need at least 3 points for a meaningful MAD
            continue

        median = statistics.median(values)
        deviations = [abs(v - median) for v in values]
        mad = statistics.median(deviations)
        
        # If MAD is 0, all points are the same, so no anomalies
        if mad == 0:
            continue

        for m in metric_group:
            val = m.value[1]
            # This is the Modified Z-score calculation
            modified_z_score = 0.6745 * (val - median) / mad
            
            if abs(modified_z_score) > threshold:
                anomaly = Anomaly(
                    metric_name=metric_name,
                    instance=m.metric.get("instance", "unknown"),
                    job=m.metric.get("job", "unknown"),
                    value=val,
                    timestamp=m.value[0],
                    reason=f"Value {val:.2f} has a Modified Z-score of {modified_z_score:.2f}, which is above the threshold of {threshold}",
                )
                anomalies.append(anomaly)
                logger.warning(f"Anomaly Detected: {anomaly}")

    return anomalies

def send_telegram_alert(anomalies: List[Anomaly]):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot token or chat ID is not configured. Skipping alert.")
        return

    message = "🚨 *Anomaly Alert* 🚨\n\n"
    for anomaly in anomalies:
        message += (
            f"Metric: `{anomaly.metric_name}`\n"
            f"Instance: `{anomaly.instance}`\n"
            f"Value: `{anomaly.value:.2f}`\n"
            f"Reason: _{anomaly.reason}_\n\n"
        )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(TELEGRAM_API_URL, json=payload)
            response.raise_for_status()
            logger.info("Successfully sent Telegram alert.")
    except httpx.RequestError as e:
        logger.error(f"Error sending Telegram alert: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram alert: {e}")


# --- Main Lambda Handler ---
def handler(event, context):
    try:
        # --- Security Check ---
        headers = event.get("headers", {})
        api_key_received = headers.get("x-api-key")
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
                    batch.put_item(Item=item)

        logger.info(
            (
                f"Successfully processed and stored "
                f"{len(metrics_for_anomaly_detection)} metric samples for cluster: {cluster_id}."
            )
        )

        # --- Anomaly Detection and Alerting ---
        if metrics_for_anomaly_detection:
            anomalies = detect_anomalies(metrics_for_anomaly_detection)
            if anomalies:
                send_telegram_alert(anomalies)

        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}