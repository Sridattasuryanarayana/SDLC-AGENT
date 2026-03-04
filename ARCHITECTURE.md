# SDLC Agent - System Architecture

## 📊 Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SDLC AGENT SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT LAYER                                                                 │
│  ──────────────────────────────────────────────────────────────────────     │
│                                                                              │
│  📋 Excel Tasks           🌐 Web Interface          💡 API Calls            │
│  (development_tasks      (http://localhost:5000)   (REST API)              │
│   .xlsx)                                                                     │
│       │                           │                       │                 │
│       ├─────────────────┬─────────┴──────────────────┬────┤                │
│       │                 │                             │    │                │
│       ▼                 ▼                             ▼    ▼                │
│  ┌────────────────────────────────────────────────────────┐                │
│  │         FILE WATCHER & TASK TRACKER                    │                │
│  │  (core/file_watcher.py)  (core/task_tracker.py)       │                │
│  │  - Monitors Excel (every 30 sec)                       │                │
│  │  - Detects "pending" status                            │                │
│  │  - Extracts task requirements                          │                │
│  └────────────┬─────────────────────────────────────────┘                │
│               │                                                             │
│               ▼                                                             │
│  ┌────────────────────────────────────────────────────────┐                │
│  │         ORCHESTRATOR LAYER                             │                │
│  │  (orchestrator.py / sdlc_orchestrator.py)             │                │
│  │  - Creates task queue                                  │                │
│  │  - Manages agent execution                             │                │
│  │  - Shared memory for context                           │                │
│  └────┬────────────────────────────────────┬──────────┬──┘                │
│       │                                    │          │                    │
│       ▼                                    ▼          ▼                    │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│  │              │   │              │   │              │                   │
│  │   AGENT 1    │   │   AGENT 2    │   │   AGENT 3    │   ...            │
│  │              │   │              │   │              │                   │
│  │  PLANNER     │   │  ARCHITECT   │   │  DEVELOPER   │                   │
│  │              │   │              │   │              │                   │
│  │ ┌──────────┐ │   │ ┌──────────┐ │   │ ┌──────────┐ │                   │
│  │ │ Analyze  │ │   │ │ Design   │ │   │ │  Write   │ │                   │
│  │ │ Reqmts   │ │   │ │ Arch     │ │   │ │  Code    │ │                   │
│  │ │ Break    │ │   │ │ Identify │ │   │ │ Backend  │ │                   │
│  │ │ Down     │ │   │ │ Files    │ │   │ │ Frontend │ │                   │
│  │ │ Tasks    │ │   │ │ to Change│ │   │ │ Tests    │ │                   │
│  │ └──────────┘ │   │ └──────────┘ │   │ └──────────┘ │                   │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                   │
│         │                  │                   │                           │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                   │
│  │              │   │              │   │              │                   │
│  │ AGENT 4      │   │ AGENT 5      │   │  LLM LAYER   │                   │
│  │              │   │              │   │              │                   │
│  │ TESTER       │   │ DEBUGGER     │   │ ┌──────────┐ │                   │
│  │              │   │              │   │ │ OpenAI   │ │                   │
│  │ ┌──────────┐ │   │ ┌──────────┐ │   │ │ Anthropic│ │                   │
│  │ │Generate  │ │   │ │ Analyze  │ │   │ │ WAIP     │ │                   │
│  │ │ Tests    │ │   │ │ Errors   │ │   │ │ Local    │ │                   │
│  │ │ Run      │ │   │ │ Fix      │ │   │ │ Mock     │ │                   │
│  │ │ Validate │ │   │ │ Re-test  │ │   │ └──────────┘ │                   │
│  │ └──────────┘ │   │ └──────────┘ │   │              │                   │
│  └──────┬───────┘   └──────┬───────┘   └──────────────┘                   │
│         │                  │                                               │
│         └──────────────┬───┘                                               │
│                        ▼                                                    │
│  ┌────────────────────────────────────────────────────────┐                │
│  │         SHARED MEMORY LAYER                            │                │
│  │  (core/memory.py)                                      │                │
│  │  - Stores agent outputs                                │                │
│  │  - Project requirements                                │                │
│  │  - Generated code & tests                              │                │
│  │  - Architecture decisions                              │                │
│  └────┬──────────────────────────────────────┬───────────┘                │
│       │                                      │                             │
│       ▼                                      ▼                             │
│  ┌──────────────────┐          ┌───────────────────────────┐               │
│  │  CODE OUTPUT     │          │   GIT INTEGRATION         │               │
│  │                  │          │                           │               │
│  │ output/          │          │ (core/git_integration.py) │               │
│  │ ├─ app.py        │          │                           │               │
│  │ ├─ routes.py     │          │ ┌─────────────────────┐   │               │
│  │ ├─ frontend.js   │          │ │ Create branch       │   │               │
│  │ ├─ tests.py      │          │ │ feature/TASK-XXX    │   │               │
│  │ └─ docs.md       │          │ └─────────────────────┘   │               │
│  └──────────┬───────┘          │                           │               │
│             │                  │ ┌─────────────────────┐   │               │
│             │                  │ │ git add .           │   │               │
│             │                  │ │ git commit -m       │   │               │
│             │                  │ │ git push origin     │   │               │
│             │                  │ └─────────────────────┘   │               │
│             │                  │                           │               │
│             │                  │ ┌─────────────────────┐   │               │
│             │                  │ │ Create GitHub PR    │   │               │
│             │                  │ │ Monitor PR status   │   │               │
│             │                  │ │ Detect approval     │   │               │
│             │                  │ │ Auto-merge on ok    │   │               │
│             │                  │ └─────────────────────┘   │               │
│             │                  └─────────────┬─────────────┘               │
│             │                                │                             │
│             └───────────────────────┬────────┘                             │
│                                     ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │         WORKSPACE (Your Code)                           │               │
│  │                                                          │               │
│  │  workspace/                                             │               │
│  │  ├─ backend/                                            │               │
│  │  │  ├─ app.py (UPDATED)                                 │               │
│  │  │  └─ routes.py (UPDATED)                              │               │
│  │  │                                                      │               │
│  │  ├─ frontend/                                           │               │
│  │  │  └─ src/components/ (UPDATED)                        │               │
│  │  │                                                      │               │
│  │  └─ tests/ (NEW)                                        │               │
│  │     └─ test_new_feature.py                              │               │
│  └────────────────┬──────────────────────────────────────┘               │
│                   │                                                       │
│                   ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │         GITHUB / GIT REPOSITORY                         │               │
│  │                                                          │               │
│  │  main branch                                            │               │
│  │  ├─ feature/TASK-001 (PR #123)                          │               │
│  │  │  └─ [🔄 Under Review] → [✅ Approved] → [Merged]    │               │
│  │  │                                                      │               │
│  │  └─ feature/TASK-002 (PR #124)                          │               │
│  │     └─ [⏳ Waiting for approval...]                      │               │
│  └────────────────┬──────────────────────────────────────┘               │
│                   │                                                       │
│                   ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │         TASK TRACKING (Excel)                           │               │
│  │                                                          │               │
│  │  tasks/development_tasks.xlsx                          │               │
│  │  ├─ TASK-001: status = "completed" ✅                   │               │
│  │  ├─ TASK-002: status = "in_progress" 🔄                │               │
│  │  ├─ TASK-003: status = "pending" ⏳                     │               │
│  │  └─ TASK-004: status = "pending" ⏳                     │               │
│  └─────────────────────────────────────────────────────────┘               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

```
Task Added to Excel
        ↓
File Watcher detects (every 30s)
        ↓
Task Tracker loads requirements
        ↓
Orchestrator creates task queue
        ↓
PLANNER AGENT processes
  └─ Output → Memory: Requirements breakdown
        ↓
ARCHITECT AGENT processes
  └─ Output → Memory: System design
        ↓
DEVELOPER AGENT processes
  └─ Output → Memory: Generated code
        ↓
TESTER AGENT processes
  └─ Output → Memory: Test code
        ↓
DEBUGGER AGENT processes
  └─ Output → Memory: Bug fixes (if needed)
        ↓
Git Integration
  ├─ Creates feature branch
  ├─ Commits code changes
  ├─ Pushes to GitHub
  └─ Creates Pull Request
        ↓
System monitors GitHub
  ├─ Waits for human review
  ├─ Human approves PR
  └─ Triggers auto-merge
        ↓
Excel updated
  └─ Task status: pending → completed
        ↓
Ready for next task!
```

---

## 🗂️ File Structure Detail

```
SDLC-AGENT/
│
├── 📊 TASK TRACKING
│   └── tasks/
│       └── development_tasks.xlsx
│           ├─ Column A: Task ID (TASK-001, TASK-002, ...)
│           ├─ Column B: Title (Feature name)
│           ├─ Column C: Description (Requirements)
│           ├─ Column D: Status (pending → in_progress → completed)
│           ├─ Column E: Priority (High/Medium/Low)
│           ├─ Column F: Assigned To (Developer/Frontend)
│           ├─ Column G: Created Date
│           └─ Column H: Updated Date
│
├── 🤖 ORCHESTRATION
│   ├── orchestrator.py
│   │   ├─ class Orchestrator
│   │   ├─ def run(goal)
│   │   ├─ def _execute_phase(agents)
│   │   └─ def _finalize()
│   │
│   ├── sdlc_orchestrator.py
│   │   ├─ class SDLCOrchestrator
│   │   ├─ def process_task(task)
│   │   ├─ def create_pr()
│   │   └─ def monitor_pr()
│   │
│   └── core/
│       ├── file_watcher.py
│       │   ├─ def watch_excel() - Monitors for changes
│       │   └─ def detect_new_tasks() - Finds pending tasks
│       │
│       ├── task_tracker.py
│       │   ├─ class TaskTracker
│       │   ├─ def load_from_excel()
│       │   ├─ def update_status()
│       │   └─ def save_to_excel()
│       │
│       ├── git_integration.py
│       │   ├─ def create_branch()
│       │   ├─ def commit_code()
│       │   ├─ def create_pr()
│       │   ├─ def monitor_pr_approval()
│       │   └─ def auto_merge()
│       │
│       ├── llm_client.py
│       │   ├─ class LLMClient
│       │   ├─ def call_ollm(prompt) - Calls OpenAI/Anthropic/etc
│       │   └─ def parse_response()
│       │
│       ├── memory.py
│       │   ├─ class SharedMemory
│       │   ├─ def store(type, content)
│       │   ├─ def get_by_type(type)
│       │   └─ def export_to_json()
│       │
│       └── task_queue.py
│           ├─ class Task
│           └─ class TaskQueue
│
├── 🧠 AI AGENTS
│   └── agents/
│       ├── base_agent.py
│       │   └─ class BaseAgent
│       │      ├─ llm_client
│       │      ├─ memory
│       │      └─ def execute()
│       │
│       ├── planner_agent.py
│       │   └─ class PlannerAgent(BaseAgent)
│       │      ├─ def analyze_requirements()
│       │      ├─ def create_task_breakdown()
│       │      └─ Outputs: Requirements objects → Memory
│       │
│       ├── architect_agent.py
│       │   └─ class ArchitectAgent(BaseAgent)
│       │      ├─ def design_architecture()
│       │      ├─ def identify_modifications()
│       │      └─ Outputs: Design documents → Memory
│       │
│       ├── developer_agent.py
│       │   └─ class DeveloperAgent(BaseAgent)
│       │      ├─ def implement_code()
│       │      ├─ def write_code_section()
│       │      └─ Outputs: Code files → Memory + output/
│       │
│       ├── tester_agent.py
│       │   └─ class TesterAgent(BaseAgent)
│       │      ├─ def generate_tests()
│       │      ├─ def run_tests()
│       │      └─ Outputs: Test files → Memory + output/
│       │
│       └── debug_agent.py
│           └─ class DebugAgent(BaseAgent)
│              ├─ def analyze_errors()
│              ├─ def fix_issues()
│              └─ Recursively calls Developer & Tester
│
├── 💾 CODE REPOSITORY
│   └── workspace/
│       ├── backend/
│       │   ├── app.py (Flask/FastAPI main app)
│       │   ├── routes.py (API endpoints)
│       │   ├── models.py (Database models)
│       │   ├── __init__.py
│       │   └── requirements.txt
│       │
│       ├── frontend/
│       │   ├── src/
│       │   │   ├── App.js (Main React component)
│       │   │   ├── index.js
│       │   │   ├── components/
│       │   │   │   ├── UserList.js
│       │   │   │   ├── Pagination.js
│       │   │   │   └── ... more components
│       │   │   └── styles.css
│       │   │
│       │   ├── public/
│       │   │   └── index.html
│       │   │
│       │   └── package.json
│       │
│       └── tests/ (Auto-generated)
│           ├── test_api.py
│           ├── test_pagination.py
│           └── test_frontend.js
│
├── 📤 OUTPUT
│   └── output/
│       └── run_YYYYMMDD_HHMMSS/
│           ├── backend_updates.py
│           ├── frontend_updates.js
│           ├── test_code.py
│           ├── CHANGES.md
│           └── summary.json
│
├── 🌐 WEB INTERFACE
│   ├── web_app.py (Flask server)
│   └── templates/
│       └── index.html (Web UI)
│
├── 🚀 ENTRY POINTS
│   ├── main.py (Alternative orchestrator)
│   ├── run_sdlc.py (CLI interface with --watch, --task, etc)
│   └── config.py (Configuration settings)
│
└── 📚 DOCUMENTATION
    ├── README.md (Main docs)
    ├── QUICK_START.md (This file)
    ├── .env.example (Environment template)
    └── .gitignore
```

---

## 🔌 API Endpoints (web_app.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Main web interface |
| `/upload` | POST | Upload requirement files |
| `/run` | POST | Execute agent workflow |
| `/jobs` | GET | List all runs |
| `/job/<id>` | GET | Get specific run details |
| `/output` | GET | List all output files |

### Example: POST /run

```json
Request:
{
  "goal": "Add pagination to user list API",
  "provider": "mock"
}

Response:
{
  "success": true,
  "job_id": "20260304_185331",
  "files": [
    {
      "name": "backend_pagination.py",
      "content": "...",
      "size": 2547
    }
  ],
  "summary": {
    "goal": "Add pagination to user list API",
    "files_generated": 3,
    "architecture": "REST API with pagination support",
    "timestamp": "2026-03-04T18:53:31"
  }
}
```

---

## 🎯 Complete Example: From Task to Deployed

### Input: New Excel Row
```
TASK-001 | Add User Pagination | Paginate the user list endpoint | pending | High | Developer
```

### Processing: Agents Work
```
Step 1: Planner
  Input: "Add pagination...
  Output: 
    - Need to modify POST /users endpoint
    - Add limit & offset parameters
    - Update response schema
    
Step 2: Architect
  Input: [Planner output]
  Output:
    - Modify: workspace/backend/routes.py
    - Modify: workspace/frontend/components/UserList.js
    - Create: workspace/tests/test_pagination.py
    
Step 3: Developer
  Input: [Architect design]
  Output: (Actual Code)
    routes.py:
      @app.route('/users')
      def get_users():
          page = request.args.get('page', 1, int)
          limit = request.args.get('limit', 10, int)
          offset = (page - 1) * limit
          users = User.query.offset(offset).limit(limit).all()
          return {...}
    
    UserList.js:
      const [page, setPage] = useState(1);
      useEffect(() => {
          fetch(`/api/users?page=${page}`)
          .then(r => r.json())
          .then(data => setUsers(data.users))
      }, [page])
    
Step 4: Tester
  Input: [Developer code]
  Output:
    test_pagination.py:
      def test_pagination_works():
          resp = client.get('/users?page=1&limit=5')
          assert len(resp.json['users']) <= 5
      
      def test_pagination_total():
          resp = client.get('/users')
          assert resp.json['total'] > 0
    
    ✅ All tests pass!
    
Step 5: Debug (if needed)
  Input: [Test results]
  Output: (if tests fail, fixes code automatically)
```

### Output: Generated Files
```
output/run_20260304_185331/
├── backend_routes_update.py (Code for routes.py)
├── frontend_userlist_update.js (Code for UserList.js)
├── test_pagination.py (Complete test file)
└── summary.json (Metadata)
```

### Git Integration
```
1. Create branch:
   git checkout -b feature/TASK-001-add-pagination

2. Apply code changes:
   cp output/backend_routes_update.py workspace/backend/routes.py
   cp output/frontend_userlist_update.js workspace/frontend/components/UserList.js
   cp output/test_pagination.py workspace/tests/

3. Commit:
   git add .
   git commit -m "feat(pagination): Add pagination to user list API"

4. Push:
   git push origin feature/TASK-001-add-pagination

5. Create PR #123 on GitHub with full description
```

### Human Review
```
GitHub shows:
- PR #123 open
- 3 files changed
- ✅ All tests passing
- Ready for review

Team lead:
- Reviews code ✅
- Approves ✅
```

### Auto-Merge
```
System detects approval:
1. git checkout main
2. git pull origin main
3. git merge --no-ff feature/TASK-001
4. git push origin main
5. Update Excel: TASK-001 → completed
```

### Result
```
Workspace now has pagination feature! 🎉

Next automatic iteration:
- TASK-002 detected as pending
- System triggers automatically
- Agents process TASK-002
- ... repeat ...
```

---

## 📌 Key Takeaways

1. **Everything is integrated** - Excel watches, agents process, Git creates PRs
2. **Fully automated** - From task addition to code generation
3. **Human in the loop** - Requires review before merge
4. **Track everything** - Excel spreadsheet keeps status
5. **Production ready** - Generates real, usable code
6. **Extensible** - Add more agents, modify prompts, customize workflow

---

**Ready to build something amazing? 🚀**
