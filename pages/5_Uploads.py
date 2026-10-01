# -*- coding: utf-8 -*-
"""
Página "Uploads" do app de validação (Streamlit multipágina).

CRIADA EM 23/09/2026, separando de "Downloads" o que não é fila automatizada
do Instagram: as três formas de entrar com material sem o programa ir buscar
ele sozinho. Pedido do auditor, olhando a tela de Downloads com mais de 1250
linhas misturando a fila com os dois caminhos manuais que já existiam.

A ORDEM É DO MAIS FREQUENTE PARA O MAIS EXCEPCIONAL, pedido do auditor:

    1. Vídeo bruto      qualquer um manda, sem exigir nada além do handle
    2. Link             registro sem baixar, ainda sem exigir papel especial
    3. Enviar arquivo    exige SUPERVISÃO, e é a ação mais rara das três

A lógica de verdade mora em fluxo_downloads.py, igual à página de Downloads:
esta é só a camada visual.
"""
import os
import sys

import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import acesso
import estilo
import fila_trabalho
import fluxo_downloads as fluxo
import identidade

# QUEM PODE ABRIR, conferido AQUI também (mesmo motivo da página de
# Downloads): esta é uma rota própria do Streamlit, alcançável sem o
# painel.py rodar antes.
acesso.exigir_login()

estilo.cabecalho(
    "Uploads",
    "Três jeitos de entrar com material sem o programa baixar sozinho.",
)

# MOVIDO DE pages/1_Downloads_e_Organizacao.py EM 24/09/2026: quem gera o
# status "NAO RECONHECIDO" é o envio de arquivo (nome fora do padrão
# "DD/MM - @handle - tela N"), não o link colado na tela de Downloads. O
# card ficou lá, contando resultado desta tela, desde que as duas se
# separaram em 23/09, sem ninguém notar até o auditor estranhar o número.
_nao_reconhecidos_envio = [
    l for l in fluxo.ler_log()
    if l["status"] == "NAO RECONHECIDO" and l.get("estagio") == "ENVIO"]
st.metric("Nomes de arquivo não reconhecidos (acumulado)", len(_nao_reconhecidos_envio),
         help="O nome do arquivo enviado não bateu com o padrão "
              "\"DD/MM - @handle - tela N\". Informe o influenciador e a "
              "data na tela, em vez de depender só do nome do arquivo.")

# ------------------------------------------------------------------
# 1. Vídeo bruto
# ------------------------------------------------------------------
st.subheader("Vídeo bruto")
st.caption(
    "O influenciador manda antes, só para o time conferir que está tudo "
    "certo. Não é a peça publicitária final: não vai para a validação "
    "regulatória, e não cria linha na Monitoramento."
)

with st.form("enviar_video_bruto", clear_on_submit=True):
    videos_brutos = st.file_uploader(
        "Vídeo (sem edição)",
        # SÓ VÍDEO, e não imagem: "vídeo bruto" é o nome da pasta, e é
        # material de conferência de vídeo, não foto de post orgânico
        # (que continua entrando por "Enviar arquivo do post").
        type=["mp4", "mov", "webm", "m4v"],
        accept_multiple_files=True,
    )
    b1, b2 = st.columns([2, 1])
    _opcoes_influ_bruto = sorted(fluxo.handles_do_cadastro() or [])
    influ_bruto = b1.selectbox(
        "Influenciador (@handle)", options=[""] + _opcoes_influ_bruto,
        format_func=lambda h: "escolher..." if not h else f"@{h}",
        key="influ_bruto",
        help=None if _opcoes_influ_bruto else
        "Não consegui ler o cadastro agora; confirme o @ com cuidado.")
    marca_bruto = b2.selectbox(
        "Marca", options=[""] + fluxo.MARCAS, key="marca_bruto",
        format_func=lambda m: "escolher..." if not m else fluxo.ROTULO_MARCA[m],
        help=fluxo.ajuda_campo_marca(forma_curta=True))
    enviar_bruto = st.form_submit_button(
        "Enviar", icon=":material/upload:", type="primary")

if enviar_bruto:
    if not videos_brutos:
        st.warning("Escolha pelo menos um vídeo antes de enviar.")
    elif not influ_bruto:
        st.warning("Escolha o influenciador antes de enviar.")
    elif not marca_bruto:
        st.warning(fluxo.aviso_marca_vazia())
    else:
        # MESMO PADRÃO DE guardar_envio + fila (30/08/2026, herdado da seção
        # "Enviar arquivo do post"): a tela só guarda e enfileira, quem sobe
        # de verdade é o trabalhador.
        guardados = []
        for arq in videos_brutos:
            try:
                caminho = fluxo.guardar_envio(arq.name, arq.getbuffer())
                guardados.append({"caminho": caminho, "nome": arq.name})
            except Exception as e:
                st.error(f"Não consegui guardar {arq.name}: {str(e)[:160]}")

        if guardados:
            fila_trabalho.criar(
                fila_trabalho.ENVIAR_VIDEO_BRUTO,
                {
                    "arquivos": guardados,
                    "campos": {
                        "handle": influ_bruto,
                        "marca": marca_bruto,
                        "pedido_por": identidade.quem_sou_eu(),
                    },
                },
                rotulo=f"{len(guardados)} vídeo(s) bruto(s) · @{influ_bruto}",
                criada_por=identidade.quem_sou_eu(),
            )
            st.session_state["bruto_mandado"] = len(guardados)
            st.rerun()

if st.session_state.pop("bruto_mandado", None):
    st.success("Vídeo recebido e na fila. O trabalho segue mesmo se você fechar a aba.")

st.divider()

# ------------------------------------------------------------------
# 2. Link só para registrar
# ------------------------------------------------------------------
# MOVIDO DE pages/1_Downloads_e_Organizacao.py EM 23/09/2026, sem mudar
# comportamento. Comentários originais preservados.
#
# TÍTULO ENCURTADO NO MESMO DIA, pedido do auditor: "sem baixar" já está na
# ajuda (o "?" ao lado), e a página inteira já se chama Uploads, então o
# título ficava repetindo o óbvio.
st.subheader(
    "Link só para registrar",
    help="Para YouTube, live e gravação, grandes demais pra baixar. Vai "
         "pra Monitoramento como registro; conferência manual.")

with st.form("registrar_link", clear_on_submit=True):
    link_externo = st.text_input("Endereço do vídeo ou da live", placeholder="https://www.youtube.com/...")
    c1, c2, c3, c4 = st.columns(4)
    # SELECTBOX NO LUGAR DE TEXTO LIVRE (16/09/2026), pedido do auditor:
    # digitar o @ à mão é onde o erro de handle acontece (a linha entra
    # com um handle que não é o do cadastro, e as colunas C a J saem
    # vazias). As opções vêm do próprio cadastro, mesma fonte já usada
    # pelo seletor de influenciador do Financeiro.
    _opcoes_influ_link = sorted(fluxo.handles_do_cadastro() or [])
    influ_link = c1.selectbox(
        "Influenciador (@handle)", options=[""] + _opcoes_influ_link,
        format_func=lambda h: "escolher..." if not h else f"@{h}",
        help=None if _opcoes_influ_link else
        "Não consegui ler o cadastro agora; confirme o @ com cuidado.")
    data_link = c2.date_input("Data do vídeo", value=None, format="DD/MM/YYYY")
    ciclo_link = c3.text_input("Ciclo", placeholder=fluxo.PLACEHOLDER_CAMPO_CICLO,
                               help=fluxo.ajuda_campo_ciclo())
    marca_link = c4.selectbox("Marca", options=[""] + fluxo.MARCAS, key="marca_link",
                              format_func=lambda m: "escolher..." if not m else fluxo.ROTULO_MARCA[m])
    # O tipo é deduzido do endereço só como sugestão inicial; continua obrigatório
    # confirmar, porque o mesmo endereço do YouTube pode ser LIVE ou vídeo comum
    # e só quem registrou sabe qual dos dois é.
    sugestao_tipo = fluxo.tipo_pelo_link(link_externo) if link_externo else ""
    opcoes_tipo = [""] + fluxo.TIPOS_VIDEO_EXTERNO
    tipo_link = st.selectbox(
        "Tipo do post", options=opcoes_tipo,
        index=opcoes_tipo.index(sugestao_tipo) if sugestao_tipo in opcoes_tipo else 0,
        key="tipo_link", format_func=lambda t: "escolher..." if not t else t,
        help="Só vídeo de fora do Instagram. Story, Feed e Reels usam a "
             "fila da página de Downloads.")
    # HORAS DE LIVE ENTROU EM 04/09/2026, a pedido do auditor. Só faz sentido
    # para o tipo LIVE: o programa não assiste a transmissão, então a duração só
    # existe se quem está registrando souber e digitar. Fica sempre visível
    # dentro do formulário, e não escondida atrás do tipo escolhido, porque um
    # st.form não atualiza a tela sozinho a cada escolha, só quando é enviado; a
    # obrigatoriedade é o que muda, não a visibilidade.
    #
    # FORMATO HH:MM:SS, E NÃO NÚMERO DECIMAL (mudou no mesmo dia). Pedido do
    # auditor: "é exatamente como tá na planilha deles". Texto livre em vez de
    # number_input porque hora tem três partes (hora, minuto, segundo), e um
    # campo numérico só teria uma; a conferência do formato acontece no envio.
    horas_live_link = st.text_input(
        "Horas de live", placeholder="00:00:00",
        # AJUDA REESCRITA EM 17/09/2026: "0150" pensando em 1h50 saía
        # calado como 1min50, porque com menos de 5 dígitos seguidos não
        # dá pra saber se sobrou hora ou minuto (ver normalizar_horas_live).
        # A ajuda agora só recomenda os dois formatos que não têm essa
        # dúvida: os dois-pontos, ou todos os 6 dígitos.
        help="Só obrigatório se o tipo for LIVE. Use os dois-pontos "
             "(1:50) ou digite tudo (015000 para 1h50min).")
    registrar_link = st.form_submit_button("Registrar na Monitoramento",
                                           icon=":material/add_link:",
                                           type="primary")

if registrar_link:
    influ_link_final = (influ_link or "").strip()
    # O ciclo saiu daqui em 31/08/2026: ele é descoberto pela data, que já é
    # exigida logo acima. Ver registrar_link_externo.
    faltando = [rotulo for valor, rotulo in (
        (link_externo, "endereço"), (influ_link_final, "influenciador"), (data_link, "data"),
        (marca_link, "marca"), (tipo_link, "tipo do post"),
    ) if not valor]
    # Repete aqui a mesma exigência que fluxo.registrar_link_externo já faz, só
    # para a mensagem de "preencha antes" já vir completa na primeira tentativa,
    # em vez de a pessoa descobrir em duas rodadas.
    horas_live_valido = fluxo.normalizar_horas_live(horas_live_link)
    if tipo_link == "LIVE" and not horas_live_link:
        faltando.append("horas de live")
    if faltando:
        st.warning(f"Preencha antes de registrar: {', '.join(faltando)}.")
    elif tipo_link == "LIVE" and not horas_live_valido:
        # EXEMPLO TROCADO EM 17/09/2026: "013000" (6 dígitos) continua
        # valendo, mas o exemplo curto de 4 dígitos saiu daqui porque é
        # exatamente o que agora é recusado, por ser ambíguo (ver
        # normalizar_horas_live).
        st.warning('Horas de live precisa estar no formato HH:MM:SS, com '
                   'os dois-pontos (1:50) ou todos os dígitos (015000).')
    else:
        with st.status("Registrando na Monitoramento...", expanded=True) as caixa:
            r = fluxo.registrar_link_externo(
                link_externo, influ_link_final, data_link, ciclo_link,
                marca_link, tipo_link, horas_live=horas_live_link,
                quem=identidade.quem_sou_eu(), log_fn=caixa.write)
            pronto = r["status"] == "OK"
            caixa.update(label=r["destino"] if pronto else f"Não registrado: {r['status']}",
                         state="complete" if pronto else "error")
        if pronto:
            st.rerun()

st.divider()

# ------------------------------------------------------------------
# 3. Enviar arquivo do post
# ------------------------------------------------------------------
# MOVIDO DE pages/1_Downloads_e_Organizacao.py EM 23/09/2026, sem mudar
# comportamento. Comentários originais preservados.
st.subheader("Enviar arquivo do post")
# ENCURTADO EM 17/09/2026, a pedido do auditor.
st.caption(
    "Baixou o Story ou a foto no seu navegador? Arraste o arquivo aqui. "
    "Aceita vídeo e imagem, e o programa faz o resto."
)

# ESTA SEÇÃO É DE SUPERVISÃO (01/09/2026, controle interno pedido pelo auditor).
#
# POR QUE ELA, e não a tela toda: aqui a pessoa escolhe TUDO à mão, o
# influenciador, a data, o ciclo e o número da tela. Nas outras seções o programa
# descobre esses campos do próprio material, e é justamente isso que faz a
# escolha de quem usa não influir no resultado da auditoria. Aqui influi, então
# quem faz precisa poder responder por isso.
#
# O PAPEL FOI CORRIGIDO NO MESMO DIA. Nasceu como coordenação, porque o pedido
# falava da "coordenadora do setor", e o auditor esclareceu que quem autoriza é a
# supervisão de Marketing de Influência. Na lista dele, supervisão e coordenação
# são níveis distintos, e é a supervisão que aprova o pagamento do ciclo.
#
# A autorização é por IDENTIDADE, e não por senha da seção. Ver o raciocínio em
# acesso.py: senha compartilhada faz o registro dizer "alguém que sabia a senha".
_pode_enviar, _motivo_papel, _sem_prova = acesso.autorizacao_para(
    acesso.PAPEL_SUPERVISAO)

if not _pode_enviar:
    st.warning(_motivo_papel)
elif _sem_prova:
    # Liberado pela chave de teste. O aviso é vermelho de propósito: numa
    # ferramenta de auditoria, material entrando sem quem responda por ele é
    # exatamente o que este controle existe para evitar, e isso não pode ficar
    # discreto na tela.
    st.error(_motivo_papel)

with st.form("enviar_fotos", clear_on_submit=True):
    fotos = st.file_uploader(
        "Arquivo do post (vídeo ou imagem)",
        type=["mp4", "mov", "webm", "m4v", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    f1, f2, f3, f4, f5 = st.columns([2, 1.3, 1, 1, 1.3])
    # SELECTBOX NO LUGAR DE TEXTO LIVRE (16/09/2026), mesmo pedido e
    # mesmo padrão já aplicado no registro de link: "acho que ter a opção
    # do handle é legal". Vazio continua significando "descobrir
    # sozinho", que é o comportamento de sempre pra quem envia arquivo.
    _opcoes_influ_foto = sorted(fluxo.handles_do_cadastro() or [])
    influ_foto = f1.selectbox(
        "Influenciador (@handle)", options=[""] + _opcoes_influ_foto,
        # FRASE ENCURTADA EM 23/09/2026, pedido do auditor: a explicação
        # ("deixe vazio pra descobrir sozinho") ficava comprida ao lado das
        # outras, que só dizem "escolher...". A FUNCIONALIDADE CONTINUA A
        # MESMA: vazio ainda significa "descobrir sozinho" (ver o comentário
        # grande acima), só o texto de fundo do campo ficou padronizado.
        format_func=lambda h: "escolher..." if not h else f"@{h}",
        key="influ_foto",
        help=None if _opcoes_influ_foto else
        "Não consegui ler o cadastro agora; a peça sai sem influenciador escolhido.")
    data_foto = f2.date_input("Data do post", value=None, format="DD/MM/YYYY", key="data_foto")
    ciclo_foto = f3.text_input("Ciclo", placeholder=fluxo.PLACEHOLDER_CAMPO_CICLO,
                               help=fluxo.ajuda_campo_ciclo(), key="ciclo_foto")
    # PLACEHOLDER TROCADO EM 23/09/2026, pedido do auditor: "próxima" dizia o
    # que acontece se deixar vazio, mas não dizia o que o campo é, pra quem
    # olha rápido. "número da tela" diz o campo; o comportamento de vazio
    # continua o mesmo, explicado no help abaixo.
    tela_foto = f4.text_input("Tela", placeholder="número da tela", key="tela_foto",
                              # ENCURTADO EM 17/09/2026.
                              help="Vazio continua de onde parou. Enviando "
                                   "várias, a numeração segue daqui.")
    marca_foto = f5.selectbox("Marca *", options=[""] + fluxo.MARCAS, key="marca_foto",
                              format_func=lambda m: "escolher..." if not m else fluxo.ROTULO_MARCA[m],
                              help=fluxo.ajuda_campo_marca(forma_curta=True))
    # FRASE PADRONIZADA EM 23/09/2026, mesmo pedido do influenciador: "a
    # pessoa não precisa saber que essa funcionalidade existe". Vazio
    # continua significando "descobrir sozinho pelo próprio material" (ver
    # processar_arquivo_enviado), só deixou de dizer isso na tela.
    tipo_foto = st.selectbox("Tipo do post", options=[""] + fluxo.TIPOS, key="tipo_foto",
                             format_func=lambda t: "escolher..." if not t else t)
    # A MARCAÇÃO TAMBÉM AQUI (01/09/2026, virou escolha de três em 03/09/2026).
    #
    # Este é o caminho por onde a FOTO entra, e foto entra bastante: as pastas
    # "orgânico" que já existem no Drive deles têm 11 imagens e 6 vídeos, ou seja
    # a maioria do material orgânico é imagem. Deixar a escolha só na seção do
    # link do Instagram faria justamente o caso mais comum ficar sem ela.
    #
    # VALE PARA O ENVIO INTEIRO, e não por arquivo. Mais simples de usar e mais
    # simples de explicar: quem tem uma peça orgânica e uma com link no mesmo
    # arraste faz dois envios. Marcação por arquivo exigiria uma tabela de
    # marcação, que é muito clique para um caso que não é o comum.
    marcacao_foto = st.radio(
        "O que são estas peças?", key="marcacao_foto",
        options=list(fluxo.ROTULO_DA_MARCACAO),
        format_func=lambda chave: fluxo.ROTULO_DA_MARCACAO[chave],
        horizontal=True,
        help=fluxo.ajuda_campo_marcacao(forma_curta=True))
    enviar_fotos = st.form_submit_button(
        "Enviar e organizar", icon=":material/upload:", type="primary",
        disabled=not _pode_enviar,
        help=None if _pode_enviar else "Esta parte é da supervisão.")

if enviar_fotos:
    # Confere de novo aqui, e não só ao desenhar o botão. Botão desabilitado é
    # aparência: quem tiver o estado da página de antes ainda pode chegar neste
    # ponto, e a autorização precisa valer onde a ação acontece.
    _pode_agora, _motivo_agora, _ = acesso.autorizacao_para(acesso.PAPEL_SUPERVISAO)
    if not _pode_agora:
        st.warning(_motivo_agora)
    elif not fotos:
        st.warning("Escolha pelo menos um arquivo antes de enviar.")
    elif not marca_foto:
        st.warning(fluxo.aviso_marca_vazia())
    else:
        # A TELA SÓ GUARDA E ENFILEIRA (30/08/2026).
        #
        # Antes ela organizava cada arquivo na hora, um por um. Cada um lista
        # o Drive algumas vezes e lê a Monitoramento inteira, então com 25
        # arquivos a tela ficava presa por minutos e a planilha era lida 25
        # vezes. Agora guarda os arquivos e cria uma tarefa; quem organiza é o
        # trabalhador, como no resto do programa.
        #
        # Com vários arquivos, a numeração de tela avança junto: senão todos
        # sairiam com o mesmo número e o nome deixaria de identificar cada um.
        # Quem faz essa contagem agora é o trabalhador, que sabe a ordem.
        guardados = []
        for arq in fotos:
            try:
                caminho = fluxo.guardar_envio(arq.name, arq.getbuffer())
                guardados.append({"caminho": caminho, "nome": arq.name})
            except Exception as e:
                st.error(f"Não consegui guardar {arq.name}: {str(e)[:160]}")

        if guardados:
            fila_trabalho.criar(
                fila_trabalho.ENVIAR_ARQUIVOS,
                {
                    "arquivos": guardados,
                    "campos": {
                        "handle": influ_foto or None,
                        # A tarefa é gravada em JSON, que não guarda data como
                        # objeto. Vai como texto e volta a ser data no
                        # trabalhador.
                        "data": data_foto.isoformat() if data_foto else None,
                        "ciclo": ciclo_foto or None,
                        "marca": marca_foto or None,
                        "tipo": tipo_foto or None,
                        "marcacao": marcacao_foto,
                        # Quem enviou, para a coluna PEDIDO_POR. Aqui a tarefa
                        # SERVE como lugar, ao contrário da fila de links: um
                        # envio de arquivo é de uma pessoa só, do começo ao fim.
                        "pedido_por": identidade.quem_sou_eu(),
                        "tela": int(tela_foto) if str(tela_foto).strip().isdigit() else None,
                    },
                },
                rotulo=f"{len(guardados)} arquivo(s) enviado(s)",
                criada_por=identidade.quem_sou_eu(),
            )
            st.session_state["envio_mandado"] = len(guardados)
            st.rerun()

if st.session_state.pop("envio_mandado", None):
    st.success("Arquivos recebidos e na fila. O trabalho segue mesmo se você fechar a aba.")

st.divider()

# ------------------------------------------------------------------
# Acompanhamento dos envios desta página (vídeo bruto + arquivo do post)
# ------------------------------------------------------------------
# MESMA TÉCNICA da página de Downloads (acompanhar_download), mas só para os
# dois tipos que moram aqui. BAIXAR_FILA fica de fora de propósito: aquele
# acompanhamento tem texto específico de pausa do Instagram que não se aplica
# a upload de arquivo nenhum.
_TIPOS_DESTA_TELA = (fila_trabalho.ENVIAR_ARQUIVOS, fila_trabalho.ENVIAR_VIDEO_BRUTO)

# MESMO CÁLCULO DA PÁGINA DE DOWNLOADS: relê rápido só enquanto há trabalho
# desta página rodando, e devagar quando não há, para não pesar a planilha
# à toa em quem está com a tela aberta sem fazer nada.
_intervalo_upload = 3 if any(fila_trabalho.ha_trabalho(t) for t in _TIPOS_DESTA_TELA) else 15


def _listar_dos_dois(situacao):
    tarefas = []
    for tipo in _TIPOS_DESTA_TELA:
        tarefas.extend(fila_trabalho.listar(situacao, tipo))
    tarefas.sort(key=lambda t: t.get("criada_em") or "")
    return tarefas


@st.fragment(run_every=_intervalo_upload)
def acompanhar_uploads():
    em_andamento = _listar_dos_dois(fila_trabalho.RODANDO)
    esperando = _listar_dos_dois(fila_trabalho.PENDENTE)

    tem_trabalho = bool(em_andamento or esperando)
    tinha_trabalho = st.session_state.get("tinha_upload_na_fila", False)
    st.session_state["tinha_upload_na_fila"] = tem_trabalho

    if esperando and not em_andamento:
        _de_pe_agora, _ = fila_trabalho.trabalhador_de_pe()
        if _de_pe_agora:
            st.info(f"{len(esperando)} na fila, esperando o processo pegar.")
        else:
            st.error(
                f"**{len(esperando)} na fila, e ninguém vai pegar:** o "
                f"processo está fora do ar. Suba ele (dois cliques em "
                f"`iniciar_trabalhador.bat`) e ele pega sozinho o que ficou "
                f"esperando."
            )

    for tarefa in em_andamento:
        verbo = ("Organizando o vídeo bruto"
                 if tarefa.get("tipo") == fila_trabalho.ENVIAR_VIDEO_BRUTO
                 else "Organizando os arquivos enviados")
        st.caption(f"{verbo} desde {tarefa.get('comecou_em', '')[11:16]}, "
                   f"pedido por {tarefa.get('criada_por', '')}.")
        mensagens = tarefa.get("mensagens") or []
        if mensagens:
            st.code("\n".join(mensagens[-25:]), language=None)

    if tinha_trabalho and not tem_trabalho:
        st.rerun(scope="app")

    if tem_trabalho:
        return

    ultimas = sorted(
        [t for tipo in _TIPOS_DESTA_TELA
         for t in fila_trabalho.ultimas_terminadas(tipo, quantas=1)],
        key=lambda t: t.get("terminou_em") or "", reverse=True,
    )
    if ultimas:
        recente = ultimas[0]
        aparencia, texto, motivos = fluxo.resumo_da_tarefa(recente)
        if aparencia == "erro":
            st.error(texto)
        elif aparencia == "atencao":
            st.warning(texto)
        elif aparencia == "nada":
            st.info(texto)
        else:
            st.success(texto)
        for motivo in motivos:
            st.caption(f"   {motivo}")
        mensagens_da_tarefa = [str(m) for m in (recente.get("mensagens") or [])]
        if mensagens_da_tarefa:
            with st.expander("Ver o que aconteceu"):
                st.code("\n".join(mensagens_da_tarefa), language=None)
        st.caption("Some sozinha depois de 48 horas.")


acompanhar_uploads()
