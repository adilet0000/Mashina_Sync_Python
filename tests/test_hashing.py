from app.utils.hashing import stable_hash


def test_stable_hash_is_deterministic() -> None:
    assert stable_hash("provider-image-url") == stable_hash("provider-image-url")
    assert stable_hash("provider-image-url") != stable_hash("other-url")
