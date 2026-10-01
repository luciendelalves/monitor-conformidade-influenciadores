# -*- coding: utf-8 -*-
"""
Tira a coluna "Link do Vídeo" da planilha da FILA de downloads.

POR QUE (31/08/2026)

Decidido pelo auditor olhando a planilha. A coluna era escrita pelo programa
depois de organizar, exibida de volta pelo programa na tela, e NUNCA usada para
decidir nada. O mesmo endereço fica em dois outros lugares:

    na Monitoramento    na coluna LINK da linha criada para a peça
    no registro em CSV  e é dele que a tela lê "Últimos organizados"

É o mesmo caso da LINK_ARQUIVO que saiu da Monitoramento em 30/08, pelo mesmo
motivo e com a mesma solução.

COMO, E POR QUE NÃO COPIANDO VALORES

Usa deleteDimension, que é a operação de "apagar coluna" do próprio Google.
Copiar valores de uma coluna para a outra pareceria equivalente e não é: perde
formato, largura, cor e validação, e transforma link clicável em texto. Foi a
lição da migração de 30/08, pega no ensaio antes de aplicar.

DEPOIS DESTA MIGRAÇÃO o layout da fila fica:

    A Influenciador   B Link   C Status   D Ciclo   E Marca

Confere primeiro e só escreve com --aplicar. Guarda cópia do bloco antigo em
arquivo, para dar para voltar atrás.

Uso:
    py migrar_tirar_coluna_destino_da_fila.py            (só mostra o que faria)
    py migrar_tirar_coluna_destino_da_fila.py --aplicar  (escreve)
"""
import json
import os
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo
import sheets_client

# Como era ANTES desta migração. Não usa fluxo.COL_FILA de propósito: aquele
# já está com o layout NOVO, e este script precisa saber o antigo.
ANTES = ["Influenciador", "Link", "Status", "Link do Vídeo", "Ciclo", "Marca"]
LETRA_QUE_SAI = "D"
INDICE_QUE_SAI = 3  # base zero, ou seja, a quarta coluna


def main():
    aplicar = "--aplicar" in sys.argv

    planilha = fluxo._planilha_fila_id()
    if not planilha:
        print("Não achei o identificador da planilha da fila. Nada feito.")
        return
    print(f"Planilha da fila: {planilha}")
    print(f"Aba: {fluxo.ABA_FILA}")
    print()

    # --- confere que a planilha ainda está no layout ANTIGO ---
    cabecalho = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_FILA}'!A1:H1").execute()
    ).get("values", [[]])
    atual = [str(c).strip() for c in (cabecalho[0] if cabecalho else [])]
    print(f"cabeçalho hoje : {atual}")
    print(f"cabeçalho antes: {ANTES}")
    print()

    if len(atual) <= INDICE_QUE_SAI:
        print("A planilha não tem a coluna que esta migração apaga. "
              "Provavelmente já foi aplicada. Nada feito.")
        return
    if "vídeo" not in atual[INDICE_QUE_SAI].lower() and \
       "video" not in atual[INDICE_QUE_SAI].lower():
        print(f"RECUSADO: a coluna {LETRA_QUE_SAI} se chama "
              f"{atual[INDICE_QUE_SAI]!r}, e eu esperava a do link do vídeo. "
              f"Alguém mexeu no layout. Confira à mão antes de rodar isto.")
        return

    # --- guarda cópia do que vai embora ---
    bloco = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_FILA}'!A1:H1000",
            valueRenderOption="FORMULA").execute()
    ).get("values", [])
    linhas_com_dado = [l for l in bloco if any(str(c).strip() for c in l)]
    print(f"linhas com dado: {len(linhas_com_dado)}")
    print()
    print(f"o que sai da coluna {LETRA_QUE_SAI} (primeiras 5):")
    for l in linhas_com_dado[1:6]:
        valor = l[INDICE_QUE_SAI] if len(l) > INDICE_QUE_SAI else ""
        print(f"   {str(valor)[:74]}")
    print()

    if not aplicar:
        print("Nada foi alterado. Para valer, rode de novo com --aplicar")
        return

    copia = os.path.join(
        BASE, "teste_watch_folder",
        f"copia_fila_antes_de_tirar_destino_{datetime.now():%Y%m%d_%H%M%S}.json")
    os.makedirs(os.path.dirname(copia), exist_ok=True)
    with open(copia, "w", encoding="utf-8") as f:
        json.dump({"quando": datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "planilha": planilha, "aba": fluxo.ABA_FILA,
                   "cabecalho": atual, "linhas": linhas_com_dado},
                  f, ensure_ascii=False, indent=2)
    print(f"cópia de segurança: {copia}")

    aba_id = sheets_client.id_da_aba(planilha, fluxo.ABA_FILA)
    if aba_id is None:
        print(f"Não achei a aba {fluxo.ABA_FILA!r}. Nada alterado.")
        return

    sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().batchUpdate(
            spreadsheetId=planilha,
            body={"requests": [{"deleteDimension": {"range": {
                "sheetId": aba_id, "dimension": "COLUMNS",
                "startIndex": INDICE_QUE_SAI,
                "endIndex": INDICE_QUE_SAI + 1}}}]}).execute())

    print(f"Coluna {LETRA_QUE_SAI} apagada. O Google moveu as seguintes para a "
          f"esquerda, com formato e tudo.")
    print()
    depois = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_FILA}'!A1:H1").execute()
    ).get("values", [[]])
    print(f"cabeçalho agora: {[str(c).strip() for c in (depois[0] if depois else [])]}")
    print()
    print("REINICIE os dois programas: o código já espera o layout novo, mas o "
          "que está em execução carregou o antigo.")


if __name__ == "__main__":
    main()
