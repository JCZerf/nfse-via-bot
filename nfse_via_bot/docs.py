DESCRIPTION = """
Consulta uma **NFS-e Via**, a nota fiscal de serviço do pedágio, pela chave de acesso, e devolve a
nota estruturada.

**Como funciona**

1. Pede um token do hCaptcha ao serviço **hate_captcha**, que resolve o desafio da página da Via
   num navegador de verdade (de 30 a 60 s).
2. Consulta a API pública da Via com o token e o mesmo `User-Agent` que o gerou.
3. Se a Via recusar o token pelo score de risco, pede outro, até `MAX_ATTEMPTS` vezes (3 por
   padrão), dentro de `DEADLINE_SECONDS` (270 s). Uma tentativa nova só começa com pelo menos 60 s
   de prazo pela frente.

**Autenticação:** com `ACCESS_TOKEN` configurado, a consulta exige o cabeçalho `X-Access-Token`.

A página `/consulta` faz a mesma consulta com um formulário.
"""

KEY = "00000000000000000000000000000000000000000000000001"

LOOKUP_EXAMPLES = {
    "chave": {"summary": "Uma chave de acesso", "value": {"access_key": KEY}},
    "com_espacos": {
        "summary": "Chave colada com espaços",
        "description": "Espaços e letras minúsculas são aceitos e normalizados.",
        "value": {"access_key": "00000 00000 00000 00000 00000 00000 00000 00000 00000 00001"},
    },
}

INVOICE = {
    "number": "1234567890123",
    "series": "001",
    "issued_at": "2026-09-20T10:15:00-03:00",
    "competence": "2026-09-20",
    "status_code": "100",
    "national_tax_code": "110101",
    "nbs": "123456789",
    "issuer": {
        "cnpj": "00000000000191",
        "name": "CONCESSIONARIA EXEMPLO",
        "municipality_code": "3100000",
    },
    "trip": {
        "plate": "ABC1D23",
        "vehicle_category": "01",
        "direction": "SUL",
        "toll_plaza": "PRACA EXEMPLO",
        "toll_plaza_km": 642.85,
        "operation_place": "Cidade A",
        "issue_place": "Cidade B",
        "access_code": "ACESSO1234567890",
        "passage_mode": "1",
        "contract_code": "0001",
    },
    "amounts": {
        "service": 13.6,
        "unconditional_discount": 0.0,
        "conditional_discount": 0.0,
        "total": 13.1,
        "payment_mode": "1",
        "taxes": {
            "issqn_base": 13.6,
            "issqn_rate": 4.68,
            "issqn": 0.64,
            "pis": 0.0,
            "cofins": 0.0,
            "ibs": 0.02,
            "cbs": 0.12,
        },
    },
    "protocol": {"number": "999", "received_at": "2026-09-20T10:16:00-03:00", "access_key": KEY},
}

RESULT_EXAMPLES = {
    "encontrada": {
        "summary": "Nota encontrada na segunda tentativa",
        "value": {
            "status": "found",
            "access_key": KEY,
            "elapsed_seconds": 86.3,
            "attempts": [
                {"seconds": 44.9, "outcome": "token_refused", "score": 0.79, "detail": None},
                {"seconds": 41.4, "outcome": "accepted", "score": None, "detail": None},
            ],
            "invoice": INVOICE,
            "messages": [],
        },
    },
    "recusada": {
        "summary": "A Via recusou todos os tokens pelo score",
        "value": {
            "status": "refused",
            "access_key": KEY,
            "elapsed_seconds": 128.6,
            "attempts": [
                {"seconds": 45.5, "outcome": "token_refused", "score": 0.79, "detail": None},
                {"seconds": 41.2, "outcome": "token_refused", "score": 0.79, "detail": None},
                {"seconds": 41.8, "outcome": "token_refused", "score": 0.79, "detail": None},
            ],
            "invoice": None,
            "messages": [],
        },
    },
    "erro_via": {
        "summary": "A Via respondeu com outro erro, que outro token não muda",
        "value": {
            "status": "error",
            "access_key": KEY,
            "elapsed_seconds": 43.0,
            "attempts": [
                {
                    "seconds": 43.0,
                    "outcome": "via_error",
                    "score": None,
                    "detail": "Nota não encontrada",
                }
            ],
            "invoice": None,
            "messages": ["Nota não encontrada"],
        },
    },
}


def _detail(summary: str, detail) -> dict:
    return {"summary": summary, "value": {"detail": detail}}


LOOKUP_RESPONSES = {
    200: {
        "description": "A consulta terminou; `status` diz se a nota veio",
        "content": {"application/json": {"examples": RESULT_EXAMPLES}},
    },
    401: {
        "description": "`ACCESS_TOKEN` configurado e `X-Access-Token` ausente ou errado",
        "content": {
            "application/json": {
                "examples": {"token": _detail("Sem o token", "X-Access-Token ausente ou errado")}
            }
        },
    },
    422: {"description": "Chave de acesso fora do formato (50 letras ou números)"},
    503: {
        "description": "O bot está sem `SOLVER_URL` ou `SOLVER_API_KEY`",
        "content": {
            "application/json": {
                "examples": {
                    "solver": _detail(
                        "Solver não configurado", "SOLVER_URL e SOLVER_API_KEY não configurados"
                    )
                }
            }
        },
    },
}
