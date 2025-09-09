#!/bin/bash

# Stop running agent and fluent-bit containers
echo "Stopping the edge-agent and fluent-bit containers......"
docker stop edge-agent fluent-bit

# Remove the agent and fluent-bit containers
echo "Removing the edge-agent and fluent-bit containers......"
docker rm edge-agent fluent-bit

# Pull latest container images
echo "Pulling the latest container images......"
docker pull salehahmed325/edge-agent:latest
docker pull salehahmed325/fluent-bit:latest

#!/bin/bash

# Stop running agent containers
echo "Stopping the edge-agent container......"
docker stop edge-agent

# Remove the agent containers
echo "Removing the edge-agent container......"
docker rm edge-agent

# Pull latest container images
echo "Pulling the latest container images......"
docker pull salehahmed325/edge-agent:latest

# Run the agent container
echo "Running the latest edge-agent container......"
docker run -d --name edge-agent --restart unless-stopped -p 8080:8080 -e TZ=Asia/Dhaka --env-file /home/saleh/ai-devops-platform/edge-agent/config.env -v /var/run/docker.sock:/var/run/docker.sock --group-add 119 salehahmed325/edge-agent:latest

# Check the container statuses
echo "Checking container statuses......"
docker ps -a | grep -e edge-agent

# Run the agent container
echo "Running the latest edge-agent container......"
docker run -d --name edge-agent --restart unless-stopped -p 8080:8080 -e TZ=Asia/Dhaka --env-file /home/saleh/ai-devops-platform/edge-agent/config.env -v /var/run/docker.sock:/var/run/docker.sock --group-add 119 salehahmed325/edge-agent:latest

# Check the container statuses
echo "Checking container statuses......"
docker ps -a | grep -e edge-agent -e fluent-bit