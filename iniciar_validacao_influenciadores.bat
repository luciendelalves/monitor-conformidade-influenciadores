@echo off
REM Abre a tela do programa, com as cinco abas.
REM
REM CORRIGIDO EM 07/09/2026. Este atalho subia app_validacao_influenciadores.py,
REM que e UMA das cinco telas, e nao a porta de entrada. Quem subia por ali via
REM so a Validacao Regulatoria, com a barra lateral automatica do Streamlit
REM mostrando nome de arquivo em vez de titulo, e sem as secoes nem o botao de
REM sair. O login continuava sendo pedido, porque cada tela confere por conta
REM propria, mas o programa parecia quebrado.
REM
REM A porta de entrada e painel.py, que e quem declara a navegacao.
REM
REM Lembrete: o trabalhador e um programa separado e precisa estar de pe.
REM Suba iniciar_trabalhador.bat primeiro.

cd /d "%~dp0"

REM TEMPORARIO, DESDE 23/09/2026: o auditor precisa testar "Enviar arquivo
REM do post" e o Cadastro nesta maquina, e as duas exigem papel de
REM supervisao ou coordenacao. Nenhum papel estava configurado aqui, o que
REM bloqueava QUALQUER pessoa, nao so ele: a tela dizia "ninguem esta
REM configurado com o papel de supervisao neste servidor".
REM
REM A checagem em si NAO foi tirada do codigo: em vez disso, o auditor
REM passou a ter o papel de supervisao NESTA maquina, com o proprio login
REM dele, entao a acao continua registrada com quem de verdade, nao com um
REM bypass sem identidade.
REM
REM TIRAR ANTES DE OUTRA PESSOA USAR ESTA MAQUINA PARA VALER, ou trocar pelo
REM e-mail de quem for a supervisao real (ver INSTALAR_NO_GCP.md, secao 4).
set EMAILS_SUPERVISAO=auditor@empresa.com

chcp 65001 > nul
REM O TITULO DIZ O QUE A JANELA E E SE PODE FECHAR (07/09/2026), porque as duas
REM janelas do programa eram parecidas e o auditor nunca sabia qual fechar.
title 2 de 2 - TELA do programa (pode fechar, o trabalho continua)
echo Abrindo a tela no navegador.
echo.
echo Esta e a janela da TELA. Fechar ela nao para download nem analise:
echo quem faz isso e a janela do TRABALHADOR.
echo.
py -m streamlit run painel.py
