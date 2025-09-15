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

        if event.get("isBase64Encoded", False):
            body = base64.b64decode(body)

        # Handle gzipped content
        if headers.get("content-encoding") == "gzip":
            body = gzip.decompress(body)

        # Try parsing as Metrics
        try:
            metrics_request = ExportMetricsServiceRequest()
            metrics_request.ParseFromString(body)
            logger.info(f"Successfully parsed OTLP Protobuf metrics message.")

            # --- OTLP Metrics Transformation and Storage ---
            metrics_for_anomaly_detection: List[Metric] = []
            cluster_id = "unknown_cluster"

            with table.batch_writer() as batch:
                for resource_metric in metrics_request.resource_metrics:
                    for scope_metric in resource_metric.scope_metrics:
                        for metric in scope_metric.metrics:
                            metric_name = metric.name
                            metric_type = metric.WhichOneof("data")

                            # Skip complex metric types we don't handle yet
                            if metric_type not in ["gauge", "sum"]:
                                continue
                            
                            if not metric_type:
                                continue
                            
                            data = getattr(metric, metric_type)

                            for data_point in data.data_points:
                                # Extract labels from attributes
                                labels = {attr.key: attr.value.string_value for attr in data_point.attributes}
                                labels["__name__"] = metric_name

                                if "cluster_id" in labels:
                                    cluster_id = labels["cluster_id"]
                                
                                # Extract timestamp and value
                                timestamp_ns = data_point.time_unix_nano
                                timestamp_sec = timestamp_ns / 1e9
                                
                                value_key = data_point.WhichOneof("value")
                                if not value_key:
                                    continue
                                metric_value = getattr(data_point, value_key)

                                # Create metric object for anomaly detection
                                metric_obj = Metric(
                                    metric=labels, value=[timestamp_sec, metric_value]
                                )
                                metrics_for_anomaly_detection.append(metric_obj)

                                # Create DynamoDB item
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

        except Exception as e:
            # --- NEW LOG PARSING BRANCH ---
            # Try parsing as raw syslog log if Metrics parsing failed
            try:
                # Assuming the body is a raw string at this point
                raw_log_line = body.decode('utf-8') if isinstance(body, bytes) else body

                # Regex to parse syslog-like format
                # Example: Sep 15 12:04:08 dev-local systemd-networkd[808]: veth1a7ffd7: Gained IPv6LL
                log_pattern = re.compile(
                    r'^(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
                    r'(?P<hostname>\S+)\s+(?P<process>[^:]+):\s+(?P<message>.*)
                )
                match = log_pattern.match(raw_log_line)

                if match:
                    parsed_data = match.groupdict()

                    # Construct timestamp
                    # Need to get the current year for the timestamp
                    current_year = datetime.now().year
                    timestamp_str = f"{parsed_data['month']} {parsed_data['day']} {current_year} {parsed_data['time']}"
                    # Convert to Unix timestamp (seconds since epoch)
                    timestamp_obj = datetime.strptime(timestamp_str, '%b %d %Y %H:%M:%S')
                    timestamp_sec = timestamp_obj.timestamp()

                    # Determine severity (simplified for now, can be enhanced)
                    # For syslog, severity is often part of the process or inferred
                    severity_text = "INFO" # Default, can be improved with more complex parsing

                    log_body = parsed_data['message']
                    attributes = {
                        "hostname": parsed_data['hostname'],
                        "process": parsed_data['process'],
                        # Add other parsed fields as attributes
                    }

                    # Create a unique ID for the log entry
                    log_id = str(uuid.uuid4())

                    item = {
                        "log_id": log_id,
                        "timestamp": Decimal(str(timestamp_sec)),
                        "body": log_body,
                        "severity_text": severity_text,
                        "attributes": convert_floats_to_decimals(attributes),
                    }
                    logs_table.put_item(Item=item) # Use put_item directly for single log, or batch_writer for multiple

                    logger.info(f"Successfully parsed and stored raw log: {log_body}")

                else:
                    logger.warning(f"Raw log line did not match expected pattern: {raw_log_line}")
                    # If it's not a raw log, try parsing as OTLP Logs
                    logs_request = ExportLogsServiceRequest()
                    logs_request.ParseFromString(body)
                    logger.info(f"Successfully parsed OTLP Protobuf logs message.")
                    # --- OTLP Logs Transformation and Storage ---
                    log_samples_processed = 0
                    with logs_table.batch_writer() as batch:
                        for resource_log in logs_request.resource_logs:
                            for scope_log in resource_log.scope_logs:
                                for log_record in scope_log.log_records:
                                    timestamp_ns = log_record.time_unix_nano
                                    timestamp_sec = timestamp_ns / 1e9

                                    log_body = log_record.body.string_value
                                    severity_text = log_record.severity_text

                                    # Extract attributes (labels) from log record
                                    attributes = {attr.key: attr.value.string_value for attr in log_record.attributes}

                                    # Create a unique ID for the log entry
                                    log_id = str(uuid.uuid4())

                                    item = {
                                        "log_id": log_id,
                                        "timestamp": Decimal(str(timestamp_sec)),
                                        "body": log_body,
                                        "severity_text": severity_text,
                                        "attributes": convert_floats_to_decimals(attributes),
                                    }
                                    batch.put_item(Item=item)
                                    log_samples_processed += 1

                    logger.info(
                        (
                            f"Successfully processed and stored "
                            f"{log_samples_processed} log samples."
                        )
                    )

            except Exception as log_e:
                logger.error(f"Failed to parse as Metrics or Logs: {e}, {log_e}", exc_info=True)
                return {"statusCode": 400, "body": "Bad Request: Invalid OTLP Payload"}

        return {"statusCode": 200, "body": "{}"}

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return {"statusCode": 500, "body": "Internal Server Error"}