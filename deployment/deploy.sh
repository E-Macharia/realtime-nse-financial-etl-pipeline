#!/bin/bash
# DevOps Deployment Script for NSE Financial ETL Pipeline

# Configuration
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="nse-pipeline"

echo "=================================================="
echo "🚢 Initiating Idempotent DevOps Deployment..."
echo "=================================================="

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "🚨 Error: docker-compose.yml not found in the current directory!"
    exit 1
fi

# 1. Stop previous containers (clean cleanup of active networks and instances)
echo "Stopping any previously running container services..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down --remove-orphans

# 2. Build changed services and start in detached mode
echo "Rebuilding and starting services (only changed layers will build)..."
# Using --build ensures that any code updates are re-compiled
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --build

# 3. List active container statuses to verify deployment success
echo "Deployment initiated. Current container list:"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps

echo "=================================================="
echo "✅ Deployment script executed successfully."
echo "=================================================="
exit 0
