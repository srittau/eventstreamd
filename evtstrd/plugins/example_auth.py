import datetime
from datetime import timedelta
from typing import Any, Protocol


class _SupportsGet(Protocol):
    def get(self, key: str) -> str | None: ...


async def check_auth(
    route: str, headers: _SupportsGet, **kwargs: object
) -> Any:
    authorization = headers.get("authorization")

    # No access to stats
    if route == "stats":
        return {"status": "forbidden"}

    if authorization is None:
        return {"status": "unauthorized", "authenticate": "Bearer"}
    if authorization.lower() == "bearer sikrit":
        return {
            "status": "ok",
            "expire": datetime.datetime.utcnow() + timedelta(minutes=1),
        }
    else:
        return {"status": "forbidden"}
