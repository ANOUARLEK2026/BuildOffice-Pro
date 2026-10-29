import json
from pathlib import Path

# Knowledge is generated when this distribution is built. Re-run the build script used by the project to refresh it.
print(Path(__file__).with_name("program_knowledge.json"))
print(json.loads(Path(__file__).with_name("program_knowledge.json").read_text(encoding="utf8"))["title"])
