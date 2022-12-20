FROM python:3.9-alpine

RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev coreutils \
    && pip install psycopg2-binary

WORKDIR /

# install requirements
COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt

# copy app
COPY RIScraper /RIScraper
COPY config.yaml /

# install cron file
COPY crontab crontab.tmp
RUN chmod 0644 crontab.tmp \
    && crontab crontab.tmp \
    && rm -rf crontab.tmp

ENTRYPOINT ["python", "RIScraper/Scraper.py"]
