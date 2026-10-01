@echo off
REM Abre a tela da instalacao do FUTEBOL, na VM, na porta 8502.
REM Criado em 24/09/2026, par de iniciar_painel_marketing.bat. Lembrete:
REM suba iniciar_trabalhador_futebol.bat primeiro.

cd /d "%~dp0"
chcp 65001 > nul

set EMAILS_SUPERVISAO=responsavel.b@empresa.com
set EMAILS_COORDENACAO=responsavel.b@empresa.com

title 2 de 2 - TELA FUTEBOL, porta 8502 (pode fechar, o trabalho continua)
echo Abrindo a tela do FUTEBOL, porta 8502.
echo.
py -m streamlit run painel.py --server.port 8502
