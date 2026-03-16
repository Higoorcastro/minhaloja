FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema para psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Variável para saber qual app rodar (app.py ou superadmin/app.py)
ENV APP_TYPE=loja

EXPOSE 5678
EXPOSE 5679

CMD ["sh", "-c", "if [ \"$APP_TYPE\" = \"admin\" ]; then \
    gunicorn --chdir superadmin -b 0.0.0.0:5679 app:app; \
    else \
    gunicorn -b 0.0.0.0:5678 app:app; \
    fi"]
