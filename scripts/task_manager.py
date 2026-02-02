#!/usr/bin/env python3
import argparse
import csv
import sys
import os
import fcntl
import time
from datetime import datetime

# Constants
STATUS_TODO = 'to_do'
STATUS_IN_PROGRESS = 'in_progress'
STATUS_IN_REVIEW = 'in_review'
STATUS_FEEDBACK = 'address_review_feedback'
STATUS_DONE = 'done'

ACTION_ACTIVE = 'active'
ACTION_PAUSED = 'paused'

# Columns based on plan:
# order, milestone_id, task_id, task_name, description, context_file, status, assigned_agent, dependency_task, action_state
COLUMNS = [
    'order', 'milestone_id', 'task_id', 'task_name', 'description', 
    'context_file', 'status', 'assigned_agent', 'dependency_task', 'action_state'
]

def read_tsv(file_path):
    """Reads the TSV file and returns a list of dictionaries."""
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        return list(reader)

def write_tsv(file_path, rows):
    """Writes the list of dictionaries to the TSV file."""
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

def acquire_lock(file_path):
    """Acquires a file lock for safe concurrent access."""
    lock_file = file_path + '.lock'
    lock_fd = open(lock_file, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return lock_fd
    except IOError:
        lock_fd.close()
        return None

def release_lock(lock_fd):
    """Releases the file lock."""
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()

def get_next_task(args):
    """Finds and returns the next task for the agent."""
    file_path = args.file
    agent_name = args.agent
    role = args.role

    lock_fd = acquire_lock(file_path)
    try:
        rows = read_tsv(file_path)
        
        # Helper to check dependency
        def is_dependency_met(dep_id, all_rows):
            if not dep_id:
                return True
            for r in all_rows:
                if r['task_id'] == dep_id:
                    return r['status'] == STATUS_DONE
            return False

        # 1. Global Pause Check
        # If ANY task is paused, we assume the system is paused (or we check the specific task)
        # The plan says "Check action_state: If 'paused', STOP".
        # We will check if the candidate task is paused.

        candidate_task = None

        if role == 'executor':
            # Priority: In Progress -> Address Feedback -> To Do
            # Actually, per plan: 
            # 1. assigned_agent == ME
            # 2. status IN [to_do, address_review_feedback]
            # 3. action_state == active
            # 4. dependency met
            
            # First, check if I already have something in progress (optional safety)
            # For now, let's just look for the next available.
            
            for row in rows:
                if row['assigned_agent'] != agent_name:
                    continue
                
                if row['action_state'] == ACTION_PAUSED:
                    # If my tasks are paused, I stop.
                    print("WAIT: System is paused.")
                    return

                if row['status'] in [STATUS_TODO, STATUS_FEEDBACK]:
                    if is_dependency_met(row['dependency_task'], rows):
                        candidate_task = row
                        break
        
        elif role == 'reviewer':
            # Reviewer looks for 'in_review'
            for row in rows:
                if row['status'] == STATUS_IN_REVIEW:
                    if row['action_state'] == ACTION_PAUSED:
                        print("WAIT: System is paused.")
                        return
                    
                    # Optional: Reviewer preference? For now, FIFO.
                    candidate_task = row
                    break

        if candidate_task:
            # Output format designed for the Agent to parse easily
            print("TASK_FOUND")
            print(f"TASK_ID: {candidate_task['task_id']}")
            print(f"STATUS: {candidate_task['status']}")
            print(f"CONTEXT_FILE: {candidate_task['context_file']}")
            print(f"DESCRIPTION: {candidate_task['description']}")
            print("-" * 20)
            print(f"INSTRUCTION: To start, run: ./scripts/task_manager.py update-status --file {file_path} --task-id {candidate_task['task_id']} --status in_progress")
        else:
            print("NO_TASK: No available tasks found.")

    finally:
        release_lock(lock_fd)

def update_status(args):
    """Updates the status of a specific task."""
    file_path = args.file
    task_id = args.task_id
    new_status = args.status

    if new_status not in [STATUS_TODO, STATUS_IN_PROGRESS, STATUS_IN_REVIEW, STATUS_FEEDBACK, STATUS_DONE]:
        print(f"ERROR: Invalid status '{new_status}'")
        sys.exit(1)

    lock_fd = acquire_lock(file_path)
    try:
        rows = read_tsv(file_path)
        updated = False
        
        for row in rows:
            if row['task_id'] == task_id:
                row['status'] = new_status
                updated = True
                break
        
        if updated:
            write_tsv(file_path, rows)
            print(f"SUCCESS: Task {task_id} updated to {new_status}")
        else:
            print(f"ERROR: Task {task_id} not found")
            sys.exit(1)

    finally:
        release_lock(lock_fd)

def toggle_pause(args):
    """Toggles the action_state for ALL tasks."""
    file_path = args.file
    new_state = args.state # active or paused

    lock_fd = acquire_lock(file_path)
    try:
        rows = read_tsv(file_path)
        for row in rows:
            row['action_state'] = new_state
        
        write_tsv(file_path, rows)
        print(f"SUCCESS: All tasks set to {new_state}")

    finally:
        release_lock(lock_fd)

def main():
    parser = argparse.ArgumentParser(description="Agent Task Manager")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Subcommand: get-next
    parser_get = subparsers.add_parser('get-next', help='Get next task for agent')
    parser_get.add_argument('--file', required=True, help='Path to tasks.tsv')
    parser_get.add_argument('--agent', required=True, help='Agent Name (e.g., agent_1)')
    parser_get.add_argument('--role', required=True, choices=['executor', 'reviewer'], help='Agent Role')

    # Subcommand: update-status
    parser_update = subparsers.add_parser('update-status', help='Update task status')
    parser_update.add_argument('--file', required=True, help='Path to tasks.tsv')
    parser_update.add_argument('--task-id', required=True, help='Task ID')
    parser_update.add_argument('--status', required=True, help='New Status')

    # Subcommand: toggle-pause
    parser_pause = subparsers.add_parser('toggle-pause', help='Pause/Resume all tasks')
    parser_pause.add_argument('--file', required=True, help='Path to tasks.tsv')
    parser_pause.add_argument('--state', required=True, choices=[ACTION_ACTIVE, ACTION_PAUSED], help='New State')

    args = parser.parse_args()

    if args.command == 'get-next':
        get_next_task(args)
    elif args.command == 'update-status':
        update_status(args)
    elif args.command == 'toggle-pause':
        toggle_pause(args)

if __name__ == "__main__":
    main()
