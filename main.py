"""
Multi-Agent Software Development Team

A framework for building software using multiple AI agents
that collaborate like a real engineering team.

Usage:
    python main.py "Build a todo web application"
    
    # Or with specific LLM provider:
    python main.py "Build a REST API" --provider openai

    # Use mock mode for testing (no API calls):
    python main.py "Build a todo app" --provider mock
"""

import sys
import argparse
from pathlib import Path

from config import Config
from orchestrator import Orchestrator, IterativeOrchestrator
from rich.console import Console

console = Console()


def main():
    """Main entry point for the multi-agent system."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Software Development Team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "goal",
        nargs="?",
        help="Project goal or requirements (e.g., 'Build a todo web app')",
    )
    
    parser.add_argument(
        "--provider",
        "-p",
        choices=["openai", "anthropic", "local", "waip", "mock"],
        default="mock",
        help="LLM provider to use (default: mock for testing)",
    )
    
    parser.add_argument(
        "--model",
        "-m",
        help="Model name to use (provider-specific)",
    )
    
    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Output directory for generated files",
    )
    
    parser.add_argument(
        "--iterative",
        "-i",
        action="store_true",
        help="Use iterative improvement mode",
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=10,
        help="Maximum iterations for iterative mode",
    )
    
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug output",
    )
    
    parser.add_argument(
        "--env-file",
        help="Path to .env file for configuration",
    )
    
    args = parser.parse_args()
    
    # Interactive mode if no goal provided
    if not args.goal:
        console.print("\n[bold blue]Multi-Agent Software Development Team[/bold blue]")
        console.print("=" * 50)
        console.print("\nThis system uses AI agents to collaboratively build software.")
        console.print("Each agent has a specialized role:\n")
        console.print("  [cyan]• Planner[/cyan] - Product manager, breaks down requirements")
        console.print("  [cyan]• Architect[/cyan] - Designs system architecture")
        console.print("  [cyan]• Developer[/cyan] - Writes backend and frontend code")
        console.print("  [cyan]• Tester[/cyan] - Creates and runs tests")
        console.print("  [cyan]• Debugger[/cyan] - Fixes bugs and issues")
        console.print()
        
        args.goal = console.input("[bold yellow]Enter your project goal:[/bold yellow] ")
        
        if not args.goal.strip():
            console.print("[red]No goal provided. Exiting.[/red]")
            sys.exit(1)
    
    # Load configuration
    config = Config.from_env(args.env_file)
    
    # Override with command line arguments
    if args.provider:
        config.llm_provider = args.provider
    if args.output:
        config.output_dir = args.output
    if args.debug:
        config.debug_mode = args.debug
    if args.max_iterations:
        config.max_iterations = args.max_iterations
    
    # Get API key if needed
    api_key = config.get_api_key()
    model = args.model or config.get_model()
    base_url = config.get_base_url()
    
    # Warn if using real provider without API key
    if config.llm_provider in ["openai", "anthropic", "waip"] and not api_key:
        console.print(f"[yellow]Warning: No API key found for {config.llm_provider}.[/yellow]")
        console.print("[yellow]Set the appropriate environment variable or use --provider mock[/yellow]")
        if config.llm_provider == "openai":
            console.print("[dim]Set OPENAI_API_KEY environment variable[/dim]")
        elif config.llm_provider == "anthropic":
            console.print("[dim]Set ANTHROPIC_API_KEY environment variable[/dim]")
        elif config.llm_provider == "waip":
            console.print("[dim]Set WAIP_API_KEY environment variable[/dim]")
        sys.exit(1)
    
    # Create orchestrator
    if args.iterative:
        orchestrator = IterativeOrchestrator(
            llm_provider=config.llm_provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            output_dir=config.output_dir,
            max_iterations=config.max_iterations,
            debug_mode=config.debug_mode,
        )
    else:
        orchestrator = Orchestrator(
            llm_provider=config.llm_provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            output_dir=config.output_dir,
            max_iterations=config.max_iterations,
            debug_mode=config.debug_mode,
        )
    
    # Run the workflow
    try:
        console.print(f"\n[bold]Provider:[/bold] {config.llm_provider}")
        console.print(f"[bold]Model:[/bold] {model}")
        console.print(f"[bold]Output:[/bold] {config.output_dir}")
        console.print()
        
        if args.iterative:
            result = orchestrator.run_iterative(args.goal)
        else:
            result = orchestrator.run(args.goal)
        
        console.print(f"\n[bold green]✓ Project files saved to: {config.output_dir}[/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        if config.debug_mode:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
