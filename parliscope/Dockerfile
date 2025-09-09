# pull official base image
FROM ghcr.io/astral-sh/uv:python3.13-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apk add --no-cache postgresql-libs \
 && apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev python3-dev g++ \
 && apk add --no-cache curl

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies with uv to system
RUN uv pip install --system --no-cache -r pyproject.toml

# Clean up build dependencies
RUN apk --purge del .build-deps

# set work directory
COPY . /app/
WORKDIR /app

RUN chmod +x entrypoint.sh
ENTRYPOINT ["/bin/sh", "entrypoint.sh"]
