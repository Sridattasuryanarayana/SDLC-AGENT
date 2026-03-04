"""Orchestrator module for coordinating multi-agent workflow."""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

from .memory import SharedMemory
from .task_queue import TaskQueue, Task, TaskStatus, TaskPriority

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent


class WorkflowPhase(Enum):
    """Phases of the development workflow."""
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEBUGGING = "debugging"
    COMPLETE = "complete"


class Orchestrator:
    """
    Central orchestrator that coordinates all agents.
    
    Responsibilities:
    - Manage workflow phases
    - Route tasks to appropriate agents
    - Track overall project progress
    - Handle agent communication
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize shared resources
        self.memory = SharedMemory(persist_path=os.path.join(output_dir, "memory.json"))
        self.task_queue = TaskQueue(persist_path=os.path.join(output_dir, "tasks.json"))
        
        # Agent registry
        self._agents: Dict[str, 'BaseAgent'] = {}
        
        # Workflow state
        self.current_phase = WorkflowPhase.PLANNING
        self.project_goal: Optional[str] = None
        self.iteration_count = 0
        self.max_iterations = 10
        
        # Logging
        self.logs: List[Dict[str, Any]] = []
    
    def register_agent(self, agent: 'BaseAgent') -> None:
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        agent.set_orchestrator(self)
        self._log(f"Registered agent: {agent.name} ({agent.role})")
    
    def get_agent(self, name: str) -> Optional['BaseAgent']:
        """Get an agent by name."""
        return self._agents.get(name)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())
    
    def set_project_goal(self, goal: str) -> None:
        """Set the project goal and store in memory."""
        self.project_goal = goal
        self.memory.store(
            key="project_goal",
            value=goal,
            category="requirements",
            created_by="orchestrator"
        )
        self._log(f"Project goal set: {goal}")
    
    def run(self, goal: str) -> Dict[str, Any]:
        """
        Run the full development workflow.
        
        Returns a dictionary with the results.
        """
        self.set_project_goal(goal)
        self.iteration_count = 0
        
        print(f"\n{'='*60}")
        print(f"MULTI-AGENT DEVELOPMENT TEAM")
        print(f"{'='*60}")
        print(f"Goal: {goal}")
        print(f"{'='*60}\n")
        
        try:
            # Phase 1: Planning
            self._run_phase(WorkflowPhase.PLANNING)
            
            # Phase 2: Architecture
            self._run_phase(WorkflowPhase.ARCHITECTURE)
            
            # Phase 3: Development
            self._run_phase(WorkflowPhase.DEVELOPMENT)
            
            # Phase 4: Testing
            self._run_phase(WorkflowPhase.TESTING)
            
            # Phase 5: Debug loop (if needed)
            self._run_debug_loop()
            
            # Mark complete
            self.current_phase = WorkflowPhase.COMPLETE
            
            return self._generate_final_report()
            
        except Exception as e:
            self._log(f"Error in workflow: {str(e)}", level="error")
            raise
    
    def _run_phase(self, phase: WorkflowPhase) -> None:
        """Run a specific phase of the workflow."""
        self.current_phase = phase
        print(f"\n{'='*40}")
        print(f"PHASE: {phase.value.upper()}")
        print(f"{'='*40}\n")
        
        agent_mapping = {
            WorkflowPhase.PLANNING: "planner",
            WorkflowPhase.ARCHITECTURE: "architect",
            WorkflowPhase.DEVELOPMENT: ["backend", "frontend"],
            WorkflowPhase.TESTING: "tester",
            WorkflowPhase.DEBUGGING: "debugger"
        }
        
        agents_to_run = agent_mapping.get(phase, [])
        
        if isinstance(agents_to_run, str):
            agents_to_run = [agents_to_run]
        
        for agent_name in agents_to_run:
            agent = self._agents.get(agent_name)
            if agent:
                self._log(f"Running agent: {agent_name}")
                print(f"\n--- {agent.role} ({agent.name}) ---\n")
                
                try:
                    result = agent.execute()
                    self._log(f"Agent {agent_name} completed", data={"result_preview": str(result)[:200]})
                except Exception as e:
                    self._log(f"Agent {agent_name} failed: {str(e)}", level="error")
                    raise
    
    def _run_debug_loop(self) -> None:
        """Run the debug loop if there are test failures."""
        test_results = self.memory.get("test_results")
        
        if not test_results or test_results.get("all_passed", True):
            print("\n✓ All tests passed, skipping debug phase.\n")
            return
        
        debugger = self._agents.get("debugger")
        tester = self._agents.get("tester")
        
        if not debugger or not tester:
            print("\n⚠ Debug or test agent not available, skipping debug loop.\n")
            return
        
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            print(f"\n--- Debug Iteration {self.iteration_count} ---\n")
            
            # Run debugger
            self._run_phase(WorkflowPhase.DEBUGGING)
            
            # Re-run tests
            self._run_phase(WorkflowPhase.TESTING)
            
            # Check if tests pass now
            test_results = self.memory.get("test_results")
            if test_results and test_results.get("all_passed", False):
                print(f"\n✓ All tests passed after {self.iteration_count} debug iterations.\n")
                return
        
        print(f"\n⚠ Max debug iterations ({self.max_iterations}) reached.\n")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate the final project report."""
        report = {
            "project_goal": self.project_goal,
            "completion_time": datetime.now().isoformat(),
            "iterations": self.iteration_count,
            "task_summary": self.task_queue.get_summary(),
            "artifacts": {
                "architecture": self.memory.get("architecture"),
                "code_files": self.memory.list_keys(category="code"),
                "test_results": self.memory.get("test_results")
            }
        }
        
        # Save report
        report_path = os.path.join(self.output_dir, "final_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save logs
        logs_path = os.path.join(self.output_dir, "orchestrator_logs.json")
        with open(logs_path, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print("PROJECT COMPLETE")
        print(f"{'='*60}")
        print(f"Output directory: {self.output_dir}")
        print(f"Total iterations: {self.iteration_count}")
        print(f"Tasks completed: {self.task_queue.get_summary().get('completed', 0)}")
        print(f"{'='*60}\n")
        
        return report
    
    def _log(self, message: str, level: str = "info", data: Optional[Dict] = None) -> None:
        """Add a log entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "phase": self.current_phase.value,
            "data": data
        }
        self.logs.append(entry)
        
        if level == "error":
            print(f"[ERROR] {message}")
    
    def add_task(
        self,
        title: str,
        description: str,
        assigned_to: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[List[str]] = None
    ) -> Task:
        """Add a task to the queue (convenience method)."""
        return self.task_queue.add_task(
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
            dependencies=dependencies
        )
    
    def get_context_for_agent(self, agent_name: str) -> str:
        """Get relevant context for an agent from shared memory."""
        return self.memory.get_context_summary()
