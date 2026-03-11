#!/bin/bash
# Entrypoint script: fix ownership of mounted volumes, then drop to appuser.
# Solves "Permission Denied" when Docker named volumes are created with root:root.

set -e

# Fix ownership of data directories (mounted as named volumes)
chown -R appuser:appuser /data/uploads /data/output 2>/dev/null || true
chown appuser:appuser /data/models 2>/dev/null || true

# Drop privileges and exec the main process
exec gosu appuser "$@"
