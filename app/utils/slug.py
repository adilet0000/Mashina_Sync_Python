import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def stable_slug(title: str, external_id: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    base = _SLUG_RE.sub("-", ascii_title).strip("-")
    external = _SLUG_RE.sub("-", external_id.lower()).strip("-")
    if base and external:
        return f"{base}-{external}"[:240]
    return (external or "listing")[:240]
