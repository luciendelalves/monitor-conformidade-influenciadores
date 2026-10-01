# -*- coding: utf-8 -*-
"""
Bloco de tela que mostra se o programa que executa as tarefas está de pé.

Fica num arquivo só, usado pelas duas telas, porque o aviso precisa ser o
mesmo nas duas: quem clica em "baixar" e quem clica em "analisar" depende do
mesmo trabalhador, e ver um aviso diferente em cada tela confundiria.

Existe desde 29/08/2026, junto com o trabalhador. Antes o trabalho acontecia
dentro da própria tela, então não havia nada que pudesse estar fora do ar.
"""
import os

import streamlit as st

import estilo
import fila_trabalho as fila

PASTA_DO_PROGRAMA = os.path.dirname(os.path.abspath(__file__))


def mostrar_situacao():
    """Avisa se ninguém está executando as tarefas. Devolve True quando está
    tudo certo, para a tela poder desabilitar botão se quiser."""
    de_pe, sinal = fila.trabalhador_de_pe()
    esperando = fila.contar(fila.PENDENTE)

    if not de_pe:
        # UMA LINHA, COM O DETALHE ESCONDIDO (05/09/2026).
        #
        # Este aviso tinha três parágrafos mais o caminho da pasta, e o auditor
        # cortou: "vc coloca muito aviso e fica poluindo a tela". Ele estava
        # certo, e a terceira vez que apontou isso no mesmo dia.
        #
        # O QUE FICA VISÍVEL é só o que muda a decisão de quem lê: nada roda
        # agora. O COMO subir é instrução, e instrução só interessa a quem
        # decidiu subir, então mora no expansor. A cor vermelha continua,
        # porque isto de fato bloqueia o programa inteiro.
        st.error(
            "**Ninguém está executando as tarefas agora.** O que for pedido "
            "fica na fila."
            + (f" Há **{esperando}** esperando." if esperando else "")
        )
        with st.expander("Como subir o processo"):
            st.markdown(
                "Dê dois cliques em `iniciar_trabalhador.bat`, ou abra o "
                "Prompt de Comando na pasta do programa e rode "
                "`py trabalhador.py`. **A janela precisa ficar aberta.**\n\n"
                f"Pasta: `{PASTA_DO_PROGRAMA}`"
            )
        return False

    fazendo = sinal.get("fazendo_agora") or []
    if sinal.get("encerrando"):
        st.warning("O processo está encerrando. Ele termina o que já começou e não "
                   "pega mais nada novo.")
    elif fazendo:
        # SEM O ✅ VERDE (08/09/2026). "Trabalhando agora" é estado de rotina, e
        # verde é reservado para veredito de conformidade da peça. Gastar a cor
        # do veredito em encanamento tira força de quem precisa dela. Ver o
        # comentário de .egb-nota em estilo.py.
        estilo.nota(f"Trabalhando agora em: <b>{', '.join(fazendo)}</b>.")
    else:
        estilo.nota("Processo de pé e sem nada em andamento.")
    return True


def botao_encerrar(key_sufixo=""):
    """Pede o encerramento sem cortar trabalho no meio.

    Existe porque alterar arquivo do programa com lote rodando derruba o lote,
    e porque no servidor vai ser preciso encerrar para atualizar. É pedido, e
    não interrupção: ele termina o que está fazendo antes de sair.

    ALCANCE AVISADO NA TELA, decidido pelo auditor em 31/08/2026. Existe UM
    trabalhador para as cinco pessoas, então quem encerra encerra o de todas, e
    até aqui o texto não dizia isso: lia como se fosse ação local de quem
    clicou. As duas opções em cima da mesa eram avisar ou tirar o botão da tela
    dos analistas. Ficou avisar, porque encerrar antes de atualizar é o
    procedimento correto, e tirar obrigaria a chamar o administrador para uma
    operação legítima e frequente.

    Quando há trabalho em andamento ou na fila, o botão só libera depois de
    marcar ciência. Sem nada rodando não custa clique nenhum, e é esse o caso
    comum de quem vai atualizar o programa.

    `key_sufixo` EXISTE DESDE 17/09/2026: a condição de "atualizar exige
    processo parado" já travava o botão de atualizar (`disabled=_de_pe`),
    mas o botão que resolve isso morava só lá embaixo, numa seção
    "Manutenção" solta, longe de onde a pessoa estava. Agora esta função
    aparece também dentro de "Cuidar das bibliotecas de download", e o
    sufixo evita colidir os `key=` fixos quando ela desenha duas vezes na
    mesma página."""
    de_pe, sinal = fila.trabalhador_de_pe()
    rodando = fila.contar(fila.RODANDO)
    esperando = fila.contar(fila.PENDENTE)
    with st.popover("Encerrar o processo", icon=":material/power_settings_new:",
                    use_container_width=True, disabled=not de_pe,
                    key=f"popover_encerrar{key_sufixo}"):
        # TEXTO ENCURTADO EM 14/09/2026: eram dois parágrafos (~9 linhas), e
        # aviso comprido é aviso que ninguém lê. Os dois fatos que precisam
        # chegar continuam aqui, só que num parágrafo só.
        #
        # "PROCESSO" NO LUGAR DE "TRABALHADOR" (15/09/2026), pedido do
        # auditor: "trabalhador" soava como se fosse uma pessoa de verdade
        # ("encerrar o trabalhador" lia estranho). O nome do arquivo
        # (trabalhador.py) e o comando de subir não mudaram, só o texto que
        # aparece pra quem usa a tela.
        st.caption(
            "Afeta todas as pessoas que usam o programa, não só você: existe um "
            "processo só. Ele termina o que já começou e nada em andamento se "
            "perde, o que não tiver terminado volta para a fila quando ele subir "
            "de novo."
        )

        liberado = True
        if rodando or esperando:
            situacao = []
            if rodando:
                situacao.append(f"{rodando} em andamento")
            if esperando:
                situacao.append(f"{esperando} esperando na fila")
            st.warning("Há " + " e ".join(situacao) + " neste momento.")
            for item in (sinal.get("fazendo_agora") or []):
                st.caption(f"   {item}")
            liberado = st.checkbox(
                "Estou ciente de que isso alcança o trabalho das outras pessoas",
                key=f"ciente_de_encerrar_o_trabalhador{key_sufixo}",
            )

        if st.button("Encerrar agora", type="primary", disabled=not liberado,
                     key=f"btn_encerrar_agora{key_sufixo}"):
            fila.pedir_parada()
            st.success("Pedido enviado. Ele sai assim que terminar o que está fazendo.")
