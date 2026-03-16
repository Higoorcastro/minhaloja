# 🏪 GestãoLoja — Sistema de Gestão Multi-Tenant v2.0 (PostgreSQL)

Sistema completo de gestão para pequenas e médias lojas, agora com arquitetura SaaS Multi-Tenant.

---

## 🏗️ Arquitetura
- **Engine:** Python + Flask
- **DB:** PostgreSQL (Multi-tenant via isolamento lógico `tenant_id`)
- **Infra:** Docker Compose (PostgreSQL)
- **Painel:** Integrado com Super Admin Panel para controle de lojas e assinaturas.

---

## 📦 Módulos
- **Dashboard:** Resumo consolidado por loja.
- **PDV (Ponto de Venda):** Registro de vendas ágil.
- **Financeiro:** Compras, Despesas e **Contas a Receber**.
- **Serviços:** Ordens de Serviço completas.
- **Relatórios:** Evolução de vendas, financeiro e posição de estoque.

---

## 🚀 Instalação e Execução (Linux)

### 1. Banco de Dados (Docker)
O banco PostgreSQL é gerenciado via Docker Compose:
```bash
docker-compose up -d
```

### 2. Painel Principal
Use o script de inicialização para o serviço da loja:
```bash
chmod +x iniciar.sh
./iniciar.sh
```

### 3. Painel Super Admin
Para gerenciar tenants e lojistas:
```bash
chmod +x iniciar_superadmin.sh
./iniciar_superadmin.sh
```

---

## 💾 Configuração
O sistema utiliza as seguintes variáveis de ambiente (definidas via `.env` ou diretoria):
- `DB_URL`: String de conexão PostgreSQL.
- `SECRET_KEY`: Chave de segurança para sessões Flask.

---

## 🖥️ Requisitos
- Linux (Ubuntu/Debian recomendado)
- Docker & Docker Compose
- Python 3.10+
- Navegador moderno

---

*Desenvolvido com Python + Flask + PostgreSQL*
