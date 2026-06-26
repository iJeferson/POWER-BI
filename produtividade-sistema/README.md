# Sistema Produtividade Consórcio

Dashboard web de produtividade (CIN, CNH, RENAVAM) com **FastAPI**, **PostgreSQL** em produção e importação de planilhas Excel.

## Stack

- **Backend:** FastAPI + SQLAlchemy
- **Banco:** PostgreSQL (produção) / SQLite (desenvolvimento local)
- **Frontend:** HTML + CSS + Chart.js (em `backend/static/`)

## Desenvolvimento local

```powershell
cd produtividade-sistema
.\run-local.ps1
```

- Dashboard: http://127.0.0.1:8000
- API Docs: http://127.0.0.1:8000/docs

Usa SQLite (`produtividade.db`) e pasta `data/uploads` para importação.

## Deploy no Railway

### 1. Criar projeto

1. Acesse [railway.app](https://railway.app) e crie um novo projeto a partir deste repositório.
2. Adicione o plugin **PostgreSQL** ao projeto.
3. O Railway define `DATABASE_URL` automaticamente no serviço da API.

### 2. Variáveis de ambiente

No serviço da aplicação, configure:

| Variável | Valor |
|----------|--------|
| `DATABASE_URL` | Referência ao PostgreSQL (`${{Postgres.DATABASE_URL}}`) |
| `UPLOAD_DIR` | `/app/uploads` |
| `CORS_ORIGINS` | URL pública do app (ex.: `https://seu-app.up.railway.app`) |

`PORT` é definido automaticamente pelo Railway.

**Importante — persistência dos dados:** os dados importados ficam no **PostgreSQL**, não no container da aplicação. Cada novo deploy **não apaga** o banco, desde que `DATABASE_URL` aponte para o PostgreSQL do Railway. Se `DATABASE_URL` não estiver configurado, o app usa SQLite temporário e **perde tudo** a cada deploy.

Confira em `/api/health`:
- `"database": "postgresql"` e `"persistent": true` → dados mantidos entre deploys
- `"database": "sqlite"` → configure o PostgreSQL imediatamente

### 3. Build e deploy

O repositório inclui:

- `Dockerfile` — build da API + frontend estático
- `railway.toml` — health check em `/api/health`

Ao fazer push, o Railway faz build e sobe o serviço. Na primeira execução, as tabelas são criadas automaticamente (`app/bootstrap.py`).

### 4. Importar dados

Após o deploy, acesse a URL pública e use **Importar dados** no dashboard para enviar planilhas mensais (aba `Dados`, mesmo formato do Power BI).

## Estrutura

```
produtividade-sistema/
├── backend/
│   ├── app/           # API FastAPI
│   └── static/        # Dashboard web
├── data/uploads/      # Planilhas locais (dev)
├── scripts/           # Utilitários locais (init_db, reset_db)
├── Dockerfile
└── railway.toml
```

## Endpoints principais

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Health check |
| GET | `/api/dashboard/kpis` | KPIs do dashboard |
| POST | `/api/importacao/arquivo` | Upload de Excel |
| GET | `/docs` | Documentação OpenAPI |

## Colunas da planilha

`POSTO`, `TIPO DE POSTO`, `REGIÃO`, `EMISSORA CAPTURA`, `INDICADORES`, `MÊS`, `Nº`, `DATA`, `INICIO`, `FIM`, `TEMPO`, `OPERADOR`, `TIPO DE CAPTURA`

Importações duplicadas são ignoradas (hash do arquivo + chave por linha).
