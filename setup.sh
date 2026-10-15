#!/bin/bash
cd "$(dirname "$0")"

# Check python
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "Error: Python 3 is not installed or not in PATH."
    exit 1
fi

"$PY" setup.py "$@"
