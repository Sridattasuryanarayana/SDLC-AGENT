"""
Orchestrator - Central Coordinator for Multi-Agent System.

The orchestrator manages the workflow, assigns tasks to agents,
and ensures proper execution order.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.memory import SharedMemory, MemoryType
from core.task_queue import TaskQueue, Task, TaskStatus, TaskPriority
from core.llm_client import LLMClient

from agents.base_agent import BaseAgent
from agents.planner_agent import PlannerAgent
from agents.architect_agent import ArchitectAgent
from agents.developer_agent import DeveloperAgent
from agents.tester_agent import TesterAgent
from agents.debug_agent import DebugAgent


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
    ):
        """
        Initialize the orchestrator.
        
        Args:
            llm_provider: LLM provider (openai, anthropic, waip, local, mock)
            api_key: API key for LLM provider
            model: Model name to use
            base_url: Base URL for providers that need it (WAIP, local)
            output_dir: Directory to save output files
            max_iterations: Maximum workflow iterations
            debug_mode: Enable debug output
        """
        self.console = Console()
        self.output_dir = output_dir
        self.max_iterations = max_iterations
        self.debug_mode = debug_mode
        
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
        
        # Workflow state
        self.iteration = 0
        self.project_goal = ""
        
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
    
    def run(self, goal: str) -> Dict[str, Any]:
        """
        Run the full development workflow for a goal.
        
        Args:
            goal: Project goal/requirements from user
            
        Returns:
            Final project output
        """
        self.project_goal = goal
        self.iteration = 0
        
        self._log_header(f"Starting Project: {goal[:50]}...")
        
        # Phase 1: Planning
        self._log_phase("Phase 1: Planning")
        self._run_planning_phase(goal)
        
        # Phase 2: Architecture
        self._log_phase("Phase 2: Architecture Design")
        self._run_architecture_phase()
        
        # Phase 3: Development
        self._log_phase("Phase 3: Development")
        self._run_development_phase()
        
        # Phase 4: Testing
        self._log_phase("Phase 4: Testing")
        self._run_testing_phase()
        
        # Phase 5: Debug (if needed)
        if self._has_issues():
            self._log_phase("Phase 5: Debugging")
            self._run_debug_phase()
        
        # Generate final output
        self._log_phase("Finalizing Project")
        result = self._generate_output()
        
        self._log_success("Project completed!")
        self._show_summary()
        
        return result
    
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
        """Generate final project output."""
        # Collect all generated code
        code_entries = self.memory.get_by_type(MemoryType.CODE)
        tests = self.memory.get_by_type(MemoryType.TEST)
        
        # Save files to output directory
        for entry in code_entries:
            filename = entry.metadata.get("filename", "unknown.py")
            filepath = os.path.join(self.output_dir, filename)
            
            # Create subdirectories if needed
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
        
        # Generate summary (convert to serializable format)
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
    
    def _show_summary(self) -> None:
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
    """
    Enhanced orchestrator with iterative improvement loop.
    
    This version supports:
    - Continuous improvement cycles
    - Automatic bug detection and fixing
    - Quality gates between phases
    """
    
    def run_iterative(self, goal: str, quality_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Run iterative development until quality threshold is met.
        
        Args:
            goal: Project goal
            quality_threshold: Minimum quality score (0-1)
            
        Returns:
            Final project output
        """
        self.project_goal = goal
        
        for iteration in range(self.max_iterations):
            self._log_header(f"Iteration {iteration + 1}/{self.max_iterations}")
            
            # Run standard workflow
            result = self.run(goal)
            
            # Assess quality
            quality_score = self._assess_quality()
            
            self.console.print(f"\nQuality Score: {quality_score:.2%}")
            
            if quality_score >= quality_threshold:
                self._log_success(f"Quality threshold met: {quality_score:.2%}")
                break
            
            # Improve based on feedback
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
