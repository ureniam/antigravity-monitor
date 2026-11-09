#!/usr/bin/env python3
import sys
import time
import argparse
from datetime import datetime, timezone

from rich import box
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.columns import Columns

from quota_fetcher import get_quota_data, format_time_diff

console = Console()

def get_color(percent: int) -> str:
    if percent > 65:
        return "green"
    elif percent > 30:
        return "yellow"
    return "red"

def make_bar(percent: int, width: int = 22) -> Text:
    color = get_color(percent)
    filled_len = int(round(width * percent / 100))
    empty_len = width - filled_len
    bar_text = Text()
    bar_text.append("[" + "█" * filled_len, style=f"bold {color}")
    bar_text.append("░" * empty_len + "]", style="dim white")
    bar_text.append(f" {percent}%", style=f"bold {color}")
    return bar_text

def build_family_panel(title: str, subtitle: str, data: dict, models: list, border_style: str) -> Panel:
    # Quota metrics table
    q_table = Table(box=box.SIMPLE, expand=True, padding=(0, 1), show_edge=False)
    q_table.add_column("Quota Window", style="bold white", width=18)
    q_table.add_column("Remaining Credit", width=32)
    q_table.add_column("Reset Time", justify="right")

    weekly = data.get("weekly")
    if weekly:
        w_bar = make_bar(weekly["percent"])
        w_time = format_time_diff(weekly["reset_iso"])
        q_table.add_row("Weekly Limit", w_bar, f"[bold]{w_time}[/bold]\n[dim]{weekly['reset_iso']}[/dim]")
    else:
        q_table.add_row("Weekly Limit", "[dim]N/A[/dim]", "-")

    five_hour = data.get("five_hour")
    if five_hour:
        f_bar = make_bar(five_hour["percent"])
        f_time = format_time_diff(five_hour["reset_iso"])
        q_table.add_row("5-Hour Rolling", f_bar, f"[bold]{f_time}[/bold]\n[dim]{five_hour['reset_iso']}[/dim]")
    else:
        q_table.add_row("5-Hour Rolling", "[dim]N/A[/dim]", "-")

    # Models breakdown table
    m_table = Table(box=box.MINIMAL, expand=True, padding=(0, 1), title="[bold dim]Shared Quota Models[/bold dim]")
    m_table.add_column("Model ID", style="cyan")
    m_table.add_column("Capability Tier", style="white")
    m_table.add_column("Tag", justify="right")

    for m in models:
        badge_style = "bold magenta" if any(k in m["badge"] for k in ["Opus", "Pro", "High"]) else "green"
        m_table.add_row(m["name"], m["type"], f"[{badge_style}][{m['badge']}][/{badge_style}]")

    group = Group(
        q_table,
        Text(""),
        m_table
    )

    return Panel(
        group,
        title=f"[bold {border_style}]{title}[/bold {border_style}]",
        subtitle=f"[dim]{subtitle}[/dim]",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2)
    )

def render_dashboard(data: dict) -> Panel:
    if "error" in data:
        return Panel(f"[bold red]Failed to fetch quota:[/bold red] {data['error']}", border_style="red", box=box.ROUNDED)

    gemini_panel = build_family_panel(
        title="⚡ GEMINI MODELS FAMILY",
        subtitle="Flash 3.8 / 3.7 / 3.6 & Pro 3.1",
        data=data.get("gemini", {}),
        models=data.get("models", {}).get("gemini", []),
        border_style="cyan"
    )

    claude_panel = build_family_panel(
        title="🧠 CLAUDE & GPT FAMILY",
        subtitle="Claude Sonnet 4.6, Opus 4.6 & GPT-OSS 120B",
        data=data.get("claude_gpt", {}),
        models=data.get("models", {}).get("claude_gpt", []),
        border_style="magenta"
    )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    header_table = Table(box=None, expand=True, show_header=False)
    header_table.add_column("Title", ratio=3)
    header_table.add_column("Meta", justify="right", ratio=2)
    header_table.add_row(
        Text.assemble(
            ("🌌 Google Antigravity ", "bold bright_white"),
            ("· Real-Time Quota & Credit Monitor", "bold cyan")
        ),
        Text(f"Synced: {now_utc}", style="dim yellow")
    )

    content = Group(
        Panel(header_table, box=box.ROUNDED, border_style="bright_blue"),
        Text(""),
        Columns([gemini_panel, claude_panel], expand=True)
    )

    return Panel(
        content,
        border_style="bright_blue",
        box=box.HEAVY,
        padding=(1, 1)
    )

def main():
    parser = argparse.ArgumentParser(description="Antigravity Live Model Quota & Credit Monitor")
    parser.add_argument("--live", "-w", action="store_true", help="Run in live continuous watch mode")
    parser.add_argument("--interval", "-i", type=int, default=10, help="Live refresh interval in seconds (default: 10)")
    parser.add_argument("--web", action="store_true", help="Launch the Web Dashboard")
    parser.add_argument("--port", type=int, default=7860, help="Web Dashboard port (default: 7860)")
    parser.add_argument("--json", action="store_true", help="Print quota output as JSON and exit")
    args = parser.parse_args()

    if args.web:
        import server
        server.run_server(port=args.port)
        return

    if args.json:
        import json
        print(json.dumps(get_quota_data(force_refresh=True), indent=2))
        return

    if not args.live:
        data = get_quota_data(force_refresh=True)
        console.print(render_dashboard(data))
        return

    console.print("[dim cyan]Starting Live Watch Mode... Press Ctrl+C to exit.[/dim cyan]")
    data = get_quota_data(force_refresh=True)
    with Live(render_dashboard(data), console=console, refresh_per_second=1, screen=True) as live:
        last_fetch = time.time()
        while True:
            time.sleep(1)
            now = time.time()
            if now - last_fetch >= args.interval:
                data = get_quota_data(force_refresh=True)
                last_fetch = now
            live.update(render_dashboard(data))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped.[/dim]")
        sys.exit(0)
