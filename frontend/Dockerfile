# pull official base image
FROM python:3.10.8-alpine

COPY requirements.txt .
RUN \
 apk add --no-cache postgresql-libs && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
 python3 -m pip install -r requirements.txt --no-cache-dir && \
 apk --purge del .build-deps

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set work directory
COPY . /app/
WORKDIR /app

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
