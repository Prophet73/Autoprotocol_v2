# WhisperX Transcription Service
# Based on pre-built whisperX image with all dependencies

FROM ghcr.io/jim60105/whisperx:no_model

# Switch to root for installation
USER root

# Install additional system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# IMPORTANT: Use /opt/whisperx instead of /app to avoid base image's VOLUME /app
# The base image declares VOLUME /app which creates anonymous volumes that
# shadow new code with old data on container restarts.
WORKDIR /opt/whisperx

# Install pip first (not included in base image)
RUN curl -sSL https://bootstrap.pypa.io/get-pip.py | /venv/bin/python

# Install our additional Python dependencies
COPY docker/requirements-extra.txt .
RUN /venv/bin/python -m pip install --no-cache-dir -r requirements-extra.txt

# Copy application code
COPY backend/ /opt/whisperx/backend/

# Create data directories
RUN mkdir -p /data/uploads /data/output /data/models /data/db && \
    chmod -R 777 /data

# Set environment variables
ENV STORAGE_PATH=/data/storage
ENV HF_HOME=/data/models
ENV PYTHONPATH=/opt/whisperx

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Override entrypoint and run API server
ENTRYPOINT []
CMD ["/venv/bin/python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Note: Base image's VOLUME /app still exists but is now unused.
# Our code lives in /opt/whisperx, so anonymous volumes won't affect it.
