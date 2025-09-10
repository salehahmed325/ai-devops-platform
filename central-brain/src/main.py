from __future__ import annotations

import os
import logging
import base64
import hashlib
from decimal import Decimal
from typing import Any, Dict, List
from dataclasses import dataclass

import boto3
import httpx
import numpy as np
import snappy
from sklearn.ensemble import IsolationForest

# Import the generated protobuf file
from prompb import remote_pb2


# --- Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
API_KEY = os.getenv("API_KEY", "dev-test-key-123")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "ai-devops-platform-data")
DYNAMODB_LOGS_TABLE_NAME = os.getenv(
    "DYNAMODB_LOGS_TABLE_NAME", "ai-devops-platform-logs"
)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# --- Logging Setup ---
# AWS Lambda automatically configures a logger, so we can just get it
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# --- DynamoDB Setup ---
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
logs_table = dynamodb.Table(DYNAMODB_LOGS_TABLE_NAME)
alert_configs_table = dynamodb.Table(
    os.getenv("DYNAMODB_ALERT_CONFIGS_TABLE_NAME", "ai-devops-platform-alert-configs")
)


# --- Data Models ---
# Replaced Pydantic's BaseModel with a lighter dataclass for the Lambda environment
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


# --- Telegram Alerting ---
class AlertManager:
    def __init__(self, alert_configs_table):
        self.alert_configs_table = alert_configs_table

    async def send_telegram_alert(self, chat_id: str, message: str):
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN is not set. Cannot send Telegram alert.")
            return

        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(TELEGRAM_API_URL, json=payload)
                response.raise_for_status()
                logger.info(f"Telegram alert sent to chat ID {chat_id}.")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while sending Telegram alert: {e}"
            )


# --- Anomaly Detection (Preserved from original file) ---
# NOTE: These functions are synchronous and will run within the async handler.
# For very high-performance needs, they could be run in a separate thread pool.
def detect_up_anomalies(metrics: List[Metric]) -> List[str]:
    anomalies = []
    try:
        up_metrics = [m for m in metrics if m.metric.get("__name__") == "up"]
        if len(up_metrics) < 2:
            return []

        up_values = [float(m.value[1]) for m in up_metrics]
        X = np.array(up_values).reshape(-1, 1)
        preds = IsolationForest(contamination="auto", random_state=42).fit_predict(X)

        for i, pred in enumerate(preds):
            if pred == -1:
                metric = up_metrics[i]
                job = metric.metric.get("job", "unknown_job")
                instance = metric.metric.get("instance", "unknown_instance")
                anomalies.append(
                    f"Anomaly detected for 'up' metric: job='{job}', "
                    f"instance='{instance}' is down (value={up_values[i]})."
                )
    except Exception as e:
        logger.error(f"Anomaly detection for 'up' metric failed: {e}")
    return anomalies


async def detect_anomalies(metrics: List[Metric], cluster_id: str) -> List[str]:
    # For now, we only have the 'up' anomaly detection.
    # The CPU anomaly detection logic was complex and required historical data fetching,
    # which needs to be re-evaluated in a serverless context for performance.
    # This is a placeholder for future, more sophisticated anomaly detection.
    all_anomalies = detect_up_anomalies(metrics)
    return all_anomalies


# --- Main Lambda Handler ---
async def handler(event, context):
    """
    AWS Lambda handler for ingesting Prometheus remote_write requests.
    """
    try:
        # --- Security Check ---
        headers = event.get("headers", {})
        api_key_received = headers.get("x-api-key")
        if api_key_received != API_KEY:
            logger.warning("Invalid or missing API Key.")
            return {"statusCode": 403, "body": "Forbidden: Invalid API Key"}

        # --- Request Body Processing ---
        body = event.get("body", "")
        if event.get("isBase64Encoded", False):
            body = base64.b64decode(body)

        if not body:
            logger.warning("Request body is empty.")
            return {"statusCode": 400, "body": "Bad Request: Empty body"}

        # Decompress and parse the protobuf message
        uncompressed_data = snappy.uncompress(body)
        write_request = remote_pb2.WriteRequest()
        write_request.ParseFromString(uncompressed_data)

        # --- Data Transformation and Storage ---
        metrics_for_anomaly_detection: List[Metric] = []
        cluster_id = "unknown_cluster"  # Default value

        with table.batch_writer() as batch:
            for ts in write_request.timeseries:
                labels = {label.name: label.value for label in ts.labels}
                metric_name = labels.get("__name__", "")

                # Extract cluster_id from labels, a common pattern
                if "cluster_id" in labels:
                    cluster_id = labels["cluster_id"]

                for sample in ts.samples:
                    # Convert timestamp from ms to seconds (float) for consistency
                    timestamp_sec = sample.timestamp_ms / 1000.0

                    # 1. Prepare metric for anomaly detection
                    # The old format was [timestamp, value]
                    metric_obj = Metric(
                        metric=labels, value=[timestamp_sec, sample.value]
                    )
                    metrics_for_anomaly_detection.append(metric_obj)

                    # 2. Prepare item for DynamoDB
                    # Create a unique identifier for the metric sample
                    labels_str = "-".join(
                        sorted([f"{k}={v}" for k, v in labels.items()])
                    )
                    labels_hash = hashlib.sha256(labels_str.encode()).hexdigest()
                    metric_identifier = f"{timestamp_sec}-{metric_name}-{labels_hash}"

                    item = {
                        "cluster_id": labels.get("cluster_id", "unknown_cluster"),
                        "metric_identifier": metric_identifier,
                        "timestamp": Decimal(str(timestamp_sec)),
                        "metric_name": metric_name,
                        "metric_labels": convert_floats_to_decimals(labels),
                        "metric_value": convert_floats_to_decimals(
                            [timestamp_sec, sample.value]
                        ),
                        "instance": labels.get("instance", "unknown"),
                        "job": labels.get("job", "unknown"),
                    }
                    batch.put_item(Item=item)

        logger.info(
            f"Successfully processed and stored {len(metrics_for_anomaly_detection)} metric samples for cluster: {cluster_id}."
        )

        # --- Anomaly Detection and Alerting ---
        anomalies = await detect_anomalies(metrics_for_anomaly_detection, cluster_id)
        if anomalies:
            alert_manager = AlertManager(alert_configs_table)
            try:
                # This logic for getting chat_id should be adapted if needed
                response = alert_configs_table.get_item(Key={"cluster_id": cluster_id})
                config_item = response.get("Item")
                if config_item and "telegram_chat_id" in config_item:
                    chat_id = config_item["telegram_chat_id"]
                    for anomaly in anomalies:
                        alert_message = f"🚨 Anomaly Alert for Cluster `{cluster_id}` 🚨\n\n{anomaly}"
                        await alert_manager.send_telegram_alert(chat_id, alert_message)
                else:
                    logger.warning(
                        f"No Telegram chat ID for cluster {cluster_id}. Logging alerts."
                    )
                    for anomaly in anomalies:
                        logger.warning(f"ALERT: {anomaly}")
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")

        return {"statusCode": 200, "body": "Success"}

    except snappy.UncompressError:
        logger.error("Invalid snappy compressed data received.")
        return {"statusCode": 400, "body": "Bad Request: Invalid snappy compression"}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}
