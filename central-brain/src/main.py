import os
import logging
from typing import Any, Dict, List

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
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

from decimal import Decimal


def convert_floats_to_decimals(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimals(elem) for elem in obj]
    return obj


# --- Pydantic Models ---
class Metric(BaseModel):
    metric: Dict[str, str]
    value: List[Any]


class IngestPayload(BaseModel):
    cluster_id: str
    metrics: List[Metric]
    kubernetes_state: Dict[str, Any]
    timestamp: float


# --- API Key Authentication ---
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


# --- Anomaly Detection ---
def detect_anomalies(metrics: List[Metric]) -> List[str]:
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
        X = np.array(up_values).reshape(-1, 1)

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
        logger.error(f"Anomaly detection failed: {e}")

    return anomalies


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
    logger.info(f"Received data from cluster: {payload.cluster_id}")

    # Store data in DynamoDB
    try:
        item = convert_floats_to_decimals(payload.dict())
        table.put_item(Item=item)
        logger.info(
            f"Successfully stored data for cluster {payload.cluster_id} in DynamoDB."
        )
    except Exception as e:
        logger.error(f"Failed to store data in DynamoDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to store data persistently")

    # Perform anomaly detection
    anomalies = detect_anomalies(payload.metrics)
    if anomalies:
        for anomaly in anomalies:
            # For now, just log alerts. Later, this will call an alert manager.
            logger.warning(f"ALERT: {anomaly}")

    return {"status": "success", "message": "Data ingested successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=LOG_LEVEL.lower())
