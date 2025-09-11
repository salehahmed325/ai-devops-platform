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
import snappy

# Import the generated protobuf file
from prompb import remote_pb2

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


# --- Telegram Alerting ---
class AlertManager:
    def __init__(self, alert_configs_table: Table):
        self.alert_configs_table = alert_configs_table

    async def send_telegram_alert(self, chat_id: str, message: str):
        if not TELEGRAM_BOT_TOKEN:
            logger.warning(
                (
                    "TELEGRAM_BOT_TOKEN is not set. "
                    "Cannot send Telegram alert."
                )
            )
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
        if event.get("isBase64Encoded", False):
            body = base64.b64decode(body)

        if not body:
            logger.warning("Request body is empty.")
            return {"statusCode": 400, "body": "Bad Request: Empty body"}

        uncompressed_data = snappy.uncompress(body)
        write_request = remote_pb2.WriteRequest()
        write_request.ParseFromString(uncompressed_data)  # type: ignore

        # --- Data Transformation and Storage ---
        metrics_for_anomaly_detection: List[Metric] = []
        cluster_id = "unknown_cluster"

        with table.batch_writer() as batch:
            for ts in write_request.timeseries:  # type: ignore
                labels = {label.name: label.value for label in ts.labels}
                metric_name = labels.get("__name__", "")

                if "cluster_id" in labels:
                    cluster_id = labels["cluster_id"]

                for sample in ts.samples:
                    timestamp_sec = sample.timestamp_ms / 1000.0
                    metric_obj = Metric(
                        metric=labels, value=[timestamp_sec, sample.value]
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
                            [timestamp_sec, sample.value]
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
        # Anomaly detection is temporarily disabled due to Lambda size limits.
        # anomalies = await detect_anomalies(
        #     metrics_for_anomaly_detection, cluster_id
        # )
        # if anomalies:
        #     alert_manager = AlertManager(alert_configs_table)
        #     try:
        #         response = alert_configs_table.get_item(
        #             Key={"cluster_id": cluster_id}
        #         )
        #         config_item = response.get("Item")
        #         if config_item and "telegram_chat_id" in config_item:
        #             chat_id = str(config_item["telegram_chat_id"])
        #             for anomaly in anomalies:
        #                 alert_message = (
        #                     f"🚨 Anomaly Alert for Cluster `{cluster_id}` 🚨\n\n{anomaly}"
        #                 )
        #                 await alert_manager.send_telegram_alert(
        #                     chat_id, alert_message
        #                 )
        #         else:
        #             logger.warning(
        #                 (
        #                     f"No Telegram chat ID for cluster {cluster_id}. "
        #                     f"Logging alerts."
        #                 )
        #             )
        #             for anomaly in anomalies:
        #                 logger.warning(f"ALERT: {anomaly}")
        #     except Exception as e:
        #         logger.error(f"Failed to send Telegram alert: {e}")

        return {"statusCode": 200, "body": "Success"}

    except snappy.UncompressError:
        logger.error("Invalid snappy compressed data received.")
        return {
            "statusCode": 400,
            "body": "Bad Request: Invalid snappy compression",
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}

# Small change to trigger CI/CD pipeline.