from app.dto import CatalogImagePayload
from app.utils.hashing import stable_hash


def normalize_external_url(value: object) -> str:
    url = str(value).strip()
    if not url:
        raise ValueError("image external_url is required")
    return url


def parse_legacy_image(
    value: object,
    *,
    fallback_priority: int,
    user_id: int,
    status: int,
) -> CatalogImagePayload:
    raw = str(value).strip()
    priority = fallback_priority
    url = raw

    if "|" in raw:
        prefix, candidate_url = raw.split("|", 1)
        if prefix.strip().isdigit():
            priority = int(prefix.strip())
            url = candidate_url

    external_url = normalize_external_url(url)
    return CatalogImagePayload(
        external_url=external_url,
        priority=priority,
        hash=stable_hash(external_url),
        status=status,
        is_blurred=False,
        user_id=user_id,
    )


def map_images(
    images: tuple[object, ...],
    *,
    user_id: int,
    status: int,
) -> tuple[CatalogImagePayload, ...]:
    payloads: list[CatalogImagePayload] = []
    seen_hashes: set[str] = set()
    for index, image in enumerate(images):
        payload = parse_legacy_image(
            image,
            fallback_priority=index,
            user_id=user_id,
            status=status,
        )
        if payload.hash in seen_hashes:
            continue
        seen_hashes.add(payload.hash)
        payloads.append(payload)
    return tuple(payloads)
