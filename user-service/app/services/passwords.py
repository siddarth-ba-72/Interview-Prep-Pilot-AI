import bcrypt
from starlette.concurrency import run_in_threadpool

BCRYPT_COST = 12
BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    # Spring's BCryptPasswordEncoder silently truncated at 72 bytes; newer bcrypt releases raise instead.
    # Truncating keeps every existing hash verifiable.
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password_sync(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(BCRYPT_COST)).decode("ascii")


def verify_password_sync(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except ValueError:  # malformed stored hash
        return False


# bcrypt at cost 12 is ~250 ms of CPU, so keep it off the event loop.
async def hash_password(password: str) -> str:
    return await run_in_threadpool(hash_password_sync, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await run_in_threadpool(verify_password_sync, password, password_hash)
