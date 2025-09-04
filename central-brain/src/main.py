import os
import logging
from typing import Any, Dict, List, Optional

from decimal import Decimal
import httpx
import hashlib

import boto3
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest


# --- Configuration ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
API_KEY = os.getenv("API_KEY", "dev-test-key-123")  # Default for development
API_KEY_NAME = "X-API-KEY"
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "ai-devops-platform-data")

# --- Logging Setup ---
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- DynamoDB Setup ---
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE_NAME)  # type: ignore
alert_configs_table = dynamodb.Table(  # type: ignore
    os.getenv("DYNAMODB_ALERT_CONFIGS_TABLE_NAME", "ai-devops-platform-alert-configs")
)


def convert_floats_to_decimals(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(elem) for elem in obj]
    return obj


# --- Telegram Alerting ---

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


class AlertManager:
    def __init__(self, alert_configs_table):
        self.alert_configs_table = alert_configs_table

    async def send_telegram_alert(self, chat_id: str, message: str):
        if not TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN is not set. Cannot send Telegram alert.")
            return

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(TELEGRAM_API_URL, json=payload)
                response.raise_for_status()
                logger.info(f"Telegram alert sent to chat ID {chat_id}.")
        except httpx.RequestError as e:
            logger.error(f"Error sending Telegram alert: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Telegram API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while sending Telegram alert: {e}"
            )


# --- Pydantic Models ---
class Metric(BaseModel):
    metric: Dict[str, str]
    value: List[Any]


class IngestPayload(BaseModel):
    cluster_id: str
    metrics: List[Metric]
    kubernetes_state: Optional[Dict[str, Any]] = None
    timestamp: float


# --- API Key Authentication ---
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


# --- Anomaly Detection ---
def detect_up_anomalies(metrics: List[Metric]) -> List[str]:
    """A simple anomaly detection function using Isolation Forest on the 'up' metric."""
    anomalies = []
    try:
        # Extract the values of the 'up' metric (0 or 1)
        up_values = [
            float(m.value[1]) for m in metrics if m.metric.get("__name__") == "up"
        ]

        if not up_values or len(up_values) < 2:
            return []  # Not enough data to detect anomalies

        # Reshape data for Isolation Forest
        X = np.array(up_values, dtype=np.float64).reshape(-1, 1)

        # Fit the model
        clf = IsolationForest(contamination="auto", random_state=42)
        preds = clf.fit_predict(X)

        # Find anomalies (-1 indicates an anomaly)
        up_metrics = [m for m in metrics if m.metric.get("__name__") == "up"]
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


def detect_cpu_anomalies(metrics: List[Metric]) -> List[str]:
    """Detects anomalies in CPU usage metrics."""
    anomalies = []
    try:
        cpu_metrics = [
            m for m in metrics if m.metric.get("__name__") == "node_cpu_seconds_total"
        ]
        logger.info(
            f"Found {len(cpu_metrics)} 'node_cpu_seconds_total' metrics with mode 'user'."
        )
        for m in cpu_metrics:
            logger.info(f"  - Timestamp: {m.value[0]}")

        # Sort metrics by timestamp to ensure correct rate calculation
        cpu_metrics.sort(key=lambda m: float(m.value[0]))

        num_cores = 1  # Default to 1 if no core information is found

        # First, try to get the number of cores from 'machine_cpu_cores' metric
        for m in metrics:
            if m.metric.get("__name__") == "machine_cpu_cores":
                try:
                    num_cores = int(float(m.value[1]))
                    logger.info(
                        f"Detected {num_cores} CPU cores from machine_cpu_cores."
                    )
                    break  # Found it, no need to check other methods
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not parse machine_cpu_cores value: {m.value[1]}"
                    )

        # If machine_cpu_cores was not found or parsed, infer from node_cpu_seconds_total
        if num_cores == 1:  # Still default, meaning machine_cpu_cores wasn't used
            if cpu_metrics:
                # Get the instance label from the first cpu_metric (assuming all are from the same instance)
                instance_label = cpu_metrics[0].metric.get("instance")
                if instance_label:
                    unique_cpus = set()
                    for m in metrics:
                        if (
                            m.metric.get("__name__") == "node_cpu_seconds_total"
                            and m.metric.get("instance") == instance_label
                            and m.metric.get("cpu") is not None
                        ):
                            unique_cpus.add(m.metric.get("cpu"))
                    if unique_cpus:
                        num_cores = len(unique_cpus)
                        logger.info(
                            f"Inferred {num_cores} CPU cores from node_cpu_seconds_total."
                        )

        logger.info(f"Final CPU cores used for calculation: {num_cores}")

        # Aggregate CPU usage per timestamp across all cores for the instance
        # This creates a single time series for total user CPU seconds for the instance
        aggregated_cpu_data = {}
        for m in cpu_metrics:
            timestamp = m.value[0]
            value = float(m.value[1])
            aggregated_cpu_data.setdefault(timestamp, 0.0)
            aggregated_cpu_data[timestamp] += value

        # Sort the aggregated data by timestamp
        sorted_aggregated_cpu_data = sorted(aggregated_cpu_data.items())

        # Calculate the rate of change for the aggregated CPU usage
        rates = []
        # Ensure there are at least two data points to calculate a rate
        if len(sorted_aggregated_cpu_data) < 2:
            logger.info("Not enough aggregated CPU data to calculate rates. Returning.")
            return []

        for i in range(1, len(sorted_aggregated_cpu_data)):
            time_diff = (
                sorted_aggregated_cpu_data[i][0] - sorted_aggregated_cpu_data[i - 1][0]
            )
            value_diff = (
                sorted_aggregated_cpu_data[i][1] - sorted_aggregated_cpu_data[i - 1][1]
            )

            if time_diff > 0 and value_diff >= 0:
                # Rate is CPU seconds per second. Divide by num_cores to get utilization per core,
                # then multiply by 100 for percentage.
                percentage_rate = (value_diff / time_diff) / num_cores * 100
                rates.append(percentage_rate)

        logger.info(f"Calculated {len(rates)} CPU usage percentages.")

        if not rates:
            logger.info("No valid CPU usage percentages calculated. Returning.")
            return []

        # Use Isolation Forest to detect anomalies in the rates
        X = np.array(rates).reshape(-1, 1)
        clf = IsolationForest(contamination="auto", random_state=42)
        preds = clf.fit_predict(X)

        logger.info(f"Finished CPU anomaly detection. Predictions: {preds}")

        # Find anomalies (-1 indicates an anomaly)
        # The index `i` here refers to the index in the `rates` list.
        # The corresponding metric for the anomaly is the second point used to calculate the rate.
        for i, pred in enumerate(preds):
            if pred == -1:
                # Get the timestamp of the second point used for this rate calculation
                anomaly_timestamp = sorted_aggregated_cpu_data[i + 1][0]
                # Find a representative metric for this timestamp to get job and instance
                # This assumes that all cpu_metrics for a given instance share the same job/instance labels
                representative_metric = next(
                    (m for m in cpu_metrics if m.value[0] == anomaly_timestamp), None
                )

                if representative_metric:
                    instance = representative_metric.metric.get(
                        "instance", "unknown_instance"
                    )
                    job = representative_metric.metric.get("job", "unknown_job")
                    anomalies.append(
                        f"High CPU usage detected on job='{job}', instance='{instance}'. Usage: {rates[i]:.2f}%"
                    )
                else:
                    anomalies.append(
                        f"High CPU usage detected. Usage: {rates[i]:.2f}% (Instance/Job details not found)"
                    )

    except Exception as e:
        logger.error(f"CPU anomaly detection failed: {e}")

    return anomalies


def detect_anomalies(metrics: List[Metric]) -> List[str]:
    """Detects anomalies in various metrics."""
    all_anomalies = []
    all_anomalies.extend(detect_up_anomalies(metrics))
    all_anomalies.extend(detect_cpu_anomalies(metrics))
    return all_anomalies


# --- FastAPI App ---
app = FastAPI(
    title="AI DevOps Central Brain",
    description="The central processing and analysis core of the AI DevOps Platform.",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/ingest")
async def ingest_data(payload: IngestPayload, api_key: str = Depends(get_api_key)):
    """Endpoint to receive data from edge agents."""
    try:
        logger.info(f"Received data from cluster: {payload.cluster_id}")
        logger.debug(f"Ingest payload: {payload.dict()}")

        # Store data in DynamoDB
        try:
            # Use a batch writer to handle potentially large metric lists
            with table.batch_writer() as batch:
                # Store each metric as a separate item
                for metric in payload.metrics:
                    # Create a unique identifier for the metric
                    labels = []
                    for k, v in sorted(metric.metric.items()):
                        labels.append(f"{k}={v}")
                    metric_labels_str = "-".join(labels)
                    labels_hash = hashlib.sha256(metric_labels_str.encode()).hexdigest()
                    metric_identifier = f"{payload.timestamp}-{metric.metric.get('__name__')}-{labels_hash}"

                    item = {
                        "cluster_id": payload.cluster_id,
                        "metric_identifier": metric_identifier,
                        "timestamp": Decimal(str(payload.timestamp)),
                        "metric_name": metric.metric.get("__name__"),
                        "metric_labels": convert_floats_to_decimals(metric.metric),
                        "metric_value": convert_floats_to_decimals(metric.value),
                    }
                    batch.put_item(Item=item)

                # Store Kubernetes state as a separate item if it exists
                if payload.kubernetes_state:
                    k8s_item = {
                        "cluster_id": payload.cluster_id,
                        "timestamp": Decimal(str(payload.timestamp)),
                        "data_type": "kubernetes_state",
                        "state": convert_floats_to_decimals(payload.kubernetes_state),
                    }
                    batch.put_item(Item=k8s_item)

            logger.info(
                f"Successfully stored data for cluster {payload.cluster_id} in DynamoDB."
            )
        except Exception as e:
            logger.error(f"Failed to store data in DynamoDB: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to store data persistently"
            )

        # Perform anomaly detection
        anomalies = detect_anomalies(payload.metrics)
        if anomalies:
            alert_manager = AlertManager(alert_configs_table)
            try:
                response = alert_configs_table.get_item(
                    Key={"cluster_id": payload.cluster_id}
                )
                item = response.get("Item")
                if item and "telegram_chat_id" in item:
                    chat_id = item["telegram_chat_id"]
                    for anomaly in anomalies:
                        alert_message = f"🚨 Anomaly Alert for Cluster `{payload.cluster_id}` 🚨\n\n{anomaly}"
                        await alert_manager.send_telegram_alert(chat_id, alert_message)
                else:
                    logger.warning(
                        f"No Telegram chat ID found for cluster {payload.cluster_id}. Logging alerts instead."
                    )
                    for anomaly in anomalies:
                        logger.warning(f"ALERT: {anomaly}")
            except Exception as e:
                logger.error(
                    f"Failed to retrieve alert configuration or send Telegram alert: {e}"
                )
                for anomaly in anomalies:
                    logger.warning(
                        f"ALERT: {anomaly}"
                    )  # Fallback to logging if alert sending fails

        return {"status": "success", "message": "Data ingested successfully"}
    except Exception as e:
        logger.error(f"An unexpected error occurred in ingest_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=LOG_LEVEL.lower())
