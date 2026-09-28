from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    SOLVER_URL: str = ""
    SOLVER_API_KEY: str = ""
    # A Via recusa parte dos tokens pelo score; cada tentativa pede um token novo ao solver.
    MAX_ATTEMPTS: int = 3
    # Abaixo dos 300 s de uma função da Vercel, para sobrar tempo de responder.
    DEADLINE_SECONDS: float = 270.0
    POLL_SECONDS: float = 3.0
    # Com valor, a rota de consulta exige o cabeçalho X-Access-Token, para a URL pública não gastar
    # o solver de quem a achar.
    ACCESS_TOKEN: str = ""
    # Proxies HTTP para o solver resolver o hCaptcha, separados por vírgula, no formato
    # http://usuario:senha@host:porta. Cada tentativa usa o seguinte, e sai por outro IP.
    PROXY_URLS: str = ""

    def proxies(self) -> list[str]:
        return [item.strip() for item in self.PROXY_URLS.split(",") if item.strip()]


settings = Settings()
