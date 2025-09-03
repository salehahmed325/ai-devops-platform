import httpx
import logging

logger = logging.getLogger(__name__)


async def get_selected_metrics(prometheus_url: str, metrics: list[str]) -> list:
    """
    Fetches the latest values for a specific list of metrics from Prometheus.

    Args:
        prometheus_url: The URL of the Prometheus server.
        metrics: A list of metric names to fetch.

    Returns:
        A list of metric data points.
    """
    all_metrics = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for metric_name in metrics:
            try:
                # Use a query that gets the latest value for all time series of a given metric name.
                # This is much more efficient than querying every single series individually.
                query = f"{metric_name}[5m]"
                response = await client.get(
                    f"{prometheus_url}/api/v1/query", params={"query": query}
                )
                response.raise_for_status()

                result = response.json()["data"]["result"]
                if result:
                    all_metrics.extend(result)
                else:
                    logger.warning(f"No data returned for metric: {metric_name}")
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error fetching metric {metric_name}: {e.response.status_code} - {e.response.text}"
                )
            except httpx.RequestError as e:
                logger.error(f"Request error fetching metric {metric_name}: {e}")
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred fetching metric {metric_name}: {e}"
                )

    logger.info(
        f"Collected {len(all_metrics)} data points for {len(metrics)} selected metrics."
    )
    return all_metrics
