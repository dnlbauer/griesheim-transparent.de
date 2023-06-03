# pull official base image
FROM python:3.11-slim


RUN \
 apt update && \
 apt install -y libpq-dev gcc cron

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .

RUN \
 python3 -m pip install --upgrade pip --no-cache-dir && \
 python3 -m pip install -r requirements.txt --no-cache-dir

# set work directory
COPY . /app/
WORKDIR /app

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
