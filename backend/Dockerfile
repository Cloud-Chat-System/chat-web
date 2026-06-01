FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system app && \
    useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

COPY --chmod=550 --chown=app:app app ./app
COPY --chmod=440 --chown=app:app seed.py .

USER app

CMD ["sh", "-c", "uvicorn app.main:app --host ${BACKEND_HOST} --port ${BACKEND_CONTAINER_PORT}"]