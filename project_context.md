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
- **Function**: It exposes an API Gateway endpoint to receive data, stores data in DynamoDB, and sends alerts via Telegram.
- **Status**: **DEPLOYED & Receiving JSON Data**. The Lambda function is successfully receiving and parsing JSON data. Anomaly detection is temporarily disabled. **Current Issue**: Data is not being stored in DynamoDB, despite `batch.put_item` being called. The Lambda logs show "Successfully processed and stored 0 metric samples", which is misleading.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket.
- **Status**: **UPDATED FOR SERVERLESS & VPC REMOVED**. The infrastructure now provisions API Gateway, Lambda, and necessary IAM roles. VPC configuration has been removed.

### d. CI/CD
- **Workflows**: Unified `central-brain.yaml` workflow for building and deploying the `central-brain` Lambda function.
- **Status**: **FUNCTIONAL**. The pipeline is successfully deploying the Lambda function.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Session Summary (2025-09-11)

Today, we debugged numerous issues with the `central-brain` Lambda function:

1.  **Lambda Layer & VPC Removal**: Removed the `layer_build` job and VPC configuration from the CI/CD and Terraform, resolving deployment errors related to empty zip files and manual VPC deletions.
2.  **Lambda Handler Fixes**:
    *   Changed `async def handler` to `def handler` to resolve `Runtime.MarshalError`.
    *   Fixed `lambda_zip_key` not being passed to the deploy job in CI/CD.
    *   Resolved `NameError: name 'logger' is not defined` by moving logger initialization.
    *   Fixed `Syntax error: keyword argument repeated: create_key` by removing `create_key` arguments from hardcoded protobuf definition.
    *   Fixed `Runtime.HandlerNotFound` by re-inserting the `handler` function.
3.  **API Key Debugging**: Resolved "Invalid or missing API Key" by simplifying the API key and ensuring it was correctly passed and recognized by the Lambda.
4.  **Data Ingestion Pivot (Protobuf to JSON)**:
    *   Encountered persistent `snappy` decompression issues (`cramjam.DecompressionError: snappy: corrupt input`) and `protobuf` parsing errors (`Error parsing message with type 'remote.WriteRequest'`).
    *   Decided to pivot to JSON data ingestion to bypass these issues, modifying both `central-brain/src/main.py` and `generate_payload.py` to handle JSON.
    *   Successfully verified JSON data reception and parsing in Lambda.

## 5. Next Steps

*   **Immediate Fix**: Debug why data is not being stored in DynamoDB by the `central-brain` Lambda function. This will involve further investigation into the `batch_writer` and `put_item` operations, and potentially checking DynamoDB permissions or table configuration.
*   **Anomaly Detection**: Re-evaluate how to implement anomaly detection given Lambda size constraints (e.g., separate service, different ML approach).
*   **Documentation**: Update other project documentation (`README.md`, `INSTALL.md`) to reflect the new architecture.