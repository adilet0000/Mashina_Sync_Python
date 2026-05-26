from hashlib import sha256
from typing import Any


def stable_hash(value: Any) -> str:
    return sha256(str(value).encode("utf-8")).hexdigest()
