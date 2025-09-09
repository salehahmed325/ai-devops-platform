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
- **Status**: **WORKING & OPTIMIZED**. The agent is containerized, and its CI/CD pipeline is functional.

### b. `central-brain`
- **Purpose**: A Dockerized Python (FastAPI) application that serves as the AI/ML core.
- **Function**: It exposes a secure `/ingest` endpoint to receive data from `edge-agent`s. It performs basic anomaly detection, stores data in DynamoDB, and sends alerts via Telegram.
- **Status**: **DEPLOYED & READY FOR ANALYSIS**.

### c. Infrastructure (Terraform)
- **Provider**: AWS
- **State Management**: Terraform state is stored remotely in an S3 bucket.
- **Status**: **COMPLETE**. The infrastructure is fully provisioned and stable.

### d. CI/CD
- **Workflows**: GitHub Actions workflows for the `edge-agent`, `central-brain`, and Terraform.
- **Status**: **FUNCTIONAL**.

## 3. How to Resume

When you start our new session, paste the entire content of this file as your first message. Then, we can proceed with the following next steps.

## 4. Session Summary (2025-09-08)

Today, we focused on resolving infrastructure issues and defining the long-term vision for the project:

1.  **Problem**: Terraform state was lost after a `terraform destroy` command, causing `terraform init` and `terraform apply` to fail.
2.  **Solution**: Recreated the S3 bucket for Terraform state and enabled versioning to prevent future data loss.
3.  **Problem**: The `terraform-init.sh` script was failing due to shell environment issues on Windows.
4.  **Solution**: Resolved the issue by running the script in Git Bash.
5.  **Feature**: Defined the long-term vision for the project to become a fully capable AIOps platform, with four key pillars: Observe, Engage, Act, and Learn.
6.  **Feature**: Updated the `README.md` files for the `edge-agent` and `central-brain` to reflect the new project goals.
7.  **Feature**: Updated this `project_context.md` file with the new vision, goals, and roadmap.

## 4. Session Summary (2025-09-08 - Continued)

Today, we continued our work on integrating Fluent Bit for log collection:

1.  **Feature**: Integrated Fluent Bit for log collection.
    *   Created Fluent Bit configuration and Dockerfile.
    *   Updated the `edge-agent`'s CI/CD pipeline to build and push the Fluent Bit image to both ECR and Docker Hub.
    *   Updated the `edge-agent` to start and monitor the Fluent Bit container.
    *   Updated the `central-brain` to receive log data and store it in a new DynamoDB table.
    *   Updated the Terraform configuration to create the new DynamoDB table and ECR repository.
2.  **Problem**: `edge-agent` failed to connect to Docker daemon.
3.  **Solution**: Mounted the Docker socket into the `edge-agent` container.
4.  **Problem**: Fluent Bit was not collecting Docker container logs.
5.  **Solution**: Updated Fluent Bit configuration to tail Docker logs and added a parser for Docker logs.

## 4. Session Summary (2025-09-09 - Continued)

Today, we focused on resolving Fluent Bit and Central Brain connectivity and permission issues.

1.  **Fluent Bit Deployment:**
    *   Transitioned from Dockerized Fluent Bit to direct installation on the server to bypass Docker-related environment and permission complexities.
    *   **Current Status:** Fluent Bit service is running, but still encountering:
        *   `float_parsing` error for `timestamp` (Fluent Bit is sending literal "$time" instead of actual timestamp).
        *   Environment variables (`CENTRAL_BRAIN_HOST`, `CENTRAL_BRAIN_PORT`, `CLUSTER_ID`, `API_KEY`) are not being correctly picked up by Fluent Bit from the system environment.
        *   Persistent `read error, check permissions` for `/var/lib/docker/containers/*/*.log`, despite running as root and setting host permissions/group ownership.
        *   `uuid` filter is not available in Fluent Bit v4.0.9.

2.  **Central Brain Connectivity & Permissions:**
    *   Resolved `AccessDeniedException` for `dynamodb:BatchWriteItem` on `ai-devops-platform-logs` by updating IAM policy.
    *   **Current Status:** Central Brain is receiving logs, but occasionally returns `HTTP status=500` with `ValidationException: Provided list of item keys contains duplicates`. This is likely due to Fluent Bit's timestamp/uniqueness issue.
    *   `TELEGRAM_BOT_TOKEN` remains unset (requires GitHub Secret configuration).

## 5. Next Steps

Here is the high-level roadmap we've defined for the project:

*   **Phase 1: Enhance Data Collection & Core Analytics**
    *   Integrate log and trace collection into the `edge-agent`.
    *   Develop more sophisticated anomaly detection models in the `central-brain`.
    *   Implement alert correlation and noise reduction.

*   **Phase 2: Introduce Automation & Remediation**
    *   Build a framework for defining and executing automated actions.
    *   Implement a few simple remediation tasks (e.g., restarting a service).
    *   Develop a basic ChatOps integration.

*   **Phase 3: Advanced AI/ML & Predictive Analytics**
    *   Develop models for root cause analysis and predictive analytics.
    *   Create a feedback loop for continuous learning.
    *   Build a user interface to visualize data, insights, and recommendations.

*   **Current Session Focus:**
    *   **Fluent Bit:** Investigate and resolve the `timestamp` parsing and environment variable propagation issues. Address the persistent log file permission error.
    *   **Central Brain:** Debug the `ValidationException` (duplicate keys) once Fluent Bit's timestamp issue is resolved.
    *   **Infrastructure:** Ensure `TELEGRAM_BOT_TOKEN` is correctly configured in GitHub Secrets and applied via Terraform.
