# -*- coding: utf-8 -*-
"""
A situação do escopo fica sempre à vista, e o rádio de pagamento saiu.

POR QUE ESTE ARQUIVO MUDOU DE CONTEÚDO (09/09/2026)

Ele nasceu em 04/09/2026 provando que o rádio "Este ciclo já foi pago?"
mostrava a situação do escopo antes da escolha, e que as três situações de
pagamento (NÃO PAGO/PARCIALMENTE PAGO/PAGO) continuavam existindo.

O rádio saiu. O auditor apontou o problema de fundo: "o pagamento vem depois
do ciclo fechado... essa mensagem é para pagamento do ciclo, e não do
escopo". Perguntar "já foi pago?" pressupunha que pagamento podia acontecer
ANTES desta tela confirmar a entrega, e é exatamente isso que o fluxo real
evita (ESCOPO → ciclo entregue → SOLICITA o pagamento → ciclo seguinte). O
fim da tela virou um botão só, "Solicitar pagamento", gatilhado por
fechamento["exige_justificativa"] (escopo_e_entrega.py).

Manter o ARQUIVO, trocar o CONTEÚDO. Sem controle de versão neste
repositório, apagar o arquivo perderia o histórico do que já foi provado
aqui; reescrever documenta a mudança no lugar onde ela aconteceu. Este teste
agora prova duas coisas: que o vocabulário antigo (PAGAMENTO_PAGO e
companhia) realmente saiu do motor, e que a situação do escopo continua
aparecendo sempre, sem depender de nenhuma escolha de pagamento.

Rodar:

    py testes\\teste_escopo_a_vista_no_pagamento.py
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

    with open(os.path.join(BASE, "pages", "3_Financeiro.py"),
              encoding="utf-8") as f:
        tela = f.read()

    print("--- 1. o vocabulário de pagamento do CICLO saiu do motor ---")
    for nome in ("PAGAMENTO_PAGO", "PAGAMENTO_PARCIAL", "PAGAMENTO_NAO_PAGO",
                 "SITUACOES_DE_PAGAMENTO", "houve_pagamento",
                 "pagamento_exige_justificativa", "achado_de_pagamento",
                 "ACHADO_PAGO_SEM_ENTREGA"):
        conferir(not hasattr(ee, nome),
                 f"escopo_e_entrega não tem mais {nome}",
                 "saiu junto com o rádio 'já foi pago?' em 09/09/2026")

    print()
    print("--- 2. e o rádio antigo saiu da tela ---")
    # COMPARA COM "codigo" (sem comentário), NÃO "tela" (fonte crua): o
    # comentário que explica a mudança CITA "Este ciclo já foi pago?" de
    # propósito, para quem ler o código entender o que saiu e por quê. Só o
    # CÓDIGO precisa ter deixado de usar a pergunta, não a explicação dela.
    codigo = "\n".join(l for l in tela.splitlines()
                       if not l.strip().startswith("#"))
    conferir("pag1.radio(" not in tela,
             "a tela não tem mais o rádio de pagamento do ciclo")
    conferir("Este ciclo já foi pago?" not in codigo,
             "a pergunta no passado saiu do código",
             "o docstring ainda pode citá-la, como histórico")
    conferir('st.button("Solicitar pagamento' in tela,
             "e o botão final agora é a solicitação")

    print()
    print("--- 3. a situação do escopo continua sempre à vista ---")
    # Antes ela só aparecia perto do rádio, condicionada a ENTREGA_NAO_FECHOU.
    # Agora ela é a faixa do topo da tela, sempre, e a justificativa é o que
    # depende da situação, não a visibilidade dela.
    conferir("ee.apresentacao(fechamento" in tela,
             "a apresentação do motor é usada, sem reescrever os nomes na tela")
    conferir('_faixa(f"**{_ap' in tela,
             "e ela sai numa faixa de largura inteira, não cortada")

    print()
    print("--- 4. a regra da justificativa cobre as duas razões, num campo só ---")
    contagem_vazia = ee.contar_entregas([], "@x", "1")
    fecha_conforme = ee.fechar_ciclo(ee.ler_escopo("Não informado"), contagem_vazia)
    conferir(not fecha_conforme["exige_justificativa"],
             "sem base para comparar, nada a justificar por composição",
             fecha_conforme)

    print()
    print("--- 5. toda situação que não fechou tem rótulo para o aviso ---")
    # O aviso mostra _ap['curto'] e _ap['icone']. Uma situação sem rótulo
    # deixaria o aviso vazio exatamente no caso em que ele mais importa.
    for situacao in ee.ENTREGA_NAO_FECHOU:
        ap = ee.apresentacao(situacao)
        conferir(bool(ap.get("curto")) and bool(ap.get("icone")),
                 f"'{situacao}' tem nome curto e ícone para o aviso",
                 str(ap))


if __name__ == "__main__":
    print("=" * 74)
    print("  A situação do escopo fica sempre à vista, sem rádio de pagamento")
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
