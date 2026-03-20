#!/bin/bash
echo "🚀 Iniciando LojaUp via Docker Compose..."
docker compose up -d --build
echo "✅ Sistema online!"
echo "📍 Loja: http://localhost:5678"
echo "📍 Admin: http://localhost:5679"
