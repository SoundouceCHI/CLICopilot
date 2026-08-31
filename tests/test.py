import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.parser import LogLine, parse_line, load_log_file, chunk_lines, prioritize_chunks


l1 = parse_line("2026-08-31 08:15:15 CRITICAL [payment] Circuit breaker ouvert", 1)
print(l1)
assert l1.level == "CRITICAL"
assert l1.module == "payment"

# WARNING case -> normalisé en WARN
l2 = parse_line("2026-08-31 08:14:22 WARNING [cache] Cache miss élevé", 2)
assert l2.level == "WARN"

# Cas qui ne matche pas le format -> fallback brut
l3 = parse_line("une ligne bizarre sans format", 3)
print(l3)
assert l3.level is None

print("OK")

#load_log_file test
lines = load_log_file("logs/sample.log")
print(f"{len(lines)} lignes chargées")
for l in lines:
    print(l.line_number, l.level, l.module, "-", l.message)

# Test fichier inexistant
try:
    load_log_file("logs/nope.log")
    print("aurait dû lever une exception")
except FileNotFoundError:
    print("FileNotFoundError bien levée")

#chunk_lines test 
lines = load_log_file("logs/sample.log")

chunks = chunk_lines(lines, max_lines_per_chunk=2)
print(f"{len(chunks)} chunks")
for c in chunks:
    print(f"  chunk {c.start_line}-{c.end_line}: {c.level_counts}")
    print("  texte:", repr(c.to_text()[:50]))


lines = load_log_file("logs/sample.log")
chunks = chunk_lines(lines, max_lines_per_chunk=2)

prioritized = prioritize_chunks(chunks)
print("Ordre avant tri:")
for c in chunks:
    print(f"  {c.start_line}-{c.end_line}: {c.level_counts}")

print("Ordre après tri (priorité aux plus graves):")
for c in prioritized:
    print(f"  {c.start_line}-{c.end_line}: {c.level_counts}")