import hashlib
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import ArquivoOrigem, Captura, Operador, Posto, TipoCaptura

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}

COLUNAS_ESPERADAS = [
    "POSTO", "TIPO DE POSTO", "REGIÃO", "EMISSORA CAPTURA", "INDICADORES",
    "MÊS", "Nº", "DATA", "INICIO", "FIM", "TEMPO", "OPERADOR", "TIPO DE CAPTURA",
]

BATCH_SIZE = 3000


def _norm_col(name: str) -> str:
    return (
        str(name)
        .strip()
        .upper()
        .replace("Ã", "A")
        .replace("Õ", "O")
        .replace("Ç", "C")
    )


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for col in df.columns:
        key = _norm_col(col)
        aliases = {
            "REGIAO": "REGIÃO",
            "MES": "MÊS",
            "N": "Nº",
            "NO": "Nº",
        }
        mapping[col] = aliases.get(key, col.strip() if col.strip() in COLUNAS_ESPERADAS else col)
    df = df.rename(columns=mapping)
    return df


def normalize_text(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def normalize_regiao(value) -> Optional[str]:
    text = normalize_text(value)
    if not text:
        return None
    key = text.upper().strip()
    if key == "CAPITAL":
        return "Capital"
    if key.startswith("INTERIOR"):
        return "Interior"
    if key == "RMS":
        return "RMS"
    return text.strip().title()


def normalize_emissora(value) -> Optional[str]:
    text = normalize_text(value)
    return text.upper() if text else None


def normalize_tipo_posto(value) -> Optional[str]:
    text = normalize_text(value)
    return text.upper() if text else None


def parse_mes_numero(mes: Optional[str], numero=None) -> Optional[int]:
    if numero is not None and str(numero).strip().replace(".0", "").isdigit():
        return int(str(numero).strip().replace(".0", ""))
    if mes:
        key = mes.strip().lower()
        if key.isdigit():
            return int(key)
        return MESES_PT.get(key)
    return None


def parse_tempo_minutos(tempo, tipo_captura: Optional[str] = None) -> Optional[Decimal]:
    if tempo is None or (isinstance(tempo, float) and pd.isna(tempo)):
        return None

    if hasattr(tempo, "hour"):
        if tipo_captura == "CNH":
            minutes = tempo.hour + tempo.minute / 60 + tempo.second / 3600
            return Decimal(str(round(minutes, 2)))
        return Decimal(str(round(tempo.hour * 60 + tempo.minute + tempo.second / 60, 2)))

    if isinstance(tempo, pd.Timedelta):
        return Decimal(str(tempo.total_seconds() / 60))

    raw = str(tempo).strip()
    if not raw:
        return None

    match = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", raw)
    if match:
        h, m, s = map(int, match.groups())
        return Decimal(str(h * 60 + m + s / 60))

    try:
        val = float(raw.replace(",", "."))
    except ValueError:
        return None

    if tipo_captura in (None, "CIN", "RENAVAM") and val > 60:
        return Decimal(str(round(val / 60, 2)))

    if tipo_captura == "CIN" and 15 <= val <= 30:
        return Decimal(str(val))

    return Decimal(str(round(val / 60 if val > 120 else val, 2)))


def captura_dedup_key(
    posto_nome: Optional[str],
    tipo_posto: Optional[str],
    regiao: Optional[str],
    data_captura: date,
    inicio: Optional[str],
    fim: Optional[str],
    operador_nome: Optional[str],
    tipo_codigo: Optional[str],
    emissora: Optional[str],
    indicadores: Optional[str],
) -> str:
    payload = "|".join([
        (posto_nome or "").strip().upper(),
        (tipo_posto or "").strip().upper(),
        (regiao or "").strip(),
        data_captura.isoformat(),
        (inicio or "").strip(),
        (fim or "").strip(),
        (operador_nome or "").strip().upper(),
        (tipo_codigo or "").strip().upper(),
        (emissora or "").strip().upper(),
        (indicadores or "").strip(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ler_planilha_dados(file_path: Path) -> pd.DataFrame:
    xl = pd.ExcelFile(file_path)
    sheet = "Dados" if "Dados" in xl.sheet_names else xl.sheet_names[0]
    df = pd.read_excel(file_path, sheet_name=sheet)
    df = _normalize_columns(df)
    return df


def _get_or_create_posto(db: Session, row: dict) -> Optional[Posto]:
    nome = normalize_text(row.get("POSTO"))
    if not nome:
        return None
    tipo = normalize_tipo_posto(row.get("TIPO DE POSTO"))
    regiao = normalize_regiao(row.get("REGIÃO") or row.get("REGIAO"))
    emissora = normalize_emissora(row.get("EMISSORA CAPTURA"))

    posto = (
        db.query(Posto)
        .filter(Posto.nome == nome, Posto.tipo_posto == tipo, Posto.regiao == regiao)
        .first()
    )
    if not posto:
        posto = Posto(nome=nome, tipo_posto=tipo, regiao=regiao, emissora_captura=emissora)
        db.add(posto)
        db.flush()
    return posto


def _get_or_create_operador(db: Session, cache: dict, nome_raw) -> Optional[Operador]:
    nome = normalize_text(nome_raw)
    if not nome:
        return None
    if nome in cache:
        return cache[nome]
    operador = db.query(Operador).filter(Operador.nome == nome).first()
    if not operador:
        operador = Operador(nome=nome)
        db.add(operador)
        db.flush()
    cache[nome] = operador
    return operador


def _get_tipo_captura(db: Session, cache: dict, codigo_raw) -> Optional[TipoCaptura]:
    if not codigo_raw:
        return None
    codigo = str(codigo_raw).strip().upper()
    if codigo in cache:
        return cache[codigo]
    tipo = db.query(TipoCaptura).filter(TipoCaptura.codigo == codigo).first()
    cache[codigo] = tipo
    return tipo


def _flush_capturas(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = sqlite_insert(Captura.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["dedup_key"])
    result = db.execute(stmt)
    return int(result.rowcount or 0)


def _fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def importar_arquivo_excel(db: Session, file_path: Path, nome_origem: Optional[str] = None) -> dict:
    content = file_path.read_bytes()
    file_hash = hashlib.sha256(content).hexdigest()
    nome_arquivo = nome_origem or file_path.name

    existente = (
        db.query(ArquivoOrigem)
        .filter(ArquivoOrigem.hash_conteudo == file_hash)
        .first()
    )
    if existente:
        return {
            "arquivo": nome_arquivo,
            "linhas_importadas": 0,
            "linhas_ignoradas": 0,
            "duplicado": True,
            "mensagem": (
                f"Arquivo já importado (mesmo conteúdo). "
                f"Original: {existente.nome_arquivo}."
            ),
        }

    df = ler_planilha_dados(file_path)
    if df.empty:
        return {
            "arquivo": nome_arquivo,
            "linhas_importadas": 0,
            "linhas_ignoradas": 0,
            "duplicado": False,
            "mensagem": "Planilha vazia.",
        }

    arquivo = ArquivoOrigem(nome_arquivo=nome_arquivo, hash_conteudo=file_hash, linhas_importadas=0)
    db.add(arquivo)
    db.flush()

    operador_cache: dict = {}
    tipo_cache: dict = {}
    posto_cache: dict = {}
    linhas_lidas = 0
    linhas_importadas = 0
    batch: list[dict] = []

    for _, row in df.iterrows():
        data_raw = row.get("DATA")
        if pd.isna(data_raw):
            continue
        try:
            data_captura = pd.to_datetime(data_raw, dayfirst=True).date()
        except (ValueError, TypeError):
            continue

        tipo_codigo = normalize_text(row.get("TIPO DE CAPTURA"))
        if tipo_codigo:
            tipo_codigo = tipo_codigo.upper()

        regiao = normalize_regiao(row.get("REGIÃO") or row.get("REGIAO"))
        tipo_posto = normalize_tipo_posto(row.get("TIPO DE POSTO"))
        emissora = normalize_emissora(row.get("EMISSORA CAPTURA"))
        mes = normalize_text(row.get("MÊS") or row.get("MES"))
        mes_num = parse_mes_numero(mes, row.get("Nº") or row.get("N"))
        indicadores = normalize_text(row.get("INDICADORES"))
        inicio = normalize_text(row.get("INICIO"))
        fim = normalize_text(row.get("FIM"))

        posto_nome = normalize_text(row.get("POSTO"))
        operador_nome = normalize_text(row.get("OPERADOR"))
        cache_key = (posto_nome, tipo_posto, regiao)
        if cache_key not in posto_cache:
            posto_cache[cache_key] = _get_or_create_posto(db, row.to_dict())
        posto = posto_cache[cache_key]

        operador = _get_or_create_operador(db, operador_cache, row.get("OPERADOR"))
        tipo = _get_tipo_captura(db, tipo_cache, tipo_codigo)
        tempo_raw = row.get("TEMPO")
        tempo_str = normalize_text(tempo_raw) if not hasattr(tempo_raw, "hour") else str(tempo_raw)

        dedup_key = captura_dedup_key(
            posto_nome,
            tipo_posto,
            regiao,
            data_captura,
            inicio,
            fim,
            operador_nome,
            tipo_codigo,
            emissora,
            indicadores,
        )

        batch.append({
            "arquivo_origem_id": arquivo.id,
            "posto_id": posto.id if posto else None,
            "operador_id": operador.id if operador else None,
            "tipo_captura_id": tipo.id if tipo else None,
            "indicadores": indicadores,
            "mes": mes,
            "mes_numero": mes_num,
            "data_captura": data_captura,
            "inicio": inicio,
            "fim": fim,
            "tempo_raw": tempo_str,
            "tempo_minutos": parse_tempo_minutos(tempo_raw, tipo_codigo),
            "regiao": regiao,
            "tipo_posto": tipo_posto,
            "emissora_captura": emissora,
            "dedup_key": dedup_key,
        })
        linhas_lidas += 1

        if len(batch) >= BATCH_SIZE:
            linhas_importadas += _flush_capturas(db, batch)
            batch.clear()

    if batch:
        linhas_importadas += _flush_capturas(db, batch)

    linhas_ignoradas = linhas_lidas - linhas_importadas
    arquivo.linhas_importadas = linhas_importadas
    db.commit()

    if linhas_importadas == 0 and linhas_ignoradas > 0:
        mensagem = (
            f"Nenhum registro novo: {_fmt_num(linhas_ignoradas)} linha(s) já existiam no banco."
        )
    elif linhas_ignoradas > 0:
        mensagem = (
            f"Importação concluída: {_fmt_num(linhas_importadas)} novos, "
            f"{_fmt_num(linhas_ignoradas)} ignorados (duplicados)."
        )
    else:
        mensagem = f"Importação concluída: {_fmt_num(linhas_importadas)} registros."

    return {
        "arquivo": nome_arquivo,
        "linhas_importadas": linhas_importadas,
        "linhas_ignoradas": linhas_ignoradas,
        "duplicado": False,
        "mensagem": mensagem,
    }


def importar_pasta(db: Session, pasta: Path) -> list[dict]:
    resultados = []
    for pattern in ("*.xlsx", "*.xls"):
        for file_path in sorted(pasta.glob(pattern)):
            if file_path.name.startswith("~$"):
                continue
            resultados.append(importar_arquivo_excel(db, file_path))
    return resultados
