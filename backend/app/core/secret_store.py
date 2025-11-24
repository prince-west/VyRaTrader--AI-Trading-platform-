# backend/app/core/secret_store.py
"""
Dev secret store. For prod replace with Vault/AWS Secrets Manager.
This implementation stores secrets in-memory and on-disk (encrypted not implemented).
"""
import os
from typing import Optional
from pathlib import Path
import json

_store_path = Path(".dev_secrets.json")


class SecretStore:
    def __init__(self):
        self._cache = {}
        if _store_path.exists():
            try:
                data = json.loads(_store_path.read_text(encoding="utf-8"))
                self._cache.update(data)
            except Exception:
                pass

    def get_secret(self, name: str) -> Optional[str]:
        # First check env
        val = os.environ.get(name)
        if val:
            return val
        return self._cache.get(name)

    def set_secret(self, name: str, value: str):
        self._cache[name] = value
        try:
            _store_path.write_text(json.dumps(self._cache), encoding="utf-8")
        except Exception:
            pass


# Simple helper
def get_secret(name: str) -> Optional[str]:
    s = SecretStore()
    return s.get_secret(name)
