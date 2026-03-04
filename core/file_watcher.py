"""
File Watcher - Monitors task files for changes and auto-triggers workflow.

Features:
- Watch Excel/JSON files for new tasks
- Polling-based monitoring (cross-platform compatible)
- Event callback system
- Graceful shutdown
"""

import os
import time
import threading
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FileChangeEvent:
    """Represents a file change event."""
    path: str
    event_type: str  # created, modified, deleted
    timestamp: datetime
    
    def __str__(self):
        return f"[{self.event_type.upper()}] {self.path} at {self.timestamp}"


class TaskFileWatcher:
    """
    Watches task files for changes and triggers callbacks.
    
    Uses polling for cross-platform compatibility.
    Can also use watchdog library if available.
    """
    
    def __init__(
        self,
        watch_paths: List[str],
        poll_interval: float = 5.0,
        use_watchdog: bool = False
    ):
        """
        Initialize file watcher.
        
        Args:
            watch_paths: List of file/folder paths to watch
            poll_interval: Seconds between poll checks
            use_watchdog: Use watchdog library if True and available
        """
        self.watch_paths = [Path(p) for p in watch_paths]
        self.poll_interval = poll_interval
        self.use_watchdog = use_watchdog
        
        # State tracking
        self._file_states: Dict[str, float] = {}  # path -> mtime
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._on_change_callbacks: List[Callable[[FileChangeEvent], None]] = []
        self._on_new_task_callbacks: List[Callable[[str], None]] = []
        
        # Initialize file states
        self._initialize_states()
    
    def _initialize_states(self) -> None:
        """Initialize file state tracking."""
        for path in self.watch_paths:
            if path.exists():
                if path.is_file():
                    self._file_states[str(path)] = path.stat().st_mtime
                elif path.is_dir():
                    for file_path in path.glob("*"):
                        if file_path.is_file():
                            self._file_states[str(file_path)] = file_path.stat().st_mtime
    
    def on_change(self, callback: Callable[[FileChangeEvent], None]) -> None:
        """Register callback for file changes."""
        self._on_change_callbacks.append(callback)
    
    def on_new_task(self, callback: Callable[[str], None]) -> None:
        """Register callback for when new task file is detected."""
        self._on_new_task_callbacks.append(callback)
    
    def _check_for_changes(self) -> List[FileChangeEvent]:
        """Check for file changes."""
        events = []
        current_files: Dict[str, float] = {}
        
        for path in self.watch_paths:
            if path.is_file() and path.exists():
                current_files[str(path)] = path.stat().st_mtime
            elif path.is_dir() and path.exists():
                for file_path in path.glob("*"):
                    if file_path.is_file():
                        current_files[str(file_path)] = file_path.stat().st_mtime
        
        # Check for new or modified files
        for file_path, mtime in current_files.items():
            if file_path not in self._file_states:
                events.append(FileChangeEvent(
                    path=file_path,
                    event_type="created",
                    timestamp=datetime.now()
                ))
            elif mtime > self._file_states[file_path]:
                events.append(FileChangeEvent(
                    path=file_path,
                    event_type="modified",
                    timestamp=datetime.now()
                ))
        
        # Check for deleted files
        for file_path in self._file_states:
            if file_path not in current_files:
                events.append(FileChangeEvent(
                    path=file_path,
                    event_type="deleted",
                    timestamp=datetime.now()
                ))
        
        # Update state
        self._file_states = current_files
        
        return events
    
    def _poll_loop(self) -> None:
        """Main polling loop."""
        print(f"[Watcher] Started monitoring {len(self.watch_paths)} path(s)")
        print(f"[Watcher] Poll interval: {self.poll_interval}s")
        
        while self._running:
            try:
                events = self._check_for_changes()
                
                for event in events:
                    print(f"[Watcher] {event}")
                    
                    # Trigger callbacks
                    for callback in self._on_change_callbacks:
                        try:
                            callback(event)
                        except Exception as e:
                            print(f"[Watcher] Callback error: {e}")
                    
                    # Trigger new task callbacks for Excel/JSON task files
                    if event.event_type in ["created", "modified"]:
                        if event.path.endswith((".xlsx", ".json")):
                            for callback in self._on_new_task_callbacks:
                                try:
                                    callback(event.path)
                                except Exception as e:
                                    print(f"[Watcher] Task callback error: {e}")
                
                time.sleep(self.poll_interval)
                
            except Exception as e:
                print(f"[Watcher] Error in poll loop: {e}")
                time.sleep(self.poll_interval)
    
    def start(self, blocking: bool = False) -> None:
        """
        Start watching for file changes.
        
        Args:
            blocking: If True, blocks the main thread
        """
        if self._running:
            print("[Watcher] Already running")
            return
        
        self._running = True
        
        if blocking:
            self._poll_loop()
        else:
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
    
    def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        print("[Watcher] Stopped")
    
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running


class SDLCEventHandler:
    """
    Handles file change events for SDLC workflow.
    
    Integrates with task tracker to detect new tasks
    and trigger the development workflow.
    """
    
    def __init__(self, workflow_callback: Callable[[str], None]):
        """
        Initialize event handler.
        
        Args:
            workflow_callback: Function to call when new task detected
        """
        self.workflow_callback = workflow_callback
        self._processed_mtimes: Dict[str, float] = {}
    
    def handle_task_file_change(self, file_path: str) -> None:
        """
        Handle task file change event.
        
        Checks for new tasks and triggers workflow.
        """
        from core.task_tracker import TaskTracker, TaskStatus
        
        print(f"[Handler] Task file changed: {file_path}")
        
        # Load tasks from file
        tracker = TaskTracker(file_path)
        new_tasks = tracker.get_new_tasks()
        
        if new_tasks:
            print(f"[Handler] Found {len(new_tasks)} new task(s)")
            for task in new_tasks:
                print(f"[Handler] Processing: {task.id} - {task.title}")
                
                # Mark as in progress
                tracker.update_task_status(task.id, TaskStatus.IN_PROGRESS)
                
                # Trigger workflow
                try:
                    self.workflow_callback(task.id)
                except Exception as e:
                    print(f"[Handler] Workflow error for {task.id}: {e}")
                    tracker.update_task_status(
                        task.id, 
                        TaskStatus.FAILED,
                        error_message=str(e)
                    )
        else:
            print("[Handler] No new tasks to process")


def create_watcher_with_workflow(
    tasks_file: str,
    workflow_callback: Callable[[str], None],
    poll_interval: float = 5.0
) -> TaskFileWatcher:
    """
    Create a file watcher that triggers SDLC workflow on new tasks.
    
    Args:
        tasks_file: Path to task file (Excel/JSON)
        workflow_callback: Function to call with task_id
        poll_interval: Seconds between checks
        
    Returns:
        Configured TaskFileWatcher instance
    """
    # Determine watch paths
    tasks_path = Path(tasks_file)
    watch_paths = [str(tasks_path.parent)]
    
    # Create watcher
    watcher = TaskFileWatcher(watch_paths, poll_interval)
    
    # Create handler
    handler = SDLCEventHandler(workflow_callback)
    
    # Register callback
    watcher.on_new_task(handler.handle_task_file_change)
    
    return watcher


if __name__ == "__main__":
    # Test watcher
    def on_task_detected(task_id: str):
        print(f">>> New task detected: {task_id}")
    
    watcher = create_watcher_with_workflow(
        "tasks/development_tasks.xlsx",
        on_task_detected,
        poll_interval=3.0
    )
    
    print("Starting watcher... Press Ctrl+C to stop")
    try:
        watcher.start(blocking=True)
    except KeyboardInterrupt:
        watcher.stop()
