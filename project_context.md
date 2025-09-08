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