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
    - **Data Ingestion (Metrics/Logs/Traces):** **FULLY FUNCTIONAL**. Successfully receives OTLP Protobuf metrics, logs, and traces via Lambda Function URL. Decompresses gzip, parses Protobuf, and stores in DynamoDB. Body presence checks are now correctly implemented within specific ingestion paths.
    - **Query Endpoint (`/data`):** **FULLY FUNCTIONAL**. Implemented a `/data` endpoint that responds to `GET` requests, queries the `ai-devops-platform-data` DynamoDB table, and returns aggregated metrics data. Handles `Decimal` serialization for JSON output.
    - **API Key Authentication:** **FULLY FUNCTIONAL**. Lambda performs API key validation via the `x-api-key` header.
    - **DynamoDB Storage:** **FULLY FUNCTIONAL** for metrics, logs, and traces. All data is stored in their respective DynamoDB tables (`ai-devops-platform-data`, `ai-devops-platform-logs`, `ai-devops-platform-traces`) with correct schema and unique keys.
    - **DynamoDB Access Permissions:** **FULLY FUNCTIONAL**. Lambda's IAM role now includes `dynamodb:Scan` permissions on `ai-devops-platform-data` table.
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

### f. Visualization Layer
- **Status**: **INITIAL SETUP COMPLETE**. Next.js application scaffolded. Basic dashboard page created. Data fetching from `central-brain` `/data` endpoint implemented and successfully displaying metrics data in a table.
- **Technology**: Next.js (React), Tailwind CSS.
- **Current Display**: Displays metrics data in a basic table format.

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

## 5. Session Summary (2025-09-16)

Today, we focused on building the initial visualization layer and debugging the data flow:

1.  **Next.js Frontend Setup**:
    *   Scaffolded a new Next.js application (`ui` directory) with TypeScript, Tailwind CSS, and App Router.
    *   Created a basic dashboard page (`src/app/dashboard/page.tsx`).
    *   Resolved a hydration mismatch error by adding `suppressHydrationWarning` to `layout.tsx`.
2.  **Central Brain Lambda Enhancements**:
    *   Implemented a new `/data` endpoint in `central-brain/src/main.py` to serve aggregated metrics data from DynamoDB.
    *   Corrected `Decimal` serialization for JSON output in the `/data` endpoint to resolve Pylance errors.
    *   Refactored body presence checks in the Lambda handler to correctly differentiate between OTLP ingestion (expecting body) and `/data` query (no body).
3.  **Data Flow Debugging & Resolution**:
    *   **CORS Issue (403)**: Confirmed permissive CORS configuration in Terraform and successful CI/CD application.
    *   **API Key Authentication (403)**: Identified and resolved the issue where the Lambda function was not receiving the correct `x-api-key` header from the frontend. Verified Lambda's `API_KEY` environment variable and ensured frontend sends the correct header.
    *   **Empty Request Body (400)**: Resolved by implementing the `/data` query endpoint in the Lambda and updating the frontend to call it.
    *   **DynamoDB Access (AccessDeniedException)**: Granted `dynamodb:Scan` permissions to the Lambda's IAM role via Terraform.
4.  **Successful Data Display**: The Next.js dashboard now successfully fetches and displays metrics data from the `central-brain` Lambda in a formatted table.

## 6. Next Steps

*   **Visualization Layer Enhancements**:
    *   Implement filtering and search for metrics (by `metric_name`, `job`, `instance`, time range).
    *   Integrate charting libraries for time-series visualization of metrics.
    *   Extend Lambda query capabilities and frontend to fetch and display logs and traces.
*   **Traces Ingestion**: (Deferred for now, but remains a future task).
