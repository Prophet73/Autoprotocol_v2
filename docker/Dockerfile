# WhisperX Transcription Service
# Based on pre-built whisperX image with all dependencies

FROM ghcr.io/jim60105/whisperx:no_model

# Switch to root for installation
USER root

# Install additional system dependencies (gosu for privilege de-escalation in entrypoint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
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

# Copy application code and scripts
COPY backend/ /opt/whisperx/backend/
COPY scripts/ /opt/whisperx/scripts/

# Copy and prepare entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user and data directories
RUN useradd -m -s /bin/bash -u 1000 appuser && \
    mkdir -p /data/uploads /data/output /data/models /data/db && \
    chown -R appuser:appuser /data && \
    chmod -R 750 /data && \
    chown -R appuser:appuser /opt/whisperx

# Lock pre-cached model files (base image) to read-only
# Prevents malicious model file replacement via unsafe torch.load deserialization
RUN find /root/.cache /home/appuser/.cache -type d -name "huggingface" -exec chmod -R 555 {} + 2>/dev/null || true

# Set environment variables
ENV STORAGE_PATH=/data/storage
ENV HF_HOME=/data/models
ENV TORCH_HOME=/data/models
ENV XDG_CACHE_HOME=/home/appuser/.cache
ENV PYTHONPATH=/opt/whisperx

# Expose port
EXPOSE 8000

# Stay as root — entrypoint.sh fixes volume permissions, then drops to appuser via gosu

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint fixes volume ownership, then execs CMD as appuser
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/venv/bin/python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Note: Base image's VOLUME /app still exists but is now unused.
# Our code lives in /opt/whisperx, so anonymous volumes won't affect it.
