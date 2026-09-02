"""
main.py
LogAI CLI entrypoint — analyzes a log file using an LLM and displays
or exports the results.
"""
import argparse
import sys

from dotenv import load_dotenv

from src.analyzer import get_provider
from src.formatter import display_analyses, export_json, export_markdown
from src.parser import chunk_lines, load_log_file, prioritize_chunks

DEFAULT_MODEL = "gemini-3.6-flash"
MAX_CHUNKS_TO_ANALYZE = 5  # safety cap to avoid burning API quota on huge files


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logai",
        description="LogAI — AI copilot for log analysis (anomaly detection, root cause, fixes).",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the log file to analyze",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--export",
        choices=["markdown", "json"],
        default=None,
        help="Export format for the analysis report",
    )
    parser.add_argument(
        "--max-lines-per-chunk",
        type=int,
        default=200,
        help="Max number of log lines sent to the LLM per API call (default: 200)",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    try:
        lines = load_log_file(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not lines:
        print(f"'{args.file}' is empty, nothing to analyze.")
        return 0

    chunks = chunk_lines(lines, max_lines_per_chunk=args.max_lines_per_chunk)
    chunks = prioritize_chunks(chunks)

    if len(chunks) > MAX_CHUNKS_TO_ANALYZE:
        print(
            f"Note: {len(chunks)} chunks found, analyzing only the "
            f"{MAX_CHUNKS_TO_ANALYZE} most severe ones to save API quota."
        )
        chunks = chunks[:MAX_CHUNKS_TO_ANALYZE]

    try:
        provider = get_provider(args.model)
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    analyses = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Analyzing chunk {i}/{len(chunks)} (lines {chunk.start_line}-{chunk.end_line})...")
        analysis = provider.analyze_chunk(chunk)
        analyses.append(analysis)

    display_analyses(analyses, args.file)

    if args.export == "markdown":
        output_path = export_markdown(analyses, args.file)
        print(f"\nReport exported to: {output_path}")
    elif args.export == "json":
        output_path = export_json(analyses, args.file)
        print(f"\nReport exported to: {output_path}")

    return 0


def main() -> None:
    load_dotenv()
    parser = build_arg_parser()
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()