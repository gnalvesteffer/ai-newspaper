#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
# Validate the server-side model configuration before starting the HTTP server.
python3 server.py --check-config "$@"
exec python3 server.py "$@"
