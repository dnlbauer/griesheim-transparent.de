# CLAUDE.md

This file provides Claude Code with context and guidelines for working with this repository.

## Project Overview

A transparency platform for local politics providing citizens access to municipal government documents, decisions, and activities. Currently deployed for Griesheim, Hesse, Germany.

**Core Purpose**: Extract, process, and make searchable municipal documents from SessionNet systems.

### System Architecture
- **Scraper**: Scrapy spider extracting documents from municipal SessionNet
- **Parliscope**: Django web app with citizen search interface + background document processing
- **Celery**: Background task processing with Redis broker for document analysis and indexing
- **Solr**: Full-text search and document indexing
- **Services**: PostgreSQL, Apache Tika, Gotenberg, preview-service

### Data Flow
1. Scraper → Documents/metadata → PostgreSQL
2. Django management command → Document processing → Solr indexing
3. Citizens → Django frontend → Solr search results

## Development Context

### Stack
- **Backend**: Django 4.1+, Python 3.13+
- **Database**: SQLite (parliscope), PostgreSQL (scraped data)
- **Task Queue**: Celery with Redis broker for background processing
- **Search**: Apache Solr with pysolr client
- **Scraping**: Scrapy framework
- **Document Processing**: Apache Tika, PDFAct, Gotenberg
- **Deployment**: Docker Compose

### Critical Constraints
- Multi-database setup: SQLite for Django app, PostgreSQL for scraped data
- External service dependencies for document processing
- German locale (de-de) and timezone (Europe/Berlin)
- No hardcoded secrets - all config via environment variables

## Code Organization

### Current Project Structure

The project follows a modular Django architecture designed for scalability:

```
griesheim-transparent/
├── deployment/                 # Docker configurations (includes Celery services)
├── solr/                      # Search engine configuration  
├── scraper/                   # Legacy Scrapy project (external)
└── parliscope/                # MAIN DJANGO PROJECT
    ├── manage.py              # Django management script
    ├── parliscope/            # MAIN PROJECT APP (Django core)
    │   ├── settings.py        # Main project settings (includes Celery config)
    │   ├── celery.py          # Celery application configuration
    │   ├── urls.py           # Root URL configuration
    │   ├── wsgi.py           # WSGI application
    │   └── databaserouter.py  # Multi-database routing
    ├── models/                # SHARED DATA MODELS (renamed from 'ris')
    │   ├── models.py          # OParl-based data models
    │   ├── admin.py           # Admin interface for models
    │   └── migrations/        # Database migrations
    ├── frontend/              # WEB INTERFACE APP
    │   ├── views.py           # Web views and API endpoints
    │   ├── urls.py           # Frontend URL patterns
    │   ├── templates/         # HTML templates
    │   ├── static/           # CSS, JS, images
    │   ├── search/           # Search utilities
    │   ├── management/commands/ # Custom Django commands (update_solr.py)
    │   └── migrations/        # Frontend-specific migrations
    └── healthcheck/           # HEALTH CHECK APP (extracted)
        ├── apps.py           # Health check backend registration
        └── backends/         # External service monitors
```

### Key Directories
- `scraper/sessionnet/`: Legacy Scrapy spider (being migrated)
- `parliscope/parliscope/`: Main Django project configuration and routing
- `parliscope/frontend/`: Django web app (views, templates, search functionality)
- `parliscope/models/`: Database models for scraped data (OParl-based)
- `parliscope/healthcheck/`: Dedicated health check backends for external services
- `parliscope/frontend/management/commands/`: Custom Django management commands
- `deployment/`: Docker Compose configurations for all environments
- `solr/`: Solr schema and configuration files

### Critical Files
- `scraper/sessionnet/spiders.py`: SessionNet scraping logic (legacy)
- `parliscope/models/models.py`: Data models (Document, Organization, Person)
- `parliscope/frontend/management/commands/update_solr.py`: Document processing pipeline
- `parliscope/parliscope/settings.py`: Multi-database and service configuration
- `parliscope/parliscope/databaserouter.py`: Database routing between SQLite and PostgreSQL
- `deployment/dev.yaml`: Complete development environment

## Development Workflow

### Quick Start
```bash
# Option 1: Docker (recommended for full stack)
cd deployment && docker-compose -f dev.yaml up

# Option 2: Local development (requires uv setup)
cd parliscope/
uv sync  # Create virtual environment and install dependencies
uv run python manage.py runserver
```

### Recommended Development Process
1. **Explore**: Read relevant files before making changes
2. **Plan**: Create clear implementation plan
3. **Code**: Make incremental changes
4. **Test**: Run tests and verify functionality
5. **Commit**: Use descriptive commit messages

### Common Commands

#### Parliscope Development
```bash
cd parliscope/
uv sync  # Install/update dependencies

# Development
uv run python manage.py runserver
uv run python manage.py check
uv run pytest  # Run tests
uv run ruff check  # Lint code
uv run ruff format  # Format code
uv run mypy  # Type check code

# Database
uv run python manage.py migrate
uv run python manage.py migrate --database=scraped
uv run python manage.py makemigrations

# Data Processing
uv run python manage.py update_solr  # Process documents to Solr
uv run python manage.py collectstatic
```

DO NOT run `python manage.py test`. Use `pytest` instead.

#### Scraper Operations
```bash
cd scraper/
uv sync  # Install/update dependencies

# Manual scraping
uv run scrapy crawl sessionnet
uv run scrapy crawl sessionnet -s SCRAPE_START=01/2023 -s SCRAPE_END=03/2023
```

### Environment Setup

#### Python Environment

**Prerequisites**: Install uv first: `curl -LsSf https://astral.sh/uv/install.sh | sh`

```bash
# Parliscope setup
cd parliscope/
uv sync  # Creates virtual environment and installs dependencies automatically

# Scraper setup  
cd ../scraper/
uv sync  # Creates virtual environment and installs dependencies automatically
```

#### Database Configuration
- **Parliscope**: SQLite at `/django_db/db.sqlite` (Django app data)
- **Models**: PostgreSQL (scraped document metadata)
- **Router**: `parliscope.databaserouter.DatabaseRouter` handles multi-DB routing

#### Required Environment Variables
```bash
# Core Django
DJANGO_SECRET_KEY=your-django-secret-key-here
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL (scraped data)
SCRAPED_DB_HOST=localhost
SCRAPED_DB_PORT=5432
SCRAPED_DB_NAME=database_name
SCRAPED_DB_USER=db_username
SCRAPED_DB_PASSWORD=db_password

# Celery background processing
CELERY_BROKER_URL=redis://localhost:6379/0

# Search and processing services
SOLR_HOST=http://localhost:8983/solr
SOLR_COLLECTION=ris
TIKA_HOST=http://localhost:9998
PDFACT_HOST=http://localhost:80
GOTENBERG_HOST=http://localhost:3000
PREVIEW_HOST=http://localhost:8000
```

## Testing & Quality Assurance

### Testing Environment Setup
For commands that require database connections, start PostgreSQL via Docker:
```bash
cd deployment/
docker-compose -f dev.yaml up -d scraper-database  # Start PostgreSQL only
```

### Testing Strategy
```bash
cd parliscope/
uv sync  # Ensure dependencies are installed

# Run all tests
uv run python manage.py test

# Test specific apps
uv run python manage.py test frontend models healthcheck

# Django system checks
uv run python manage.py check
uv run python manage.py check --deploy
```

### Database Operations
```bash
cd parliscope/
uv sync  # Ensure dependencies are installed

# Migrations
uv run python manage.py makemigrations  # Create new migrations
uv run python manage.py migrate         # Apply to SQLite
uv run python manage.py migrate --database=scraped  # Apply to PostgreSQL

# Inspection
uv run python manage.py showmigrations
uv run python manage.py dbshell [--database=scraped]
```

## Code Standards

### Django Patterns
- **Models**: Extend `BaseModel` for `created_at`/`last_modified` fields
- **Commands**: Inherit from `BaseCommand` for management commands
- **Settings**: Use `django-environ` for configuration
- **Database**: Multi-DB routing via `DatabaseRouter`

### Code Conventions
- **Naming**: PascalCase classes, snake_case functions, UPPER_CASE constants
- **Imports**: Standard library → third-party → local imports
- **Private methods**: Prefix with underscore (`_parse_args`)
- **Database models**: Explicit `db_table` names, no DB constraints on ForeignKeys

### Architecture Guidelines
- **External services**: Centralize in `processing/external_services.py`
- **Utilities**: Common functions in dedicated utils modules
- **Configuration**: Environment variables only (no hardcoded values)
- **Logging**: Module-level loggers with `logging.getLogger(__name__)`
- **Error handling**: Specific exceptions, proper context managers

### Security Requirements
- **Secrets**: Environment variables only
- **Authentication**: Support both session and HTTP Basic Auth
- **Database**: Django ORM prevents SQL injection
- **CSRF**: Maintain Django middleware protection

## Development Guidelines

### When Making Changes
1. **Read first**: Understand existing patterns before coding
2. **Test changes**: Run `uv run python manage.py test` and `uv run python manage.py check`
3. **Follow conventions**: Match existing code style and patterns
4. **Update docs**: Keep this file current with changes


### Deployment
- **CI/CD**: GitHub Actions builds Docker images
- **Config**: `.github/workflows/build.yml`
- **Dependencies**: Dependabot automated updates

### Getting Help
Refer to key files when understanding functionality:
- Models: `parliscope/models/models.py`
- Scraping: `scraper/sessionnet/spiders.py`
- Document processing: `parliscope/parliscope/tasks/indexing.py`
- Periodic task setup: `parliscope/parliscope/management/commands/setup_periodic_tasks.py`
- Configuration: `parliscope/parliscope/settings.py`
- Health checks: `parliscope/healthcheck/`

---
*Keep this document updated as the codebase evolves!*
- when running python manage.py commands, use DEBUG=true
- Dont use `python -c` for testing snippets. Use the tools provided by django or pytest.
- Favor double quotes for strings instead of single quotes. Use f-strings for formatting.