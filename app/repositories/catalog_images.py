from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.config import Settings
from app.dto import CatalogImagePayload
from app.repositories.catalog_listings import CatalogListingsRepository


class CatalogImagesRepository:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.listings_repository = CatalogListingsRepository(session, settings)

    def insert_images(
        self,
        *,
        listing_id: int,
        images: Iterable[CatalogImagePayload],
    ) -> int:
        inserted = 0
        for image in images:
            self.listings_repository.insert_image(listing_id, image)
            inserted += 1
        return inserted
