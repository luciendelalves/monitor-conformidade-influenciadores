# -*- coding: utf-8 -*-
"""
O fechamento de ciclo vai para planilha própria, e o arquivo local é a rede.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

O auditor perguntou onde a justificativa ia parar: "essa justificativa vai pra
algum lugar na planilha ou só na mensagem do whatsapp?". A resposta era ruim:
texto do WhatsApp e um CSV nesta máquina. Mensagem de WhatsApp não é registro de
auditoria (não dá para filtrar, contar nem auditar depois), e CSV local vive numa
máquina só, o que deixou de ser aceitável no momento em que uma pessoa do
Marketing passou a testar o programa na máquina dela.

PLANILHA PRÓPRIA, NÃO ABA DA MONITORAMENTO, decidido com ele. As quatro razões
estão em registro_fechamentos.py: grão diferente (uma linha por ciclo, não por
post), dono diferente (conclusão da auditoria, não dado operacional do
Marketing), público diferente (o Financeiro precisa ler os fechamentos sem ver
todo o dado por post) e sobrevivência (a Monitoramento em uso é cópia de teste).

O QUE ESTE TESTE PROTEGE, e cada item já foi um erro possível:

  - gravar nos DOIS lugares, não num só
  - o arquivo local NUNCA depender da planilha para funcionar
  - falha de planilha não derrubar o fechamento nem sumir calada
  - justificativa que começa com "=" ou "-" não virar fórmula
  - o registro só ACRESCENTAR, nunca reescrever linha existente

Rodar:

    py testes\teste_registro_de_fechamentos.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import registro_fechamentos as rf

    CAMPOS = ("quando", "quem", "influenciador", "ciclo", "justificativa",
              "justificativa_pagamento")

    print("--- 1. a planilha e PROPRIA, nao a Monitoramento ---")
    import fluxo_downloads as fluxo
    conferir(rf.NOME_DO_ARQUIVO_ID != os.path.basename(fluxo.ARQUIVO_MONITORAMENTO_ID),
             "o identificador e um arquivo diferente do da Monitoramento",
             "misturar os dois faria o fechamento gravar dentro do dado "
             "operacional do Marketing")
    conferir(rf.ABA == "Fechamentos",
             "e a aba tem nome proprio", rf.ABA)

    print()
    print("--- 2. a letra da coluna e calculada certo ---")
    # Bobo, mas se errar aqui o cabecalho e a escrita apontam para faixas
    # diferentes e a planilha sai torta sem erro nenhum.
    for numero, esperado in ((1, "A"), (18, "R"), (26, "Z"), (27, "AA")):
        conferir(rf._letra(numero) == esperado,
                 f"coluna {numero} e {esperado}", rf._letra(numero))

    print()
    print("--- 3. os titulos sao em texto de gente ---")
    # "justificativa_pagamento" ERA O EXEMPLO AQUI, e saiu de _titulo() em
    # 09/09/2026 junto com o rádio "já foi pago?" que o alimentava (ver
    # pages/3_Financeiro.py). "justificativa" continua com título proprio, e
    # prova o mesmo comportamento: campo interno vira nome de gente.
    conferir(rf._titulo("justificativa") == "JUSTIFICATIVA DA ENTREGA",
             "campo interno vira titulo legivel",
             rf._titulo("justificativa"))
    conferir("_" not in rf._titulo("pecas_sem_evidencia"),
             "e nenhum titulo sai com nome de variavel",
             rf._titulo("pecas_sem_evidencia"))

    print()
    print("--- 4. sem planilha configurada, avisa em vez de estourar ---")
    guardado = rf.planilha_id
    rf.planilha_id = lambda: ""
    try:
        gravou, motivo = rf.gravar({"quando": "x"}, CAMPOS)
        conferir(gravou is False, "nao grava sem planilha")
        conferir(rf.NOME_DO_ARQUIVO_ID in motivo,
                 "e o motivo diz qual arquivo falta", motivo[:80])
        conferir(rf.ler(CAMPOS) == [],
                 "e a leitura devolve lista vazia, nao erro")
    finally:
        rf.planilha_id = guardado

    print()
    print("--- 5. falha da planilha NAO derruba, e NAO passa calada ---")
    # E o ponto central. Se a rede cair no meio do fechamento, o registro nao
    # pode se perder nem a pessoa concluir que foi para a planilha.
    import types
    falso = types.ModuleType("sheets_client")

    def explode(*a, **k):
        raise RuntimeError("rede fora")

    falso.executar = explode
    falso.get_service = explode
    falso.adicionar_linhas = explode
    antigo = sys.modules.get("sheets_client")
    sys.modules["sheets_client"] = falso
    guardado2 = rf.planilha_id
    rf.planilha_id = lambda: "planilha_de_mentira"
    try:
        gravou, motivo = rf.gravar({"quando": "x"}, CAMPOS)
        conferir(gravou is False, "falha de rede devolve False, sem levantar erro")
        conferir("rede fora" in motivo,
                 "e devolve o motivo real, para a tela poder dizer", motivo[:60])
    finally:
        rf.planilha_id = guardado2
        if antigo is not None:
            sys.modules["sheets_client"] = antigo
        else:
            sys.modules.pop("sheets_client", None)

    print()
    print("--- 6. a tela grava nos DOIS e conta qual deu certo ---")
    with open(os.path.join(BASE, "pages", "3_Financeiro.py"),
              encoding="utf-8") as f:
        tela = f.read()
    conferir("registro_fechamentos.gravar" in tela,
             "a tela grava na planilha")
    conferir("_gravar_no_arquivo(registro)" in tela,
             "e tambem no arquivo local")
    # A ORDEM IMPORTA: local primeiro, porque ele nao falha por rede.
    corpo = tela.split("def gravar_fechamento(")[1][:600]
    conferir(corpo.index("_gravar_no_arquivo") < corpo.index("registro_fechamentos.gravar"),
             "e o arquivo local vem PRIMEIRO",
             "se a planilha falhar depois, o registro ja existe em algum lugar")
    conferir("fechamento_na_planilha" in tela,
             "a tela guarda se a planilha aceitou")
    conferir("so no arquivo local desta maquina" in tela.lower()
             or "só no arquivo local desta máquina" in tela.lower(),
             "e AVISA quando ficou so no arquivo local",
             "esconder isso recriaria o problema que a planilha resolveu")

    print()
    print("--- 7. o registro so ACRESCENTA ---")
    # Fechamento e fato datado: corrigir um fechamento e registrar outro, nao
    # reescrever o anterior. Se aparecer escrita por linha aqui, a trilha deixou
    # de ser trilha.
    fonte = open(os.path.join(BASE, "registro_fechamentos.py"),
                 encoding="utf-8").read()
    conferir("adicionar_linhas" in fonte,
             "usa acrescentar linha (append), que a API resolve sozinha")
    conferir("escrever_lote" not in fonte,
             "e NAO usa escrita por linha especifica",
             "escrita por linha permitiria sobrescrever fechamento anterior")
    # A REGRA FICOU PRECISA EM 16/09/2026, em vez de banir `batchUpdate`
    # inteiro. O modulo passou a precisar de duas chamadas que nao tocam em
    # registro nenhum: criar a aba quando ela nao existe (addSheet) e formatar
    # a aba como texto (repeatCell so de numberFormat, porque "2026-08-16
    # 00:18:57" estava virando 46250,01894 na tela). Banir a palavra inteira
    # reprovaria essas duas e continuaria deixando passar qualquer coisa que
    # nao usasse batchUpdate. O que precisa continuar proibido e o que APAGA
    # ou SOBRESCREVE dado.
    conferir(".clear(" not in fonte, "nao limpa faixa nenhuma")
    for destrutivo in ("deleteSheet", "deleteDimension", "deleteRange",
                       "updateCells", "cutPaste", "moveDimension"):
        conferir(destrutivo not in fonte, f"e nao usa {destrutivo}")
    if "repeatCell" in fonte:
        conferir('"fields": "userEnteredFormat.numberFormat"' in fonte
                 and "userEnteredValue" not in fonte,
                 "o repeatCell mexe so no FORMATO, nunca no valor da celula",
                 "com userEnteredValue no fields, ele apagaria o conteudo")

    print()
    print("--- 8. justificativa que comecaria formula fica texto ---")
    # Justificativa e texto livre digitado por uma pessoa, e comecar frase com
    # "-" e comum. Sem a neutralizacao, o Sheets trataria como formula e o
    # registro guardaria erro em vez do que a pessoa escreveu.
    import sheets_client as sc
    for bruto in ("=adiantamento aprovado", "-Marketing pediu outro formato",
                  "+1 combo a mais", "@fulano aprovou"):
        seguro = sc._neutralizar_formula(bruto)
        conferir(seguro != bruto and seguro.endswith(bruto),
                 f"{bruto[:22]!r} e neutralizado sem perder o texto",
                 repr(seguro[:34]))


if __name__ == "__main__":
    print("=" * 74)
    print("  Fechamento em planilha propria, com o arquivo local como rede")
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
