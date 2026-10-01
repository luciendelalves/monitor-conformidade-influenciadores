# -*- coding: utf-8 -*-
"""
A automação NÃO escreve CRONOGRAMA nem PAGAMENTO. Nunca.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

Este teste já provou o contrário. Por um dia, toda linha nova nascia com
PAGAMENTO = "Pendente", e havia função e tela para editar as duas colunas pelo
programa. O auditor decidiu voltar atrás, com estas palavras:

    "CRONOGRAMA e PAGAMENTO continuam manuais na planilha nas linhas
    individuais, cada entrega de video por enquanto vai continuar sendo
    preenchida a mão como não pago ou pago, cronograma sim ou não"

Então o arquivo foi invertido: onde ele exigia a escrita, agora exige a AUSÊNCIA
dela. Ele existe para que a decisão não se perca, porque a escrita é fácil de
reintroduzir sem querer, e ninguém perceberia: uma célula preenchida a mais não
quebra nada visivelmente, só passa por cima do trabalho de quem preenche à mão.

A DIREÇÃO DE LONGO PRAZO CONTINUA SENDO a planilha virar banco de dados e o
programa ser a única interface. Quando isso voltar, este arquivo é o lugar de
inverter de novo, e o código removido está no histórico do Git.

Rodar:

    py testes\teste_automacao_nao_escreve_cronograma_e_pagamento.py
"""
import os
import re
import sys
import types

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. nao existe funcao para escrever essas colunas ---")
    for nome in ("corrigir_coluna_na_monitoramento",
                 "corrigir_pagamento_na_monitoramento",
                 "corrigir_cronograma_na_monitoramento"):
        conferir(not hasattr(fluxo, nome),
                 f"{nome} nao existe mais",
                 "foi removida quando as colunas voltaram a ser manuais")
    conferir(not hasattr(fluxo, "VOCABULARIO_MEDIDO"),
             "a lista de valores permitidos para escrita tambem saiu")
    conferir(not hasattr(fluxo, "PAGAMENTO_PADRAO_NA_CRIACAO"),
             "e o valor padrao de PAGAMENTO na criacao saiu")

    print()
    print("--- 2. a correcao de CICLO nao foi afetada ---")
    # Ela e outra coisa: corrige erro de LEITURA da automacao, e continua sendo
    # a unica escrita por escolha humana na Monitoramento. Se este teste falhar,
    # a remocao pegou junto algo que nao devia.
    conferir(hasattr(fluxo, "corrigir_ciclo_na_monitoramento"),
             "corrigir_ciclo_na_monitoramento continua existindo")

    print()
    print("--- 3. as duas colunas continuam sendo LIDAS ---")
    # Ler nao e escrever. O programa mostra as duas na tabela do Monitoramento e
    # na contagem do Financeiro, e para isso precisa da posicao delas.
    conferir(fluxo.COL_MON.get("cronograma") == 17,
             "CRONOGRAMA continua mapeada na coluna Q, para leitura",
             str(fluxo.COL_MON.get("cronograma")))
    conferir(fluxo.COL_MON.get("pagamento") == 19,
             "PAGAMENTO continua mapeada na coluna S, para leitura",
             str(fluxo.COL_MON.get("pagamento")))

    print()
    print("--- 4. criar linha deixa as duas VAZIAS ---")
    escritos = {}
    # ESCRITA_FEITA E O GET QUE REFLETE O QUE FOI ESCRITO (18/09/2026): desde
    # que registrar_na_monitoramento passou a RELER a própria linha depois de
    # escrever, para pegar colisão entre instalações em máquinas diferentes
    # (ver o comentário "CONFERE SE A ESCRITA CONTINUA DE PÉ" no
    # fluxo_downloads.py), o dublê precisa simular isso: antes da escrita,
    # get() devolve vazio (linha nova, como sempre simulou); depois da
    # escrita, get() passa a devolver o valor da coluna ARQUIVO que foi
    # gravado, senão a confirmação vê "nada gravado" e trata como colisão
    # sempre, mesmo sem concorrência nenhuma. Foi assim que este teste
    # quebrou ao rodar a suíte inteira depois da trava entre máquinas.
    escrita_feita = {"sim": False}

    class SheetsFalso:
        @staticmethod
        def executar(fn):
            return fn()

        class _Servico:
            class _SS:
                @staticmethod
                def values():
                    class _V:
                        @staticmethod
                        def get(spreadsheetId, range):
                            class _Exec:
                                @staticmethod
                                def execute():
                                    if not escrita_feita["sim"]:
                                        return {"values": []}
                                    linha_escrita = escritos.get("values", [[]])[0]
                                    indice = fluxo.COL_MON["arquivo"] - 1
                                    if len(linha_escrita) > indice:
                                        return {"values": [[linha_escrita[indice]]]}
                                    return {"values": []}
                            return _Exec()

                        @staticmethod
                        def update(spreadsheetId, range, body, valueInputOption=None):
                            class _Exec:
                                @staticmethod
                                def execute():
                                    escritos["values"] = body.get("values")
                                    escrita_feita["sim"] = True
                                    return {}
                            return _Exec()
                    return _V()

            @staticmethod
            def spreadsheets():
                return SheetsFalso._Servico._SS()

        @staticmethod
        def get_service():
            return SheetsFalso._Servico()

    falso = types.ModuleType("sheets_client")
    falso.executar = SheetsFalso.executar
    falso.get_service = SheetsFalso.get_service
    import sheets_client as _de_verdade
    falso._neutralizar_formula = _de_verdade._neutralizar_formula
    # _TRAVA_DA_API ENTROU EM 16/09/2026, quando registrar_na_monitoramento
    # passou a segurar a trava da leitura até a escrita (ver o comentário no
    # próprio fluxo_downloads.py). O dublê precisa da mesma trava real: é um
    # RLock comum, sem estado próprio deste teste, só precisa existir.
    falso._TRAVA_DA_API = _de_verdade._TRAVA_DA_API
    antigo = sys.modules.get("sheets_client")
    sys.modules["sheets_client"] = falso

    guardado_id = fluxo._planilha_monitoramento_id
    fluxo._planilha_monitoramento_id = lambda: "planilha_de_mentira"
    guardado_cab = fluxo.garantir_cabecalhos_automacao
    fluxo.garantir_cabecalhos_automacao = lambda planilha: None
    guardado_al = fluxo.dados_de_cadastro_para_a_linha
    fluxo.dados_de_cadastro_para_a_linha = lambda handle, cabecalho: ({}, "")
    try:
        fluxo.registrar_na_monitoramento(
            "@fulano", None, "1", "https://drive.google.com/x", marca="LOTTU",
            tipo="STORIES")
        valores = escritos.get("values", [[]])[0]
        for chave in ("cronograma", "pagamento"):
            i = fluxo.COL_MON[chave] - 1
            vazia = len(valores) <= i or not str(valores[i]).strip()
            conferir(vazia, f"{chave.upper()} nasce VAZIA na linha nova",
                     str(valores[i]) if len(valores) > i else "(fora da linha)")
    finally:
        fluxo._planilha_monitoramento_id = guardado_id
        fluxo.garantir_cabecalhos_automacao = guardado_cab
        fluxo.dados_de_cadastro_para_a_linha = guardado_al
        if antigo is not None:
            sys.modules["sheets_client"] = antigo
        else:
            sys.modules.pop("sheets_client", None)

    print()
    print("--- 5. nenhuma tela escreve nessas colunas ---")
    for nome in sorted(os.listdir(os.path.join(BASE, "pages"))):
        if not nome.endswith(".py"):
            continue
        with open(os.path.join(BASE, "pages", nome), encoding="utf-8") as f:
            tela = f.read()
        for proibido in ("corrigir_coluna_na_monitoramento",
                         "corrigir_pagamento_na_monitoramento",
                         "corrigir_cronograma_na_monitoramento"):
            # o nome pode aparecer em COMENTARIO explicando que foi removido;
            # o que nao pode e uma CHAMADA, com parentese aberto.
            conferir(f"{proibido}(" not in tela,
                     f"{nome} nao chama {proibido}")


if __name__ == "__main__":
    print("=" * 74)
    print("  A automacao NAO escreve CRONOGRAMA nem PAGAMENTO")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
