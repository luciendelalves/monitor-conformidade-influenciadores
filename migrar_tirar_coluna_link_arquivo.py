# -*- coding: utf-8 -*-
"""
Migração de 29/08/2026: tira a coluna LINK_ARQUIVO da Monitoramento.

POR QUE

Nas linhas criadas pela automação, o link do arquivo já ia na coluna LINK, e
era repetido na LINK_ARQUIVO logo depois da DATA_DOWNLOAD. O mesmo endereço
aparecia duas vezes lado a lado na planilha. Apontado pelo auditor olhando a
planilha de teste.

O que a coluna também fazia, e foi substituído: ela era o gatilho da fila de
validação. Esse papel passou para a coluna SITUACAO, que já carregava a mesma
informação (ver fluxo_downloads.tem_arquivo_para_analisar).

O QUE ESTE SCRIPT FAZ

Apaga a coluna X, e com isso o bloco da automação anda uma casa para a
esquerda:

    antes:  W DATA_DOWNLOAD | X LINK_ARQUIVO | Y SITUACAO | Z VALIDACAO | AA EVIDENCIA | AB VALIDADO_EM
    depois: W DATA_DOWNLOAD | X SITUACAO     | Y VALIDACAO | Z EVIDENCIA | AA VALIDADO_EM

Apaga a coluna de verdade, em vez de copiar valor de uma para a outra. Isso
foi decidido depois de simular a cópia e ver o estrago: copiar move o
conteúdo, mas NÃO move o formato da célula. A VALIDADO_EM guarda data e hora,
que por baixo é um número, então ela chegaria na coluna vizinha como 46263,77
em vez de 29/08/2026 18:25. O mesmo valeria para as cores já aplicadas na
planilha de teste. Apagando a coluna, o próprio Google desloca conteúdo,
formato e cor juntos.

Antes de apagar, guarda em arquivo o conteúdo do bloco lido como FÓRMULA, não
como texto exibido: a coluna EVIDENCIA guarda fórmulas de HYPERLINK, e uma
cópia de segurança com o texto exibido no lugar delas não serviria para
restaurar nada.

SEGURANÇA

Roda só na planilha de TESTE, e recusa rodar em qualquer outra. Mostra o que
vai fazer e pede confirmação antes de escrever. Guarda uma cópia do bloco
antigo em arquivo, para dar para voltar atrás se algo sair errado.

Uso:
    py migrar_tirar_coluna_link_arquivo.py            (só mostra o que faria)
    py migrar_tirar_coluna_link_arquivo.py --aplicar  (escreve)
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

MONITORAMENTO_REAL = "13uLhupENDl6bSHfRioaQz0mcZUio_IOojp1_c1CFhQU"

# Como era antes desta migração. Não usa fluxo.COL_MON de propósito: aquele
# arquivo já está com o layout NOVO, e este script precisa saber o antigo.
ANTES = ["DATA_DOWNLOAD", "LINK_ARQUIVO", "SITUACAO", "VALIDACAO", "EVIDENCIA", "VALIDADO_EM"]
FAIXA_ANTIGA = "W:AB"
FAIXA_NOVA = "W:AA"
COLUNA_QUE_SAI = 1  # posição da LINK_ARQUIVO dentro do bloco acima


def ler_bloco(planilha, ultima_linha):
    """Lê o bloco inteiro como FÓRMULA, não como texto exibido."""
    return sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_MONITORAMENTO}'!W1:AB{ultima_linha}",
            valueRenderOption="FORMULA",
        ).execute()
    ).get("values", [])


def main():
    aplicar = "--aplicar" in sys.argv

    planilha = fluxo._planilha_monitoramento_id()
    if not planilha:
        print("Não achei o identificador da Monitoramento de teste. Nada feito.")
        return
    if planilha == MONITORAMENTO_REAL:
        print("RECUSADO: este é o identificador da Monitoramento REAL do Marketing. "
              "Esta migração só roda na cópia de teste.")
        return

    print(f"Planilha: {planilha}")

    # Descobre até onde há dado, olhando a coluna do influenciador.
    coluna_handle = fluxo.letra_da_coluna(fluxo.COL_MON["handle"])
    handles = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_MONITORAMENTO}'!{coluna_handle}1:{coluna_handle}20000",
        ).execute()
    ).get("values", [])
    ultima_linha = max(len(handles), 1)
    print(f"Linhas com dado: {ultima_linha} (incluindo o cabeçalho)")

    bloco = ler_bloco(planilha, ultima_linha)
    if not bloco:
        print("O bloco da automação está vazio. Nada a migrar.")
        return

    novo = []
    for linha in bloco:
        preenchida = list(linha) + [""] * (len(ANTES) - len(linha))
        novo.append([v for i, v in enumerate(preenchida[:len(ANTES)]) if i != COLUNA_QUE_SAI])

    # Mostra o cabeçalho e as linhas que têm algum conteúdo. Linha vazia não
    # ensina nada sobre a migração e esconderia as que importam.
    com_conteudo = [(i + 1, antiga, nova)
                    for i, (antiga, nova) in enumerate(zip(bloco, novo))
                    if any(str(c).strip() for c in nova)]
    print()
    print(f"{len(com_conteudo) - 1} linha(s) de dado no bloco, além do cabeçalho.")
    print()
    print("ANTES (o que sai está marcado com [x]):")
    for numero, antiga, _ in com_conteudo[:12]:
        campos = list(antiga) + [""] * (len(ANTES) - len(antiga))
        mostrar = " | ".join(
            (f"[x]{str(c)[:26]}" if i == COLUNA_QUE_SAI else str(c)[:26])
            for i, c in enumerate(campos[:len(ANTES)]))
        print(f"  linha {numero:>3}: {mostrar}")
    print()
    print("DEPOIS:")
    for numero, _, nova in com_conteudo[:12]:
        print(f"  linha {numero:>3}: " + " | ".join(str(c)[:26] for c in nova))

    if not aplicar:
        print()
        print("Nada foi escrito. Para aplicar de verdade, rode de novo com --aplicar")
        return

    # Confere que a coluna a apagar é mesmo a LINK_ARQUIVO, e não outra coisa.
    # Sem isto, rodar o script duas vezes apagaria a SITUACAO na segunda vez.
    titulo_atual = str(bloco[0][COLUNA_QUE_SAI]).strip() if len(bloco[0]) > COLUNA_QUE_SAI else ""
    if titulo_atual != "LINK_ARQUIVO":
        print()
        print(f"RECUSADO: a coluna X se chama {titulo_atual!r}, não 'LINK_ARQUIVO'. "
              "A migração provavelmente já foi feita. Nada alterado.")
        return

    # Cópia de segurança do bloco antigo, antes de qualquer escrita.
    copia = os.path.join(BASE, "teste_watch_folder",
                         f"backup_bloco_automacao_{datetime.now():%Y%m%d_%H%M%S}.json")
    with open(copia, "w", encoding="utf-8") as f:
        json.dump({"planilha": planilha, "faixa": FAIXA_ANTIGA,
                   "colunas": ANTES, "valores": bloco}, f, ensure_ascii=False, indent=2)
    print()
    print(f"Cópia do bloco antigo guardada em {copia}")

    aba_id = sheets_client.id_da_aba(planilha, fluxo.ABA_MONITORAMENTO)
    if aba_id is None:
        print(f"Não achei a aba {fluxo.ABA_MONITORAMENTO!r}. Nada alterado.")
        return

    # A coluna X é a de número 24, e a API conta a partir do zero.
    sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().batchUpdate(
            spreadsheetId=planilha,
            body={"requests": [{"deleteDimension": {"range": {
                "sheetId": aba_id, "dimension": "COLUMNS",
                "startIndex": 23, "endIndex": 24,
            }}}]},
        ).execute(),
        repetivel=False,  # repetir apagaria a coluna seguinte
    )
    print("Coluna X (LINK_ARQUIVO) apagada. O resto do bloco andou uma casa para a esquerda.")
    print()
    print("Confira na planilha antes de seguir. O histórico de versões do Google "
          "também permite voltar atrás.")
    print("Reinicie o app e o trabalhador para o código novo valer.")


if __name__ == "__main__":
    main()
