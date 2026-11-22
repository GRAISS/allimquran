import json
from pathlib import Path

COPY = json.loads((Path(__file__).parent / "public/trial-copy.json").read_text())
