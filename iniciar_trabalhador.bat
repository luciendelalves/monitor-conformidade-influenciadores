@echo off
REM Sobe o trabalhador, que e quem baixa e analisa de verdade.
REM Criado em 29/08/2026, junto com a fila de trabalho.
REM
REM Esta janela precisa ficar aberta. Fechar ela para o trabalho: o que estava
REM em andamento volta para a fila e roda de novo na proxima vez que subir.
REM
REM O app do Streamlit e o trabalhador sao dois programas separados de
REM proposito. O app so mostra e enfileira; quem executa e este aqui.
REM
REM SOBE TAMBEM UM VIGIA, MINIMIZADO, DESDE 24/09/2026: avisa numa janela do
REM Windows se o trabalhador cair sem ninguem ter a tela do app aberta para
REM notar (ver vigia_trabalhador.py). So uma copia roda por maquina; subir o
REM trabalhador de novo no mesmo dia nao empilha vigia.

cd /d "%~dp0"
REM Coloca a janela em UTF-8 para os acentos aparecerem certos.
chcp 65001 > nul
start /min "Vigia do trabalhador" py vigia_trabalhador.py
REM O TITULO DIZ O QUE A JANELA E E SE PODE FECHAR (07/09/2026), porque as duas
REM janelas do programa eram parecidas e o auditor nunca sabia qual fechar.
title 1 de 2 - TRABALHADOR (NAO FECHE, e quem baixa e analisa)
echo Subindo o trabalhador. DEIXE ESTA JANELA ABERTA.
echo.
echo Esta e a janela que baixa e analisa. Fechar ela para o trabalho no meio.
echo Para encerrar sem cortar trabalho, use o botao na tela do programa.
echo.
py trabalhador.py
echo.
echo O trabalhador saiu. Pressione uma tecla para fechar.
pause > nul
