"""Inicializa tabelas, migrações leves e view de produtividade."""
import logging
import time

from sqlalchemy import inspect, text

from app.database import Base, SessionLocal, engine
from app.models import TipoCaptura

logger = logging.getLogger(__name__)

VIEW_SQL = """
CREATE VIEW IF NOT EXISTS vw_produtividade AS
SELECT
    c.id,
    ao.nome_arquivo AS nome_da_origem,
    p.nome AS posto,
    COALESCE(c.tipo_posto, p.tipo_posto) AS tipo_posto,
    COALESCE(c.regiao, p.regiao) AS regiao,
    COALESCE(c.emissora_captura, p.emissora_captura) AS emissora_captura,
    c.indicadores,
    c.mes,
    c.mes_numero AS numero_mes,
    c.data_captura AS data,
    c.inicio,
    c.fim,
    c.tempo_raw AS tempo,
    c.tempo_minutos,
    o.nome AS operador,
    tc.codigo AS tipo_de_captura
FROM capturas c
LEFT JOIN arquivos_origem ao ON ao.id = c.arquivo_origem_id
LEFT JOIN postos p ON p.id = c.posto_id
LEFT JOIN operadores o ON o.id = c.operador_id
LEFT JOIN tipos_captura tc ON tc.id = c.tipo_captura_id
"""

MIGRATIONS = [
    "ALTER TABLE capturas ADD COLUMN regiao VARCHAR(100)",
    "ALTER TABLE capturas ADD COLUMN tipo_posto VARCHAR(100)",
    "ALTER TABLE capturas ADD COLUMN emissora_captura VARCHAR(100)",
    "ALTER TABLE capturas ADD COLUMN dedup_key VARCHAR(64)",
]


def migrate_dedup():
    from app.models import Captura, Operador, Posto, TipoCaptura
    from app.services.excel_importer import captura_dedup_key

    insp = inspect(engine)
    if "capturas" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("capturas")}
    if "dedup_key" not in cols:
        with engine.begin() as conn:
            conn.execute(text(MIGRATIONS[-1]))

    db = SessionLocal()
    try:
        while True:
            rows = (
                db.query(Captura, Posto, Operador, TipoCaptura)
                .outerjoin(Posto, Captura.posto_id == Posto.id)
                .outerjoin(Operador, Captura.operador_id == Operador.id)
                .outerjoin(TipoCaptura, Captura.tipo_captura_id == TipoCaptura.id)
                .filter(Captura.dedup_key.is_(None))
                .limit(5000)
                .all()
            )
            if not rows:
                break
            for cap, posto, operador, tipo in rows:
                cap.dedup_key = captura_dedup_key(
                    posto.nome if posto else None,
                    cap.tipo_posto or (posto.tipo_posto if posto else None),
                    cap.regiao or (posto.regiao if posto else None),
                    cap.data_captura,
                    cap.inicio,
                    cap.fim,
                    operador.nome if operador else None,
                    tipo.codigo if tipo else None,
                    cap.emissora_captura or (posto.emissora_captura if posto else None),
                    cap.indicadores,
                )
            db.commit()
    finally:
        db.close()

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM capturas
            WHERE dedup_key IS NOT NULL
              AND id NOT IN (
                SELECT MIN(id)
                FROM capturas
                WHERE dedup_key IS NOT NULL
                GROUP BY dedup_key
              )
        """))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_capturas_dedup_key ON capturas(dedup_key)"
        ))
        if "arquivos_origem" in insp.get_table_names():
            conn.execute(text("""
                DELETE FROM arquivos_origem
                WHERE hash_conteudo IS NOT NULL
                  AND id NOT IN (
                    SELECT MIN(id)
                    FROM arquivos_origem
                    WHERE hash_conteudo IS NOT NULL
                    GROUP BY hash_conteudo
                  )
            """))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_arquivos_origem_hash "
                "ON arquivos_origem(hash_conteudo)"
            ))


def migrate():
    insp = inspect(engine)
    if "capturas" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("capturas")}
    with engine.begin() as conn:
        for sql in MIGRATIONS:
            col = sql.split("ADD COLUMN ")[1].split()[0]
            if col not in cols:
                try:
                    conn.execute(text(sql))
                except Exception:
                    pass


def wait_for_database(max_attempts: int = 30, delay: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Conexão com banco estabelecida.")
            return
        except Exception as exc:
            logger.warning("Aguardando banco (%s/%s): %s", attempt, max_attempts, exc)
            if attempt == max_attempts:
                raise
            time.sleep(delay)


def init_db_core() -> None:
    Base.metadata.create_all(bind=engine)
    migrate()

    db = SessionLocal()
    try:
        if db.query(TipoCaptura).count() == 0:
            for codigo, desc in [
                ("CIN", "Carteira de Identidade Nacional"),
                ("CNH", "Carteira Nacional de Habilitacao"),
                ("RENAVAM", "Registro Nacional de Veiculos Automotores"),
            ]:
                db.add(TipoCaptura(codigo=codigo, descricao=desc))
            db.commit()
    finally:
        db.close()

    with engine.begin() as conn:
        conn.execute(text("DROP VIEW IF EXISTS vw_produtividade"))
        conn.execute(text(VIEW_SQL))


def init_db():
    if not engine.url.drivername.startswith("sqlite"):
        wait_for_database()
    init_db_core()
    migrate_dedup()


if __name__ == "__main__":
    init_db()
    print(f"Banco pronto: {engine.url}")
