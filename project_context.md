# Project Context for AI DevOps Platform

## 1. Project Vision & Goal

- **Vision**: To create a cloud-native, AI-powered monitoring platform that helps DevOps teams proactively identify anomalies, predict issues, and optimize their infrastructure using machine learning.
- **Core Components**: The system consists of two main parts: a lightweight `edge-agent` that collects data from client infrastructure, and a cloud-hosted `central-brain` that performs analysis and provides insights.

## 2. Current Architecture & Status

### a. `edge-agent`
- **Purpose**: A Dockerized Python (FastAPI) application that is deployed on a target server.
- **Function**: It queries a Prometheus instance to collect metrics, and is intended to forward them to the `central-brain`.
- **Status**: **COMPLETE & WORKING**. The agent is containerized, and its CI/CD pipeline in `.github/workflows/edge-agent.yaml` automatically builds, tests, and pushes its image to both AWS ECR and Docker Hub.

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
- **Status**: **COMPLETE**. The infrastructure has been successfully deployed via the workflow in `.github/workflows/terraform.yaml` (after several fixes to the workflow itself).

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Current State & Next Steps

**Current State:**
*   **End-to-End Data Flow:** `edge-agent` collects metrics and sends them to `central-brain`. `central-brain` ingests, processes, stores in DynamoDB, and sends Telegram alerts for anomalies.
*   **Infrastructure:** All necessary AWS resources are provisioned via Terraform.
*   **Alerting:** Telegram alerting is functional.

**Outstanding Issue:**
*   **Edge Agent Metric Collection:** The `edge-agent/src/prometheus_helper.py` file's `get_metrics` function has a syntax/formatting issue that prevents it from correctly collecting all Prometheus metrics. This needs to be manually corrected.

**Manual Correction Required for `edge-agent/src/prometheus_helper.py`:**
*   **Open the file:** `D:\projects\ai-devops-platform\edge-agent\src\prometheus_helper.py`
*   **Find this block of code (around line 17):**
    ```python
                series_url = urljoin(self.prometheus_url, "api/v1/series")            async with httpx.AsyncClient() as client:                                match_query = """{__name__=~".+"}"""
                series_response = await client.get(series_url, params={"match[]": match_query})
    ```
*   **Replace that entire block with this corrected and properly formatted code:**
    ```python
            series_url = urljoin(self.prometheus_url, "api/v1/series")
            async with httpx.AsyncClient() as client:
                match_query = '{__name__=~".+"}' # This is the query to get all series
                series_response = await client.get(series_url, params={"match[]": match_query})
    ```
*   **Save the file.**
*   **Run `black` on the file manually** to ensure it's formatted correctly:
    `D:/projects/ai-devops-platform/venv/Scripts/black.exe edge-agent/src/prometheus_helper.py`
*   **Commit and push this change to GitHub.** This will trigger the `Build Edge Agent` workflow.
*   **Pull the latest image on your dev server and run it.**

**Next Steps (after manual correction and `edge-agent` update):**

1.  **Verify Expanded Metric Collection:** Confirm the `edge-agent` is now collecting all Prometheus metrics by checking `central-brain` logs for a wider variety of ingested data.
2.  **Refine Anomaly Detection in `central-brain`:**
    *   The `detect_anomalies` function currently only looks at the `up` metric. It needs to be updated to analyze the expanded set of metrics for anomalies. This will be a significant AI/ML task.
3.  **Review and Refine Alerting**:
    *   Consider adding more sophisticated alert templating or customization options.
    *   Explore integrating other alerting channels (e.g., email via SNS, PagerDuty, Slack).
4.  **Implement AI/ML for Prediction and Optimization**:
    *   Utilize the historical data in DynamoDB to train machine learning models for predicting future issues or suggesting infrastructure optimizations.
5.  **Develop a User Interface/Dashboard**:
    *   Create a frontend application to visualize ingested data, anomalies, and alert configurations.
6.  **Expand Edge Agent Capabilities (Further)**:
    *   Add more data collection points or integrate with other monitoring tools.
