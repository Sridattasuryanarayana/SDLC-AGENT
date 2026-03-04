"""
Shared Memory System for Multi-Agent Communication.

This module provides a centralized memory store that all agents can access
to share information, decisions, and artifacts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import json


class MemoryType(Enum):
    """Types of memories that can be stored."""
    REQUIREMENT = "requirement"
    ARCHITECTURE = "architecture"
    CODE = "code"
    TEST = "test"
    BUG_REPORT = "bug_report"
    DECISION = "decision"
    TASK = "task"


@dataclass
class MemoryEntry:
    """A single entry in the shared memory."""
    id: str
    type: MemoryType
    content: Any
    agent: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            content=data["content"],
            agent=data["agent"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )


class SharedMemory:
    """
    Centralized memory store for all agents.
    
    Provides methods to store and retrieve information that needs
    to be shared across the multi-agent system.
    """

    def __init__(self):
        self._memories: Dict[str, MemoryEntry] = {}
        self._counter = 0

    def _generate_id(self) -> str:
        """Generate a unique ID for a memory entry."""
        self._counter += 1
        return f"mem_{self._counter:04d}"

    def store(
        self,
        type: MemoryType,
        content: Any,
        agent: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store information in shared memory.
        
        Args:
            type: The type of memory being stored
            content: The actual content to store
            agent: The name of the agent storing this
            metadata: Optional additional metadata
            
        Returns:
            The ID of the stored memory
        """
        memory_id = self._generate_id()
        entry = MemoryEntry(
            id=memory_id,
            type=type,
            content=content,
            agent=agent,
            metadata=metadata or {},
        )
        self._memories[memory_id] = entry
        return memory_id

    def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory by ID."""
        return self._memories.get(memory_id)

    def get_by_type(self, type: MemoryType) -> List[MemoryEntry]:
        """Get all memories of a specific type."""
        return [m for m in self._memories.values() if m.type == type]

    def get_by_agent(self, agent: str) -> List[MemoryEntry]:
        """Get all memories created by a specific agent."""
        return [m for m in self._memories.values() if m.agent == agent]

    def get_latest(self, type: MemoryType) -> Optional[MemoryEntry]:
        """Get the most recent memory of a specific type."""
        memories = self.get_by_type(type)
        if not memories:
            return None
        return max(memories, key=lambda m: m.timestamp)

    def get_all(self) -> List[MemoryEntry]:
        """Get all memories."""
        return list(self._memories.values())

    def search(self, query: str) -> List[MemoryEntry]:
        """
        Simple text search across all memories.
        
        For production, integrate with vector DB like ChromaDB.
        """
        results = []
        query_lower = query.lower()
        for memory in self._memories.values():
            content_str = str(memory.content).lower()
            if query_lower in content_str:
                results.append(memory)
        return results

    def get_context_for_agent(self, agent_type: str) -> Dict[str, Any]:
        """
        Get relevant context for a specific agent type.
        
        Returns formatted context that an agent can use.
        """
        context = {
            "requirements": [],
            "architecture": None,
            "code": [],
            "tests": [],
            "bugs": [],
        }

        # Get requirements
        for mem in self.get_by_type(MemoryType.REQUIREMENT):
            context["requirements"].append(mem.content)

        # Get latest architecture
        arch = self.get_latest(MemoryType.ARCHITECTURE)
        if arch:
            context["architecture"] = arch.content

        # Get code
        for mem in self.get_by_type(MemoryType.CODE):
            context["code"].append({
                "file": mem.metadata.get("filename", "unknown"),
                "content": mem.content,
            })

        # Get tests
        for mem in self.get_by_type(MemoryType.TEST):
            context["tests"].append(mem.content)

        # Get bug reports
        for mem in self.get_by_type(MemoryType.BUG_REPORT):
            context["bugs"].append(mem.content)

        return context

    def export_to_json(self, filepath: str) -> None:
        """Export all memories to a JSON file."""
        data = [m.to_dict() for m in self._memories.values()]
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def import_from_json(self, filepath: str) -> None:
        """Import memories from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        for item in data:
            entry = MemoryEntry.from_dict(item)
            self._memories[entry.id] = entry
            # Update counter to avoid ID collisions
            num = int(entry.id.split("_")[1])
            if num >= self._counter:
                self._counter = num + 1

    def clear(self) -> None:
        """Clear all memories."""
        self._memories.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._memories)

    def __repr__(self) -> str:
        return f"SharedMemory(entries={len(self._memories)})"
