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
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
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
DYNAMODB_TRACES_TABLE_NAME = os.getenv(
    "DYNAMODB_TRACES_TABLE_NAME", "ai-devops-platform-traces"
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
traces_table: Table = dynamodb.Table(DYNAMODB_TRACES_TABLE_NAME)
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
        # --- NEW: Ignore counter metrics which always increase ---
        if metric_name.endswith("_total"):
            logger.info(f"Skipping anomaly detection for counter metric: {metric_name}")
            continue

        # The value is a list [timestamp, value], so we need index 1
        values = [float(m.value[1]) for m in metric_group]
        
        if len(values) < 3: # Need at least 3 points for a meaningful MAD
            continue

        median = statistics.median(values)
        deviations = [abs(v - median) for v in values]
        mad = statistics.median(deviations)
        
        # If MAD is 0, all points are the same, so no anomalies
        if mad == 0:
            continue

        for m in metric_group:
            val = float(m.value[1])
            # This is the Modified Z-score calculation
            modified_z_score = 0.6745 * (val - median) / mad if mad else 0.0
            
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

    # --- NEW: Group anomalies by metric name for a cleaner message ---
    anomalies_by_metric: Dict[str, List[Anomaly]] = {}
    for anom in anomalies:
        if anom.metric_name not in anomalies_by_metric:
            anomalies_by_metric[anom.metric_name] = []
        anomalies_by_metric[anom.metric_name].append(anom)

    message = "🚨 *AIOps Anomaly Alert* 🚨\n\n"
    
    for metric_name, anomaly_group in anomalies_by_metric.items():
        # --- NEW: More readable format ---
        message += f"📈 *Metric:* `{metric_name}`\n"
        message += "Abnormal behavior detected across one or more instances:\n\n"
        
        for anomaly in anomaly_group:
            # Convert timestamp to readable format
            timestamp_str = datetime.fromtimestamp(anomaly.timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
            message += (
                f"  - *Instance:* `{anomaly.instance}`\n"
                f"  - *Detected Value:* `{anomaly.value:.2f}`\n"
                f"  - *When:* {timestamp_str}\n"
            )
        
        message += "\n*Explanation:* Values for this metric are significantly different from the recent norm.\n\n"
        message += "---\n\n"

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

# --- New Helper Functions for Handler ---

def _parse_otlp_metrics(metrics_request: ExportMetricsServiceRequest) -> List[Metric]:
    """Parses an OTLP ExportMetricsServiceRequest into a list of Metric data classes."""
    metrics_list = []
    for resource_metric in metrics_request.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric_proto in scope_metric.metrics:
                # Extract attributes from the resource level
                attributes = {attr.key: attr.value.string_value for attr in resource_metric.resource.attributes}
                job = attributes.get("service.name", "unknown_job")
                instance = attributes.get("service.instance.id", "unknown_instance")

                # Handle different metric types (Gauge and Sum are common)
                data_points = []
                if metric_proto.HasField("gauge"):
                    data_points = metric_proto.gauge.data_points
                elif metric_proto.HasField("sum"):
                    data_points = metric_proto.sum.data_points

                for dp in data_points:
                    # Extract value (can be double or int)
                    value = dp.as_double if dp.HasField("as_double") else dp.as_int
                    # Timestamp is in nanoseconds, convert to seconds
                    timestamp = dp.time_unix_nano / 1e9

                    metric_dict = {
                        "__name__": metric_proto.name,
                        "job": job,
                        "instance": instance,
                    }
                    # Add any other labels/attributes from the data point
                    for attr in dp.attributes:
                        metric_dict[attr.key] = attr.value.string_value

                    metrics_list.append(
                        Metric(metric=metric_dict, value=[timestamp, str(value)])
                    )
    logger.info(f"Parsed {len(metrics_list)} individual metric data points.")
    return metrics_list

def _store_metrics_in_dynamodb(metrics: List[Metric]):
    """Stores a list of metrics in DynamoDB using a batch writer."""
    if not metrics:
        return

    try:
        with table.batch_writer() as batch:
            # --- FIX: Enumerate to create a unique index for each metric in the batch ---
            for i, metric in enumerate(metrics):
                metric_name = metric.metric.get("__name__", "unknown")
                job = metric.metric.get("job", "unknown")
                instance = metric.metric.get("instance", "unknown")
                timestamp = metric.value[0]

                # Get cluster_id from metric attributes, default to job name
                cluster_id = metric.metric.get("cluster.id", job)
                
                # --- FIX: Add index to the identifier to guarantee uniqueness ---
                metric_identifier = f"{metric_name}#{instance}#{timestamp}#{i}"

                item = {
                    "cluster_id": cluster_id,
                    "metric_identifier": metric_identifier,
                    "metric_name": metric_name,
                    "job": job,
                    "instance": instance,
                    "timestamp": Decimal(str(timestamp)),
                    "value": Decimal(str(metric.value[1])),
                    "ttl": int(datetime.now().timestamp()) + (24 * 60 * 60 * 7),
                    "full_metric": convert_floats_to_decimals(metric.metric),
                }
                batch.put_item(Item=item)
        logger.info(f"Successfully stored {len(metrics)} metrics in DynamoDB.")
    except Exception as e:
        logger.error(f"Error storing metrics in DynamoDB: {e}", exc_info=True)


def _parse_and_store_logs_in_dynamodb(logs_request: ExportLogsServiceRequest):
    """Parses an OTLP ExportLogsServiceRequest and stores logs in DynamoDB."""
    log_count = 0
    try:
        with logs_table.batch_writer() as batch:
            for resource_log in logs_request.resource_logs:
                attributes = {attr.key: attr.value.string_value for attr in resource_log.resource.attributes}
                cluster_id = attributes.get("cluster.id", attributes.get("service.name", "unknown_cluster"))
                job = attributes.get("service.name", "unknown_job")
                instance = attributes.get("service.instance.id", "unknown_instance")

                for scope_log in resource_log.scope_logs:
                    # --- FIX: Enumerate to create a unique index for each log in the batch ---
                    for i, log_record in enumerate(scope_log.log_records):
                        log_count += 1
                        
                        # --- FIX: Add index to nanosecond timestamp to guarantee uniqueness ---
                        unique_timestamp = log_record.time_unix_nano + i

                        item = {
                            "cluster_id": cluster_id,
                            "timestamp": Decimal(unique_timestamp),
                            "job": job,
                            "instance": instance,
                            "severity": log_record.severity_text,
                            "body": log_record.body.string_value,
                            "attributes": {attr.key: attr.value.string_value for attr in log_record.attributes},
                            "ttl": int(datetime.now().timestamp()) + (24 * 60 * 60 * 7),  # 7-day TTL
                        }
                        batch.put_item(Item=item)
        logger.info(f"Successfully stored {log_count} logs in DynamoDB.")
    except Exception as e:
        logger.error(f"Error storing logs in DynamoDB: {e}", exc_info=True)

def _parse_and_store_traces_in_dynamodb(traces_request: ExportTraceServiceRequest):
    """Parses an OTLP ExportTraceServiceRequest and stores traces in DynamoDB."""
    span_count = 0
    try:
        with traces_table.batch_writer() as batch:
            for resource_span in traces_request.resource_spans:
                resource_attributes = {attr.key: attr.value.string_value for attr in resource_span.resource.attributes}
                service_name = resource_attributes.get("service.name", "unknown_service")

                for scope_span in resource_span.scope_spans:
                    for span in scope_span.spans:
                        span_count += 1
                        
                        # OTLP IDs are byte arrays, convert to hex strings for storage
                        trace_id = span.trace_id.hex()
                        span_id = span.span_id.hex()
                        parent_span_id = span.parent_span_id.hex() if span.parent_span_id else ""

                        item = {
                            "trace_id": trace_id,
                            "span_id": span_id,
                            "parent_span_id": parent_span_id,
                            "service_name": service_name,
                            "span_name": span.name,
                            "span_kind": span.kind,
                            "start_time_unix_nano": Decimal(span.start_time_unix_nano),
                            "end_time_unix_nano": Decimal(span.end_time_unix_nano),
                            "duration_nano": Decimal(span.end_time_unix_nano - span.start_time_unix_nano),
                            "status_code": span.status.code,
                            "status_message": span.status.message,
                            "attributes": {attr.key: attr.value.string_value for attr in span.attributes},
                            "events": [
                                {
                                    "name": event.name,
                                    "timestamp": Decimal(event.time_unix_nano),
                                    "attributes": {attr.key: attr.value.string_value for attr in event.attributes},
                                }
                                for event in span.events
                            ],
                            "ttl": int(datetime.now().timestamp()) + (24 * 60 * 60 * 7),  # 7-day TTL
                        }
                        batch.put_item(Item=item)
        logger.info(f"Successfully stored {span_count} spans in DynamoDB.")
    except Exception as e:
        logger.error(f"Error storing traces in DynamoDB: {e}", exc_info=True)


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
            if not body: # Add this check
                logger.warning("Received empty request body for /v1/metrics.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": "Bad Request: Empty body for metrics"}),
                    "headers": {"Content-Type": "application/json"},
                }
            metrics_request = ExportMetricsServiceRequest()
            metrics_request.ParseFromString(body_bytes)
            logger.info(f"Successfully parsed {len(metrics_request.resource_metrics)} metric resources.")
            
            parsed_metrics = _parse_otlp_metrics(metrics_request)
            _store_metrics_in_dynamodb(parsed_metrics)
            
            anomalies = detect_anomalies(parsed_metrics)
            if anomalies:
                send_telegram_alert(anomalies)

            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Metrics received and processed"}),
            }

        elif "/v1/logs" in path:
            if not body: # Add this check
                logger.warning("Received empty request body for /v1/logs.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": "Bad Request: Empty body for logs"}),
                    "headers": {"Content-Type": "application/json"},
                }
            logs_request = ExportLogsServiceRequest()
            logs_request.ParseFromString(body_bytes)
            logger.info(f"Successfully parsed {len(logs_request.resource_logs)} log resources.")

            _parse_and_store_logs_in_dynamodb(logs_request)

            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Logs received and processed"}),
            }

        elif "/v1/traces" in path:
            if not body: # Add this check
                logger.warning("Received empty request body for /v1/traces.")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": "Bad Request: Empty body for traces"}),
                    "headers": {"Content-Type": "application/json"},
                }
            traces_request = ExportTraceServiceRequest()
            traces_request.ParseFromString(body_bytes)
            logger.info(f"Successfully parsed {len(traces_request.resource_spans)} trace resources.")

            _parse_and_store_traces_in_dynamodb(traces_request)

            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Traces received and processed"}),
            }

        elif "/data" in path and event.get("requestContext", {}).get("http", {}).get("method") == "GET":
            logger.info("Received GET request for /data. Scanning DynamoDB for metrics.")
            try:
                # Perform a simple scan on the metrics table
                response = table.scan(Limit=10) # Limit to 10 items for a quick test
                items = response.get("Items", [])

                # Convert Decimal types to float for JSON serialization
                # Create a new list of items with Decimal converted to float for JSON serialization
                serializable_items = []
                for item in items:
                    serializable_item = {}
                    for key, value in item.items():
                        if isinstance(value, Decimal):
                            serializable_item[key] = float(value)
                        else:
                            serializable_item[key] = value
                    serializable_items.append(serializable_item)

                return {
                    "statusCode": 200,
                    "body": json.dumps({"message": "Data retrieved successfully", "data": serializable_items}),
                    "headers": {"Content-Type": "application/json"},
                }
            except Exception as e:
                logger.error(f"Error scanning DynamoDB for /data: {e}", exc_info=True)
                return {
                    "statusCode": 500,
                    "body": json.dumps({"message": "Internal Server Error during data retrieval"}),
                    "headers": {"Content-Type": "application/json"},
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