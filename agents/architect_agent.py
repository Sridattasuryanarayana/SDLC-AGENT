"""
Architecture Agent - Software Architect Role.

Responsible for designing system architecture,
choosing technologies, and defining structure.
"""

import json
from typing import Any, Dict
from .base_agent import BaseAgent
from core.memory import MemoryType
from core.task_queue import Task


class ArchitectAgent(BaseAgent):
    """
    Architecture Agent acts as the software architect.
    
    Responsibilities:
    - Design system architecture
    - Choose appropriate frameworks and technologies
    - Define folder structure and patterns
    - Create API contracts
    - Document technical decisions
    """
    
    def _get_responsibilities(self) -> str:
        return """- Design scalable and maintainable system architecture
- Choose appropriate frameworks, languages, and tools
- Define project structure and coding patterns
- Create API contracts and data models
- Document architectural decisions and rationale
- Consider security, performance, and scalability"""
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute an architecture task."""
        if task.name == "design_architecture":
            return self.design_architecture(task.input_data)
        elif task.name == "define_api":
            return self.define_api_contracts(task.input_data)
        elif task.name == "choose_stack":
            return self.recommend_tech_stack(task.input_data)
        else:
            return self.generic_architecture(task)
    
    def design_architecture(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design the complete system architecture.
        
        Args:
            input_data: Requirements and context
            
        Returns:
            Architecture specification
        """
        requirements = input_data.get("requirements", "")
        context = self.get_context()
        
        prompt = f"""Design a complete software architecture for this project:

Requirements:
{requirements}

Existing Context:
{json.dumps(context.get('requirements', []), indent=2)}

Return JSON with this structure:
{{
    "overview": "high-level architecture description",
    "tech_stack": {{
        "backend": {{"framework": "string", "language": "string", "rationale": "why"}},
        "frontend": {{"framework": "string", "language": "string", "rationale": "why"}},
        "database": {{"type": "string", "name": "string", "rationale": "why"}},
        "additional": ["other technologies needed"]
    }},
    "project_structure": {{
        "folders": ["list of main folders"],
        "key_files": {{"folder/file.ext": "purpose"}}
    }},
    "components": [
        {{"name": "string", "type": "service|controller|model|etc", "description": "purpose"}}
    ],
    "data_models": [
        {{"name": "string", "fields": {{"field": "type"}}, "description": "purpose"}}
    ],
    "api_endpoints": [
        {{"method": "GET|POST|etc", "path": "/path", "description": "what it does"}}
    ],
    "patterns": ["design patterns to use"],
    "considerations": {{
        "security": ["security considerations"],
        "performance": ["performance considerations"],
        "scalability": ["scalability considerations"]
    }}
}}"""

        try:
            architecture = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            # Fallback architecture
            architecture = self._default_architecture()
        
        # Store in memory
        self.store_output(
            type=MemoryType.ARCHITECTURE,
            content=architecture,
            metadata={"version": "1.0"},
        )
        
        return {"status": "success", "architecture": architecture}
    
    def define_api_contracts(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Define API contracts for the system.
        
        Args:
            input_data: Architecture and requirements
            
        Returns:
            API specification
        """
        context = self.get_context()
        arch = context.get("architecture", {})
        
        prompt = f"""Define detailed API contracts based on this architecture:

Architecture:
{json.dumps(arch, indent=2)}

Return JSON with OpenAPI-style specification:
{{
    "base_url": "/api/v1",
    "endpoints": [
        {{
            "path": "/resource",
            "method": "GET",
            "summary": "description",
            "parameters": [{{"name": "param", "type": "string", "required": true}}],
            "request_body": {{"field": "type"}},
            "responses": {{
                "200": {{"description": "success", "schema": {{}}}},
                "400": {{"description": "bad request"}}
            }}
        }}
    ]
}}"""

        try:
            api_spec = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            api_spec = {"base_url": "/api/v1", "endpoints": []}
        
        self.store_output(
            type=MemoryType.ARCHITECTURE,
            content=api_spec,
            metadata={"type": "api_contract"},
        )
        
        return {"status": "success", "api_spec": api_spec}
    
    def recommend_tech_stack(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend technology stack for the project.
        
        Args:
            input_data: Project requirements
            
        Returns:
            Technology recommendations
        """
        requirements = input_data.get("requirements", "")
        constraints = input_data.get("constraints", [])
        
        prompt = f"""Recommend the best technology stack for this project:

Requirements:
{requirements}

Constraints:
{json.dumps(constraints, indent=2)}

Consider:
- Team expertise (assume general full-stack experience)
- Project timeline (assume moderate timeline)
- Scalability needs
- Community support and documentation

Return JSON with:
{{
    "recommendation": {{
        "backend": {{"choice": "name", "version": "x.x", "rationale": "why"}},
        "frontend": {{"choice": "name", "version": "x.x", "rationale": "why"}},
        "database": {{"choice": "name", "type": "sql|nosql", "rationale": "why"}},
        "hosting": {{"choice": "name", "rationale": "why"}}
    }},
    "alternatives": [
        {{"component": "backend", "alternative": "name", "trade_offs": "pros/cons"}}
    ]
}}"""

        try:
            stack = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            stack = self._default_stack()
        
        return {"status": "success", "tech_stack": stack}
    
    def generic_architecture(self, task: Task) -> Dict[str, Any]:
        """Handle generic architecture tasks."""
        context = self.get_context()
        
        prompt = f"""Complete this architecture task:

Task: {task.name}
Description: {task.description}

Context:
{json.dumps(context, indent=2)}

Provide your architectural decision as structured JSON."""

        response = self.think(prompt)
        
        return {"status": "success", "result": response}
    
    def _default_architecture(self) -> Dict[str, Any]:
        """Return a sensible default architecture."""
        return {
            "overview": "Modern web application with REST API backend and SPA frontend",
            "tech_stack": {
                "backend": {
                    "framework": "FastAPI",
                    "language": "Python 3.11",
                    "rationale": "High performance, easy to use, great documentation",
                },
                "frontend": {
                    "framework": "React",
                    "language": "TypeScript",
                    "rationale": "Component-based, large ecosystem, type safety",
                },
                "database": {
                    "type": "PostgreSQL",
                    "name": "PostgreSQL 15",
                    "rationale": "Reliable, feature-rich, great for complex queries",
                },
                "additional": ["Redis for caching", "Docker for containerization"],
            },
            "project_structure": {
                "folders": ["backend/", "frontend/", "tests/", "docs/"],
                "key_files": {
                    "backend/main.py": "Application entry point",
                    "backend/models.py": "Database models",
                    "backend/routes/": "API route handlers",
                    "frontend/src/App.tsx": "React app root",
                    "frontend/src/components/": "UI components",
                },
            },
            "components": [],
            "data_models": [],
            "api_endpoints": [],
            "patterns": ["Repository Pattern", "Dependency Injection", "REST"],
            "considerations": {
                "security": ["Input validation", "Authentication", "HTTPS"],
                "performance": ["Database indexing", "Caching", "Pagination"],
                "scalability": ["Stateless design", "Horizontal scaling ready"],
            },
        }
    
    def _default_stack(self) -> Dict[str, Any]:
        """Return default technology stack."""
        return {
            "recommendation": {
                "backend": {
                    "choice": "FastAPI",
                    "version": "0.100+",
                    "rationale": "Modern Python framework with async support",
                },
                "frontend": {
                    "choice": "React",
                    "version": "18+",
                    "rationale": "Industry standard with large ecosystem",
                },
                "database": {
                    "choice": "PostgreSQL",
                    "type": "sql",
                    "rationale": "Reliable and feature-rich",
                },
                "hosting": {
                    "choice": "Docker + Cloud",
                    "rationale": "Portable and scalable",
                },
            },
            "alternatives": [],
        }
