import json

import httpx

KEY = "1" * 36 + "P" + "2" * 13
REFUSAL = {
    "sucesso": False,
    "token": "",
    "notificacoes": [
        {
            "tipoNotificacao": 0,
            "codigo": "HCAPTCHA_INVALIDO",
            "mensagem": "Verificação hCaptcha inválida. Score de risco (0,79) acima do permitido.",
        }
    ],
}
NOT_FOUND = {
    "sucesso": False,
    "token": "",
    "notificacoes": [
        {"tipoNotificacao": 0, "codigo": "NAO_ENCONTRADA", "mensagem": "Nota não encontrada"}
    ],
}


def invoice_body() -> dict:
    return {
        "sucesso": True,
        "token": "t",
        "dados": {
            "nfseViaProc": {
                "NFSeVia": {
                    "infNFSeVia": {
                        "tpAmb": "1",
                        "cStat": "100",
                        "dhEmi": "2026-09-20T10:15:00-03:00",
                        "dhCompet": "2026-09-20",
                        "fornec": {
                            "CNPJ": "00000000000191",
                            "xNome": "CONCESSIONARIA X",
                            "cMun": "3100000",
                        },
                        "serv": {
                            "xLocOper": "Cidade A",
                            "xPracaEmi": "PRACA 1",
                            "kmPracaEmi": "642.850000",
                            "xLocEmi": "Cidade B",
                            "nNFSeVia": "1234567890123",
                            "serie": "001",
                            "cTribNac": "110101",
                            "cNBS": "123456789",
                            "explVia": {
                                "categVeic": "01",
                                "sentido": "SUL",
                                "placa": "ABC1D23",
                                "codAcessoPed": "ACESSO1234567890",
                                "modPassagem": "1",
                                "codContrato": "0001",
                            },
                        },
                        "valores": {
                            "vServ": "13.60",
                            "modPagamento": "1",
                            "vDescCondIncond": {"vDescIncond": "0.00", "vDescCond": "0.00"},
                            "trib": {
                                "issqn": {"vBC": "13.60", "pAliq": "4.68", "vISSQN": "0.64"},
                                "tribFed": {"piscofins": {"vPis": "0.00", "vCofins": "0.00"}},
                                "ibscbs": {
                                    "vTotNF": "13.10",
                                    "gIBS": {"vIBSTot": "0.02"},
                                    "gCBS": {"vCBS": "0.12"},
                                },
                            },
                        },
                    }
                },
                "protNFSeVia": {
                    "infProt": {
                        "chNFSeVia": KEY,
                        "dhRecbto": "2026-09-20T10:16:00-03:00",
                        "nProt": "999",
                    }
                },
            }
        },
        "notificacoes": [],
    }


class World:
    # Um solver e uma Via falsos, respondendo pela ordem das listas.
    def __init__(self, via: list[tuple[int, dict]], solver_errors: list[str | None] | None = None):
        self.via = list(via)
        self.solver_errors = list(solver_errors or [])
        self.consults: list[httpx.Request] = []
        self.tasks: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/createTask"):
            self.tasks.append(json.loads(request.content)["task"])
            error = self.solver_errors.pop(0) if self.solver_errors else None
            if error:
                return httpx.Response(200, json={"errorId": 1, "errorCode": error})
            return httpx.Response(200, json={"errorId": 0, "taskId": 7})
        if path.endswith("/getTaskResult"):
            solution = {"hCaptchaResponse": "P1_token", "userAgent": "UA/1.0"}
            return httpx.Response(200, json={"errorId": 0, "status": "ready", "solution": solution})
        self.consults.append(request)
        status, body = self.via.pop(0)
        return httpx.Response(status, content=json.dumps(body))

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
