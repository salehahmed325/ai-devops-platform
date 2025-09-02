import httpx
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(self, prometheus_url):
        self.prometheus_url = prometheus_url

    async def get_metrics(self):
        """Collect all metrics from Prometheus"""
        all_metrics = []
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Get all active series
                series_url = urljoin(self.prometheus_url, "api/v1/series")
                match_query = '{__name__=~".+"}'  # This is the query to get all series
                series_response = await client.get(
                    series_url, params={"match[]": match_query}
                )
                series_response.raise_for_status()
                series_data = series_response.json()
                series_list = series_data.get("data", [])

                logger.info(f"Found {len(series_list)} active series in Prometheus.")

                # Step 2: For each series, get its latest value
                query_url = urljoin(self.prometheus_url, "api/v1/query")
                for series_labels in series_list:
                    # Construct a query string from labels to get the latest value of this series
                    # Exclude __name__ as it's part of the query itself
                    query_parts = []
                    metric_name = series_labels.pop("__name__", None)
                    if not metric_name:
                        continue  # Skip if no metric name

                    for key, value in series_labels.items():
                        query_parts.append(f'{key}="{value}"')

                    query_string = (
                        f"{metric_name}{{{','.join(query_parts)}}}"
                        if query_parts
                        else metric_name
                    )

                    try:
                        metric_response = await client.get(
                            query_url, params={"query": query_string}
                        )
                        metric_response.raise_for_status()
                        metric_data = metric_response.json()
                        result = metric_data.get("data", {}).get("result", [])
                        if result:
                            all_metrics.extend(result)
                    except httpx.RequestError as e:
                        logger.error(f"Error querying metric {query_string!r}: {e}")
                    except httpx.HTTPStatusError as e:
                        logger.error(
                            f"Prometheus API error for {query_string!r}: {e.response.status_code} - {e.response.text}"
                        )

                logger.info(
                    f"Collected {len(all_metrics)} actual metrics from Prometheus."
                )
                return all_metrics

        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting Prometheus series: {e}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Prometheus series API error: {e.response.status_code} - {e.response.text}"
            )
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred during metric collection: {e}")
            return []
