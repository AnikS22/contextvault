"""Easy memory recall (search) commands for ContextVault."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.syntax import Syntax

console = Console()


@click.command(name="recall")
@click.argument("query", required=True)
@click.option("--limit", "-n", default=10, help="Maximum number of results")
@click.option("--type", "filter_type", help="Filter by document type")
@click.option("--full", is_flag=True, help="Show full content (not just preview)")
def recall_memory(query, limit, filter_type, full):
    """
    Search your AI's memory.

    Examples:
        contextible recall "python projects"
        contextible recall "contracts" --type contract --limit 5
        contextible recall "meeting notes" --full
    """
    from ...storage import VectorDatabase

    console.print()
    console.print(f"[bold cyan]🔍 Searching:[/bold cyan] {query}")
    console.print()

    with console.status("[bold green]Searching memory..."):
        try:
            db = VectorDatabase()
            if not db.is_available():
                console.print("[red]✗ Vector database not available.[/red]")
                console.print("[dim]Run 'contextible feed' to add documents first.[/dim]\n")
                return

            # Build filter
            where_filter = None
            if filter_type:
                where_filter = {"type": filter_type}

            # Search
            results = db.search(query, n_results=limit, where=where_filter)

        except Exception as e:
            console.print(f"[red]✗ Search failed: {e}[/red]\n")
            return

    if not results:
        console.print(Panel.fit(
            "[yellow]No results found.[/yellow]\n\n"
            "Try a different search query or add more documents with:\n"
            "[cyan]contextible feed <file>[/cyan]",
            border_style="yellow"
        ))
        console.print()
        return

    # Display results
    console.print(f"[green]Found {len(results)} results:[/green]")
    console.print()

    for i, result in enumerate(results, 1):
        metadata = result.get("metadata", {})
        content = result["content"]
        distance = result.get("distance", 0)

        # Calculate relevance score (lower distance = higher relevance)
        relevance = max(0, min(100, int((2 - distance) * 50)))

        # Header
        doc_type = metadata.get("type", metadata.get("document_type", "unknown"))
        source = metadata.get("filename", metadata.get("source", "N/A"))

        console.print(f"[bold cyan]{i}. [{doc_type}][/bold cyan] {source}")
        console.print(f"   [dim]Relevance: {relevance}%  |  Distance: {distance:.4f}[/dim]")

        # Show metadata if available
        if metadata:
            meta_items = []
            for key in ["project", "client", "date", "category"]:
                if key in metadata:
                    meta_items.append(f"{key}: {metadata[key]}")

            if meta_items:
                console.print(f"   [dim]{' | '.join(meta_items)}[/dim]")

        # Content
        if full:
            # Show full content
            console.print(Panel(
                content,
                border_style="dim",
                box=box.ROUNDED
            ))
        else:
            # Show preview
            preview = content[:300].replace("\n", " ")
            if len(content) > 300:
                preview += "..."
            console.print(f"   {preview}")

        console.print()

    console.print("[dim]💡 Use --full to see complete content[/dim]")
    console.print()


@click.command(name="recent")
@click.option("--limit", "-n", default=20, help="Number of recent documents")
def show_recent(limit):
    """Show recently added documents."""
    from ...storage import VectorDatabase

    console.print()

    with console.status("[bold green]Loading recent documents..."):
        try:
            db = VectorDatabase()
            if not db.is_available():
                console.print("[red]✗ Vector database not available.[/red]\n")
                return

            # Get all documents (ChromaDB doesn't have a "recent" query, so we get all)
            results = db.search("", n_results=limit)

        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]\n")
            return

    if not results:
        console.print("[yellow]No documents found.[/yellow]")
        console.print("[dim]Add documents with: contextible feed <file>[/dim]\n")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Source", style="green")
    table.add_column("Preview", style="dim")

    for i, result in enumerate(results[:limit], 1):
        metadata = result.get("metadata", {})
        content = result["content"]

        doc_type = metadata.get("type", metadata.get("document_type", "unknown"))
        source = metadata.get("filename", metadata.get("source", "N/A"))
        preview = content[:50].replace("\n", " ")

        if len(content) > 50:
            preview += "..."

        table.add_row(str(i), doc_type, source, preview)

    console.print(table)
    console.print()
    console.print(f"[dim]Showing {min(len(results), limit)} most recent documents[/dim]")
    console.print()


@click.command(name="stats-recall")
def recall_stats():
    """Show memory statistics."""
    from ...storage import VectorDatabase

    console.print()

    with console.status("[bold green]Calculating statistics..."):
        try:
            db = VectorDatabase()
            if not db.is_available():
                console.print("[red]✗ Vector database not available.[/red]\n")
                return

            stats = db.get_statistics()

            # Get type breakdown (would need to query all docs)
            total_docs = stats["total_documents"]

        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]\n")
            return

    console.print(Panel.fit(
        f"[bold cyan]🧠 Memory Statistics[/bold cyan]\n\n"
        f"📄 Total memories: [green]{total_docs:,}[/green]\n"
        f"💾 Storage: [green]{stats['storage_size_mb']:.2f} MB[/green]\n"
        f"📁 Collection: [cyan]{stats['collection_name']}[/cyan]\n\n"
        f"[dim]Search with: contextible recall \"query\"[/dim]",
        border_style="cyan"
    ))
    console.print()
