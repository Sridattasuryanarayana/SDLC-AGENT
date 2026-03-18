"""
Orchestrator - Central Coordinator for Multi-Agent System.

The orchestrator manages the full SDLC workflow:
1. Receive enhancement/development request
2. Run agents (Planner → Architect → Developer → Tester → Debug)
3. Write generated code to Git repository
4. Create feature branch, commit, push
5. Create Pull Request for human review
6. Monitor PR until merged → workflow complete
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from enum import Enum
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.memory import SharedMemory, MemoryType
from core.task_queue import TaskQueue, Task, TaskStatus, TaskPriority
from core.llm_client import LLMClient
from core.git_integration import GitIntegration, GitConfig, GitHubPRCreator

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
    COMPLETED = "completed"
    FAILED = "failed"


class Orchestrator:
    """
    Central coordinator for the multi-agent development team.
    
    The orchestrator:
    - Receives project goals from users
    - Creates and manages agents
    - Assigns tasks based on dependencies
    - Monitors progress
    - Handles failures and retries
    """
    
    def __init__(
        self,
        llm_provider: str = "mock",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        output_dir: str = "./output",
        max_iterations: int = 10,
        debug_mode: bool = False,
        # Git / PR settings
        repo_local_path: str = "./workspace",
        repo_url: str = "",
        main_branch: str = "main",
        github_token: Optional[str] = None,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
        auto_create_pr: bool = True,
    ):
        self.console = Console()
        self.output_dir = output_dir
        self.max_iterations = max_iterations
        self.debug_mode = debug_mode
        self.auto_create_pr = auto_create_pr
        
        # Workflow state
        self.iteration = 0
        self.project_goal = ""
        self.workflow_status = WorkflowStatus.IDLE
        self.workflow_log: List[Dict[str, Any]] = []
        
        # Initialize core components
        self.memory = SharedMemory()
        self.task_queue = TaskQueue()
        
        # Initialize LLM client
        self.llm_client = LLMClient(
            provider=llm_provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        
        # Initialize agents
        self.agents = self._create_agents()
        
        # Initialize Git integration
        git_config = GitConfig(
            repo_url=repo_url or os.getenv("GIT_REPO_URL", ""),
            local_path=repo_local_path,
            main_branch=main_branch,
            github_token=github_token or os.getenv("GITHUB_TOKEN"),
            github_owner=github_owner or os.getenv("GITHUB_OWNER"),
            github_repo=github_repo or os.getenv("GITHUB_REPO"),
        )
        self.git = GitIntegration(git_config)
        
        # Initialize PR creator if GitHub is configured
        self.pr_creator: Optional[GitHubPRCreator] = None
        gh_token = github_token or os.getenv("GITHUB_TOKEN")
        gh_owner = github_owner or os.getenv("GITHUB_OWNER")
        gh_repo = github_repo or os.getenv("GITHUB_REPO")
        if all([gh_token, gh_owner, gh_repo]):
            self.pr_creator = GitHubPRCreator(
                token=gh_token,
                owner=gh_owner,
                repo=gh_repo,
            )
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def _create_agents(self) -> Dict[str, BaseAgent]:
        """Create all agents for the system."""
        return {
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
    
    def run(self, goal: str, branch_prefix: str = "feature") -> Dict[str, Any]:
        """
        Run the full SDLC workflow:
        Plan → Architect → Develop → Test → Debug → Git Commit → PR Create.
        
        Returns:
            Result dict with files, PR info, workflow log.
        """
        self.project_goal = goal
        self.iteration = 0
        self.workflow_log = []
        
        self._log_header(f"Starting Project: {goal[:80]}...")
        self._log_workflow("workflow_start", {"goal": goal})
        
        # Phase 1: Planning
        self.workflow_status = WorkflowStatus.PLANNING
        self._log_phase("Phase 1: Planning")
        self._run_planning_phase(goal)
        self._log_workflow("planning_complete")
        
        # Phase 2: Architecture
        self.workflow_status = WorkflowStatus.ARCHITECTING
        self._log_phase("Phase 2: Architecture Design")
        self._run_architecture_phase()
        self._log_workflow("architecture_complete")
        
        # Phase 3: Development
        self.workflow_status = WorkflowStatus.DEVELOPING
        self._log_phase("Phase 3: Development")
        self._run_development_phase()
        self._log_workflow("development_complete")
        
        # Phase 4: Testing
        self.workflow_status = WorkflowStatus.TESTING
        self._log_phase("Phase 4: Testing")
        self._run_testing_phase()
        self._log_workflow("testing_complete")
        
        # Phase 5: Debug (if needed)
        if self._has_issues():
            self.workflow_status = WorkflowStatus.DEBUGGING
            self._log_phase("Phase 5: Debugging")
            self._run_debug_phase()
            self._log_workflow("debugging_complete")
        
        # Generate output files
        self._log_phase("Generating Output")
        result = self._generate_output()
        
        # Phase 6: Git operations — branch, commit, push
        self.workflow_status = WorkflowStatus.COMMITTING
        git_result = self._git_commit_and_push(goal, branch_prefix)
        result["git"] = git_result
        
        # Phase 7: Create PR
        pr_result: Dict[str, Any] = {}
        if git_result.get("success") and self.auto_create_pr and self.pr_creator:
            self.workflow_status = WorkflowStatus.PR_CREATED
            pr_result = self._create_pull_request(
                goal, git_result.get("branch", "")
            )
            result["pr"] = pr_result
            self._log_workflow("pr_created", pr_result)
        
        result["workflow_log"] = self.workflow_log
        
        self.workflow_status = WorkflowStatus.COMPLETED
        self._log_success("Project completed!")
        self._show_summary(result)
        
        return result
    
    def _log_workflow(self, event: str, data: Dict[str, Any] = None) -> None:
        """Append to the workflow audit log."""
        self.workflow_log.append({
            "event": event,
            "status": self.workflow_status.value,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        })
    
    def _run_planning_phase(self, goal: str) -> None:
        """Execute planning phase."""
        planner = self.agents["planner"]
        
        # Analyze requirements
        task = Task(
            id="plan_001",
            name="analyze_requirements",
            description="Analyze project requirements",
            assigned_agent="planner",
            input_data={"requirements": goal},
        )
        
        self._execute_task(planner, task)
        
        # Create task breakdown
        task = Task(
            id="plan_002",
            name="create_task_breakdown",
            description="Break project into tasks",
            assigned_agent="planner",
            input_data={"requirements": goal},
        )
        
        self._execute_task(planner, task)
    
    def _run_architecture_phase(self) -> None:
        """Execute architecture design phase."""
        architect = self.agents["architect"]
        
        context = self.memory.get_context_for_agent("architect")
        
        task = Task(
            id="arch_001",
            name="design_architecture",
            description="Design system architecture",
            assigned_agent="architect",
            input_data={"requirements": self.project_goal, "context": context},
        )
        
        self._execute_task(architect, task)
    
    def _run_development_phase(self) -> None:
        """Execute development phase."""
        developer = self.agents["developer"]
        
        # Implement backend
        task = Task(
            id="dev_001",
            name="implement_backend",
            description="Implement backend API",
            assigned_agent="developer",
            input_data={},
        )
        self._execute_task(developer, task)
        
        # Implement frontend
        task = Task(
            id="dev_002",
            name="implement_frontend",
            description="Implement frontend UI",
            assigned_agent="developer",
            input_data={},
        )
        self._execute_task(developer, task)
    
    def _run_testing_phase(self) -> None:
        """Execute testing phase."""
        tester = self.agents["tester"]
        
        # Generate tests
        task = Task(
            id="test_001",
            name="generate_tests",
            description="Generate test suite",
            assigned_agent="tester",
            input_data={},
        )
        self._execute_task(tester, task)
        
        # Run tests
        task = Task(
            id="test_002",
            name="run_tests",
            description="Run and analyze tests",
            assigned_agent="tester",
            input_data={},
        )
        self._execute_task(tester, task)
    
    def _run_debug_phase(self) -> None:
        """Execute debugging phase."""
        debugger = self.agents["debugger"]
        
        bugs = self.memory.get_by_type(MemoryType.BUG_REPORT)
        
        for bug in bugs:
            task = Task(
                id=f"debug_{bug.id}",
                name="fix_bug",
                description=f"Fix bug: {bug.content.get('description', 'Unknown')}",
                assigned_agent="debugger",
                input_data={"bug_report": bug.content, "analysis": {}},
            )
            self._execute_task(debugger, task)
    
    def _execute_task(self, agent: BaseAgent, task: Task) -> Dict[str, Any]:
        """Execute a task with an agent."""
        self._log_task(task.name, agent.name)
        
        try:
            result = agent.execute(task)
            self._log_task_complete(task.name)
            return result
        except Exception as e:
            self._log_error(f"Task {task.name} failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _has_issues(self) -> bool:
        """Check if there are unresolved bugs."""
        bugs = self.memory.get_by_type(MemoryType.BUG_REPORT)
        return len(bugs) > 0
    
    def _generate_output(self) -> Dict[str, Any]:
        """Generate final project output files."""
        # Collect all generated code
        code_entries = self.memory.get_by_type(MemoryType.CODE)
        tests = self.memory.get_by_type(MemoryType.TEST)
        
        # Save files to output directory
        for entry in code_entries:
            filename = entry.metadata.get("filename", "unknown.py")
            filepath = os.path.join(self.output_dir, filename)
            os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else self.output_dir, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(entry.content)
        
        for entry in tests:
            filename = entry.metadata.get("filename", "test_unknown.py")
            filepath = os.path.join(self.output_dir, "tests", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(entry.content)
        
        # Export memory
        self.memory.export_to_json(os.path.join(self.output_dir, "project_memory.json"))
        
        arch_entry = self.memory.get_latest(MemoryType.ARCHITECTURE)
        architecture = arch_entry.content if arch_entry else "N/A"
        
        summary = {
            "goal": self.project_goal,
            "files_generated": len(code_entries) + len(tests),
            "architecture": architecture,
            "output_directory": self.output_dir,
            "timestamp": datetime.now().isoformat(),
        }
        
        with open(os.path.join(self.output_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        return summary
    
    # ── Git & PR Operations ──────────────────────────────────────
    
    def _git_commit_and_push(
        self, goal: str, branch_prefix: str = "feature"
    ) -> Dict[str, Any]:
        """Create branch, write files to repo, commit & push."""
        result: Dict[str, Any] = {"success": False, "branch": "", "files": []}
        
        try:
            # Generate branch name from goal
            import re
            slug = re.sub(r"[^a-zA-Z0-9\s-]", "", goal.lower())
            slug = re.sub(r"\s+", "-", slug)[:40].strip("-")
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            branch_name = f"{branch_prefix}/{slug}-{ts}"
            
            self._log_phase(f"Phase 6: Git — branch {branch_name}")
            self.git.create_branch(branch_name)
            
            # Write output files into the repo workspace
            files_written = self._write_output_to_repo()
            result["files"] = files_written
            
            if files_written:
                self.git.stage_files()
                commit_msg = f"feat: {goal[:72]}\n\nGenerated by SDLC Agent"
                self.git.commit(commit_msg)
                self.git.push(branch_name)
                self._log_success(f"Pushed {len(files_written)} files to {branch_name}")
            
            result["success"] = True
            result["branch"] = branch_name
            
        except Exception as e:
            self._log_error(f"Git operations failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _write_output_to_repo(self) -> List[str]:
        """Copy generated files from output dir into the Git repo workspace."""
        files_written: List[str] = []
        output_path = Path(self.output_dir)
        
        if not output_path.exists():
            return files_written
        
        for file_path in output_path.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name in {"project_memory.json", "summary.json", ".gitkeep"}:
                continue
            
            rel = file_path.relative_to(output_path)
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            self.git.write_file(str(rel), content)
            files_written.append(str(rel))
        
        return files_written
    
    def _create_pull_request(
        self, goal: str, branch_name: str
    ) -> Dict[str, Any]:
        """Create a GitHub Pull Request."""
        if not self.pr_creator:
            return {"success": False, "error": "GitHub PR creator not configured"}
        
        self._log_phase("Phase 7: Creating Pull Request")
        
        code_count = len(self.memory.get_by_type(MemoryType.CODE))
        test_count = len(self.memory.get_by_type(MemoryType.TEST))
        
        body = (
            f"## Description\n{goal}\n\n"
            f"## Generated by SDLC Agent\n"
            f"- **Code files:** {code_count}\n"
            f"- **Test files:** {test_count}\n\n"
            f"### Agents involved\n"
            f"- 🎯 **Planner** — Task breakdown and planning\n"
            f"- 🏗️ **Architect** — System design\n"
            f"- 💻 **Developer** — Code implementation\n"
            f"- 🧪 **Tester** — Test generation\n\n"
            f"---\n*Automated by SDLC Agentic Workflow*"
        )
        
        pr_result = self.pr_creator.create_pr(
            title=f"feat: {goal[:72]}",
            body=body,
            head_branch=branch_name,
            base_branch=self.git.config.main_branch,
            draft=False,
        )
        
        if pr_result.get("success"):
            self._log_success(f"PR #{pr_result['pr_number']}: {pr_result['pr_url']}")
            self.workflow_status = WorkflowStatus.AWAITING_REVIEW
        else:
            self._log_error(f"PR creation failed: {pr_result.get('error')}")
        
        return pr_result
    
    def check_pr_merged(self, pr_number: int) -> bool:
        """Check if a PR has been merged (final workflow step)."""
        if not self.pr_creator:
            return False
        merged = self.pr_creator.is_pr_merged(pr_number)
        if merged:
            self.workflow_status = WorkflowStatus.COMPLETED
        return merged
    
    def _show_summary(self, result: Dict[str, Any] = None) -> None:
        """Display project summary."""
        table = Table(title="Project Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        code_count = len(self.memory.get_by_type(MemoryType.CODE))
        test_count = len(self.memory.get_by_type(MemoryType.TEST))
        bug_count = len(self.memory.get_by_type(MemoryType.BUG_REPORT))
        
        table.add_row("Code Files Generated", str(code_count))
        table.add_row("Test Files Generated", str(test_count))
        table.add_row("Bugs Found", str(bug_count))
        table.add_row("Output Directory", self.output_dir)
        
        if result:
            git_info = result.get("git", {})
            if git_info.get("branch"):
                table.add_row("Git Branch", git_info["branch"])
            pr_info = result.get("pr", {})
            if pr_info.get("pr_url"):
                table.add_row("Pull Request", pr_info["pr_url"])
        
        self.console.print(table)
    
    # Logging helpers
    def _log_header(self, message: str) -> None:
        """Log a header message."""
        self.console.print(Panel(message, style="bold blue"))
    
    def _log_phase(self, phase: str) -> None:
        """Log phase start."""
        self.console.print(f"\n[bold cyan]{'='*50}[/bold cyan]")
        self.console.print(f"[bold cyan]{phase}[/bold cyan]")
        self.console.print(f"[bold cyan]{'='*50}[/bold cyan]\n")
    
    def _log_task(self, task: str, agent: str) -> None:
        """Log task execution."""
        self.console.print(f"  [yellow]>[/yellow] {agent}: {task}")
    
    def _log_task_complete(self, task: str) -> None:
        """Log task completion."""
        self.console.print(f"  [green]✓[/green] {task} completed")
    
    def _log_success(self, message: str) -> None:
        """Log success message."""
        self.console.print(f"\n[bold green]✓ {message}[/bold green]")
    
    def _log_error(self, message: str) -> None:
        """Log error message."""
        self.console.print(f"[bold red]✗ {message}[/bold red]")
    
    def _log_debug(self, message: str) -> None:
        """Log debug message."""
        if self.debug_mode:
            self.console.print(f"[dim]{message}[/dim]")


class IterativeOrchestrator(Orchestrator):
    """Enhanced orchestrator with iterative improvement loop and quality gates."""
    
    def run_iterative(self, goal: str, quality_threshold: float = 0.8) -> Dict[str, Any]:
        """Run iterative development until quality threshold is met."""
        self.project_goal = goal
        result = {}
        
        for iteration in range(self.max_iterations):
            self._log_header(f"Iteration {iteration + 1}/{self.max_iterations}")
            result = self.run(goal)
            
            quality_score = self._assess_quality()
            self.console.print(f"\nQuality Score: {quality_score:.2%}")
            
            if quality_score >= quality_threshold:
                self._log_success(f"Quality threshold met: {quality_score:.2%}")
                break
            
            self._improve_from_feedback()
        
        return result
    
    def _assess_quality(self) -> float:
        """Assess overall project quality."""
        # Simple heuristic based on:
        # - Code coverage estimate
        # - Number of bugs
        # - Architecture completeness
        
        code_count = len(self.memory.get_by_type(MemoryType.CODE))
        test_count = len(self.memory.get_by_type(MemoryType.TEST))
        bug_count = len(self.memory.get_by_type(MemoryType.BUG_REPORT))
        
        if code_count == 0:
            return 0.0
        
        test_coverage = min(test_count / code_count, 1.0) * 0.4
        bug_penalty = max(0, 0.3 - (bug_count * 0.1))
        base_score = 0.3  # Base for having any output
        
        return min(test_coverage + bug_penalty + base_score, 1.0)
    
    def _improve_from_feedback(self) -> None:
        """Improve project based on quality assessment."""
        bugs = self.memory.get_by_type(MemoryType.BUG_REPORT)
        
        if bugs:
            self._log_phase("Improvement: Fixing Remaining Bugs")
            self._run_debug_phase()
