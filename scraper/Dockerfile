FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install system dependencies
RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev coreutils

WORKDIR /

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies with uv
RUN uv sync --frozen --no-dev

# copy app
COPY sessionnet /scraper/sessionnet
COPY scrapy.cfg /scraper

# install cron file
COPY crontab crontab.tmp
RUN chmod 0644 crontab.tmp \
    && crontab crontab.tmp \
    && rm -rf crontab.tmp

WORKDIR /scraper
ENTRYPOINT ["scrapy"]
