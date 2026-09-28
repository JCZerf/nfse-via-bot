import re
from dataclasses import dataclass

import httpx

from nfse_via_bot.solver import Token

API = "https://api.via.nfse.gov.br/consultapublica/consulta/{key}"
# A API confere de onde vem o pedido, como faz com a página oficial.
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "pt-BR",
    "origin": "https://via.nfse.gov.br",
    "referer": "https://via.nfse.gov.br/",
}
REFUSED_TOKEN = "HCAPTCHA_INVALIDO"
SCORE = re.compile(r"Score de risco \(([\d.,]+)\)")


@dataclass(frozen=True)
class Answer:
    status: int
    body: dict

    @property
    def accepted(self) -> bool:
        return self.status == 200 and bool(self.body.get("sucesso"))

    @property
    def token_refused(self) -> bool:
        return any(n.get("codigo") == REFUSED_TOKEN for n in self.messages)

    @property
    def messages(self) -> list[dict]:
        return self.body.get("notificacoes") or []

    @property
    def score(self) -> float | None:
        for note in self.messages:
            found = SCORE.search(note.get("mensagem") or "")
            if found:
                return float(found.group(1).replace(",", "."))
        return None


async def consult(client: httpx.AsyncClient, access_key: str, token: Token) -> Answer:
    headers = {**HEADERS, "x-hcaptcha-token": token.value, "user-agent": token.user_agent}
    response = await client.get(API.format(key=access_key), headers=headers)
    try:
        body = response.json()
    except ValueError:
        body = {"notificacoes": [{"codigo": "RESPOSTA_INVALIDA", "mensagem": response.text[:200]}]}
    return Answer(response.status_code, body if isinstance(body, dict) else {})
