@echo off
REM Baixador de videos - Auditoria Interna EGB
REM Roda na maquina da pessoa, usando a sessao do Firefox dela.
REM Nao tem credencial nenhuma da auditoria dentro.

cd /d "%~dp0"
chcp 65001 > nul
title Baixador de videos - Auditoria EGB
py baixador.py
