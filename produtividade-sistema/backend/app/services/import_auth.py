import hashlib
import hmac
import time
from typing import Optional

from fastapi import Header, HTTPException

from app.config import settings

TOKEN_MAX_AGE = 8 * 3600


def import_protegido() -> bool:
    return bool(settings.import_password.strip())


def criar_token_importacao() -> str:
    ts = int(time.time())
    sig = hmac.new(
        settings.import_password.encode("utf-8"),
        str(ts).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{ts}.{sig}"


def validar_token_importacao(token: Optional[str]) -> bool:
    if not import_protegido():
        return True
    if not token:
        return False
    try:
        ts_str, sig = token.split(".", 1)
        ts = int(ts_str)
    except (ValueError, AttributeError):
        return False
    if time.time() - ts > TOKEN_MAX_AGE:
        return False
    esperado = hmac.new(
        settings.import_password.encode("utf-8"),
        ts_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(sig, esperado)


def verificar_senha_importacao(senha: str) -> bool:
    if not import_protegido():
        return True
    return hmac.compare_digest(senha, settings.import_password)


def exigir_importacao_autorizada(
    x_import_token: Optional[str] = Header(None, alias="X-Import-Token"),
) -> None:
    if not validar_token_importacao(x_import_token):
        raise HTTPException(401, "Senha de importação necessária ou sessão expirada")
