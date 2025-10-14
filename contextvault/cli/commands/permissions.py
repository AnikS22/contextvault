"""Permission management commands for ContextVault CLI."""

import requests
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@click.group(name="permissions")
def permissions_group():
    """Permission management commands."""
    pass

@permissions_group.command()
def list():
    """List all permissions."""
    console.print("🔐 [bold blue]Permission List[/bold blue]")
    
    try:
        response = requests.get('http://localhost:11435/api/permissions/')

        if response.status_code == 200:
            data = response.json()  # API returns list directly, not wrapped in 'data'
            
            if data:
                table = Table(title="Model Permissions")
                table.add_column("Model ID", style="cyan", width=20)
                table.add_column("Model Name", style="blue", width=20)
                table.add_column("Allowed Scopes", style="green", width=30)
                table.add_column("Active", style="yellow", width=8)
                
                for perm in data:
                    # Parse scope (comma-separated string) into list
                    scope = perm.get('scope', '')
                    scopes_list = [s.strip() for s in scope.split(',') if s.strip()] if scope else []
                    scopes_str = ', '.join(scopes_list) if scopes_list else 'None'
                    active_str = "✅ Yes" if perm.get('is_active', False) else "❌ No"

                    table.add_row(
                        perm['model_id'],
                        perm.get('model_name', 'Unknown'),
                        scopes_str,
                        active_str
                    )
                
                console.print(table)
            else:
                console.print("ℹ️ [yellow]No permissions configured[/yellow]")
        else:
            console.print(f"❌ [red]Failed to list permissions: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: python -m contextvault.cli start")
    except Exception as e:
        console.print(f"❌ [red]Error listing permissions: {e}[/red]")

@permissions_group.command()
@click.argument('model_id')
@click.argument('scopes')
@click.option('--model-name', help='Human-readable model name')
def grant(model_id: str, scopes: str, model_name: Optional[str]):
    """Grant permissions to a model."""
    console.print(f"🔓 [bold blue]Granting Permissions to {model_id}[/bold blue]")
    
    # Parse scopes
    scope_list = [scope.strip() for scope in scopes.split(',')]
    
    try:
        response = requests.post('http://localhost:11435/api/permissions/grant', json={
            'model_id': model_id,
            'model_name': model_name or model_id,
            'scopes': scope_list
        })
        
        if response.status_code == 200:
            console.print("✅ [green]Permissions granted successfully[/green]")
            console.print(f"   Model: {model_id}")
            console.print(f"   Scopes: {', '.join(scope_list)}")
        else:
            console.print(f"❌ [red]Failed to grant permissions: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: python -m contextvault.cli start")
    except Exception as e:
        console.print(f"❌ [red]Error granting permissions: {e}[/red]")

@permissions_group.command()
@click.argument('model_id')
@click.argument('scopes')
def revoke(model_id: str, scopes: str):
    """Revoke permissions from a model."""
    console.print(f"🔒 [bold blue]Revoking Permissions from {model_id}[/bold blue]")
    
    # Parse scopes
    scope_list = [scope.strip() for scope in scopes.split(',')]
    
    try:
        response = requests.post('http://localhost:11435/api/permissions/revoke', json={
            'model_id': model_id,
            'scopes': scope_list
        })
        
        if response.status_code == 200:
            console.print("✅ [green]Permissions revoked successfully[/green]")
            console.print(f"   Model: {model_id}")
            console.print(f"   Scopes: {', '.join(scope_list)}")
        else:
            console.print(f"❌ [red]Failed to revoke permissions: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: python -m contextvault.cli start")
    except Exception as e:
        console.print(f"❌ [red]Error revoking permissions: {e}[/red]")

@permissions_group.command()
@click.argument('model_id')
def check(model_id: str):
    """Check permissions for a model."""
    console.print(f"🔍 [bold blue]Checking Permissions for {model_id}[/bold blue]")

    try:
        response = requests.get(f'http://localhost:11435/api/permissions/models/{model_id}/summary')

        if response.status_code == 200:
            data = response.json()

            if data:
                allowed_scopes = data.get('allowed_scopes', [])
                has_unrestricted = data.get('has_unrestricted_access', False)
                is_denied = data.get('is_denied_access', False)

                panel_content = f"""[bold]Model ID:[/bold] {model_id}
[bold]Model Name:[/bold] {data.get('model_name', 'Unknown')}
[bold]Total Permissions:[/bold] {data.get('total_permissions', 0)}
[bold]Active Permissions:[/bold] {data.get('active_permissions', 0)}
[bold]Allowed Scopes:[/bold] {', '.join(allowed_scopes) if allowed_scopes else 'None'}
[bold]Unrestricted Access:[/bold] {'✅ Yes' if has_unrestricted else '❌ No'}
[bold]Access Denied:[/bold] {'❌ Yes' if is_denied else '✅ No'}
[bold]Usage Count:[/bold] {data.get('usage_count', 0)}"""

                panel = Panel(
                    panel_content,
                    title="Permission Details",
                    border_style="blue"
                )
                console.print(panel)
            else:
                console.print(f"ℹ️ [yellow]No permissions found for {model_id}[/yellow]")
        elif response.status_code == 404:
            console.print(f"ℹ️ [yellow]No permissions found for {model_id}[/yellow]")
        else:
            console.print(f"❌ [red]Failed to check permissions: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: python -m contextvault.cli start")
    except Exception as e:
        console.print(f"❌ [red]Error checking permissions: {e}[/red]")

@permissions_group.command()
@click.argument('model_id')
@click.option('--active/--inactive', default=True, help='Set permission active status')
def toggle(model_id: str, active: bool):
    """Toggle permission active status."""
    status = "activate" if active else "deactivate"
    console.print(f"🔄 [bold blue]{status.title()}ing Permissions for {model_id}[/bold blue]")
    
    try:
        response = requests.post('http://localhost:11435/api/permissions/toggle', json={
            'model_id': model_id,
            'is_active': active
        })
        
        if response.status_code == 200:
            console.print(f"✅ [green]Permissions {status}d successfully[/green]")
        else:
            console.print(f"❌ [red]Failed to {status} permissions: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: python -m contextvault.cli start")
    except Exception as e:
        console.print(f"❌ [red]Error toggling permissions: {e}[/red]")

@permissions_group.command()
def summary():
    """Show permission summary."""
    console.print("📊 [bold blue]Permission Summary[/bold blue]")

    try:
        response = requests.get('http://localhost:11435/api/permissions/models/')

        if response.status_code == 200:
            summaries = response.json()

            total_models = len(summaries)
            active_models = len([s for s in summaries if s.get('active_permissions', 0) > 0])
            inactive_models = total_models - active_models

            # Collect scope statistics
            scope_counts = {}
            for summary in summaries:
                for scope in summary.get('allowed_scopes', []):
                    scope_counts[scope] = scope_counts.get(scope, 0) + 1

            scope_list = "\n".join([f"  • {scope}: {count}" for scope, count in sorted(scope_counts.items(), key=lambda x: x[1], reverse=True)])
            if not scope_list:
                scope_list = "  No scopes configured"

            panel_content = f"""[bold]Total Models:[/bold] {total_models}
[bold]Active Models:[/bold] {active_models}
[bold]Inactive Models:[/bold] {inactive_models}

[bold]Most Common Scopes:[/bold]
{scope_list}"""

            panel = Panel(
                panel_content,
                title="Permission Summary",
                border_style="blue"
            )
            console.print(panel)
        else:
            console.print(f"❌ [red]Failed to get summary: {response.status_code}[/red]")
            
    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: python -m contextvault.cli start")
    except Exception as e:
        console.print(f"❌ [red]Error getting summary: {e}[/red]")
