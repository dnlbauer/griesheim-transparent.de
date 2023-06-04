# pull official base image
FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .

RUN \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev python3-dev g++ && \
 python3 -m pip install --upgrade pip --no-cache-dir && \
 python3 -m pip install -r requirements.txt --no-cache-dir && \
 apk --purge del .build-deps

RUN \
 python3 -m pip install --upgrade pip --no-cache-dir && \
 python3 -m pip install -r requirements.txt --no-cache-dir

# set work directory
COPY . /app/
WORKDIR /app

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
