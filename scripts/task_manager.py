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
    """Finds and returns the next task for the agent with smart responses."""
    file_path = args.file
    agent_name = args.agent
    role = args.role

    lock_fd = acquire_lock(file_path)
    try:
        rows = read_tsv(file_path)
        
        if not rows:
            print("NO_TASKS_EXIST: The task file is empty. Wait for the Planner to generate tasks.")
            return
        
        # Helper to check dependency
        def is_dependency_met(dep_id, all_rows):
            if not dep_id:
                return True
            for r in all_rows:
                if r['task_id'] == dep_id:
                    return r['status'] == STATUS_DONE
            return False
        
        def get_blocking_task(dep_id, all_rows):
            """Returns info about the blocking task."""
            for r in all_rows:
                if r['task_id'] == dep_id:
                    return r
            return None

        candidate_task = None
        my_tasks = []
        blocked_tasks = []
        paused_detected = False
        feedback_tasks = []

        if role == 'executor':
            # Collect all tasks assigned to this agent
            for row in rows:
                if row['assigned_agent'] != agent_name:
                    continue
                my_tasks.append(row)
                
                # Check for pause
                if row['action_state'] == ACTION_PAUSED:
                    paused_detected = True
                
                # Check for feedback tasks
                if row['status'] == STATUS_FEEDBACK:
                    feedback_tasks.append(row)
            
            # If paused, respond immediately
            if paused_detected:
                print("PAUSED: System is paused. Wait 1 minute before polling again.")
                return
            
            # Now find a candidate
            for row in my_tasks:
                if row['status'] in [STATUS_TODO, STATUS_FEEDBACK]:
                    if is_dependency_met(row['dependency_task'], rows):
                        candidate_task = row
                        break
                    else:
                        blocked_tasks.append(row)
        
        elif role == 'reviewer':
            # Reviewer looks for 'in_review' tasks (any, not assigned)
            for row in rows:
                if row['action_state'] == ACTION_PAUSED:
                    paused_detected = True
                    
                if row['status'] == STATUS_IN_REVIEW:
                    if row['action_state'] != ACTION_PAUSED:
                        candidate_task = row
                        break
            
            if paused_detected and not candidate_task:
                print("PAUSED: System is paused. Wait 1 minute before polling again.")
                return

        # --- Output Decision ---
        if candidate_task:
            # Check if it's a feedback task
            is_feedback = candidate_task['status'] == STATUS_FEEDBACK
            
            print("TASK_FOUND")
            print(f"TASK_ID: {candidate_task['task_id']}")
            print(f"STATUS: {candidate_task['status']}")
            print(f"CONTEXT_FILE: {candidate_task['context_file']}")
            print(f"DESCRIPTION: {candidate_task['description']}")
            
            if is_feedback:
                print("-" * 20)
                print("⚠️  ATTENTION: This task has review feedback that needs to be addressed.")
                print("Read the feedback comments in the context file before making changes.")
            
            print("-" * 20)
            print(f"INSTRUCTION: To start, run: ./scripts/task_manager.py update-status --file {file_path} --task-id {candidate_task['task_id']} --status in_progress")
        
        elif role == 'executor':
            # No candidate found - determine why
            all_done = all(t['status'] == STATUS_DONE for t in my_tasks) if my_tasks else False
            
            if not my_tasks:
                print("NO_ASSIGNMENT: No tasks are assigned to you. Wait for the Planner to assign tasks or check your agent name.")
            elif all_done:
                print("ALL_DONE: 🎉 All your assigned tasks are complete! You can stop polling.")
            elif blocked_tasks:
                blocker = blocked_tasks[0]
                blocking_task = get_blocking_task(blocker['dependency_task'], rows)
                if blocking_task:
                    print(f"BLOCKED: Task [{blocker['task_id']}] is waiting on [{blocking_task['task_id']}] (status: {blocking_task['status']}, assigned to: {blocking_task['assigned_agent']}).")
                else:
                    print(f"BLOCKED: Task [{blocker['task_id']}] is waiting on dependency [{blocker['dependency_task']}].")
                print("Wait 1 minute before polling again.")
            else:
                # Edge case: tasks exist but in other states (e.g., in_progress, in_review)
                in_progress = [t for t in my_tasks if t['status'] == STATUS_IN_PROGRESS]
                if in_progress:
                    print(f"IN_PROGRESS: You have task [{in_progress[0]['task_id']}] still in progress. Complete it before fetching a new one.")
                else:
                    print("WAIT: No actionable tasks at this moment. Wait 1 minute before polling again.")
        
        elif role == 'reviewer':
            # No tasks in_review
            in_review_count = sum(1 for r in rows if r['status'] == STATUS_IN_REVIEW)
            if in_review_count == 0:
                all_done = all(r['status'] == STATUS_DONE for r in rows)
                if all_done:
                    print("ALL_DONE: 🎉 All tasks are complete! You can stop polling.")
                else:
                    print("NO_REVIEWS: No tasks are currently awaiting review. Wait 1 minute before polling again.")
            else:
                print("WAIT: Reviews exist but may be paused. Wait 1 minute before polling again.")

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
