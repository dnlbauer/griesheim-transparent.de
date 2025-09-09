![actions](https://github.com/dnlbauer/griesheim-transparent.de/actions/workflows/build.yml/badge.svg?branch=main)

# griesheim-transparent.de

Repository for [http://griesheim-transparent.de](http://griesheim-transparent.de) - A transparency platform providing citizens access to municipal government documents, decisions, and activities from Griesheim (Germany, Hesse, Darmstadt-Dieburg) city parliament.

## Project Structure

### Core Components
1. **parliscope**: Django web application for citizen search interface and document processing
   - **frontend**: Web interface with search functionality and document viewer
   - **models**: Database models for scraped data (based on OParl standard)
   - **healthcheck**: Health monitoring for external services
   - **parliscope**: Main project configuration and settings

2. **scraper**: Scrapy-based web scraper for SessionNet municipal information systems
   - Extracts documents, meetings, and metadata from SessionNet
   - Stores data in PostgreSQL database

3. **solr**: Apache Solr search platform with German language configuration
   - Full-text indexing and search capabilities
   - Custom schema for municipal documents

4. **deployment**: Docker Compose configurations for development and production

## System Architecture

### Data Flow
1. **Scraper** → Documents/metadata → **PostgreSQL**
2. **Django management commands** → Document processing → **Solr indexing**
3. **Citizens** → Django frontend → **Solr search results**

### External Services
The platform integrates with several microservices for document processing:
- **PostgreSQL**: Metadata storage for scraped data
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
- **Document processing pipeline**: OCR, text extraction, format conversion, thumbnails
- **Full-text search**: German-language optimized Solr configuration
- **Health monitoring**: Service availability checks for all external dependencies
- **Responsive design**: Mobile-friendly interface for citizen access

## Workflow
1. **Automated scraping**: Cron job regularly extracts data from SessionNet
2. **Document processing**: Management commands process documents through external services
3. **Search indexing**: Processed documents are indexed in Solr for fast search
4. **Citizen access**: Web interface provides search and document viewing capabilities

## License
MIT
