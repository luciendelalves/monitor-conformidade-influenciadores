@echo off
REM Sobe os dois programas de uma vez, na ordem certa, com um clique so.
REM Criado em 09/09/2026, pedido do auditor para facilitar o dia a dia de
REM quem nao e da auditoria: ate aqui eram dois cliques, em dois arquivos
REM diferentes, dentro da pasta do programa, numa ordem que importa. Isso e
REM facil de errar pra quem nao acompanhou a historia dos dois processos.
REM
REM NAO MUDA A ARQUITETURA DE DOIS PROCESSOS. So poupa o clique duplo: cada
REM `start` abaixo abre o SEU proprio `iniciar_*.bat` do jeito de sempre, com
REM o titulo que ja avisa o que e cada janela e se pode fechar.

cd /d "%~dp0"
start "" "iniciar_trabalhador.bat"
REM Um respiro antes da tela, so para a janela do trabalhador aparecer
REM primeiro na tela de quem esta olhando. A tela funciona mesmo se o
REM trabalhador ainda estiver subindo: ela avisa sozinha quando ele nao
REM estiver de pe (ver painel_trabalhador.py).
timeout /t 2 /nobreak > nul
start "" "iniciar_validacao_influenciadores.bat"
