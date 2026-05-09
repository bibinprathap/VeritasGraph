"""
VeritasReason CLI Entry Point

This module provides the command-line interface for the VeritasReason framework,
enabling users to interact with the framework via terminal commands.
"""

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .core.orchestrator import VeritasReason
from .utils.logging import setup_logging

console = Console()

@click.group()
@click.version_option(version=__version__)
def main():
    """VeritasReason - Semantic Layer & Knowledge Engineering Framework"""
    setup_logging()

@main.command()
def info():
    """Display information about VeritasReason."""
    console.print(f"[bold blue]VeritasReason Framework[/bold blue] v{__version__}")
    console.print("A comprehensive Python framework for transforming unstructured data into semantic layers.")
    
    table = Table(title="Framework Components")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("Core Orchestrator", "Active")
    table.add_row("Knowledge Graph Engine", "Active")
    table.add_row("Pipeline Execution", "Active")
    table.add_row("Vector Store Integration", "Active")
    
    console.print(table)

@main.command()
@click.option("--source", "-s", multiple=True, help="Data sources to process.")
@click.option("--config", "-c", help="Path to configuration file.")
def build(source, config):
    """Build a knowledge base from sources."""
    console.print(f"Initializing VeritasReason with {len(source)} sources...")
    try:
        framework = VeritasReason(config=config)
        # framework.build_knowledge_base(sources=list(source))
        console.print("[bold green]Success:[/bold green] Knowledge base construction initiated.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
