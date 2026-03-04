"""
Complete SDLC Workflow Guide
==============================

This document explains how the automated SDLC agent system works.
"""

# WORKFLOW OVERVIEW
# =================
# 
# 1. Developer adds a task to Excel file
# 2. Task Watcher detects the new task (pending status)
# 3. Auto-triggers SDLC Orchestrator
# 4. Agents run sequentially:
#    - Planner: Breaks down requirements
#    - Architect: Designs solution
#    - Developer: Writes code
#    - Tester: Generates & runs tests
#    - Debugger: Fixes any issues
# 5. All changes committed to feature branch
# 6. Pull Request created on GitHub
# 7. Human reviewer approves/requests changes
# 8. Once merged, task marked complete
#
# ============================================


# GETTING STARTED
# ===============

# 1. Setup
#    cd SDLC-AGENT
#    pip install -r requirements.txt
#    cp .env.example .env
#    # Edit .env with your API keys


# 2. Configure Environment Variables
#    
#    GITHUB_TOKEN=ghp_xxxx...     # Get from https://github.com/settings/tokens
#    GITHUB_REPO=your/repo-name   # Where to create PRs
#    OPENAI_API_KEY=sk-xxxx...    # Or use ANTHROPIC, WAIP, LOCAL_LLM
#    LLM_PROVIDER=openai          # mock | openai | anthropic | waip | local


# 3. Start Task Watcher (Auto-trigger mode)
#    python task_watcher.py
#    
#    This will:
#    - Monitor tasks/development_tasks.xlsx every 5 seconds
#    - Detect new tasks with "pending" status
#    - Auto-trigger workflow
#    - Update task status as it progresses


# 4. Add a Task to Excel
#    
#    | Task ID | Title | Description | Status | Assigned To | Created Date |
#    |---------|-------|-------------|--------|-------------|--------------|
#    | TASK-001| Add API endpoint | Create POST /users endpoint | pending | Backend | 2026-03-04 |
#    
#    Save the file → Task Watcher detects it → Workflow starts!


# ============================================
# WORKFLOW PHASES
# ============================================

# 1. PLANNING PHASE
# -----------------
# Planner Agent analyses the task description and breaks it down:
# 
# Input:  "Add pagination to user list API"
# Output: 
#   - Subtask 1: Modify API endpoint to accept page/limit params
#   - Subtask 2: Implement pagination logic in database query
#   - Subtask 3: Update API documentation
#   - Subtask 4: Write unit tests for pagination


# 2. ARCHITECTURE PHASE
# ---------------------
# Architect Agent designs the solution:
# 
# Input: Subtasks from planner
# Output:
#   - Files to modify: backend/app.py, backend/models.py
#   - Design patterns: Repository pattern for data access
#   - Database query optimization
#   - API response structure


# 3. DEVELOPMENT PHASE
# --------------------
# Developer Agent writes the actual code:
# 
# - Modifies backend/app.py to add pagination
# - Updates models to support pagination
# - Adds pagination logic to queries
# - Updates API documentation


# 4. TESTING PHASE
# ----------------
# Tester Agent generates and runs tests:
# 
# - Generates unit tests for pagination
# - Generates integration tests for API
# - Records test results
# - Identifies any failures


# 5. DEBUG PHASE (if needed)
# --------------------------
# Debug Agent fixes any issues:
# 
# - Analyzes test failures
# - Fixes bugs in code
# - Re-runs tests
# - Validates fixes


# ============================================
# GIT & PR CREATION
# ============================================

# After all phases complete:
# 
# 1. Creates feature branch: feature/TASK-001-add-pagination
# 2. Commits all changes with messages:
#    - "feat: Add pagination parameters to API"
#    - "feat: Implement pagination logic"
#    - "test: Add pagination unit tests"
# 3. Pushes branch to GitHub
# 4. Creates Pull Request automatically:
#    - Title: "[TASK-001] Add pagination to user list API"
#    - Description: Links task, lists changes, test results
#    - Assigns to code reviewer


# ============================================
# HUMAN REVIEW & APPROVAL
# ============================================

# 1. Human reviewer gets notified
# 2. Reviews code changes
# 3. Can approve or request changes
#    
#    If approved:
#    - Task Watcher detects PR merged
#    - Updates task status to "completed"
#    - Workflow ends ✓
#    
#    If changes requested:
#    - Agents receive feedback
#    - Make necessary modifications
#    - Update PR with new commits


# ============================================
# COMMAND REFERENCE
# ============================================

"""
# Mode 1: Watch Mode (Auto-trigger)
python task_watcher.py
→ Automatically detects new pending tasks
→ Runs workflow for each new task


# Mode 2: Process Single Task
python run_sdlc.py --task TASK-001
→ Processes one specific task manually


# Mode 3: Check Status
python run_sdlc.py --status
→ Shows status of all tasks


# Mode 4: Web Interface
python web_app.py
→ Open http://localhost:5000
→ Upload files
→ Enter goal
→ Generate code


# Mode 5: Main Orchestrator
python main.py "Build a REST API for user management"
→ One-off project
→ No task tracking
→ Direct goal input
"""


# ============================================
# EXAMPLE WORKFLOW
# ============================================

"""
Time: 9:00 AM

1. Developer adds task to Excel:
   TASK-001 | Add user search API | ... | pending

2. Task Watcher detects at 9:00:05

3. Workflow starts:
   
   [Planner] Analyzing: "Add user search API"
   ✓ Subtasks created
   
   [Architect] Designing solution
   ✓ Files identified: app.py, models.py
   
   [Developer] Writing code
   ✓ Added search endpoint
   ✓ Added database filter logic
   
   [Tester] Running tests
   ✓ All 12 tests passed
   
   [Debugger] Final checks
   ✓ No issues found

4. GitHub Actions:
   ✓ Branch created: feature/TASK-001-add-search
   ✓ Code committed
   ✓ Branch pushed
   ✓ PR #42 created

5. 9:15 AM - PR Created
   [Backend Team] receives notification
   
6. 9:45 AM - Code Review Complete
   [Sarah] Approves PR
   PR merged to main
   
7. Task Watcher detects merge
   ✓ Task status → "completed"
   
[WORKFLOW COMPLETE] ✓
"""


# ============================================
# CONFIGURATION OPTIONS
# ============================================

"""
.env Configuration
==================

# LLM Provider
LLM_PROVIDER=openai           # mock | openai | anthropic | waip | local

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# WAIP (Internal)
WAIP_API_KEY=token|...
WAIP_API_ENDPOINT=https://api.waip.wiprocms.com
WAIP_MODEL=gpt-4o

# Local LLM (Ollama)
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=codellama

# GitHub
GITHUB_TOKEN=ghp_...          # GitHub personal access token
GITHUB_REPO=username/repo     # Target repository

# System
OUTPUT_DIR=./output           # Where to save generated code
DEBUG_MODE=false              # Verbose logging
MAX_ITERATIONS=10             # Max workflow iterations
"""


# ============================================
# TROUBLESHOOTING
# ============================================

"""
Q: Task Watcher not detecting new tasks?
A: 
  1. Check file is saved (Excel auto-closes)
  2. Task status must be "pending"
  3. Check file path is correct
  4. Verify Excel file format (XLSX)

Q: PR not being created?
A:
  1. Verify GITHUB_TOKEN in .env
  2. Check token has repo access
  3. Verify GITHUB_REPO is correct
  4. Check GitHub API rate limits

Q: LLM provider not working?
A:
  1. Verify API key in .env
  2. Check internet connection
  3. Try mock provider for testing
  4. Review agent logs

Q: Generated code has bugs?
A:
  1. Debug Agent runs automatically
  2. Check test output for details
  3. Review code in PR before merging
  4. Provide feedback for improvement
"""
