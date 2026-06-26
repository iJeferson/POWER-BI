from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class CapturaOut(BaseModel):
    id: int
    nome_da_origem: Optional[str] = None
    posto: Optional[str] = None
    tipo_posto: Optional[str] = None
    regiao: Optional[str] = None
    emissora_captura: Optional[str] = None
    indicadores: Optional[str] = None
    mes: Optional[str] = None
    data: date
    inicio: Optional[str] = None
    fim: Optional[str] = None
    tempo: Optional[str] = None
    tempo_minutos: Optional[Decimal] = None
    operador: Optional[str] = None
    tipo_de_captura: Optional[str] = None

    class Config:
        from_attributes = True


class ImportacaoResultado(BaseModel):
    arquivo: str
    linhas_importadas: int
    linhas_ignoradas: int = 0
    duplicado: bool = False
    mensagem: str


class DashboardKPIs(BaseModel):
    total_atendimentos: int
    total_cin: int
    total_cnh: int
    total_renavam: int
    pct_cin: float
    pct_cnh: float
    pct_renavam: float
    colaboradores_ativos: int
    total_postos: int
    media_operador: float
    tempo_medio_geral: Optional[float] = None
    tempo_medio_cin: Optional[float] = None
    tempo_medio_cnh: Optional[float] = None
    tempo_medio_renavam: Optional[float] = None
    posto_mais_produtivo: Optional[str] = None
    operador_mais_produtivo: Optional[str] = None
    qtd_posto_destaque: int = 0
    qtd_operador_destaque: int = 0
    hora_pico: Optional[int] = None
    hora_pico_qtd: int = 0
    dia_semana_pico: Optional[str] = None
    dia_semana_pico_qtd: int = 0
    pct_fim_semana: float = 0.0
    media_diaria: Optional[float] = None


class RankingItem(BaseModel):
    nome: str
    total: int


class FiltrosDashboard(BaseModel):
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    regiao: Optional[str] = None
    posto: Optional[str] = None
    tipo_captura: Optional[str] = None
    operador: Optional[str] = None
