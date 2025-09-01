import httpx
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, prometheus_url):
        self.prometheus_url = prometheus_url

    async def get_metrics(self):
        """Get metrics from Prometheus"""
        try:
            query_url = urljoin(self.prometheus_url, "api/v1/query")
            async with httpx.AsyncClient() as client:
                response = await client.get(query_url, params={"query": "up"})
                response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
                data = response.json()
                return data.get("data", {}).get("result", [])
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Error response {e.response.status_code} while requesting {e.request.url!r}: {e}"
            )
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return []
