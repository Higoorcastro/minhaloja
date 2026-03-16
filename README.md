# 🏪 GestãoLoja — Sistema de Gestão de Loja v1.0

Sistema completo de gestão para pequenas e médias lojas.
Banco de dados local SQLite — sem servidor externo necessário.

---

## 📦 Módulos

| Módulo | Funcionalidades |
|---|---|
| **Dashboard** | Resumo do dia/mês, gráficos de vendas, top produtos |
| **Ponto de Venda** | PDV com grid de produtos, carrinho, desconto, checkout |
| **Vendas** | Histórico, filtros por data/status, cancelamento |
| **Ordens de Serviço** | Cadastro completo, kanban por status, edição |
| **Produtos** | Cadastro, preço custo/venda, estoque, categorias |
| **Clientes** | Cadastro completo com CPF/CNPJ |
| **Financeiro** | Despesas, compras/entradas de estoque |
| **Relatórios** | Vendas por período, financeiro, posição de estoque |

---

## 🚀 Como Usar no Windows

### Opção 1 — Mais Simples (Recomendada)

**Pré-requisito:** Instalar Python 3.10+ em https://python.org
> ⚠️ Durante a instalação, marque **"Add Python to PATH"**

1. Extraia o ZIP numa pasta qualquer (ex: `C:\GestaoLoja\`)
2. Dê duplo clique em **`INICIAR.bat`**
3. O sistema abrirá automaticamente no seu navegador padrão
4. Para encerrar: feche a janela preta do terminal

### Opção 2 — Executável .EXE (Portátil)

Para gerar um `.exe` único sem precisar do Python instalado:

1. Instale PyInstaller: `pip install pyinstaller`
2. Na pasta do projeto, execute: `pyinstaller loja.spec`
3. O executável será criado em `dist/GestaoLoja.exe`
4. Copie o `.exe` para qualquer lugar e execute diretamente

---

## 💾 Banco de Dados

- O arquivo `loja.db` é criado automaticamente na mesma pasta do programa
- **Faça backup** do `loja.db` periodicamente para não perder dados
- É possível abrir com qualquer visualizador SQLite (ex: DB Browser for SQLite)

---

## 🖥️ Requisitos

- Windows 7 / 8 / 10 / 11
- Python 3.10+ (apenas para a opção com INICIAR.bat)
- ~50MB de espaço em disco
- Navegador web (Chrome, Edge, Firefox)

---

## 📞 Fluxo de Uso Sugerido

1. **Cadastre categorias** no módulo Produtos
2. **Cadastre seus produtos** com preços e estoque inicial
3. **Cadastre clientes** se necessário
4. **Use o PDV** para registrar vendas rápidas
5. **Crie Ordens de Serviço** para serviços técnicos
6. **Lance despesas** no Financeiro mensalmente
7. **Consulte Relatórios** para acompanhar o desempenho

---

*Desenvolvido com Python + Flask + SQLite*
