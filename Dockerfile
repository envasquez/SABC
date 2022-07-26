FROM python:3-alpine
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN apk --update add libxml2-dev libxslt-dev libffi-dev gcc musl-dev libgcc openssl-dev curl
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev tree py3-pip
WORKDIR /app

RUN addgroup -S sabc && adduser -S sabc -G sabc
COPY sabc sabc
ADD entrypoint.sh /app/
ADD requirements.txt /app/
RUN pip install -r requirements.txt
RUN chown -R sabc:sabc /app
USER sabc
#CMD ["./entrypoint.sh"]