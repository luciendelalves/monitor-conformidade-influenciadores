# -*- coding: utf-8 -*-
r"""
Avisa na tela do Windows quando o trabalhador cai, sem precisar abrir o app.

POR QUE EXISTE (24/09/2026)

O trabalhador já grava um sinal de vida a cada volta do laço
(fila_trabalho.registrar_sinal_de_vida), e o app já confere isso
(trabalhador_de_pe()). Mas essa conferência é PASSIVA: só acontece quando
alguém abre a tela. Se o trabalhador cair e ninguém abrir o app, o trabalho
para e ninguém sabe, às vezes por horas, e no servidor (sem ninguém de olho
na tela o dia inteiro) isso tende a piorar, não a melhorar.

Pedido do auditor: um aviso simples, sem depender de conta de e-mail nem de
nada configurado por fora. Isto é a resposta possível dentro desse limite:
avisa quem estiver logado NESTA máquina, na hora. Não alcança alguém que não
esteja diante dela, e isso não é limitação de código, é o que um aviso só na
tela sempre vai ser.

COMO DECIDE QUE É QUEDA DE VERDADE, E NÃO PARADA PEDIDA

Ao encerrar por qualquer caminho que passe pelo bloco `finally` de
trabalhador.main, o próprio trabalhador grava um sinal de vida com
"encerrado": True, tanto ao receber pedido de parada quanto ao sair depois de
uma falha tratada. O aviso só dispara quando o sinal está velho E o último
sinal registrado NÃO diz "encerrado": True, ou seja, o processo se calou no
meio de alguma coisa, sem avisar que estava saindo. Isso cobre queda de
verdade, encerramento forçado (Gerenciador de Tarefas) e a máquina sendo
reiniciada; não dispara por pedido de parada pela tela.

Também não avisa antes de ver o trabalhador de pé pelo menos uma vez, para
não confundir "acabou de subir, ainda sem primeiro sinal" com "caiu".

SÓ UMA CÓPIA POR MÁQUINA

Sobe junto com o trabalhador, pelo mesmo iniciar_trabalhador.bat. Se já
existir uma rodando, a nova desiste em silêncio (trava.travar, o mesmo
mecanismo já usado para os arquivos compartilhados deste programa), para
reiniciar o trabalhador várias vezes no mesmo dia não empilhar janelas.

Uso:

    py vigia_trabalhador.py
"""
import ctypes
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import fila_trabalho as fila
import trava

SEGUNDOS_ENTRE_CONFERENCIAS = 30
ARQUIVO_TRAVA_VIGIA = os.path.join(fila.PASTA_FILA, "vigia_trabalhador")


def decidir_estado(visto_de_pe, de_pe, ja_avisado, sinal):
    """Função pura: decide o novo (visto_de_pe, ja_avisado, avisar_agora) a
    partir da leitura fresca de fila.trabalhador_de_pe(). Separada do laço e
    da caixa de mensagem para a lógica poder ser testada sem esperar 30
    segundos nem abrir janela nenhuma."""
    if de_pe:
        return True, False, False
    if visto_de_pe and not sinal.get("encerrado") and not ja_avisado:
        return visto_de_pe, True, True
    return visto_de_pe, ja_avisado, False


def _avisar(mensagem):
    # MB_ICONWARNING (0x30) + MB_SYSTEMMODAL (0x1000): fica por cima de
    # qualquer janela, mesmo sem ninguém ter focado nela antes. Só a
    # biblioteca padrão do Python, sem instalar nada (24/09/2026).
    ctypes.windll.user32.MessageBoxW(
        0, mensagem, "O trabalhador parou", 0x30 | 0x1000)


def vigiar():
    if os.name != "nt":
        print("Este aviso é só para Windows, onde o trabalhador roda hoje.")
        return
    visto_de_pe = False
    ja_avisado = False
    while True:
        if not fila.parada_pedida():
            de_pe, sinal = fila.trabalhador_de_pe()
            visto_de_pe, ja_avisado, avisar_agora = decidir_estado(
                visto_de_pe, de_pe, ja_avisado, sinal)
            if avisar_agora:
                _avisar(
                    "O trabalhador (janela 1 de 2) parou de responder.\n\n"
                    f"Último sinal de vida: {sinal.get('atualizado_em') or 'nunca'}.\n\n"
                    "Nada está sendo baixado nem analisado agora. Suba o "
                    "trabalhador de novo (iniciar_trabalhador.bat).")
        time.sleep(SEGUNDOS_ENTRE_CONFERENCIAS)


if __name__ == "__main__":
    try:
        with trava.travar(ARQUIVO_TRAVA_VIGIA, segundos_limite=5):
            vigiar()
    except TimeoutError:
        print("Já existe um vigia rodando nesta máquina. Saindo.")
