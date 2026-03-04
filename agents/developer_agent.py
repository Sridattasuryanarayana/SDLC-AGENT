"""
Developer Agent - Software Developer Role.

Responsible for implementing backend and frontend code
based on architecture specifications.
"""

import json
import re
from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent
from core.memory import MemoryType
from core.task_queue import Task


class DeveloperAgent(BaseAgent):
    """
    Developer Agent handles code implementation.
    
    Responsibilities:
    - Write backend API code
    - Create frontend components
    - Implement database models
    - Handle business logic
    - Follow architectural decisions
    """
    
    def _get_responsibilities(self) -> str:
        return """- Implement clean, maintainable, and well-documented code
- Follow the architectural decisions and patterns specified
- Write backend API endpoints with proper error handling
- Create frontend components with good UX practices
- Implement database models and migrations
- Follow security best practices
- Write self-documenting code with appropriate comments"""
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a development task."""
        if task.name == "implement_backend":
            return self.implement_backend(task.input_data)
        elif task.name == "implement_frontend":
            return self.implement_frontend(task.input_data)
        elif task.name == "implement_models":
            return self.implement_models(task.input_data)
        elif task.name == "implement_feature":
            return self.implement_feature(task.input_data)
        else:
            return self.generic_development(task)
    
    def implement_backend(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement backend API code.
        
        Args:
            input_data: Architecture and requirements
            
        Returns:
            Generated backend code files
        """
        context = self.get_context()
        arch = context.get("architecture", {})
        
        prompt = f"""Implement the backend API based on this architecture:

Architecture:
{json.dumps(arch, indent=2)}

Requirements:
{json.dumps(context.get('requirements', []), indent=2)}

Generate the following files:
1. main.py - FastAPI application entry point
2. models.py - Pydantic models and database schemas
3. routes.py - API route handlers
4. database.py - Database connection and session management

For each file, provide complete, production-ready code.
Format: Separate each file with "### FILENAME: filename.py" header."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        # Parse the response into separate files
        files = self._parse_code_files(response)
        
        # Store each file in memory
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.CODE,
                content=code,
                metadata={"filename": filename, "type": "backend"},
            )
        
        return {"status": "success", "files": files}
    
    def implement_frontend(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement frontend UI code.
        
        Args:
            input_data: Architecture and requirements
            
        Returns:
            Generated frontend code files
        """
        context = self.get_context()
        arch = context.get("architecture", {})
        
        prompt = f"""Implement the frontend UI based on this architecture:

Architecture:
{json.dumps(arch, indent=2)}

Requirements:
{json.dumps(context.get('requirements', []), indent=2)}

Generate the following files:
1. App.tsx - Main React application component
2. api.ts - API client functions
3. types.ts - TypeScript type definitions
4. components/TaskList.tsx - Main feature component

For each file, provide complete, production-ready code.
Use modern React patterns (hooks, functional components).
Format: Separate each file with "### FILENAME: filename.tsx" header."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_code_files(response)
        
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.CODE,
                content=code,
                metadata={"filename": filename, "type": "frontend"},
            )
        
        return {"status": "success", "files": files}
    
    def implement_models(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement database models.
        
        Args:
            input_data: Model specifications
            
        Returns:
            Generated model code
        """
        context = self.get_context()
        arch = context.get("architecture", {})
        data_models = arch.get("data_models", [])
        
        prompt = f"""Implement database models based on these specifications:

Data Models:
{json.dumps(data_models, indent=2)}

Tech Stack:
- Backend: {arch.get('tech_stack', {}).get('backend', {}).get('framework', 'FastAPI')}
- Database: {arch.get('tech_stack', {}).get('database', {}).get('type', 'PostgreSQL')}

Generate:
1. SQLAlchemy models (models.py)
2. Pydantic schemas for API (schemas.py)
3. Database migrations if needed

Use modern Python type hints and best practices."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_code_files(response)
        
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.CODE,
                content=code,
                metadata={"filename": filename, "type": "models"},
            )
        
        return {"status": "success", "files": files}
    
    def implement_feature(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement a specific feature.
        
        Args:
            input_data: Feature specification
            
        Returns:
            Generated feature code
        """
        feature_name = input_data.get("name", "feature")
        description = input_data.get("description", "")
        context = self.get_context()
        
        prompt = f"""Implement this feature:

Feature: {feature_name}
Description: {description}

Existing Code Context:
{json.dumps([c['file'] for c in context.get('code', [])], indent=2)}

Architecture:
{json.dumps(context.get('architecture', {}), indent=2)}

Generate all necessary code changes/additions.
Format: Separate each file with "### FILENAME: filename.ext" header."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_code_files(response)
        
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.CODE,
                content=code,
                metadata={"filename": filename, "feature": feature_name},
            )
        
        return {"status": "success", "files": files, "feature": feature_name}
    
    def generic_development(self, task: Task) -> Dict[str, Any]:
        """Handle generic development tasks."""
        context = self.get_context()
        
        prompt = f"""Complete this development task:

Task: {task.name}
Description: {task.description}

Input:
{json.dumps(task.input_data, indent=2)}

Context:
{json.dumps(context, indent=2)}

Generate the required code."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_code_files(response)
        
        if files:
            for filename, code in files.items():
                self.store_output(
                    type=MemoryType.CODE,
                    content=code,
                    metadata={"filename": filename, "task": task.name},
                )
            return {"status": "success", "files": files}
        else:
            return {"status": "success", "result": response}
    
    def _parse_code_files(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response into separate code files.
        
        Args:
            response: Raw LLM response with code blocks
            
        Returns:
            Dictionary of filename to code content
        """
        files = {}
        
        # Pattern for explicit file headers
        file_pattern = r'###\s*FILENAME:\s*([^\n]+)'
        parts = re.split(file_pattern, response)
        
        if len(parts) > 1:
            # Response has explicit file markers
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    filename = parts[i].strip()
                    code = self._extract_code(parts[i + 1])
                    if code:
                        files[filename] = code
        else:
            # Try to extract code blocks with language hints
            code_blocks = re.findall(
                r'```(\w+)?\n(.*?)```',
                response,
                re.DOTALL
            )
            
            for i, (lang, code) in enumerate(code_blocks):
                ext = self._get_extension(lang)
                filename = f"generated_{i + 1}.{ext}"
                files[filename] = code.strip()
        
        return files
    
    def _extract_code(self, text: str) -> Optional[str]:
        """Extract code from markdown code blocks."""
        # Try to find code block
        match = re.search(r'```\w*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Return cleaned text if no code block
        return text.strip() if text.strip() else None
    
    def _get_extension(self, language: Optional[str]) -> str:
        """Get file extension for a language."""
        extensions = {
            "python": "py",
            "py": "py",
            "javascript": "js",
            "js": "js",
            "typescript": "ts",
            "ts": "ts",
            "tsx": "tsx",
            "jsx": "jsx",
            "json": "json",
            "sql": "sql",
            "html": "html",
            "css": "css",
        }
        return extensions.get(language.lower() if language else "", "txt")
    
    def refactor_code(self, code: str, instructions: str) -> str:
        """
        Refactor existing code based on instructions.
        
        Args:
            code: Existing code to refactor
            instructions: Refactoring instructions
            
        Returns:
            Refactored code
        """
        prompt = f"""Refactor this code following these instructions:

Instructions: {instructions}

Code:
```
{code}
```

Return the refactored code. Maintain the same functionality unless instructed otherwise."""

        return self.generate_code(prompt)
