"""Graph RAG commands for ContextVault CLI."""

import requests
import time
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

@click.group(name="graph-rag")
def graph_rag_group():
    """Graph RAG knowledge management commands."""
    pass


@graph_rag_group.command(name="add")
@click.argument('content')
@click.option('--id', 'document_id', required=True, help='Unique document ID')
@click.option('--extract-entities/--no-extract-entities', default=True, help='Extract entities from content')
@click.option('--metadata', help='JSON metadata')
def add_document(content: str, document_id: str, extract_entities: bool, metadata: Optional[str]):
    """Add a document to Graph RAG with entity extraction."""

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("✨ Adding document to Graph RAG...", total=None)

        try:
            import json
            metadata_dict = json.loads(metadata) if metadata else None

            response = requests.post('http://localhost:11435/api/graph-rag/add', json={
                'content': content,
                'document_id': document_id,
                'extract_entities': extract_entities,
                'metadata': metadata_dict
            })

            time.sleep(0.3)

            if response.status_code == 201:
                result = response.json()
                progress.update(task, description="✅ Document added successfully!")
                time.sleep(0.2)
                console.print()
                console.print(Panel(
                    f"[bold cyan]Document ID:[/bold cyan] {result.get('document_id', 'unknown')}\n"
                    f"[bold cyan]Entities Extracted:[/bold cyan] {result.get('entities_extracted', 0)}\n"
                    f"[bold cyan]Relationships Created:[/bold cyan] {result.get('relationships_created', 0)}\n"
                    f"[bold cyan]Content:[/bold cyan] {content[:60]}..." if len(content) > 60 else f"[bold cyan]Content:[/bold cyan] {content}",
                    title="🎯 Graph RAG Document",
                    border_style="green",
                    box=box.ROUNDED
                ))
            elif response.status_code == 503:
                progress.update(task, description="❌ Graph RAG unavailable")
                time.sleep(0.2)
                console.print("\n❌ [red]Graph RAG is not available[/red]")
                console.print("   Ensure Neo4j is running: [bold]docker run -p 7474:7474 -p 7687:7687 neo4j[/bold]")
            else:
                progress.update(task, description="❌ Failed to add document")
                time.sleep(0.2)
                error_detail = response.json().get('detail', 'Unknown error')
                console.print(f"\n❌ [red]Failed: {error_detail}[/red]")

        except requests.exceptions.ConnectionError:
            progress.update(task, description="❌ Connection failed")
            time.sleep(0.2)
            console.print("\n❌ [red]ContextVault proxy not running[/red]")
            console.print("   Start it with: [bold]contextible start[/bold]")
        except Exception as e:
            progress.update(task, description="❌ Error occurred")
            time.sleep(0.2)
            console.print(f"\n❌ [red]Error: {e}[/red]")


@graph_rag_group.command(name="search")
@click.argument('query')
@click.option('--limit', default=10, help='Number of results to show')
@click.option('--use-graph/--no-use-graph', default=True, help='Use graph traversal')
@click.option('--min-relevance', default=0.5, type=float, help='Minimum relevance score (0.0-1.0)')
@click.option('--show-entities', is_flag=True, help='Show matched entities')
def search(query: str, limit: int, use_graph: bool, min_relevance: float, show_entities: bool):
    """Search Graph RAG using hybrid search."""

    with Progress(
        SpinnerColumn(spinner_name="arc"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"🔍 Searching Graph RAG for '{query}'...", total=None)

        try:
            response = requests.post('http://localhost:11435/api/graph-rag/search', json={
                'query': query,
                'limit': limit,
                'use_graph': use_graph,
                'min_relevance': min_relevance
            })

            time.sleep(0.3)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total = data.get('total', 0)

                progress.update(task, description=f"✅ Found {total} result(s)!")
                time.sleep(0.2)
                console.print()

                if results:
                    for i, result in enumerate(results, 1):
                        colors = ["cyan", "blue", "magenta", "green", "yellow"]
                        border_color = colors[(i-1) % len(colors)]

                        panel_content = f"""[bold]Content:[/bold] {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}
[bold]Relevance:[/bold] {result['relevance_score']:.3f}
[bold]Search Type:[/bold] {result['search_type']}"""

                        if show_entities and result.get('matched_entity'):
                            panel_content += f"""
[bold]Matched Entity:[/bold] {result['matched_entity']} ({result.get('entity_type', 'UNKNOWN')})"""

                        if show_entities and result.get('related_entities'):
                            entities_str = ', '.join([f"{e['text']} ({e['type']})" for e in result['related_entities'][:5]])
                            panel_content += f"""
[bold]Related:[/bold] {entities_str}"""

                        panel = Panel(
                            panel_content,
                            title=f"🎯 Result {i}",
                            border_style=border_color,
                            box=box.ROUNDED
                        )
                        console.print(panel)
                        time.sleep(0.1)
                else:
                    console.print("ℹ️  [yellow]No results found[/yellow]")
            elif response.status_code == 503:
                progress.update(task, description="❌ Graph RAG unavailable")
                time.sleep(0.2)
                console.print("\n❌ [red]Graph RAG is not available[/red]")
                console.print("   Ensure Neo4j is running")
            else:
                progress.update(task, description="❌ Search failed")
                time.sleep(0.2)
                console.print(f"\n❌ [red]Search failed: {response.status_code}[/red]")

        except requests.exceptions.ConnectionError:
            progress.update(task, description="❌ Connection failed")
            time.sleep(0.2)
            console.print("\n❌ [red]ContextVault proxy not running[/red]")
            console.print("   Start it with: [bold]contextible start[/bold]")
        except Exception as e:
            progress.update(task, description="❌ Error occurred")
            time.sleep(0.2)
            console.print(f"\n❌ [red]Error: {e}[/red]")


@graph_rag_group.command(name="entity")
@click.argument('entity_text')
@click.option('--type', 'entity_type', help='Entity type (PERSON, ORG, etc.)')
@click.option('--depth', default=1, type=int, help='Relationship depth (1-3)')
def get_entity_relationships(entity_text: str, entity_type: Optional[str], depth: int):
    """Get relationships for an entity."""

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"🔍 Finding relationships for '{entity_text}'...", total=None)

        try:
            response = requests.post('http://localhost:11435/api/graph-rag/entity-relationships', json={
                'entity_text': entity_text,
                'entity_type': entity_type,
                'depth': depth
            })

            time.sleep(0.3)

            if response.status_code == 200:
                data = response.json()
                entity = data.get('entity')
                relationships = data.get('relationships', [])

                progress.update(task, description=f"✅ Found {len(relationships)} relationship(s)!")
                time.sleep(0.2)
                console.print()

                if entity:
                    console.print(Panel(
                        f"[bold cyan]Entity:[/bold cyan] {entity['text']}\n"
                        f"[bold cyan]Type:[/bold cyan] {entity['type']}",
                        title="📍 Entity Info",
                        border_style="cyan"
                    ))
                    console.print()

                if relationships:
                    table = Table(title="🔗 Relationships")
                    table.add_column("Target", style="cyan", width=25)
                    table.add_column("Type", style="blue", width=15)
                    table.add_column("Relationship", style="green", width=20)

                    for rel in relationships:
                        table.add_row(
                            rel.get('target', 'Unknown'),
                            rel.get('target_type', 'Unknown'),
                            rel.get('relationship', 'Unknown')
                        )

                    console.print(table)
                else:
                    console.print("ℹ️  [yellow]No relationships found[/yellow]")
            elif response.status_code == 503:
                progress.update(task, description="❌ Graph RAG unavailable")
                time.sleep(0.2)
                console.print("\n❌ [red]Graph RAG is not available[/red]")
            else:
                progress.update(task, description="❌ Failed")
                time.sleep(0.2)
                console.print(f"\n❌ [red]Failed: {response.status_code}[/red]")

        except requests.exceptions.ConnectionError:
            progress.update(task, description="❌ Connection failed")
            time.sleep(0.2)
            console.print("\n❌ [red]ContextVault proxy not running[/red]")
            console.print("   Start it with: [bold]contextible start[/bold]")
        except Exception as e:
            progress.update(task, description="❌ Error occurred")
            time.sleep(0.2)
            console.print(f"\n❌ [red]Error: {e}[/red]")


@graph_rag_group.command(name="stats")
def stats():
    """Show Graph RAG statistics."""
    console.print("📊 [bold blue]Graph RAG Statistics[/bold blue]")

    try:
        response = requests.get('http://localhost:11435/api/graph-rag/stats')

        if response.status_code == 200:
            data = response.json()

            if data.get('available'):
                stats_panel = Panel(
                    f"""[bold]Total Documents:[/bold] {data.get('total_documents', 0)}
[bold]Total Entities:[/bold] {data.get('total_entities', 0)}
[bold]Total Relationships:[/bold] {data.get('total_relationships', 0)}
[bold]Database:[/bold] {data.get('database', 'Unknown')}
[bold]Status:[/bold] [green]✅ Available[/green]""",
                    title="Graph RAG Statistics",
                    border_style="green"
                )
            else:
                stats_panel = Panel(
                    f"""[bold]Status:[/bold] [red]❌ Unavailable[/red]
[bold]Error:[/bold] {data.get('error', 'Neo4j is not running')}

[yellow]To start Neo4j:[/yellow]
docker run -d -p 7474:7474 -p 7687:7687 \\
  -e NEO4J_AUTH=neo4j/password \\
  neo4j""",
                    title="Graph RAG Statistics",
                    border_style="red"
                )

            console.print(stats_panel)
        else:
            console.print(f"❌ [red]Failed to get statistics: {response.status_code}[/red]")

    except requests.exceptions.ConnectionError:
        console.print("❌ [red]ContextVault proxy not running[/red]")
        console.print("   Start it with: [bold]contextible start[/bold]")
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")


@graph_rag_group.command(name="health")
def health():
    """Check Graph RAG health status."""
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("🏥 Checking Graph RAG health...", total=None)

        try:
            response = requests.get('http://localhost:11435/api/graph-rag/health')
            time.sleep(0.3)

            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                available = data.get('available')
                message = data.get('message')

                if available:
                    progress.update(task, description="✅ Graph RAG is healthy!")
                    time.sleep(0.2)
                    console.print()
                    console.print(Panel(
                        f"[bold green]Status:[/bold green] {status}\n"
                        f"[bold green]Message:[/bold green] {message}",
                        title="✅ Graph RAG Health",
                        border_style="green"
                    ))
                else:
                    progress.update(task, description="❌ Graph RAG unavailable")
                    time.sleep(0.2)
                    console.print()
                    console.print(Panel(
                        f"[bold red]Status:[/bold red] {status}\n"
                        f"[bold red]Message:[/bold red] {message}",
                        title="❌ Graph RAG Health",
                        border_style="red"
                    ))
            else:
                progress.update(task, description="❌ Health check failed")
                time.sleep(0.2)
                console.print(f"\n❌ [red]Failed: {response.status_code}[/red]")

        except requests.exceptions.ConnectionError:
            progress.update(task, description="❌ Connection failed")
            time.sleep(0.2)
            console.print("\n❌ [red]ContextVault proxy not running[/red]")
            console.print("   Start it with: [bold]contextible start[/bold]")
        except Exception as e:
            progress.update(task, description="❌ Error occurred")
            time.sleep(0.2)
            console.print(f"\n❌ [red]Error: {e}[/red]")
