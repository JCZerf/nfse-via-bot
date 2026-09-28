import hmac
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator

from nfse_via_bot.config import settings
from nfse_via_bot.docs import DESCRIPTION, LOOKUP_EXAMPLES, LOOKUP_RESPONSES
from nfse_via_bot.service import Result, fetch_invoice

PAGE = Path(__file__).with_name("page.html")

app = FastAPI(
    title="NFS-e Via",
    version="0.1.0",
    description=DESCRIPTION,
    openapi_tags=[
        {"name": "consulta", "description": "Consulta da nota pela chave de acesso"},
        {"name": "saude", "description": "Estado do serviço"},
    ],
)


class Health(BaseModel):
    status: str = Field(description="`ok` quando o serviço responde")
    solver_configured: bool = Field(
        description="Se `SOLVER_URL` e `SOLVER_API_KEY` estão definidos"
    )


class Lookup(BaseModel):
    access_key: str = Field(
        description="A chave de acesso da NFS-e Via: 50 letras ou números; espaços são ignorados"
    )

    @field_validator("access_key")
    @classmethod
    def check_key(cls, value: str) -> str:
        key = "".join(value.split()).upper()
        if len(key) != 50 or not key.isalnum():
            raise ValueError("a chave de acesso tem 50 letras ou números")
        return key


@app.get("/", include_in_schema=False)
@app.get("/api/docs", include_in_schema=False)
async def home() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/consulta", response_class=HTMLResponse, include_in_schema=False)
async def page() -> str:
    return PAGE.read_text()


@app.get(
    "/health",
    response_model=Health,
    tags=["saude"],
    summary="Estado do serviço",
    description="Responde na hora, sem chamar o solver nem a Via.",
)
async def health() -> Health:
    return Health(
        status="ok", solver_configured=bool(settings.SOLVER_URL and settings.SOLVER_API_KEY)
    )


@app.post(
    "/api/invoices",
    response_model=Result,
    tags=["consulta"],
    summary="Consulta uma NFS-e Via pela chave de acesso",
    description=(
        "Resolve o hCaptcha pelo solver, consulta a Via e devolve a nota estruturada. Leva de 30 a "
        "270 s, conforme quantas tentativas forem precisas.\n\n"
        "- `found`: a nota veio em `invoice`.\n"
        "- `refused`: a Via recusou todos os tokens pelo score de risco; `attempts` traz o "
        "score de cada um. Tente de novo mais tarde.\n"
        "- `error`: a Via respondeu com outro erro (em `messages`), ou o solver falhou em todas as "
        "tentativas (em `attempts[].detail`)."
    ),
    responses=LOOKUP_RESPONSES,
)
async def lookup(
    request: Annotated[Lookup, Body(openapi_examples=LOOKUP_EXAMPLES)],
    x_access_token: Annotated[
        str | None, Header(description="Obrigatório quando `ACCESS_TOKEN` está configurado")
    ] = None,
) -> Result:
    if settings.ACCESS_TOKEN and not hmac.compare_digest(
        x_access_token or "", settings.ACCESS_TOKEN
    ):
        raise HTTPException(status_code=401, detail="X-Access-Token ausente ou errado")
    if not (settings.SOLVER_URL and settings.SOLVER_API_KEY):
        raise HTTPException(status_code=503, detail="SOLVER_URL e SOLVER_API_KEY não configurados")
    return await fetch_invoice(request.access_key, settings)
