FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/usr/src/app/sabc" \
    POSTGRES_PASSWORD="sabc" \
    DJANGO_DEBUG=1 \
    USER=sabc \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev

ADD docker/requirements.txt /app
RUN pip install -r requirements.txt

RUN useradd -m $USER && chown -R ${USER}:${USER} /app
USER ${USER}