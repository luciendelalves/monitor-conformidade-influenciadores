# -*- coding: utf-8 -*-
"""
Prova que o programa distingue "perfil sem story" de "conta bloqueada".

POR QUE ESTE TESTE EXISTE (30/08/2026)

O yt-dlp relata perfil SEM STORY com a mensagem "You need to log in to access
this content", que parece falta de sessão e não é. No código dele:

    videos = ... /feed/reels_media/?reel_ids=...
    if not videos:
        self.raise_login_required('You need to log in to access this content')

Recusa de sessão de verdade dá outra: "This content is unreachable".

Em 29/08 eu tratei a primeira como bloqueio. O resultado: a conta ficou
pausada por horas, com a espera dobrando a cada tentativa, por causa de
perfis que simplesmente não tinham story no ar. E me levou a duas hipóteses
erradas seguidas sobre a causa.

Pausar à toa não é inofensivo: enquanto a conta está de castigo, download
nenhum acontece, e a pessoa conclui que o programa está quebrado.

    py testes\teste_sinais_do_instagram.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


CASOS = [
    # (mensagem do yt-dlp, é perfil sem story?, aciona o freio?, o que é)
    ("ERROR: [instagram:story] You need to log in to access this content. "
     "Use --cookies-from-browser or --cookies for the authentication.",
     True, False, "perfil sem story no ar"),

    ("ERROR: [instagram:story] This content is unreachable",
     False, True, "sessão recusada de verdade"),

    ("HTTP Error 429: Too Many Requests",
     False, True, "pedido para ir mais devagar"),

    ("checkpoint_required",
     False, True, "conta desconfiada, o caso severo"),

    ("HTTP Error 401: Unauthorized",
     False, True, "sessão inválida"),

    ("Nenhum arquivo gerado, o conteúdo pode ter saído do ar",
     False, False, "falha comum, não é da conta"),
]


def rodar():
    for mensagem, sem_story, freia, oque in CASOS:
        s = fluxo.e_perfil_sem_story(mensagem)
        b = fluxo.parece_bloqueio(mensagem)
        conferir(s == sem_story and b == freia,
                 f"{oque}: {'sem story' if sem_story else 'tem story ou n/a'}, "
                 f"{'freia' if freia else 'NÃO freia'}",
                 f"veio sem_story={s} freia={b}")

    print()
    print("--- a regra que não pode voltar atrás ---")
    conferir(not fluxo.parece_bloqueio(
        "You need to log in to access this content"),
        "perfil sem story NUNCA pode pausar a conta",
        "foi esse engano que deixou a conta parada por horas em 30/08")

    conferir(fluxo.parece_bloqueio("This content is unreachable"),
             "mas sessão recusada de verdade continua pausando")

    print()
    print("--- o caso severo continua severo ---")
    conferir(not fluxo.e_so_espera("checkpoint required"),
             "checkpoint é tratado como conta desconfiada, não como espera")
    conferir(fluxo.e_so_espera("HTTP Error 429"),
             "429 continua sendo espera curta")


if __name__ == "__main__":
    print("=" * 72)
    print("  O que é bloqueio do Instagram e o que só parece")
    print("=" * 72)
    print()
    rodar()
    print()
    print("=" * 72)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 72)
    sys.exit(1 if falhas else 0)
