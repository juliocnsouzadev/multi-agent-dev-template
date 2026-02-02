#!/bin/bash
# Wrapper for toggle-pause using the Python backend
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/task_manager.py"
TASKS_FILE="$SCRIPT_DIR/../tasks.tsv"

STATE=""
FILE="$TASKS_FILE"

# Usage: ./toggle_pause.sh {on|off} [--file {PATH}]
if [ "$#" -lt 1 ]; then
    echo "Usage: ./toggle_pause.sh {on|off} [--file {PATH}]"
    exit 1
fi

if [ "$1" == "on" ]; then
    STATE="paused"
elif [ "$1" == "off" ]; then
    STATE="active"
else
    echo "Invalid state only 'on' or 'off' allowed."
    exit 1
fi
shift

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --file) FILE="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

python3 "$PYTHON_SCRIPT" toggle-pause --file "$FILE" --state "$STATE"
