FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/sabc" \
    POSTGRES_PASSWORD="sabc" \
    USER=sabc \
    POETRY_VERSION=1.5.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
ENV PATH=${POETRY_HOME}/bin:${PATH}

WORKDIR /app

COPY ../poetry.lock ../pyproject.toml /app/

RUN apt-get update && apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 -
RUN poetry install --no-root

ENTRYPOINT [ "poetry", "shell" ]