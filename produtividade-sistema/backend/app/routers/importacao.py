import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import (
    ImportAuthRequest,
    ImportAuthResponse,
    ImportConfigResponse,
    ImportacaoResultado,
    ImportSessaoResponse,
)
from app.services.excel_importer import importar_arquivo_excel, importar_pasta
from app.services.import_auth import (
    TOKEN_MAX_AGE,
    criar_token_importacao,
    exigir_importacao_autorizada,
    import_protegido,
    importacao_disponivel,
    senha_configurada,
    validar_token_importacao,
    verificar_senha_importacao,
)

router = APIRouter(prefix="/api/importacao", tags=["importacao"])


@router.get("/config", response_model=ImportConfigResponse)
def config_importacao():
    bloqueada = not importacao_disponivel()
    return ImportConfigResponse(
        requer_senha=import_protegido() and senha_configurada(),
        disponivel=not bloqueada,
        motivo_bloqueio=(
            "IMPORT_PASSWORD não está configurada no servidor. "
            "Defina a variável de ambiente no Railway."
        )
        if bloqueada
        else None,
    )


@router.get("/sessao", response_model=ImportSessaoResponse)
def sessao_importacao(x_import_token: str | None = Header(None, alias="X-Import-Token")):
    return ImportSessaoResponse(
        autenticado=validar_token_importacao(x_import_token),
        requer_senha=import_protegido(),
    )


@router.post("/auth", response_model=ImportAuthResponse)
def autenticar_importacao(body: ImportAuthRequest):
    if not importacao_disponivel():
        raise HTTPException(503, "IMPORT_PASSWORD não configurada no servidor")
    if not import_protegido() or not senha_configurada():
        return ImportAuthResponse(token="", expira_em_segundos=TOKEN_MAX_AGE)
    if not verificar_senha_importacao(body.senha):
        raise HTTPException(401, "Senha incorreta")
    return ImportAuthResponse(token=criar_token_importacao(), expira_em_segundos=TOKEN_MAX_AGE)


@router.post("/arquivo", response_model=ImportacaoResultado)
async def importar_arquivo(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(exigir_importacao_autorizada),
):
    if not arquivo.filename or not arquivo.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Envie um arquivo Excel (.xlsx ou .xls)")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / arquivo.filename

    with dest.open("wb") as f:
        shutil.copyfileobj(arquivo.file, f)

    try:
        resultado = importar_arquivo_excel(db, dest, arquivo.filename)
        return ImportacaoResultado(**resultado)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro na importação: {e}") from e


@router.post("/pasta", response_model=list[ImportacaoResultado])
def importar_da_pasta_local(
    db: Session = Depends(get_db),
    _: None = Depends(exigir_importacao_autorizada),
):
    """Importa todos os Excel da pasta /app/uploads (útil em produção com volume montado)."""
    pasta = Path(settings.upload_dir)
    if not pasta.exists():
        raise HTTPException(404, "Pasta de uploads não encontrada")
    try:
        return [ImportacaoResultado(**r) for r in importar_pasta(db, pasta)]
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro na importação em lote: {e}") from e
