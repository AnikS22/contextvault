#!/usr/bin/env python3
"""
ContextVault CLI Entry Point

This module provides the main CLI interface for ContextVault.
Run with: python -m contextvault.cli
"""

import sys
import click
from pathlib import Path

# Add the contextvault package to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextvault.cli.commands import (
    system, context, permissions, templates, 
    test, demo, diagnose, config, setup, mcp, learning
)

@click.group()
@click.version_option(version="0.1.0", prog_name="ContextVault")
def cli():
    """
    ContextVault - AI Memory for Local AI Models
    
    ContextVault gives your local AI models persistent memory,
    transforming them from generic chatbots into personal assistants
    that actually know you.
    """
    pass

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

if __name__ == "__main__":
    cli()
