import datetime
from http import HTTPStatus
from typing import Any, Mapping, Tuple, Optional

from evtstrd.exc import PluginError
from evtstrd.http import HTTPError
from evtstrd.plugins import load_plugin


async def check_auth(
    path: str, headers: Mapping[str, str], **kwargs: Any
) -> Tuple[Optional[datetime.datetime], Any]:
    auth = load_plugin("auth", "check_auth")
    if auth is None:
        return None, None
    response = await auth(path, headers, **kwargs)
    status = response["status"]
    if status == "ok":
        expire: Optional[datetime.datetime] = response.get("expire")
        return expire, response.get("data")
    elif status == "unauthorized":
        authenticate = response.get("authenticate")
        if authenticate is None:
            raise PluginError(
                "auth", "'authenticate' field missing from response"
            )
        raise HTTPError(
            HTTPStatus.UNAUTHORIZED,
            "Unauthorized",
            headers=[("WWW-Authenticate", authenticate)],
        )
    elif status == "forbidden":
        raise HTTPError(HTTPStatus.FORBIDDEN, "Forbidden")
    else:
        raise PluginError("auth", f"unsupported response status '{status}'")
