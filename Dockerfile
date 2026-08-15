# Matches the Python version used for local development (.venv is 3.14), so
# the container cannot diverge from what the tests actually run against.
# 3.10 was previously used and reaches end of life in October 2026; every
# pinned dependency already required >=3.10, leaving no headroom.
FROM python:3.14-slim

# Set the working directory inside the container
WORKDIR /app

# System dependencies. curl is needed by the HEALTHCHECK below, which the
# slim image does not ship.
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies before copying the source, so editing code
# does not invalidate the (slow) dependency layer on every rebuild.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files to the container.
# .env is deliberately NOT copied: it is excluded in .dockerignore and
# supplied at runtime via docker-compose's env_file. Baking it in would
# leave the API keys in the image layers permanently.
COPY . /app

# Copy the Supervisor configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports for Flask applications
EXPOSE 5000 5005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:5000/login >/dev/null && \
      curl -sf http://localhost:5005/health >/dev/null || exit 1

# Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
