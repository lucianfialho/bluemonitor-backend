# Configuration Guide

This directory contains configuration files for the BlueMonitor application.

## Files

- `.env.example` - Example environment variables file. Copy this to `.env` and update the values as needed.
- `docker-compose.yml` - Docker Compose configuration for local development.
- `Dockerfile` - Docker configuration for building the application image.
- `pytest.ini` - Configuration for running tests.
- `pyproject.toml` - Project metadata and build configuration.
- `requirements.txt` - Python dependencies.

## Environment Variables

All configuration is done through environment variables, which can be set in the `.env` file or in your environment.

### Required Variables

- `MONGODB_URL` - MongoDB connection string (e.g., `mongodb://localhost:27017`)
- `SERPAPI_KEY` - API key for SerpAPI service
- `SECRET_KEY` - Secret key for cryptographic operations

### Optional Variables

See `.env.example` for a complete list of available configuration options with their default values.

## Development Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update the values in `.env` as needed.

3. Start the development services:
   ```bash
   docker-compose up -d
   ```

## Testing

To run tests with the local configuration:

```bash
pytest
```

## Deployment

For production deployments, make sure to:

1. Set `ENVIRONMENT=production`
2. Set `DEBUG=false`
3. Use secure values for all secrets
4. Configure proper CORS settings in `BACKEND_CORS_ORIGINS`
5. Set up proper logging and monitoring

## Security Notes

- Never commit the `.env` file to version control
- Use strong, unique values for all secrets
- Restrict database and Redis access to trusted networks
- Keep all dependencies up to date
- Regularly rotate API keys and secrets
