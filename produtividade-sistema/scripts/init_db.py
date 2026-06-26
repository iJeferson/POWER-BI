"""Inicializa o banco e cria a view de produtividade."""

import sys

from pathlib import Path



BACKEND = Path(__file__).resolve().parent.parent / "backend"

sys.path.insert(0, str(BACKEND))



from app.bootstrap import init_db



if __name__ == "__main__":

    init_db()

    print("Banco pronto.")

