"""
formatter.py
Terminal UI display (rich) and analysis report exports (Markdown / JSON).
"""
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.analyzer import ChunkAnalysis, Severity

console = Console()

SEVERITY_STYLE = {
    Severity.INFO: "cyan",
    Severity.WARN: "yellow",
    Severity.ERROR: "red",
    Severity.CRITICAL: "bold white on red",
}


def display_analyses(analyses: list[ChunkAnalysis], log_file: str) -> None:
    """Display the full analysis report in the terminal via rich."""
    console.rule(f"[bold]LogAI — Analysis of {log_file}[/bold]")

    all_incidents = [inc for a in analyses for inc in a.incidents]
    if not all_incidents:
        console.print(Panel("No incident detected in this file.", style="green"))
        return

    # Global summary
    summary_text = "\n".join(f"• {a.summary}" for a in analyses if a.summary)
    console.print(Panel(summary_text, title="Summary", border_style="blue"))

    # Incident table, sorted by descending severity
    severity_order = {Severity.CRITICAL: 0, Severity.ERROR: 1, Severity.WARN: 2, Severity.INFO: 3}
    sorted_incidents = sorted(all_incidents, key=lambda i: severity_order.get(i.severity, 99))

    table = Table(title="Detected incidents", show_lines=True)
    table.add_column("Severity", justify="center")
    table.add_column("Title")
    table.add_column("Module")
    table.add_column("Root cause")
    table.add_column("Suggested fix")
    table.add_column("Lines")

    for inc in sorted_incidents:
        style = SEVERITY_STYLE.get(inc.severity, "white")
        table.add_row(
            Text(inc.severity.value, style=style),
            inc.title,
            inc.affected_module or "—",
            inc.root_cause,
            inc.suggested_fix,
            ", ".join(str(l) for l in inc.related_lines) or "—",
        )

    console.print(table)

    counts: dict[Severity, int] = {}
    for inc in all_incidents:
        counts[inc.severity] = counts.get(inc.severity, 0) + 1
    counts_str = "  ".join(f"{sev.value}: {n}" for sev, n in counts.items())
    console.print(Panel(counts_str, title="Breakdown by severity", border_style="magenta"))


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_markdown(analyses: list[ChunkAnalysis], log_file: str, output_dir: str = ".") -> Path:
    """Export the analysis report as a Markdown file."""
    lines = [
        f"# LogAI Analysis Report — `{log_file}`",
        "",
        f"_Generated on {datetime.now():%Y-%m-%d %H:%M:%S}_",
        "",
        "## Summary",
    ]
    for a in analyses:
        if a.summary:
            lines.append(f"- {a.summary}")
    lines.append("")

    all_incidents = [inc for a in analyses for inc in a.incidents]

    if not all_incidents:
        lines.append("No incident detected.")
    else:
        lines.append("## Detected incidents")
        lines.append("")
        lines.append("| Severity | Title | Module | Root cause | Fix | Lines |")
        lines.append("|---|---|---|---|---|---|")
        for inc in all_incidents:
            lines.append(
                f"| {inc.severity.value} | {inc.title} | {inc.affected_module or '—'} "
                f"| {inc.root_cause} | {inc.suggested_fix} "
                f"| {', '.join(str(l) for l in inc.related_lines) or '—'} |"
            )

    output_path = Path(output_dir) / f"analysis_report_{_timestamp()}.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_json(analyses: list[ChunkAnalysis], log_file: str, output_dir: str = ".") -> Path:
    """Export the analysis report as a JSON file."""
    payload = {
        "log_file": log_file,
        "generated_at": datetime.now().isoformat(),
        "chunks": [json.loads(a.model_dump_json()) for a in analyses],
    }
    output_path = Path(output_dir) / f"analysis_report_{_timestamp()}.json"
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path