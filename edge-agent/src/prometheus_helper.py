import aiohttp
import logging

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, prometheus_url):
        self.prometheus_url = prometheus_url
        self.session = aiohttp.ClientSession()

    async def get_metrics(self):
        """Get metrics from Prometheus"""
        try:
            async with self.session.get(
                f"{self.prometheus_url}"  # This is correct if PROMETHEUS_URL=http://192.168.101.17:9090
            ) as response:
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
