# syntax=docker/dockerfile:1
# Image de l'application pour l'hebergement (Mistral App, VPS, etc.).
# Mode hors ligne (exe) : non utilise, voir build.spec / releases.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=*

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-hosting.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-hosting.txt

COPY . .
RUN python manage.py collectstatic --noinput

RUN groupadd -g 1000 app && \
    useradd -u 1000 -g 1000 -m -s /usr/sbin/nologin app && \
    chown -R 1000:1000 /app
USER 1000:1000

EXPOSE 8000
CMD ["sh", "deploy/entrypoint.sh"]
