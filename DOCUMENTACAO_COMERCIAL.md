# MinhaLoja — Sistema de Gestão Comercial
## Documentação Técnica e Comercial Completa

**Versão:** 1.0
**Plataforma:** SaaS Multi-Tenant (Web)
**Tecnologia:** Python + Flask + PostgreSQL
**Implantação:** Docker / Cloud-ready

---

## Visão Geral

**MinhaLoja** é um sistema ERP (Enterprise Resource Planning) completo para pequenas e médias empresas, entregue como serviço SaaS (Software as a Service). A plataforma centraliza todas as operações comerciais — vendas, estoque, finanças, clientes, ordens de serviço e relatórios — em um único painel web moderno, acessível de qualquer dispositivo.

Construído com arquitetura **multi-tenant**, o sistema permite que múltiplas lojas compartilhem a mesma infraestrutura com isolamento total de dados, tornando-o ideal para revendedores, franquias e grupos empresariais.

---

## Proposta de Valor

| Problema do Cliente | Solução MinhaLoja |
|---|---|
| Controle de vendas em planilhas | PDV digital completo com histórico |
| Desconhecimento do estoque real | Controle automático atualizado em tempo real |
| Dificuldade para emitir OS | Módulo de ordens de serviço com workflow |
| Finanças desorganizadas | Dashboard financeiro com contas, movimentações e relatórios |
| Falta de controle de clientes | CRM básico com histórico de compras |
| Múltiplos sistemas desconexos | Tudo em um único painel integrado |

---

## Módulos do Sistema

### 1. Dashboard

Painel principal com visão consolidada em tempo real de toda a operação:

- **KPIs de Vendas:** Total do dia, semana e mês com comparativo
- **Resumo Financeiro:** Saldo em caixa, entradas e saídas
- **Alertas de Estoque:** Produtos abaixo do estoque mínimo
- **Últimas Transações:** Feed das movimentações mais recentes
- **Status de Contas a Receber:** Pendentes, vencidas e recebidas hoje

**Benefício comercial:** Visão executiva instantânea sem precisar de relatórios manuais.

---

### 2. PDV — Ponto de Venda

Interface otimizada para velocidade, projetada para uso diário no balcão:

- **Busca rápida de produtos** por nome ou código
- **Carrinho de compras** com quantidade editável
- **Desconto por item** ou no total da venda
- **Múltiplas formas de pagamento:**
  - Dinheiro
  - Cartão de Débito
  - Cartão de Crédito (1x, 2x, 3x)
  - PIX
  - Transferência Bancária
- **Integração com máquinas de cartão:** cálculo automático de taxas por maquininha
- **Seleção de cliente e vendedor** na venda
- **Número sequencial automático** por loja
- **Cancelamento de venda** com registro de motivo
- **Impressão de recibo**

**Benefício comercial:** Reduz o tempo de cada transação e elimina erros manuais de cálculo.

---

### 3. Gestão de Vendas

Histórico completo e rastreável de todas as transações:

- **Listagem filtrada** por período, cliente, vendedor e status
- **Detalhamento de cada venda:** itens, valores, forma de pagamento, taxas
- **Status:** Concluída ou Cancelada
- **Rastreamento de taxas:** valor bruto × taxa de cartão = valor líquido
- **Relatório de vendas por vendedor**

**Benefício comercial:** Auditoria e controle total do histórico comercial.

---

### 4. Ordens de Serviço (OS)

Módulo completo para empresas que prestam serviços de manutenção e reparo:

**Informações da OS:**
- Cliente, equipamento, problema reportado
- Diagnóstico técnico e solução aplicada
- Técnico responsável
- Senha/PIN do dispositivo (armazenado de forma segura)
- Observações e checklist de procedimentos
- Previsão de conclusão

**Workflow de Status:**
```
ABERTA → DIAGNÓSTICO → EM REPARO → CONCLUÍDA
                              ↓
                          CANCELADA
```

**Prioridades:** Baixa, Normal, Alta, Urgente

**Financeiro integrado:**
- Valor do serviço
- Valor das peças utilizadas (com baixa automática no estoque)
- Desconto
- Total a cobrar
- Forma de pagamento

**Benefício comercial:** Controle profissional de assistências técnicas, com histórico de cada equipamento.

---

### 5. Produtos e Estoque

Catálogo centralizado com controle de estoque automático:

**Cadastro de produtos:**
- Código único por loja
- Nome, descrição e categoria
- Preço de custo e preço de venda
- Unidade de medida (UN, KG, L, CX, MT, etc.)
- Estoque atual e estoque mínimo

**Movimentação automática de estoque:**
- Baixa automática ao fechar uma venda no PDV
- Baixa automática ao usar peças em uma OS
- Entrada automática ao registrar uma compra

**Alertas:**
- Produto com estoque abaixo do mínimo aparece em destaque no dashboard
- Relatório de estoque com posição geral e valor total

**Benefício comercial:** Elimina falta de produtos inesperada e permite reposição proativa.

---

### 6. Clientes (CRM)

Cadastro completo da base de clientes:

- Nome, CPF/CNPJ, telefone, e-mail, endereço
- Histórico de compras vinculado
- Busca rápida no PDV e na criação de OS
- Registro no ato do cadastro (sem formulários externos)
- Associação automática em vendas e contas a receber

**Benefício comercial:** Conhecimento da base de clientes e fidelização.

---

### 7. Financeiro

Módulo financeiro completo, substituindo planilhas e cadernos:

#### 7.1 Contas

- Múltiplas contas: Caixa (obrigatória), contas bancárias adicionais
- Saldo atualizado em tempo real
- **Transferências entre contas** registradas e auditadas

#### 7.2 Contas a Receber

- Criação de cobranças com data de vencimento
- Vinculação com cliente
- **Status automático:** Pendente → Parcial → Paga
- Registro de pagamentos parciais
- **Dashboard de recebimentos:**
  - Total a receber (pendentes + parciais)
  - Total vencido (em atraso)
  - Recebido hoje
  - Recebido no mês

#### 7.3 Despesas

- Registro de despesas operacionais
- Categorias: Aluguel, Energia, Água, Salários, etc.
- Forma de pagamento e conta debitada

#### 7.4 Compras

- Registro de compras a fornecedores
- Itens da compra com entrada automática no estoque
- Nota fiscal e fornecedor

#### 7.5 Movimentações

- Histórico completo de todas as entradas e saídas
- Rastreabilidade: origem de cada movimentação (venda, compra, despesa, transferência)
- Filtros por conta, tipo e período

#### 7.6 Máquinas de Cartão

- Cadastro de múltiplas maquininhas
- Taxa por modalidade:
  - Débito
  - Crédito 1x
  - Crédito 2x
  - Crédito 3x
- Cálculo automático do valor líquido em cada venda

**Benefício comercial:** Visão real do fluxo de caixa, sem surpresas no fechamento do mês.

---

### 8. Relatórios

Análises prontas sem necessidade de exportar dados:

#### Relatório de Vendas
- Total vendido por período (dia, semana, mês)
- Quantidade de vendas
- Ticket médio
- Top 20 produtos mais vendidos
- Distribuição por forma de pagamento
- Receita líquida após taxas de cartão

#### Relatório Financeiro
- Receitas totais (vendas + OS)
- Despesas totais
- Compras realizadas
- **Lucro bruto** do período
- Comparativo entre períodos

#### Relatório de Estoque
- Posição atual de cada produto
- Produtos com estoque crítico (abaixo do mínimo)
- Valor total do estoque (preço de custo)
- Giro de estoque

**Benefício comercial:** Dados para decisão sem contratar analista.

---

### 9. Configurações

Painel de administração da loja:

#### Usuários e Permissões
- Dois perfis: **Administrador** (acesso total) e **Operador** (permissões específicas)
- Permissões granulares por módulo (PDV, Financeiro, Relatórios, etc.)
- Criação, edição e desativação de usuários
- Alteração de senha com segurança

#### Configurações da Loja
- Nome da empresa
- Upload da logo customizada
- Informações de contato

#### Taxas de Pagamento
- Configuração de taxas fixas por forma de pagamento
- Uso integrado no PDV e relatórios

#### Vendedores
- Cadastro de vendedores ativos
- Vinculação nas vendas para comissionamento

---

## Painel Super Admin

Plataforma de gestão para operadores do SaaS:

### Dashboard Administrativo
- Total de lojas (tenants) cadastradas
- Lojas ativas, suspensas e canceladas
- Receita mensal estimada (com base nos planos)
- Últimas lojas cadastradas

### Gestão de Planos
- Criação de planos com preço mensal
- Limite de usuários por plano
- Módulos incluídos (controle granular de acesso)
- Ativação/desativação de planos

### Gestão de Lojas
- Cadastro de novas lojas (tenants)
- Status: ATIVO, SUSPENSO, CANCELADO
- Data de vencimento da assinatura
- Plano contratado
- Gerenciamento de usuários de cada loja

### Gestão de Usuários
- Visualização de todos os usuários de todas as lojas
- Ativação e desativação
- Reset de senhas

---

## Arquitetura Técnica

### Stack de Tecnologia

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.11 + Flask 3.0 |
| Banco de Dados | PostgreSQL 15 |
| ORM (Super Admin) | SQLAlchemy 2.0 + Flask-SQLAlchemy 3.1 |
| Servidor WSGI | Gunicorn 21.2 (multi-worker) |
| Autenticação | bcrypt 4.0 (hash seguro) |
| Rate Limiting | Flask-Limiter 3.5 |
| Containerização | Docker + Docker Compose |
| Proxy Reverso | Nginx |
| Frontend | HTML5 + CSS3 + JavaScript Vanilla |
| Estilização | Tailwind CSS + CSS customizado |
| Ícones | Lucide Icons (SVG) |
| Tipografia | Google Fonts (Sora, Inter, JetBrains Mono) |

### Arquitetura Multi-Tenant

```
┌─────────────────────────────────────────────┐
│              Nginx (Proxy Reverso)           │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
    ┌────▼────┐          ┌────▼──────┐
    │  App    │          │SuperAdmin │
    │ :5678   │          │  :5679    │
    └────┬────┘          └────┬──────┘
         │                    │
         └──────────┬─────────┘
                    │
          ┌─────────▼──────────┐
          │   PostgreSQL 15    │
          │  (Multi-Schema)    │
          └────────────────────┘
```

**Isolamento de dados:** Todas as tabelas possuem `tenant_id`, garantindo que cada loja enxergue apenas seus dados. O isolamento é validado em 100% das queries via decorators de autenticação.

### Banco de Dados — 25+ Tabelas

| Área | Tabelas |
|---|---|
| Multi-Tenant | `tenants`, `planos`, `tenant_usuarios`, `superadmin_usuarios` |
| Produtos | `produtos`, `categorias` |
| Clientes | `clientes` |
| Vendas | `vendas`, `venda_itens` |
| Ordens de Serviço | `ordens_servico`, `os_itens` |
| Compras | `compras`, `compra_itens` |
| Financeiro | `despesas`, `contas`, `movimentacoes`, `contas_receber`, `recebimentos` |
| Cartões | `maquininhas`, `pagamento_taxas` |
| Configuração | `config`, `vendedores` |

### Segurança

- **Senhas:** bcrypt com salt automático (fator de custo 12)
- **Sessões:** HTTP-only cookies, SameSite protection
- **Rate Limiting:** 10 tentativas/min no login, 5/min na troca de senha
- **SQL Injection:** Parametrized queries em 100% das consultas
- **Autorização:** Decorators `@require_auth` e `@require_module` em todas as rotas
- **RBAC:** Controle de acesso baseado em papéis (admin/operador) e plano contratado
- **Migração de hash:** Migração transparente de SHA-256 legado para bcrypt

### Performance

- **29 índices PostgreSQL** em colunas de busca frequente
- **Gunicorn multi-worker** (configurável)
- **Connection pooling** nativo do psycopg2
- Queries otimizadas com LIMIT para listagens longas
- Índices em `tenant_id`, `criado_em`, `status`, `conta_id`

---

## API REST

O sistema expõe uma API REST completa com **100+ endpoints** organizados por domínio:

| Domínio | Endpoints | Descrição |
|---|---|---|
| `/api/auth/` | 5 | Login, logout, perfil, senha |
| `/api/produtos` | 5 | CRUD produtos e categorias |
| `/api/clientes` | 4 | CRUD clientes |
| `/api/vendas` | 4 | PDV e histórico de vendas |
| `/api/os` | 4 | CRUD ordens de serviço |
| `/api/compras` | 2 | Registro de compras |
| `/api/despesas` | 3 | Registro de despesas |
| `/api/contas` | 6 | Contas + transferências |
| `/api/movimentacoes` | 1 | Histórico financeiro |
| `/api/contas_receber` | 6 | A/R com recebimentos |
| `/api/vendedores` | 4 | CRUD vendedores |
| `/api/maquininhas` | 4 | CRUD máquinas de cartão |
| `/api/relatorios/` | 3 | Vendas, financeiro, estoque |
| `/api/config` | 4 | Configurações + logo |
| `/api/usuarios` | 4 | Gestão de usuários |
| `/api/plano/info` | 1 | Info do plano contratado |

---

## Fluxos Operacionais

### Fluxo de Venda (PDV)

```
1. Operador abre o PDV
2. Busca e adiciona produtos ao carrinho
3. Seleciona cliente (ou cria novo na hora)
4. Aplica desconto (opcional)
5. Escolhe forma de pagamento
6. Se cartão: seleciona maquininha + parcelas
7. Sistema calcula taxa automaticamente
8. Confirma venda → número sequencial gerado
9. Estoque é baixado automaticamente
10. Movimentação financeira registrada
11. Recibo disponível para impressão
```

### Fluxo de Ordem de Serviço

```
1. Recepção cria OS com dados do cliente e equipamento
2. Técnico recebe OS com status "ABERTA"
3. Realiza diagnóstico → status "DIAGNÓSTICO"
4. Inicia reparo → status "EM REPARO"
5. Conclui → status "CONCLUÍDA"
6. Cliente paga → registro da forma de pagamento
7. Peças utilizadas baixam automaticamente o estoque
```

### Fluxo de Contas a Receber

```
1. Cria conta a receber com vencimento
2. Status inicial: PENDENTE
3. Cliente paga parcialmente → status PARCIAL
4. Cliente quita → status PAGA
5. Dashboard exibe inadimplência em tempo real
```

---

## Diferenciais Competitivos

### 1. Arquitetura SaaS-Ready
- Multi-tenant nativo: uma instalação serve infinitas lojas
- Isolamento total de dados entre clientes
- Planos configuráveis com módulos e limite de usuários
- Painel de gestão completo para o operador do SaaS

### 2. Completude
- Da venda ao fluxo de caixa sem sair do sistema
- Estoque integrado com vendas, compras e OS
- Financeiro completo: contas, movimentações, A/R, despesas

### 3. Segurança Empresarial
- Autenticação com bcrypt (padrão de mercado)
- Rate limiting nativo
- Controle de acesso granular por módulo
- Auditoria completa de movimentações

### 4. Tecnologia Moderna
- Stack Python/Flask amplamente suportado
- PostgreSQL robusto e confiável
- Docker-ready para deploy em qualquer cloud
- Interface responsiva, acessível de qualquer dispositivo

### 5. Personalização por Loja
- Logo customizada por tenant
- Nome da empresa nas configurações
- Taxas de pagamento configuráveis
- Vendedores cadastráveis

### 6. Baixo Custo de Infraestrutura
- Uma única instalação Docker atende múltiplos clientes
- PostgreSQL eficiente com índices otimizados
- Nginx + Gunicorn para alta disponibilidade

---

## Planos e Módulos (Exemplo de Configuração)

O Super Admin pode criar planos com qualquer combinação de módulos:

| Módulo | Código | Descrição |
|---|---|---|
| Dashboard | `dashboard` | Painel principal e KPIs |
| PDV | `pdv` | Ponto de venda |
| Vendas | `vendas` | Histórico de vendas |
| Ordens de Serviço | `os` | Gestão de manutenções |
| Produtos | `produtos` | Catálogo e estoque |
| Clientes | `clientes` | Cadastro de clientes |
| Financeiro | `financeiro` | Contas, caixa, A/R |
| Relatórios | `relatorios` | Análises e relatórios |
| Configurações | `settings` | Usuários e setup |

**Exemplo de plano Básico:** `dashboard,pdv,produtos,clientes`
**Exemplo de plano Completo:** `dashboard,pdv,vendas,os,produtos,clientes,financeiro,relatorios,settings`

---

## Requisitos de Infraestrutura

### Para Instalação Local / VPS

| Componente | Mínimo | Recomendado |
|---|---|---|
| CPU | 1 vCPU | 2 vCPUs |
| RAM | 1 GB | 2 GB |
| Disco | 10 GB | 20 GB SSD |
| S.O. | Linux (qualquer distro) | Ubuntu 22.04 LTS |
| Docker | 24+ | Latest |
| Docker Compose | 2.0+ | Latest |

### Instalação com Docker Compose

```bash
# 1. Clone o repositório
git clone <repositório>
cd minhaloja

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# 3. Inicie todos os serviços
docker-compose up -d

# 4. Acesse:
# Loja: http://localhost:5678
# Super Admin: http://localhost:5679
```

### Variáveis de Ambiente

```env
DB_URL=postgresql://postgres:SENHA@db:5432/minhaloja_db
SECRET_KEY=<64 chars hex>
SESSION_COOKIE_SECURE=true  # Para produção com HTTPS
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=120
```

---

## Modelo de Dados — Resumo Visual

```
TENANTS (Lojas)
   │
   ├── PLANOS (Plano contratado)
   │
   ├── TENANT_USUARIOS (Usuários da loja)
   │
   ├── PRODUTOS → CATEGORIAS
   │
   ├── CLIENTES
   │
   ├── VENDAS ──────┬── VENDA_ITENS → PRODUTOS
   │                │
   │                └── VENDEDORES, MAQUININHAS
   │
   ├── ORDENS_SERVICO ──── OS_ITENS → PRODUTOS
   │
   ├── COMPRAS ──── COMPRA_ITENS → PRODUTOS
   │
   ├── DESPESAS
   │
   ├── CONTAS ──── MOVIMENTACOES
   │
   ├── CONTAS_RECEBER ──── RECEBIMENTOS
   │
   ├── MAQUININHAS
   │
   ├── PAGAMENTO_TAXAS
   │
   └── CONFIG (Configurações da loja)
```

---

## Telas do Sistema

### Tela de Login
- Design moderno "neural-tech" com efeito glassmorphism
- Animações suaves de entrada
- Validação client-side e server-side
- Redirecionamento automático após login

### Dashboard Principal
- Sidebar colapsável (expandida 240px / comprimida 68px)
- Navegação fluida entre módulos sem reload de página (SPA-like)
- Indicador visual de seção ativa
- Avatar e nome do usuário no topo
- Responsivo para tablets e desktops

### Painel Super Admin
- Template base com sidebar e topbar
- Cards de KPIs com ícones e cores
- Tabelas com ações inline (editar, excluir, ativar)
- Modais para criação e edição
- Design consistente com Tailwind CSS

---

## Glossário Técnico

| Termo | Significado |
|---|---|
| SaaS | Software as a Service — entregue via web, sem instalação |
| Multi-Tenant | Múltiplos clientes compartilham a mesma instalação |
| Tenant | Uma loja/empresa usando o sistema |
| PDV | Ponto de Venda — interface de caixa |
| OS | Ordem de Serviço |
| A/R | Contas a Receber |
| RBAC | Role-Based Access Control — permissões por papel |
| ERP | Enterprise Resource Planning — sistema integrado de gestão |
| bcrypt | Algoritmo de hash seguro para senhas |
| Rate Limiting | Limite de requisições para prevenção de ataques |
| ORM | Object-Relational Mapping — abstração do banco de dados |
| WSGI | Interface padrão Python para servidores web |

---

## Suporte e Extensibilidade

O sistema foi desenvolvido para ser facilmente extensível:

- **Novos módulos:** Adicionar rotas Flask + template + permissão no plano
- **Novas formas de pagamento:** Configuráveis via `pagamento_taxas`
- **Integrações externas:** API REST documentada
- **Customização visual:** Logo e nome por tenant
- **Relatórios personalizados:** Queries PostgreSQL nativas

---

*Documentação gerada para fins comerciais — MinhaLoja SaaS v1.0*
