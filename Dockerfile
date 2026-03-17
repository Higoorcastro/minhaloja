FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_TYPE=loja

EXPOSE 5678
EXPOSE 5679

CMD ["sh", "-c", "\
  if [ \"$APP_TYPE\" = \"admin\" ]; then \
    exec gunicorn \
      --chdir superadmin \
      --bind 0.0.0.0:5679 \
      --workers ${GUNICORN_WORKERS:-2} \
      --timeout ${GUNICORN_TIMEOUT:-120} \
      --access-logfile - \
      --error-logfile - \
      --log-level warning \
      app:app; \
  else \
    exec gunicorn \
      --bind 0.0.0.0:5678 \
      --workers ${GUNICORN_WORKERS:-2} \
      --timeout ${GUNICORN_TIMEOUT:-120} \
      --access-logfile - \
      --error-logfile - \
      --log-level warning \
      app:app; \
  fi"]
