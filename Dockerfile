# Use Python 3.10 as the base image
FROM python:3.10

# Set the working directory inside the container
WORKDIR /app

# Copy the application files to the container
COPY . /app
COPY .env /app/.env

# Install system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
#RUN mkdir -p /var/log/supervisor /app/logs

# Set permissions for logs directory
#RUN chmod -R 777 /var/log/supervisor /app/logs

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Supervisor configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports for Flask applications
EXPOSE 5000 5005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:5000/login >/dev/null && \
      curl -s -o /dev/null -w "%{http_code}" http://localhost:5005/webhook | grep -qE '[2-4][0-9][0-9]' || exit 1

# Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
