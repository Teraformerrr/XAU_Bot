from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def banner(title: str):
    console.rule(f"[bold cyan]{title}")


def kv(title: str, mapping: dict):
    table = Table(box=box.MINIMAL_HEAVY_HEAD)
    table.add_column(title, style="bold")
    table.add_column("Value")
    for k, v in mapping.items():
        table.add_row(str(k), str(v))
    console.print(table)


def info(msg: str):
    console.print(f"[green]INFO[/]: {msg}")


def warn(msg: str):
    console.print(f"[yellow]WARN[/]: {msg}")


def error(msg: str):
    console.print(f"[red]ERROR[/]: {msg}")
