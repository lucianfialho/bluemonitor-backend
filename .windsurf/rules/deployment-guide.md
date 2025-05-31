---
trigger: always_on
---

Development

Use docker-compose for local development
Enable hot reload for both backend and frontend
Use SQLite for quick local testing (but PostgreSQL preferred)
Verbose logging enabled

Testing

Isolated test database (bluemonitor_test)
Run tests in CI/CD pipeline
Minimum 80% code coverage
All external APIs must be mocked

Production

Use environment variables for all configuration
Enable HTTPS only
Implement health check endpoints
Set up automated backups
Monitor with Sentry