"""
Planner Agent - Product Manager Role.

Responsible for understanding requirements and breaking
projects into manageable tasks.
"""

import json
from typing import Any, Dict, List
from .base_agent import BaseAgent
from core.memory import MemoryType
from core.task_queue import Task, TaskPriority


class PlannerAgent(BaseAgent):
    """
    Planner Agent acts as the product manager.
    
    Responsibilities:
    - Understand user requirements
    - Break project into tasks
    - Prioritize work
    - Define acceptance criteria
    """
    
    def _get_responsibilities(self) -> str:
        return """- Analyze user requirements and extract key features
- Break down complex projects into manageable tasks
- Prioritize tasks based on dependencies and importance
- Define clear acceptance criteria for each task
- Identify potential risks and blockers"""
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a planning task."""
        if task.name == "analyze_requirements":
            return self.analyze_requirements(task.input_data.get("requirements", ""))
        elif task.name == "create_task_breakdown":
            return self.create_task_breakdown(task.input_data.get("requirements", ""))
        else:
            return self.generic_planning(task)
    
    def analyze_requirements(self, requirements: str) -> Dict[str, Any]:
        """
        Analyze project requirements.
        
        Args:
            requirements: Raw requirements from user
            
        Returns:
            Structured analysis
        """
        prompt = f"""Analyze these software requirements and provide a structured breakdown:

Requirements:
{requirements}

Return JSON with this structure:
{{
    "project_name": "string",
    "summary": "brief description",
    "features": ["list of main features"],
    "technical_requirements": ["list of technical needs"],
    "constraints": ["any limitations or constraints"],
    "questions": ["clarifying questions if any"]
}}"""

        try:
            analysis = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            response = self.think(prompt)
            analysis = {
                "project_name": "Unknown",
                "summary": response,
                "features": [],
                "technical_requirements": [],
                "constraints": [],
                "questions": [],
            }
        
        # Store in memory
        self.store_output(
            type=MemoryType.REQUIREMENT,
            content=analysis,
            metadata={"raw_requirements": requirements},
        )
        
        return {"status": "success", "analysis": analysis}
    
    def create_task_breakdown(self, requirements: str) -> Dict[str, Any]:
        """
        Create a detailed task breakdown for the project.
        
        Args:
            requirements: Project requirements
            
        Returns:
            Task list with priorities and dependencies
        """
        prompt = f"""Create a detailed task breakdown for this software project:

Requirements:
{requirements}

Return JSON with this structure:
{{
    "tasks": [
        {{
            "name": "task name",
            "description": "what needs to be done",
            "agent": "architect|developer|tester|debugger",
            "priority": "critical|high|medium|low",
            "dependencies": ["list of task names this depends on"],
            "estimated_complexity": "low|medium|high",
            "acceptance_criteria": ["list of criteria"]
        }}
    ]
}}

Guidelines:
- Start with architecture/design tasks
- Backend and frontend can run in parallel
- Testing depends on implementation
- Include at least one task for each agent type"""

        try:
            breakdown = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            # Default task breakdown
            breakdown = {
                "tasks": [
                    {
                        "name": "Design System Architecture",
                        "description": "Create technical architecture",
                        "agent": "architect",
                        "priority": "critical",
                        "dependencies": [],
                        "estimated_complexity": "medium",
                        "acceptance_criteria": ["Architecture document created"],
                    },
                    {
                        "name": "Implement Backend",
                        "description": "Create backend API",
                        "agent": "developer",
                        "priority": "high",
                        "dependencies": ["Design System Architecture"],
                        "estimated_complexity": "high",
                        "acceptance_criteria": ["API endpoints working"],
                    },
                    {
                        "name": "Implement Frontend",
                        "description": "Create user interface",
                        "agent": "developer",
                        "priority": "high",
                        "dependencies": ["Design System Architecture"],
                        "estimated_complexity": "high",
                        "acceptance_criteria": ["UI functional"],
                    },
                    {
                        "name": "Write Tests",
                        "description": "Create test suite",
                        "agent": "tester",
                        "priority": "medium",
                        "dependencies": ["Implement Backend"],
                        "estimated_complexity": "medium",
                        "acceptance_criteria": ["Tests passing"],
                    },
                ]
            }
        
        # Store in memory
        self.store_output(
            type=MemoryType.TASK,
            content=breakdown,
            metadata={"source": "planner"},
        )
        
        return {"status": "success", "breakdown": breakdown}
    
    def generic_planning(self, task: Task) -> Dict[str, Any]:
        """Handle generic planning tasks."""
        context = self.get_context()
        
        prompt = f"""Complete this planning task:

Task: {task.name}
Description: {task.description}

Available context:
{json.dumps(context, indent=2)}

Provide your output as structured JSON."""

        response = self.think(prompt)
        
        return {"status": "success", "result": response}
    
    def prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize a list of tasks.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Sorted task list by priority
        """
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }
        
        return sorted(
            tasks,
            key=lambda t: priority_order.get(t.get("priority", "medium"), 2)
        )
