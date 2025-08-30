# Put your custom imports FIRST
from prometheus_helper import PrometheusClient
from k8s_client import KubernetesClient

# Then import third-party packages
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import uvicorn
import os
import logging
import asyncio
from contextlib import asynccontextmanager


# Configuration
CLUSTER_ID = os.getenv("CLUSTER_ID")
CENTRAL_API_URL = os.getenv("CENTRAL_API_URL")
API_KEY = os.getenv("API_KEY")
PROMETHEUS_URL = os.getenv(
    "PROMETHEUS_URL", "http://prometheus-operated.monitoring.svc:9090"
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EdgeAgent:
    def __init__(self):
        self.prometheus = PrometheusClient(PROMETHEUS_URL)
        self.kubernetes = KubernetesClient()
        self.is_healthy = True

    async def collect_metrics(self):
        """Collect metrics from Prometheus"""
        try:
            metrics = await self.prometheus.get_metrics()
            logger.info(f"Collected {len(metrics)} metrics")
            return metrics
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            self.is_healthy = False
            return {}

    async def send_to_central_brain(self, data):
        """Send data to central brain"""
        # TODO: Implement actual API call
        logger.info(f"Would send data to {CENTRAL_API_URL}")
        return True

    async def run_loop(self):
        """Main collection loop"""
        logger.info(f"Starting Edge Agent for cluster {CLUSTER_ID}")

        while True:
            try:
                # Collect data
                metrics = await self.collect_metrics()
                k8s_state = await self.kubernetes.get_cluster_state()

                # Prepare payload
                payload = {
                    "cluster_id": CLUSTER_ID,
                    "metrics": metrics,
                    "kubernetes_state": k8s_state,
                    "timestamp": asyncio.get_event_loop().time(),
                }

                # Send to central brain
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
