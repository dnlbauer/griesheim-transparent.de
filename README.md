![actions](https://github.com/dnlbauer/griesheim-transparent.de/actions/workflows/build.yml/badge.svg?branch=main)

# griesheim-transparent.de

Repository for [http://griesheim-transparent.de](http://griesheim-transparent.de) - A transparency platform providing citizens access to municipal government documents, decisions, and activities from Griesheim (Germany, Hesse, Darmstadt-Dieburg) city parliament.

## Project Structure

### Core Components
1. **parliscope**: Django web application for citizen search interface and document processing
   - **frontend**: Web interface with search functionality and document viewer
   - **models**: Database models for scraped data (based on OParl standard)
   - **healthcheck**: Health monitoring for external services
   - **parliscope**: Main project configuration, settings, and Celery setup

2. **scraper**: Scrapy-based web scraper for SessionNet municipal information systems
   - Extracts documents, meetings, and metadata from SessionNet
   - Stores data in PostgreSQL database

3. **solr**: Apache Solr search platform with German language configuration
   - Full-text indexing and search capabilities
   - Custom schema for municipal documents

4. **deployment**: Docker Compose configurations with Celery infrastructure
   - Redis broker for task queue
   - Celery Beat for scheduled tasks
   - Celery Worker for background processing
## System Architecture

### Data Flow
1. **Scraper** → Documents/metadata → **PostgreSQL**
2. **Django management commands** → Document processing → **Solr indexing**
3. **Citizens** → Django frontend → **Solr search results**

### External Services
The platform integrates with several microservices for document processing:
- **PostgreSQL**: Metadata storage for scraped data
- **Redis**: Message broker for Celery background task queue
- **Apache Tika**: PDF text extraction, metadata extraction, and OCR
- **PDFAct**: Advanced PDF text extraction with structure recognition
- **Gotenberg**: Document format conversion to PDF
- **Preview Service**: Document thumbnail generation

## Development

### Quick Start
```bash
# Full development environment with Docker
cd deployment && docker-compose -f dev.yaml up

# Local development (requires uv)
cd parliscope/ && uv sync && uv run python manage.py runserver
cd scraper/ && uv sync && uv run scrapy crawl sessionnet
```

### Key Features
- **Multi-database setup**: SQLite for Django app data, PostgreSQL for scraped data
- **Background task processing**: Celery with Redis broker for scalable document processing
- **Document processing pipeline**: OCR, text extraction, format conversion, thumbnails
- **Full-text search**: German-language optimized Solr configuration
- **Health monitoring**: Service availability checks for all external dependencies
- **Responsive design**: Mobile-friendly interface for citizen access

## Workflow
1. **Automated scraping**: Cron job regularly extracts data from SessionNet
2. **Document processing**: Celery background tasks process documents through external services
3. **Search indexing**: Processed documents are indexed in Solr for fast search
4. **Citizen access**: Web interface provides search and document viewing capabilities

## Initial Setup

After deploying the application for the first time:

1. **Run database migrations:**
   ```bash
   python manage.py migrate
   python manage.py migrate --database=scraped
   ```

2. **Create a superuser account:**
   ```bash
   python manage.py createsuperuser
   ```

3. **Configure periodic Solr indexing** (choose one method):

   **Option A: Management command (recommended)**
   ```bash
   python manage.py setup_periodic_tasks --schedule "0 3 * * *"
   ```
   This creates a daily task to update the Solr search index at 3 AM.

   **Option B: Django admin interface**
   - Navigate to `/admin/django_celery_beat/periodictask/`
   - Create new periodic task:
     - **Name:** `update-solr-index`
     - **Task:** `parliscope.tasks.indexing.update_solr_index`
     - **Crontab schedule:** Create/select schedule (e.g., daily at 3 AM)
     - **Arguments (JSON):** `{"force": false, "allow_ocr": true, "chunk_size": 10}`

4. **Manual indexing trigger (optional):**
   - Superusers can trigger immediate indexing via `/update/` endpoint
   - Uses Celery task queue for background processing

## License
MIT
