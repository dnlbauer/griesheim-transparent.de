# CLAUDE.md

This file provides guidance to a coding agent when working with code in this repository.

## Project Overview

This is a transparency platform for local politics. The platform provides
access to information about local government activities, decisions, and documents.
Currently, the platform is tailored for the municipality of Griesheim, Hesse, Germany.

The system consists of:

- **Scraper**: Scrapy-based web scraper that extracts documents from the municipal "Ratsinformationssystem".
- **Frontend**: Django web application providing the frontend with the search interface and document processing
- **Solr**: Search platform for indexing and querying documents
- **Supporting services**: PostgreSQL, Tika, preview service, Gotenberg for document processing

## Key Dependencies

- **Frontend**: Django, pysolr, requests, tika, gunicorn
- **Scraper**: Scrapy, psycopg2, peewee ORM
- **External services**: Apache Tika, PDFAct, Gotenberg, preview-service

## Architecture

### Core Components

- **scraper/**: Scrapy project (`sessionnet`) that scrapes municipal documents from SessionNet
- **frontend/**: Django application with two main functions:
  - Web interface for citizens to search documents (`frontend/` app)
  - Background processing to sync scraped data to Solr (`ris/` app for database models)
- **solr/**: Solr configuration for search indexing
- **deployment/**: Docker Compose setup for local development

### Data Flow

1. Scraper runs via cron to extract documents and metadata → PostgreSQL database
2. Frontend management command `update_solr` processes documents:
   - Converts files to PDF via Gotenberg
   - Extracts text content via Tika/PDFAct
   - Generates preview images
   - Indexes content in Solr
3. Django frontend queries Solr for search functionality

### Key Files

- `scraper/sessionnet/spiders.py`: Main scraping logic
- `scraper/sessionnet/pipelines.py`: Data processing pipeline
- `frontend/frontend/management/commands/update_solr.py`: Solr synchronization
- `frontend/ris/models.py`: Database models for scraped data
- `deployment/dev.yaml`: Complete docker-compose development environment

## Development Commands

### Local Development with Docker

```bash
# Start full development environment
cd deployment
docker-compose -f dev.yaml up

# Build individual services
docker build -t griesheimtransparent-frontend frontend/
docker build -t griesheimtransparent-scraper scraper/
docker build -t griesheimtransparent-solr solr/
```

### Frontend (Django)

```bash
cd frontend/

# Run development server
python manage.py runserver

# Database operations
python manage.py migrate  # For frontend database
python manage.py migrate --database=ris  # For scraper database

# Sync scraped data to Solr index
python manage.py update_solr

# Collect static files
python manage.py collectstatic

# Run tests
python manage.py test
```

### Scraper (Scrapy)

```bash
cd scraper/

# Run scraper manually
scrapy crawl sessionnet

# Scrape specific date range
scrapy crawl sessionnet -s SCRAPE_START=01/2023 -s SCRAPE_END=03/2023

# Run with crontab (automated)
# See scraper/crontab for scheduled runs
```

### Database Configuration

- **Frontend database**: SQLite (`/django_db/db.sqlite`) for Django app data
- **Scraper database**: PostgreSQL for scraped document metadata
- Database connections configured via environment variables (see `deployment/dev.yaml`)

## Environment Variables

Critical environment variables (defined in `deployment/dev.yaml`):

- `DJANGO_SECRET_KEY`: Django secret key
- `SOLR_HOST`, `SOLR_COLLECTION`: Solr connection
- `RIS_DB_*`: PostgreSQL scraper database credentials
- `DEBUG`: Django debug mode
- External service hosts: `TIKA_HOST`, `PDFACT_HOST`, `GOTENBERG_HOST`, `PREVIEW_HOST`

## Build and CI

- GitHub Actions builds and publishes Docker images for all components
- CI configuration: `.github/workflows/build.yml`
- Dependabot configured for automated dependency updates

**IMPORTANT: Update this document as the codebase evolves!**
