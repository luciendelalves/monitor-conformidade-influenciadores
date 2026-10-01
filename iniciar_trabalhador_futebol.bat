@echo off
REM Sobe o trabalhador da instalacao do FUTEBOL, na VM.
REM Criado em 24/09/2026, junto com o par de MARKETING. Ver o cabecalho de
REM iniciar_trabalhador_marketing.bat para o motivo de existir; e o mesmo,
REM so muda o layout e os e-mails.

cd /d "%~dp0"
chcp 65001 > nul

set LAYOUT_PASTAS_DRIVE=futebol

REM INSTALAR_NO_GCP.md, secao 4, tabela de 22/09/2026: so a Responsável B por
REM enquanto, unica pessoa desta instalacao.
set EMAILS_SUPERVISAO=responsavel.b@empresa.com
set EMAILS_COORDENACAO=responsavel.b@empresa.com

title 1 de 2 - TRABALHADOR FUTEBOL (NAO FECHE, e quem baixa e analisa)

start /min "Vigia do trabalhador - Futebol" py vigia_trabalhador.py

echo Subindo o trabalhador da instalacao FUTEBOL. DEIXE ESTA JANELA ABERTA.
echo.
py trabalhador.py
echo.
echo O trabalhador saiu. Pressione uma tecla para fechar.
pause > nul
