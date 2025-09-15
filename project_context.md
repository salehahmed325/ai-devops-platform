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
    - **Data Ingestion (Metrics):** **FULLY FUNCTIONAL**. Successfully receives OTLP Protobuf metrics via Lambda Function URL, decompresses gzip, parses Protobuf, and stores in DynamoDB. Metrics are filtered by type (only Gauge and Sum) by the collector.
    - **Data Ingestion (Logs):** **FULLY FUNCTIONAL**. Logs are successfully flowing from the collector and stored in `ai-devops-platform-logs` DynamoDB table.
    - **Traces Ingestion:** Lambda is ready to receive and store OTLP traces. Infrastructure (DynamoDB table, IAM permissions) is provisioned. Collector is configured to receive and export traces. **PENDING TRACE SOURCE APPLICATION.**
    - **DynamoDB Storage:** **FULLY FUNCTIONAL** for metrics, logs, and traces. All data is stored in their respective DynamoDB tables (`ai-devops-platform-data`, `ai-devops-platform-logs`, `ai-devops-platform-traces`) with correct schema and unique keys.
    - **Anomaly Detection:** Implemented using MAD (Median Absolute Deviation), confirmed working for metrics, and sending Telegram alerts. Noise reduction implemented by ignoring counter metrics. Telegram alerts are now more readable and grouped.
    - **Telegram Alerts:** Confirmed working.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket.
- **Status**: **UPDATED FOR SERVERLESS & LAMBDA FUNCTION URL**. Provisions Lambda, DynamoDB tables (including traces), and necessary IAM roles. API Gateway has been replaced by a direct Lambda Function URL.

### d. CI/CD
- **Workflows**: Unified `central-brain.yaml` workflow for building and deploying the `central-brain` Lambda function.
- **Status**: **FUNCTIONAL**. Pipeline successfully deploys the Lambda function and passes secrets securely.

### e. OpenTelemetry Collector Configuration (`otel-collector-config.yaml`)
- **Purpose**: Collects metrics and logs from sources (e.g., Prometheus, filelog) and exports them to the `central-brain` Lambda.
- **Current Status**:
    - **Metrics Collection:** Configured to scrape Prometheus and send metrics. Metrics filtering is now correctly implemented using the `filter` processor to send only Gauge and Sum types.
    - **Log Collection:** Configured to read from `/var/log/syslog` and send logs.
    - **Traces Collection:** OTLP receiver for traces is configured, and a traces pipeline is active.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message.

## 4. Session Summary (2025-09-15)

Today, we made significant progress in building out the core observability capabilities of the AI DevOps Platform:

1.  **Central Brain Robustness**:
    *   Resolved `Runtime.HandlerNotFound` error by implementing the main Lambda handler.
    *   Fixed DynamoDB `ValidationException` errors for both metrics and logs by aligning item structures with table schemas and ensuring key uniqueness.
    *   Implemented noise reduction in anomaly detection by ignoring counter metrics.
    *   Improved Telegram alert readability and grouping.
2.  **Traces Ingestion**:
    *   Provisioned `ai-devops-platform-traces` DynamoDB table and updated IAM permissions via Terraform.
    *   Implemented OTLP trace ingestion logic in the `central-brain` Lambda function.
    *   Configured OpenTelemetry Collector to receive and export traces.
    *   **Current Status**: Trace ingestion pipeline is fully set up on the infrastructure, Lambda, and Collector sides. A source application is required to generate and send traces.
3.  **OpenTelemetry Collector Configuration**:
    *   Successfully debugged and implemented correct metric filtering (Gauge and Sum only) using the `filter` processor.
    *   Configured trace reception and export.

## 5. Next Steps

*   **Immediate Fix**: Debug and correct the `transform` processor's `metric_statements` syntax in `otel-collector-config.yaml` to correctly filter metrics by type. This is the critical blocker.
*   **Verify Log Flow**: Once the collector configuration is fixed, verify that logs are successfully flowing from the collector to the Lambda and being stored in DynamoDB.
*   **Traces Ingestion**: After logs are flowing, implement traces ingestion.
*   **Visualization Layer**: Begin building a web UI for data visualization.