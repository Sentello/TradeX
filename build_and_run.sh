#!/bin/bash

set -e

CONTAINER_NAME="tradex_container"
DOCKER_COMPOSE_FILE="docker-compose.yml"

echo "🚀 Stopping and removing old container..."
docker-compose -f $DOCKER_COMPOSE_FILE down || true

echo "🔨 Building new Docker image without cache..."
docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache

echo "🚢 Starting new container..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

echo "📜 Showing logs for 10 seconds..."
timeout 10 docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
