# -*- coding: utf-8 -*-
"""
Link que ficou esperando na fila baixa sozinho, e nao entra em laco.

POR QUE ESTE TESTE EXISTE (08/09/2026)

Medido em uso real: dois stories da @lomma, colados um atras do outro. A tarefa
de download comecou 10:28:43 e terminou 10:29:08, e o segundo link ficou parado
com status vazio. Nada falhou, nada foi bloqueado, o teto do dia estava em 1 de
20 chamadas. O link ficou esperando um clique que ninguem sabia que era preciso
dar, porque a tela havia prometido que ele entraria na rodada em andamento.

A causa e uma corrida: quem cola um link so cria tarefa se ainda nao existe uma,
e a rodada rele a fila UMA vez no fim dela. Link que chega a planilha depois
dessa releitura e antes de a tarefa terminar nao e visto por ninguem. A correcao
de 06/09/2026 estreitou essa janela; ela nao fechou.

Agora o trabalhador confere a fila quando esta ocioso e cria a tarefa ele mesmo.
A decisao esta numa funcao PURA, e e ela que este teste exercita: sem planilha,
sem trabalhador de pe, sem chamada ao Instagram.

O QUE MAIS IMPORTA AQUI SAO OS CASOS 6 E 7. Uma varredura automatica que cria
tarefa sozinha pode gastar chamada do Instagram em laco, e chamada repetida foi
o que marcou duas contas em agosto de 2026. Por isso a espera reinicia quando
ainda esta entrando link, e existe freio para o caso de a tarefa nao resolver
nada.

    py testes\teste_link_esperando_baixa_sozinho.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import trabalhador  # noqa: E402

ESPERA = trabalhador.SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO
decidir = trabalhador.decidir_se_baixa_sozinho

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


ZERADO = {"quantas": 0, "esperando_desde": None, "tentou_com": None}


def rodar():
    print("--- 1. fila vazia: nao cria nada ---")
    criar, motivo, estado = decidir(1000.0, False, 0, dict(ZERADO))
    conferir(not criar, "sem link esperando, nao cria tarefa")
    conferir(motivo == "", "e nao escreve nada no log", repr(motivo))

    print()
    print("--- 2. ja existe tarefa de download: nao cria outra ---")
    # Uma tarefa processa TODAS as linhas pendentes. Criar outra e o que a regra
    # de rajada evita, porque as pausas entre links valem DENTRO de uma rodada.
    criar, _m, estado = decidir(1000.0, True, 3, dict(ZERADO))
    conferir(not criar, "com tarefa em andamento, nao cria uma segunda")

    print()
    print("--- 3. primeira vez que ve: espera, e avisa uma vez ---")
    criar, motivo, estado = decidir(1000.0, False, 1, dict(ZERADO))
    conferir(not criar, "nao dispara no primeiro instante")
    conferir("esperando na fila" in motivo,
             "avisa no log que viu link esperando", repr(motivo))
    conferir(estado["esperando_desde"] == 1000.0,
             "e marca desde quando esta esperando", str(estado))

    print()
    print("--- 4. dentro da espera: continua esperando, calado ---")
    criar, motivo, estado2 = decidir(1000.0 + ESPERA - 1, False, 1, estado)
    conferir(not criar, "um segundo antes do prazo, ainda nao dispara")
    conferir(motivo == "", "e nao repete o aviso a cada conferencia",
             repr(motivo))

    print()
    print("--- 5. vencida a espera: cria a tarefa ---")
    criar, motivo, estado3 = decidir(1000.0 + ESPERA, False, 1, estado)
    conferir(criar, "no prazo, cria a tarefa sozinho")
    conferir("Baixando sozinho" in motivo, "e diz isso no log", repr(motivo))
    conferir(estado3["tentou_com"] == 1,
             "e registra com quantas linhas tentou", str(estado3))

    print()
    print("--- 6. ainda entrando link: a espera REINICIA ---")
    # Sem isto, cada link viraria uma rodada de um link so, e as pausas entre
    # links do Instagram deixariam de existir, porque elas acontecem dentro de
    # uma rodada e nao entre tarefas.
    criar, motivo, estado_b = decidir(1000.0, False, 1, dict(ZERADO))
    criar, motivo, estado_b = decidir(1000.0 + 30, False, 2, estado_b)
    conferir(not criar, "chegou link novo, nao dispara ainda")
    conferir(estado_b["esperando_desde"] == 1000.0 + 30,
             "e a espera recomeca do zero", str(estado_b))
    criar, _m, estado_b2 = decidir(1000.0 + 30 + ESPERA - 1, False, 2, estado_b)
    conferir(not criar, "a contagem passou a valer da chegada do ultimo")
    criar, _m, estado_b3 = decidir(1000.0 + 30 + ESPERA, False, 2, estado_b)
    conferir(criar, "e dispara com o lote inteiro junto")

    print()
    print("--- 7. FREIO CONTRA LACO: tarefa que nao resolveu nada ---")
    # Se a tarefa automatica rodou e a quantidade esperando continua a mesma,
    # criar outra igual repetiria o mesmo nada para sempre, gastando chamada do
    # Instagram em cada volta. Para aqui e deixa para a pessoa, que tem o botao.
    depois_de_tentar = dict(estado3)   # tentou_com=1, esperando_desde=1000+ESPERA
    criar, motivo, estado4 = decidir(
        1000.0 + ESPERA * 3, False, 1, depois_de_tentar)
    conferir(not criar,
             "nao cria segunda tarefa automatica para a mesma quantidade",
             str(estado4))
    # E continua sem criar por mais tempo que passe.
    criar, _m, _e = decidir(1000.0 + ESPERA * 50, False, 1, estado4)
    conferir(not criar, "e nao volta a tentar so porque o tempo passou")

    print()
    print("--- 8. houve progresso: pode tentar de novo ---")
    # Baixou uma de duas: a quantidade mudou, entao existe trabalho novo que a
    # tentativa anterior nao viu, e o freio sai do caminho.
    criar, _m, estado5 = decidir(2000.0, False, 2, dict(ZERADO))
    criar, _m, estado5 = decidir(2000.0 + ESPERA, False, 2, estado5)
    conferir(criar, "criou a tarefa com 2 esperando")
    criar, _m, estado6 = decidir(3000.0, False, 1, estado5)
    conferir(not criar, "caiu para 1, reinicia a espera")
    criar, _m, _e = decidir(3000.0 + ESPERA, False, 1, estado6)
    conferir(criar, "e volta a criar tarefa, porque houve progresso")

    print()
    print("--- 9. o trabalhador conhece as duas constantes ---")
    conferir(isinstance(ESPERA, int) and ESPERA > 0,
             f"a espera e um numero positivo ({ESPERA}s)")
    conferir(trabalhador.SEGUNDOS_ENTRE_CONFERENCIAS_DA_FILA
             > trabalhador.SEGUNDOS_ENTRE_VOLTAS,
             "e conferir a fila e mais raro que a volta do laco",
             "conferir a planilha a cada volta seriam centenas de chamadas por hora")

    print()
    print("--- 10. a varredura NAO escreve na coluna de status ---")
    # Armadilha conhecida: a coluna SITUACAO/status e o gatilho. Linha COM
    # status e ignorada pela rodada, entao escrever "esperando" ali para
    # aparecer na tela faria a linha nunca mais ser baixada.
    fonte = open(os.path.join(BASE, "trabalhador.py"), encoding="utf-8").read()
    corpo = fonte.split("def varrer_fila_esperando(")[1].split("\ndef ")[0]
    for proibido in ("escrever_lote", "ABA_FILA", "gravar"):
        conferir(proibido not in corpo,
                 f"a varredura nao usa {proibido!r}")
    conferir('x["status"]' in corpo and "not x" in corpo,
             "e usa o mesmo criterio da rodada: link com status vazio")

    print()
    print("--- 11. a varredura age com a linha de download parada ---")
    # ATENCAO AO QUE ESTE BLOCO PROVA, E AO QUE NAO PROVA.
    #
    # Em 08/09/2026 a primeira versao da varredura derrubou o trabalhador com
    # "Segmentation fault", porque lia a planilha da thread principal enquanto a
    # thread de download escrevia nela. QUEM IMPEDE ISSO HOJE E A TRAVA em
    # sheets_client, testada em teste_planilha_uma_thread_por_vez.py, e nao a
    # guarda conferida aqui: a mesma corrida ja existia antes desta varredura,
    # entre concluir_analise e processar_fila.
    #
    # A guarda continua valendo pelo proposito da varredura: ela existe para
    # agir DEPOIS de a tarefa terminar, e conferir a fila no meio de um download
    # seria chamada a planilha sem uso.
    chamada = fonte.split("# 3.5.")[1].split("# 4. Diz que")[0]
    conferir("download_em_voo is None" in chamada,
             "a varredura so e chamada com a linha de download parada")
    conferir("varrer_fila_esperando(" in chamada,
             "e e ela que e chamada ali")
    conferir("sheets_client" in chamada,
             "e o comentario aponta onde esta a protecao de verdade",
             "sem isso alguem tira a trava achando que a guarda basta")
    # Dentro da funcao, a conferencia de tarefa vem ANTES da chamada a planilha.
    posicao_ha_trabalho = corpo.find("ha_trabalho")
    posicao_ler_fila = corpo.find("ler_fila")
    conferir(0 <= posicao_ha_trabalho < posicao_ler_fila,
             "e ha_trabalho e conferido antes de ler a planilha",
             f"ha_trabalho em {posicao_ha_trabalho}, ler_fila em {posicao_ler_fila}")
    conferir("CHAMAR SÓ COM A LINHA DE DOWNLOAD PARADA" in corpo,
             "e a exigencia esta escrita no docstring da funcao")


if __name__ == "__main__":
    print("=" * 74)
    print("  Link que ficou esperando baixa sozinho")
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
