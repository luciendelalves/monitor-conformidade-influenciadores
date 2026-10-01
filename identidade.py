# -*- coding: utf-8 -*-
"""
Quem está usando o programa.

ISTO NÃO É LOGIN, E A DISTINÇÃO IMPORTA (29/08/2026)

O nome aqui é DECLARADO pela própria pessoa, sem senha e sem verificação.
Qualquer um pode escrever qualquer coisa. Serve para as cinco pessoas se
coordenarem entre si, não para controlar acesso, e em nenhum lugar deve ser
usado como prova de quem fez o quê numa evidência de auditoria.

POR QUE EXISTE MESMO ASSIM

Sem nada, o programa registra o usuário do COMPUTADOR onde ele roda. Num
servidor, isso é a mesma resposta para as cinco pessoas, o que produz dois
problemas concretos:

  1. A coluna "Pedido por" mostra sempre o mesmo nome, e mente sem parecer que
     mente.
  2. Não dá para separar "tirar da fila o que EU mandei" de "tirar o que todo
     mundo mandou". Sem essa separação, um clique de uma pessoa desfaz o
     trabalho das outras quatro.

Um nome declarado resolve os dois, e é honesto desde que apresentado como o
que é.

QUANDO O LOGIN CHEGAR

`quem_sou_eu` já procura primeiro pela pessoa autenticada. No dia que o login
existir, ela passa a devolver o e-mail de verdade sozinha, o campo da barra
lateral some (ver campo_na_barra_lateral) e nada mais precisa mudar.
"""
import os
import sys

import streamlit as st

CHAVE = "nome_de_quem_usa"

# Onde o nome fica guardado entre uma visita e outra.
#
# No ENDEREÇO da página, não num arquivo (30/08/2026). Guardar em arquivo do
# servidor seria o erro óbvio: o servidor é um só, então o nome de uma pessoa
# valeria para as cinco, que é exatamente o problema que este campo existe
# para resolver.
#
# No endereço, cada pessoa carrega o seu no próprio navegador, e ele sobrevive
# a recarregar a página e a fechar e abrir a aba, desde que o endereço seja o
# mesmo. Vale guardar nos favoritos.
#
# Ressalva: quem copiar o endereço e mandar para outra pessoa manda o nome
# junto. Como é nome declarado e não credencial, o estrago é a pessoa aparecer
# com o nome errado até corrigir o campo. Quando houver login, isto tudo sai.
CHAVE_NO_ENDERECO = "eu"


def _ler_do_endereco():
    """Recupera o nome guardado no endereço, se ainda não houver um na sessão."""
    if st.session_state.get(CHAVE):
        return
    try:
        guardado = st.query_params.get(CHAVE_NO_ENDERECO)
    except Exception:
        return
    if guardado:
        st.session_state[CHAVE] = str(guardado)


def _guardar_no_endereco():
    """Chamado quando a pessoa mexe no campo."""
    nome = str(st.session_state.get(CHAVE) or "").strip()
    try:
        if nome:
            if st.query_params.get(CHAVE_NO_ENDERECO) != nome:
                st.query_params[CHAVE_NO_ENDERECO] = nome
        elif CHAVE_NO_ENDERECO in st.query_params:
            del st.query_params[CHAVE_NO_ENDERECO]
    except Exception:
        pass


def pessoa_autenticada():
    """E-mail de quem entrou, quando houver login de verdade. None se não há."""
    try:
        usuario = getattr(st, "user", None)
        if usuario is None:
            return None
        try:
            email = usuario.get("email")
        except Exception:
            email = getattr(usuario, "email", None)
        return str(email) if email else None
    except Exception:
        return None


def usuario_do_computador():
    return os.environ.get("USERNAME") or os.environ.get("USER") or "desconhecido"


def quem_sou_eu():
    """Nome a registrar nas tarefas, na ordem de confiança."""
    autenticada = pessoa_autenticada()
    if autenticada:
        return autenticada
    declarado = str(st.session_state.get(CHAVE) or "").strip()
    if declarado:
        return declarado
    return usuario_do_computador()


def tenho_nome():
    """Se dá para separar o que é meu do que é dos outros."""
    return bool(pessoa_autenticada() or str(st.session_state.get(CHAVE) or "").strip())


def campo_na_barra_lateral():
    """Desenha o campo de identificação. Chamado uma vez, em painel.py, para
    aparecer em todas as abas.

    Some sozinho quando houver login: com pessoa autenticada não há o que
    declarar."""
    if pessoa_autenticada():
        with st.sidebar:
            # Escrito à mão, e não com st.caption, por dois motivos vistos na
            # tela em 31/08/2026, no primeiro uso do login:
            #
            #   1. o markdown transforma endereço de e-mail em link sozinho, e
            #      o e-mail aparecia azul e sublinhado, como se fosse para
            #      clicar. Não é: é só a informação de quem está usando
            #   2. o cinza do st.caption some no fundo escuro da barra lateral,
            #      que é o mesmo motivo já registrado mais abaixo neste arquivo
            st.markdown(
                '<div style="font-size:0.8rem;color:#9FB3CC;line-height:1.5">'
                'Você está como</div>'
                f'<div style="font-size:0.9rem;color:#FFFFFF;font-weight:600;'
                f'word-break:break-all;line-height:1.45;margin-bottom:0.35rem">'
                f'{pessoa_autenticada()}</div>',
                unsafe_allow_html=True,
            )
        return

    _ler_do_endereco()

    with st.sidebar:
        st.text_input(
            "Seu nome",
            key=CHAVE,
            placeholder="digite seu nome",
            on_change=_guardar_no_endereco,
            help="Fica registrado no que você mandar analisar ou baixar, e é o que "
                 "permite separar o seu trabalho do das outras pessoas. Fica guardado "
                 "neste navegador, então você não precisa digitar de novo. Não é "
                 "login: não tem senha e ninguém confere.",
        )
        # Texto escrito à mão em vez de st.caption: o cinza padrão do Streamlit
        # some no fundo escuro da barra lateral, e este aviso precisa ser lido
        # (apontado em 30/08/2026). A cor acompanha a do campo vazio.
        if not tenho_nome():
            st.markdown(
                '<div style="color:#F0B357;font-size:0.8rem;line-height:1.45;'
                'margin-top:-0.4rem">⚠️ Sem o nome, o programa não separa o seu '
                'trabalho do das outras pessoas.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="color:#8FD8F5;font-size:0.82rem;margin-top:-0.4rem">'
                f'Analista: <strong style="color:#FFFFFF">{quem_sou_eu()}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )
