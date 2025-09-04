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
    - **CPU Core Collection**: Modified to collect `machine_cpu_cores` (and `node_cpu_info` was reverted).

### b. `central-brain`
- **Purpose**: A Dockerized Python (FastAPI) application that serves as the AI/ML core.
- **Function**: It exposes a secure `/ingest` endpoint to receive data from `edge-agent`s. It performs anomaly detection on the `up` metric and CPU usage, stores data persistently, and sends Telegram alerts for detected anomalies. It is set up for future expansion (e.g., more advanced AI/ML, other alerting channels).
- **Status**: **DEPLOYED & READY FOR ANALYSIS** (with ongoing debugging).
    - **CPU Percentage Calculation**: Refactored `detect_cpu_anomalies` to:
        - Process CPU metrics per job/instance.
        - Retrieve historical `node_cpu_seconds_total` data from DynamoDB using a Global Secondary Index (GSI).
        - Calculate CPU usage percentages based on total CPU seconds (all modes) and number of cores.
        - **Current Observation**: Calculated percentages are still very low (e.g., 0.000003%), suggesting instances are genuinely idle or `node_cpu_seconds_total` is not behaving as expected for busy CPU.
    - **IAM Permissions**: `dynamodb:Query` permission added to `AIDevOpsPlatformPolicy` for the `ai-devops-platform-data` table and its GSI.
    - **Pylance Errors**: All identified Pylance errors have been resolved.
    - **Telegram Alert Token**: `TELEGRAM_BOT_TOKEN` warning persists (needs to be set in ECS task definition environment variables).

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket (`ai-devops-platform-tfstate-...`).
- **Provisioned Resources**:
    - A dedicated **VPC** with public and private subnets.
    - A **NAT Gateway** to provide secure internet access for private resources.
    - **ECR Repositories** for both `edge-agent` and `central-brain` images.
    - An **S3 Bucket** (`ai-devops-platform-models-...`) for future AI/ML model storage.
    - Two **DynamoDB Tables**: `ai-devops-platform-data` for ingested metrics and `ai-devops-platform-alert-configs` for storing alert recipient configurations (e.g., Telegram chat IDs).
        - `ai-devops-platform-data`: Now includes `MetricName-InstanceJob-index` GSI for efficient historical data retrieval.
    - A comprehensive **IAM Policy** (`AIDevOpsPlatformPolicy`) providing necessary permissions, including DynamoDB read/write and SNS publish (for future alerting channels).
    - An **ECS Cluster** (`ai-devops-platform-cluster-dev`).
    - An **Application Load Balancer** to expose the `central-brain` service.
    - An **ECS Service** (`ai-devops-platform-service-dev`) running the `central-brain` container with `LOG_LEVEL=DEBUG` and `TELEGRAM_BOT_TOKEN` environment variables.
- **Status**: **COMPLETE** (with recent updates applied).
    - `dynamodb/main.tf`: `MetricName-InstanceJob-index` GSI added to `ai-devops-platform-data` table.
    - `iam/main.tf`: `dynamodb:Query` permission added for the GSI.
    - `ecs/main.tf`: `force_new_deployment = true` added to ECS service.

### d. CI/CD
- **Workflows**: GitHub Actions workflows (`central-brain.yaml`, `edge-agent.yaml`, `terraform.yaml`).
- **Status**: **FUNCTIONAL** (with recent fixes).
    - `central-brain.yaml`: `central-brain-image-tag` artifact now uploaded unconditionally on successful build.
    - `terraform.yaml`: `Read Image Tag` step made more robust for `workflow_dispatch` runs.

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
12. **Problem**: CPU anomaly alerts showed negative rates due to unsorted metrics.
13. **Solution**: Sorted CPU metrics by timestamp before rate calculation in `central-brain/src/main.py`.
14. **Problem**: CPU anomaly detection was not sensitive enough (3-sigma model).
15. **Solution**: Replaced 3-sigma with `IsolationForest` for CPU anomaly detection in `central-brain/src/main.py`.
16. **Problem**: CPU anomaly alerts showed negative rates due to counter resets/decreases.
17. **Solution**: Filtered out negative `value_diff` in CPU rate calculation in `central-brain/src/main.py`.
18. **Problem**: CPU anomaly alerts lacked job name and percentage display.
19. **Solution**: Included job name and converted CPU usage to percentage in `central-brain/src/main.py`.
20. **Problem**: CPU percentage calculation was wildly inaccurate (millions of percent).
21. **Solution**: Corrected unit conversion for `node_cpu_seconds_total` (removed erroneous division by 10^9) in `central-brain/src/main.py`.
22. **Problem**: `central-brain` could not retrieve historical CPU data from DynamoDB due to missing `dynamodb:Query` permission on the GSI.
23. **Solution**: Added `dynamodb:Query` permission to the IAM policy for the GSI in `infrastructure/terraform/modules/iam/main.tf`.
24. **Problem**: `terraform.yaml` workflow failed during manual runs due to missing artifact.
25. **Solution**: Made `Read Image Tag` step in `terraform.yaml` more robust by defaulting to `latest` if artifact is not found.
26. **Problem**: `central-brain-image-tag` artifact not consistently uploaded.
27. **Solution**: Removed restrictive `if` condition from `Upload Image Tag Artifact` step in `central-brain.yaml`.

## 5. Next Steps

1.  **Verify CPU Percentage Accuracy**: Confirm that the calculated CPU usage percentages in the `central-brain` logs are now realistic (between 0-100%).
2.  **Test Anomaly Detection**: Generate actual CPU load on an instance to verify that the `central-brain` correctly detects high CPU usage and sends alerts.
3.  **Address `TELEGRAM_BOT_TOKEN` Warning**: Ensure the `TELEGRAM_BOT_TOKEN` environment variable is correctly set in the ECS task definition for the `central-brain` service.
