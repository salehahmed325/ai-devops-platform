# Central Brain Service

## Purpose
The Central Brain service is the core analytical component of the AI DevOps Platform. It is responsible for:
- Ingesting metric and Kubernetes state data from Edge Agents.
- Performing real-time anomaly detection on the ingested data.
- Storing processed data persistently in a DynamoDB table for historical analysis and future machine learning model training.
- Providing an API endpoint for data ingestion and potentially for querying processed data (future work).
- Sending real-time alerts for detected anomalies to configured channels (e.g., Telegram).

## How it Works
1.  **Data Ingestion**: Edge Agents deployed in various clusters send metric and Kubernetes state data to the `/ingest` endpoint of the Central Brain.
2.  **Data Processing**: Upon receiving data, the Central Brain performs the following:
    *   **Data Transformation**: Converts incoming data, specifically handling float-to-Decimal conversion for compatibility with DynamoDB.
    *   **Persistent Storage**: Stores the transformed data in an AWS DynamoDB table (`ai-devops-platform-data` by default) for long-term storage and retrieval.
    *   **Anomaly Detection**: Applies a simple Isolation Forest model to detect anomalies in key metrics (e.g., the `up` metric).
    *   **Alerting**: Retrieves alert configurations (e.g., Telegram chat IDs) from a dedicated DynamoDB table (`ai-devops-platform-alert-configs`) and sends real-time notifications for detected anomalies to the specified channels.
3.  **Scalability**: The service is deployed as an AWS ECS Fargate service, allowing it to scale automatically based on demand.