import asyncio
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import httpx

VIA_PAGE = "https://via.nfse.gov.br/consultapublica/"


@dataclass(frozen=True)
class Token:
    value: str
    user_agent: str


class SolverError(Exception):
    def __init__(self, code: str, description: str = ""):
        super().__init__(f"{code}: {description}" if description else code)
        self.code = code
        self.description = description


def task_for(proxy: str | None) -> dict:
    if not proxy:
        return {"type": "HCaptchaTaskProxyless", "websiteURL": VIA_PAGE}
    parts = urlparse(proxy)
    task = {
        "type": "HCaptchaTask",
        "websiteURL": VIA_PAGE,
        "proxyType": parts.scheme or "http",
        "proxyAddress": parts.hostname,
        "proxyPort": parts.port,
    }
    if parts.username:
        task["proxyLogin"] = unquote(parts.username)
        task["proxyPassword"] = unquote(parts.password or "")
    return task


async def solve(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    poll_seconds: float,
    proxy: str | None = None,
) -> Token:
    tasks = f"{base_url.rstrip('/')}/api/v1/hcaptcha"
    task = task_for(proxy)
    created = (
        await client.post(f"{tasks}/createTask", json={"clientKey": api_key, "task": task})
    ).json()
    if created.get("errorId"):
        raise SolverError(
            created.get("errorCode", "ERROR_UNKNOWN"), created.get("errorDescription", "")
        )
    while True:
        await asyncio.sleep(poll_seconds)
        result = (
            await client.post(
                f"{tasks}/getTaskResult", json={"clientKey": api_key, "taskId": created["taskId"]}
            )
        ).json()
        if result.get("errorId"):
            raise SolverError(
                result.get("errorCode", "ERROR_UNKNOWN"), result.get("errorDescription", "")
            )
        if result.get("status") == "ready":
            solution = result["solution"]
            return Token(solution["hCaptchaResponse"], solution["userAgent"])
