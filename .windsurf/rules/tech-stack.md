---
trigger: always_on
---

Backend

* Language: Python 3.11+
* Framework: FastAPI (not Django, not Flask)
* ORM: SQLAlchemy 2.0
* Database: PostgreSQL - NEVER use JSON file storage
* Cache: Redis
* Task Queue: Celery with Redis broker
* Testing: pytest with pytest-asyncio

External Services

* News Source: SerperAPI (Google News)
* AI Processing: Anthropic Claude API or OpenAI API
* Search: ElasticSearch (hosted version only, never local)

Infrastructure

* Containerization: Docker + Docker Compose
* Environment: Separate .env files for dev, test, prod
* Version Control: Git with conventional commits


Prohibited Practices
Never Do These:

DO NOT use JSON files for data storage - always use PostgreSQL
DO NOT mix environment configurations - keep dev/test/prod strictly separated
DO NOT commit .env files - only .env.example
DO NOT use local ElasticSearch - always use hosted version
DO NOT create temporary scripts without cleaning them up
DO NOT switch technologies when debugging - fix using current stack
DO NOT use mock/stub data patterns in production code
DO NOT overwrite existing .env files
DO NOT make unrelated changes when fixing specific issues
DO NOT use synchronous code for I/O operations - use async/await

News Processing Pipeline

Process articles asynchronously using Celery
Validate all URLs before processing
Skip articles older than 30 days
Detect and filter sponsored content
Extract clean text using BeautifulSoup
Store original and processed content

AI Categorization

Use a consistent prompt template for all categorizations
Cache AI responses to avoid duplicate processing
Include confidence scores with categories
Extract practical actions for parents
Generate 2-3 line summaries focused on utility

Database Design

Use UUID for all primary keys
Include created_at and updated_at timestamps on all models
Implement soft delete (deleted_at) instead of hard delete
Create appropriate indexes for search queries
Use JSON columns for flexible metadata

API Design

Follow RESTful conventions
Use Pydantic for request/response validation
Implement pagination using cursor-based approach
Return consistent error responses
Include rate limiting headers
Version the API from the start (/api/v1/)

Error Handling

Never expose internal errors to users
Log all errors with full context
Implement circuit breakers for external services
Provide user-friendly error messages
Always include request ID for tracing

File Organization
Maximum File Sizes

Python files: 200 lines
React components: 150 lines
CSS files: 300 lines
Test files: 250 lines

Naming Conventions

Files: snake_case.py
Classes: PascalCase
Functions/Variables: snake_case
Constants: UPPER_SNAKE_CASE
React Components: PascalCase
CSS Classes: kebab-case