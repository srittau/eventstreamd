import datetime
from datetime import timedelta
from typing import Any, Mapping


async def check_auth(
    route: str, headers: Mapping[str, str], **kwargs: Any
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
