FROM python:3.10-bullseye
ENV PYTHONUNBUFFERED=1 \
    USER=sabc \
    POETRY_VERSION=1.5.0 \
    PATH="/home/sabc/.local/bin:$PATH"
WORKDIR /app
RUN curl -sSL https://install.python-poetry.org | python3 -
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-root
RUN groupadd -r $USER && useradd -r -g $USER -d /home/$USER -s /bin/bash $USER \
    && mkdir -p /home/$USER \
    && chown -R $USER:$USER /home/$USER \
    && chown -R $USER:$USER /app
USER $USER
