#!/usr/bin/env python3
"""
Contextible - AI Memory for Local AI Models

The coolest CLI for giving your AI superpowers!
"""

import sys
import time
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box

# Add the contextvault package to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextvault.cli.commands import (
    system, context, permissions, templates,
    test, demo, diagnose, config, setup, mcp, learning
)

console = Console()

def show_banner():
    """Display an awesome animated banner"""

    # ASCII art logo
    logo = r"""
   ____            _            _   _ _     _
  / ___|___  _ __ | |_ _____  _| |_(_) |__ | | ___
 | |   / _ \| '_ \| __/ _ \ \/ / __| | '_ \| |/ _ \
 | |__| (_) | | | | ||  __/>  <| |_| | |_) | |  __/
  \____\___/|_| |_|\__\___/_/\_\\__|_|_.__/|_|\___|
    """

    tagline = "AI Memory for Your Local Models"
    version = "v0.1.0"

    # Create gradient colors for the logo
    colors = ["cyan", "bright_cyan", "bright_blue", "blue"]

    # Animate the logo appearing
    lines = logo.strip().split('\n')
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        console.print(f"[{color}]{line}[/{color}]", highlight=False)
        time.sleep(0.05)

    # Print tagline with animation
    time.sleep(0.1)
    tagline_text = Text(tagline, style="bold magenta")
    console.print(Align.center(tagline_text))

    time.sleep(0.05)
    version_text = Text(version, style="dim white")
    console.print(Align.center(version_text))

    console.print()

def show_quick_banner():
    """Display a quick version of the banner (for subcommands)"""
    text = Text("✨ Contextible ✨", style="bold cyan")
    console.print(Align.center(text))
    console.print()

@click.group(invoke_without_command=True)
@click.option('--no-banner', is_flag=True, help='Skip the animated banner')
@click.version_option(version="0.1.0", prog_name="Contextible")
@click.pass_context
def cli(ctx, no_banner):
    """
    ✨ Contextible - AI Memory for Local AI Models ✨

    Transform your local AI models from generic chatbots into personal
    assistants that actually remember you!

    Features:
    • 🧠 Automatic conversation learning
    • 🔍 Semantic search for context retrieval
    • 🎨 Beautiful CLI with animations
    • 🔒 100% local and private
    • ⚡ Fast and efficient

    Get started: contextible setup
    """
    # Show banner only when no subcommand is provided
    if ctx.invoked_subcommand is None:
        if not no_banner:
            show_banner()

        # Show help when run without arguments
        console.print(Panel(
            "[bold cyan]Welcome to Contextible![/bold cyan]\n\n"
            "Type [bold]contextible --help[/bold] to see all available commands.\n"
            "Quick start: [bold]contextible setup[/bold]",
            title="Getting Started",
            border_style="cyan",
            box=box.ROUNDED
        ))

# Add command groups
cli.add_command(setup.setup)
cli.add_command(system.system_group)
cli.add_command(context.context_group)
cli.add_command(permissions.permissions_group)
cli.add_command(templates.templates)
cli.add_command(test.test_group)
cli.add_command(demo.demo_group)
cli.add_command(diagnose.diagnose_group)
cli.add_command(config.config_group)
cli.add_command(mcp.mcp_group)
cli.add_command(learning.learning_group)

# Add convenience shortcuts
cli.add_command(system.start, name="start")  # contextible start -> contextible system start
cli.add_command(system.stop, name="stop")    # contextible stop -> contextible system stop

if __name__ == "__main__":
    cli()
