@echo off
title Sistema de Loja - GestaoLoja
color 0A

echo ============================================
echo    SISTEMA DE GESTAO DE LOJA v1.1
echo ============================================
echo.
echo  Acesso inicial:
echo    Login: admin
echo    Senha: admin123
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Por favor instale o Python em:
    echo https://www.python.org/downloads/
    echo.
    echo Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

echo [OK] Python encontrado

if not exist ".venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
    echo [INFO] Instalando Flask...
    .venv\Scripts\pip install flask --quiet
    echo [OK] Dependencias instaladas
)

echo [INFO] Iniciando servidor...
echo [INFO] O sistema abrira no navegador automaticamente.
echo.
echo Para encerrar, feche esta janela ou pressione CTRL+C
echo ============================================
echo.

.venv\Scripts\python app.py
pause
