import hmac
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator

from nfse_via_bot.config import settings
from nfse_via_bot.service import Result, fetch_invoice

PAGE = Path(__file__).with_name("page.html")

app = FastAPI(
    title="NFS-e Via",
    version="0.1.0",
    description=(
        "Consulta uma NFS-e Via pela chave de acesso e devolve a nota estruturada. O token do "
        "hCaptcha vem do serviço hate_captcha; quando a Via recusa o token pelo score, a consulta "
        "pede outro, até `MAX_ATTEMPTS` vezes."
    ),
)


class Lookup(BaseModel):
    access_key: str = Field(description="A chave de acesso da NFS-e Via, com 50 caracteres")

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


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "solver_configured": bool(settings.SOLVER_URL and settings.SOLVER_API_KEY),
    }


@app.post("/api/invoices", response_model=Result)
async def lookup(request: Lookup, x_access_token: Annotated[str | None, Header()] = None) -> Result:
    if settings.ACCESS_TOKEN and not hmac.compare_digest(
        x_access_token or "", settings.ACCESS_TOKEN
    ):
        raise HTTPException(status_code=401, detail="X-Access-Token ausente ou errado")
    if not (settings.SOLVER_URL and settings.SOLVER_API_KEY):
        raise HTTPException(status_code=503, detail="SOLVER_URL e SOLVER_API_KEY não configurados")
    return await fetch_invoice(request.access_key, settings)
