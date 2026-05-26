from dataclasses import dataclass

from app.config.settings import PROVIDER_KEYS


@dataclass(frozen=True)
class ProviderConfig:
    key: str
    display_name: str
    legacy_service: str | None = None
    enabled: bool = True


PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "autohub": ProviderConfig("autohub", "Autohub", "AutohubSync"),
    "autoland": ProviderConfig("autoland", "Autoland", "AutolandSync"),
    "shredder": ProviderConfig("shredder", "Shredder", "ShredderSync"),
    "okayamaomsk": ProviderConfig("okayamaomsk", "OkayamaOmsk", "OkayamaOmskSync"),
    "banzaimotors": ProviderConfig("banzaimotors", "Banzai Motors", "BanzaiMotorsSync"),
    "bavaria": ProviderConfig("bavaria", "Bavaria", "BavariaSync"),
    "shinabar": ProviderConfig("shinabar", "Shinabar", "ShinabarSync"),
    "avtoinstall": ProviderConfig("avtoinstall", "AvtoInstall", "AvtoinstallSync"),
    "allmotors": ProviderConfig("allmotors", "All Motors", "AllMotorsSync"),
    "autoshina": ProviderConfig("autoshina", "Autoshina", "AutoshinaSync"),
    "detalkg": ProviderConfig("detalkg", "Detal KG", "DetalKgSync"),
    "toyota": ProviderConfig("toyota", "Toyota", "ToyotaSync"),
    "toyota_tradein": ProviderConfig("toyota_tradein", "Toyota Trade-In", "ToyotaTradeinSync"),
    "lexus": ProviderConfig("lexus", "Lexus", "LexusSync"),
    "kia": ProviderConfig("kia", "KIA", "KiaSync"),
}


def list_provider_configs() -> tuple[ProviderConfig, ...]:
    return tuple(PROVIDER_CONFIGS[key] for key in PROVIDER_KEYS)


def get_provider_config(provider: str) -> ProviderConfig:
    key = provider.lower().replace("-", "_")
    try:
        return PROVIDER_CONFIGS[key]
    except KeyError as exc:
        supported = ", ".join(PROVIDER_KEYS)
        message = f"unsupported provider {provider!r}; supported providers: {supported}"
        raise ValueError(message) from exc
