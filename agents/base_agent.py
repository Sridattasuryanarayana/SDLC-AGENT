"""
Base Agent Class.

All specialized agents inherit from this base class,
which provides common functionality for LLM interaction
and memory access.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from core.memory import SharedMemory, MemoryType
from core.task_queue import Task
from core.llm_client import LLMClient


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-agent system.
    
    Each agent has:
    - A name and role
    - Access to shared memory
    - An LLM client for reasoning
    - Methods to execute tasks
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        llm_client: LLMClient,
        memory: SharedMemory,
    ):
        """
        Initialize the agent.
        
        Args:
            name: Unique agent name
            role: Description of agent's role
            llm_client: LLM client for generation
            memory: Shared memory store
        """
        self.name = name
        self.role = role
        self.llm = llm_client
        self.memory = memory
        self._system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for this agent."""
        return f"""You are {self.name}, a {self.role} in a multi-agent software development team.

Your responsibilities:
{self._get_responsibilities()}

Guidelines:
- Be concise and precise in your outputs
- Follow best practices for software development
- Coordinate with other agents through the shared task system
- Always explain your reasoning briefly

When generating code:
- Use modern, idiomatic patterns
- Include appropriate error handling
- Add comments for complex logic
- Consider edge cases
"""
    
    @abstractmethod
    def _get_responsibilities(self) -> str:
        """Return a description of this agent's responsibilities."""
        pass
    
    @abstractmethod
    def execute(self, task: Task) -> Dict[str, Any]:
        """
        Execute a task assigned to this agent.
        
        Args:
            task: The task to execute
            
        Returns:
            Dictionary with execution results
        """
        pass
    
    def get_context(self) -> Dict[str, Any]:
        """Get relevant context from shared memory."""
        return self.memory.get_context_for_agent(self.name)
    
    def store_output(
        self,
        type: MemoryType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store output in shared memory."""
        return self.memory.store(
            type=type,
            content=content,
            agent=self.name,
            metadata=metadata,
        )
    
    def think(self, prompt: str, context: Optional[str] = None) -> str:
        """
        Use LLM to reason about a problem.
        
        Args:
            prompt: The thinking prompt
            context: Optional additional context
            
        Returns:
            The LLM's response
        """
        full_prompt = prompt
        if context:
            full_prompt = f"Context:\n{context}\n\n{prompt}"
        
        return self.llm.chat(
            user_message=full_prompt,
            system_prompt=self._system_prompt,
        )
    
    def generate_code(self, specification: str) -> str:
        """
        Generate code based on a specification.
        
        Args:
            specification: What the code should do
            
        Returns:
            Generated code
        """
        prompt = f"""Generate production-ready code for the following specification:

{specification}

Return ONLY the code, wrapped in appropriate markdown code blocks.
Include necessary imports and type hints."""

        return self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
            temperature=0.3,  # Lower temperature for code
        )
    
    def analyze(self, content: str, question: str) -> str:
        """
        Analyze content and answer a question about it.
        
        Args:
            content: Content to analyze
            question: Question to answer
            
        Returns:
            Analysis result
        """
        prompt = f"""Analyze the following content and answer the question.

Content:
{content}

Question: {question}"""

        return self.llm.chat(
            user_message=prompt,
            system_prompt=self._system_prompt,
        )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, role={self.role})"
