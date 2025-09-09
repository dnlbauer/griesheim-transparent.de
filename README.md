![actions](https://github.com/dnlbauer/griesheim-transparent.de/actions/workflows/build.yml/badge.svg?branch=main)

# griesheim-transparent.de

Repository for [http://griesheim-transparent.de](http://griesheim-transparent.de) - A search engine for documents of the Griesheim (Germany, Hessen, Darmstadt-Dieburg)
city parliament.

## Modules
1) **scraper**: Scrapy-based webscraper for the "Ratsinformationssystem" aka. sessionnet https://sessionnet.owl-it.de/griesheim/bi/info.asp
2) **parliscope**: Django project for frontend and management jobs for analysis
3) **solr**: Solr Search Platform configuration

  
## Additional services
The full service is build on several microservices required at indexing time and for data storage (see [docker compose file](deployment/dev.yaml) for details):
- A postgresql database to store scraped metadata.
- [Tika](https://hub.docker.com/r/apache/tika) for pdf metadata extraction, text extraction and OCR.
- [fpurchess/preview-service](https://hub.docker.com/r/fpurchess/preview-service) for thumbnail generation.
- [gotenberg](https://hub.docker.com/r/gotenberg/gotenberg) to convert different file formats to pdf.

## Workflow:
- The scraper docker image runs a cron job to scrape the sessionnet regulary and stores metadata+binary files stored to postgresql and the datastore.
- The frontend management task is also run in a cron job to periodically sync the scraped data into the solr index for searching. This includes:
  - Combining metadata from scraped meetings, meeting agendas, consultations etc.
  - Converting non-pdfs to pdf
  - Extracting document metadata and content from pdfs with pdfact, tika and/or tika+tesseract (ocr)
  - Generating preview images with the preview-service
- The frontend django app makes the data available to the user by queyring the solr search platform

## License
MIT
 
