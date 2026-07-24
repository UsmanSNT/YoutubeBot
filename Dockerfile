# Use official Python image
FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash bot

# Install uv package manager
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy source code
COPY . .

# Install dependencies and the package from pyproject.toml
RUN uv pip install --system --no-cache-dir -e .

# Create directories for data and set permissions
RUN mkdir -p /app/data /app/data/temp /app/logs && \
    chown -R bot:bot /app

# Switch to non-root user
USER bot

# Configure environment variables
ENV DATA_DIR=/app/data
ENV TEMP_DIR=/app/data/temp
ENV DB_PATH=/app/data/bot.db

# Configure volumes for persistent data
VOLUME ["/app/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.append('/app'); import bot.config; print('OK')" || exit 1

# Default command
CMD ["python", "run.py"]
