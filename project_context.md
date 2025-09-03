# Project Context for AI DevOps Platform

## 1. Project Vision & Goal

- **Vision**: To create a cloud-native, AI-powered monitoring platform that helps DevOps teams proactively identify anomalies, predict issues, and optimize their infrastructure using machine learning.
- **Core Components**: The system consists of two main parts: a lightweight `edge-agent` that collects data from client infrastructure, and a cloud-hosted `central-brain` that performs analysis and provides insights.

## 2. Current Architecture & Status

### a. `edge-agent`
- **Purpose**: A Dockerized Python (FastAPI) application that is deployed on a target server.
- **Function**: It queries a Prometheus instance to collect metrics, and forwards them to the `central-brain`.
- **Status**: **WORKING & OPTIMIZED**. The agent is containerized, and its CI/CD pipeline in `.github/workflows/edge-agent.yaml` automatically builds, tests, and pushes its image to both AWS ECR and Docker Hub.
    - **Data Collection Refinement**: The agent now collects a 5-minute range of data for each metric, providing the necessary data for rate calculations.
    - **Conditional K8s State**: It conditionally collects and sends Kubernetes cluster state only if running within a K8s environment, preventing unnecessary empty data payloads.
    - **Code Quality**: Pylance type warnings and Black formatting issues have been resolved.

### b. `central-brain`
- **Purpose**: A Dockerized Python (FastAPI) application that serves as the AI/ML core.
- **Function**: It exposes a secure `/ingest` endpoint to receive data from `edge-agent`s. It performs anomaly detection on the `up` metric and CPU usage, stores data persistently, and sends Telegram alerts for detected anomalies. It is set up for future expansion (e.g., more advanced AI/ML, other alerting channels).
- **Status**: **DEPLOYED & READY FOR ANALYSIS**. The application code is complete. The CI/CD pipeline in `.github/workflows/central-brain.yaml` is working. The infrastructure has been deployed to AWS via Terraform, and the service is running on ECS Fargate and is accessible via a public Application Load Balancer.
    - **Payload Compatibility**: The `/ingest` endpoint has been updated to handle batch writes of metrics and the optional `kubernetes_state` field from the `edge-agent`.

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

## 4. Session Summary (2025-09-04)

Today, we focused on debugging the data pipeline and refining the anomaly detection capabilities:

1.  **Problem**: The `central-brain` was failing to store data in DynamoDB due to the payload size exceeding the 400KB limit for a single item.
2.  **Solution**: Modified the `central-brain/src/main.py` to process the incoming metrics in batches, storing each metric as a separate item in DynamoDB.
3.  **Problem**: The `central-brain`'s ECS task execution role lacked the necessary IAM permission (`dynamodb:BatchWriteItem`) to perform the batch write operation.
4.  **Solution**: Updated the IAM policy in `infrastructure/terraform/modules/iam/main.tf` to include the `dynamodb:BatchWriteItem` permission.
5.  **Problem**: The `BatchWriteItem` operation was failing due to duplicate primary keys in the batch, as all metrics had the same `cluster_id` and `timestamp`.
6.  **Solution**: Changed the primary key of the DynamoDB table to use a unique `metric_identifier` (a combination of timestamp, metric name, and a hash of the labels). This required recreating the DynamoDB table.
7.  **Problem**: The `metric_identifier` was too long, exceeding the 1024-byte limit for a range key.
8.  **Solution**: Used a SHA256 hash of the metric labels to create a fixed-size identifier.
9.  **Feature**: Implemented a new anomaly detection function in `central-brain` to monitor CPU usage (`node_cpu_seconds_total` with `mode='user'`).
10. **Feature**: Updated the `edge-agent` to collect the last 5 minutes of data for each metric, providing the necessary data for rate calculations.
11. **Feature**: Added manual triggers (`workflow_dispatch`) to the `central-brain` and `edge-agent` CI/CD workflows to allow for manual deployments.

**Current State:**
*   **Robust Data Pipeline:** The data pipeline is now stable and can handle large payloads from the `edge-agent`.
*   **Enhanced Anomaly Detection:** The `central-brain` can now detect anomalies in both service availability (`up` metric) and CPU usage.
*   **Flexible Workflows:** The CI/CD workflows for the `central-brain` and `edge-agent` can be triggered manually.

## 5. Next Steps

The next major task is to continue refining the anomaly detection and improving the overall system.

1.  **Refine CPU Anomaly Detection**:
    *   **Analyze the Data**: Analyze the CPU usage data to determine if the current 3-sigma model is effective or if it needs to be adjusted.
    *   **Consider Other Metrics**: Explore other metrics that would be good candidates for anomaly detection, such as memory usage, disk I/O, and network traffic.
2.  **Review and Refine Alerting**:
    *   **Improve Alert Messages**: Make the alert messages more informative by including more context about the anomaly.
    *   **Integrate Other Channels**: Explore integrating other alerting channels like email or PagerDuty.
3.  **Develop a User Interface/Dashboard**:
    *   Create a frontend application to visualize the ingested data, anomalies, and alert configurations.