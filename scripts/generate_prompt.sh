#!/bin/bash

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"
TASKS_FILE="$SCRIPT_DIR/../tasks.tsv"

# Defaults
AGENT=""
ROLE=""
REQUIREMENTS=""
N_AGENTS="2" # Default to 2 agents

# Helper
usage() {
    echo "Usage: ./generate_prompt.sh --agent {NAME} --role {executor|reviewer|planner} [--requirements {PATH}] [--n-agents {INT}]"
    echo "Example: ./generate_prompt.sh --agent agent_1 --role executor"
    echo "Example: ./generate_prompt.sh --agent planner --role planner --requirements requirements.md --n-agents 3"
    exit 1
}

# Parse Args
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --agent) AGENT="$2"; shift ;;
        --role) ROLE="$2"; shift ;;
        --requirements) REQUIREMENTS="$2"; shift ;;
        --n-agents) N_AGENTS="$2"; shift ;;
        *) echo "Unknown: $1"; usage ;;
    esac
    shift
done

if [ -z "$AGENT" ] || [ -z "$ROLE" ]; then
    usage
fi

# Select Template
if [ "$ROLE" == "executor" ]; then
    TEMPLATE_FILE="$TEMPLATES_DIR/executor_prompt.md"
elif [ "$ROLE" == "reviewer" ]; then
    TEMPLATE_FILE="$TEMPLATES_DIR/reviewer_prompt.md"
elif [ "$ROLE" == "planner" ]; then
    TEMPLATE_FILE="$TEMPLATES_DIR/planner_prompt.md"
    if [ -z "$REQUIREMENTS" ]; then
        echo "Error: --requirements {PATH} is required for planner role."
        exit 1
    fi
    # Ensure requirements path is absolute
    if [[ "$REQUIREMENTS" != /* ]]; then
        REQUIREMENTS="$(pwd)/$REQUIREMENTS"
    fi
else
    echo "Error: Role must be 'executor', 'reviewer', or 'planner'."
    exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template not found at $TEMPLATE_FILE"
    exit 1
fi

# Read and Replace
# Using python for safe replacement handling
export TEMPLATE_FILE
export AGENT
export SCRIPT_DIR
export TASKS_FILE
export REQUIREMENTS
export N_AGENTS

# Header
echo "----------------------------------------------------------------"
echo "COPY THE PROMPT BELOW AND PASTE IT INTO THE AGENT'S CHAT WINDOW"
echo "----------------------------------------------------------------"

python3 -c "
import os
import sys

try:
    with open(os.environ['TEMPLATE_FILE'], 'r') as f:
        content = f.read()

    # Common replacements
    content = content.replace('{{AGENT_NAME}}', os.environ['AGENT'])
    content = content.replace('{{SCRIPTS_PATH}}', os.environ['SCRIPT_DIR'])
    content = content.replace('{{TASKS_FILE}}', os.environ['TASKS_FILE'])
    
    # Planner specific
    if os.environ.get('REQUIREMENTS'):
        content = content.replace('{{REQUIREMENTS_PATH}}', os.environ['REQUIREMENTS'])
    
    if os.environ.get('N_AGENTS'):
        content = content.replace('{{AGENTS_COUNT}}', os.environ['N_AGENTS'])

    print(content)
except Exception as e:
    sys.stderr.write(f'Error generating prompt: {e}\n')
    sys.exit(1)
"
