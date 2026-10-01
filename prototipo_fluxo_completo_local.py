# -*- coding: utf-8 -*-
"""
Linha de comando do fluxo de download/organização de vídeos (FASE 2: fila de
teste no Sheets + pasta de TESTE real no Drive). A lógica de verdade mora em
fluxo_downloads.py — este arquivo é só o wrapper de terminal, mesmo padrão do
resto do projeto (o app Streamlit usa o MESMO módulo, página "Downloads e
Organização").

Uso:
    py prototipo_fluxo_completo_local.py            (fila + watch)
    py prototipo_fluxo_completo_local.py so-watch   (só a pasta monitorada)
"""
import sys

import fluxo_downloads as fluxo


def main():
    so_watch = "so-watch" in sys.argv
    log = []
    if not so_watch:
        log += fluxo.processar_fila()
    log += fluxo.processar_watch()
    ok = sum(1 for l in log if l["status"] == "OK")
    print(f"\nResumo: {len(log)} item(ns) processado(s), {ok} organizados na pasta de TESTE do Drive. "
          f"Log: {fluxo.ARQUIVO_LOG}")


if __name__ == "__main__":
    main()
