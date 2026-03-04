# SDLC Agent - Quick Start Guide

## ✅ Everything is Already Set Up!

Your complete automated development system is ready to use.

---

## 📁 File Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| **Development Tasks** | `tasks/development_tasks.xlsx` | Track all development work |
| **Code Repository** | `workspace/` | Your backend + frontend code |
| **Backend Code** | `workspace/backend/` | Flask/FastAPI application |
| **Frontend Code** | `workspace/frontend/` | React application |
| **AI Agents** | `agents/` | 5 agents: Planner, Architect, Developer, Tester, Debugger |
| **Generated Output** | `output/` | Generated code & test results |
| **Web Interface** | `web_app.py` | Browser-based UI |

---

## 🚀 How to Start (3 Options)

### **Option 1: Web Interface (Easiest - Best for Testing)**

```powershell
cd SDLC-AGENT
python web_app.py
# Open browser: http://localhost:5000
```

**What to do:**
1. Enter your requirement (e.g., "Add pagination to user list")
2. Select provider: `Mock` (free testing)
3. Click `Generate Code`
4. View results with syntax highlighting
5. Download all files

**Best for:** Quick testing, demos, trying new features

---

### **Option 2: Auto-Trigger from Excel (Best for Production)**

```powershell
cd SDLC-AGENT
python run_sdlc.py --watch
```

**What to do:**
1. Open `tasks/development_tasks.xlsx`
2. Add new rows with:
   - Task ID: `TASK-XXX`
   - Title: Feature name
   - Description: Requirements
   - **Status: `pending`** ← This triggers automation!
   - Priority: `High/Medium`
   - Save file

**The system will:**
- Auto-detect the new task
- Run all 5 agents automatically
- Generate code
- Create PR on GitHub
- Update Excel when complete

**Best for:** Production use, continuous development

---

### **Option 3: Process Single Task**

```powershell
cd SDLC-AGENT
python run_sdlc.py --task TASK-001
```

**Best for:** Manual control, processing specific tasks

---

## 📋 Excel Tasks File

### **Location:**
```
SDLC-AGENT/tasks/development_tasks.xlsx
```

### **Current Tasks:**

| Task ID | Title | Description | Status |
|---------|-------|-------------|--------|
| TASK-001 | Add User Pagination | Add pagination to user list API endpoint | pending |
| TASK-002 | Implement Authentication | Add JWT authentication to all endpoints | pending |
| TASK-003 | Add User Search | Implement search functionality for users | pending |
| TASK-004 | Create User Dashboard | Build frontend dashboard component | pending |

### **How to Add New Task:**

1. **Open Excel:** `tasks/development_tasks.xlsx`
2. **Add new row:**
   ```
   TASK-005 | Add Email Verification | Send verification email | pending | High | Developer
   ```
3. **Save file** (Ctrl+S)
4. **System auto-detects** within 30 seconds
5. **Watch it work!**

---

## 💻 Code Repository Structure

### **Backend (workspace/backend/)**
```python
app.py              # Flask/FastAPI application
routes.py           # API endpoints
models.py           # Database models
requirements.txt    # Python dependencies
```

### **Frontend (workspace/frontend/)**
```javascript
src/App.js           # React main component
src/components/      # React components
src/styles.css       # Styling
package.json         # JS dependencies
```

### **Tests (workspace/tests/) - Auto-Generated**
```python
test_api.py          # Backend tests
test_pagination.py   # Feature-specific tests
```

---

## 🤖 How Automation Works

### **Complete Automated Workflow:**

```
1. Developer adds task to Excel
                ↓
2. System detects (every 30 secs)
                ↓
3. File Watcher triggers Orchestrator
                ↓
4. 5 Agents process sequentially:
   ├─ Planner: Break down requirements
   ├─ Architect: Design solution
   ├─ Developer: Write code
   ├─ Tester: Create & run tests
   └─ Debugger: Fix any issues
                ↓
5. Code generated to output/
                ↓
6. Git integration creates:
   ├─ Feature branch
   ├─ Commits code
   ├─ Pushes to GitHub
   └─ Creates Pull Request
                ↓
7. System waits for human approval
                ↓
8. PR merged → Task marked complete
                ↓
9. Excel updated: pending → completed
                ↓
10. Ready for next task!
```

---

## 🎯 Try It Now!

### **Fastest Way (Web Interface):**

```powershell
# Terminal 1: Start web server
cd SDLC-AGENT
python web_app.py

# Terminal 2: Open browser
http://localhost:5000
```

**Then:**
1. Type: "Create a simple calculator with add, subtract, multiply, divide functions"
2. Provider: Mock
3. Click: Generate Code
4. ✅ See generated code immediately!

### **Production Way (Excel Auto-Trigger):**

```powershell
# Terminal: Start watch mode
cd SDLC-AGENT
python run_sdlc.py --watch

# Meanwhile... add task to Excel
# File: tasks/development_tasks.xlsx
# Add row with status = "pending"
# System auto-triggers! 🚀
```

---

## 📊 Example: Add Pagination Feature

### **Step 1: Add to Excel**
```
TASK-001 | Add User Pagination | Add limit/offset to user list API | pending
```

### **Step 2: Save Excel**
Just press Ctrl+S

### **Step 3: Watch It Work**
```
✅ TASK-001 detected
✅ Planner analyzing requirements...
✅ Architect designing solution...
✅ Developer writing code...
✅ Tester creating tests...
✅ PR created: #123
⏳ Waiting for approval...

(You review & approve the PR on GitHub)

✅ PR merged
✅ TASK-001 marked complete!
```

### **Step 4: Generated Files**
```
output/run_20260304_XXXXXX/
├── backend_pagination_changes.py    (API code)
├── frontend_pagination_changes.js   (React code)
├── test_pagination.py               (Tests)
└── CHANGES_SUMMARY.md               (Documentation)
```

---

## 🔧 Configuration

### **For Real AI (OpenAI, Anthropic, etc.):**

1. **Copy template:**
   ```powershell
   copy .env.example .env
   ```

2. **Add your API key:**
   ```
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-...your-key...
   ```

3. **Use provider:**
   ```powershell
   # Web interface
   Select: OpenAI (instead of Mock)
   
   # Or watch mode - it auto-uses .env
   python run_sdlc.py --watch
   ```

### **For GitHub Integration:**

1. **Add GitHub token to .env:**
   ```
   GITHUB_TOKEN=ghp_...your-token...
   GITHUB_REPO=your-username/your-repo
   ```

2. **System will auto-create PRs!**

---

## 🎁 What You Get

| Feature | What It Does |
|---------|------------|
| **Auto Task Detection** | Monitors Excel for new tasks |
| **Code Generation** | AI writes backend + frontend code |
| **Test Creation** | Automatically creates & runs tests |
| **Git Integration** | Creates branches, commits, PRs |
| **Web Interface** | Easy browser-based access |
| **Output Files** | All generated code saved |
| **Task Tracking** | Excel spreadsheet status updates |
| **Human Review** | Requires human approval before merge |

---

## 📞 Support Commands

```powershell
# Check task status
python run_sdlc.py --status

# Process specific task
python run_sdlc.py --task TASK-001

# Initialize sample tasks
python run_sdlc.py --init

# Watch mode (continuous)
python run_sdlc.py --watch

# Web interface
python web_app.py
```

---

## 🚀 Next Steps

1. **Choose your method:**
   - Web UI for testing → `python web_app.py`
   - Excel auto-trigger for production → `python run_sdlc.py --watch`

2. **Add your first task** to Excel OR enter goal in web UI

3. **Watch the agents work!** 🤖

4. **Review generated code** and approve PR

5. **See results** - feature is automatically merged!

---

## 💡 Key Points

✅ **Everything is ready** - No additional setup needed
✅ **Excel-based task tracking** - Simple, familiar interface
✅ **Auto-trigger system** - Detects new tasks automatically
✅ **5 AI agents** - Work together like a real dev team
✅ **Code generation** - Produces production-ready code
✅ **Testing included** - Auto-generates comprehensive tests
✅ **GitHub integration** - Full PR workflow
✅ **Human in the loop** - Requires review before merge

---

## 🎯 Try Right Now!

```powershell
# Fastest start (2 commands):
cd SDLC-AGENT
python web_app.py

# Then open: http://localhost:5000
# And enter your requirements!
```

**Happy developing! 🚀**
