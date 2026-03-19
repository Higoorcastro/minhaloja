#!/bin/bash

# Cores para o terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Puxando atualizações do Git...${NC}"
git pull

echo -e "${BLUE}🛑 Parando containers atuais...${NC}"
docker compose down

echo -e "${BLUE}🚀 Subindo containers e compilando alterações...${NC}"
docker compose up -d --build

echo -e "${BLUE}📋 Aguardando banco de dados estabilizar...${NC}"
until docker exec lojaup_db pg_isready -U "${POSTGRES_USER:-postgres}" > /dev/null 2>&1; do
  sleep 2
done

echo -e "${BLUE}⚙️ Inicializando banco do Super Admin...${NC}"
docker exec -w /app/superadmin lojaup_admin python -c "from app import app, init_db; init_db()"

echo -e "${BLUE}⚙️ Inicializando banco da Loja...${NC}"
docker exec lojaup_app python app.py init

echo -e "${GREEN}✅ Deploy finalizado com sucesso!${NC}"
echo -e "📍 Loja: http://localhost:5678"
echo -e "📍 Admin: http://localhost:5679"
