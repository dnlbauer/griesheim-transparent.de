FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev coreutils \
    && pip install psycopg2-binary

WORKDIR /

# install requirements
COPY requirements.txt /requirements.txt
RUN pip install --upgrade pip --no-cache-dir \
    && pip install -r requirements.txt --no-cache-dir

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
