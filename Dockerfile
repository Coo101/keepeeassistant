FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0 \
    DJANGO_DATA_DIR=/data

# Pango/GTK libraries so WeasyPrint can render real PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs a key but never signs anything; the real key comes from
# the environment at runtime. This throwaway value stays in the build step.
RUN DJANGO_SECRET_KEY=build-time-only-not-a-secret \
    python manage.py collectstatic --noinput

# Not root: a break-in stays limited to the app and its data.
RUN useradd --system --uid 1000 --no-create-home app \
    && mkdir -p /data \
    && chown -R app /data
USER app

VOLUME /data
EXPOSE 8000

# Migrations run at startup so the volume-backed database stays current.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3}"]
