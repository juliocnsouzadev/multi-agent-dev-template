#!/bin/bash
# Wrapper for get-next-task using the Python backend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/task_manager.py"
TASKS_FILE="$SCRIPT_DIR/../tasks.tsv"

# Defaults
AGENT=""
ROLE=""
FILE="$TASKS_FILE"

# Parse args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --agent) AGENT="$2"; shift ;;
        --role) ROLE="$2"; shift ;;
        --file) FILE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

if [ -z "$AGENT" ] || [ -z "$ROLE" ]; then
    echo "Usage: ./get_next_task.sh --agent {NAME} --role {executor|reviewer} [--file {PATH}]"
    exit 1
fi

python3 "$PYTHON_SCRIPT" get-next --file "$FILE" --agent "$AGENT" --role "$ROLE"
