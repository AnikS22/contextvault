"""Interactive settings management for ContextVault."""

import click
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


@click.group(name="settings")
def settings_group():
    """Manage ContextVault settings interactively."""
    pass


@settings_group.command(name="show")
def show_settings():
    """Display current settings."""
    from ...config import settings

    console.print()
    console.print(Panel.fit(
        "[bold cyan]ContextVault Settings[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    # Create settings table
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("Setting", style="cyan", width=30)
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")

    # Database settings
    table.add_section()
    table.add_row(
        "database_url",
        str(settings.database_url),
        "Where your data is stored"
    )

    # API settings
    table.add_section()
    table.add_row(
        "api_host",
        settings.api_host,
        "API server host"
    )
    table.add_row(
        "api_port",
        str(settings.api_port),
        "API server port"
    )

    # Ollama settings
    table.add_section()
    table.add_row(
        "ollama_host",
        settings.ollama_host,
        "Ollama server host"
    )
    table.add_row(
        "ollama_port",
        str(settings.ollama_port),
        "Ollama server port"
    )
    table.add_row(
        "proxy_port",
        str(settings.proxy_port),
        "ContextVault proxy port"
    )

    # Context settings
    table.add_section()
    table.add_row(
        "max_context_tokens",
        f"{settings.max_context_tokens:,}",
        "Maximum tokens for context"
    )
    table.add_row(
        "max_context_entries",
        str(settings.max_context_entries),
        "Max entries to retrieve"
    )

    # Token counting
    table.add_section()
    table.add_row(
        "use_token_counting",
        "✓ Enabled" if settings.use_token_counting else "✗ Disabled",
        "Accurate token counting"
    )
    table.add_row(
        "default_tokenizer",
        settings.default_tokenizer_type,
        "Tokenizer type (llama/mistral/gpt)"
    )

    # Performance
    table.add_section()
    table.add_row(
        "enable_caching",
        "✓ Enabled" if settings.enable_caching else "✗ Disabled",
        "Cache for performance"
    )
    table.add_row(
        "cache_ttl",
        f"{settings.cache_ttl_seconds}s",
        "Cache time-to-live"
    )

    console.print(table)
    console.print()
    console.print("[dim]💡 Run 'contextible settings edit' to change these values[/dim]")
    console.print()


@settings_group.command(name="edit")
def edit_settings():
    """Interactive settings editor."""
    from ...config import settings

    console.print()
    console.print("[bold cyan]Settings Editor[/bold cyan]")
    console.print("[dim]Press Enter to keep current value[/dim]\n")

    # Load current .env or create new
    env_path = Path.cwd() / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value

    # Interactive editing
    console.print("[bold]1. Model Connection[/bold]")

    ollama_host = Prompt.ask(
        "Ollama host",
        default=env_vars.get("OLLAMA_HOST", settings.ollama_host)
    )

    ollama_port = IntPrompt.ask(
        "Ollama port",
        default=int(env_vars.get("OLLAMA_PORT", settings.ollama_port))
    )

    proxy_port = IntPrompt.ask(
        "ContextVault proxy port",
        default=int(env_vars.get("PROXY_PORT", settings.proxy_port))
    )

    console.print("\n[bold]2. Memory Configuration[/bold]")

    max_tokens = IntPrompt.ask(
        "Maximum context tokens",
        default=int(env_vars.get("MAX_CONTEXT_TOKENS", settings.max_context_tokens))
    )

    max_entries = IntPrompt.ask(
        "Maximum context entries",
        default=int(env_vars.get("MAX_CONTEXT_ENTRIES", settings.max_context_entries))
    )

    console.print("\n[bold]3. Performance[/bold]")

    enable_caching = Confirm.ask(
        "Enable caching?",
        default=env_vars.get("ENABLE_CACHING", "true").lower() == "true"
    )

    if enable_caching:
        cache_ttl = IntPrompt.ask(
            "Cache TTL (seconds)",
            default=int(env_vars.get("CACHE_TTL_SECONDS", settings.cache_ttl_seconds))
        )
    else:
        cache_ttl = settings.cache_ttl_seconds

    # Preview changes
    console.print("\n[bold]Preview Changes:[/bold]")

    changes_table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
    changes_table.add_column("Setting", style="cyan")
    changes_table.add_column("New Value", style="green")

    changes_table.add_row("OLLAMA_HOST", ollama_host)
    changes_table.add_row("OLLAMA_PORT", str(ollama_port))
    changes_table.add_row("PROXY_PORT", str(proxy_port))
    changes_table.add_row("MAX_CONTEXT_TOKENS", f"{max_tokens:,}")
    changes_table.add_row("MAX_CONTEXT_ENTRIES", str(max_entries))
    changes_table.add_row("ENABLE_CACHING", str(enable_caching))
    changes_table.add_row("CACHE_TTL_SECONDS", str(cache_ttl))

    console.print(changes_table)
    console.print()

    if not Confirm.ask("Save these settings?", default=True):
        console.print("[yellow]Changes discarded.[/yellow]")
        return

    # Write to .env
    with open(env_path, "w") as f:
        f.write("# ContextVault Configuration\n")
        f.write(f"# Last updated: {__import__('datetime').datetime.now().isoformat()}\n\n")

        f.write("# Model Connection\n")
        f.write(f"OLLAMA_HOST={ollama_host}\n")
        f.write(f"OLLAMA_PORT={ollama_port}\n")
        f.write(f"PROXY_PORT={proxy_port}\n\n")

        f.write("# Memory Configuration\n")
        f.write(f"MAX_CONTEXT_TOKENS={max_tokens}\n")
        f.write(f"MAX_CONTEXT_ENTRIES={max_entries}\n\n")

        f.write("# Performance\n")
        f.write(f"ENABLE_CACHING={str(enable_caching).lower()}\n")
        f.write(f"CACHE_TTL_SECONDS={cache_ttl}\n\n")

        # Preserve other settings
        for key, value in env_vars.items():
            if key not in ["OLLAMA_HOST", "OLLAMA_PORT", "PROXY_PORT",
                           "MAX_CONTEXT_TOKENS", "MAX_CONTEXT_ENTRIES",
                           "ENABLE_CACHING", "CACHE_TTL_SECONDS"]:
                f.write(f"{key}={value}\n")

    console.print("[bold green]✓ Settings saved to .env[/bold green]")
    console.print("[dim]Restart ContextVault for changes to take effect[/dim]\n")


@settings_group.command(name="reset")
def reset_settings():
    """Reset all settings to defaults."""
    console.print()

    if not Confirm.ask(
        "[bold yellow]⚠️  Reset all settings to defaults?[/bold yellow]",
        default=False
    ):
        console.print("[dim]Reset cancelled.[/dim]")
        return

    env_path = Path.cwd() / ".env"

    with open(env_path, "w") as f:
        f.write("# ContextVault Configuration (Defaults)\n\n")
        f.write("DATABASE_URL=sqlite:///./contextvault.db\n")
        f.write("OLLAMA_HOST=127.0.0.1\n")
        f.write("OLLAMA_PORT=11434\n")
        f.write("PROXY_PORT=11435\n")
        f.write("MAX_CONTEXT_TOKENS=8192\n")
        f.write("MAX_CONTEXT_ENTRIES=100\n")
        f.write("ENABLE_CACHING=true\n")
        f.write("CACHE_TTL_SECONDS=300\n")

    console.print("[bold green]✓ Settings reset to defaults[/bold green]\n")


@settings_group.command(name="presets")
def show_presets():
    """Show available configuration presets."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Configuration Presets[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    presets_table = Table(show_header=True, header_style="bold", box=box.ROUNDED)
    presets_table.add_column("Preset", style="cyan", width=15)
    presets_table.add_column("Context", justify="right")
    presets_table.add_column("Use Case", style="dim")

    presets_table.add_row("tiny", "4K tokens", "Testing and development")
    presets_table.add_row("small", "8K tokens", "Quick tasks and demos")
    presets_table.add_row("medium", "32K tokens", "Balanced performance (recommended)")
    presets_table.add_row("large", "128K tokens", "Maximum context for Llama 3.1")
    presets_table.add_row("xl", "256K tokens", "Future models with huge context")

    console.print(presets_table)
    console.print()
    console.print("[dim]💡 Apply a preset with: contextible settings apply <preset>[/dim]")
    console.print()


@settings_group.command(name="apply")
@click.argument("preset", type=click.Choice(["tiny", "small", "medium", "large", "xl"]))
def apply_preset(preset):
    """Apply a configuration preset."""
    presets = {
        "tiny": {"max_tokens": 4096, "max_entries": 50},
        "small": {"max_tokens": 8192, "max_entries": 100},
        "medium": {"max_tokens": 32768, "max_entries": 200},
        "large": {"max_tokens": 131072, "max_entries": 500},
        "xl": {"max_tokens": 262144, "max_entries": 1000},
    }

    config = presets[preset]

    console.print(f"\n[bold cyan]Applying '{preset}' preset...[/bold cyan]")
    console.print(f"  Max tokens: {config['max_tokens']:,}")
    console.print(f"  Max entries: {config['max_entries']}")
    console.print()

    if not Confirm.ask("Apply this preset?", default=True):
        console.print("[dim]Cancelled.[/dim]")
        return

    # Update .env
    env_path = Path.cwd() / ".env"
    lines = []

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if not line.strip().startswith(("MAX_CONTEXT_TOKENS=", "MAX_CONTEXT_ENTRIES=")):
                    lines.append(line)

    lines.append(f"MAX_CONTEXT_TOKENS={config['max_tokens']}\n")
    lines.append(f"MAX_CONTEXT_ENTRIES={config['max_entries']}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)

    console.print(f"[bold green]✓ Applied '{preset}' preset[/bold green]\n")
