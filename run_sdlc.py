"""
SDLC Agentic Workflow - Main Runner

This script runs the complete SDLC automation:
1. Monitors task file (Excel/JSON) for new development tasks
2. Auto-triggers multi-agent workflow when new task is added
3. Agents collaborate: Planner → Architect → Developer → Tester
4. Creates feature branch, commits code, pushes to remote
5. Creates Pull Request for human review
6. Monitors PR until merged, then marks task complete

Usage:
    # Start watching for new tasks (auto-trigger mode)
    python run_sdlc.py --watch
    
    # Process a single task
    python run_sdlc.py --task TASK-001
    
    # Show task status
    python run_sdlc.py --status
    
    # Initialize with sample tasks
    python run_sdlc.py --init

Author: Multi-Agent Dev Team
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from sdlc_orchestrator import SDLCOrchestrator, SDLCConfig, create_sdlc_orchestrator
from core.task_tracker import TaskTracker, TaskStatus, DevelopmentTask

console = Console()


def show_banner():
    """Display application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║       🤖 SDLC AGENTIC WORKFLOW - Multi-Agent Dev Team 🤖      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║   Automated Software Development Lifecycle                    ║
║                                                               ║
║   📋 Task Added → 🤖 Agents Run → 📝 PR Created → ✅ Merged   ║
║                                                               ║
║   Agents:                                                     ║
║   • Planner    - Breaks down requirements                     ║
║   • Architect  - Designs system architecture                  ║
║   • Developer  - Writes backend & frontend code               ║
║   • Tester     - Generates and runs tests                     ║
║   • Debugger   - Fixes bugs and issues                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="cyan")


def init_tasks_file(tasks_file: str):
    """Initialize tasks file with sample tasks."""
    tracker = TaskTracker(tasks_file)
    
    # Add sample tasks if empty
    if len(tracker.get_all_tasks()) <= 1:
        sample_tasks = [
            DevelopmentTask(
                id="TASK-001",
                title="Add user authentication",
                description="Implement JWT-based authentication with login/register endpoints",
                type="feature",
                priority="high",
                target_component="backend"
            ),
            DevelopmentTask(
                id="TASK-002",
                title="Create dashboard UI",
                description="Build a responsive dashboard with charts and statistics",
                type="feature",
                priority="medium",
                target_component="frontend"
            ),
            DevelopmentTask(
                id="TASK-003",
                title="Add API rate limiting",
                description="Implement rate limiting middleware to prevent abuse",
                type="enhancement",
                priority="medium",
                target_component="backend"
            ),
        ]
        
        for task in sample_tasks:
            if task.id not in tracker.tasks:
                tracker.add_task(task)
        
        console.print(f"[green]✓[/green] Created sample tasks in {tasks_file}")
    else:
        console.print(f"[yellow]![/yellow] Tasks file already has tasks: {tasks_file}")
    
    # Display tasks
    tracker = TaskTracker(tasks_file)
    console.print(f"\nTasks ({len(tracker.get_all_tasks())}):")
    for task in tracker.get_all_tasks():
        status_color = "green" if task.status == "new" else "yellow"
        console.print(f"  • [{status_color}]{task.status:15}[/{status_color}] {task.id}: {task.title}")


def show_status(tasks_file: str):
    """Show current task status."""
    tracker = TaskTracker(tasks_file)
    orchestrator = create_sdlc_orchestrator(tasks_file)
    orchestrator.display_status_table()
    
    # Summary
    all_tasks = tracker.get_all_tasks()
    new_count = len([t for t in all_tasks if t.status == "new"])
    in_progress = len([t for t in all_tasks if t.status == "in_progress"])
    completed = len([t for t in all_tasks if t.status in ["completed", "merged"]])
    
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  New: {new_count} | In Progress: {in_progress} | Completed: {completed} | Total: {len(all_tasks)}")


def process_single_task(tasks_file: str, task_id: str):
    """Process a single task."""
    console.print(f"\n[bold]Processing task:[/bold] {task_id}\n")
    
    orchestrator = create_sdlc_orchestrator(tasks_file)
    result = orchestrator.run_single_task(task_id)
    
    if result["success"]:
        console.print(Panel(
            f"[green]✓ Task completed successfully![/green]\n\n"
            f"Task ID: {result['task_id']}\n"
            f"Files changed: {len(result['files_changed'])}\n"
            f"PR URL: {result.get('pr_url', 'N/A')}",
            title="Success"
        ))
    else:
        console.print(Panel(
            f"[red]✗ Task failed[/red]\n\n"
            f"Error: {result.get('error', 'Unknown error')}",
            title="Error"
        ))
    
    return result


def start_watch_mode(tasks_file: str):
    """Start watching for new tasks."""
    console.print("\n[bold cyan]Starting watch mode...[/bold cyan]")
    console.print("[dim]Add new tasks to Excel file to auto-trigger workflow[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    orchestrator = create_sdlc_orchestrator(tasks_file)
    
    try:
        orchestrator.start_watching()
    except KeyboardInterrupt:
        orchestrator.stop_watching()
        console.print("\n[yellow]Watch mode stopped.[/yellow]")


def add_task_interactive(tasks_file: str):
    """Add a new task interactively."""
    console.print("\n[bold]Add New Development Task[/bold]\n")
    
    task_id = console.input("[cyan]Task ID[/cyan] (e.g., TASK-004): ").strip()
    title = console.input("[cyan]Title[/cyan]: ").strip()
    description = console.input("[cyan]Description[/cyan]: ").strip()
    
    task_type = console.input("[cyan]Type[/cyan] (feature/bugfix/enhancement) [feature]: ").strip() or "feature"
    priority = console.input("[cyan]Priority[/cyan] (low/medium/high/critical) [medium]: ").strip() or "medium"
    component = console.input("[cyan]Component[/cyan] (backend/frontend/both) [backend]: ").strip() or "backend"
    
    task = DevelopmentTask(
        id=task_id,
        title=title,
        description=description,
        type=task_type,
        priority=priority,
        target_component=component
    )
    
    tracker = TaskTracker(tasks_file)
    tracker.add_task(task)
    
    console.print(f"\n[green]✓[/green] Task {task_id} added successfully!")
    console.print(f"[dim]The task will be auto-processed if watch mode is running.[/dim]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SDLC Agentic Workflow - Automated Development Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Start watching for new tasks (auto-trigger mode)"
    )
    
    parser.add_argument(
        "--task", "-t",
        help="Process a specific task by ID"
    )
    
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show current task status"
    )
    
    parser.add_argument(
        "--init", "-i",
        action="store_true",
        help="Initialize with sample tasks"
    )
    
    parser.add_argument(
        "--add", "-a",
        action="store_true",
        help="Add a new task interactively"
    )
    
    parser.add_argument(
        "--tasks-file", "-f",
        default="tasks/development_tasks.xlsx",
        help="Path to tasks file (Excel or JSON)"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    # Show banner
    show_banner()
    
    # Handle commands
    if args.init:
        init_tasks_file(args.tasks_file)
    
    elif args.status:
        show_status(args.tasks_file)
    
    elif args.add:
        add_task_interactive(args.tasks_file)
    
    elif args.task:
        process_single_task(args.tasks_file, args.task)
    
    elif args.watch:
        start_watch_mode(args.tasks_file)
    
    else:
        # Interactive mode
        console.print("[bold]What would you like to do?[/bold]\n")
        console.print("  1. [cyan]Watch[/cyan] - Start auto-trigger mode")
        console.print("  2. [cyan]Status[/cyan] - View task status")
        console.print("  3. [cyan]Add[/cyan] - Add a new task")
        console.print("  4. [cyan]Init[/cyan] - Initialize with sample tasks")
        console.print("  5. [cyan]Exit[/cyan] - Quit")
        console.print()
        
        choice = console.input("[bold yellow]Choose (1-5):[/bold yellow] ").strip()
        
        if choice == "1":
            start_watch_mode(args.tasks_file)
        elif choice == "2":
            show_status(args.tasks_file)
        elif choice == "3":
            add_task_interactive(args.tasks_file)
        elif choice == "4":
            init_tasks_file(args.tasks_file)
        elif choice == "5":
            console.print("[dim]Goodbye![/dim]")
        else:
            console.print("[red]Invalid choice[/red]")


if __name__ == "__main__":
    main()
