#!/usr/bin/env bash
# Quick launcher for Project Cleaner
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/cleaner.py" "$@"
