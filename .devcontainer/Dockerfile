FROM python:3.11-slim
# DEVELOPMENT CONTAINER
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
ENV PATH=${POETRY_HOME}/bin:${PATH}

WORKDIR /app

RUN apt-get update && apt-get install -y gcc curl build-essential libpq-dev
RUN curl -sSL https://install.python-poetry.org | python3 -
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-root

ENTRYPOINT [ "poetry", "shell" ]