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
sleep 5

echo -e "${BLUE}⚙️ Executando script de inicialização do banco...${NC}"
# Executa o init_db dentro do container da loja
docker exec lojaup_app python app.py init

echo -e "${GREEN}✅ Deploy finalizado com sucesso!${NC}"
echo -e "📍 Loja: http://localhost:5678"
echo -e "📍 Admin: http://localhost:5679"
