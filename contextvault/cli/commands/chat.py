"""Interactive Chat Mode for ContextVault CLI."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import requests

console = Console()


@click.command(name="chat")
@click.option("--model", default="ollama:mistral", help="Model to use (e.g., ollama:llama3.1)")
@click.option("--use-graph-rag", is_flag=True, default=True, help="Use Graph RAG for context")
def interactive_chat(model: str, use_graph_rag: bool):
    """Start an interactive chat session with memory."""

    console.print(Panel(
        f"[bold cyan]ContextVault Interactive Chat[/bold cyan]\n\n"
        f"Model: {model}\n"
        f"Graph RAG: {'Enabled' if use_graph_rag else 'Disabled'}\n\n"
        f"Type 'exit' or 'quit' to end the session\n"
        f"Type '/help' for commands",
        title="🧠 ContextVault Chat",
        border_style="cyan"
    ))

    conversation_history = []

    while True:
        try:
            # Get user input
            user_input = console.input("\n[bold green]You:[/bold green] ")

            if not user_input.strip():
                continue

            # Check for exit commands
            if user_input.lower() in ["exit", "quit", "/quit", "/exit"]:
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break

            # Check for help command
            if user_input.lower() == "/help":
                console.print(Panel(
                    "[bold]Available Commands:[/bold]\n\n"
                    "/help - Show this help message\n"
                    "/clear - Clear conversation history\n"
                    "/model <name> - Switch model\n"
                    "/graph on|off - Toggle Graph RAG\n"
                    "exit, quit - End session",
                    title="Help",
                    border_style="blue"
                ))
                continue

            # Check for clear command
            if user_input.lower() == "/clear":
                conversation_history = []
                console.print("[yellow]Conversation history cleared[/yellow]")
                continue

            # Add to conversation history
            conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # Make request to ContextVault proxy
            try:
                response = requests.post(
                    "http://localhost:11435/api/chat",
                    json={
                        "model": model.split(":")[-1] if ":" in model else model,
                        "messages": conversation_history,
                        "use_graph_rag": use_graph_rag,
                        "stream": False
                    },
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    assistant_message = data.get("message", {}).get("content", "")

                    # Add to conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": assistant_message
                    })

                    # Display response
                    console.print("\n[bold blue]Assistant:[/bold blue]")
                    console.print(Markdown(assistant_message))

                else:
                    console.print(f"[red]Error: {response.status_code}[/red]")
                    console.print(f"[dim]{response.text}[/dim]")

            except requests.exceptions.ConnectionError:
                console.print("[red]❌ ContextVault proxy not running[/red]")
                console.print("[yellow]Start it with: contextible start[/yellow]")
                break

            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Goodbye! 👋[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
