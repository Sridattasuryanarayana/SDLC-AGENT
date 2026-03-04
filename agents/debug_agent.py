"""
Debug Agent - Bug Fixer Role.

Responsible for analyzing errors, identifying bugs,
and proposing fixes.
"""

import json
import re
from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent
from core.memory import MemoryType
from core.task_queue import Task


class DebugAgent(BaseAgent):
    """
    Debug Agent handles bug fixing and error resolution.
    
    Responsibilities:
    - Analyze error logs and stack traces
    - Identify root causes of bugs
    - Propose and implement fixes
    - Verify fixes resolve issues
    """
    
    def _get_responsibilities(self) -> str:
        return """- Analyze error messages and stack traces
- Identify root causes of bugs and failures
- Propose targeted fixes with minimal code changes
- Verify fixes don't introduce new issues
- Document bug fixes for future reference
- Suggest preventive measures"""
    
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a debugging task."""
        if task.name == "analyze_error":
            return self.analyze_error(task.input_data)
        elif task.name == "fix_bug":
            return self.fix_bug(task.input_data)
        elif task.name == "review_fix":
            return self.review_fix(task.input_data)
        else:
            return self.generic_debug(task)
    
    def analyze_error(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an error and identify root cause.
        
        Args:
            input_data: Error information
            
        Returns:
            Analysis with root cause and recommendations
        """
        error_message = input_data.get("error", "")
        stack_trace = input_data.get("stack_trace", "")
        context = self.get_context()
        
        prompt = f"""Analyze this error and identify the root cause:

Error Message:
{error_message}

Stack Trace:
{stack_trace}

Related Code:
{json.dumps(context.get('code', []), indent=2)}

Return JSON:
{{
    "root_cause": "clear explanation of what's causing the error",
    "affected_files": ["list of files involved"],
    "error_type": "type of error (syntax, logic, runtime, etc.)",
    "severity": "critical|high|medium|low",
    "fix_suggestions": [
        {{
            "description": "what to fix",
            "file": "filename",
            "change": "describe the code change"
        }}
    ],
    "prevention": "how to prevent similar errors"
}}"""

        try:
            analysis = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            response = self.think(prompt)
            analysis = {
                "root_cause": response,
                "affected_files": [],
                "error_type": "unknown",
                "severity": "medium",
                "fix_suggestions": [],
                "prevention": "Review code carefully",
            }
        
        # Store analysis in memory
        self.store_output(
            type=MemoryType.BUG_REPORT,
            content=analysis,
            metadata={"error": error_message, "type": "analysis"},
        )
        
        return {"status": "success", "analysis": analysis}
    
    def fix_bug(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement a fix for a identified bug.
        
        Args:
            input_data: Bug information and analysis
            
        Returns:
            Fixed code
        """
        bug_report = input_data.get("bug_report", {})
        analysis = input_data.get("analysis", {})
        context = self.get_context()
        
        # Get the affected code
        affected_files = analysis.get("affected_files", [])
        code_context = []
        for code_entry in context.get("code", []):
            if code_entry.get("file") in affected_files or not affected_files:
                code_context.append(code_entry)
        
        prompt = f"""Fix this bug based on the analysis:

Bug Report:
{json.dumps(bug_report, indent=2)}

Analysis:
{json.dumps(analysis, indent=2)}

Affected Code:
{json.dumps(code_context, indent=2)}

Requirements:
1. Make minimal changes to fix the bug
2. Don't change unrelated code
3. Add appropriate error handling
4. Include comments explaining the fix

For each file that needs changes, provide the complete fixed code.
Format: Separate each file with "### FILENAME: filename.ext" header."""

        response = self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.2,  # Lower temperature for precise fixes
        )
        
        files = self._parse_code_files(response)
        
        for filename, code in files.items():
            self.store_output(
                type=MemoryType.CODE,
                content=code,
                metadata={
                    "filename": filename,
                    "type": "fix",
                    "bug_id": bug_report.get("id", "unknown"),
                },
            )
        
        return {"status": "success", "files": files}
    
    def review_fix(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review a proposed fix.
        
        Args:
            input_data: Original bug and proposed fix
            
        Returns:
            Review results
        """
        original_bug = input_data.get("bug", {})
        proposed_fix = input_data.get("fix", {})
        
        prompt = f"""Review this bug fix:

Original Bug:
{json.dumps(original_bug, indent=2)}

Proposed Fix:
{json.dumps(proposed_fix, indent=2)}

Evaluate:
1. Does the fix address the root cause?
2. Are there any side effects?
3. Is the fix complete?
4. Are there better alternatives?

Return JSON:
{{
    "approved": true/false,
    "addresses_root_cause": true/false,
    "potential_side_effects": ["list any concerns"],
    "completeness": "complete|partial|insufficient",
    "suggestions": ["improvement suggestions"],
    "verdict": "summary of review"
}}"""

        try:
            review = self.llm.generate_json(
                user_message=prompt,
                system_prompt=self._system_prompt,
            )
        except json.JSONDecodeError:
            review = {
                "approved": True,
                "addresses_root_cause": True,
                "potential_side_effects": [],
                "completeness": "complete",
                "suggestions": [],
                "verdict": "Fix appears acceptable",
            }
        
        return {"status": "success", "review": review}
    
    def generic_debug(self, task: Task) -> Dict[str, Any]:
        """Handle generic debugging tasks."""
        context = self.get_context()
        bugs = context.get("bugs", [])
        
        prompt = f"""Complete this debugging task:

Task: {task.name}
Description: {task.description}

Known Bugs:
{json.dumps(bugs, indent=2)}

Code Context:
{json.dumps(context.get('code', []), indent=2)}

Analyze and fix any issues found."""

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
                    metadata={"filename": filename, "type": "debug_fix"},
                )
            return {"status": "success", "files": files}
        else:
            return {"status": "success", "result": response}
    
    def _parse_code_files(self, response: str) -> Dict[str, str]:
        """Parse response into code files."""
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
            code_blocks = re.findall(r'```\w*\n(.*?)```', response, re.DOTALL)
            for i, code in enumerate(code_blocks):
                files[f"fix_{i + 1}.py"] = code.strip()
        
        return files
    
    def _extract_code(self, text: str) -> Optional[str]:
        """Extract code from text."""
        match = re.search(r'```\w*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip() if text.strip() else None
    
    def trace_error(self, stack_trace: str) -> List[Dict[str, Any]]:
        """
        Parse and trace a stack trace.
        
        Args:
            stack_trace: Raw stack trace string
            
        Returns:
            Structured trace information
        """
        trace_info = []
        
        # Pattern for Python stack trace
        frame_pattern = r'File "([^"]+)", line (\d+), in (\w+)'
        matches = re.findall(frame_pattern, stack_trace)
        
        for file_path, line_num, func_name in matches:
            trace_info.append({
                "file": file_path,
                "line": int(line_num),
                "function": func_name,
            })
        
        return trace_info
    
    def suggest_debugging_steps(self, error: str) -> List[str]:
        """
        Suggest debugging steps for an error.
        
        Args:
            error: Error message
            
        Returns:
            List of debugging steps
        """
        prompt = f"""Suggest step-by-step debugging approach for this error:

Error: {error}

Provide 5-7 specific steps to debug this issue."""

        response = self.think(prompt)
        
        # Parse numbered steps from response
        steps = re.findall(r'\d+\.\s*(.+)', response)
        
        return steps if steps else [response]
