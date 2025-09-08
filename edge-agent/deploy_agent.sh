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

# Run the fluent-bit container
echo "Running the latest fluent-bit container......"
docker run -d \
  --name fluent-bit \
  --restart unless-stopped \
  -v /var/log:/var/log:ro \
  -v /var/lib/docker/containers:/var/lib/docker/containers:ro \
  -e CLUSTER_ID=$(grep CLUSTER_ID /home/saleh/ai-devops-platform/edge-agent/config.env | cut -d '=' -f2) \
  -e API_KEY=$(grep API_KEY /home/saleh/ai-devops-platform/edge-agent/config.env | cut -d '=' -f2) \
  salehahmed325/fluent-bit:latest

# Run the agent container
echo "Running the latest edge-agent container......"
docker run -d \
  --name edge-agent \
  --restart unless-stopped \
  -p 8080:8080 \
  -e TZ=Asia/Dhaka \
  --env-file /home/saleh/ai-devops-platform/edge-agent/config.env \
  --add-host=central-brain:172.17.0.1 \
  salehahmed325/edge-agent:latest

# Check the container statuses
echo "Checking container statuses......"
docker ps -a | grep -e edge-agent -e fluent-bit
