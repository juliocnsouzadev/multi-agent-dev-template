#!/usr/bin/env bash

# Colors
# Checks if stdout is a terminal to use colors, otherwise empty.
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    CYAN='\033[0;36m'
    WHITE='\033[0;37m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
    DIM='\033[2m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    MAGENTA=''
    CYAN=''
    WHITE=''
    BOLD=''
    NC=''
    DIM=''
fi

# File path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TSV_FILE="$SCRIPT_DIR/../tasks.tsv"
VERBOSE=0

if [ "$1" == "--verbose" ] || [ "$1" == "-v" ]; then
    VERBOSE=1
fi


# Check if file exists
if [ ! -f "$TSV_FILE" ]; then
    printf "${RED}Error: $TSV_FILE not found!${NC}\n"
    exit 1
fi

# Function to clean text (remove \r for CRLF compatibility)
clean_tsv() {
    # Remove \r characters, skip header (tail -n +2 is handled in logic usually, but here we clean whole stream)
    # Actually, let's keep it simple: tr -d '\r'
    tr -d '\r' < "$TSV_FILE"
}

# Check logic
task_count=$(clean_tsv | tail -n +2 | wc -l | tr -d ' ')
if [ "$task_count" -eq 0 ]; then
    printf "${YELLOW}No tasks found in $TSV_FILE${NC}\n"
    printf "${WHITE}Add tasks to the TSV file to track progress.${NC}\n"
    exit 0
fi

# Get stats
total_tasks=$task_count
done_tasks=$(clean_tsv | tail -n +2 | awk -F'\t' '$7 == "done" {count++} END {print count+0}')
to_do_tasks=$(clean_tsv | tail -n +2 | awk -F'\t' '$7 == "to_do" {count++} END {print count+0}')
in_progress_tasks=$(clean_tsv | tail -n +2 | awk -F'\t' '$7 == "in_progress" {count++} END {print count+0}')
in_review_tasks=$(clean_tsv | tail -n +2 | awk -F'\t' '$7 == "in_review" {count++} END {print count+0}')
address_feedback_tasks=$(clean_tsv | tail -n +2 | awk -F'\t' '$7 == "address_review_feedback" {count++} END {print count+0}')
paused_tasks=$(clean_tsv | tail -n +2 | awk -F'\t' '{gsub(/^[ \t]+|[ \t]+$/, "", $10); if ($10 == "paused") count++} END {print count+0}')

# Check for GLOBAL PAUSE (if all or most are paused)
# We simply check if there is at least one paused task, but usually it's all or nothing via toggle_pause.sh
is_system_paused=0
if [ "$paused_tasks" -eq "$total_tasks" ] && [ "$total_tasks" -gt 0 ]; then
    is_system_paused=1
fi

percentage=$((done_tasks * 100 / total_tasks))

# --- UI Functions ---

draw_bar() {
    local pct=$1
    local width=40
    local filled=$((pct * width / 100))
    local empty=$((width - filled))
    
    printf "  ${WHITE}["
    printf "${GREEN}"
    for ((i=0; i<filled; i++)); do printf "━"; done
    printf "${DIM}"
    for ((i=0; i<empty; i++)); do printf "━"; done
    printf "${WHITE}] ${BOLD}${pct}%%${NC}"
}

print_header() {
    clear
    printf "${BOLD}${BLUE}🤖 Multi-Agent Swarm Monitor${NC}\n"
    if [ "$is_system_paused" -eq 1 ]; then
        printf "${WHITE}Status: ${RED}⏸️  SYSTEM PAUSED${NC}\n"
    else
        printf "${WHITE}Status: ${GREEN}▶️  ACTIVE${NC}\n"
    fi
    printf "\n"
}

print_summary() {
    draw_bar $percentage
    printf "\n\n"
    printf "  ${GREEN}✅ Done: $done_tasks${NC}  ${YELLOW}⚡ In Progress: $in_progress_tasks${NC}  ${CYAN}👀 Review: $in_review_tasks${NC}  ${MAGENTA}🔧 Fix: $address_feedback_tasks${NC}  ${DIM}📝 Todo: $to_do_tasks${NC}\n"
    printf "\n"
}

# --- Main Render ---

print_header
print_summary

printf "${BOLD}${WHITE}📦 Milestone Progress${NC}\n"
printf "${DIM}────────────────────────────────────────────────────────${NC}\n"

# Group by milestone
milestones=$(clean_tsv | tail -n +2 | awk -F'\t' '{print $2}' | sort -u | sort -t. -k1,1n -k2,2n)

for ms in $milestones; do
    # Get stats for this milestone
    ms_total=$(clean_tsv | tail -n +2 | awk -F'\t' -v m="$ms" '$2==m {c++} END {print c+0}')
    ms_done=$(clean_tsv | tail -n +2 | awk -F'\t' -v m="$ms" '$2==m && $7=="done" {c++} END {print c+0}')
    ms_prog=$(clean_tsv | tail -n +2 | awk -F'\t' -v m="$ms" '$2==m && $7=="in_progress" {c++} END {print c+0}')
    
    # Calculate pct
    ms_pct=0
    if [ "$ms_total" -gt 0 ]; then
        ms_pct=$((ms_done * 100 / ms_total))
    fi

    # Determine Icon
    icon="${DIM}○${NC}"
    if [ "$ms_pct" -eq 100 ]; then icon="${GREEN}●${NC}"; 
    elif [ "$ms_prog" -gt 0 ]; then icon="${YELLOW}◐${NC}"; 
    elif [ "$ms_done" -gt 0 ]; then icon="${CYAN}◔${NC}"; fi
    
    printf "  %b  ${BOLD}%-5s${NC} " "$icon" "$ms"
    
    # Mini bar
    mb_width=20
    mb_filled=$((ms_pct * mb_width / 100))
    mb_empty=$((mb_width - mb_filled))
    printf "${DIM}"
    for ((i=0; i<mb_filled; i++)); do printf "━"; done
    printf "${DIM}"
    for ((i=0; i<mb_empty; i++)); do printf "─"; done
    printf "${NC} ${ms_pct}%%  (${ms_done}/${ms_total})\n"
done
printf "\n"

# Show Paused Tasks
paused_list=$(clean_tsv | tail -n +2 | awk -F'\t' '{gsub(/^[ \t]+|[ \t]+$/, "", $10); if ($10=="paused") print $8"\t"$3"\t"$4}')
if [ -n "$paused_list" ]; then
    printf "${BOLD}${RED}⏸️  Paused Tasks${NC}\n"
    printf "${DIM}────────────────────────────────────────────────────────${NC}\n"
    echo "$paused_list" | while IFS=$'\t' read -r agent tid name; do
         printf "  %b [${RED}%s${NC}] %s ${DIM}(assigned: %s)${NC}\n" "⛔" "$tid" "$name" "$agent"
    done
    printf "\n"
fi

# Show Active Work info
if [ "$in_progress_tasks" -gt 0 ]; then
    printf "${BOLD}${YELLOW}⚡ Active Agents${NC}\n"
    printf "${DIM}────────────────────────────────────────────────────────${NC}\n"
    # Filter for in_progress
    clean_tsv | tail -n +2 | awk -F'\t' '$7=="in_progress" {print $8"\t"$3"\t"$4}' | while IFS=$'\t' read -r agent tid name; do
        printf "  %b %-12s ${WHITE}→${NC} [${CYAN}%s${NC}] %s\n" "🤖" "$agent" "$tid" "$name"
    done
    printf "\n"
fi

# Show Blocked or Needs Attention
if [ "$address_feedback_tasks" -gt 0 ]; then
    printf "${BOLD}${MAGENTA}🔧 Needs Attention${NC}\n"
    clean_tsv | tail -n +2 | awk -F'\t' '$7=="address_review_feedback" {print $8"\t"$3"\t"$4}' | while IFS=$'\t' read -r agent tid name; do
        printf "  %b %-12s ${WHITE}→${NC} [${MAGENTA}%s${NC}] %s\n" "⚠️" "$agent" "$tid" "$name"
    done
    printf "\n"
fi

# Show Review Queue
if [ "$in_review_tasks" -gt 0 ]; then
     printf "${BOLD}${CYAN}👀 Ready for Review${NC}\n"
      clean_tsv | tail -n +2 | awk -F'\t' '$7=="in_review" {print $8"\t"$3"\t"$4}' | while IFS=$'\t' read -r agent tid name; do
        printf "  %b [${CYAN}%s${NC}] %s ${DIM}(by %s)${NC}\n" "🔎" "$tid" "$name" "$agent"
    done
    printf "\n"
fi

# Verbose Mode Lists
if [ "$VERBOSE" -eq 1 ]; then
    # Last DONE tasks
    if [ "$done_tasks" -gt 0 ]; then
        printf "${BOLD}${GREEN}✅ Recently Completed${NC}\n"
        # Print last 5 done tasks
        clean_tsv | tail -n +2 | awk -F'\t' '$7=="done" {print $8"\t"$3"\t"$4}' | tail -n 5 | while IFS=$'\t' read -r agent tid name; do
             printf "  %b [${GREEN}%s${NC}] %s ${DIM}(by %s)${NC}\n" "✓" "$tid" "$name" "$agent"
        done
        printf "\n"
    fi

    # Up Next (Todo)
    if [ "$to_do_tasks" -gt 0 ]; then
        printf "${BOLD}${WHITE}📝 Up Next (Top 5)${NC}\n"
        clean_tsv | tail -n +2 | awk -F'\t' '$7=="to_do" {print $8"\t"$3"\t"$4}' | head -n 5 | while IFS=$'\t' read -r agent tid name; do
             printf "  %b [${DIM}%s${NC}] %s ${DIM}(assigned: %s)${NC}\n" "○" "$tid" "$name" "$agent"
        done
        printf "\n"
    fi
else
    printf "${DIM}Tip: Use --verbose to see Todo/Done lists.${NC}\n"
fi


printf "${DIM}Last updated: $(date '+%H:%M:%S')${NC}\n"
