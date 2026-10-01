# -*- coding: utf-8 -*-
"""
"Esperando o trabalhador" só é tranquilizador se houver trabalhador.

POR QUE ESTE ARQUIVO EXISTE (06/09/2026)

O auditor viu a fila parada e perguntou por que, dizendo que já era recorrente:
"não é a primeira vez, ai preciso limpar a fila".

O DIAGNÓSTICO: não havia bug, e os três números da tela estavam todos certos,
só contando coisas diferentes (todas as linhas da fila, as linhas sem status, e
as tarefas na fila do trabalhador). O que estava errado era o TOM: o trabalhador
estava fora do ar, então a tarefa esperava por alguém que não existia, e a tela
dizia isso numa caixa azul, no tom de "está tudo em ordem, aguarde".

O aviso vermelho de trabalhador fora do ar existe, mas mora no TOPO da página.
Quem está mexendo na fila está lá embaixo: lê "esperando" e conclui que é
normal. Informação certa no lugar errado é quase tão ruim quanto informação
errada.

E LIMPAR A FILA NÃO RESOLVE, embora pareça resolver: apaga a linha da planilha e
zera o contador de pendente, mas a tarefa órfã continua na fila do trabalhador e
a causa (ninguém executando) não é tocada. Por isso a mensagem nova diz o que
resolve de verdade.

Rodar:

    py testes\teste_fila_esperando_sem_trabalhador.py
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
    with open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
              encoding="utf-8") as f:
        tela = f.read()

    print("--- 1. a mensagem PERGUNTA se ha trabalhador antes de tranquilizar ---")
    bloco = tela.split("if esperando and not em_andamento:")[1][:2400]
    conferir("trabalhador_de_pe()" in bloco,
             "consulta se o trabalhador esta de pe",
             "sem isso a mensagem afirma que alguem vai pegar, sem saber")
    conferir("st.info(" in bloco and "st.error(" in bloco,
             "e tem DOIS tons: azul quando ha quem pegue, vermelho quando nao")

    print()
    print("--- 2. o caso sem trabalhador diz o que resolve ---")
    depois = bloco.split("else:")[-1]
    conferir("ninguém vai pegar" in depois or "ninguem vai pegar" in depois,
             "diz que ninguem vai pegar, em vez de 'esperando'")
    conferir("iniciar_trabalhador.bat" in depois,
             "e diz COMO resolver, nomeando o arquivo")
    conferir("Limpar a fila não resolve" in depois
             or "Limpar a fila nao resolve" in depois,
             "e avisa que limpar a fila NAO resolve",
             "era o remedio errado que o auditor vinha usando")

    print()
    print("--- 3. o arquivo que a mensagem manda clicar existe ---")
    # Mensagem que manda clicar num arquivo inexistente e pior que mensagem
    # nenhuma: manda a pessoa procurar o que nao ha.
    conferir(os.path.exists(os.path.join(BASE, "iniciar_trabalhador.bat")),
             "iniciar_trabalhador.bat existe na pasta do programa")

    print()
    print("--- 4. os tres contadores da tela contam coisas DIFERENTES ---")
    # Eles divergem por desenho, e foi essa divergencia que levantou a suspeita
    # de bug. Cada um responde a uma pergunta distinta, e este teste registra
    # isso para ninguem "consertar" fazendo os tres iguais.
    conferir('pendentes = [x for x in fila if x["link"] and not x["status"]]' in tela,
             "PENDENTE e linha da planilha SEM status")
    conferir("len(fila)" in tela,
             "LIMPAR A FILA conta TODAS as linhas, com status ou sem")
    conferir("_listar_dos_dois(fila_trabalho.PENDENTE)" in tela,
             "ESPERANDO conta tarefa na fila do TRABALHADOR, nao linha de planilha")

    print()
    print("--- 5. o botao de baixar pendentes explica por que esta travado ---")
    # Ele fica desabilitado quando ja ha download em andamento, e sem o texto de
    # ajuda a pessoa conclui que o programa quebrou.
    conferir("disabled=ja_baixando" in tela,
             "o botao trava quando ja ha download em andamento")
    conferir("Já tem um download rodando" in tela,
             "e diz isso na ajuda, em vez de so ficar cinza")


    print()
    print("--- 6. a espera PROPOSITAL entre links fica visivel ---")
    # O auditor pos dois links, o segundo nao veio de imediato e ele concluiu
    # que nao viria: "eu achei que ele ficava na fila mas que ele iria ser
    # baixado". Ele vinha, depois da pausa. O programa espaca links do
    # Instagram de proposito (30 a 180s), porque bater vários seguidos sem
    # pausa levou a erro 429 na conta. A pausa era reportada apenas na janela
    # do trabalhador, que nao e onde a pessoa esta olhando.
    import fluxo_downloads as fluxo
    conferir(fluxo.PAUSA_INSTAGRAM_MIN_SEG > 0
             and fluxo.PAUSA_INSTAGRAM_MAX_SEG > fluxo.PAUSA_INSTAGRAM_MIN_SEG,
             f"a pausa entre links existe e tem faixa "
             f"({fluxo.PAUSA_INSTAGRAM_MIN_SEG} a "
             f"{fluxo.PAUSA_INSTAGRAM_MAX_SEG}s)")
    conferir("PAUSA_INSTAGRAM_MIN_SEG" in tela,
             "a tela mostra a duracao real da pausa, lida do modulo",
             "escrever o numero na tela a mao faria os dois divergirem")
    # CONFERE O SENTIDO, E NAO A PONTUACAO (corrigido em 08/09/2026). A versao
    # anterior exigia a frase exata "um por vez, com pausa", e reprovou quando o
    # texto ganhou negrito no meio, "um por vez**, com pausa". Teste que quebra
    # por causa de dois asteriscos treina quem mexe a ignorar o resultado.
    conferir("um por vez" in tela,
             "a tela diz que os links vao um por vez")
    conferir("de propósito" in tela or "proposital" in tela,
             "e diz que o espacamento e proposital, nao defeito")

    # AS DUAS PAUSAS APARECEM, e nao so a menor (08/09/2026). A tela citava
    # apenas a pausa entre LINKS, de 30 a 180s, e existe uma segunda, entre
    # RODADAS, de 180 a 420s. Em uso real a pausa sorteada foi de 356s: o
    # auditor esperava no maximo 3 minutos, esperou 6, e concluiu que travou.
    conferir(fluxo.PAUSA_ENTRE_RODADAS_MAX_SEG > fluxo.PAUSA_INSTAGRAM_MAX_SEG,
             "a pausa entre rodadas e maior que a entre links",
             "se deixar de ser, este teste perde o sentido")
    conferir("PAUSA_ENTRE_RODADAS" in tela,
             "e a tela mostra tambem a pausa entre rodadas, lida do modulo",
             "mostrar so a menor faz a pessoa achar que travou")
    conferir("ela está na vez" in tela or "ela esta na vez" in tela,
             "e que a linha sem baixar NAO foi esquecida")
    # O botao de pendentes tambem: dizer so "ja tem download em andamento"
    # deixava a pessoa achando que precisava clicar de novo depois.
    conferir("vai** pegar estes" in tela or "vai pegar estes" in tela,
             "o botao travado diz que o download em curso VAI pegar os "
             "pendentes")

    print()
    print("--- 7. a rodada RELE a fila antes de desistir ---")
    # A CORRIDA QUE O AUDITOR PEGOU: "coloquei um video para baixar atras do
    # outros, mas o segundo não baixou". A expectativa dele estava certa, e o
    # programa prometia isso.
    #
    # A janela era: quem cola um link so cria tarefa se ainda NAO existe uma
    # (para nao virar rajada sem pausa). Se o link entra enquanto uma tarefa
    # esta terminando, ninguem cria tarefa nova E a tarefa em curso ja passou da
    # ultima leitura da fila. O link fica orfao.
    fonte = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    trecho = fonte.split("# FIM DA RODADA: continua sozinho ou para aqui?")[1][:1800]
    conferir("ler_fila()" in trecho,
             "antes de parar, a rodada pergunta de novo a planilha",
             "'deixados_para_depois' conta so o que a rodada viu no COMECO dela")
    conferir("chegou_no_meio" in trecho,
             "e trata o caso de link que entrou no meio do trabalho")
    conferir("if not chegou_no_meio:" in trecho and "break" in trecho,
             "so para quando a releitura confirma que nao ha mais nada")

    print()
    print("--- 8. colar link NAO cria tarefa duplicada ---")
    # A protecao que existia antes e continua valendo: uma tarefa por vez, para
    # as pausas entre links acontecerem DENTRO da rodada. Sem isso, tres cliques
    # gerariam tres tarefas e os links sairiam em rajada, sem pausa entre eles.
    conferir("ha_trabalho(fila_trabalho.BAIXAR_FILA)" in tela,
             "a tela pergunta se ja ha tarefa de download antes de criar outra")
    conferir("if not ja_tem_trabalho:" in tela,
             "e so cria quando nao ha",
             "e por isso que a rodada precisa reler: e ela que pega o link novo")
if __name__ == "__main__":
    print("=" * 74)
    print('  "Esperando o trabalhador" exige que haja trabalhador')
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
