# Multi-Agent Software Development Team

A Python framework that simulates a software engineering team using multiple AI agents. Each agent has a specialized role and collaborates through a shared task system to build software projects.

## 🚀 SDLC Agentic Workflow (NEW!)

This system automates the entire Software Development Lifecycle:

```text
📋 Task Added → 🤖 Agents Run → 💻 Code Generated → 📝 PR Created → 👤 Human Review → ✅ Merged
```

### Workflow Diagram

```text
                         ┌─────────────────────────────────────────┐
                         │         SDLC ORCHESTRATOR               │
                         │                                         │
    Excel/JSON ────────▶ │  📋 Task Monitor (Auto-Trigger)         │
    (New Task)           │         │                               │
                         │         ▼                               │
                         │  ┌─────────────┐                        │
                         │  │   Planner   │ Break down requirements│
                         │  └──────┬──────┘                        │
                         │         ▼                               │
                         │  ┌─────────────┐                        │
                         │  │  Architect  │ Design architecture    │
                         │  └──────┬──────┘                        │
                         │         ▼                               │
                         │  ┌─────────────┐                        │
                         │  │  Developer  │ Write code             │
                         │  └──────┬──────┘                        │
                         │         ▼                               │
                         │  ┌─────────────┐                        │
                         │  │   Tester    │ Generate tests         │
                         │  └──────┬──────┘                        │
                         │         ▼                               │
                         │  ┌─────────────┐                        │
                         │  │  Git Commit │ Branch, commit, push   │
                         │  └──────┬──────┘                        │
                         │         ▼                               │
                         │  ┌─────────────┐                        │
                         │  │  Create PR  │ GitHub Pull Request    │
                         │  └─────────────┘                        │
                         │                                         │
                         └─────────────────────────────────────────┘
                                        │
                                        ▼
                              👤 Human Reviews PR
                                        │
                                        ▼
                              ✅ Merge & Complete
```

## Installation

```bash
cd multi-agent-dev-team

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Initialize Tasks
```bash
python run_sdlc.py --init
```

### 2. View Task Status
```bash
python run_sdlc.py --status
```

### 3. Process a Task
```bash
python run_sdlc.py --task TASK-001
```

### 4. Watch Mode (Auto-Trigger)
```bash
python run_sdlc.py --watch
```

## Configuration

Edit `.env` with your settings:
```env
# LLM Provider (waip, openai, anthropic, local, mock)
LLM_PROVIDER=waip
WAIP_API_KEY=your-api-key
WAIP_API_ENDPOINT=https://api.waip.wiprocms.com

# Task tracking
TASKS_FILE=tasks/development_tasks.xlsx

# GitHub (for PR creation)
GITHUB_TOKEN=your-github-token
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo-name
```

## Task Management (Excel)

Tasks are managed in `tasks/development_tasks.xlsx`:

| Task ID | Title | Description | Type | Priority | Status | Component |
|---------|-------|-------------|------|----------|--------|-----------|
| TASK-001 | Add auth | Implement JWT auth | feature | high | new | backend |
| TASK-002 | Dashboard | Build dashboard | feature | medium | new | frontend |

### Task Status Flow
```
new → in_progress → development_complete → pr_created → pr_review → merged → completed
```

## AI Agents

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **Planner** | Product Manager | Analyzes requirements, creates task breakdown |
| **Architect** | Software Architect | Designs system, chooses tech stack |
| **Developer** | Software Developer | Implements backend and frontend code |
| **Tester** | QA Engineer | Generates tests, validates code |
| **Debugger** | Bug Fixer | Analyzes errors, proposes fixes |

## Project Structure

```
multi-agent-dev-team/
├── run_sdlc.py              # 🚀 Main SDLC runner
├── sdlc_orchestrator.py     # SDLC workflow orchestrator
├── main.py                  # Original agent runner
├── config.py                # Configuration
├── .env                     # Your settings
│
├── agents/                  # AI Agents
│   ├── planner_agent.py
│   ├── architect_agent.py
│   ├── developer_agent.py
│   ├── tester_agent.py
│   └── debug_agent.py
│
├── core/                    # Core modules
│   ├── llm_client.py        # LLM providers (WAIP, OpenAI, etc.)
│   ├── task_tracker.py      # Excel/JSON task management
│   ├── git_integration.py   # Git operations & GitHub PR
│   ├── file_watcher.py      # Auto-trigger on file changes
│   └── memory.py            # Shared memory
│
├── tasks/                   # Task tracking
│   └── development_tasks.xlsx
│
├── workspace/               # Git repository workspace
│
└── output/                  # Agent output files
```

## Commands Reference

```bash
# SDLC Workflow Commands
python run_sdlc.py --init          # Initialize sample tasks
python run_sdlc.py --status        # View task status
python run_sdlc.py --task TASK-001 # Process single task
python run_sdlc.py --watch         # Auto-trigger on new tasks
python run_sdlc.py --add           # Add task interactively

# Original Mode (Simple)
python main.py "Build an API" --provider waip
```

## LLM Providers

| Provider | Variables |
|----------|-----------|
| **WAIP** | `WAIP_API_KEY`, `WAIP_API_ENDPOINT`, `WAIP_MODEL` |
| **OpenAI** | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| **Anthropic** | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| **Local (Ollama)** | `LOCAL_LLM_URL`, `LOCAL_LLM_MODEL` |

## License

MIT
