FROM python:3.11-alpine
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH="/app/sabc"
ENV POSTGRES_PASSWORD="sabc"
ENV DJANGO_DEBUG=0
ENV DJANGO_SECRET_KEY="d7nkrwbu1j0q9$z^$ip*vj4itf641bbm+^hki1zn^an80i3_t4"
RUN addgroup --gid 1000 -S sabc && adduser --uid 1000 -S sabc -G sabc
WORKDIR /app
COPY sabc sabc
ADD requirements-docker.txt /app/
ADD django_vars.env /app/
ADD create_superuser.sh /app/
ADD db_vars.env /app/
RUN pip install -r requirements-docker.txt
RUN chown -R sabc:sabc /app
USER sabc