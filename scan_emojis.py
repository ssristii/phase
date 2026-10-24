import pathlib
import re

pattern = re.compile(r"[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF\u2600-\u27BF\uFE0F\u200D]")
for p in pathlib.Path(".").rglob("*"):
    if any(part in {"node_modules", ".git"} for part in p.parts):
        continue
    if p.is_file() and p.suffix in {".py", ".md", ".tsx", ".sql", ".html", ".css", ".js", ".json", ".txt"}:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        hits = [(i + 1, line) for i, line in enumerate(text.splitlines()) if pattern.search(line)]
        if hits:
            print("EMOJI", p)
            for i, line in hits:
                print(" ", i, line)
print("done")

