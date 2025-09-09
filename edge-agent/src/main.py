# Put your custom imports FIRST
from prometheus_helper import get_selected_metrics
from k8s_client import KubernetesClient

# Then import third-party packages
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import uvicorn
import os
import logging
import asyncio
import time
import httpx
from contextlib import asynccontextmanager


# Configuration
CLUSTER_ID = os.getenv("CLUSTER_ID")
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL")
API_KEY = os.getenv("API_KEY")
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL", "http://prometheus-operated.monitoring.svc:9090"
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# List of specific metrics to collect
TARGET_METRICS = [
    "up",
    "node_cpu_seconds_total",
    "node_memory_MemTotal_bytes",
    "node_memory_MemFree_bytes",
    "node_memory_MemAvailable_bytes",
    "node_disk_read_bytes_total",
    "node_disk_written_bytes_total",
    "node_network_receive_bytes_total",
    "node_network_transmit_bytes_total",
    "container_cpu_usage_seconds_total",
    "container_memory_usage_bytes",
    "container_network_receive_bytes_total",
    "container_network_transmit_bytes_total",
    "machine_cpu_cores",
]


# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EdgeAgent:
    def __init__(self):
        self.kubernetes = KubernetesClient()
        self.is_healthy = True

    async def collect_metrics(self):
        """Collect a curated list of metrics from Prometheus"""
        try:
            logger.info(f"Collecting {len(TARGET_METRICS)} target metrics...")
            metrics = await get_selected_metrics(PROMETHEUS_URL, TARGET_METRICS)
            logger.info(f"Collected {len(metrics)} data points.")
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            self.is_healthy = False
            return []

    async def send_to_central_brain(self, data):
        """Send data to central brain"""
        if not CENTRAL_API_URL:
            logger.warning("CENTRAL_API_URL is not set. Skipping data send.")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{CENTRAL_API_URL}/ingest",
                    json=data,
                    headers={"X-API-KEY": API_KEY or ""},
                    timeout=60.0,
                )
                response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
                logger.info(
                    f"Successfully sent data to central brain. Status: {response.status_code}"
                )
                return True
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Error response {e.response.status_code} while requesting {e.request.url!r}: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return False

    async def run_loop(self):
        """Main collection loop"""
        logger.info(f"Starting Edge Agent for cluster {CLUSTER_ID}")

        while True:
            try:
                # Collect data
                metrics = await self.collect_metrics()
                k8s_state = await self.kubernetes.get_cluster_state()

                # Send to central brain in batches

                if (
                    not metrics
                    and not k8s_state.get("nodes")
                    and not k8s_state.get("pods")
                    and not k8s_state.get("deployments")
                ):
                    logger.warning("No metrics or K8s state collected, skipping send.")
                else:
                    payload = {
                        "cluster_id": CLUSTER_ID,
                        "metrics": metrics,
                        "timestamp": time.time(),
                    }
                    if (
                        k8s_state.get("nodes")
                        or k8s_state.get("pods")
                        or k8s_state.get("deployments")
                    ):
                        payload["kubernetes_state"] = k8s_state

                    # Send batch to central brain
                    # The batching logic for metrics is handled within collect_metrics if needed
                    # For simplicity, sending the entire payload as one item for now.
                    # If metrics list is very large, this might need re-evaluation.
                    logger.info(
                        f"Sending payload to central brain. Metrics: {len(metrics)}, K8s State: {bool(k8s_state.get('nodes') or k8s_state.get('pods') or k8s_state.get('deployments'))}"
                    )
                    await self.send_to_central_brain(payload)

                # Wait for next collection
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    agent = EdgeAgent()
    app.state.agent = agent

    # Start the collection loop as a background task
    task = asyncio.create_task(agent.run_loop())
    app.state.background_task = task

    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AI DevOps Edge Agent", lifespan=lifespan)


@app.get("/health")
async def health_check():
    if app.state.agent.is_healthy:
        return {"status": "healthy"}
    raise HTTPException(status_code=503, detail="Agent not healthy")


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/info")
async def info():
    return {"cluster_id": CLUSTER_ID, "version": "0.1.0", "status": "running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level=LOG_LEVEL.lower())
