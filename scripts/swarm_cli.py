#!/usr/bin/env python3
import os
import sys
import subprocess
import csv
import argparse

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(SCRIPT_DIR, "../tasks.tsv")

# Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def print_header():
    os.system('clear')
    print(f"{Colors.BOLD}{Colors.CYAN}🤖 Multi-Agent Swarm CLI{Colors.ENDC}")
    print(f"{Colors.CYAN}──────────────────────────────────────────{Colors.ENDC}")

def get_agents_from_tsv():
    agents = set()
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    if row.get('assigned_agent'):
                        agents.add(row['assigned_agent'])
        except Exception:
            pass
    return sorted(list(agents))

def get_task_ids_from_tsv():
    tasks = []
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    tasks.append((row['task_id'], row['task_name'], row['status']))
        except Exception:
            pass
    return tasks

def run_script(script_name, args=[]):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    cmd = [script_path] + args
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print(f"{Colors.FAIL}Error: Script {script_name} not found.{Colors.ENDC}")

def menu_generate_prompt():
    print(f"\n{Colors.BOLD}Generate Agent Prompt{Colors.ENDC}")
    print("1. Planner (Architect)")
    print("2. Executor (Developer)")
    print("3. Reviewer (QA)")
    print("0. Back")
    
    choice = input(f"\n{Colors.GREEN}Select Role > {Colors.ENDC}")
    
    role = ""
    if choice == '1': role = "planner"
    elif choice == '2': role = "executor"
    elif choice == '3': role = "reviewer"
    elif choice == '0': return
    else: return

    agent_name = ""
    if role == "planner":
        agent_name = "planner"
        req_path = input(f"Path to requirements.md (default: requirements.md) > ") or "requirements.md"
        n_agents = input(f"Number of agents [2] > ") or "2"
        run_script("generate_prompt.sh", ["--agent", agent_name, "--role", role, "--requirements", req_path, "--n-agents", n_agents])
    else:
        # Suggest agents
        known_agents = get_agents_from_tsv()
        agent_name = ""
        
        if known_agents:
            print(f"\n{Colors.DIM}Caught agents in TSV:{Colors.ENDC}")
            for i, ag in enumerate(known_agents):
                print(f"{i+1}. {ag}")
            print("0. Custom/New Agent")
            
            ag_choice = input(f"\n{Colors.GREEN}Select Agent > {Colors.ENDC}")
            if ag_choice == '0':
                agent_name = input(f"Agent Name (e.g., agent_1) > ")
            elif ag_choice.isdigit():
                idx = int(ag_choice) - 1
                if 0 <= idx < len(known_agents):
                    agent_name = known_agents[idx]
                else:
                    print(f"{Colors.FAIL}Invalid selection.{Colors.ENDC}")
                    return
        else:
            agent_name = input(f"Agent Name (e.g., agent_1) > ")
        if not agent_name:
            print(f"{Colors.FAIL}Agent name required.{Colors.ENDC}")
            return
            
        run_script("generate_prompt.sh", ["--agent", agent_name, "--role", role])
    
    input(f"\n{Colors.DIM}Press Enter to continue...{Colors.ENDC}")

def menu_show_progress():
    print(f"\n{Colors.BOLD}Show Progress{Colors.ENDC}")
    verbose = input(f"Verbose mode? (y/N) > ").lower() == 'y'
    args = ["--verbose"] if verbose else []
    run_script("show_progress.sh", args)
    input(f"\n{Colors.DIM}Press Enter to continue...{Colors.ENDC}")

def menu_toggle_pause():
    print(f"\n{Colors.BOLD}Toggle Pause{Colors.ENDC}")
    print("1. Pause All Agents")
    print("2. Resume All Agents")
    print("0. Back")
    choice = input(f"\n{Colors.GREEN}Select Action > {Colors.ENDC}")
    
    if choice == '0':
        return
    
    if choice == '1':
        run_script("toggle_pause.sh", ["on"])
    elif choice == '2':
        run_script("toggle_pause.sh", ["off"])
    
    # Show status after toggle
    run_script("show_progress.sh")
    input(f"\n{Colors.DIM}Press Enter to continue...{Colors.ENDC}")

def menu_update_status():
    print(f"\n{Colors.BOLD}Manual Task Update{Colors.ENDC}")
    
    tasks = get_task_ids_from_tsv()
    if not tasks:
        print(f"{Colors.WARNING}No tasks found in TSV.{Colors.ENDC}")
        return

    print(f"\n{Colors.DIM}Caught tasks in TSV:{Colors.ENDC}")
    # Pagination or just scroll? For CLI let's list them.
    for i, (t_id, t_name, t_stat) in enumerate(tasks):
        # Color status
        stat_color = Colors.ENDC
        if t_stat == "done": stat_color = Colors.GREEN
        elif t_stat == "in_progress": stat_color = Colors.WARNING
        elif t_stat == "to_do": stat_color = Colors.DIM
        
        print(f"{i+1}. [{t_id}] {t_name} ({stat_color}{t_stat}{Colors.ENDC})")
    print("0. Back")
    
    t_choice = input(f"\n{Colors.GREEN}Select Task # > {Colors.ENDC}")
    if t_choice == '0':
        return
    if not t_choice.isdigit():
        print(f"{Colors.FAIL}Invalid number.{Colors.ENDC}")
        return
        
    idx = int(t_choice) - 1
    if not (0 <= idx < len(tasks)):
        print(f"{Colors.FAIL}Selection out of range.{Colors.ENDC}")
        return

    task_id = tasks[idx][0]
    task_name = tasks[idx][1]
    current_status = tasks[idx][2]
    
    print(f"{Colors.BLUE}Selected: [{task_id}] {task_name} (Current: {current_status}){Colors.ENDC}")

    print("\nSelect New Status:")
    print("1. to_do")
    print("2. in_progress")
    print("3. in_review")
    print("4. address_review_feedback")
    print("5. done")
    print("0. Back")
    
    s_choice = input(f"\n{Colors.GREEN}Status > {Colors.ENDC}")
    if s_choice == '0': return

    status_map = {
        '1': 'to_do', '2': 'in_progress', '3': 'in_review',
        '4': 'address_review_feedback', '5': 'done'
    }
    
    new_status = status_map.get(s_choice)
    if new_status:
        run_script("update_task_status.sh", [task_id, new_status])
        print(f"{Colors.GREEN}Updated!{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}Invalid status.{Colors.ENDC}")
        
    input(f"\n{Colors.DIM}Press Enter to continue...{Colors.ENDC}")

def main():
    while True:
        print_header()
        print("1. 🗣️  Generate Agent Prompt  (Setup)")
        print("2. 📊 Show Progress          (Monitor)")
        print("3. ⏸️  Toggle Pause/Resume    (Control)")
        print("4. ✏️  Update Task Status     (Manage)")
        print("q. Quit")
        
        choice = input(f"\n{Colors.GREEN}Option > {Colors.ENDC}")
        
        if choice == '1': menu_generate_prompt()
        elif choice == '2': menu_show_progress()
        elif choice == '3': menu_toggle_pause()
        elif choice == '4': menu_update_status()
        elif choice.lower() == 'q':
            print("Bye!")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
