# Project Context for AI DevOps Platform

## 1. Project Vision & Goal

- **Vision**: To create a fully capable, cloud-native AIOps platform that helps DevOps teams proactively identify anomalies, predict issues, and automate remediation tasks to optimize their infrastructure.
- **Core Pillars**:
    - **Observe**: Collect a wide range of data, including metrics, logs, traces, and events.
    - **Engage**: Provide intelligent alerting, noise reduction, and ChatOps integration.
    - **Act**: Enable automated and assisted remediation of identified issues.
    - **Learn**: Use advanced AI/ML models for predictive analytics, root cause analysis, and continuous learning.

## 2. Current Architecture & Status

### a. `edge-agent`
- **Purpose**: A Dockerized Python (FastAPI) application that is deployed on a target server.
- **Function**: It queries a Prometheus instance to collect metrics and forwards them to the `central-brain`.
- **Status**: **WORKING & OPTIMIZED**. The agent is containerized, and its CI/CD pipeline is functional. (Note: Its role in metrics collection will be replaced by standard agents in the future).

### b. `central-brain`
- **Purpose**: A serverless AWS Lambda function that serves as the AI/ML core.
- **Function**: It exposes an API Gateway endpoint to receive Prometheus `remote_write` data. It stores data in DynamoDB and sends alerts via Telegram.
- **Status**: **DEPLOYED (but anomaly detection temporarily disabled)**. The core ingestion and storage are functional. Anomaly detection is currently disabled due to AWS Lambda size limits for `numpy` and `scikit-learn`.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket.
- **Status**: **UPDATED FOR SERVERLESS**. The infrastructure now provisions API Gateway, Lambda, and necessary IAM roles.

### d. CI/CD
- **Workflows**: Unified `central-brain.yaml` workflow for building and deploying the `central-brain` Lambda function and its associated layer.
- **Status**: **IN PROGRESS / DEBUGGING**. The pipeline is currently failing during the Lambda Layer publication step due to an empty zip file.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Session Summary (2025-09-10)

Today, we undertook a major architectural pivot and debugged numerous CI/CD issues:

1.  **Architectural Pivot**: Transitioned the `central-brain` from an ECS-based container to a cost-effective, serverless AWS Lambda function exposed via API Gateway.
2.  **Code Refactoring**: Rewrote `central-brain/src/main.py` to be a Lambda handler, including Prometheus `remote_write` parsing.
3.  **Infrastructure Refactoring**: Updated Terraform to provision Lambda, API Gateway, and associated IAM roles, removing old ECS/ALB resources.
4.  **CI/CD Refactoring**: Unified the `central-brain` build and deploy workflows into a single `central-brain.yaml` file, removing the separate `terraform.yaml`.
5.  **Debugging CI/CD and Code Issues**:
    *   Resolved `pip install zip` error (incorrect dependency).
    *   Fixed `black` formatting and `flake8` linting errors (syntax, unused imports, line length conflicts).
    *   Addressed local Pylance type-checking warnings (`boto3` stubs, protobuf type hints).
    *   Resolved `NoSuchBucket` error (timing issue between S3 upload and Terraform apply).
    *   Encountered `RequestEntityTooLargeException` for Lambda Layer (zipped size limit).
    *   Encountered `InvalidParameterValueException: Unzipped size must be smaller than 262144000 bytes` for Lambda Layer (unzipped size limit).
    *   **Current Issue**: The `layer_build` job is now creating an empty zip file, leading to `Uploaded file must be a non-empty zip` error. Anomaly detection is temporarily disabled.

## 5. Next Steps

*   **Immediate Fix**: Resolve the `Uploaded file must be a non-empty zip` error in the `layer_build` job.
*   **Anomaly Detection**: Re-evaluate how to implement anomaly detection given Lambda size constraints (e.g., separate service, different ML approach).
*   **Documentation**: Update other project documentation (`README.md`, `INSTALL.md`) to reflect the new architecture.