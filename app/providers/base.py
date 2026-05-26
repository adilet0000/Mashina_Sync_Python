from abc import ABC, abstractmethod
from collections.abc import Iterable

from app.dto import LegacyAd


class ProviderAdapterError(RuntimeError):
    pass


class ProviderNotImplementedError(ProviderAdapterError):
    pass


class ProviderAdapter(ABC):
    provider_key: str

    @abstractmethod
    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        raise ProviderNotImplementedError(f"provider {self.provider_key!r} is not implemented")


class NotImplementedProviderAdapter(ProviderAdapter):
    def __init__(self, provider_key: str) -> None:
        self.provider_key = provider_key

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        raise ProviderNotImplementedError(f"provider {self.provider_key!r} is not implemented")
