from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CapturaOut, DashboardKPIs, RankingItem
from app.services.metrics import (
    calcular_kpis,
    capturas_por_data,
    capturas_por_dia_semana,
    capturas_por_emissora,
    capturas_por_hora,
    capturas_por_mes,
    capturas_por_regiao,
    capturas_por_tipo,
    capturas_por_tipo_posto,
    opcoes_filtros_cascata,
    buscar_autocomplete,
    ranking_operadores,
    ranking_postos,
    resumo_dados,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _f(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    regiao: Optional[str] = None,
    posto: Optional[str] = None,
    tipo_captura: Optional[str] = None,
    operador: Optional[str] = None,
    emissora: Optional[str] = None,
    tipo_posto: Optional[str] = None,
    mes: Optional[str] = None,
):
    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "regiao": regiao,
        "posto": posto,
        "tipo_captura": tipo_captura,
        "operador": operador,
        "emissora": emissora,
        "tipo_posto": tipo_posto,
        "mes": mes,
    }


@router.get("/kpis", response_model=DashboardKPIs)
def obter_kpis(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None, description="Capital,Interior,RMS"),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None, description="CIN,CNH,RENAVAM"),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None, description="CONSORCIO,DPT,PREFEITURA,SAEB"),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return calcular_kpis(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/resumo")
def obter_resumo(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return resumo_dados(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/ranking/postos", response_model=list[RankingItem])
def ranking_postos_endpoint(
    limit: int = Query(15, ge=1, le=100),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return ranking_postos(db, limit=limit, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/ranking/operadores", response_model=list[RankingItem])
def ranking_operadores_endpoint(
    limit: int = Query(15, ge=1, le=100),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return ranking_operadores(db, limit=limit, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-mes")
def por_mes(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_mes(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-tipo")
def por_tipo(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_tipo(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-regiao")
def por_regiao(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_regiao(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-emissora")
def por_emissora(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_emissora(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-data")
def por_data(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_data(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-hora")
def por_hora(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_hora(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-dia-semana")
def por_dia_semana(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_dia_semana(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/por-tipo-posto")
def por_tipo_posto(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return capturas_por_tipo_posto(db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes))


@router.get("/capturas", response_model=list[CapturaOut])
def listar_capturas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    sql = "SELECT * FROM vw_produtividade WHERE 1=1"
    params = {}
    if data_inicio:
        sql += " AND data >= :data_inicio"
        params["data_inicio"] = data_inicio
    if data_fim:
        sql += " AND data <= :data_fim"
        params["data_fim"] = data_fim
    if regiao:
        regs = [r.strip() for r in regiao.split(",")]
        sql += " AND regiao IN :regioes"
        params["regioes"] = tuple(regs)
    if posto:
        sql += " AND posto = :posto"
        params["posto"] = posto
    if tipo_captura:
        tipos = [t.strip().upper() for t in tipo_captura.split(",")]
        sql += " AND tipo_de_captura IN :tipos"
        params["tipos"] = tuple(tipos)
    if operador:
        sql += " AND operador = :operador"
        params["operador"] = operador
    if emissora:
        emis = [e.strip().upper() for e in emissora.split(",")]
        sql += " AND emissora_captura IN :emissoras"
        params["emissoras"] = tuple(emis)
    if tipo_posto:
        tps = [t.strip().upper() for t in tipo_posto.split(",")]
        sql += " AND tipo_posto IN :tipos_posto"
        params["tipos_posto"] = tuple(tps)
    if mes:
        meses = [m.strip() for m in mes.split(",")]
        sql += " AND mes IN :meses"
        params["meses"] = tuple(meses)
    sql += " ORDER BY data DESC, id DESC LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip

    rows = db.execute(text(sql), params).mappings().all()
    return [
        CapturaOut(
            id=r["id"],
            nome_da_origem=r["nome_da_origem"],
            posto=r["posto"],
            tipo_posto=r["tipo_posto"],
            regiao=r["regiao"],
            emissora_captura=r.get("emissora_captura"),
            indicadores=r["indicadores"],
            mes=r["mes"],
            data=r["data"],
            inicio=r["inicio"],
            fim=r["fim"],
            tempo=r["tempo"],
            tempo_minutos=r["tempo_minutos"],
            operador=r["operador"],
            tipo_de_captura=r["tipo_de_captura"],
        )
        for r in rows
    ]


@router.get("/capturas/total")
def total_capturas(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    sql = "SELECT COUNT(*) FROM vw_produtividade WHERE 1=1"
    params = {}
    if data_inicio:
        sql += " AND data >= :data_inicio"
        params["data_inicio"] = data_inicio
    if data_fim:
        sql += " AND data <= :data_fim"
        params["data_fim"] = data_fim
    if regiao:
        sql += " AND regiao IN :regioes"
        params["regioes"] = tuple(r.strip() for r in regiao.split(","))
    if posto:
        sql += " AND posto = :posto"
        params["posto"] = posto
    if tipo_captura:
        sql += " AND tipo_de_captura IN :tipos"
        params["tipos"] = tuple(t.strip().upper() for t in tipo_captura.split(","))
    if operador:
        sql += " AND operador = :operador"
        params["operador"] = operador
    if emissora:
        sql += " AND emissora_captura IN :emissoras"
        params["emissoras"] = tuple(e.strip().upper() for e in emissora.split(","))
    if tipo_posto:
        sql += " AND tipo_posto IN :tipos_posto"
        params["tipos_posto"] = tuple(t.strip().upper() for t in tipo_posto.split(","))
    if mes:
        sql += " AND mes IN :meses"
        params["meses"] = tuple(m.strip() for m in mes.split(","))
    return {"total": db.execute(text(sql), params).scalar()}


@router.get("/filtros")
def opcoes_filtros(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    base = opcoes_filtros_cascata(
        db, **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes)
    )
    base["formato_importacao"] = {
        "arquivo": "Planilha mensal (.xlsx)",
        "aba": "Dados",
        "colunas": [
            "POSTO", "TIPO DE POSTO", "REGIÃO", "EMISSORA CAPTURA", "INDICADORES",
            "MÊS", "Nº", "DATA", "INICIO", "FIM", "TEMPO", "OPERADOR", "TIPO DE CAPTURA",
        ],
    }
    return base


@router.get("/filtros/buscar")
def buscar_filtros(
    tipo: str = Query(..., pattern="^(operador|posto)$"),
    q: str = Query("", min_length=1, max_length=120),
    limit: int = Query(20, ge=1, le=50),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    regiao: Optional[str] = Query(None),
    posto: Optional[str] = Query(None),
    tipo_captura: Optional[str] = Query(None),
    operador: Optional[str] = Query(None),
    emissora: Optional[str] = Query(None),
    tipo_posto: Optional[str] = Query(None),
    mes: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return buscar_autocomplete(
        db,
        tipo,
        q,
        limit=limit,
        **_f(data_inicio, data_fim, regiao, posto, tipo_captura, operador, emissora, tipo_posto, mes),
    )
