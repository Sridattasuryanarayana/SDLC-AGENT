"""
SDLC Orchestrator - Complete Software Development Lifecycle Automation.

This orchestrator manages the entire development workflow:
1. Monitor for new tasks (from Excel/JSON)
2. Run agents (Planner → Architect → Developer → Tester)
3. Create Git branch and commit changes
4. Create Pull Request
5. Wait for PR approval and merge
6. Mark task as complete

Workflow:
  New Task Added → Auto-Trigger → Agents Execute → PR Created → Human Review → Merged → Complete
"""

import os
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Core modules
from core.task_tracker import TaskTracker, TaskStatus, DevelopmentTask
from core.git_integration import GitIntegration, GitConfig, GitHubPRCreator
from core.file_watcher import TaskFileWatcher, create_watcher_with_workflow
from core.memory import SharedMemory, MemoryType
from core.task_queue import TaskQueue
from core.llm_client import LLMClient

# Agents
from agents.base_agent import BaseAgent
from agents.planner_agent import PlannerAgent
from agents.architect_agent import ArchitectAgent
from agents.developer_agent import DeveloperAgent
from agents.tester_agent import TesterAgent
from agents.debug_agent import DebugAgent


class WorkflowStatus(Enum):
    """Status of the SDLC workflow."""
    IDLE = "idle"
    PLANNING = "planning"
    ARCHITECTING = "architecting"
    DEVELOPING = "developing"
    TESTING = "testing"
    DEBUGGING = "debugging"
    COMMITTING = "committing"
    PR_CREATED = "pr_created"
    AWAITING_REVIEW = "awaiting_review"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SDLCConfig:
    """Configuration for SDLC workflow."""
    # Task tracking
    tasks_file: str = "tasks/development_tasks.xlsx"
    
    # LLM settings
    llm_provider: str = "waip"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: str = "gpt-4o"
    
    # Git settings
    repo_url: str = ""
    repo_local_path: str = "./workspace"
    main_branch: str = "main"
    
    # GitHub settings
    github_token: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    
    # Workflow settings
    output_dir: str = "./output"
    auto_create_pr: bool = True
    poll_interval: float = 10.0
    pr_check_interval: float = 30.0
    max_iterations: int = 10
    debug_mode: bool = False
    
    @classmethod
    def from_env(cls) -> "SDLCConfig":
        """Load configuration from environment."""
        from dotenv import load_dotenv
        load_dotenv()
        
        return cls(
            tasks_file=os.getenv("TASKS_FILE", "tasks/development_tasks.xlsx"),
            llm_provider=os.getenv("LLM_PROVIDER", "waip"),
            llm_api_key=os.getenv("WAIP_API_KEY") or os.getenv("OPENAI_API_KEY"),
            llm_base_url=os.getenv("WAIP_API_ENDPOINT", "https://api.waip.wiprocms.com"),
            llm_model=os.getenv("WAIP_MODEL", "gpt-4o"),
            repo_url=os.getenv("GIT_REPO_URL", ""),
            repo_local_path=os.getenv("GIT_LOCAL_PATH", "./workspace"),
            main_branch=os.getenv("GIT_MAIN_BRANCH", "main"),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_owner=os.getenv("GITHUB_OWNER"),
            github_repo=os.getenv("GITHUB_REPO"),
            output_dir=os.getenv("OUTPUT_DIR", "./output"),
            auto_create_pr=os.getenv("AUTO_CREATE_PR", "true").lower() == "true",
            poll_interval=float(os.getenv("POLL_INTERVAL", "10")),
            pr_check_interval=float(os.getenv("PR_CHECK_INTERVAL", "30")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "10")),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
        )


class SDLCOrchestrator:
    """
    Main orchestrator for the SDLC Agentic Workflow.
    
    Coordinates:
    - Task monitoring and auto-trigger
    - AI agent execution (Planner, Architect, Developer, Tester)
    - Git operations (branch, commit, push)
    - PR creation and monitoring
    - Workflow completion
    """
    
    def __init__(self, config: Optional[SDLCConfig] = None):
        """Initialize the SDLC orchestrator."""
        self.config = config or SDLCConfig.from_env()
        self.console = Console()
        
        # Initialize components
        self._init_task_tracker()
        self._init_llm_client()
        self._init_memory()
        self._init_agents()
        self._init_git()
        
        # State
        self.current_status = WorkflowStatus.IDLE
        self.current_task: Optional[DevelopmentTask] = None
        self._watcher: Optional[TaskFileWatcher] = None
        self._running = False
        
        # Ensure directories exist
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _init_task_tracker(self) -> None:
        """Initialize task tracker."""
        self.task_tracker = TaskTracker(self.config.tasks_file)
        self.console.print(f"[green]✓[/green] Task tracker: {self.config.tasks_file}")
    
    def _init_llm_client(self) -> None:
        """Initialize LLM client."""
        self.llm_client = LLMClient(
            provider=self.config.llm_provider,
            api_key=self.config.llm_api_key,
            model=self.config.llm_model,
            base_url=self.config.llm_base_url,
        )
        self.console.print(f"[green]✓[/green] LLM: {self.config.llm_provider} ({self.config.llm_model})")
    
    def _init_memory(self) -> None:
        """Initialize shared memory."""
        self.memory = SharedMemory()
        self.task_queue = TaskQueue()
    
    def _init_agents(self) -> None:
        """Initialize all AI agents."""
        self.agents = {
            "planner": PlannerAgent(
                name="Planner",
                role="Product Manager",
                llm_client=self.llm_client,
                memory=self.memory,
            ),
            "architect": ArchitectAgent(
                name="Architect",
                role="Software Architect",
                llm_client=self.llm_client,
                memory=self.memory,
            ),
            "developer": DeveloperAgent(
                name="Developer",
                role="Software Developer",
                llm_client=self.llm_client,
                memory=self.memory,
            ),
            "tester": TesterAgent(
                name="Tester",
                role="QA Engineer",
                llm_client=self.llm_client,
                memory=self.memory,
            ),
            "debugger": DebugAgent(
                name="Debugger",
                role="Bug Fixer",
                llm_client=self.llm_client,
                memory=self.memory,
            ),
        }
        self.console.print(f"[green]✓[/green] Agents: {', '.join(self.agents.keys())}")
    
    def _init_git(self) -> None:
        """Initialize Git integration."""
        git_config = GitConfig(
            repo_url=self.config.repo_url,
            local_path=self.config.repo_local_path,
            main_branch=self.config.main_branch,
            github_token=self.config.github_token,
            github_owner=self.config.github_owner,
            github_repo=self.config.github_repo,
        )
        self.git = GitIntegration(git_config)
        
        # Initialize PR creator if GitHub is configured
        self.pr_creator: Optional[GitHubPRCreator] = None
        if all([self.config.github_token, self.config.github_owner, self.config.github_repo]):
            self.pr_creator = GitHubPRCreator(
                token=self.config.github_token,
                owner=self.config.github_owner,
                repo=self.config.github_repo,
            )
            self.console.print(f"[green]✓[/green] GitHub: {self.config.github_owner}/{self.config.github_repo}")
        else:
            self.console.print("[yellow]![/yellow] GitHub PR creation not configured")
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {"info": "blue", "success": "green", "warning": "yellow", "error": "red"}.get(level, "white")
        self.console.print(f"[dim]{timestamp}[/dim] [{color}]{message}[/{color}]")
    
    def process_task(self, task_id: str) -> Dict[str, Any]:
        """
        Process a single development task through the full SDLC.
        
        Steps:
        1. Load and validate task
        2. Create feature branch
        3. Run agents (Plan → Architect → Develop → Test)
        4. Commit and push changes
        5. Create PR
        6. Return result
        """
        result = {
            "task_id": task_id,
            "success": False,
            "pr_url": None,
            "pr_number": None,
            "files_changed": [],
            "error": None
        }
        
        try:
            # 1. Load task
            task = self.task_tracker.get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            self.current_task = task
            self._log(f"Processing task: {task.id} - {task.title}", "info")
            
            # Store task in memory
            self.memory.store(
                type=MemoryType.REQUIREMENT,
                content={
                    "task_id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "type": task.type,
                    "component": task.target_component,
                },
                agent="Orchestrator"
            )
            
            # 2. Create feature branch
            branch_name = self.git.generate_branch_name(task.id, task.title)
            self._log(f"Creating branch: {branch_name}", "info")
            self.git.create_branch(branch_name)
            
            self.task_tracker.update_task_status(
                task_id, 
                TaskStatus.IN_PROGRESS,
                branch_name=branch_name
            )
            
            # 3. Run agent workflow
            self._run_agent_workflow(task)
            
            # 4. Write generated files to repo
            files_changed = self._write_output_to_repo(task)
            result["files_changed"] = files_changed
            
            # 5. Commit and push
            if files_changed:
                self._log("Committing changes...", "info")
                self.git.stage_files()
                commit_message = f"feat({task.id}): {task.title}\n\n{task.description}"
                self.git.commit(commit_message)
                self.git.push(branch_name)
                
                self.task_tracker.update_task_status(
                    task_id,
                    TaskStatus.DEVELOPMENT_COMPLETE,
                    files_changed=files_changed
                )
            
            # 6. Create PR
            if self.pr_creator and self.config.auto_create_pr and files_changed:
                pr_result = self._create_pull_request(task, branch_name)
                
                if pr_result.get("success"):
                    result["pr_url"] = pr_result["pr_url"]
                    result["pr_number"] = pr_result["pr_number"]
                    
                    self.task_tracker.update_task_status(
                        task_id,
                        TaskStatus.PR_CREATED,
                        pr_url=pr_result["pr_url"],
                        pr_number=pr_result["pr_number"]
                    )
                    
                    self._log(f"PR created: {pr_result['pr_url']}", "success")
            
            result["success"] = True
            self._log(f"Task {task_id} processing complete!", "success")
            
        except Exception as e:
            result["error"] = str(e)
            self._log(f"Error processing task {task_id}: {e}", "error")
            
            self.task_tracker.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
            
            if self.config.debug_mode:
                import traceback
                traceback.print_exc()
        
        finally:
            self.current_task = None
            self.current_status = WorkflowStatus.IDLE
        
        return result
    
    def _run_agent_workflow(self, task: DevelopmentTask) -> None:
        """Run the agent workflow for a task."""
        goal = f"{task.title}: {task.description}"
        
        # Phase 1: Planning
        self.current_status = WorkflowStatus.PLANNING
        self._log("Phase 1: Planning", "info")
        self._run_agent("planner", {
            "action": "create_task_breakdown",
            "goal": goal,
            "task_type": task.type,
            "component": task.target_component
        })
        
        # Phase 2: Architecture
        self.current_status = WorkflowStatus.ARCHITECTING
        self._log("Phase 2: Architecture", "info")
        self._run_agent("architect", {
            "action": "design_architecture",
            "goal": goal,
            "component": task.target_component
        })
        
        # Phase 3: Development
        self.current_status = WorkflowStatus.DEVELOPING
        self._log("Phase 3: Development", "info")
        
        if task.target_component in ["backend", "both"]:
            self._run_agent("developer", {
                "action": "implement_backend",
                "goal": goal
            })
        
        if task.target_component in ["frontend", "both"]:
            self._run_agent("developer", {
                "action": "implement_frontend",
                "goal": goal
            })
        
        # Phase 4: Testing
        self.current_status = WorkflowStatus.TESTING
        self._log("Phase 4: Testing", "info")
        test_result = self._run_agent("tester", {
            "action": "generate_tests",
            "goal": goal
        })
        
        # Phase 5: Debug if needed
        if test_result and test_result.get("errors"):
            self.current_status = WorkflowStatus.DEBUGGING
            self._log("Phase 5: Debugging", "info")
            self._run_agent("debugger", {
                "action": "fix_bugs",
                "errors": test_result["errors"]
            })
    
    def _run_agent(self, agent_name: str, context: Dict[str, Any]) -> Optional[Dict]:
        """Run a specific agent with context."""
        agent = self.agents.get(agent_name)
        if not agent:
            self._log(f"Agent not found: {agent_name}", "warning")
            return None
        
        try:
            # Create task for agent
            from core.task_queue import Task
            agent_task = Task(
                id=f"{self.current_task.id}_{agent_name}",
                name=context.get("action", "execute"),
                description=context.get("goal", ""),
                assigned_agent=agent_name,
                input_data=context
            )
            
            result = agent.execute(agent_task)
            self._log(f"  ✓ {agent_name} completed", "success")
            return result
            
        except Exception as e:
            self._log(f"  ✗ {agent_name} failed: {e}", "error")
            return None
    
    def _write_output_to_repo(self, task: DevelopmentTask) -> List[str]:
        """Write generated output files to the repository."""
        files_written = []
        output_dir = Path(self.config.output_dir)
        
        if not output_dir.exists():
            return files_written
        
        # Copy files from output to repo workspace
        for file_path in output_dir.glob("**/*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                rel_path = file_path.relative_to(output_dir)
                
                # Skip certain files
                if rel_path.name in ["project_memory.json", "summary.json"]:
                    continue
                
                content = file_path.read_text(encoding="utf-8")
                repo_path = self.git.write_file(str(rel_path), content)
                files_written.append(str(rel_path))
                self._log(f"  → {rel_path}", "info")
        
        return files_written
    
    def _create_pull_request(
        self, 
        task: DevelopmentTask, 
        branch_name: str
    ) -> Dict[str, Any]:
        """Create a pull request for the task."""
        if not self.pr_creator:
            return {"success": False, "error": "PR creator not configured"}
        
        title = f"[{task.id}] {task.title}"
        
        body = f"""## Description
{task.description}

## Task Details
- **Task ID:** {task.id}
- **Type:** {task.type}
- **Priority:** {task.priority}
- **Component:** {task.target_component}

## Changes
This PR was automatically generated by the Multi-Agent Development Team.

### Agents involved:
- 🎯 **Planner** - Task breakdown and planning
- 🏗️ **Architect** - System design
- 💻 **Developer** - Code implementation
- 🧪 **Tester** - Test generation

---
*Automated by SDLC Agentic Workflow*
"""
        
        return self.pr_creator.create_pr(
            title=title,
            body=body,
            head_branch=branch_name,
            base_branch=self.config.main_branch,
            draft=False
        )
    
    def check_pr_status(self, task_id: str) -> Optional[str]:
        """Check if a task's PR has been merged."""
        task = self.task_tracker.get_task(task_id)
        if not task or not task.pr_number or not self.pr_creator:
            return None
        
        pr_info = self.pr_creator.get_pr(task.pr_number)
        
        if pr_info.get("merged"):
            self.task_tracker.update_task_status(task_id, TaskStatus.MERGED)
            self._log(f"PR #{task.pr_number} for {task_id} has been merged!", "success")
            return "merged"
        elif pr_info.get("state") == "closed":
            return "closed"
        else:
            return "open"
    
    def start_watching(self) -> None:
        """Start watching for new tasks and auto-trigger workflow."""
        self._running = True
        
        self.console.print(Panel(
            "[bold blue]SDLC Agentic Workflow Started[/bold blue]\n\n"
            f"📋 Tasks file: {self.config.tasks_file}\n"
            f"⏱️  Poll interval: {self.config.poll_interval}s\n"
            f"🤖 Agents ready: {len(self.agents)}\n\n"
            "[dim]Add new tasks to Excel file to auto-trigger workflow[/dim]",
            title="Multi-Agent Dev Team"
        ))
        
        # Create watcher
        self._watcher = create_watcher_with_workflow(
            self.config.tasks_file,
            self.process_task,
            self.config.poll_interval
        )
        
        # Also check for existing new tasks
        self._process_pending_tasks()
        
        # Start watching
        try:
            self._watcher.start(blocking=True)
        except KeyboardInterrupt:
            self.stop_watching()
    
    def _process_pending_tasks(self) -> None:
        """Process any pending tasks that exist."""
        new_tasks = self.task_tracker.get_new_tasks()
        
        if new_tasks:
            self._log(f"Found {len(new_tasks)} pending task(s)", "info")
            for task in new_tasks:
                self.process_task(task.id)
    
    def stop_watching(self) -> None:
        """Stop the file watcher."""
        self._running = False
        if self._watcher:
            self._watcher.stop()
        self.console.print("\n[yellow]SDLC workflow stopped[/yellow]")
    
    def run_single_task(self, task_id: str) -> Dict[str, Any]:
        """Run workflow for a single task (non-watching mode)."""
        return self.process_task(task_id)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "status": self.current_status.value,
            "current_task": self.current_task.id if self.current_task else None,
            "tasks_pending": len(self.task_tracker.get_new_tasks()),
            "tasks_in_progress": len(self.task_tracker.get_tasks_by_status(TaskStatus.IN_PROGRESS)),
            "tasks_completed": len(self.task_tracker.get_tasks_by_status(TaskStatus.COMPLETED)),
            "running": self._running
        }
    
    def display_status_table(self) -> None:
        """Display a status table of all tasks."""
        table = Table(title="Development Tasks Status")
        
        table.add_column("Task ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Status", style="magenta")
        table.add_column("PR", style="blue")
        table.add_column("Branch", style="dim")
        
        status_colors = {
            "new": "green",
            "in_progress": "yellow",
            "development_complete": "blue",
            "pr_created": "cyan",
            "pr_review": "magenta",
            "merged": "green",
            "completed": "green",
            "failed": "red"
        }
        
        for task in self.task_tracker.get_all_tasks():
            color = status_colors.get(task.status, "white")
            pr_info = f"#{task.pr_number}" if task.pr_number else "-"
            branch = task.branch_name[:30] + "..." if task.branch_name and len(task.branch_name) > 30 else (task.branch_name or "-")
            
            table.add_row(
                task.id,
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                f"[{color}]{task.status}[/{color}]",
                pr_info,
                branch
            )
        
        self.console.print(table)


def create_sdlc_orchestrator(
    tasks_file: str = "tasks/development_tasks.xlsx",
    **kwargs
) -> SDLCOrchestrator:
    """
    Factory function to create SDLC orchestrator.
    
    Args:
        tasks_file: Path to task tracking file
        **kwargs: Additional configuration options
        
    Returns:
        Configured SDLCOrchestrator instance
    """
    config = SDLCConfig.from_env()
    config.tasks_file = tasks_file
    
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return SDLCOrchestrator(config)


if __name__ == "__main__":
    # Test the orchestrator
    orchestrator = create_sdlc_orchestrator()
    orchestrator.display_status_table()
