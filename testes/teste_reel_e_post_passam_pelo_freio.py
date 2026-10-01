# -*- coding: utf-8 -*-
"""
Reel e post de feed autenticados passam pelo freio da conta.

POR QUE ESTE TESTE EXISTE (07/09/2026)

O programa tem tres protecoes para nao marcar a conta do Instagram: respeitar
uma pausa ativa, contar a chamada no teto do dia, e recuar ao levar bloqueio.
Em 29/08/2026 descobriu-se que o caminho novo do Story tinha ficado sem as tres,
e o comentario em baixar_story_ytdlp registra isso como "o tipo de buraco
silencioso que marcou duas contas em agosto".

A correcao de la nao chegou aqui. Story tem funcao propria; Reel e post de feed
dividem baixar_video com YouTube, TikTok e X, e naquela funcao a tentativa
AUTENTICADA (a que manda os cookies da conta) nao passava por protecao nenhuma.

O efeito e o pior possivel porque e invisivel: o programa mostrava, por exemplo,
5 de 20 usados no dia enquanto a conta ja tinha conversado 20 vezes com o
Instagram. Contador que subestima o uso e como se marca uma conta, e foi assim
em 25/08 e 27/08.

Isso passa a valer mais agora que o programa vai ser usado todo dia pelo
Marketing, com a conta deles.

O teste NAO chama o Instagram. O yt-dlp e substituido por um dublê que falha
sem sair da maquina, o estado da conta vai para uma pasta temporaria, e o
caminho de reserva pelo instaloader tambem e substituido, para o teste nao
esbarrar em rede por um caminho lateral.

    py testes\teste_reel_e_post_passam_pelo_freio.py
"""
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


REEL = "https://www.instagram.com/reel/DcT0RkaCHbc/"
YOUTUBE = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class DubleDoYtDlp:
    """Faz o papel do yt_dlp.YoutubeDL sem sair da maquina.

    Registra quantas vezes foi construido, que e como o teste sabe se a
    tentativa autenticada chegou a acontecer, e falha sempre, que e o caminho
    que leva o programa a tentar autenticado."""

    construcoes = []

    def __init__(self, opcoes):
        DubleDoYtDlp.construcoes.append(opcoes)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def extract_info(self, *_a, **_k):
        raise RuntimeError("duble: nao ha rede neste teste")


def preparar(pasta):
    """Isola o estado da conta e desliga tudo o que falaria com a rede."""
    import fluxo_downloads as fluxo
    fluxo.ARQUIVO_ESTADO_CONTA = os.path.join(pasta, "estado_conta.json")
    # DESLIGA O CONTADOR COMPARTILHADO (24/09/2026), mesmo motivo do resto
    # desta função: sem isto, _contar_uso_instagram/situacao_da_conta
    # falariam de verdade com a planilha de fechamentos desta máquina.
    fluxo._planilha_fechamentos_id = lambda: None
    # Cookies presentes e falsos: e o que faz o programa entrar na tentativa
    # autenticada, que e justamente o trecho sob teste.
    fluxo._opcoes_cookies = lambda: {"cookiefile": os.path.join(pasta, "c.txt")}

    # O CAMINHO DE RESERVA TAMBEM E DESLIGADO, e isto nao e detalhe: sem isso,
    # depois das duas tentativas falharem, o programa cairia no instaloader e
    # o teste gastaria chamada de verdade. Ja aconteceu de um stub no lugar
    # errado deixar um teste bater no Instagram e consumir 11 chamadas.
    def _reserva_desligada(*_a, **_k):
        raise RuntimeError("duble: reserva desligada no teste")
    fluxo.baixar_post_instaloader = _reserva_desligada

    import yt_dlp
    yt_dlp.YoutubeDL = DubleDoYtDlp
    return fluxo


def usados(fluxo):
    _pode, _motivo, quantos, _restantes = fluxo.situacao_da_conta()
    return quantos


def tentar(fluxo, link, pasta):
    DubleDoYtDlp.construcoes = []
    try:
        fluxo.baixar_video(link, pasta)
        return None
    except Exception as e:
        return e


def rodar():
    with tempfile.TemporaryDirectory() as pasta:
        fluxo = preparar(pasta)

        print("--- 1. Reel do Instagram entra no teto do dia ---")
        antes = usados(fluxo)
        erro = tentar(fluxo, REEL, pasta)
        depois = usados(fluxo)
        conferir(depois == antes + 1,
                 "a tentativa autenticada de Reel conta UMA chamada",
                 f"foi de {antes} para {depois}")
        conferir(len(DubleDoYtDlp.construcoes) == 2,
                 "e houve mesmo duas tentativas, a anonima e a autenticada",
                 f"houve {len(DubleDoYtDlp.construcoes)}")
        conferir(erro is not None, "a falha do dublê chega a quem chamou")

        print()
        print("--- 2. o teto e do Instagram, e nao do YouTube ---")
        # Contar YouTube aqui gastaria budget que nao e dele e faria o programa
        # parar de baixar do Instagram sem motivo nenhum.
        antes = usados(fluxo)
        tentar(fluxo, YOUTUBE, pasta)
        conferir(usados(fluxo) == antes,
                 "link de YouTube nao gasta o teto da conta do Instagram",
                 f"foi de {antes} para {usados(fluxo)}")
        conferir(len(DubleDoYtDlp.construcoes) == 2,
                 "e ele continua tentando anonimo e autenticado normalmente")

        print()
        print("--- 3. a tentativa anonima continua de graca ---")
        # Ela nao manda cookie nenhum, entao nao e a conta que esta falando.
        # Se ela contasse, o teto cairia pela metade sem motivo.
        fluxo._opcoes_cookies = lambda: {}
        antes = usados(fluxo)
        tentar(fluxo, REEL, pasta)
        conferir(usados(fluxo) == antes,
                 "sem cookies configurados, nada e contado",
                 f"foi de {antes} para {usados(fluxo)}")
        conferir(len(DubleDoYtDlp.construcoes) == 1,
                 "e so houve a tentativa anonima")
        fluxo._opcoes_cookies = lambda: {"cookiefile": os.path.join(pasta, "c.txt")}

        print()
        print("--- 4. no teto, a conta continua sendo usada (virou recomendação) ---")
        # REVISADO EM 17/09/2026: o teto travava a chamada; agora e so
        # recomendacao (decisao do auditor, depois de eu levantar o risco pra
        # metodologia de subida medida). `pode_usar` continua True passando
        # do numero, entao a tentativa AUTENTICADA acontece normalmente e o
        # contador continua andando. As duas OUTRAS travas (uma conta por
        # dia, pausa apos bloqueio real) continuam travando de verdade; isto
        # aqui e so o numero de referencia.
        while usados(fluxo) < fluxo.limite_diario_vigente():
            fluxo._contar_uso_instagram()
        pode, motivo, quantos, restantes = fluxo.situacao_da_conta()
        conferir(pode, "passar do teto recomendado NAO trava mais",
                 f"usados={quantos}")
        conferir(bool(motivo) and restantes == 0,
                 "mas o aviso continua existindo, so nao bloqueia",
                 motivo)
        erro = tentar(fluxo, REEL, pasta)
        conferir(len(DubleDoYtDlp.construcoes) == 2,
                 "a tentativa AUTENTICADA acontece normalmente, passando do teto",
                 f"houve {len(DubleDoYtDlp.construcoes)} tentativa(s)")
        conferir(usados(fluxo) == quantos + 1,
                 "e o contador continua andando alem do numero recomendado",
                 f"foi de {quantos} para {usados(fluxo)}")


if __name__ == "__main__":
    print("=" * 74)
    print("  Reel e post de feed passam pelo freio da conta")
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
