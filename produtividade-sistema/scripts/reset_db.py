"""Zera o banco SQLite local e reinicia estrutura vazia."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BACKEND = SCRIPTS.parent / "backend"
ROOT = SCRIPTS.parent
sys.path.insert(0, str(BACKEND))

from app.bootstrap import init_db


def main():
    db_file = ROOT / "produtividade.db"
    for suffix in ("", "-wal", "-shm"):
        f = Path(str(db_file) + suffix)
        if f.exists():
            f.unlink()
            print(f"Removido: {f.name}")

    init_db()
    print("Banco zerado e pronto para importacao.")


if __name__ == "__main__":
    main()
