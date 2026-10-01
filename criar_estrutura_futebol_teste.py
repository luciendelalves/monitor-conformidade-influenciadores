# -*- coding: utf-8 -*-
"""
Cria "Divulgações" e as quatro pastas de bet dentro da raiz de teste do
layout futebol, usando a PRÓPRIA credencial do programa (drive_file_token.json
desta máquina), para essas pastas ficarem visíveis para o programa depois.

POR QUE ESTE SCRIPT EXISTE (21/09/2026)

As mesmas pastas foram criadas uma vez pelo conector de Drive do Claude, e
o programa não as viu ("FALTA PASTA NO DRIVE"), mesmo elas existindo e
aparecendo normalmente no navegador. O motivo: o token do programa
(escopo drive.file) só vê o que a PRÓPRIA autorização dele criou ou abriu
antes. Pasta feita por outra ferramenta, mesmo na mesma conta, fica
invisível para ele. Já tinha acontecido isso neste projeto antes.

A saída é criar de novo, mas por dentro do programa, com o token de quem
vai USAR o programa depois. Por isso este script precisa ser rodado NA
MÁQUINA de quem vai usar (a Responsável B), com a pasta `_drive_credenciais`
dela já autorizada (passo 7.4 do INSTALAR.md já feito).

Rodar, dentro de producao\\analises:

    py criar_estrutura_futebol_teste.py

É seguro rodar mais de uma vez: `obter_ou_criar_pasta` procura antes de
criar, então não duplica.
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import drive_client_upload

# A raiz de teste do layout futebol (TESTE_LAYOUT_FUTEBOL_SCRIPT_12set).
RAIZ_TESTE = "1JaQXsUOrLlv8ORfsXiqbwTWzEfWKdWKM"

BETS = ["01. EDS", "02. ONA", "03. LOTTU", "04. EDSCAP"]


def rodar():
    print("Criando (ou achando) \"Divulgações\" dentro da raiz de teste...")
    id_divulgacoes = drive_client_upload.obter_ou_criar_pasta("Divulgações", RAIZ_TESTE)
    print(f"  Divulgações: {id_divulgacoes}")

    for bet in BETS:
        id_bet = drive_client_upload.obter_ou_criar_pasta(bet, id_divulgacoes)
        print(f"  {bet}: {id_bet}")

    print()
    print("Pronto. Coloque este id em teste_watch_folder\\drive_teste_pasta_raiz_id.txt:")
    print(f"  {id_divulgacoes}")


if __name__ == "__main__":
    rodar()
