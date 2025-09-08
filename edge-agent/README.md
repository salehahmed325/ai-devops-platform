# Edge Agent

The `edge-agent` is a lightweight, containerized agent responsible for collecting metrics from a local Prometheus instance and forwarding them to the `central-brain` for analysis.

## Features

*   **Metric Collection**: Scrapes a Prometheus server to gather all available time series data.
*   **Secure Forwarding**: Sends the collected data to the `central-brain`'s secure `/ingest` endpoint.
*   **Health Checks**: Provides a `/health` endpoint to confirm the agent is running correctly.

## Deployment

The `edge-agent` is deployed as a Docker container on the server you wish to monitor.

### Prerequisites

*   Docker must be installed on the host machine.
*   A Prometheus instance must be running and accessible from the host.
*   You must have the `CENTRAL_API_URL` and `API_KEY` from your `central-brain` deployment.

### Running the Agent

1.  **Create a `config.env` file:**
    Create a file named `config.env` with the following content, replacing the placeholder values:

    ```env
    # The public URL of your central-brain service
    CENTRAL_API_URL=https://your-alb-url.us-east-1.elb.amazonaws.com

    # The secret API key for your central-brain
    API_KEY=your_secret_api_key

    # The URL for the local Prometheus instance
    # Use host.docker.internal to connect to a service running on the host
    PROMETHEUS_URL=http://host.docker.internal:9090

    # A unique identifier for the cluster or server being monitored
    CLUSTER_ID=my-production-server-1

    # Optional: Set the log level (e.g., INFO, DEBUG)
    LOG_LEVEL=INFO
    ```

2.  **Run the Docker container:**
    Execute the following `docker run` command. This command will:
    *   Run the container in detached mode (`-d`).
    *   Add the necessary host mapping for connecting to the host's Prometheus service.
    *   Give the container a name (`edge-agent`).
    *   Ensure it restarts automatically.
    *   Load the environment variables from your `config.env` file.
    *   Use the latest pre-built image from Docker Hub.

    ```bash
    docker run -d \
      --add-host=host.docker.internal:host-gateway \
      --name edge-agent \
      --restart unless-stopped \
      --env-file config.env \
      salehahmed325/edge-agent:latest
    ```

### Verifying the Agent

You can check the agent's logs to ensure it is running correctly:

```bash
docker logs -f edge-agent
```

You should see logs indicating that it is collecting metrics and successfully sending them to the `central-brain`.

Triggering CI/CD.