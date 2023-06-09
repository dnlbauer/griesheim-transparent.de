# Scrapy settings for sessionnet project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
from sessionnet.utils import month_from_now
from os import environ

BOT_NAME = "griesheim-transparent scraper"

SPIDER_MODULES = ["sessionnet.spiders"]
NEWSPIDER_MODULE = "sessionnet.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "griesheim-transparent/scrapy (+https://griesheim-transparent.de)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de; en",
}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "sessionnet.pipelines.MyFilesPipeline": 1,
    "sessionnet.pipelines.HTMLFilterPipeline": 300,
    "sessionnet.pipelines.PsqlExportPipeline": 999,
}

import os
FILES_STORE = os.path.join(os.getcwd(), "filestore")
FILES_EXPIRES = 90
MYFILESPIELINE_FILES_EXPIRES = FILES_EXPIRES

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 60*60
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

LOG_LEVEL = "INFO"

SCRAPE_ORGANIZATIONS = True
SCRAPE_MEETINGS = True
SCRAPE_START = "01/2011"
SCRAPE_END = month_from_now(3)

DB_HOST = environ.get("DB_HOST", default="localhost")
DB_PORT = int(environ.get("DB_PORT", default="5432"))
DB_NAME = environ.get("DB_NAME", default="")
DB_USER = environ.get("DB_USER", default="")
DB_PASSWORD = environ.get("DB_PASSWORD", default="")

