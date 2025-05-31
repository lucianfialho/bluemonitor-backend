# BlueMonitor - Backend

Backend service for BlueMonitor, a platform for tracking and analyzing autism-related news in Brazil.

## Features

- News collection from multiple sources using SerpAPI
- Content extraction and processing
- AI-powered topic clustering and summarization
- Sentiment analysis
- RESTful API for frontend consumption

## Tech Stack

- Python 3.11+
- FastAPI
- MongoDB
- SerpAPI
- Hugging Face Transformers
- Docker

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure your environment variables
4. Run the application: `uvicorn app.main:app --reload`

## Project Structure

```
bluemonitor/
├── app/
│   ├── api/                  # API routes
│   ├── core/                 # Core configurations
│   ├── models/               # Database models
│   ├── schemas/              # Pydantic models
│   ├── services/             # Business logic
│   │   ├── ai/               # AI services
│   │   ├── news/             # News processing
│   │   └── storage/          # Database operations
│   └── main.py               # FastAPI application
├── tests/                    # Test files
├── .env.example              # Example environment variables
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Development

### Prerequisites

- Python 3.11+
- MongoDB
- Poetry (for dependency management)

### Setup

1. Install Poetry if you haven't already:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up pre-commit hooks:
   ```bash
   poetry run pre-commit install
   ```

4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

5. Update the `.env` file with your configuration.

### Running Locally

```bash
# Start MongoDB (if not using Docker)
docker-compose up -d mongodb

# Run the application
uvicorn app.main:app --reload
```

## API Documentation

Once the application is running, you can access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=term-missing
```

## Deployment

### Docker

Build and run the application using Docker Compose:

```bash
docker-compose up --build
```

### Production

For production deployments, you'll want to:

1. Set `ENVIRONMENT=production` in your `.env` file
2. Configure proper CORS settings
3. Set up a reverse proxy (Nginx, Traefik, etc.)
4. Configure HTTPS
5. Set up monitoring and logging

## License

MIT
