#!/bin/bash
# Wrapper for update-task-status using the Python backend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/task_manager.py"
TASKS_FILE="$SCRIPT_DIR/../tasks.tsv"

# Defaults
TASK_ID=""
STATUS=""
FILE="$TASKS_FILE"

# Parse args
# Expected usage: ./update_task_status.sh {TASK_ID} {STATUS} [--file {PATH}]
# Validating positional arguments first for simplicity in Agent prompt

if [ "$#" -lt 2 ]; then
    echo "Usage: ./update_task_status.sh {TASK_ID} {STATUS} [--file {PATH}]"
    exit 1
fi

TASK_ID="$1"
STATUS="$2"
shift 2

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --file) FILE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

python3 "$PYTHON_SCRIPT" update-status --file "$FILE" --task-id "$TASK_ID" --status "$STATUS"
