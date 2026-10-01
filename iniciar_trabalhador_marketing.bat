@echo off
REM Sobe o trabalhador da instalacao do MARKETING, na VM.
REM Criado em 24/09/2026, pronto para a migracao (ver INSTALAR_NO_GCP.md,
REM secoes 4 e 8). Existe para nao depender de digitar os e-mails e o layout
REM a mao no dia da subida, que e exatamente o erro que o proprio guia avisa
REM para evitar (digitar errado nao da erro na hora, so quebra depois).
REM
REM Esta janela precisa ficar aberta (ou virar Tarefa Agendada, ver secao 8).
REM O app do Streamlit e o trabalhador sao dois programas separados.

cd /d "%~dp0"
chcp 65001 > nul

REM Decide para qual pasta do Drive os videos vao (fluxo_downloads.LAYOUT_PASTAS).
set LAYOUT_PASTAS_DRIVE=marketing

REM Quem pode corrigir cadastro, reabrir download e enviar arquivo a mao
REM nesta instalacao (INSTALAR_NO_GCP.md, secao 4, tabela de 22/09/2026).
set EMAILS_SUPERVISAO=responsavel.c@empresa.com,responsavel.d@empresa.com
set EMAILS_COORDENACAO=responsavel.c@empresa.com,responsavel.d@empresa.com

title 1 de 2 - TRABALHADOR MARKETING (NAO FECHE, e quem baixa e analisa)

REM O vigia avisa nesta tela se o trabalhador cair (ver vigia_trabalhador.py,
REM 24/09/2026). So uma copia por pasta de instalacao.
start /min "Vigia do trabalhador - Marketing" py vigia_trabalhador.py

echo Subindo o trabalhador da instalacao MARKETING. DEIXE ESTA JANELA ABERTA.
echo.
py trabalhador.py
echo.
echo O trabalhador saiu. Pressione uma tecla para fechar.
pause > nul
