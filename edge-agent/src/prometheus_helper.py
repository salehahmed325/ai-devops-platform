import aiohttp
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, prometheus_url):
        self.prometheus_url = prometheus_url
        self.session = aiohttp.ClientSession()

    async def get_metrics(self):
        """Get metrics from Prometheus"""
        try:
            query_url = urljoin(self.prometheus_url, "api/v1/query")
            async with self.session.get(query_url, params={"query": "up"}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("result", [])
                else:
                    logger.error(f"Prometheus query failed: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return []

    async def close(self):
        """Close the session"""
        await self.session.close()
