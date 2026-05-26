from dataclasses import dataclass


@dataclass(frozen=True)
class HttpClientConfig:
    timeout: float
    user_agent: str = "mashinakg-python-sync/0.1"


class ProviderHttpClient:
    def __init__(self, config: HttpClientConfig) -> None:
        self.config = config

    def get_text(self, url: str) -> str:
        import httpx

        response = httpx.get(
            url,
            headers={"User-Agent": self.config.user_agent},
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        return response.text

    def get_bytes(self, url: str) -> bytes:
        import httpx

        response = httpx.get(
            url,
            headers={"User-Agent": self.config.user_agent},
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        return response.content
