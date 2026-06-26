from datetime import date
from typing import Optional

from sqlalchemy import Integer, cast, func, or_
from sqlalchemy.orm import Query, Session

from app.models import ArquivoOrigem, Captura, Operador, Posto, TipoCaptura
from app.schemas import DashboardKPIs, RankingItem


def _split_list(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _regiao_variants(regiao: str) -> list[str]:
    key = regiao.strip().upper()
    if key == "CAPITAL":
        return ["Capital"]
    if key.startswith("INTERIOR"):
        return ["Interior", "INTERIOR"]
    if key == "RMS":
        return ["RMS"]
    return [regiao.strip()]


DIAS_SEMANA = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb"}


def _hora_inicio_expr():
    return cast(func.substr(Captura.inicio, 1, func.instr(Captura.inicio, ":") - 1), Integer)


def _dia_semana_expr():
    return cast(func.strftime("%w", Captura.data_captura), Integer)


def _apply_filtros(
    q: Query,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    regiao: Optional[str] = None,
    posto: Optional[str] = None,
    tipo_captura: Optional[str] = None,
    operador: Optional[str] = None,
    emissora: Optional[str] = None,
    tipo_posto: Optional[str] = None,
    mes: Optional[str] = None,
    *,
    joined_posto: bool = False,
    joined_operador: bool = False,
    joined_tipo: bool = False,
) -> Query:
    if data_inicio:
        q = q.filter(Captura.data_captura >= data_inicio)
    if data_fim:
        q = q.filter(Captura.data_captura <= data_fim)

    meses = _split_list(mes)
    if meses:
        q = q.filter(Captura.mes.in_(meses))

    regioes = _split_list(regiao)
    if regioes:
        expanded: list[str] = []
        for r in regioes:
            expanded.extend(_regiao_variants(r))
        q = q.filter(or_(Captura.regiao.in_(expanded), func.trim(Captura.regiao).in_(expanded)))

    emissoras = _split_list(emissora)
    if emissoras:
        q = q.filter(Captura.emissora_captura.in_([e.upper() for e in emissoras]))

    tipos_posto = _split_list(tipo_posto)
    if tipos_posto:
        q = q.filter(Captura.tipo_posto.in_([t.upper() for t in tipos_posto]))

    if posto:
        if not joined_posto:
            q = q.join(Posto, Captura.posto_id == Posto.id)
            joined_posto = True
        q = q.filter(Posto.nome == posto)

    tipos = _split_list(tipo_captura)
    if tipos:
        if not joined_tipo:
            q = q.join(TipoCaptura, Captura.tipo_captura_id == TipoCaptura.id)
            joined_tipo = True
        q = q.filter(TipoCaptura.codigo.in_([t.upper() for t in tipos]))
    elif tipo_captura:
        if not joined_tipo:
            q = q.join(TipoCaptura, Captura.tipo_captura_id == TipoCaptura.id)
        q = q.filter(TipoCaptura.codigo == tipo_captura.upper())

    if operador:
        if not joined_operador:
            q = q.join(Operador, Captura.operador_id == Operador.id)
        q = q.filter(Operador.nome == operador)

    return q


def _filtros_sem(chaves: list[str], **filtros) -> dict:
    f = {**filtros}
    for chave in chaves:
        f.pop(chave, None)
    return f


def ranking_postos(
    db: Session,
    limit: int = 10,
    *,
    excluir_filtro: Optional[str] = None,
    **filtros,
) -> list[RankingItem]:
    f = _filtros_sem([excluir_filtro], **filtros) if excluir_filtro else filtros
    q = (
        db.query(Posto.nome, func.count(Captura.id).label("total"))
        .select_from(Captura)
        .join(Posto, Captura.posto_id == Posto.id)
        .filter(Captura.posto_id.isnot(None))
        .group_by(Posto.id, Posto.nome)
        .order_by(func.count(Captura.id).desc())
    )
    q = _apply_filtros(q, **f, joined_posto=True)
    return [RankingItem(nome=r[0], total=r[1]) for r in q.limit(limit).all()]


def ranking_operadores(
    db: Session,
    limit: int = 10,
    *,
    excluir_filtro: Optional[str] = None,
    **filtros,
) -> list[RankingItem]:
    f = _filtros_sem([excluir_filtro], **filtros) if excluir_filtro else filtros
    q = (
        db.query(Operador.nome, func.count(Captura.id).label("total"))
        .select_from(Captura)
        .join(Operador, Captura.operador_id == Operador.id)
        .filter(Captura.operador_id.isnot(None))
        .group_by(Operador.id, Operador.nome)
        .order_by(func.count(Captura.id).desc())
    )
    q = _apply_filtros(q, **f, joined_operador=True)
    return [RankingItem(nome=r[0], total=r[1]) for r in q.limit(limit).all()]


def calcular_kpis(db: Session, **filtros) -> DashboardKPIs:
    q = _apply_filtros(db.query(Captura), **filtros)
    total = q.count()

    def count_tipo(codigo: str) -> int:
        f = {**filtros, "tipo_captura": codigo}
        return _apply_filtros(db.query(Captura), **f).count()

    total_cin = count_tipo("CIN")
    total_cnh = count_tipo("CNH")
    total_renavam = count_tipo("RENAVAM")

    colab_q = _apply_filtros(
        db.query(func.count(func.distinct(Captura.operador_id))).filter(Captura.operador_id.isnot(None)),
        **filtros,
    )
    colab_count = colab_q.scalar() or 0

    postos_q = _apply_filtros(
        db.query(func.count(func.distinct(Captura.posto_id))).filter(Captura.posto_id.isnot(None)),
        **filtros,
    )
    postos_total = postos_q.scalar() or 0

    media_operador = round(total / colab_count, 2) if colab_count else 0.0

    def tempo_medio_tipo(codigo: str) -> Optional[float]:
        sub = (
            db.query(func.avg(Captura.tempo_minutos))
            .join(TipoCaptura)
            .filter(TipoCaptura.codigo == codigo, Captura.tempo_minutos.isnot(None))
        )
        if codigo in ("CIN", "CNH"):
            sub = sub.filter(Captura.tempo_minutos >= 0.25, Captura.tempo_minutos <= 30)
        f = {**filtros}
        f.pop("tipo_captura", None)
        sub = _apply_filtros(sub, **f, joined_tipo=True)
        val = sub.scalar()
        return round(float(val), 2) if val else None

    tempo_geral = _apply_filtros(
        db.query(func.avg(Captura.tempo_minutos)).filter(Captura.tempo_minutos.isnot(None)),
        **filtros,
    )
    tempo_medio = tempo_geral.scalar()

    # Com filtro de posto/operador ativo, o destaque reflete o recorte atual.
    posto_rank = ranking_postos(
        db,
        limit=1,
        excluir_filtro=None if filtros.get("posto") else "posto",
        **filtros,
    )
    oper_rank = ranking_operadores(
        db,
        limit=1,
        excluir_filtro=None if filtros.get("operador") else "operador",
        **filtros,
    )
    temporal = _metricas_temporais(db, total, **filtros)

    return DashboardKPIs(
        total_atendimentos=total,
        total_cin=total_cin,
        total_cnh=total_cnh,
        total_renavam=total_renavam,
        pct_cin=round(total_cin / total * 100, 2) if total else 0,
        pct_cnh=round(total_cnh / total * 100, 2) if total else 0,
        pct_renavam=round(total_renavam / total * 100, 2) if total else 0,
        colaboradores_ativos=colab_count,
        total_postos=postos_total,
        media_operador=media_operador,
        tempo_medio_geral=round(float(tempo_medio), 2) if tempo_medio else None,
        tempo_medio_cin=tempo_medio_tipo("CIN"),
        tempo_medio_cnh=tempo_medio_tipo("CNH"),
        tempo_medio_renavam=tempo_medio_tipo("RENAVAM"),
        posto_mais_produtivo=posto_rank[0].nome if posto_rank else None,
        operador_mais_produtivo=oper_rank[0].nome if oper_rank else None,
        qtd_posto_destaque=posto_rank[0].total if posto_rank else 0,
        qtd_operador_destaque=oper_rank[0].total if oper_rank else 0,
        hora_pico=temporal["hora_pico"],
        hora_pico_qtd=temporal["hora_pico_qtd"],
        dia_semana_pico=temporal["dia_semana_pico"],
        dia_semana_pico_qtd=temporal["dia_semana_pico_qtd"],
        pct_fim_semana=temporal["pct_fim_semana"],
        media_diaria=temporal["media_diaria"],
    )


def capturas_por_mes(db: Session, **filtros):
    q = (
        db.query(Captura.mes, Captura.mes_numero, func.count(Captura.id))
        .group_by(Captura.mes, Captura.mes_numero)
        .order_by(Captura.mes_numero)
    )
    q = _apply_filtros(q, **filtros)
    return [{"mes": r[0], "mes_numero": r[1], "total": r[2]} for r in q.all()]


def capturas_por_tipo(db: Session, **filtros):
    q = (
        db.query(TipoCaptura.codigo, func.count(Captura.id))
        .join(Captura, Captura.tipo_captura_id == TipoCaptura.id)
        .group_by(TipoCaptura.codigo)
        .order_by(func.count(Captura.id).desc())
    )
    q = _apply_filtros(q, **filtros, joined_tipo=True)
    return [{"tipo": r[0], "total": r[1]} for r in q.all()]


def capturas_por_regiao(db: Session, **filtros):
    q = (
        db.query(Captura.regiao, func.count(Captura.id))
        .filter(Captura.regiao.isnot(None))
        .group_by(Captura.regiao)
        .order_by(func.count(Captura.id).desc())
    )
    q = _apply_filtros(q, **filtros)
    return [{"regiao": r[0], "total": r[1]} for r in q.all()]


def capturas_por_emissora(db: Session, **filtros):
    q = (
        db.query(Captura.emissora_captura, func.count(Captura.id))
        .filter(Captura.emissora_captura.isnot(None))
        .group_by(Captura.emissora_captura)
        .order_by(func.count(Captura.id).desc())
    )
    q = _apply_filtros(q, **filtros)
    return [{"emissora": r[0], "total": r[1]} for r in q.all()]


def capturas_por_data(db: Session, **filtros):
    q = (
        db.query(Captura.data_captura, func.count(Captura.id))
        .group_by(Captura.data_captura)
        .order_by(Captura.data_captura)
    )
    q = _apply_filtros(q, **filtros)
    return [{"data": r[0].isoformat(), "total": r[1]} for r in q.all()]


def capturas_por_hora(db: Session, **filtros):
    hora = _hora_inicio_expr()
    q = (
        db.query(hora.label("hora"), func.count(Captura.id))
        .filter(Captura.inicio.isnot(None), Captura.inicio != "", func.instr(Captura.inicio, ":") > 0)
        .group_by(hora)
    )
    q = _apply_filtros(q, **filtros)
    rows = {int(r[0]): r[1] for r in q.all() if r[0] is not None}
    return [{"hora": h, "total": rows.get(h, 0)} for h in range(24)]


def capturas_por_dia_semana(db: Session, **filtros):
    dow = _dia_semana_expr()
    q = (
        db.query(dow.label("dow"), func.count(Captura.id))
        .group_by(dow)
        .order_by(dow)
    )
    q = _apply_filtros(q, **filtros)
    rows = {int(r[0]): r[1] for r in q.all() if r[0] is not None}
    ordem = [1, 2, 3, 4, 5, 6, 0]
    return [{"dia": DIAS_SEMANA[d], "dia_numero": d, "total": rows.get(d, 0)} for d in ordem]


def capturas_por_tipo_posto(db: Session, **filtros):
    q = (
        db.query(Captura.tipo_posto, func.count(Captura.id))
        .filter(Captura.tipo_posto.isnot(None))
        .group_by(Captura.tipo_posto)
        .order_by(func.count(Captura.id).desc())
    )
    q = _apply_filtros(q, **filtros)
    return [{"tipo_posto": r[0], "total": r[1]} for r in q.all()]


def _metricas_temporais(db: Session, total: int, **filtros) -> dict:
    horas = capturas_por_hora(db, **filtros)
    dias = capturas_por_dia_semana(db, **filtros)
    pico_h = max(horas, key=lambda x: x["total"], default={"hora": None, "total": 0})
    pico_d = max(dias, key=lambda x: x["total"], default={"dia": None, "total": 0})

    dow = _dia_semana_expr()
    weekend = (
        _apply_filtros(db.query(func.count(Captura.id)), **filtros)
        .filter(dow.in_([0, 6]))
        .scalar()
        or 0
    )
    dias_unicos = (
        _apply_filtros(db.query(func.count(func.distinct(Captura.data_captura))), **filtros).scalar() or 0
    )

    return {
        "hora_pico": pico_h["hora"],
        "hora_pico_qtd": pico_h["total"],
        "dia_semana_pico": pico_d["dia"],
        "dia_semana_pico_qtd": pico_d["total"],
        "pct_fim_semana": round(weekend / total * 100, 2) if total else 0.0,
        "media_diaria": round(total / dias_unicos, 1) if dias_unicos else None,
    }


def resumo_dados(db: Session, **filtros) -> dict:
    q = _apply_filtros(db.query(Captura), **filtros)
    total_capturas = q.count()
    data_min = _apply_filtros(db.query(func.min(Captura.data_captura)), **filtros).scalar()
    data_max = _apply_filtros(db.query(func.max(Captura.data_captura)), **filtros).scalar()
    total_arquivos = db.query(func.count(ArquivoOrigem.id)).scalar() or 0
    ultima_importacao = db.query(func.max(ArquivoOrigem.importado_em)).scalar()
    anos_rows = (
        _apply_filtros(
            db.query(func.strftime("%Y", Captura.data_captura))
            .filter(Captura.data_captura.isnot(None))
            .distinct(),
            **filtros,
        )
        .all()
    )
    anos = sorted({int(r[0]) for r in anos_rows if r[0]})
    return {
        "total_capturas": total_capturas,
        "total_arquivos": total_arquivos,
        "data_minima": data_min.isoformat() if data_min else None,
        "data_maxima": data_max.isoformat() if data_max else None,
        "ultima_importacao": ultima_importacao.isoformat() if ultima_importacao else None,
        "anos": anos,
    }


def opcoes_filtros_cascata(db: Session, **filtros) -> dict:
    def capturas_q(*exclude: str):
        f = {**filtros}
        for key in exclude:
            f.pop(key, None)
        return _apply_filtros(db.query(Captura), **f)

    regioes = sorted({
        r[0] for r in capturas_q("regiao").with_entities(Captura.regiao).distinct().all() if r[0]
    })
    emissoras = sorted({
        r[0] for r in capturas_q("emissora").with_entities(Captura.emissora_captura).distinct().all() if r[0]
    })
    tipos_posto = sorted({
        r[0] for r in capturas_q("tipo_posto").with_entities(Captura.tipo_posto).distinct().all() if r[0]
    })
    meses = (
        capturas_q("mes")
        .with_entities(Captura.mes, Captura.mes_numero)
        .filter(Captura.mes.isnot(None))
        .distinct()
        .order_by(Captura.mes_numero)
        .all()
    )

    f_posto = {**filtros}
    f_posto.pop("posto", None)
    postos_q = (
        db.query(Posto.nome)
        .join(Captura, Captura.posto_id == Posto.id)
        .distinct()
        .order_by(Posto.nome)
    )
    postos = [r[0] for r in _apply_filtros(postos_q, **f_posto, joined_posto=True).all()]

    f_op = {**filtros}
    f_op.pop("operador", None)
    operadores_q = (
        db.query(Operador.nome)
        .join(Captura, Captura.operador_id == Operador.id)
        .distinct()
        .order_by(Operador.nome)
    )
    operadores = [
        r[0]
        for r in _apply_filtros(operadores_q, **f_op, joined_operador=True).limit(500).all()
    ]

    f_tipo = {**filtros}
    f_tipo.pop("tipo_captura", None)
    tipos_q = (
        db.query(TipoCaptura.codigo)
        .join(Captura, Captura.tipo_captura_id == TipoCaptura.id)
        .distinct()
        .order_by(TipoCaptura.codigo)
    )
    tipos = [r[0] for r in _apply_filtros(tipos_q, **f_tipo, joined_tipo=True).all()]

    return {
        "regioes": regioes,
        "emissoras": emissoras,
        "tipos_posto": tipos_posto,
        "meses": [{"nome": m[0], "numero": m[1]} for m in meses],
        "postos": postos,
        "operadores": operadores,
        "tipos_captura": tipos,
    }
