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
- **Status**: **COMPLETE**. The infrastructure has been successfully deployed via the workflow in `.github/workflows/terraform.yaml`.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Next Steps

1.  **Review and Refine Alerting**:
    *   Consider adding more sophisticated alert templating or customization options.
    *   Explore integrating other alerting channels (e.g., email via SNS, PagerDuty, Slack).
2.  **Implement AI/ML for Prediction and Optimization**:
    *   Utilize the historical data in DynamoDB to train machine learning models for predicting future issues or suggesting infrastructure optimizations.
3.  **Develop a User Interface/Dashboard**:
    *   Create a frontend application to visualize ingested data, anomalies, and alert configurations.
4.  **Expand Edge Agent Capabilities**:
    *   Add more data collection points or integrate with other monitoring tools.
