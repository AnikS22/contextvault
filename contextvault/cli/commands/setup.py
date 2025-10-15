"""Setup commands for ContextVault CLI."""

import subprocess
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

@click.command()
def setup():
    """Initialize Contextible for first-time use."""

    # Show animated header
    console.print("\n[bold cyan]✨ Contextible Setup Wizard ✨[/bold cyan]\n", justify="center")
    time.sleep(0.3)
    
    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Check Python version
        task = progress.add_task("🐍 Checking Python version...", total=None)
        time.sleep(0.5)

        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            progress.update(task, description=f"❌ Python {python_version.major}.{python_version.minor} found (need 3.8+)")
            console.print(f"\n❌ [red]Python {python_version.major}.{python_version.minor} found, but 3.8+ is required[/red]")
            return

        progress.update(task, description=f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    console.print()
    
    # Check dependencies
    console.print("\n📦 [blue]Checking dependencies...[/blue]")
    
    required_packages = [
        "sqlalchemy", "fastapi", "uvicorn", "requests", "pydantic"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            console.print(f"   ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            console.print(f"   ❌ {package}")
    
    if missing_packages:
        console.print(f"\n❌ [red]Missing required packages: {', '.join(missing_packages)}[/red]")
        console.print("   Install with: pip install -r requirements.txt")
        return
    
    # Check optional dependencies
    console.print("\n📦 [blue]Checking optional dependencies...[/blue]")

    optional_packages = {
        "sentence_transformers": "Semantic search (recommended)",
        "sklearn": "Fallback semantic search (required if sentence_transformers missing)"
    }

    for package, description in optional_packages.items():
        try:
            __import__(package)
            console.print(f"   ✅ {package} - {description}")
        except ImportError:
            if package == "sklearn":
                console.print(f"   ❌ {package} - {description}")
                console.print("   Install with: pip install scikit-learn")
            else:
                console.print(f"   ⚠️ {package} - {description}")
                console.print("   Install with: pip install sentence-transformers")

    # Check Graph RAG dependencies (REQUIRED for production)
    console.print("\n🔗 [bold blue]Checking Graph RAG (Primary Retrieval System)...[/bold blue]")

    graph_rag_packages = {
        "neo4j": "Neo4j graph database driver (REQUIRED)",
        "spacy": "Entity extraction for Graph RAG (REQUIRED)",
        "pandas": "Data processing for Graph RAG (REQUIRED)"
    }

    graph_rag_available = True
    missing_packages = []

    for package, description in graph_rag_packages.items():
        try:
            __import__(package)
            console.print(f"   ✅ {package} - {description}")
        except ImportError:
            console.print(f"   ❌ {package} - {description}")
            missing_packages.append(package)
            graph_rag_available = False

    if missing_packages:
        console.print(f"\n   [red]Missing Graph RAG packages. Install with:[/red]")
        console.print(f"   [yellow]pip install {' '.join(missing_packages)}[/yellow]")

    # Check spaCy model if spacy is installed
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            console.print("   ✅ spacy model (en_core_web_sm)")
        except:
            console.print("   ❌ spacy model (en_core_web_sm) not found - REQUIRED")
            console.print("   [yellow]Install with: python -m spacy download en_core_web_sm[/yellow]")
            graph_rag_available = False
    except ImportError:
        console.print("   ⚠️  spacy not available - install first")

    # Check Neo4j availability (CRITICAL)
    console.print("\n🗄️  [bold blue]Checking Neo4j Database (REQUIRED)...[/bold blue]")
    neo4j_running = False

    try:
        import requests
        response = requests.get("http://localhost:7474", timeout=2)
        console.print("   ✅ Neo4j is running (http://localhost:7474)")
        neo4j_running = True
    except:
        console.print("   ❌ Neo4j is NOT running - REQUIRED for Graph RAG")
        console.print("\n   [bold yellow]Start Neo4j with Docker:[/bold yellow]")
        console.print("   [cyan]docker run -d --name contextvault-neo4j \\[/cyan]")
        console.print("   [cyan]  -p 7474:7474 -p 7687:7687 \\[/cyan]")
        console.print("   [cyan]  -e NEO4J_AUTH=neo4j/password \\[/cyan]")
        console.print("   [cyan]  neo4j:latest[/cyan]")
        console.print("\n   [dim]Access Neo4j Browser at: http://localhost:7474[/dim]")

    if not graph_rag_available or not neo4j_running:
        console.print("\n   [bold red]⚠️  Graph RAG is NOT fully configured![/bold red]")
        console.print("   [yellow]Graph RAG is the default retrieval system. Please install all dependencies.[/yellow]")
    
    # Check Ollama
    console.print("\n🤖 [blue]Checking Ollama...[/blue]")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get("models", [])
            
            if models:
                console.print(f"   ✅ Ollama is running with {len(models)} models")
                
                # Check for mistral:latest
                model_names = [model.get("name", "") for model in models]
                if "mistral:latest" in model_names:
                    console.print("   ✅ mistral:latest is available")
                else:
                    console.print("   ⚠️ mistral:latest not found")
                    console.print("   Install with: ollama pull mistral:latest")
            else:
                console.print("   ⚠️ Ollama is running but no models found")
                console.print("   Install a model: ollama pull mistral:latest")
        else:
            console.print(f"   ❌ Ollama API error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        console.print("   ❌ Ollama is not running")
        console.print("   Start with: ollama serve")
    except Exception as e:
        console.print(f"   ❌ Ollama check failed: {e}")
    
    # Initialize ContextVault
    console.print("\n🔧 [blue]Initializing ContextVault...[/blue]")
    
    try:
        from contextvault.database import init_database
        init_database()
        console.print("   ✅ Database initialized")
        
        # Create default permissions
        from contextvault.database import get_db_context
        from contextvault.models.permissions import Permission
        
        with get_db_context() as db:
            # Check if permissions already exist
            existing = db.query(Permission).filter(
                Permission.model_id == 'mistral:latest'
            ).first()
            
            if not existing:
                permission = Permission(
                    model_id='mistral:latest',
                    model_name='Mistral (Latest)',
                    scope='personal,work,preferences,notes',
                    is_active=True
                )
                db.add(permission)
                db.commit()
                console.print("   ✅ Default permissions created")
            else:
                console.print("   ✅ Permissions already exist")
        
        # Add sample context
        from contextvault.models.context import ContextEntry
        
        with get_db_context() as db:
            existing_count = db.query(ContextEntry).count()
            
            if existing_count == 0:
                sample_entries = [
                    {
                        'content': 'I am a software engineer who loves Python and testing. I prefer detailed explanations and want to understand how systems work.',
                        'context_type': 'preference',
                        'source': 'sample',
                        'tags': ['python', 'testing', 'software', 'engineering']
                    },
                    {
                        'content': 'I have two cats named Luna and Pixel. They are playful and love string toys.',
                        'context_type': 'note',
                        'source': 'sample',
                        'tags': ['pets', 'cats', 'luna', 'pixel']
                    },
                    {
                        'content': 'I drive a Tesla Model 3 and live in San Francisco. I enjoy hiking and rock climbing.',
                        'context_type': 'note',
                        'source': 'sample',
                        'tags': ['tesla', 'san francisco', 'hiking', 'rock climbing']
                    }
                ]
                
                for entry_data in sample_entries:
                    entry = ContextEntry(**entry_data)
                    db.add(entry)
                
                db.commit()
                console.print("   ✅ Sample context added")
            else:
                console.print("   ✅ Context entries already exist")
        
        time.sleep(0.3)
        console.print("\n" + "="*60)
        console.print("🎉 [bold green]Setup Complete! Contextible is ready to use![/bold green]", justify="center")
        console.print("="*60 + "\n")

        # Show next steps with Graph RAG emphasis
        console.print(Panel(
            """[bold cyan]🚀 Quick Start Guide (Graph RAG Enabled)[/bold cyan]

[bold]1. Start Neo4j (REQUIRED):[/bold]
   [yellow]docker run -d --name contextvault-neo4j \\
     -p 7474:7474 -p 7687:7687 \\
     -e NEO4J_AUTH=neo4j/password neo4j:latest[/yellow]

[bold]2. Start the Proxy:[/bold]
   [yellow]contextible start[/yellow]

   This starts Contextible on port 11435 with Graph RAG
   (Ollama runs on 11434)

[bold]3. Add Knowledge to Graph RAG:[/bold]
   [yellow]contextible graph-rag add "John Smith works at Acme Corp" --id doc1[/yellow]
   [yellow]contextible graph-rag add "Acme raised $50M funding" --id doc2[/yellow]

[bold]4. Check Graph RAG Status:[/bold]
   [yellow]contextible graph-rag stats[/yellow]
   [yellow]contextible graph-rag search "Acme Corp" --show-entities[/yellow]

[bold]5. Use With Your AI:[/bold]
   Point your AI client to [cyan]http://localhost:11435[/cyan]
   instead of [dim]http://localhost:11434[/dim]

[bold green]✨ Your AI now has Graph RAG memory with entity relationships![/bold green]

[dim]Legacy context commands still work:
  contextible context add "I love Python"
  contextible context search "python"[/dim]""",
            title="✨ Next Steps",
            border_style="cyan",
            box=box.ROUNDED
        ))
        
    except Exception as e:
        console.print(f"❌ [red]Setup failed: {e}[/red]")
        console.print("   Check the error message above and try again")
