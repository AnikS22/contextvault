"""System management commands for ContextVault CLI."""

import subprocess
import time
import requests
import signal
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@click.group(name="system")
def system_group():
    """System management commands."""
    pass

@system_group.command()
def start():
    """Start the ContextVault proxy server."""
    console.print("🚀 [bold blue]Starting ContextVault...[/bold blue]")

    # Check if already running
    try:
        response = requests.get("http://localhost:11435/health", timeout=2)
        if response.status_code == 200:
            console.print("✅ [green]ContextVault is already running[/green]")
            console.print("   Proxy: http://localhost:11435")
            console.print("   Use [bold]contextible stop[/bold] to stop it")
            return
    except:
        pass

    # Start the proxy using uvicorn directly
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "ollama_proxy.py"

    try:
        console.print("🔗 [cyan]Launching ContextVault Ollama Proxy...[/cyan]")
        console.print()
        console.print("📡 [bold]Proxy will be available at:[/bold]")
        console.print("   • Main: http://localhost:11435")
        console.print("   • Health: http://localhost:11435/health")
        console.print("   • Docs: http://localhost:11435/docs")
        console.print()
        console.print("💡 [dim]Tip: Use Ctrl+C to stop the server[/dim]")
        console.print()

        # Run the proxy (this will block)
        subprocess.run(
            [sys.executable, str(script_path)],
            cwd=script_path.parent
        )

    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]ContextVault stopped by user[/yellow]")
    except Exception as e:
        console.print(f"❌ [red]Error starting ContextVault: {e}[/red]")

@system_group.command()
def stop():
    """Stop the ContextVault proxy server."""
    console.print("🛑 [bold blue]Stopping ContextVault...[/bold blue]")
    
    try:
        # Kill any running proxy processes
        result = subprocess.run(
            ["pkill", "-f", "ollama_proxy.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print("✅ [green]ContextVault stopped successfully[/green]")
        else:
            console.print("⚠️ [yellow]No running ContextVault processes found[/yellow]")
            
    except Exception as e:
        console.print(f"❌ [red]Error stopping ContextVault: {e}[/red]")

@system_group.command()
def status():
    """Show ContextVault system status."""

    with Progress(
        SpinnerColumn(spinner_name="point"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("🔍 Checking system status...", total=None)

        # Check proxy status
        try:
            response = requests.get("http://localhost:11435/health", timeout=5)

            if response.status_code == 200:
                health_data = response.json()

                progress.update(task, description="✅ Status check complete!")
                time.sleep(0.2)
                console.print()

                # Create status table
                from rich.table import Table
                from rich import box
                table = Table(title="✨ System Status", box=box.ROUNDED, border_style="cyan")
                table.add_column("Component", style="bold cyan", width=25)
                table.add_column("Status", style="bold", width=15)
                table.add_column("Details", style="white", width=20)

                # Proxy status
                proxy_healthy = health_data.get("proxy", {}).get("healthy", False)
                table.add_row(
                    "🚀 ContextVault Proxy",
                    "[green]✅ Running[/green]" if proxy_healthy else "[red]❌ Failed[/red]",
                    "localhost:11435"
                )

                # Ollama status
                ollama_status = health_data.get("ollama", {}).get("status", "unknown")
                table.add_row(
                    "🤖 Ollama Integration",
                    "[green]✅ Connected[/green]" if ollama_status == "healthy" else "[red]❌ Failed[/red]",
                    "localhost:11434"
                )

                # Database status
                db_healthy = health_data.get("database", {}).get("healthy", False)
                table.add_row(
                    "💾 Database",
                    "[green]✅ Connected[/green]" if db_healthy else "[red]❌ Failed[/red]",
                    "SQLite"
                )

                # Context injection
                ctx_enabled = health_data.get("context_injection") == "enabled"
                table.add_row(
                    "🧠 Context Injection",
                    "[green]✅ Enabled[/green]" if ctx_enabled else "[red]❌ Disabled[/red]",
                    "Active"
                )

                console.print(table)

                if all([proxy_healthy, ollama_status == "healthy", db_healthy, ctx_enabled]):
                    console.print()
                    from rich.panel import Panel
                    console.print(Panel(
                        "[bold green]All systems operational![/bold green] 🎉\nYour AI has superpowers! 🚀",
                        border_style="green",
                        box=box.ROUNDED
                    ))
                else:
                    console.print("\n⚠️  [yellow]Some components have issues[/yellow]")

            else:
                progress.update(task, description="❌ Status check failed")
                time.sleep(0.2)
                console.print("\n❌ [red]ContextVault proxy not responding[/red]")

        except requests.exceptions.ConnectionError:
            progress.update(task, description="❌ Connection failed")
            time.sleep(0.2)
            console.print("\n❌ [red]ContextVault proxy not running[/red]")
            console.print("   Run [bold]contextible start[/bold] to start it")
        except Exception as e:
            progress.update(task, description="❌ Error occurred")
            time.sleep(0.2)
            console.print(f"\n❌ [red]Error checking status: {e}[/red]")

@system_group.command()
def health():
    """Run detailed health check."""
    console.print("🏥 [bold blue]ContextVault Health Check[/bold blue]")
    console.print("=" * 40)
    
    try:
        response = requests.get("http://localhost:11435/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            
            # Display detailed health information
            console.print(Panel(
                f"""[bold]Proxy Status:[/bold] {'✅ Healthy' if health_data.get('proxy', {}).get('healthy') else '❌ Unhealthy'}
[bold]Ollama Status:[/bold] {health_data.get('ollama', {}).get('status', 'Unknown')}
[bold]Database Status:[/bold] {'✅ Healthy' if health_data.get('database', {}).get('healthy') else '❌ Unhealthy'}
[bold]Context Injection:[/bold] {health_data.get('context_injection', 'Unknown')}
[bold]Uptime:[/bold] {health_data.get('uptime', 'Unknown')}""",
                title="Health Summary",
                border_style="green"
            ))
            
        else:
            console.print("❌ [red]Health check failed[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]Cannot connect to ContextVault[/red]")
    except Exception as e:
        console.print(f"❌ [red]Health check error: {e}[/red]")

@system_group.command()
def logs():
    """Show ContextVault logs."""
    console.print("📋 [bold blue]ContextVault Logs[/bold blue]")
    console.print("=" * 40)
    
    log_file = Path.home() / ".contextvault" / "logs" / "contextvault.log"
    
    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Show last 50 lines
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                for line in recent_lines:
                    console.print(line.rstrip())
                    
        except Exception as e:
            console.print(f"❌ [red]Error reading logs: {e}[/red]")
    else:
        console.print("⚠️ [yellow]No log file found[/yellow]")
        console.print(f"   Expected location: {log_file}")

@system_group.command()
@click.option('--port', default=8080, help='Port for the web dashboard')
def dashboard(port: int):
    """Start the web dashboard."""
    console.print(f"🌐 [bold blue]Starting ContextVault Dashboard on port {port}[/bold blue]")
    
    # Check if ContextVault is running
    try:
        response = requests.get("http://localhost:11435/health", timeout=2)
        if response.status_code != 200:
            console.print("❌ [red]ContextVault proxy must be running first[/red]")
            console.print("   Run 'python -m contextvault.cli start'")
            return
    except:
        console.print("❌ [red]ContextVault proxy must be running first[/red]")
        console.print("   Run 'python -m contextvault.cli start'")
        return
    
    # Start dashboard
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "start_dashboard.py"
    
    try:
        console.print(f"🚀 [green]Starting dashboard server...[/green]")
        console.print(f"   Dashboard: http://localhost:{port}")
        console.print("   Press CTRL+C to stop")
        
        subprocess.run([
            sys.executable, str(script_path)
        ])
        
    except KeyboardInterrupt:
        console.print("\n⏹️ [yellow]Dashboard stopped[/yellow]")
    except Exception as e:
        console.print(f"❌ [red]Error starting dashboard: {e}[/red]")
