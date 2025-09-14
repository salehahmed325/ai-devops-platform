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
- **Purpose**: Originally a Dockerized Python (FastAPI) application for metrics collection.
- **Status**: **DECOMMISSIONED**. Its role has been replaced by the OpenTelemetry Collector, a standard and more robust solution for data collection.

### b. `central-brain`
- **Purpose**: A serverless AWS Lambda function that serves as the AI/ML core.
- **Function**: Receives OTLP data, stores it in DynamoDB, performs anomaly detection, and sends alerts via Telegram.
- **Current Status**:
    - **Data Ingestion (Metrics):** **FULLY FUNCTIONAL**. Successfully receives OTLP Protobuf metrics via Lambda Function URL, decompresses gzip, parses Protobuf, and stores in DynamoDB. This is highly efficient and standard.
    - **Data Ingestion (Logs):** **READY IN LAMBDA, PENDING COLLECTOR CONFIGURATION**. The Lambda function is updated to differentiate and parse OTLP Protobuf logs and store them in `ai-devops-platform-logs` DynamoDB table. Logs are not yet flowing due to collector configuration.
    - **DynamoDB Storage:** Confirmed working for metrics. Log storage logic is implemented in Lambda.
    - **Anomaly Detection:** Implemented using MAD (Median Absolute Deviation), confirmed working for metrics, and sending Telegram alerts.
    - **Telegram Alerts:** Confirmed working.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket.
- **Status**: **UPDATED FOR SERVERLESS & LAMBDA FUNCTION URL**. Provisions Lambda, DynamoDB tables, and necessary IAM roles. API Gateway has been replaced by a direct Lambda Function URL.

### d. CI/CD
- **Workflows**: Unified `central-brain.yaml` workflow for building and deploying the `central-brain` Lambda function.
- **Status**: **FUNCTIONAL**. Pipeline successfully deploys the Lambda function and passes secrets securely.

### e. OpenTelemetry Collector Configuration (`otel-collector-config.yaml`)
- **Purpose**: Collects metrics and logs from sources (e.g., Prometheus, filelog) and exports them to the `central-brain` Lambda.
- **Current Status**:
    - **Metrics Collection:** Configured to scrape Prometheus and send metrics.
    - **Log Collection:** Configured to read from `/var/log/syslog` and send logs.
    - **Filtering:** Intended to filter metrics to only send Gauges and Sums.
    - **Current Issue**: **PERSISTENT CONFIGURATION ERROR**. The `transform` processor's `metric_statements` syntax for filtering by `metric.type_str` is causing an `invalid syntax: unexpected token "=="` error in the collector. This is preventing the collector from starting with the correct filtering and thus preventing logs from flowing.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message.

## 4. Session Summary (2025-09-14)

Today, we made significant progress and encountered persistent challenges:

1.  **Metrics Ingestion (OTLP Protobuf):** Successfully implemented end-to-end. The OpenTelemetry Collector sends gzipped Protobuf metrics via Lambda Function URL, which the Lambda correctly decompresses, parses, and stores.
2.  **Anomaly Detection:** Implemented and confirmed working for metrics.
3.  **Log Ingestion (Lambda Side):** The `central-brain` Lambda was updated to parse and store OTLP Protobuf logs.
4.  **OpenTelemetry Collector Filtering Issue:** Repeated attempts to correctly configure the `transform` processor in `otel-collector-config.yaml` to filter metrics by type (`metric.type_str`) have failed due to persistent syntax errors in the OTTL expression. This is currently blocking the proper flow of logs and metric filtering.

## 5. Next Steps

*   **Immediate Fix**: Debug and correct the `transform` processor's `metric_statements` syntax in `otel-collector-config.yaml` to correctly filter metrics by type. This is the critical blocker.
*   **Verify Log Flow**: Once the collector configuration is fixed, verify that logs are successfully flowing from the collector to the Lambda and being stored in DynamoDB.
*   **Traces Ingestion**: After logs are flowing, implement traces ingestion.
*   **Visualization Layer**: Begin building a web UI for data visualization.
