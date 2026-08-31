"""
test_real_call.py
Manual smoke test — makes a REAL call to the Gemini API.
Run this yourself locally once your .env is set up.
"""
from dotenv import load_dotenv

load_dotenv()  # loads GEMINI_API_KEY from .env

from src.parser import load_log_file, chunk_lines
from src.analyzer import get_provider

lines = load_log_file("logs/sample.log")
chunks = chunk_lines(lines, max_lines_per_chunk=200)

print(f"{len(chunks)} chunk(s) to analyze")

provider = get_provider("gemini-3.6-flash")
analysis = provider.analyze_chunk(chunks[0])

print("\n--- Summary ---")
print(analysis.summary)

print(f"\n--- Incidents ({len(analysis.incidents)}) ---")
for inc in analysis.incidents:
    print(f"[{inc.severity.value}] {inc.title}")
    print(f"  Module: {inc.affected_module}")
    print(f"  Root cause: {inc.root_cause}")
    print(f"  Fix: {inc.suggested_fix}")
    print(f"  Lines: {inc.related_lines}")
    print()