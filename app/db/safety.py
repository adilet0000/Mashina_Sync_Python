from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class DatabaseTargetInfo:
    host: str | None
    port: int | None
    database: str | None
    username: str | None

    @property
    def is_local(self) -> bool:
        return self.host in {None, "", "localhost", "127.0.0.1", "::1"}

    def as_safe_string(self) -> str:
        host = self.host or "unknown"
        port = f":{self.port}" if self.port else ""
        database = self.database or "unknown"
        username = self.username or "unknown"
        return f"host={host}{port} database={database} username={username}"


def describe_database_url(url: str | None) -> DatabaseTargetInfo:
    if not url:
        return DatabaseTargetInfo(host=None, port=None, database=None, username=None)
    parsed = urlparse(url)
    database = parsed.path.lstrip("/") or None
    return DatabaseTargetInfo(
        host=parsed.hostname,
        port=parsed.port,
        database=database,
        username=parsed.username,
    )
