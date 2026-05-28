def listing_identity_key(category_id: int, external_id: str) -> str:
    """Stable sync key inside one catalog user scope."""
    return f"{int(category_id)}:{external_id}"


def listing_identity_label(category_id: int, external_id: str) -> str:
    return f"category_id={int(category_id)} external_id={external_id}"
