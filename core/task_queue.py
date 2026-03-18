"""
Task Queue System for Agent Coordination.

This module implements a task queue that the orchestrator uses
to assign work to agents and track progress.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import heapq


class TaskStatus(Enum):
    """Status of a task in the queue."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Priority levels for tasks."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Task:
    """Represents a task to be executed by an agent."""
    id: str
    name: str
    description: str
    assigned_agent: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority for heap operations."""
        return self.priority.value < other.priority.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "assigned_agent": self.assigned_agent,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class TaskQueue:
    """
    Priority queue for managing agent tasks.
    
    The orchestrator uses this to:
    - Add new tasks
    - Get next task for execution
    - Track task dependencies
    - Monitor progress
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._priority_queue: List[Task] = []
        self._counter = 0

    def _generate_id(self) -> str:
        """Generate unique task ID."""
        self._counter += 1
        return f"task_{self._counter:04d}"

    def add_task(
        self,
        name: str,
        description: str,
        assigned_agent: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a new task to the queue.
        
        Returns:
            The task ID
        """
        task_id = self._generate_id()
        task = Task(
            id=task_id,
            name=name,
            description=description,
            assigned_agent=assigned_agent,
            priority=priority,
            dependencies=dependencies or [],
            input_data=input_data or {},
            metadata=metadata or {},
        )
        self._tasks[task_id] = task
        heapq.heappush(self._priority_queue, task)
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_next_ready_task(self) -> Optional[Task]:
        """
        Get the highest priority task that is ready to execute.
        
        A task is ready if:
        - It's in PENDING status
        - All its dependencies are COMPLETED
        """
        ready_tasks = []
        
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
                
            # Check if all dependencies are completed
            deps_satisfied = all(
                self._tasks.get(dep_id) and 
                self._tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            
            if deps_satisfied:
                ready_tasks.append(task)
        
        if not ready_tasks:
            return None
            
        # Return highest priority (lowest value)
        return min(ready_tasks, key=lambda t: t.priority.value)

    def start_task(self, task_id: str) -> bool:
        """Mark a task as in progress."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        return True

    def complete_task(self, task_id: str, output_data: Optional[Dict[str, Any]] = None) -> bool:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.output_data = output_data
        return True

    def fail_task(self, task_id: str, error_message: str) -> bool:
        """Mark a task as failed."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now()
        task.error_message = error_message
        return True

    def block_task(self, task_id: str, reason: str) -> bool:
        """Mark a task as blocked."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.BLOCKED
        task.error_message = reason
        return True

    def retry_task(self, task_id: str) -> bool:
        """Reset a failed task to pending for retry."""
        task = self._tasks.get(task_id)
        if not task or task.status not in [TaskStatus.FAILED, TaskStatus.BLOCKED]:
            return False
        task.status = TaskStatus.PENDING
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        return True

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with a specific status."""
        return [t for t in self._tasks.values() if t.status == status]

    def get_tasks_by_agent(self, agent: str) -> List[Task]:
        """Get all tasks assigned to a specific agent."""
        return [t for t in self._tasks.values() if t.assigned_agent == agent]

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self._tasks.values())

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress statistics."""
        total = len(self._tasks)
        if total == 0:
            return {
                "total": 0,
                "completed": 0,
                "in_progress": 0,
                "pending": 0,
                "failed": 0,
                "blocked": 0,
                "progress_percent": 0,
            }
        
        by_status = {}
        for status in TaskStatus:
            by_status[status.value] = len(self.get_tasks_by_status(status))
        
        completed = by_status.get("completed", 0)
        
        return {
            "total": total,
            "completed": completed,
            "in_progress": by_status.get("in_progress", 0),
            "pending": by_status.get("pending", 0),
            "failed": by_status.get("failed", 0),
            "blocked": by_status.get("blocked", 0),
            "progress_percent": round((completed / total) * 100, 1),
        }

    def is_all_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(
            t.status == TaskStatus.COMPLETED 
            for t in self._tasks.values()
        )

    def has_failures(self) -> bool:
        """Check if any tasks have failed."""
        return any(
            t.status == TaskStatus.FAILED
            for t in self._tasks.values()
        )

    def clear(self) -> None:
        """Clear all tasks."""
        self._tasks.clear()
        self._priority_queue.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._tasks)

    def __repr__(self) -> str:
        progress = self.get_progress()
        return f"TaskQueue(total={progress['total']}, completed={progress['completed']})"
