# -*- coding: utf-8 -*-
"""
"Pagamento" nomeava DUAS coisas nesta tela; hoje só uma delas decide algo.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

O auditor perguntou se havia redundância entre as telas Cronograma e Pagamento,
Financeiro e Cadastro. Parte não era (o Cadastro é outra etapa: contrato
entrando, número do Netlex). Mas entre Cronograma e Financeiro era, e em
05/09/2026 as duas foram JUNTADAS numa tela só. No mesmo dia ele decidiu que a
edição post a post sai do programa e volta a ser manual na planilha, então o
que sobrou aqui foi o pagamento do post sendo MOSTRADO.

NAQUELA ÉPOCA, o pagamento do CICLO era DECIDIDO por um rádio ("já foi pago?"),
e a palavra "pagamento" nomeava duas coisas na mesma tela: o post (Realizado/
Pendente, mostrado) e o ciclo (NÃO PAGO/PARCIAL/PAGO, decidido). Este arquivo
provava a desambiguação entre as duas.

O QUE MUDOU EM 09/09/2026: o auditor apontou que o rádio pressupunha a ordem
errada ("o pagamento vem depois do ciclo fechado... essa mensagem é para
pagamento do ciclo, e não do escopo"). O rádio saiu, e no lugar entrou
"Solicitar pagamento", gatilhado pela situação do escopo
(`fechamento["exige_justificativa"]`), não por uma segunda declaração de
pagamento. Não existem mais DUAS coisas chamadas "pagamento" com peso de
decisão na tela: existe o post (mostrado, Realizado/Pendente) e a
SOLICITAÇÃO (um verbo diferente, não um estado de pagamento).

O QUE ESTE TESTE AINDA PROVA: que o pagamento por post continua sendo só
leitura (o programa nunca escreve na coluna PAGAMENTO da Monitoramento), e
que a tela não reintroduziu o vocabulário antigo do ciclo por engano.

Rodar:

    py testes\\teste_dois_pagamentos_desambiguados.py
"""
import os
import sys

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
    import escopo_e_entrega as ee

    def ler(nome):
        with open(os.path.join(BASE, "pages", nome), encoding="utf-8") as f:
            return f.read()

    tela = ler("3_Financeiro.py")

    print("--- 1. o pagamento por post continua nomeado e só leitura ---")
    conferir("post a post" in tela.lower(),
             "o nível do post é nomeado como post a post")
    conferir("Fechar o ciclo" in tela,
             "e a decisão do ciclo (agora solicitação) tem seção própria")
    # A FRASE EXATA MUDOU EM 16/09/2026, e o motivo é bom: a tabela tela a
    # tela ("Os posts deste ciclo", que mostrava CRONOGRAMA e PAGAMENTO só
    # para conferência) SAIU do Financeiro, porque a mesma informação já está
    # na Monitoramento. Sem a tabela, o aviso "isto aqui é só conferência,
    # quem preenche é gente na planilha" perdeu o objeto que ele explicava.
    # O que precisa continuar valendo é o fato, e ele continua escrito no
    # arquivo (tanto no docstring quanto perto da contagem de pagamento), em
    # singular ou plural. A garantia de verdade, que a tela NÃO escreve nessa
    # coluna, é a seção 3 aqui embaixo, que olha o código e não o texto.
    conferir("à mão na planilha" in tela,
             "o arquivo diz que o pagamento do post é preenchido à mão, fora daqui")

    print()
    print("--- 2. o vocabulário do CICLO (NÃO PAGO/PARCIAL/PAGO) não voltou ---")
    # SE ALGUÉM REINTRODUZIR o rádio antigo, a mesma confusão de 05/09/2026
    # volta: duas coisas chamadas "pagamento" na mesma tela, uma mostrada e
    # outra decidida. Este teste falha se isso acontecer.
    for nome in ("PAGAMENTO_PAGO", "PAGAMENTO_PARCIAL", "PAGAMENTO_NAO_PAGO",
                 "SITUACOES_DE_PAGAMENTO"):
        conferir(not hasattr(ee, nome),
                 f"escopo_e_entrega não tem mais {nome}",
                 "reintroduzir isso reabriria a ambiguidade que este teste existe para evitar")
    conferir('"pagamento": pagamento' not in tela,
             "o registro de fechamento não tem mais campo 'pagamento' do ciclo",
             "a variável 'pagamento' do rádio antigo nem existe mais")

    print()
    print("--- 3. quem escreve cada um continua sendo lugar diferente ---")
    # O NIVEL DO POST NAO E ESCRITO PELO PROGRAMA (decisao de 05/09/2026): ele
    # e preenchido a mao na planilha. O nivel do ciclo e gravado, mas no
    # registro de fechamento, nunca na coluna S.
    conferir("corrigir_coluna_na_monitoramento(" not in tela,
             "a tela NÃO escreve o pagamento do post",
             "ele é preenchido à mão na planilha")
    conferir('"justificativa": justificativa' in tela,
             "e o nível do ciclo (a justificativa da solicitação) vai para o "
             "registro de fechamento")
    conferir('COL_MON["pagamento"]' not in tela
             and "escrever_lote" not in tela,
             "e a tela não escreve na coluna S por nenhum outro caminho")

    print()
    print("--- 4. o Financeiro só MOSTRA a contagem do post, não decide por ela ---")
    conferir("_contagem_pagamento" in tela,
             "a contagem post a post continua aparecendo")
    conferir("não decide a solicitação abaixo" in tela or "não decide" in tela,
             "e a tela avisa por escrito que a contagem não decide")


if __name__ == "__main__":
    print("=" * 74)
    print('  "Pagamento" nomeava duas coisas; hoje só uma decide algo')
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
