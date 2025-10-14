"""Easy document feeding commands for ContextVault."""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich import box

console = Console()


@click.command(name="feed")
@click.argument("paths", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("--type", "doc_type", help="Document type (contract, email, note, etc.)")
@click.option("--recursive", "-r", is_flag=True, help="Process directories recursively")
@click.option("--pattern", help="File pattern for filtering (e.g., '*.pdf')")
def feed_documents(paths, doc_type, recursive, pattern):
    """
    Add documents to your AI's memory.

    Examples:
        contextible feed document.txt
        contextible feed folder/ --recursive
        contextible feed contracts/ --type contract --pattern "*.pdf"
        contextible feed file1.md file2.txt file3.pdf
    """
    from ...storage import VectorDatabase, DocumentIngestionPipeline

    console.print()
    console.print(Panel.fit(
        "[bold cyan]📥 Document Ingestion[/bold cyan]\n"
        "Adding documents to your AI's unlimited memory...",
        border_style="cyan"
    ))
    console.print()

    # Initialize
    with console.status("[bold green]Initializing..."):
        try:
            db = VectorDatabase()
            if not db.is_available():
                console.print("[red]✗ Vector database not available.[/red]")
                console.print("[dim]Install ChromaDB: pip install chromadb[/dim]\n")
                return

            pipeline = DocumentIngestionPipeline(db, chunk_size=500, batch_size=50)
        except Exception as e:
            console.print(f"[red]✗ Initialization failed: {e}[/red]\n")
            return

    # Process each path
    total_files = 0
    total_chunks = 0
    failed_files = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:

        for path_str in paths:
            path = Path(path_str)

            if path.is_file():
                # Single file
                task = progress.add_task(f"Processing {path.name}...", total=1)

                try:
                    successful, failed, chunk_ids = pipeline.ingest_file(
                        str(path),
                        document_type=doc_type
                    )

                    if successful > 0:
                        total_files += 1
                        total_chunks += successful
                        progress.update(task, completed=1, description=f"✓ {path.name} ({successful} chunks)")
                    else:
                        failed_files += 1
                        progress.update(task, completed=1, description=f"✗ {path.name} failed")

                except Exception as e:
                    failed_files += 1
                    progress.update(task, completed=1, description=f"✗ {path.name}: {e}")

            elif path.is_dir():
                # Directory
                task = progress.add_task(f"Scanning {path.name}/...", total=None)

                try:
                    stats = pipeline.ingest_directory(
                        str(path),
                        recursive=recursive,
                        file_pattern=pattern,
                        document_type=doc_type
                    )

                    total_files += stats["successful_files"]
                    failed_files += stats["failed_files"]
                    total_chunks += stats["total_chunks"]

                    progress.update(
                        task,
                        completed=1,
                        description=f"✓ {path.name}/ ({stats['successful_files']} files, {stats['total_chunks']} chunks)"
                    )

                except Exception as e:
                    failed_files += 1
                    progress.update(task, completed=1, description=f"✗ {path.name}/: {e}")

    # Results summary
    console.print()

    if total_files > 0:
        console.print(Panel.fit(
            f"[bold green]✓ Ingestion Complete![/bold green]\n\n"
            f"📄 Files processed: [cyan]{total_files}[/cyan]\n"
            f"📦 Chunks created: [cyan]{total_chunks:,}[/cyan]\n"
            f"❌ Failed: [red]{failed_files}[/red]\n\n"
            f"[dim]Your AI can now recall information from these documents.[/dim]",
            border_style="green",
            box=box.ROUNDED
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]✗ No documents processed[/bold red]\n\n"
            f"Check the errors above and try again.",
            border_style="red"
        ))

    console.print()


@click.command(name="status-feed")
def feed_status():
    """Show document storage statistics."""
    from ...storage import VectorDatabase

    console.print()

    try:
        db = VectorDatabase()
        if not db.is_available():
            console.print("[red]✗ Vector database not available.[/red]\n")
            return

        stats = db.get_statistics()
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]\n")
        return

    console.print(Panel.fit(
        f"[bold cyan]📊 Document Storage Statistics[/bold cyan]\n\n"
        f"📄 Total documents: [green]{stats['total_documents']:,}[/green]\n"
        f"💾 Storage size: [green]{stats['storage_size_mb']:.2f} MB[/green]\n"
        f"📁 Collection: [cyan]{stats['collection_name']}[/cyan]\n"
        f"📂 Location: [dim]{stats['persist_directory']}[/dim]\n\n"
        f"[dim]Add more with: contextible feed <file>[/dim]",
        border_style="cyan"
    ))
    console.print()
