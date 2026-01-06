#!/usr/bin/env python3
"""
CLI Utilities - Enhanced Visual Output

Provides rich console output with colors, progress bars, and tables
for an improved user experience.
"""

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box
from typing import Dict, Any, List
import time

console = Console()


def print_banner():
    """Print the application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║   AI Factory Benchmarking Framework                   ║
    ║   High-Performance AI Infrastructure Testing          ║
    ╚═══════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_section(title: str, style: str = "bold blue"):
    """Print a section header"""
    console.print(f"\n[{style}]{'='*60}")
    console.print(f"[{style}]{title}")
    console.print(f"[{style}]{'='*60}[/{style}]\n")


def print_subsection(title: str):
    """Print a subsection header"""
    console.print(f"\n[bold yellow]▶ {title}[/bold yellow]")


def print_info(message: str):
    """Print an info message"""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_success(message: str):
    """Print a success message"""
    console.print(f"[green]✓[/green] {message}", style="green")


def print_warning(message: str):
    """Print a warning message"""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


def print_error(message: str):
    """Print an error message"""
    console.print(f"[red]✗[/red] {message}", style="red")


def print_benchmark_config(config: Dict[str, Any]):
    """Print benchmark configuration in a formatted table"""
    table = Table(title="Benchmark Configuration", box=box.ROUNDED)
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Clients", justify="right", style="green")
    table.add_column("RPS", justify="right", style="green")
    table.add_column("Duration", justify="right", style="yellow")
    
    for service in config.get('services', []):
        table.add_row(
            service.get('service_name', 'unknown'),
            service.get('service_type', 'unknown'),
            str(service.get('client_count', 1)),
            str(service.get('requests_per_second', 10)),
            f"{service.get('duration', 60)}s"
        )
    
    console.print(table)


def print_benchmark_results(results: Dict[str, Any]):
    """Print benchmark results in a formatted table"""
    table = Table(title="Benchmark Results Summary", box=box.DOUBLE)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green", justify="right")
    
    summary = results.get('summary', {})
    timing = results.get('timing', {})
    
    # Add summary metrics
    table.add_row("Total Requests", str(summary.get('total_requests', 0)))
    table.add_row("Successful", f"{summary.get('successful_requests', 0)} ({summary.get('success_rate', 0):.2f}%)")
    table.add_row("Failed", str(summary.get('failed_requests', 0)))
    table.add_row("", "")  # Separator
    
    # Add timing metrics
    table.add_row("Avg Latency", f"{timing.get('avg_duration', 0):.3f}s")
    table.add_row("Min Latency", f"{timing.get('min_duration', 0):.3f}s")
    table.add_row("Max Latency", f"{timing.get('max_duration', 0):.3f}s")
    table.add_row("", "")  # Separator
    
    # Add percentiles
    percentiles = results.get('percentiles', {})
    table.add_row("P50 (Median)", f"{percentiles.get('p50', 0):.3f}s")
    table.add_row("P95", f"{percentiles.get('p95', 0):.3f}s")
    table.add_row("P99", f"{percentiles.get('p99', 0):.3f}s")
    
    console.print(table)


def print_monitoring_info():
    """Print monitoring stack information"""
    import os
    
    # Get monitoring node from environment
    monitoring_node = os.environ.get('MONITORING_NODE', 'localhost')
    pushgateway_url = os.environ.get('PUSHGATEWAY_URL', f'http://{monitoring_node}:9091')
    
    panel = Panel(
        f"""[bold cyan]Monitoring Services[/bold cyan]

[green]Grafana:[/green]      http://{monitoring_node}:3000
                 Login: admin / admin

[green]Prometheus:[/green]   http://{monitoring_node}:9090

[green]Pushgateway:[/green]  {pushgateway_url}

[yellow]💡 Set PUSHGATEWAY_URL or MONITORING_NODE environment variable[/yellow]
[yellow]   to push metrics to remote monitoring stack[/yellow]""",
        box=box.DOUBLE,
        style="blue"
    )
    console.print(panel)


def print_completion_banner(benchmark_id: str, report_path: str):
    """Print completion banner with results location"""
    panel = Panel(
        f"""[bold green]✓ Benchmark Completed Successfully![/bold green]

[cyan]Benchmark ID:[/cyan]  {benchmark_id}
[cyan]Report saved to:[/cyan] {report_path}

[yellow]Next steps:[/yellow]
  • View JSON report: cat {report_path} | python -m json.tool
  • Check Grafana dashboards: http://localhost:3000
  • Query metrics: sqlite3 metrics.db
  • Export to Prometheus: python src/monitoring/prometheus_exporter.py {benchmark_id}""",
        box=box.DOUBLE,
        style="green"
    )
    console.print(panel)
