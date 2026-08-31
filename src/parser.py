"""
parser.py
Ingestion and chunking of log files before sending them to the LLM.
"""
from dataclasses import dataclass, field
import re
from pathlib import Path

@dataclass
class LogLine:
    raw: str
    line_number: int
    timestamp: str | None = None
    level: str | None = None
    module: str | None = None
    message: str | None = None


#Recognized log level formats
LOG_LEVELS = ["DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL", "FATAL"]

#Fault-tolerant regex : "2026-08-31 08:15:15 CRITICAL [payment] message..."
LOG_LINE_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
    r"\s+(?P<level>" + "|".join(LOG_LEVELS) + r")"
    r"\s*(?:\[(?P<module>[^\]]+)\])?"
    r"\s*(?P<message>.*)$"
)


def parse_line(raw: str, line_number: int) -> LogLine:
    """parses a raw line into a structured LogLine (or a raw one if the format does not match)"""
    match = LOG_LINE_PATTERN.match(raw.strip())
    if not match:
        return LogLine(raw=raw.rstrip("\n"), line_number=line_number)

    data = match.groupdict()
    level = data["level"].upper()
    if level == "WARNING":
        level = "WARN"

    return LogLine(
        raw=raw.rstrip("\n"),
        line_number=line_number,
        timestamp=data["timestamp"],
        level=level,
        module=data["module"],
        message=data["message"],
    )


def load_log_file(path: str | Path) -> list[LogLine]:
    """loads a log file and returns a list of parsing lines"""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier de log introuvable : {path}")
    if not file_path.is_file():
        raise ValueError(f"Le chemin fourni n'est pas un fichier : {path}")

    lines: list[LogLine] = []
    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for i, raw_line in enumerate(f, start=1):
            if raw_line.strip():
                lines.append(parse_line(raw_line, i))
    return lines


@dataclass
class LogChunk:
    """a batch of log lines ready to be send to LLM"""
    lines: list[LogLine] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def to_text(self) -> str:
        return "\n".join(line.raw for line in self.lines)

    @property
    def level_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for line in self.lines:
            if line.level:
                counts[line.level] = counts.get(line.level, 0) + 1
        return counts


def chunk_lines(
    lines: list[LogLine],
    max_lines_per_chunk: int = 200,) -> list[LogChunk]:

    """
    Splits a list of LogLines into chunks of limited size.
    Simple strategy based on the number of lines (sufficient for an MVP).
    """
    if not lines:
        return []

    chunks: list[LogChunk] = []
    for i in range(0, len(lines), max_lines_per_chunk):
        batch = lines[i : i + max_lines_per_chunk]
        chunks.append(
            LogChunk(
                lines=batch,
                start_line=batch[0].line_number,
                end_line=batch[-1].line_number,
            )
        )
    return chunks


def prioritize_chunks(chunks: list[LogChunk]) -> list[LogChunk]:
    """
    Sorts the chunks to prioritize analyzing those containing the most severe levels (CRITICAL, then ERROR)
    useful for limiting the number of LLM calls on very large files.
    """
    severity_rank = {lvl: i for i, lvl in enumerate(LOG_LEVELS)}

    def chunk_score(chunk: LogChunk) -> int:
        if not chunk.level_counts:
            return -1
        return max(severity_rank.get(lvl, -1) for lvl in chunk.level_counts)

    return sorted(chunks, key=chunk_score, reverse=True)