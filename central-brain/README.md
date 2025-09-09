# Central Brain

The `central-brain` is the core backend service for the AI DevOps Platform. It is a Python FastAPI application responsible for ingesting, analyzing, and storing metrics, as well as sending alerts.

## Features

*   **Metric Ingestion**: Exposes a secure `/ingest` endpoint to receive metric payloads from `edge-agent`s.
*   **Anomaly Detection**: Analyzes incoming metrics for anomalies. (Currently, it checks if the `up` metric is `0`).
*   **Data Storage**: Stores all ingested metrics in an AWS DynamoDB table for historical analysis and model training.
*   **Alerting**: Sends alerts via Telegram when anomalies are detected.

## Future Goals

To become a fully capable AIOps tool, the `central-brain` will be enhanced with the following capabilities:

*   **Advanced Anomaly Detection**: Implement more sophisticated machine learning models to detect a wider range of anomalies in metrics, logs, and traces.
*   **Alert Correlation and Noise Reduction**: Group related alerts, suppress duplicates, and identify the root cause of incidents to reduce alert fatigue.
*   **Automated Remediation**: Develop a framework for defining and executing automated actions to remediate common issues (e.g., restarting a service, scaling a resource).
*   **Predictive Analytics**: Build models to forecast future resource utilization, predict potential issues, and assist with capacity planning.
*   **ChatOps Integration**: Allow users to interact with the platform, query data, and trigger actions directly from chat applications like Slack and Microsoft Teams.

## Configuration

The `central-brain` is configured via environment variables. These are set automatically by the Terraform deployment based on the created infrastructure and input variables.

| Environment Variable  | Description                                                                 | Set Via                  |
| --------------------- | --------------------------------------------------------------------------- | ------------------------ |
| `CENTRAL_API_URL`     | The public URL of the Application Load Balancer fronting the service.         | Terraform Output         |
| `API_KEY`             | The secret API key that agents must use to authenticate.                      | Terraform Variable       |
| `PROMETHEUS_URL`      | The URL of the Prometheus instance to scrape (used by `edge-agent`).          | `edge-agent` config      |
| `LOG_LEVEL`           | The application log level (e.g., `INFO`, `DEBUG`).                            | Terraform Variable       |
| `TELEGRAM_BOT_TOKEN`  | The secret token for the Telegram bot used for sending alerts.                | Terraform Variable (Secret) |
| `TELEGRAM_CHAT_ID`    | The ID of the Telegram chat or channel to send alerts to.                     | Terraform Variable       |
| `AWS_REGION`          | The AWS region where the infrastructure is deployed.                          | Environment (via ECS)    |
| `DYNAMODB_TABLE_DATA` | The name of the DynamoDB table for storing metric data.                       | Terraform Output         |
| `DYNAMODB_TABLE_ALERTS`| The name of the DynamoDB table for storing alert configurations.              | Terraform Output         |

## Deployment

The `central-brain` is designed for automated, zero-touch deployment.

1.  **Build**: The `.github/workflows/central-brain.yaml` GitHub Actions workflow is triggered on every push to the `main` branch.
2.  **Test**: The workflow runs unit tests.
3.  **Publish**: If tests pass, the workflow builds a new Docker image and pushes it to the AWS ECR repository.
4.  **Deploy**: The Terraform configuration for the ECS service is set up to pull the `latest` image from ECR. When the ECS task is restarted or updated, it will automatically use the new image.

There are no manual deployment steps required for this component under normal operation.

updated at 06:18PM on 08/09/2025
testing ci/cd