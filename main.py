from datetime import datetime
import pandas as pd
import typer
from rich.console import Console
from rich.table import Table
import jira_client
from jira_client import auth_from_config, save_config, load_config, delete_config, search_issues, view_config

app = typer.Typer(help="🧰 Jira CLI Tool - Manage tasks easily from your terminal!")
console = Console()

user_app = typer.Typer(help="Manage Jira user credentials.")
app.add_typer(user_app, name="user")

@user_app.command("set")
def auth_set():
    """Set or update Jira credentials."""
    email = typer.prompt("Enter your Jira email")
    token = typer.prompt("Enter your Jira API token", hide_input=True)
    url = typer.prompt("Enter your Jira site URL (e.g. https://yourname.atlassian.net)")
    save_config(email, token, url)
    typer.echo("✅ Jira credentials saved successfully.")


@user_app.command("view")
def auth_view():
    """View stored credentials (token is masked)."""
    view_config()


@user_app.command("delete")
def auth_delete():
    """Delete stored credentials."""
    delete_config()


@user_app.command()
def whoami():
    """Check current Jira authentication."""
    jira = auth_from_config()
    me = jira.current_user()
    typer.echo(f"👋 Authenticated as: {me}")

@app.command()
def list(
    username: str = typer.Option(None, "--user", "-u", help="Filter by assignee username/email"),
    date: str = typer.Option(None, "--date", "-d", help="Filter by created date (YYYY-MM-DD)"),
    status: list[str] = typer.Option(None, "--status", "-s", help="Filter by one or more issue statuses"),
    due_now: bool = typer.Option(False, "--due-now", help="Show issues due today or overdue"),
    export: bool = typer.Option(False, "--export", "-e", help="Export results")
):
    """
    List Jira issues assigned to you (or another user),
    with optional filters for date, status, and due today or overdue.
    """

    try:
        auth_from_config()
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        typer.echo("👉 Run `python main.py user set` first to configure your Jira credentials.")
        raise typer.Exit(code=1)


    try:
        df = search_issues(username=username, date=date, status=status)
    except Exception as e:
        console.print(f"[red]❌ Error fetching issues: {e}[/red]")
        raise typer.Exit(code=1)

    if df.empty:
        console.print("[green]No issues found ✅[/green]")
        raise typer.Exit()


    if due_now:
        today = pd.Timestamp.now().normalize()
        df["Due"] = pd.to_datetime(df["Due"], errors="coerce").dt.normalize()
        df = df[df["Due"].notna() & (df["Due"] <= today)]


    if df.empty:
        console.print("[yellow]No issues match your filters.[/yellow]")
        raise typer.Exit()
    if export and not df.empty:
        from datetime import datetime

        date_str = datetime.now().strftime("%Y-%m-%d")
        user_part = username if username else "me"
        status_part = status if status else "all"
        date_part = date if date else date_str

        filename = f"{user_part}_{status_part}_{date_part}_issues.csv"
        df.to_csv(filename, index=False)
        typer.echo(f"📁 Exported filtered issues to {filename}")
    console.print(f"[green]✅ Found {len(df)} issues.")

    table = Table(title="Filtered Jira Issues", show_lines=True)
    for col in df.columns:
        table.add_column(col, style="cyan")

    for _, row in df.iterrows():
        table.add_row(*[str(v or "") for v in row.values])

    console.print(table)


@app.command()
def create(project: str = typer.Option(..., "--project", "-p"),
           summary: str = typer.Option(..., "--summary", "-s"),
           description: str = typer.Option("", "--description", "-d"),
           issue_type: str = typer.Option("Task", "--type", "-t")):
    """Create a single Jira issue"""
    try:
        jira = auth_from_config()
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        typer.echo("👉 Run `python main.py user set` first to configure your Jira credentials.")
        raise typer.Exit(code=1)
    jira_client.create_issue(project, summary, description, issue_type)

@app.command()
def bulk(csv: str = typer.Option(..., "--csv", "-c"),
         project: str = typer.Option(..., "--project", "-p")):
    """Bulk upload Jira issues from a CSV"""
    try:
        jira = auth_from_config()
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        typer.echo("👉 Run `python main.py user set` first to configure your Jira credentials.")
        raise typer.Exit(code=1)
    jira_client.bulk_create_from_csv(csv, project)

if __name__ == "__main__":
    app()
