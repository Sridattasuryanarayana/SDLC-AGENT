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
        msg_lower = last_message.lower()
        
        # Check system prompt for mode hints first
        sys_lower = ""
        for m in messages:
            if m.get("role") == "system":
                sys_lower = m["content"].lower()
                break

        # Order matters: RAG/explain prompts embed full code context that may
        # contain generic keywords like "implement", so detect them FIRST via
        # distinctive phrases that only the explain/enhance prompts use.
        if "code analyst" in msg_lower or "code analyst" in sys_lower:
            content = self._mock_explain_response()
        elif "code enhancer" in msg_lower or "enhancement approach" in msg_lower:
            content = self._mock_explain_response()
        elif "implement" in msg_lower and "backend" in msg_lower and "full code context" not in msg_lower:
            content = self._mock_backend_code()
        elif "implement" in msg_lower and "frontend" in msg_lower and "full code context" not in msg_lower:
            content = self._mock_frontend_code()
        elif any(k in msg_lower for k in ("implement", "generate the following files", "### filename")):
            content = self._mock_backend_code()
        elif "test" in msg_lower:
            content = self._mock_test_response()
        elif "debug" in msg_lower or "fix" in msg_lower:
            content = self._mock_debug_response()
        elif "task" in msg_lower or "plan" in msg_lower:
            content = self._mock_planning_response()
        elif "architecture" in msg_lower or "design" in msg_lower:
            content = self._mock_architecture_response()
        elif "explain" in msg_lower or "analyze" in msg_lower:
            content = self._mock_explain_response()
        else:
            content = self._mock_backend_code()
        
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
        return self._mock_backend_code()
    
    def _mock_backend_code(self) -> str:
        return '''### FILENAME: backend/main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

app = FastAPI(title="SDLC Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### FILENAME: backend/models.py
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO

class TaskResponse(TaskCreate):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class TaskList(BaseModel):
    tasks: List[TaskResponse]
    total: int
```

### FILENAME: backend/routes.py
```python
from fastapi import APIRouter, HTTPException
from typing import List
from models import TaskCreate, TaskResponse, TaskStatus
from database import get_db

router = APIRouter()

@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks():
    db = get_db()
    return db.get_all_tasks()

@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate):
    db = get_db()
    return db.create_task(task)

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int):
    db = get_db()
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: TaskCreate):
    db = get_db()
    updated = db.update_task(task_id, task)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated

@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    db = get_db()
    if not db.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
```

### FILENAME: backend/database.py
```python
from typing import Optional, List
from datetime import datetime
from models import TaskCreate, TaskResponse

class InMemoryDB:
    def __init__(self):
        self._tasks = {}
        self._counter = 0

    def create_task(self, task: TaskCreate) -> TaskResponse:
        self._counter += 1
        record = TaskResponse(
            id=self._counter,
            title=task.title,
            description=task.description,
            status=task.status,
            created_at=datetime.utcnow(),
        )
        self._tasks[self._counter] = record
        return record

    def get_task(self, task_id: int) -> Optional[TaskResponse]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[TaskResponse]:
        return list(self._tasks.values())

    def update_task(self, task_id: int, data: TaskCreate) -> Optional[TaskResponse]:
        if task_id not in self._tasks:
            return None
        existing = self._tasks[task_id]
        updated = TaskResponse(
            id=task_id,
            title=data.title,
            description=data.description,
            status=data.status,
            created_at=existing.created_at,
            updated_at=datetime.utcnow(),
        )
        self._tasks[task_id] = updated
        return updated

    def delete_task(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None

_db = InMemoryDB()

def get_db() -> InMemoryDB:
    return _db
```'''
    
    def _mock_frontend_code(self) -> str:
        return '''### FILENAME: frontend/src/App.tsx
```typescript
import React, { useEffect, useState } from "react";
import { TaskList } from "./components/TaskList";
import { Task, fetchTasks, createTask } from "./api";

export default function App() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [title, setTitle] = useState("");

    useEffect(() => {
        fetchTasks().then(setTasks);
    }, []);

    const handleAdd = async () => {
        if (!title.trim()) return;
        const task = await createTask({ title, status: "todo" });
        setTasks((prev) => [...prev, task]);
        setTitle("");
    };

    return (
        <div className="app">
            <h1>Task Manager</h1>
            <div className="add-task">
                <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="New task..." />
                <button onClick={handleAdd}>Add</button>
            </div>
            <TaskList tasks={tasks} />
        </div>
    );
}
```

### FILENAME: frontend/src/api.ts
```typescript
export interface Task {
    id: number;
    title: string;
    description?: string;
    status: "todo" | "in_progress" | "done";
    created_at: string;
}

const API_BASE = "/api";

export async function fetchTasks(): Promise<Task[]> {
    const res = await fetch(`${API_BASE}/tasks`);
    return res.json();
}

export async function createTask(data: Partial<Task>): Promise<Task> {
    const res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    return res.json();
}
```

### FILENAME: frontend/src/types.ts
```typescript
export interface Task {
    id: number;
    title: string;
    description?: string;
    status: "todo" | "in_progress" | "done";
    created_at: string;
    updated_at?: string;
}

export interface ApiResponse<T> {
    data: T;
    message?: string;
}
```

### FILENAME: frontend/src/components/TaskList.tsx
```typescript
import React from "react";
import { Task } from "../api";

interface Props {
    tasks: Task[];
}

export function TaskList({ tasks }: Props) {
    if (tasks.length === 0) return <p>No tasks yet.</p>;

    return (
        <ul className="task-list">
            {tasks.map((task) => (
                <li key={task.id} className={`task-item ${task.status}`}>
                    <span className="task-title">{task.title}</span>
                    <span className="task-status">{task.status}</span>
                </li>
            ))}
        </ul>
    );
}
```'''
    
    def _mock_explain_response(self) -> str:
        return """## Architecture Overview
This codebase follows a standard client-server architecture with a Python backend API and a TypeScript/React frontend.

## Module Breakdown
- **Backend (FastAPI)**: REST API with CRUD operations, Pydantic models for validation, in-memory database
- **Frontend (React)**: SPA consuming the API, component-based UI with TypeScript type safety

## Data Flow
1. User interacts with React frontend
2. Frontend calls API endpoints via fetch
3. Backend processes request, validates with Pydantic
4. Database operations performed
5. Response returned to frontend

## Entry Points
- Backend: `main.py` → FastAPI app with router
- Frontend: `App.tsx` → Root component

## Recommendations
- Add authentication middleware
- Migrate to persistent database (PostgreSQL)
- Add input sanitization and rate limiting
- Implement proper error boundaries in React"""
    
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
