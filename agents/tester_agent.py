"""
Tester Agent - QA Engineer Role.

Responsible for generating tests, validating code,
and ensuring quality.
"""

import json
import re
from typing import Any, Dict, List
from .base_agent import BaseAgent
from core.memory import MemoryType
from core.task_queue import Task


class TesterAgent(BaseAgent):
    """
    Tester Agent handles quality assurance.
    
    Responsibilities:
    - Generate unit tests
    - Create integration tests
    - Validate API endpoints
    - Run test suites
    - Report bugs and issues
    """
    
    def _get_responsibilities(self) -> str:
        return """- Generate comprehensive unit and integration tests
- Validate API endpoints work correctly
- Test edge cases and error handling
- Ensure code coverage targets are met
- Report bugs with clear reproduction steps
- Verify fixes resolve reported issues"""
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a testing task."""
        if task.name == "generate_tests":
            return self.generate_tests(task.input_data)
        elif task.name == "validate_api":
            return self.validate_api(task.input_data)
        elif task.name == "run_tests":
            return self.run_tests(task.input_data)
        else:
            return self.generic_testing(task)
    
    def generate_tests(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate tests for the codebase.
        
        Args:
            input_data: Code and specifications
            
        Returns:
            Generated test files
        """
        context = self.get_context()
        code_files = context.get("code", [])
        
        prompt = f"""Generate comprehensive tests for this codebase:

Code Files:
{json.dumps(code_files, indent=2)}

Architecture:
{json.dumps(context.get('architecture', {}), indent=2)}

Generate:
1. Unit tests (test_unit.py) - Test individual functions
2. Integration tests (test_integration.py) - Test API endpoints
3. Test fixtures (conftest.py) - Pytest fixtures

Requirements:
- Use pytest as the testing framework
- Include edge cases and error conditions
- Mock external dependencies
- Aim for high code coverage
- Include docstrings explaining each test

Format: Separate each file with "### FILENAME: filename.py" header."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_test_files(response)
        
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.TEST,
                content=code,
                metadata={"filename": filename},
            )
        
        return {"status": "success", "files": files}
    
    def validate_api(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate API endpoints.
        
        Args:
            input_data: API specification
            
        Returns:
            Validation results and test cases
        """
        context = self.get_context()
        arch = context.get("architecture", {})
        endpoints = arch.get("api_endpoints", [])
        
        prompt = f"""Generate API validation tests for these endpoints:

Endpoints:
{json.dumps(endpoints, indent=2)}

Generate pytest tests that validate:
1. Correct status codes
2. Response schema validation
3. Error handling (400, 404, 500 cases)
4. Authentication if required
5. Input validation

Use FastAPI TestClient for testing."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_test_files(response)
        
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.TEST,
                content=code,
                metadata={"filename": filename, "type": "api_validation"},
            )
        
        return {"status": "success", "files": files}
    
    def run_tests(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate running tests and analyze results.
        
        In a real system, this would execute pytest.
        Here we analyze test code for potential issues.
        
        Args:
            input_data: Test configuration
            
        Returns:
            Test analysis results
        """
        context = self.get_context()
        tests = context.get("tests", [])
        code = context.get("code", [])
        
        prompt = f"""Analyze these tests and code for potential issues:

Tests:
{json.dumps(tests, indent=2)}

Code:
{json.dumps(code, indent=2)}

Identify:
1. Tests that might fail
2. Missing test coverage
3. Potential bugs in the code
4. Edge cases not tested

Return JSON:
{{
    "analysis": {{
        "test_count": number,
        "coverage_estimate": "low|medium|high",
        "potential_failures": [
            {{"test": "name", "reason": "why it might fail"}}
        ],
        "missing_coverage": ["areas not tested"],
        "potential_bugs": [
            {{"location": "file/line", "description": "bug description"}}
        ],
        "recommendations": ["improvement suggestions"]
    }}
}}"""

        try:
            analysis = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            analysis = {
                "analysis": {
                    "test_count": len(tests),
                    "coverage_estimate": "unknown",
                    "potential_failures": [],
                    "missing_coverage": [],
                    "potential_bugs": [],
                    "recommendations": ["Manual review recommended"],
                }
            }
        
        return {"status": "success", "results": analysis}
    
    def generic_testing(self, task: Task) -> Dict[str, Any]:
        """Handle generic testing tasks."""
        context = self.get_context()
        
        prompt = f"""Complete this testing task:

Task: {task.name}
Description: {task.description}

Context:
{json.dumps(context, indent=2)}

Generate appropriate tests or analysis."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,
        )
        
        files = self._parse_test_files(response)
        
        if files:
            for filename, code in files.items():
                self.store_output(
                    type=MemoryType.TEST,
                    content=code,
                    metadata={"filename": filename, "task": task.name},
                )
            return {"status": "success", "files": files}
        else:
            return {"status": "success", "result": response}
    
    def _parse_test_files(self, response: str) -> Dict[str, str]:
        """Parse LLM response into test files."""
        files = {}
        
        file_pattern = r'###\s*FILENAME:\s*([^\n]+)'
        parts = re.split(file_pattern, response)
        
        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    filename = parts[i].strip()
                    code = self._extract_code(parts[i + 1])
                    if code:
                        files[filename] = code
        else:
            code_blocks = re.findall(r'```python\n(.*?)```', response, re.DOTALL)
            for i, code in enumerate(code_blocks):
                files[f"test_{i + 1}.py"] = code.strip()
        
        return files
    
    def _extract_code(self, text: str) -> str:
        """Extract code from text."""
        match = re.search(r'```\w*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
    
    def report_bug(
        self,
        description: str,
        code_location: str,
        reproduction_steps: List[str],
        severity: str = "medium",
    ) -> str:
        """
        Create a bug report and store in memory.
        
        Args:
            description: Bug description
            code_location: Where the bug is
            reproduction_steps: How to reproduce
            severity: Bug severity level
            
        Returns:
            Bug report ID
        """
        bug_report = {
            "description": description,
            "location": code_location,
            "reproduction_steps": reproduction_steps,
            "severity": severity,
            "status": "open",
        }
        
        return self.store_output(
            type=MemoryType.BUG_REPORT,
            content=bug_report,
            metadata={"severity": severity},
        )
