# -*- coding: utf-8 -*-
"""
Visao que NAO RESPONDEU nao pode virar acusacao.

POR QUE ESTE TESTE EXISTE (08/09/2026)

A checagem de resposta da visao colapsava TRES estados num booleano:

    o modelo disse sim          -> True
    o modelo disse que nao viu  -> False
    o modelo NAO RESPONDEU      -> False    <-- o problema

Erro do Ollama, tempo esgotado ou resposta que a regex nao reconhece caiam todos
em `resposta = ""`, e `""` nao casa com "sim", entao virava False, que significa
"a visao olhou e nao viu".

ISSO ERA FALHA SEGURA ATE 07/09/2026, e deixou de ser no mesmo dia. Enquanto
visao-sim ABSOLVIA o publi, colapsar "nao" com "nao respondeu" era conservador.
Desde que a regra mudou, visao-NAO produz NAO CONFORME:

    publi lido por OCR                     -> cumprido
    nao lido, e a visao diz que NAO viu    -> NAO CONFORME
    nao lido, e a visao diz que VIU        -> REQUER VERIFICACAO

Ou seja: com o Ollama fora do ar, toda peca cujo publi o OCR nao le sai como NAO
CONFORME. Falha de infraestrutura virando acusacao contra influenciador, que e o
erro mais caro que este programa pode cometer. O docstring da funcao continuava
prometendo "falha segura", o que tornava o defeito invisivel para quem lesse o
codigo.

O QUE ESTE TESTE TRAVA

  1. os tres estados existem e sao distinguiveis
  2. resposta em INGLES conta: 13 de 81 respostas reais do modelo vieram em
     ingles ("NO"), e nenhuma afirmativa veio assim, mas o modelo troca de
     idioma e "YES" lido como negativa seria acusacao errada
  3. resposta que o programa nao entende NAO e tratada como negativa
  4. duvida da visao nao vira acusacao
  5. a evidencia distingue "a visao sugeriu que esta la" de "a visao nao
     respondeu", porque a evidencia e o que a pessoa le para decidir

Nao chama o Ollama: a conversa com o modelo e substituida por um duble.

    py testes\teste_visao_sem_resposta_nao_acusa.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import validar_avisos_portaria136 as motor  # noqa: E402

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def com_resposta(texto_ou_erro):
    """Troca a conversa com o Ollama por uma resposta fixa, ou por um erro."""
    def duble(_imagem, _pergunta, **_k):
        if isinstance(texto_ou_erro, Exception):
            raise texto_ou_erro
        return texto_ou_erro
    motor._perguntar_ollama = duble


def rodar():
    print("--- 1. SIM e NAO continuam sendo lidos como antes ---")
    for resposta, esperado in (("SIM", True), ("SIM.", True), ("Sim", True),
                               ("sim, contém", True),
                               ("NÃO", False), ("NÃO.", False)):
        com_resposta(resposta)
        r = motor.perguntar_visao_local("qualquer.png", ["publi"])
        conferir(r.get("publi") is esperado,
                 f"{resposta!r} -> {esperado}", f"veio {r.get('publi')!r}")

    print()
    print("--- 2. resposta em INGLES conta ---")
    # 13 de 81 respostas reais do modelo vieram em ingles, todas negativas. O
    # modelo troca de idioma, e um "YES" lido como negativa seria acusacao.
    for resposta, esperado in (("NO", False), ("NO.", False),
                               ("YES", True), ("Yes", True)):
        com_resposta(resposta)
        r = motor.perguntar_visao_local("qualquer.png", ["publi"])
        conferir(r.get("publi") is esperado,
                 f"{resposta!r} -> {esperado}", f"veio {r.get('publi')!r}")

    print()
    print("--- 3. NAO RESPONDEU e um terceiro estado, e nao uma negativa ---")
    # E o coracao do defeito. None significa "nao sei", e nao "nao viu".
    casos = [
        (RuntimeError("ollama fora do ar"), "erro na chamada"),
        ("", "resposta vazia"),
        ("   ", "resposta em branco"),
        ("Talvez", "resposta que o programa nao entende"),
        ("A imagem mostra uma pessoa segurando um celular", "descricao livre"),
    ]
    for resposta, rotulo in casos:
        com_resposta(resposta)
        r = motor.perguntar_visao_local("qualquer.png", ["publi"])
        conferir(r.get("publi") is None,
                 f"{rotulo} -> nao sei (None)",
                 f"veio {r.get('publi')!r}; False aqui significaria "
                 f"'a visao olhou e nao viu', e viraria NAO CONFORME")

    print()
    print("--- 4. o 18+ pergunta duas vezes, e combina os tres estados ---")
    # Ele aceita sim em qualquer das duas perguntas. Com tres estados, so pode
    # afirmar ausencia quando as DUAS negarem.
    com_resposta("NÃO")
    r = motor.perguntar_visao_local("qualquer.png", ["18"])
    conferir(r.get("18") is False, "as duas perguntas negando -> False",
             f"veio {r.get('18')!r}")
    com_resposta(RuntimeError("caiu"))
    r = motor.perguntar_visao_local("qualquer.png", ["18"])
    conferir(r.get("18") is None, "as duas sem resposta -> nao sei",
             f"veio {r.get('18')!r}")

    print()
    print("--- 5. duvida da visao NAO vira acusacao ---")
    # A regra: so da para afirmar ausencia quando a visao NEGOU. Item que nem
    # foi perguntado nao gera duvida, senao a evidencia enche de aviso inutil.
    conferir(motor.visao_deixa_duvida({"publi": True}, "publi", False) is True,
             "visao disse que viu, e o OCR nao leu -> duvida")
    conferir(motor.visao_deixa_duvida({"publi": None}, "publi", False) is True,
             "visao NAO RESPONDEU, e o OCR nao leu -> duvida",
             "sem isso, Ollama fora do ar vira NAO CONFORME")
    conferir(motor.visao_deixa_duvida({"publi": False}, "publi", False) is False,
             "visao NEGOU, e o OCR nao leu -> ausencia, sem duvida",
             "e o unico caso em que da para afirmar que nao esta la")
    conferir(motor.visao_deixa_duvida({"publi": None}, "publi", True) is False,
             "o OCR leu -> nao ha duvida, qualquer coisa que a visao diga")
    conferir(motor.visao_deixa_duvida({}, "publi", False) is False,
             "item que nem foi perguntado nao gera duvida",
             "marcar isso encheria a evidencia de aviso sem uso")

    print()
    print("--- 6. a evidencia diz QUAL dos dois casos aconteceu ---")
    # A frase de duvida afirmava "a IA de visao sugere que esta presente". Para
    # o caso de nao ter respondido, isso seria mentira, e a evidencia e o que a
    # pessoa le para decidir.
    fonte = open(os.path.join(BASE, "validar_avisos_portaria136.py"),
                 encoding="utf-8").read()
    conferir("não respondeu" in fonte.lower(),
             "existe frase para o caso de a visao nao responder")
    conferir(fonte.count("sugere que está presente") >= 1,
             "e a frase antiga, de sugestao, continua existindo",
             "as duas situacoes sao diferentes e a evidencia tem de separar")


if __name__ == "__main__":
    print("=" * 74)
    print("  Visao que nao respondeu nao vira acusacao")
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
