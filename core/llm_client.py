"""
LLM Client for Agent Intelligence.

This module provides a unified interface for different LLM providers,
allowing agents to use OpenAI, Anthropic, or local models.
"""

import os
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Any = None


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            raw_response=response,
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        # Extract system message if present
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=chat_messages,
        )
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            raw_response=response,
        )


class WAIPProvider(BaseLLMProvider):
    """WAIP (Wipro AI Platform) provider."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.waip.wiprocms.com", model: str = "gpt-4o"):
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except ImportError:
            raise ImportError("Please install requests: pip install requests")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.conversation_history = []
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import requests
        
        url = f"{self.base_url}/v1.1/skills/completion/query"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "messages": messages,
            "skill_parameters": {
                "model_name": self.model,
                "emb_type": "openai",
                "max_output_tokens": max_tokens
            },
            "stream_response": False
        }
        
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=300)
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data['data']['content'].strip(),
            model=self.model,
            usage={
                "prompt_tokens": data.get('usage', {}).get('prompt_tokens', 0),
                "completion_tokens": data.get('usage', {}).get('completion_tokens', 0),
                "total_tokens": data.get('usage', {}).get('total_tokens', 0),
            },
            raw_response=data,
        )


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM provider (Ollama, etc.)."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "codellama"):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        try:
            import requests
        except ImportError:
            raise ImportError("Please install requests: pip install requests")
        
        # Format for Ollama API
        prompt = self._format_messages(messages)
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data.get("response", ""),
            model=self.model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            raw_response=data,
        )
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into a single prompt."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n\n".join(parts)


class MockLLMProvider(BaseLLMProvider):
    """Mock provider for testing without API calls."""
    
    def __init__(self):
        self.call_count = 0
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self.call_count += 1
        
        # Analyze the last user message to provide contextual mock response
        last_message = messages[-1]["content"] if messages else ""
        
        # Generate mock responses based on context
        if "architecture" in last_message.lower():
            content = self._mock_architecture_response()
        elif "test" in last_message.lower():
            content = self._mock_test_response()
        elif "task" in last_message.lower() or "plan" in last_message.lower():
            content = self._mock_planning_response()
        elif "debug" in last_message.lower() or "fix" in last_message.lower():
            content = self._mock_debug_response()
        else:
            content = self._mock_code_response()
        
        return LLMResponse(
            content=content,
            model="mock-model",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )
    
    def _mock_planning_response(self) -> str:
        return json.dumps({
            "tasks": [
                {"name": "Design Architecture", "agent": "architect"},
                {"name": "Implement Backend", "agent": "developer"},
                {"name": "Implement Frontend", "agent": "developer"},
                {"name": "Write Tests", "agent": "tester"},
            ]
        })
    
    def _mock_architecture_response(self) -> str:
        return json.dumps({
            "backend": {"framework": "FastAPI", "language": "Python"},
            "frontend": {"framework": "React", "language": "TypeScript"},
            "database": "PostgreSQL",
            "structure": {
                "backend/": ["main.py", "models.py", "routes.py"],
                "frontend/": ["App.tsx", "components/"],
                "tests/": ["test_api.py"],
            }
        })
    
    def _mock_code_response(self) -> str:
        return '''```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Task(BaseModel):
    id: int
    title: str
    completed: bool = False

tasks: List[Task] = []

@app.get("/tasks")
def get_tasks():
    return tasks

@app.post("/tasks")
def create_task(task: Task):
    tasks.append(task)
    return task
```'''
    
    def _mock_test_response(self) -> str:
        return '''```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_tasks():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_task():
    response = client.post("/tasks", json={"id": 1, "title": "Test", "completed": False})
    assert response.status_code == 200
```'''
    
    def _mock_debug_response(self) -> str:
        return json.dumps({
            "analysis": "The error is caused by missing validation",
            "fix": "Add input validation to the endpoint",
            "code_changes": [
                {"file": "main.py", "change": "Add Pydantic model validation"}
            ]
        })


class LLMClient:
    """
    Unified LLM client that can use different providers.
    
    Usage:
        client = LLMClient(provider="openai", api_key="...")
        response = client.chat("Write a Python function...")
    """
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the LLM client.
        
        Args:
            provider: One of "openai", "anthropic", "local", or "mock"
            api_key: API key for the provider
            model: Model name to use
            base_url: Base URL for local providers
        """
        self.provider_name = provider
        
        if provider == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY")
            mdl = model or os.getenv("OPENAI_MODEL", "gpt-4")
            if not key:
                raise ValueError("OpenAI API key required")
            self.provider = OpenAIProvider(api_key=key, model=mdl)
            
        elif provider == "anthropic":
            key = api_key or os.getenv("ANTHROPIC_API_KEY")
            mdl = model or os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            if not key:
                raise ValueError("Anthropic API key required")
            self.provider = AnthropicProvider(api_key=key, model=mdl)
            
        elif provider == "local":
            url = base_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
            mdl = model or os.getenv("LOCAL_LLM_MODEL", "codellama")
            self.provider = LocalLLMProvider(base_url=url, model=mdl)
        
        elif provider == "waip":
            key = api_key or os.getenv("WAIP_API_KEY")
            url = base_url or os.getenv("WAIP_API_ENDPOINT", "https://api.waip.wiprocms.com")
            mdl = model or os.getenv("WAIP_MODEL", "gpt-4o")
            if not key:
                raise ValueError("WAIP API key required")
            self.provider = WAIPProvider(api_key=key, base_url=url, model=mdl)
            
        elif provider == "mock":
            self.provider = MockLLMProvider()
            
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a chat message and get a response.
        
        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            history: Optional conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            The assistant's response text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": user_message})
        
        response = self.provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return response.content
    
    def generate_json(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Generate a JSON response.
        
        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            temperature: Lower for more deterministic output
            
        Returns:
            Parsed JSON dictionary
        """
        if system_prompt:
            system_prompt += "\n\nRespond ONLY with valid JSON, no other text."
        else:
            system_prompt = "Respond ONLY with valid JSON, no other text."
        
        response = self.chat(
            user_message=user_message,
            system_prompt=system_prompt,
            temperature=temperature,
        )
        
        # Try to extract JSON from response
        content = response.strip()
        
        # Handle markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        return json.loads(content.strip())
