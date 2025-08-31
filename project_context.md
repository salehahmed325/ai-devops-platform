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
- **Function**: It exposes a secure `/ingest` endpoint to receive data from `edge-agent`s. It currently performs a basic anomaly detection on the `up` metric and is set up for future expansion.
- **Status**: **DEPLOYED & RUNNING**. The application code is complete. The CI/CD pipeline in `.github/workflows/central-brain.yaml` is working. The infrastructure has been deployed to AWS via Terraform, and the service is running on ECS Fargate and is accessible via a public Application Load Balancer.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket (`ai-devops-platform-tfstate-...`).
- **Provisioned Resources**:
    - A dedicated **VPC** with public and private subnets.
    - A **NAT Gateway** to provide secure internet access for private resources.
    - **ECR Repositories** for both `edge-agent` and `central-brain` images.
    - An **S3 Bucket** (`ai-devops-platform-models-...`) for future AI/ML model storage.
    - A comprehensive **IAM Policy** (`AIDevOpsPlatformPolicy`) providing necessary permissions.
    - An **ECS Cluster** (`ai-devops-platform-cluster-dev`).
    - An **Application Load Balancer** to expose the `central-brain` service.
    - An **ECS Service** (`ai-devops-platform-service-dev`) running the `central-brain` container.
- **Status**: **COMPLETE**. The infrastructure has been successfully deployed via the workflow in `.github/workflows/terraform.yaml`.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Next Steps

1.  **Get the Public URL**: The `central-brain` is running, but we need its public URL. We can get this from the Terraform outputs by running the following command from the `infrastructure/terraform` directory:
    ```bash
    terraform output central_brain_url
    ```
2.  **Connect the `edge-agent`**: Update the `CENTRAL_API_URL` in the `edge-agent.env` file on your dev server to point to the new public URL of the `central-brain`.
3.  **Verify End-to-End Data Flow**: Restart the `edge-agent` container and check the logs of the `central-brain` container in AWS CloudWatch to confirm it is receiving data.
4.  **Implement Persistent Storage**: Modify the `central-brain` to store the ingested data in a persistent database (e.g., AWS RDS or DynamoDB) instead of the current in-memory list.
