from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    TIMESTAMP,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Posto(Base):
    __tablename__ = "postos"

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    tipo_posto = Column(String(100))
    regiao = Column(String(100))
    emissora_captura = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    capturas = relationship("Captura", back_populates="posto")


class Operador(Base):
    __tablename__ = "operadores"

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False, unique=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    capturas = relationship("Captura", back_populates="operador")


class TipoCaptura(Base):
    __tablename__ = "tipos_captura"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(20), nullable=False, unique=True)
    descricao = Column(String(100))

    capturas = relationship("Captura", back_populates="tipo_captura")


class ArquivoOrigem(Base):
    __tablename__ = "arquivos_origem"

    id = Column(Integer, primary_key=True)
    nome_arquivo = Column(String(500), nullable=False)
    hash_conteudo = Column(String(64), unique=True)
    importado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    linhas_importadas = Column(Integer, default=0)


class Captura(Base):
    __tablename__ = "capturas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    arquivo_origem_id = Column(Integer, ForeignKey("arquivos_origem.id"))
    posto_id = Column(Integer, ForeignKey("postos.id"))
    operador_id = Column(Integer, ForeignKey("operadores.id"))
    tipo_captura_id = Column(Integer, ForeignKey("tipos_captura.id"))
    indicadores = Column(String(255))
    mes = Column(String(50))
    mes_numero = Column(Integer)
    data_captura = Column(Date, nullable=False)
    inicio = Column(String(50))
    fim = Column(String(50))
    tempo_raw = Column(String(50))
    tempo_minutos = Column(Numeric(10, 2))
    regiao = Column(String(100))
    tipo_posto = Column(String(100))
    emissora_captura = Column(String(100))
    dedup_key = Column(String(64), unique=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    posto = relationship("Posto", back_populates="capturas")
    operador = relationship("Operador", back_populates="capturas")
    tipo_captura = relationship("TipoCaptura", back_populates="capturas")
    arquivo_origem = relationship("ArquivoOrigem")
