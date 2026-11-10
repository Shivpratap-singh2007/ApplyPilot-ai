FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
COPY agent/requirements.txt /app/agent/requirements.txt

RUN pip install --no-cache-dir -r /app/backend/requirements.txt -r /app/agent/requirements.txt \
    && pip install --no-cache-dir "psycopg[binary]>=3.2.0" \
    && playwright install chromium --with-deps

COPY backend /app/backend
COPY agent /app/agent

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

