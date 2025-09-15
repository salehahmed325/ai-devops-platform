import os
import logging
import base64
import hashlib
from decimal import Decimal
from typing import Any, Dict, List
from dataclasses import dataclass
import json
import statistics
import uuid
import re
from datetime import datetime

import boto3
import httpx

import gzip

# OTLP Protobuf imports
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
    ExportLogsServiceRequest,
)

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
        # Set a longer timeout to handle potential Lambda cold starts
        with httpx.Client(timeout=15.0) as client:
            response = client.post(TELEGRAM_API_URL, json=payload)
            response.raise_for_status()
            logger.info("Successfully sent Telegram alert.")
    except httpx.RequestError as e:
        logger.error(f"Error sending Telegram alert: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram alert: {e}")


# --- Main Lambda Handler ---
def handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """
    Main AWS Lambda handler for processing OTLP metrics and logs.
    """
    logger.debug(f"Received event: {json.dumps(event)}")

    # API Key Authentication
    api_key_header = event.get("headers", {}).get("x-api-key")
    if not api_key_header or api_key_header != API_KEY:
        logger.warning("Unauthorized access: Invalid or missing API Key.")
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Forbidden: Invalid API Key"}),
            "headers": {"Content-Type": "application/json"},
        }

    # Route based on path
    path = event.get("rawPath", "")
    body = event.get("body", "")
    is_base64_encoded = event.get("isBase64Encoded", False)

    if not body:
        logger.warning("Received empty request body.")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Bad Request: Empty body"}),
            "headers": {"Content-Type": "application/json"},
        }

    try:
        # Decode body if it's base64 encoded
        if is_base64_encoded:
            body_bytes = base64.b64decode(body)
        else:
            body_bytes = body.encode("utf-8")

        # Decompress if gzipped
        if event.get("headers", {}).get("content-encoding") == "gzip":
            body_bytes = gzip.decompress(body_bytes)

        if "/v1/metrics" in path:
            metrics_request = ExportMetricsServiceRequest()
            metrics_request.ParseFromString(body_bytes)
            # Here you would process the metrics, e.g., store them, run anomaly detection
            logger.info(f"Successfully parsed {len(metrics_request.resource_metrics)} metric resources.")
            # Dummy processing for now
            # In a real scenario, you'd call functions to store and analyze these metrics
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Metrics received"}),
            }

        elif "/v1/logs" in path:
            logs_request = ExportLogsServiceRequest()
            logs_request.ParseFromString(body_bytes)
            # Here you would process the logs
            logger.info(f"Successfully parsed {len(logs_request.resource_logs)} log resources.")
            # Dummy processing for now
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Logs received"}),
            }

        else:
            logger.warning(f"Unhandled path: {path}")
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Not Found"}),
            }

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
        }

