import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import ImportacaoResultado
from app.services.excel_importer import importar_arquivo_excel, importar_pasta

router = APIRouter(prefix="/api/importacao", tags=["importacao"])


@router.post("/arquivo", response_model=ImportacaoResultado)
async def importar_arquivo(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
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
def importar_da_pasta_local(db: Session = Depends(get_db)):
    """Importa todos os Excel da pasta /app/uploads (útil em produção com volume montado)."""
    pasta = Path(settings.upload_dir)
    if not pasta.exists():
        raise HTTPException(404, "Pasta de uploads não encontrada")
    try:
        return [ImportacaoResultado(**r) for r in importar_pasta(db, pasta)]
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro na importação em lote: {e}") from e
