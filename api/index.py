import sys
from pathlib import Path

# A Vercel roda a função a partir de api/; o pacote fica na raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nfse_via_bot.main import app  # noqa: E402

__all__ = ["app"]
