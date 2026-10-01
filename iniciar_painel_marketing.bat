@echo off
REM Abre a tela da instalacao do MARKETING, na VM, na porta 8501.
REM Criado em 24/09/2026 (ver INSTALAR_NO_GCP.md, secoes 3 e 4: cada
REM instalacao precisa da sua propria porta, senao as duas telas disputam a
REM mesma). Lembrete: suba iniciar_trabalhador_marketing.bat primeiro.

cd /d "%~dp0"
chcp 65001 > nul

set EMAILS_SUPERVISAO=responsavel.c@empresa.com,responsavel.d@empresa.com
set EMAILS_COORDENACAO=responsavel.c@empresa.com,responsavel.d@empresa.com

title 2 de 2 - TELA MARKETING, porta 8501 (pode fechar, o trabalho continua)
echo Abrindo a tela do MARKETING, porta 8501.
echo.
py -m streamlit run painel.py --server.port 8501
