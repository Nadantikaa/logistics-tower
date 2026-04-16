import json
from pathlib import Path
from typing import Any

from app.config import DATA_DIR


class JsonDataStore:
    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir

    def read_json(self, filename: str) -> list[dict[str, Any]]:
        path = self.data_dir / filename
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


store = JsonDataStore()

