FROM python:3.11-alpine
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH="/app/sabc"

RUN apk --update add libxml2-dev libxslt-dev libffi-dev gcc musl-dev libgcc openssl-dev curl && apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev tree py3-pip
RUN addgroup -S sabc && adduser -S sabc -G sabc

WORKDIR /app
COPY sabc sabc
ADD requirements-docker.txt /app/
ADD django_vars.env /app/
ADD create_superuser.sh /app/
ADD db_vars.env /app/

RUN pip install -r requirements-docker.txt
RUN chown -R sabc:sabc /app
USER sabc