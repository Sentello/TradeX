#!/bin/bash

CONTAINER_NAME="tradex_container"
DOCKER_COMPOSE_FILE="docker-compose.yml"

log_message() {
    local MESSAGE="$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $MESSAGE"
}

log_message "🚀 Stopping and removing old container..."
docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans || true

log_message "🧹 Cleaning up unused Docker resources..."
docker system prune -f > /dev/null 2>&1 || true

log_message "🔨 Building new Docker image without cache..."
docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache

log_message "🚢 Starting new container..."
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

log_message "📜 Showing logs for 10 seconds..."
timeout 10 docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f

log_message "✅ Build process completed successfully!"
