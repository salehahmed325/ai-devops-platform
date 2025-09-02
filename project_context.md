# Project Context for AI DevOps Platform

## 1. Project Vision & Goal

- **Vision**: To create a cloud-native, AI-powered monitoring platform that helps DevOps teams proactively identify anomalies, predict issues, and optimize their infrastructure using machine learning.
- **Core Components**: The system consists of two main parts: a lightweight `edge-agent` that collects data from client infrastructure, and a cloud-hosted `central-brain` that performs analysis and provides insights.

## 2. Current Architecture & Status

### a. `edge-agent`
- **Purpose**: A Dockerized Python (FastAPI) application that is deployed on a target server.
- **Function**: It queries a Prometheus instance to collect metrics, and forwards them to the `central-brain` in batches.
- **Status**: **COMPLETE & WORKING**. The agent is containerized, and its CI/CD pipeline in `.github/workflows/edge-agent.yaml` automatically builds, tests, and pushes its image to both AWS ECR and Docker Hub. The data collection and batching mechanism has been debugged and is now working reliably.

### b. `central-brain`
- **Purpose**: A Dockerized Python (FastAPI) application that serves as the AI/ML core.
- **Function**: It exposes a secure `/ingest` endpoint to receive data from `edge-agent`s. It performs anomaly detection on the `up` metric, stores data persistently, and sends Telegram alerts for detected anomalies. It is set up for future expansion (e.g., more advanced AI/ML, other alerting channels).
- **Status**: **DEPLOYED & RUNNING**. The application code is complete. The CI/CD pipeline in `.github/workflows/central-brain.yaml` is working. The infrastructure has been deployed to AWS via Terraform, and the service is running on ECS Fargate and is accessible via a public Application Load Balancer.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket (`ai-devops-platform-tfstate-...`).
- **Provisioned Resources**:
    - A dedicated **VPC** with public and private subnets.
    - A **NAT Gateway** to provide secure internet access for private resources.
    - **ECR Repositories** for both `edge-agent` and `central-brain` images.
    - An **S3 Bucket** (`ai-devops-platform-models-...`) for future AI/ML model storage.
    - Two **DynamoDB Tables**: `ai-devops-platform-data` for ingested metrics and `ai-devops-platform-alert-configs` for storing alert recipient configurations (e.g., Telegram chat IDs).
    - A comprehensive **IAM Policy** (`AIDevOpsPlatformPolicy`) providing necessary permissions, including DynamoDB read/write and SNS publish (for future alerting channels).
    - An **ECS Cluster** (`ai-devops-platform-cluster-dev`).
    - An **Application Load Balancer** to expose the `central-brain` service.
    - An **ECS Service** (`ai-devops-platform-service-dev`) running the `central-brain` container with `LOG_LEVEL=DEBUG` and `TELEGRAM_BOT_TOKEN` environment variables.
- **Status**: **COMPLETE**. The infrastructure has been successfully deployed via the workflow in `.github/workflows/terraform.yaml`.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Session Summary (2025-09-02)

Today, we successfully debugged and fixed the end-to-end data pipeline. Here is a summary of the steps taken:

1.  **Initial Problem**: The `edge-agent` was not correctly collecting metrics from Prometheus due to a bug in `prometheus_helper.py`.
2.  **Fix 1**: We corrected the `prometheus_helper.py` file to correctly handle the `httpx` client.
3.  **New Problem**: The `edge-agent` was timing out when connecting to Prometheus. We discovered this was due to a networking issue between the Docker container and the host machine.
4.  **Fix 2**: We configured the `edge-agent` to use `host.docker.internal` to connect to the host machine, and added the `--add-host` flag to the `docker run` command.
5.  **New Problem**: The `edge-agent` was timing out when sending the large payload of metrics to the `central-brain`.
6.  **Fix 3**: We implemented batching in the `edge-agent` to send the metrics in smaller chunks.
7.  **New Problem**: The `central-brain` was still timing out because the batches were too large for DynamoDB's item size limit.
8.  **Fix 4**: We reduced the batch size to a smaller number (200), which resolved the final issue.

**Current State:**
*   **End-to-End Data Flow:** The `edge-agent` is now reliably collecting all metrics from Prometheus and sending them in batches to the `central-brain`. The `central-brain` is successfully ingesting this data and storing it in DynamoDB.
*   **Alerting:** The basic alerting for the `up` metric is still functional.

## 5. Next Steps

The next major task is to leverage the rich dataset we are now collecting.

1.  **Refine Anomaly Detection in `central-brain`**:
    *   **Explore the Data**: Analyze the metrics being stored in the `ai-devops-platform-data` DynamoDB table to identify which metrics are the best candidates for anomaly detection.
    *   **Choose Models**: Select appropriate statistical methods or machine learning models for the chosen metrics.
    *   **Implement**: Update the `detect_anomalies` function in `central-brain/src/main.py` to incorporate the new models.
2.  **Review and Refine Alerting**:
    *   Consider adding more sophisticated alert templating to provide more context in the alerts.
    *   Explore integrating other alerting channels (e.g., email via SNS, PagerDuty, Slack).
3.  **Develop a User Interface/Dashboard**:
    *   Create a frontend application to visualize ingested data, anomalies, and alert configurations.