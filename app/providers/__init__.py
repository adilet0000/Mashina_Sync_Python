from app.providers.allmotors import ALLMOTORS_SITE_URL, AllmotorsProviderAdapter
from app.providers.autohub import AUTOHUB_FEED_URL, AutohubProviderAdapter
from app.providers.autoland import AUTOLAND_FEED_URL, AutolandProviderAdapter
from app.providers.autoshina import AUTOSHINA_SITE_URL, AutoshinaProviderAdapter
from app.providers.avtoinstall import AVTOINSTALL_FEED_URL, AvtoinstallProviderAdapter
from app.providers.banzaimotors import (
    BANZAIMOTORS_PARTS_FEED_URL,
    BANZAIMOTORS_WHEELS_FEED_URL,
    BanzaimotorsProviderAdapter,
)
from app.providers.base import (
    NotImplementedProviderAdapter,
    ProviderAdapter,
    ProviderAdapterError,
    ProviderNotImplementedError,
)
from app.providers.bavaria import (
    BAVARIA_PARTS_FEED_URL,
    BAVARIA_WHEELS_FEED_URL,
    BavariaProviderAdapter,
)
from app.providers.detalkg import DETALKG_PARTS_FEED_URL, DETALKG_SITE_URL, DetalKgProviderAdapter
from app.providers.kia import KIA_FEED_URL, KiaProviderAdapter
from app.providers.lexus import LEXUS_FEED_URL, LexusProviderAdapter
from app.providers.okayamaomsk import OKAYAMAOMSK_FEED_URL, OkayamaomskProviderAdapter
from app.providers.shinabar import SHINABAR_FEED_URL, ShinabarProviderAdapter
from app.providers.shredder import SHREDDER_FEED_URL, ShredderProviderAdapter
from app.providers.toyota import TOYOTA_FEED_URL, ToyotaProviderAdapter
from app.providers.toyota_tradein import (
    TOYOTA_TRADEIN_FEED_URL,
    ToyotaTradeinProviderAdapter,
)

__all__ = [
    "ALLMOTORS_SITE_URL",
    "AUTOHUB_FEED_URL",
    "AUTOLAND_FEED_URL",
    "AUTOSHINA_SITE_URL",
    "AVTOINSTALL_FEED_URL",
    "BANZAIMOTORS_PARTS_FEED_URL",
    "BANZAIMOTORS_WHEELS_FEED_URL",
    "BAVARIA_PARTS_FEED_URL",
    "BAVARIA_WHEELS_FEED_URL",
    "DETALKG_PARTS_FEED_URL",
    "DETALKG_SITE_URL",
    "KIA_FEED_URL",
    "LEXUS_FEED_URL",
    "OKAYAMAOMSK_FEED_URL",
    "SHINABAR_FEED_URL",
    "SHREDDER_FEED_URL",
    "TOYOTA_FEED_URL",
    "TOYOTA_TRADEIN_FEED_URL",
    "AllmotorsProviderAdapter",
    "AutohubProviderAdapter",
    "AutolandProviderAdapter",
    "AutoshinaProviderAdapter",
    "AvtoinstallProviderAdapter",
    "BanzaimotorsProviderAdapter",
    "BavariaProviderAdapter",
    "DetalKgProviderAdapter",
    "KiaProviderAdapter",
    "LexusProviderAdapter",
    "NotImplementedProviderAdapter",
    "OkayamaomskProviderAdapter",
    "ProviderAdapter",
    "ProviderAdapterError",
    "ProviderNotImplementedError",
    "ShinabarProviderAdapter",
    "ShredderProviderAdapter",
    "ToyotaProviderAdapter",
    "ToyotaTradeinProviderAdapter",
]
