FROM python:3.10-alpine

RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
RUN pip install psycopg2-binary

WORKDIR /

COPY requirements.txt /requirements.txt
RUN pip install -r requirements.txt
COPY RIScraper /RIScraper
COPY config.yaml /

ENTRYPOINT ["python", "RIScraper/Scraper.py"]
