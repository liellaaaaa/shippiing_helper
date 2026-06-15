import json
from pathlib import Path
from typing import Optional


class CustomsNameService:
    _instance: "CustomsNameService | None" = None

    def __init__(self, json_path: str):
        self._cache: dict[str, dict] = {}
        self._load(json_path)

    def _load(self, json_path: str):
        p = Path(json_path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            records = json.load(f)
        for r in records:
            key = r.get("internal_code", "").strip()
            if key:
                self._cache[key] = r

    def lookup(self, internal_code: str) -> Optional[dict]:
        return self._cache.get(internal_code.strip())

    @classmethod
    def get_instance(cls, json_path: str) -> "CustomsNameService":
        if cls._instance is None:
            cls._instance = cls(json_path)
        return cls._instance