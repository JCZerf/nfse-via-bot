import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from nfse_via_bot.config import Settings
from nfse_via_bot.invoice import Invoice, parse
from nfse_via_bot.solver import SolverError, solve
from nfse_via_bot.via import consult

# Uma resolução da Via leva de 30 a 60 s; sem esse tempo pela frente, outra tentativa não termina.
MIN_ROOM_SECONDS = 60


class Attempt(BaseModel):
    seconds: float
    outcome: Literal["accepted", "token_refused", "solver_error", "via_error"]
    score: float | None = Field(default=None, description="Score de risco que a Via informou")
    detail: str | None = None


class Result(BaseModel):
    status: Literal["found", "refused", "error"]
    access_key: str
    elapsed_seconds: float
    attempts: list[Attempt]
    invoice: Invoice | None = None
    messages: list[str] = Field(default_factory=list, description="Notificações da Via")


async def fetch_invoice(
    access_key: str, settings: Settings, client: httpx.AsyncClient | None = None
) -> Result:
    owned = client is None
    client = client or httpx.AsyncClient(timeout=30)
    started = time.monotonic()
    attempts: list[Attempt] = []
    try:
        while len(attempts) < settings.MAX_ATTEMPTS:
            left = settings.DEADLINE_SECONDS - (time.monotonic() - started)
            if attempts and left < MIN_ROOM_SECONDS:
                break
            began = time.monotonic()
            proxies = settings.proxies()
            proxy = proxies[len(attempts) % len(proxies)] if proxies else None
            try:
                token = await solve(
                    client,
                    settings.SOLVER_URL,
                    settings.SOLVER_API_KEY,
                    settings.POLL_SECONDS,
                    proxy,
                )
            except (SolverError, httpx.HTTPError) as error:
                attempts.append(
                    Attempt(seconds=_since(began), outcome="solver_error", detail=str(error))
                )
                continue
            answer = await consult(client, access_key, token)
            if answer.accepted:
                attempts.append(Attempt(seconds=_since(began), outcome="accepted"))
                return _result("found", access_key, started, attempts, parse(answer.body))
            texts = [n.get("mensagem", "") for n in answer.messages]
            if answer.token_refused:
                attempts.append(
                    Attempt(seconds=_since(began), outcome="token_refused", score=answer.score)
                )
                continue
            # Chave inexistente ou outro erro da Via: outro token não muda a resposta.
            attempts.append(
                Attempt(seconds=_since(began), outcome="via_error", detail="; ".join(texts))
            )
            return _result("error", access_key, started, attempts, None, texts)
        refused = any(a.outcome == "token_refused" for a in attempts)
        return _result("refused" if refused else "error", access_key, started, attempts, None)
    finally:
        if owned:
            await client.aclose()


def _since(moment: float) -> float:
    return round(time.monotonic() - moment, 1)


def _result(status, access_key, started, attempts, invoice, messages=None) -> Result:
    return Result(
        status=status,
        access_key=access_key,
        elapsed_seconds=_since(started),
        attempts=attempts,
        invoice=invoice,
        messages=messages or [],
    )
