# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary system packages
RUN apt-get update && apt-get install -y \
    supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /app/logs /var/log/supervisor

# Copy application files and .env
COPY . /app
COPY .env /app/.env

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set permissions for logs directory
RUN chmod -R 777 /app/logs

# Expose the ports for the Flask apps
EXPOSE 5000
EXPOSE 5005

# Add a health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -sf http://localhost:5000 && curl -sf http://localhost:5005 || exit 1

# Default command to start supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

