# Agente de IA para Agendamento de Exames de Vista (MVP)

Este backend expõe um endpoint de chat que usa um modelo da OpenAI para conduzir a conversa e, quando tiver as informações necessárias, **cria um evento no Google Agenda** com regras de **prioridade** (alto/médio/baixo) para lembretes.

## O que este MVP faz

- Conversa em PT-BR para **agendar exame de vista**
- Usa **OpenAI** (function calling) para extrair/confirmar dados
- Cria eventos no **Google Calendar**
- Aplica **prioridade** → configura lembretes (overrides) no evento
- Persiste histórico e agendamentos em **SQLite** (`backend/app.db`)

## Requisitos

- Python 3.11+ (recomendado)
- Credenciais da OpenAI
- Credenciais do Google (OAuth Client) **ou** Service Account

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Edite `backend/.env` com suas chaves e caminhos.

Inicie o servidor:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Abra a UI (estática) em `http://localhost:8000/`.

## Google Calendar: autenticação

### Opção A) Service Account (recomendado em produção)

- Crie uma Service Account no Google Cloud, baixe o JSON e aponte:
  - `GOOGLE_SERVICE_ACCOUNT_FILE=/caminho/para/service-account.json`
- Defina o calendário alvo:
  - `GOOGLE_CALENDAR_ID=primary` (se o usuário autenticado for o owner) **ou** o ID do calendário compartilhado.
- Se usar Google Workspace com delegação:
  - `GOOGLE_WORKSPACE_SUBJECT_EMAIL=usuario@empresa.com`

### Opção B) OAuth (mais comum para testes)

- Gere `credentials.json` (OAuth Client) e salve em `backend/credentials.json`
- Rode:

```bash
python backend/scripts/google_oauth_setup.py
```

Ele cria `backend/token.json` (refresh token) que o servidor usa para operar.

## Prioridade → lembretes

- `high`: 24h e 2h antes (email + popup)
- `medium`: 24h antes (email + popup)
- `low`: 2h antes (popup)

Você pode ajustar em `backend/app/reminders.py`.

## Endpoints

- `GET /healthz`
- `POST /api/chat`
  - body: `{ "session_id": "...(opcional)", "message": "..." }`
  - resposta: `{ "session_id": "...", "reply": "...", "appointment": {...} }`

