# AI Agent Platform

A FastAPI backend service for creating, managing, and interacting with AI agents via text and voice. Integrates with OpenAI APIs for chat completions, speech-to-text (Whisper), and text-to-speech.

## Features

- **Agent Management** — Create, update, and list AI agents with custom system prompts
- **Chat Sessions** — Multiple chat sessions per agent with full message history
- **Text Messaging** — Send messages and receive responses (JSON or SSE streaming)
- **Voice Interaction** — Upload audio, transcribe via STT, generate response, return TTS audio
- **Interactive API Docs** — Auto-generated Swagger UI and ReDoc
- **Frontend UI** — Minimal web interface for demo purposes

## Tech Stack

- **Python 3.10+** / **FastAPI**
- **PostgreSQL** with pgvector extension
- **SQLAlchemy** (async) + **Alembic** migrations
- **OpenAI API** (chat, Whisper STT, TTS)
- **Docker** for containerization

## Project Structure

```
AI-Agent-Platform/
├── src/
│   ├── main.py                     # FastAPI application entry point
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment variables template
│   ├── routes/                     # API endpoint definitions
│   │   ├── api.py                  # Router aggregator
│   │   ├── agents_router.py        # Agent CRUD endpoints
│   │   ├── sessions_router.py      # Session endpoints
│   │   ├── chat_router.py          # Chat & voice endpoints
│   │   └── schemes/                # Pydantic request/response models
│   ├── controllers/                # Business logic
│   │   └── conversation.py         # Chat conversation logic
│   ├── models/                     # Data access layer
│   │   ├── AgentModel.py
│   │   ├── SessionModel.py
│   │   ├── MessageModel.py
│   │   └── ai_agent_platform_DB/   # Database schema & migrations
│   │       ├── schemes/            # SQLAlchemy ORM models
│   │       └── alembic/            # Alembic migration scripts
│   ├── stores/                     # External service providers
│   │   └── LLM/OpenAIProvider.py   # OpenAI integration
│   ├── helpers/config.py           # Settings via pydantic-settings
│   ├── static/                     # Frontend UI files
│   └── tests/                      # Test suite
├── docker/
│   ├── docker-compose.yml          # Database only (development)
│   └── .env.example
├── docker-compose.yml              # Full stack (production)
├── Dockerfile                      # Backend containerization
├── entrypoint.sh                   # Auto-migrate & start
├── .env.example                    # Production env template
├── postman_collection.json         # Postman collection
└── README.md
```

## Prerequisites

- Python 3.10+
- PostgreSQL (or use Docker Compose for the database)
- OpenAI API key

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/ahmedbadawy11/AI-Agent-Platform
cd AI-Agent-Platform
```

### 2. Start the database

Use Docker Compose to spin up PostgreSQL with pgvector:

```bash
cd docker
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD
docker-compose up -d
cd ..
```

### 3. Run database migrations

The project uses Alembic for schema management. Set up and run migrations:

```bash
cd src/models/ai_agent_platform_DB
cp alembic.ini.example alembic.ini
```

Edit `alembic.ini` and set the `sqlalchemy.url` to your database connection string:

```ini
sqlalchemy.url = postgresql://postgres:ai_agent123@localhost:5432/AI_Agent_Platform
```

> **Note:** Use the standard `postgresql://` driver (not `postgresql+asyncpg://`) for Alembic,
> since it runs synchronous migrations.

Then create the database and apply migrations:

```bash
# Create the database if it doesn't exist
# (connect to postgres and run: CREATE DATABASE "AI_Agent_Platform";)

### (Optional) Create a new migration
alembic revision --autogenerate -m "Add ..."

# Apply all migrations
alembic upgrade head
cd ../../..
```

### 4. Configure environment variables

```bash
cd src
cp .env.example .env
```

Edit `src/.env` with your settings:

| Variable | Description | Example |
|---|---|---|
| `APP_NAME` | Application name | `AI-Agent-Platform` |
| `APP_VERSION` | Application version | `0.1.0` |
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_USERNAME` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `ai_agent123` |
| `POSTGRES_MAIN_DATABASE` | Database name | `AI_Agent_Platform` |
| `GENERATION_MODEL_ID` | Chat model | `gpt-4o-mini` |
| `GENERATION_DAFAULT_MAX_TOKENS` | Max response tokens | `200` |
| `GENERATION_DAFAULT_TEMPERATURE` | Temperature (0-2) | `0.1` |
| `STT_MODEL_ID` | Speech-to-text model | `whisper-1` |
| `STT_LANGUAGE` | STT language hint (optional) | `en` |
| `TTS_MODEL_ID` | Text-to-speech model | `tts-1` |
| `TTS_VOICE` | TTS voice | `alloy` |
| `LOG_LEVEL` | Logging level | `INFO` |

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the application

```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:

- **Web UI**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc


## API Endpoints

All endpoints are under `/api/v1`.

### Agents

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/agents` | List all agents |
| `POST` | `/api/v1/agents` | Create a new agent |
| `PUT` | `/api/v1/agents/{agent_id}` | Update an agent |

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/agents/{agent_id}/sessions` | List sessions for an agent |
| `POST` | `/api/v1/agents/{agent_id}/sessions` | Create a new session |
| `GET` | `/api/v1/agents/sessions/{session_id}` | Get session by ID |

### Chat & Voice

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/sessions/session-messages?session_id={id}` | List messages in a session |
| `POST` | `/api/v1/sessions/send-message` | Send text message (JSON response) |
| `POST` | `/api/v1/sessions/stream-message` | Send text message (SSE streaming) |
| `POST` | `/api/v1/sessions/send-voice-message` | Send voice message (multipart form) |

## Testing

The project uses **pytest** with async support for testing. Tests use an in-memory SQLite database and mock the OpenAI provider, so no external services are needed.

### Run tests

```bash
cd src
pip install -r requirements.txt
pytest tests/ -v
```

### Test coverage

The test suite covers:

- **Agent endpoints** — create, list, update, validation errors, 404 handling
- **Session endpoints** — create, list by agent, get by ID, 404 handling
- **Chat endpoints** — send message, streaming, message persistence, voice messages, input validation

## Postman Collection

A Postman collection is included at `postman_collection.json` for manual API testing.

### Import into Postman

1. Open Postman
2. Click **Import** and select `postman_collection.json`
3. The collection uses a `{{base_url}}` variable (defaults to `http://localhost:8000`)
4. Run requests in order: **Create Agent** → **Create Session** → **Send Message**

The collection auto-captures `agent_id` and `session_id` from create responses into collection variables for downstream requests.

## Docker (Production Deployment)

The project includes a production-ready `docker-compose.yml` at the project root that runs the
**full stack** (app + PostgreSQL/pgvector) with a single command. The app container automatically:

1. Waits for PostgreSQL to be ready
2. Creates the database if it doesn't exist
3. Runs Alembic migrations
4. Starts the FastAPI server

### Quick start (build locally)

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD and OPENAI_API_KEY at minimum
docker-compose up -d
```

The app will be available at http://localhost:8000 once both containers are healthy.

### Deploy from a registry (client server)

If you push the image to Docker Hub or a private registry, the client only needs **three files**:

- `docker-compose.yml`
- `.env.example` (copy to `.env` and configure)

```bash
# On the client server
cp .env.example .env
# Edit .env — set OPENAI_API_KEY, POSTGRES_PASSWORD, and the image name:
#   APP_IMAGE=your-dockerhub-user/ai-agent-platform:latest
docker-compose up -d
```

When `APP_IMAGE` is set, Compose pulls that image instead of building locally.

### Push image to Docker Hub

```bash
# Build and tag
docker build -t your-dockerhub-user/ai-agent-platform:latest .

# Push
docker push your-dockerhub-user/ai-agent-platform:latest
```

### Build the image only (without Compose)

```bash
docker build -t ai-agent-platform .
```

### Docker Compose services

| Service | Image | Port | Description |
|---|---|---|---|
| `pgvector` | `pgvector/pgvector:0.8.1-pg17-trixie` | `5432` | PostgreSQL with pgvector extension |
| `app` | Built from `Dockerfile` or pulled via `APP_IMAGE` | `8000` | FastAPI backend |

### Environment variables

All configuration is done via the `.env` file at the project root. See `.env.example` for all
available variables. Key variables:

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | Yes | Database password |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `APP_IMAGE` | No | Set to pull from registry instead of building locally |

### Stop / remove

```bash
docker-compose down          # stop containers
docker-compose down -v       # stop and remove database volume
```

### Database-only Docker Compose (development)

The `docker/docker-compose.yml` file runs **only** the PostgreSQL database, useful when
developing locally and running the app outside Docker:

```bash
cd docker
cp .env.example .env
docker-compose up -d
cd ..
```

