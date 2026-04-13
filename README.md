# A modular RAG system for querying your personal data (emails, notes, journals) using PostgreSQL, pgvector, and OpenAI.

## Project Structure

The project follows a **Layered Architecture** to ensure clean separation of concerns and scalability.

```text
de-assist/
├── connectors/         # External integrations (Gmail, Telegram)
├── core/               # Business logic (Ingestion, Embedding, RAG)
├── db/                 # Database schema and persistence layer
├── scripts/            # Utility and development scripts
├── tests/              # Automated tests
├── config/             # Configuration templates
├── data/               # Local data storage (ignored by git)
├── main.py             # CLI Entry point
├── docker-compose.yml  # Infrastructure as Code
└── pyproject.toml      # Dependency and package management
```

### Strategy & Reasoning

1.  **Separation of Concerns**:
    *   **Core**: Contains the pure logic for chunking, embedding, and searching. It doesn't care if the data comes from a JSON file or an API.
    *   **Connectors**: Handles the messiness of external APIs (OAuth, Webhooks, sanitization).
    *   **DB**: Isolates all SQL logic. If we switch databases, we only change this folder.
2.  **Maintainability**: By grouping related files, developers can navigate the codebase intuitively. New features have a predictable home.
3.  **Security**: 
    *   Sensitive credentials and tokens are kept in the root (and ignored by git) or managed via environment variables.
    *   The `scripts/` folder isolates development-only code from the application flow.
4.  **Extensibility**: Adding a new source (e.g., Slack) simply requires a new file in `connectors/` without touching the `core` retrieval logic.

## Quick Start

### 1. Prerequisites
- Python 3.14 (managed by `uv`)
- Docker & Docker Compose
- An OpenAI API Key (`text-embedding-3-small` and `gpt-4o-mini` are used by default)
### 2. Setup
```bash
# Start the database
docker-compose up -d

# Install dependencies and the project
uv sync

# Setup schema
uv run de-assist setup
```

### 3. Usage
- **Ingest Local Data**: `uv run de-assist ingest --source local --dir data`
- **Ingest Gmail**: `uv run de-assist ingest --source gmail`
- **Search**: `uv run de-assist search "your query"`
- **Ask AI**: `uv run de-assist ask "your question"`
- **Telegram Bot**: `uv run telegram-bot`

## Development
- **Run Tests**: `uv run pytest`
- **Generate Sample Data**: `uv run python scripts/generate_sample_data.py`

## Docker Deployment (Private Server)

You can deploy the entire stack (Database + Bot) using Docker.

1.  **Configure `.env`**: Ensure all keys are correctly set.
2.  **Initialize Database**:
    ```bash
    docker-compose run --rm app de-assist setup
    ```
3.  **Deploy**:
    ```bash
    # Start the DB and the Telegram Bot
    docker-compose up -d
    ```

The `bot` service will restart automatically if it crashes or if the server reboots.
