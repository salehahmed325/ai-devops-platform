# Central Brain Service

## Purpose
The Central Brain service is the core analytical component of the AI DevOps Platform. It is responsible for:
- Ingesting metric and Kubernetes state data from Edge Agents.
- Performing real-time anomaly detection on the ingested data.
- Storing processed data persistently in a DynamoDB table for historical analysis and future machine learning model training.
- Providing an API endpoint for data ingestion and potentially for querying processed data (future work).

## How it Works
1.  **Data Ingestion**: Edge Agents deployed in various clusters send metric and Kubernetes state data to the `/ingest` endpoint of the Central Brain.
2.  **Data Processing**: Upon receiving data, the Central Brain performs the following:
    *   **Data Transformation**: Converts incoming data, specifically handling float-to-Decimal conversion for compatibility with DynamoDB.
    *   **Persistent Storage**: Stores the transformed data in an AWS DynamoDB table (`ai-devops-platform-data` by default) for long-term storage and retrieval.
    *   **Anomaly Detection**: Applies a simple Isolation Forest model to detect anomalies in key metrics (e.g., the `up` metric).
3.  **Alerting (Future)**: Currently, detected anomalies are logged. In future iterations, this service will integrate with an alerting system to notify DevOps teams of potential issues.
4.  **Scalability**: The service is deployed as an AWS ECS Fargate service, allowing it to scale automatically based on demand.