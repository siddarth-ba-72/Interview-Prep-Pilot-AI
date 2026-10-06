import bcrypt

from app.services.passwords import hash_password, hash_password_sync, verify_password, verify_password_sync


def test_hash_uses_cost_12_and_verifies():
    hashed = hash_password_sync("correct horse battery")
    assert hashed.startswith("$2b$12$")
    assert verify_password_sync("correct horse battery", hashed)
    assert not verify_password_sync("wrong", hashed)


def test_verifies_spring_style_2a_hash():
    spring_hash = bcrypt.hashpw(b"spring-password", bcrypt.gensalt(12, prefix=b"2a")).decode()
    assert spring_hash.startswith("$2a$12$")
    assert verify_password_sync("spring-password", spring_hash)


def test_spring_verifies_python_hash_prefix_is_compatible():
    # Spring's BCryptPasswordEncoder accepts $2a$, $2b$ and $2y$.
    assert hash_password_sync("x" * 8)[:4] in {"$2a$", "$2b$", "$2y$"}


def test_passwords_truncate_at_72_bytes_like_spring():
    long = "a" * 72
    hashed = hash_password_sync(long + "extra-ignored-suffix")
    assert verify_password_sync(long, hashed)  # bytes past 72 never mattered
    assert verify_password_sync(long + "different-suffix", hashed)


def test_truncation_counts_bytes_not_characters():
    password = "é" * 50  # 100 bytes
    hashed = hash_password_sync(password)
    assert verify_password_sync("é" * 36, hashed)  # first 72 bytes only


def test_malformed_stored_hash_is_a_mismatch_not_an_error():
    assert verify_password_sync("anything", "not-a-bcrypt-hash") is False


async def test_async_wrappers():
    hashed = await hash_password("async-password")
    assert await verify_password("async-password", hashed)
    assert not await verify_password("nope", hashed)
