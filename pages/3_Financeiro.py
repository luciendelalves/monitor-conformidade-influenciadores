# -*- coding: utf-8 -*-
"""
Fechamento de ciclo: cruza o ESCOPO contratado com o que foi entregue.

PEDIDO DO AUDITOR EM 03/09/2026, com as palavras dele: uma aba de financeiro que
cruze as entregas com o ESCOPO da Dados_influ, feche o ciclo, e no fim gere um
texto para a pessoa copiar e colar no WhatsApp do Financeiro solicitando o
pagamento.

O FORMATO NÃO FOI INVENTADO. Ele é a aba `Achado01_EntregaEComprovacao` da
planilha final da auditoria (confirmada por ele no Drive, 260 linhas), que já
fazia esse cruzamento à mão, com as colunas Escopo Contratado, Entregue, Não
Entregue, Status Escopo, Observação e Status Pagamento, e o vocabulário ✅ 🚫 ⏳.
Quem lê o papel de trabalho e quem lê esta tela têm que ver a mesma coisa.

A CONTA NÃO ESTÁ AQUI, está em escopo_e_entrega.py, para poder ser testada sem
abrir o Streamlit. Esta tela só mostra e registra.

O QUE ESTA TELA NÃO FAZ, de propósito: ela não autoriza pagamento. Ela confirma
ENTREGA e SOLICITA o pagamento, produzindo o texto do aviso. Quem decide pagar
e paga é o Financeiro, com o processo dele.

ELA NÃO ESCREVE NA MONITORAMENTO. Chegou a escrever por algumas horas em
05/09/2026 (edição de CRONOGRAMA e PAGAMENTO na tabela dos posts), e voltou
atrás no mesmo dia, por decisão do auditor: as duas colunas continuam
preenchidas à mão na planilha, linha por linha. Esta tela lê as duas e mostra.
O que ela GRAVA é o registro de fechamento, e desde 05/09/2026 ele vai para uma
planilha própria (ver registro_fechamentos.py) e para um arquivo local, que é a
rede quando a planilha falha.

O PAGAMENTO POR POST ("Realizado"/"Pendente", coluna PAGAMENTO da Monitoramento)
continua aparecendo na tabela dos posts, só para conferência: quem preenche é o
Marketing, à mão, e esta tela nunca escreve ali.

O FECHAMENTO DO CICLO MUDOU DE PERGUNTA EM 09/09/2026. Existia um rádio "Este
ciclo já foi pago?", que registrava o que já tinha acontecido. O auditor
apontou o problema: "o pagamento vem depois do ciclo fechado... essa mensagem
é para pagamento do ciclo, e não do escopo". O fluxo real é ESCOPO → ciclo
entregue → SOLICITA o pagamento → ciclo seguinte, e perguntar "já foi pago?"
no meio disso pressupõe a ordem errada. Agora o fim da tela é um botão só,
"Solicitar pagamento": se o ciclo bate com o escopo, solicita direto; se está
diferente (faltou quantidade, ou veio composição fora do contrato), exige
justificativa antes, e a justificativa mais quem fechou ficam gravados no
registro. Ver escopo_e_entrega.fechar_ciclo (campo exige_justificativa).
"""
import collections
import csv
import os
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import acesso
import calendario_divulgacoes as calendario
import escopo_e_entrega as ee
import estilo
import fluxo_downloads as fluxo
import identidade
import registro_fechamentos
import sheets_client

# A SEÇÃO "FECHAR O CICLO" ESTÁ DESLIGADA DESDE 11/09/2026, a pedido do
# auditor: "não era pra excluir a aba de financeiro, mas sim a parte do ciclo
# fechado". A tela continua abrindo e conferindo escopo contra entrega e o
# cronograma do Calendário; o que sai é só o fim dela, a justificativa, o
# botão "Solicitar pagamento", o texto para o WhatsApp e a gravação no
# registro de fechamentos. NADA FOI APAGADO: o código inteiro continua abaixo,
# só guardado atrás desta chave, para religar bastando trocar False por True.
FECHAMENTO_DE_CICLO_ATIVO = False

acesso.exigir_login()

estilo.cabecalho(
    "Financeiro",
    # ENCURTADA DE NOVO EM 17/09/2026, mesmo pedido da tela de Downloads.
    "Cruza o escopo contratado com o que foi entregue no ciclo.",
)

# ONDE O FECHAMENTO FICA REGISTRADO: nos DOIS, planilha e arquivo local.
#
# A PENDÊNCIA QUE ESTAVA ESCRITA AQUI FOI RESOLVIDA EM 05/09/2026. Ela dizia que
# o certo era virar planilha, "para o Marketing e o Financeiro lerem sem
# depender desta máquina". O auditor cobrou ao perguntar onde a justificativa
# ia parar, e a resposta era ruim: texto do WhatsApp e CSV nesta máquina.
#
# Virou planilha PRÓPRIA, não aba da Monitoramento. Ver registro_fechamentos.py
# para as quatro razões (grão, dono, público e sobrevivência).
#
# O ARQUIVO LOCAL CONTINUA, como rede. Se a planilha não estiver configurada ou
# a escrita falhar (rede fora, token expirado), o fechamento não se perde.
# Perder registro de auditoria por falha de rede seria pior que ter o dado em
# dois lugares.
ARQUIVO_FECHAMENTOS = os.path.join(fluxo.PASTA_TESTE, "fechamentos_ciclo.csv")
# "pagamento", "achado" e "justificativa_pagamento" SAÍRAM DAQUI EM
# 09/09/2026, junto com o rádio "já foi pago?" que os alimentava (ver o
# docstring do módulo). A pergunta que sobrou é uma só, "por que autorizar
# a solicitação mesmo com o ciclo diferente do escopo?", e ela já tinha
# campo próprio: "justificativa". Não criar uma coluna nova para a mesma
# pergunta.
CAMPOS_FECHAMENTO = ("quando", "quem", "influenciador", "ciclo", "marca",
                     "periodo", "escopo", "entregue", "situacao",
                     "justificativa", "decisoes",
                     # As quatro razões de uma peça não contar, separadas.
                     # Juntas num só número, "3 peças fora da cota" não diria
                     # se o problema é conformidade, acesso a arquivo, limite da
                     # automação ou análise que não rodou.
                     "pecas_reprovadas", "pecas_sem_evidencia",
                     "pecas_no_limite_da_automacao", "pecas_sem_veredito",
                     # O que o Calendário dizia no instante do fechamento. Ver
                     # o motivo em registro_fechamentos._titulo.
                     "cronograma_calendario")


def gravar_fechamento(registro):
    """Grava na planilha e no arquivo local. Devolve (na_planilha, motivo).

    A ORDEM É PROPOSITAL: o arquivo local primeiro, porque ele nunca falha por
    rede. Se a planilha falhar depois, o registro já existe em algum lugar."""
    _gravar_no_arquivo(registro)
    return registro_fechamentos.gravar(registro, CAMPOS_FECHAMENTO)


# HISTÓRICO DE ENTREGAS, SEPARADO DO FECHAMENTO (14/09/2026, ampliado em
# 16/09/2026).
#
# NASCEU COMO "Notas_Financeiro" EM 14/09: só a nota de consulta, ao lado de
# "Escopo contratado x entrega", sempre visível (não atrás de
# FECHAMENTO_DE_CICLO_ATIVO), sem gerar texto pra WhatsApp e sem "Solicitar
# pagamento" nenhum.
#
# VIROU HISTÓRICO GERAL EM 16/09/2026, pedido do auditor: a nota "precisa ser
# mais geral e mostrar também as entregas sem justificativas... uma planilha
# geral de entrega mostrando o escopo e o que foi entregue, quem fez, data e
# o que for necessário para guardar", e que apareça filtrada por
# influenciador do mesmo jeito que a Monitoramento aparece dentro do
# Monitoramento. Por isso o registro passou a guardar a fotografia inteira do
# fechamento (situação, total contratado, total entregue, o que faltou), e
# não só o texto livre; a nota continua existindo, só que agora é um campo a
# mais dentro de um registro mais completo, e pode ficar em branco quando não
# há nada a justificar.
#
# ABA PRÓPRIA, "Historico_Entregas", NA MESMA PLANILHA DE FECHAMENTOS, e não a
# aba "Fechamentos" com um marcador de tipo: são grãos diferentes (registro de
# consulta não é ciclo fechado), mesmo raciocínio que já separou esta
# planilha da Monitoramento (ver registro_fechamentos.py). O NOME DA ABA
# MUDOU JUNTO (de Notas_Financeiro para Historico_Entregas): a aba tinha
# nascido um dia antes e ainda não tinha sido entregue ao Marketing, então
# renomear agora não deixa para trás uma aba órfã.
ABA_HISTORICO_ENTREGAS = "Historico_Entregas"
# PERÍODO E ESCOPO ENTRARAM EM 16/09/2026, ao comparar estas colunas com a aba
# `Achado01_EntregaEComprovacao` do papel de trabalho, que é o molde original
# deste cruzamento (ver o topo de escopo_e_entrega.py). As duas guardam coisas
# que MUDAM depois, e é isso que as torna necessárias num histórico:
#
#   periodo  "ciclo 3" não diz QUANDO. Este projeto já mediu que o número do
#            ciclo se repete em anos diferentes (12,6% dos ciclos tinham
#            janela contaminada antes da correção de 11/09/2026), então sem a
#            data a linha antiga fica ambígua.
#   escopo   o texto do escopo vive no cadastro e é reescrito nas renovações.
#            Também está medido aqui que a coluna ESCOPO não é foto congelada.
#            Guardando só o total (um número), daqui a seis meses ninguém
#            reconstrói o que estava contratado naquele ciclo.
#
# FICARAM DE FORA, de propósito: "Status Pagamento" (quem decide pagamento é o
# Financeiro, olhando a própria Monitoramento), "Validação Data NF" (é do
# Achado 2 da RA 16, outra pergunta) e "Status Comprovação" (a situação já
# nomeia esse caso quando é ele, "Cota fecha, mas falta evidência").
# "conferido_a_mao" ENTROU EM 16/09/2026, junto com a declaração passando a
# contar no total (ver ee.CONFORME_COM_OBSERVACAO). Sem esta coluna, um ciclo
# fecharia com um número que ninguém consegue reconstruir depois: parte dele
# veio de alguém dizendo "conferi, existe", e esse alguém precisa ficar ao
# lado do número, com o que foi declarado.
CAMPOS_HISTORICO_ENTREGAS = (
    "quando", "quem", "influenciador", "ciclo", "marca", "periodo", "escopo",
    "situacao", "total_contratado", "total_entregue", "o_que_faltou",
    "conferido_a_mao", "nota")
ARQUIVO_HISTORICO_ENTREGAS = os.path.join(fluxo.PASTA_TESTE, "historico_entregas.csv")


def _resumo_o_que_faltou(fechamento):
    """Texto curto do que faltou, para a coluna 'o_que_faltou' do histórico.
    Vazio quando não faltou nada, para a planilha não repetir "nenhum" em
    milhares de linhas."""
    partes = []
    if fechamento["faltando"]:
        partes.append(", ".join(f"{t} {n}" for t, n in sorted(fechamento["faltando"].items())))
    if fechamento["fora_do_escopo"]:
        partes.append("fora do escopo: " + ", ".join(
            f"{t} {n}" for t, n in sorted(fechamento["fora_do_escopo"].items())))
    return "; ".join(partes)


def registrar_no_historico_de_entregas(influenciador, ciclo_do_registro, marca_do_registro,
                                       fechamento, nota, quem,
                                       periodo_do_registro="", escopo_do_registro="",
                                       conferido_a_mao=""):
    """Grava uma fotografia do fechamento (escopo x entrega) no histórico
    geral, na aba própria e no CSV local de reserva. Mesmo padrão de
    gravar_fechamento, com um resumo do fechamento em vez de um texto livre
    só. `nota` pode vir vazia: um ciclo sem nada a justificar também entra no
    histórico, é o que o torna GERAL e não só um mural de justificativas."""
    registro = dict(
        quando=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        quem=str(quem or ""), influenciador=str(influenciador or ""),
        ciclo=str(ciclo_do_registro or ""), marca=str(marca_do_registro or ""),
        periodo=str(periodo_do_registro or ""),
        # O TEXTO CRU DO CADASTRO, como estava neste instante. Ver o comentário
        # de CAMPOS_HISTORICO_ENTREGAS: ele é reescrito nas renovações.
        escopo=str(escopo_do_registro or ""),
        # RÓTULO EM PORTUGUÊS DE GENTE, NÃO A CONSTANTE (16/09/2026, achado ao
        # revisar as colunas pensando em quem vai usar isto: "COTA_SEM_EVIDENCIA"
        # e "COTA_NO_LIMITE_DA_AUTOMACAO" são nomes de variável do código, não
        # texto para o Marketing ler. `ee.apresentacao` já existe e já é usada
        # na própria tela para isto (a faixa colorida logo acima).
        situacao=ee.apresentacao(fechamento.get("situacao"))["curto"],
        total_contratado=str(fechamento.get("total_contratado") or 0),
        total_entregue=str(fechamento.get("total_entregue") or 0),
        o_que_faltou=_resumo_o_que_faltou(fechamento),
        conferido_a_mao=str(conferido_a_mao or ""),
        nota=str(nota or ""))
    _novo = not os.path.exists(ARQUIVO_HISTORICO_ENTREGAS)
    os.makedirs(os.path.dirname(ARQUIVO_HISTORICO_ENTREGAS), exist_ok=True)
    # A LISTA DE CAMPOS PODE CRESCER, e cresceu em 16/09/2026 (periodo e
    # escopo). Sem esta conferência, o append escreveria os valores novos
    # embaixo dos títulos antigos e o arquivo passaria a mentir em silêncio.
    # É o mesmo defeito que já aconteceu com o CSV de fechamento em
    # 03/09/2026, e a correção é a mesma: reescrever o arquivo com os títulos
    # novos, preservando o que já estava lá.
    if not _novo:
        with open(ARQUIVO_HISTORICO_ENTREGAS, encoding="utf-8", newline="") as f:
            _antigos = list(csv.DictReader(f))
            _titulos = tuple(_antigos[0].keys()) if _antigos else ()
        if _titulos and _titulos != CAMPOS_HISTORICO_ENTREGAS:
            with open(ARQUIVO_HISTORICO_ENTREGAS, "w", newline="", encoding="utf-8") as f:
                _escritor = csv.DictWriter(f, fieldnames=CAMPOS_HISTORICO_ENTREGAS)
                _escritor.writeheader()
                for _antigo in _antigos:
                    _escritor.writerow({c: _antigo.get(c, "") or ""
                                        for c in CAMPOS_HISTORICO_ENTREGAS})
    with open(ARQUIVO_HISTORICO_ENTREGAS, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS_HISTORICO_ENTREGAS)
        if _novo:
            escritor.writeheader()
        escritor.writerow(registro)
    return registro_fechamentos.gravar(registro, CAMPOS_HISTORICO_ENTREGAS,
                                       aba=ABA_HISTORICO_ENTREGAS)


@st.cache_data(ttl=60, show_spinner=False)
def _historico_de_entregas():
    """O histórico já registrado, mais novo primeiro. Vazio quando a aba
    ainda não existe ou a planilha de fechamentos não está configurada."""
    return registro_fechamentos.ler(CAMPOS_HISTORICO_ENTREGAS, aba=ABA_HISTORICO_ENTREGAS)


def _gravar_no_arquivo(registro):
    novo = not os.path.exists(ARQUIVO_FECHAMENTOS)
    os.makedirs(os.path.dirname(ARQUIVO_FECHAMENTOS), exist_ok=True)
    if not novo:
        # A LISTA DE CAMPOS PODE TER CRESCIDO DESDE O ÚLTIMO FECHAMENTO, e foi o
        # que aconteceu em 03/09/2026, quando a coluna do achado entrou no meio.
        # Sem esta conferência, o append escreveria os valores novos sob os
        # títulos antigos e o registro passaria a mentir em silêncio.
        with open(ARQUIVO_FECHAMENTOS, encoding="utf-8", newline="") as f:
            antigos = list(csv.DictReader(f))
            titulos = tuple(antigos[0].keys()) if antigos else ()
        if titulos and titulos != CAMPOS_FECHAMENTO:
            with open(ARQUIVO_FECHAMENTOS, "w", newline="", encoding="utf-8") as f:
                escritor = csv.DictWriter(f, fieldnames=CAMPOS_FECHAMENTO)
                escritor.writeheader()
                for antigo in antigos:
                    escritor.writerow({c: antigo.get(c, "") or ""
                                       for c in CAMPOS_FECHAMENTO})
    with open(ARQUIVO_FECHAMENTOS, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS_FECHAMENTO)
        if novo:
            escritor.writeheader()
        escritor.writerow({c: registro.get(c, "") for c in CAMPOS_FECHAMENTO})


# 60 SEGUNDOS, ERAM 300 (06/09/2026), pelo mesmo motivo do Monitoramento.
@st.cache_data(ttl=60, show_spinner="Lendo a Monitoramento e o cadastro...")
def carregar():
    """Entregas da Monitoramento e escopo do cadastro, numa leitura só."""
    planilha = fluxo._planilha_monitoramento_id()
    if not planilha:
        return [], {}
    # SEM TETO DE LINHA (07/09/2026). A faixa terminava em 20000, e a
    # Monitoramento real do Marketing já tem 24.334 linhas. Passando disso, a
    # entrega simplesmente não vinha: o ciclo aparecia INCOMPLETO, o aviso do
    # Financeiro saía com período e quantidade errados, e nada na tela dizia que
    # houve corte. Pedir a coluna sem número final devolve até a última linha
    # com conteúdo, que é o que se quer.
    valores = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha,
            range=f"'{fluxo.ABA_MONITORAMENTO}'!A2:{fluxo.ULTIMA_COLUNA_MON}",
        ).execute()).get("values", [])

    def campo(linha, chave):
        i = fluxo.COL_MON[chave] - 1
        return str(linha[i]).strip() if i < len(linha) and linha[i] else ""

    entregas = []
    for numero, linha in enumerate(valores, start=2):
        if not campo(linha, "handle"):
            continue
        entregas.append({
            "linha": numero,
            "handle": campo(linha, "handle"),
            "ciclo": campo(linha, "ciclo"),
            "tipo": campo(linha, "tipo"),
            "post": campo(linha, "post"),
            "marcacao": campo(linha, "marcacao"),
            "data_post": campo(linha, "data_post"),
            "marca": campo(linha, "marca"),
            "validacao": campo(linha, "validacao"),
            "arquivo": campo(linha, "arquivo") or campo(linha, "link"),
            # PAGAMENTO E CRONOGRAMA são lidas para MOSTRAR, e só. Quem as
            # preenche é uma pessoa, à mão, na planilha. Nenhuma das duas decide
            # a situação do ciclo: quem decide é o rádio no fim, escolha humana.
            "pagamento": campo(linha, "pagamento"),
            "cronograma": campo(linha, "cronograma"),
        })

    lido = fluxo._ler_cadastro_completo()
    escopos = {}
    if lido:
        _cab, por_handle = lido
        for chave, dados in por_handle.items():
            escopos[chave] = {
                "escopo": dados[9].strip() if len(dados) > 9 else "",
                "status": dados[8].strip() if len(dados) > 8 else "",
                "inicio": dados[6].strip() if len(dados) > 6 else "",
                "fim": dados[7].strip() if len(dados) > 7 else "",
            }
    return entregas, escopos


try:
    entregas, escopos = carregar()
except Exception as e:
    st.error(f"Não consegui ler os dados agora: {str(e)[:200]}")
    st.stop()

if not entregas:
    st.info("A Monitoramento de teste ainda não tem entrega registrada.")
    st.stop()

# A EXPLICAÇÃO DE ONDE VEM CADA NÚMERO VIROU help DO SELETOR (16/09/2026,
# enxugamento pedido pelo auditor): era um parágrafo sempre visível no topo,
# acima do campo em que se trabalha. O fato continua a um clique de distância,
# para quem precisar saber de onde sai a conta.
_topo_esq, topo_dir = st.columns([4, 1])
if topo_dir.button("Atualizar agora", icon=":material/refresh:",
                   use_container_width=True):
    carregar.clear()
    st.rerun()

# --- a planilha desta tela, SEMPRE VISÍVEL -----------------------------
#
# CADA TELA MOSTRA A PLANILHA DELA (16/09/2026, pedido do auditor): a
# Monitoramento mostra a Monitoramento, o Cadastro mostra a Dados_influ, e o
# Financeiro passou a mostrar a planilha de histórico, com o mesmo trio de
# filtros do Cadastro (Situação/Influenciador/Procurar) e a mesma contagem
# "N de M".
#
# SUBIU PARA O TOPO DA TELA (17/09/2026, pedido do auditor): morava no fim,
# atrás da escolha de influenciador/ciclo, e por isso sumia sempre que
# ninguém tinha escolhido um influenciador ainda (a tela para ali com "Escolha
# um influenciador para começar"). É consulta, não depende de nada que vem
# depois, então não faz sentido ela desaparecer por causa de um filtro de
# outra seção. O filtro de Influenciador AQUI DENTRO também não parte mais
# do que está escolhido lá embaixo (não dava mais para isso, essa seção
# roda antes); abre sempre em "Todos", e continua podendo trocar.
with st.container(key="fin_zona_historico"):
    # ROTULADA COMO CONSULTA (17/09/2026), pedido do auditor: esta seção é
    # só leitura e filtro, sem ação nenhuma, diferente do resto da tela.
    # Mesmo estilo do rótulo pequeno usado no cabeçalho das telas
    # (estilo.cabecalho), reaproveitado aqui por seção.
    st.markdown('<div class="egb-eyebrow">Consulta</div>', unsafe_allow_html=True)
    st.subheader(
        "Histórico de entregas",
        # ENCURTADO EM 17/09/2026, pedido do auditor de resumir todo help=.
        help="Cada linha é um ciclo já registrado, com escopo, total "
             "entregue e situação.")

    _todo_historico = pd.DataFrame(_historico_de_entregas())
    if _todo_historico.empty:
        st.caption("Nenhum registro no histórico ainda. A primeira vez que "
                   "alguém registrar um ciclo aqui, a aba é criada sozinha.")
    else:
        # CINCO FILTROS NUMA LINHA SÓ (17/09/2026), pedido do auditor
        # comparando com os da Monitoramento: só os que fazem sentido no grão
        # desta tabela (uma linha por CICLO FECHADO, não por post). Tipo e
        # Marcação, que a Monitoramento tem, não existem nesse grão. "Quem
        # registrou" entrou e saiu no mesmo dia: o próprio "Procurar" já
        # busca "de quem registrou" (é o que o placeholder dele diz), então
        # um filtro exato ao lado virava a mesma pergunta duas vezes.
        hc1, hc2, hc3, hc4, hc5 = st.columns(5)
        opcoes_situacao_hist = ["Todas"] + sorted(
            v for v in _todo_historico["situacao"].unique() if v)
        filtro_situacao_hist = hc1.selectbox(
            "Situação", opcoes_situacao_hist, key="hist_filtro_situacao")
        opcoes_influ_hist = ["Todos"] + sorted(
            {fluxo.chave_de_pasta(v) for v in _todo_historico["influenciador"] if v})
        filtro_influ_hist = hc2.selectbox(
            "Influenciador", opcoes_influ_hist,
            format_func=lambda h: h if h == "Todos" else f"@{h}", key="hist_filtro_influ")
        opcoes_marca_hist = ["Todas"] + sorted(
            v for v in _todo_historico["marca"].unique() if v)
        filtro_marca_hist = hc3.selectbox(
            "Marca", opcoes_marca_hist, key="hist_filtro_marca")
        opcoes_ciclo_hist = ["Todos"] + sorted(
            (v for v in _todo_historico["ciclo"].unique() if v),
            key=lambda c: (len(c), c))
        filtro_ciclo_hist = hc4.selectbox(
            "Ciclo", opcoes_ciclo_hist, key="hist_filtro_ciclo")
        busca_hist = hc5.text_input(
            "Procurar", placeholder="parte do @, de quem registrou ou da observação",
            key="hist_busca")

        historico_filtrado = _todo_historico
        if filtro_situacao_hist != "Todas":
            historico_filtrado = historico_filtrado[
                historico_filtrado["situacao"] == filtro_situacao_hist]
        if filtro_influ_hist != "Todos":
            historico_filtrado = historico_filtrado[
                historico_filtrado["influenciador"].map(fluxo.chave_de_pasta) == filtro_influ_hist]
        if filtro_marca_hist != "Todas":
            historico_filtrado = historico_filtrado[
                historico_filtrado["marca"] == filtro_marca_hist]
        if filtro_ciclo_hist != "Todos":
            historico_filtrado = historico_filtrado[
                historico_filtrado["ciclo"] == filtro_ciclo_hist]
        if busca_hist.strip():
            termo_hist = busca_hist.strip().lower()
            casa_hist = pd.Series(False, index=historico_filtrado.index)
            for coluna_hist in ("influenciador", "quem", "nota"):
                casa_hist = casa_hist | historico_filtrado[coluna_hist].str.lower().str.contains(
                    termo_hist, na=False)
            historico_filtrado = historico_filtrado[casa_hist]

        st.caption(f"{len(historico_filtrado)} de {len(_todo_historico)} no histórico.")
        st.dataframe(historico_filtrado[list(CAMPOS_HISTORICO_ENTREGAS)],
                    width="stretch", hide_index=True)

st.divider()

# --- escolha do influenciador e do ciclo ---------------------------------
# SEM NINGUÉM PRÉ-SELECIONADO (17/09/2026), achado pelo auditor: sem a opção
# em branco, o selectbox sempre abre no primeiro @ da lista (ordem
# alfabética), e isso confundia, porque o filtro do histórico lá embaixo
# também parte desse mesmo @ (ver "JÁ VEM NO INFLUENCIADOR ESCOLHIDO", mais
# abaixo). Parecia que alguém tinha escolhido um influenciador, quando
# ninguém tinha.
handles = sorted({fluxo.chave_de_pasta(e["handle"]) for e in entregas if e["handle"]})
c1, c2 = st.columns([2, 1])
handle = c1.selectbox("Influenciador", [""] + handles,
                      format_func=lambda h: "escolher..." if not h else f"@{h}",
                      # ENCURTADO EM 17/09/2026.
                      help="Um combo é um post do dia, mesmo com várias telas.")
if not handle:
    st.info("Escolha um influenciador para começar.")
    st.stop()
ciclos = sorted({e["ciclo"].replace(".0", "") for e in entregas
                 if fluxo.chave_de_pasta(e["handle"]) == handle and e["ciclo"]},
                key=lambda c: (len(c), c))
if not ciclos:
    st.warning("Esse influenciador não tem ciclo preenchido nas entregas.")
    st.stop()
ciclo = c2.selectbox("Ciclo", ciclos)

dados_cadastro = escopos.get(handle, {})
texto_escopo = dados_cadastro.get("escopo", "")
lido = ee.ler_escopo(texto_escopo)
contagem = ee.contar_entregas(entregas, handle, ciclo)

# A DECLARAÇÃO DE QUEM CONFERE PASSA A CONTAR (16/09/2026), decisão do
# auditor: "pode ser um conforme com observação". O rádio "Conferi à mão e as
# entregas existem" existe na tela desde 03/09, mas a resposta dele era
# montada e descartada (só ia para o registro de fechamento, que está
# desligado): a pessoa respondia e nada acontecia.
#
# LIDO DO session_state, E NÃO DA VARIÁVEL DO WIDGET, porque o rádio é
# desenhado bem mais abaixo nesta mesma tela, e o fechamento precisa do valor
# aqui em cima. O Streamlit guarda o que foi escolhido na chave, e reexecuta
# a página inteira a cada escolha, então na próxima passada o número já chega
# certo. Chave sem nada escolhido ainda simplesmente não entra.
_DECLARACAO_EXISTE = "Conferi à mão e as entregas existem"
declaracoes = {}
for _tipo_nv, _quanto_nv in (lido.get("contratado_nao_validavel") or {}).items():
    if st.session_state.get(f"nao_validavel_{_tipo_nv}") == _DECLARACAO_EXISTE:
        declaracoes[_tipo_nv] = _quanto_nv

# ENTREGA FORA DA PLATAFORMA, MESMO PADRÃO (17/09/2026): lido do
# session_state pelo mesmo motivo do bloco acima, o campo é desenhado mais
# abaixo nesta mesma tela. Só entra quando tem quantidade em posts (ver
# ler_escopo); item sem número nunca aparece com campo nenhum.
#
# O NÚMERO DIGITADO VIAJA INTEIRO, e não só um sim/não (23/09/2026): quem
# decide se ele cabe no contratado ou sobra pra cobrir outro tipo é
# escopo_e_entrega.fechar_ciclo, não a tela.
declaracoes_nao_mensuravel = {}
for _qtd_nm, _texto_nm in (lido.get("nao_mensuraveis") or []):
    if _qtd_nm:
        _digitado = st.session_state.get(f"nm_qtd_{_texto_nm}") or 0
        if _digitado:
            declaracoes_nao_mensuravel[_texto_nm] = _digitado

fechamento = ee.fechar_ciclo(lido, contagem, declaracoes=declaracoes,
                             declaracoes_nao_mensuravel=declaracoes_nao_mensuravel)

# A JANELA REAL DO CICLO, e não a que se supõe. A própria auditoria registrou
# que um número de ciclo agrupou registros de 27/03 a 16/05, com 29 dias sem
# posts no meio. Mostrar as datas deixa isso à vista de quem fecha.
#
# E DATA SE ORDENA COMO DATA, NUNCA COMO TEXTO (07/09/2026). A planilha devolve
# DD/MM/AA, então ordenar como texto ordena pelo DIA. Medido nas 24.334 linhas
# reais da Monitoramento do Marketing: 822 dos 1.057 ciclos com mais de uma
# data saíam com o período errado, e vários terminavam antes de começar
# ("01/02/24 a 31/01/24"). Isso ia para o aviso do Financeiro. Mesmo defeito da
# contagem de POST, mesma correção: passa pelo leitor de data.
_datas = [(fluxo.data_de_celula(e["data_post"]), e["data_post"])
          for e in contagem["linhas"] if e["data_post"]]
_legiveis = sorted(d for d in _datas if d[0])
if _legiveis:
    _inicio, _fim = _legiveis[0][1], _legiveis[-1][1]
    periodo = _inicio if _inicio == _fim else f"{_inicio} a {_fim}"
    # A LIMITAÇÃO FICA NA PRÓPRIA LINHA, e não escondida: data ilegível não
    # entra no intervalo, e quem lê precisa saber que o período é parcial.
    _fora = len(_datas) - len(_legiveis)
    if _fora:
        periodo += f" ({_fora} entrega(s) com data ilegível, fora do intervalo)"
elif _datas:
    periodo = "datas não legíveis"
else:
    periodo = "sem data"
marcas = sorted({e["marca"] for e in contagem["linhas"] if e["marca"]})


# O CRONOGRAMA DO CICLO, LIDO DO CALENDÁRIO (11/09/2026).
#
# A Monitoramento só tem o que foi entregue. As datas em que o influenciador
# NÃO postou existem no Calendário de Divulgações, e são elas que fazem o texto
# do Financeiro ficar igual ao cronograma que o Marketing já manda no grupo.
#
# 120 SEGUNDOS DE CACHE, e não 60 como a leitura da Monitoramento: o Calendário
# muda menos e a leitura pode custar duas abas quando o ciclo atravessa o mês.
@st.cache_data(ttl=120, show_spinner="Lendo o Calendário de Divulgações...")
def carregar_cronograma(handle_alvo, ciclo_alvo):
    """(primeira, ultima, linhas, problemas, quando) do ciclo no Calendário.

    `quando` é o INSTANTE DA LEITURA, e não o do desenho da tela: a leitura
    fica em cache, então os dois podem ser bem diferentes. É esse instante que
    vai para a mensagem e para o registro do fechamento."""
    primeira, ultima = fluxo.janela_do_ciclo(handle_alvo, ciclo_alvo)
    agora = datetime.now()
    if not primeira or not ultima:
        return None, None, [], [], agora
    linhas_cal, problemas = calendario.linhas_do_influenciador(
        handle_alvo, primeira, ultima)
    return primeira, ultima, linhas_cal, problemas, agora


try:
    (_janela_ini, _janela_fim, _linhas_cal, _problemas_cal,
     _lido_em) = carregar_cronograma(handle, ciclo)
except Exception as e:
    # Falha aqui não pode derrubar o fechamento: o Calendário é conveniência
    # para o texto, e a evidência da auditoria já está na Monitoramento.
    _janela_ini, _janela_fim, _linhas_cal = None, None, []
    _problemas_cal, _lido_em = [str(e)[:200]], datetime.now()

cronograma = ee.montar_cronograma(contagem["posts"], _linhas_cal)
# A LISTA DE DIVERGÊNCIAS SAIU EM 23/09/2026, junto com o aviso que ela
# alimentava (ver mais abaixo, onde ficava). A nota de cada data continua
# existindo dentro do cronograma, e continua aparecendo na tabela e no
# registro do fechamento; o que saiu foi o aviso em destaque na tela.

# SÓ O QUE JÁ FOI RESOLVIDO VAI PARA A MENSAGEM (11/09/2026).
#
# O auditor levantou o problema de fundo: "essa parte da planilha deles é bem
# volátil, sempre pode mudar, o que está na planilha de calendário não
# necessariamente é o que será entregue".
#
# A coluna Status separa as duas coisas. `Publicada` e `Não Postada` foram
# escritos por uma PESSOA do Marketing: é registro, não plano. Célula vazia é
# plano puro, que pode ser remarcado, cancelado ou movido de data. Data que
# ninguém resolveu não entra em solicitação de pagamento, porque ali ela seria
# lida como falta, e falta é o que ela justamente não se sabe se é.
#
# NA TELA ELAS CONTINUAM APARECENDO, com a situação "Sem marcação". Ver o
# cronograma acontecendo é trabalho interno de quem fecha; o que não pode é ir
# para outra área como se fosse conclusão.
cronograma_resolvido = [i for i in cronograma if i["estado"] != ee.PENDENTE]


def linha_de_cronograma(item, para_mensagem=False):
    """Uma data do cronograma em texto. Serve a mensagem e o registro.

    `para_mensagem=True` DEIXA DE FORA A NOTA DE COMPARAÇÃO (16/09/2026),
    pedido do auditor: a mensagem que vai para o Marketing devia ficar "como
    está na planilha deles", sem a camada de comparação entre o Calendário e
    o que foi baixado aqui. A exceção é NOTA_SEM_LINHA: não é uma comparação,
    é avisar que não existe linha do Calendário com que comparar, e isso o
    Marketing não descobriria sozinho olhando a própria planilha.

    Sem `para_mensagem` (o padrão), a nota completa aparece: é o caso do
    registro do fechamento (cronograma_congelado) e da tela interna, que
    continuam precisando do detalhe para alguém conferir depois."""
    dia = f"{item['data']:%d/%m}"
    marca_do_dia = f" {item['marca']}" if item["marca"] else ""
    if para_mensagem:
        nota_texto = item["nota"] if item["nota"] == ee.NOTA_SEM_LINHA else ""
    else:
        nota_texto = item["nota"]
    nota = f" ({nota_texto})" if nota_texto else ""
    if item["estado"] == ee.ENTREGUE:
        return f"{item['numero']}º - {dia}{marca_do_dia} ✅{nota}"
    if item["estado"] == ee.NAO_POSTADA:
        return f"{dia} ❌"
    if item["estado"] == ee.DIVERGENCIA:
        return f"{dia} ⚠️{nota}"
    return dia


def cronograma_congelado():
    """O que o Calendário dizia neste instante, para o registro do fechamento.

    VAI PARA O REGISTRO SEMPRE, inclusive com a chave da mensagem desligada, e
    inclusive as datas ainda sem marcação. É evidência do que a auditoria viu,
    não texto de aviso: o Calendário é planilha viva de outra área, e sem isto
    uma edição posterior deles tornaria impossível reconstruir a conclusão."""
    if not cronograma:
        return ""
    lido = f"lido em {_lido_em:%d/%m/%Y %H:%M}"
    return lido + " | " + " | ".join(linha_de_cronograma(i) for i in cronograma)

st.divider()

# A SITUAÇÃO SAIU DO INDICADOR E VIROU FAIXA (03/09/2026), por defeito visto
# pelo auditor na tela: o indicador do Streamlit tem a largura da coluna, e
# nomes como "SEM BASE PARA COMPARAR" apareciam como "SEM BA...". A cor já diz
# se aquilo segue para o financeiro ou vira achado.
#
# A EXPLICAÇÃO SAIU DA FAIXA EM 09/09/2026, a pedido do auditor: "esse aviso
# não precisa ser grande, basta ficar em amarelo e constar Ciclo Incompleto ou
# algo do tipo". O nome curto já diz o essencial; a explicação inteira
# continua existindo em ee.apresentacao(situacao)["explicacao"], para quem
# lê o código ou os testes, só não vai mais para a tela.
_ap = ee.apresentacao(fechamento["situacao"])
_faixa = {"achado": st.error, "ok": st.success}.get(_ap["gravidade"], st.warning)
_faixa(f"**{_ap['icone']} {_ap['curto']}**")

# SÓ OS NÚMEROS QUE CARREGAM INFORMAÇÃO (04/09/2026).
#
# O auditor apontou que a tela fica poluída quando falta entrega: "tem muito
# campo em destaque". Indicadores do mesmo tamanho, quase sempre zero, gastam
# ênfase sem dizer nada, e o que importa deixa de saltar.
#
# QUALQUER VEREDITO CONTA COMO ENTREGA (16/09/2026, revisão da decisão de
# 31/08/2026): peça reprovada na régua da portaria deixou de travar o
# fechamento, então não faz mais sentido um indicador separado de "cota"
# contra "total" — os dois são o mesmo número agora. O que sobra de
# informativo é QUANTAS peças vieram reprovadas, pra quem fecha saber que
# precisa revisar, sem que isso impeça de fechar. Igual para "Orgânicos", que
# só aparece se o contrato pede orgânico ou se algum chegou.
_total = sum(contagem["entregue"].values())
_reprovadas = len(contagem["reprovadas"])
_organico = sum(contagem["entregue_organico"].values())

_indicadores = [
    ("Entregas no ciclo", _total,
     "Todo post entregue neste ciclo, de qualquer tipo."),
]
if _reprovadas:
    _indicadores.append((
        "Peças reprovadas", _reprovadas,
        "Não passaram na régua da portaria, mas contam como entrega mesmo "
        "assim. Revisar para não se repetir; os motivos estão logo abaixo."))
if _organico or lido.get("contratado_organico"):
    _indicadores.append((
        "Orgânicos", _organico,
        "Contados à parte: peça orgânica não passa pela régua da portaria, "
        "então não tem veredito para exibir."))
# "TELAS NA PLANILHA" SAIU EM 16/09/2026, junto com a tabela tela a tela que
# ela resumia: o número apontava para uma tabela que não existe mais aqui, e
# a contagem de linhas por ciclo está na Monitoramento, que é a tela dela.

for _coluna, (_titulo, _valor, _ajuda) in zip(
        st.columns(len(_indicadores)), _indicadores):
    _coluna.metric(_titulo, _valor, help=_ajuda)

# AS TRÊS RAZÕES DE UMA PEÇA NÃO CONTAR, e elas pedem AÇÕES DIFERENTES de
# pessoas diferentes (03/09/2026, do cruzamento com a aba Achado03 do papel de
# trabalho). Ver categoria_do_gap em escopo_e_entrega.py.
#
# PEÇA REPROVADA SAIU DAQUI EM 16/09/2026: ela passou a contar como entrega
# (ver o indicador "Peças reprovadas" acima e o motivo em fechamento pelos
# "motivos"), então "não conta para a cota" não é mais verdade pra ela.
_razoes = [
    (contagem["sem_evidencia"], "a análise não conseguiu abrir",
     "pasta vazia, sem acesso, ou link da rede social em vez do arquivo; "
     "resolve-se conseguindo o arquivo"),
    (contagem["limite_da_automacao"], "a automação não conseguiu decidir",
     "normalmente aviso pequeno ou de baixo contraste; precisa de alguém "
     "olhando a peça"),
    (contagem["sem_veredito"], "ainda não foram analisadas",
     "a análise não rodou nessas linhas"),
]
_com_peca = [(linhas_r, o_que, porque) for linhas_r, o_que, porque in _razoes
             if linhas_r]
if _com_peca:
    # VIROU LINHA DE TEXTO, E NÃO CAIXA DESTACADA (04/09/2026). O auditor, sobre
    # esta caixa: "acho que isso aqui não precisa botar". A informação não foi
    # apagada, porque ela diz quantas peças esperam alguém olhando, e isso é
    # ação de alguém. O que ela perdeu foi o destaque, que competia com a
    # situação do ciclo logo acima sem ser mais importante que ela.
    #
    # E O TEXTO ANTIGO PROMETIA "por mais de um motivo" MESMO QUANDO HAVIA SÓ
    # UM, o que fazia a frase parecer defeito de tela: o cabeçalho anunciava
    # vários e vinha um item só na lista.
    _partes = [f"{len(linhas_r)} que {o_que} ({porque})"
               for linhas_r, o_que, porque in _com_peca]
    st.caption("**Não contam para a cota:** " + "; ".join(_partes) + ".")

st.caption(f"**Período real das entregas deste ciclo:** {periodo}"
           + (f"  ·  **Marca:** {', '.join(marcas)}" if marcas else "")
           + (f"  ·  **Contrato:** {dados_cadastro.get('inicio', '?')} a "
              f"{dados_cadastro.get('fim', '?')}" if dados_cadastro else ""))

# --- escopo x entrega -----------------------------------------------------
#
# TEXTO ENXUGADO EM 16/09/2026, pedido do auditor de deixar a tela mais
# enxuta: a explicação completa (esta zona confere o CONTRATO inteiro do
# ciclo; a zona de baixo confere DATA por data contra o Calendário) virou
# help do subheader, em vez de parágrafo sempre visível.
with st.container(key="fin_zona_escopo"):
    # ENCURTADO EM 17/09/2026.
    st.subheader("Escopo contratado x entrega",
                 help="O que foi combinado contra o que foi entregue neste "
                      "ciclo.")
    st.caption(f"Escopo no cadastro: {texto_escopo or '(não preenchido)'}")
    
    # ENTREGA FORA DA PLATAFORMA ENTRA NA MESMA TABELA (17/09/2026, pedido do
    # auditor depois de testar ao vivo): antes ela só aparecia lá embaixo, no
    # checkbox, e a tabela de cima parecia 100% fechada mesmo faltando
    # confirmar a diária, escondendo o motivo de a Observação virar
    # obrigatória. Linha própria aqui, com o mesmo Contratado/Entregue/Falta,
    # e ⏳ (em vez de 🚫) para "ainda não confirmado", porque a peça pode
    # muito bem já ter acontecido, só falta alguém confirmar, não é o mesmo
    # "faltou de verdade" da 🚫.
    _linhas_nm = [
        {"Tipo": texto + " (fora da plataforma)",
         "Contratado": quantidade,
         "Entregue": declaracoes_nao_mensuravel.get(texto, 0),
         "Falta": "—" if texto in declaracoes_nao_mensuravel else quantidade,
         "Status": "✅" if texto in declaracoes_nao_mensuravel else "⏳"}
        for quantidade, texto in (lido.get("nao_mensuraveis") or [])
        if quantidade]
    if fechamento["por_tipo"] or _linhas_nm:
        tabela = pd.DataFrame([
            {"Tipo": p["tipo"] + (" (alternativa)" if p["alternativa"] else ""),
             "Contratado": p["contratado"],
             "Entregue": p["entregue"],
             "Falta": p["falta"] or "—",
             "Status": "✅" if not p["falta"] else "🚫"}
            for p in fechamento["por_tipo"]] + _linhas_nm)
        st.dataframe(tabela, use_container_width=True, hide_index=True)
    else:
        st.warning("Não há quantidade contratada legível para comparar.")
    
    # O MOTIVO SÓ APARECE QUANDO É ACHADO (04/09/2026).
    #
    # A FALTA DE ENTREGA NÃO É MAIS ESCRITA AQUI. Ela era dita três vezes na mesma
    # tela: a tabela logo acima já mostra "Contratado 16, Entregue 2, Falta 14, 🚫";
    # o motivo repetia em texto ("Falta quantidade: STORIES, 14 a entregar"); e o
    # fechamento ainda exige justificativa escrita se alguém pagar sem a entrega
    # ter fechado. O auditor cortou a repetição do meio: "não precisa fazer
    # referência as NÃO entregas, pq a pessoa já vai justificar quando for pagar e
    # não existir a entrega combinada do escopo". A informação continua na tabela,
    # que é onde ela é mais precisa (por tipo, com a quantidade), e a consequência
    # continua no pagamento, que é onde ela obriga alguém a escrever o porquê.
    #
    # A MUDANÇA DE COMPOSIÇÃO CONTINUA EM CAIXA VERMELHA, e a diferença não é
    # estética: ali o motivo diz o que a tabela NÃO diz, que é qual tipo veio FORA
    # do escopo contratado. Isso não é falta de entrega, é entrega trocada.
    #
    # A CONDIÇÃO MUDOU EM 09/09/2026, de "situação == NÃO CONFORME" (estado que
    # saiu do motor) para "exige_justificativa" direto. A diferença importa: hoje
    # um ciclo pode fechar CONFORME (cota cumprida) e ainda assim ter composição
    # trocada para explicar, então esta caixa não pode mais depender da situação.
    # A CAIXA DE MOTIVOS SAIU DE DENTRO DO `if exige_justificativa` EM
    # 23/09/2026, e isso foi um defeito que durou algumas horas: quando a
    # justificativa deixou de ser exigida em ciclo compensado, a explicação
    # de QUEM COBRIU QUEM passou a ser calculada e nunca desenhada. O auditor
    # viu na tela e perguntou se a compensação ainda estava sendo
    # implementada. Estava pronta; era a caixa que não aparecia.
    #
    # A COR SEPARA AS DUAS SITUAÇÕES, que é o que o `if` fazia por acidente:
    # ciclo que não fechou continua em vermelho, porque ali há o que resolver;
    # ciclo que fechou por compensação sai em azul, porque é explicação e não
    # problema. Pintar de vermelho um ciclo apto a pagamento diria o contrário
    # do que o fechamento concluiu.
    #
    # UMA CAIXA SÓ, COM OS MOTIVOS EM LISTA (05/09/2026). Eram três `st.error`
    # empilhados, um por motivo, e o auditor perguntou: "não dá pra colocar
    # tudo em uma faixa única não?". Dá, e é melhor: são razões do MESMO
    # veredito, não problemas separados.
    #
    # E O MOTIVO DE FALTA DE QUANTIDADE SAI DA LISTA, porque a tabela logo
    # acima já mostra Contratado, Entregue, Falta e 🚫 por tipo, com mais
    # precisão. É a mesma decisão que ele já tinha pedido: "não precisa fazer
    # referência as NÃO entregas, pq a pessoa já vai justificar quando for
    # pagar".
    _motivos = [m for m in fechamento["motivos"]
                if not str(m).lower().startswith("falta quantidade")]
    if _motivos:
        _texto_motivos = "  \n".join(f"- {m}" for m in _motivos)
        if fechamento["exige_justificativa"]:
            st.error(_texto_motivos)
        else:
            st.info(_texto_motivos)
    
    # --- histórico de entregas deste escopo, sempre visível ---------------------
    #
    # FORA de FECHAMENTO_DE_CICLO_ATIVO de propósito: registrar aqui não é
    # fechar nada, é consulta e registro simples, para quem tem acesso à
    # ferramenta (o Financeiro vai ganhar acesso) ver depois o que já foi
    # observado sobre este escopo. Não gera texto de WhatsApp nenhum; isso
    # continua só na seção do Calendário, mais abaixo.
    st.divider()
    # A AÇÃO FICA AQUI, A PLANILHA FICA NO FIM DA TELA (16/09/2026): registrar
    # é a consequência do que a tabela de escopo acabou de mostrar, então o
    # botão mora junto dela; consultar o histórico inteiro é outra coisa, e
    # virou seção própria no fim, como a planilha desta tela (o mesmo papel
    # que a Monitoramento tem na tela de Monitoramento).
    # ENCURTADO EM 17/09/2026.
    st.subheader(
        "Registrar este ciclo no histórico",
        help="Registro simples, sem gerar mensagem nem solicitar pagamento.")
    # OBRIGATÓRIA QUANDO O CICLO PEDE JUSTIFICATIVA (15/09/2026, ampliado
    # 16/09/2026 com a queda de Stories): se falta quantidade no total, veio
    # composição fora do escopo, OU Stories caiu mesmo com o total fechando,
    # a pessoa precisa registrar o porquê, não só ter a opção.
    _nota_obrigatoria = bool(fechamento["exige_justificativa"])
    # CICLO QUE FECHOU NÃO TEM CAMPO DE TEXTO NENHUM (23/09/2026, pedido do
    # auditor, em duas etapas no mesmo dia).
    #
    # Primeiro ele pediu que a Observação não aparecesse em ciclo compensado
    # ou batendo exato. Eu tirei só a obrigatoriedade, e a caixa continuou
    # lá escrito "(opcional)"; ele apontou de novo. Então escondi atrás de um
    # expansor, e ele apontou uma terceira vez: "deveria não existir, e sim
    # uma frase automática dizendo Ciclo completo, ou no caso da entrega
    # compensada, Ciclo completo (entrega compensada)".
    #
    # ESTÁ CERTO, E O MOTIVO É DE AUDITORIA, não de tela: um campo de texto
    # convida a escrever, e o que a pessoa escreveria ali é justamente o que
    # o programa acabou de calcular sozinho, com mais precisão. Melhor MOSTRAR
    # o que vai ser registrado do que pedir que alguém redija de novo.
    #
    # O QUE APARECE É EXATAMENTE O QUE VAI SER GRAVADO, e é por isso que o
    # texto vem do motor (escopo_e_entrega._nota_automatica) em vez de ser
    # remontado aqui: tela e registro que dizem coisas diferentes é o começo
    # de um histórico em que não se pode confiar.
    if _nota_obrigatoria:
        # ENCURTADO EM 17/09/2026, pedido do auditor. Os motivos detalhados
        # (falta no total, composição fora do escopo) já aparecem na caixa de
        # motivos logo acima, não precisam repetir aqui.
        st.warning("Este ciclo pede justificativa, escreva o motivo antes de "
                   "registrar.")
        nota_escopo = st.text_area(
            "Observação *", key="nota_escopo_financeiro",
            # ALTURA MÍNIMA (16/09/2026, pedido do auditor): a caixa grande de
            # antes parecia exigir um texto longo pra poder registrar. Ela
            # ainda cresce sozinha se a pessoa escrever mais.
            height=68,
            # O EXEMPLO É DE SUBSTITUIÇÃO, NÃO DE AUTORIZAÇÃO (16/09/2026): o
            # texto anterior sugeria que toda troca passa por aval do
            # Marketing, e não é assim que eles trabalham. A troca acontece
            # pela repercussão da entrega, e o que o histórico quer saber é o
            # que entrou no lugar.
            placeholder="ex: faltou 1 story, mas entregamos 1 reels a mais")
    else:
        nota_escopo = ""
        _nota_do_programa = fechamento.get("nota_automatica") or "Ciclo completo."
        st.caption(f"Vai ser registrado assim: **{_nota_do_programa}**")
    if st.button("Registrar no histórico",
                 disabled=_nota_obrigatoria and not nota_escopo.strip()):
        # CONFERE SE GRAVOU MESMO (16/09/2026). Antes esta linha dizia
        # "Registrado no histórico." sem olhar o retorno, e no primeiro teste
        # de verdade isso teria mentido: a aba ainda não existia, o Google
        # recusou a leitura, `gravar` devolveu False e a tela comemorou. O
        # CSV local continua sendo a rede de segurança, e agora a tela diz
        # qual dos dois caminhos funcionou.
        # NOTA AUTOMÁTICA QUANDO NINGUÉM ESCREVEU (23/09/2026, pedido do
        # auditor): ciclo completo ou compensado não exige mais Observação à
        # mão, e sem isto ele entraria no histórico com a coluna NOTA vazia.
        # O texto vem do motor (ver escopo_e_entrega._nota_automatica), que é
        # quem sabe o que cobriu o quê. O que a pessoa escreve SEMPRE ganha:
        # ele diz por que aconteceu, este só diz o que aconteceu.
        _nota_para_gravar = (nota_escopo.strip()
                             or fechamento.get("nota_automatica") or "")
        _gravou, _motivo_registro = registrar_no_historico_de_entregas(
            handle, ciclo, ", ".join(marcas), fechamento, _nota_para_gravar,
            identidade.quem_sou_eu(), periodo_do_registro=periodo,
            escopo_do_registro=texto_escopo,
            # AS DUAS DECLARAÇÕES JUNTAS (17/09/2026): a de tipo (YouTube,
            # Twitter) e a de fora da plataforma (diária, evento), separadas
            # por "; " porque a segunda já usa vírgula dentro do próprio
            # texto do item.
            conferido_a_mao="; ".join(
                [f"{t} ({n})" for t, n in sorted(declaracoes.items())]
                + [f"\"{t}\" ({n})" for t, n in sorted(declaracoes_nao_mensuravel.items())]))
        _historico_de_entregas.clear()
        if _gravou:
            st.success("Registrado no histórico.")
        else:
            st.warning(
                f"Gravei no arquivo local, mas **não** na planilha: "
                f"{_motivo_registro}. O registro não se perdeu, e quem abrir "
                f"a planilha agora não vai ver esta linha.")

    # --- as opções que o programa NÃO decide sozinho ---
    #
    # Pedido do auditor em 03/09/2026: "considere as exceções para que a gente
    # consiga ter as opções necessárias para não inferir nada". Cada bloco abaixo
    # existe porque o dado real tem um caso que nenhum programa resolve sem alguém
    # que leia o contrato. A escolha fica registrada no fechamento.
    decisoes = {}
    
    if lido.get("contratado_nao_validavel"):
        st.subheader("Tipos que a régua da portaria não alcança")
        st.caption(
            "O programa baixa e analisa peça do Instagram. Post do X, vídeo do "
            "YouTube, TikTok e Facebook são entregas de verdade, registradas na "
            "Monitoramento, mas nenhuma delas recebe veredito CONFORME, porque a "
            "análise não roda nesses tipos. Como só peça CONFORME conta para a cota, "
            "sem esta escolha o ciclo nunca fecharia."
        )
        for tipo, quantidade in sorted(lido["contratado_nao_validavel"].items()):
            entregue_do_tipo = contagem["entregue"].get(tipo, 0)
            escolha = st.radio(
                f"{tipo}: contratado {quantidade}, entregue {entregue_do_tipo}",
                ("Ainda não conferi",
                 "Conferi à mão e as entregas existem",
                 "Conferi à mão e as entregas NÃO existem"),
                key=f"nao_validavel_{tipo}", horizontal=True)
            decisoes[f"{tipo}"] = escolha
    
    # ENTREGA FORA DA PLATAFORMA (17/09/2026), pedido do auditor: "diária de
    # divulgação... precisa ter um campo para conferir manualmente e lá a
    # pessoa vai poder marcar um CHECK de que essas mídias foram entregues e
    # com justificativa obrigatória". Só aparece pra item que TEM quantidade
    # em posts; live em horas e detalhe entre parênteses ficam de fora daqui
    # (aparecem só em "Conferir à mão", lá embaixo, sem checkbox).
    #
    # VIROU CAMPO DE QUANTIDADE EM 23/09/2026, no lugar do check. O auditor
    # perguntou: "se a compensação for de alguma entrega externa, estamos
    # preparados para isso?", e a resposta era não: o check só confirmava a
    # própria linha do contrato, nunca sobrava pra cobrir outro tipo (um
    # story faltando, por exemplo), porque o teto travava exatamente nisso.
    # Agora dá para digitar MAIS do que o contratado, e o excedente vira
    # sobra disputável por qualquer falta, igual sobra medida (ver
    # escopo_e_entrega.fechar_ciclo, onde o teto caiu só pra este lado).
    _nm_contavel = [(qtd, texto) for qtd, texto in (lido.get("nao_mensuraveis") or []) if qtd]
    if _nm_contavel:
        st.subheader("Entregas fora da plataforma")
        # A OBSERVAÇÃO SÓ FICA OBRIGATÓRIA SE SOBRAR ALGO A EXPLICAR (revisto
        # 17/09/2026, no mesmo dia, depois de testar ao vivo): marcar o check
        # não força mais a Observação sozinho. Se confirmar aqui é só o que
        # faltava para o ciclo fechar por inteiro, a tabela acima já mostra
        # tudo certo e o motivo automático já registra a confirmação, sem
        # texto nenhum. Só volta a pedir Observação se, mesmo confirmando,
        # ainda faltar entrega de verdade, OU se o que exceder o contratado
        # for o que fechou o ciclo (ver escopo_e_entrega.fechar_ciclo): ali o
        # programa não tem como conferir nada sozinho, então quem decide
        # precisa poder responder por isso.
        st.caption(
            "O download não enxerga essas peças. Confirme quantas já "
            "aconteceram de verdade; aparece na tabela acima. Digitar mais "
            "do que o contratado é possível, e o excedente pode cobrir a "
            "falta de outro tipo, mas se for isso que fechar o ciclo, pede "
            "justificativa."
        )
        for quantidade, texto in _nm_contavel:
            digitado = st.number_input(
                f"{texto} (contratado {quantidade})", min_value=0,
                # O PADRÃO É ZERO, e não o contratado: um número pré-marcado
                # confirmaria a entrega sem ninguém decidir isso, e a decisão
                # de que aconteceu tem que partir de quem está fechando.
                value=0, step=1, key=f"nm_qtd_{texto}")
            decisoes[f"nm_{texto}"] = "confirmado" if digitado else ""

    if lido.get("ambiguos") or lido.get("condicionais"):
        st.subheader("Itens do escopo que dependem de leitura do contrato")
        for quantidade, trecho in lido.get("ambiguos") or []:
            st.caption(f"**\"{trecho}\"**: o contrato pede {quantidade}, sem dizer o "
                       f"formato da peça.")
            decisoes[trecho] = st.text_input(
                f"Como contar \"{trecho}\"?", key=f"ambiguo_{trecho}",
                placeholder="ex: 20 reels, conforme e-mail de [nome] em [data]")
        for trecho in lido.get("condicionais") or []:
            st.caption(f"**\"{trecho}\"**: a quantidade depende de condição no "
                       f"contrato, e o programa não sabe qual mês do contrato é "
                       f"este ciclo.")
            decisoes[trecho] = st.text_input(
                f"Esta condição vale neste ciclo?", key=f"condicional_{trecho}",
                placeholder="ex: sim, este é o 3º mês do contrato")
    
    if fechamento["conferir_a_mao"]:
        # TÍTULO CORRIGIDO EM 17/09/2026: "que o programa NÃO mediu" é falso
        # pro caso do orgânico, que É contado no total (pergunta do auditor:
        # "eles continuam contando para a entrega né?" — continuam). O que é
        # comum aos itens da lista é não ter conformidade afirmada, não
        # ausência de medição; o motivo exato de cada um já está na linha.
        with st.expander(f"Conferir à mão: {len(fechamento['conferir_a_mao'])} item(ns)"):
            st.caption("O fechamento não afirma conformidade sobre estes "
                       "itens; o motivo de cada um está abaixo.")
            for item in fechamento["conferir_a_mao"]:
                st.markdown(f"- {item}")

# --- o cronograma do ciclo -------------------------------------------------
#
# "OS POSTS DESTE CICLO" (a tabela tela a tela: Linha/Tipo/Marcação/Arquivo,
# com CRONOGRAMA e PAGAMENTO só para conferência, nunca escritos por aqui)
# SAIU DAQUI EM 16/09/2026, pedido do auditor: "já tem na Monitoramento", e
# tem mesmo, é a mesma informação sem corte nenhum. Fica só a visão por
# DATA, que é exclusiva desta tela porque cruza com o Calendário, e é ela
# que vai para o texto do WhatsApp mais abaixo.
st.divider()
with st.container(key="fin_zona_cronograma"):
    # TEXTO ENXUGADO EM 16/09/2026: a explicação (esta zona confere DATA por
    # data contra o Calendário do Marketing, sem relação com o contrato)
    # virou help do subheader.
    # ENCURTADO EM 17/09/2026.
    st.subheader("Cronograma do ciclo",
                 help="Data por data contra o Calendário do Marketing, com o "
                      "texto pronto pro WhatsApp.")

    _ICONE_ESTADO = {ee.ENTREGUE: "✅", ee.NAO_POSTADA: "❌",
                     ee.DIVERGENCIA: "⚠️", ee.PENDENTE: ""}
    _NOME_ESTADO = {ee.ENTREGUE: "Entregue", ee.NAO_POSTADA: "Não postada",
                    ee.DIVERGENCIA: "Divergência", ee.PENDENTE: "Sem marcação"}
    
    if _problemas_cal:
        st.warning(
            "Não consegui ler o Calendário inteiro, então este cronograma pode "
            "estar incompleto: " + "; ".join(_problemas_cal))
    if not _janela_ini:
        # A MESMA MENSAGEM COBRE DOIS MOTIVOS (11/09/2026): falta ciclo na cópia da
        # Monitoramento, OU o número do ciclo se repete em períodos tão separados
        # que fluxo.janela_do_ciclo não confia nele (ver o docstring de lá). Os dois
        # dão no mesmo resultado prático: sem janela segura, sem cronograma.
        st.caption(
            "Sem o cronograma: não dá para determinar com segurança as datas "
            "deste ciclo (falta a data na cópia da Monitoramento, ou o número do "
            "ciclo se repete em períodos muito separados). O texto do Financeiro "
            "sai só com as entregas."
        )
    elif not cronograma:
        st.caption(
            f"O Calendário não tem nenhuma linha de @{handle} entre "
            f"{_janela_ini:%d/%m/%Y} e {_janela_fim:%d/%m/%Y}."
        )
    else:
        # DUAS FRASES SAÍRAM DAQUI EM 16/09/2026, as duas por terem ficado
        # FALSAS, não por enxugamento:
        #   1. "a marcação ✅ é do que foi baixado e validado por aqui, não do
        #      que está escrito na planilha deles" deixou de valer quando o
        #      auditor mandou confiar na marcação deles ("se eles marcaram,
        #      pode colocar verde como entregue mesmo"). Hoje o ✅ é das duas
        #      coisas. Ver montar_cronograma em escopo_e_entrega.py.
        #   2. "só vai para a mensagem se você ligar a chave lá embaixo" era
        #      da época em que o cronograma dependia do bloco de fechamento;
        #      desde 11/09/2026 o texto do WhatsApp roda sempre, logo abaixo.
        st.caption(
            f"Datas de {_janela_ini:%d/%m/%Y} a {_janela_fim:%d/%m/%Y}, lidas do "
            f"Calendário de Divulgações em {_lido_em:%d/%m/%Y, %Hh%M}."
        )
        # A TABELA VIROU EXPANDER (16/09/2026, enxugamento): ela é a mesma
        # lista que o texto do WhatsApp logo abaixo já mostra pronta, em
        # outro formato. Fica à mão para quem quiser conferir data a data
        # antes de mandar, sem competir com o texto, que é o que a pessoa
        # veio buscar.
        with st.expander(f"Ver as {len(cronograma)} data(s) em tabela"):
            st.dataframe(
                pd.DataFrame([
                    {"Nº": i["numero"] or "",
                     "Data": f"{i['data']:%d/%m/%Y}",
                     "Marca": i["marca"],
                     "": _ICONE_ESTADO[i["estado"]],
                     "Situação": _NOME_ESTADO[i["estado"]],
                     "Observação": i["nota"]}
                    for i in cronograma]),
                # width="stretch" E NÃO a forma antiga de ocupar a largura toda
                # (11/09/2026): a antiga está marcada para remoção pelo Streamlit,
                # e este repositório tem teste que CONTA os usos dela para a
                # dívida não crescer. Tabela nova já nasce na forma nova. O teste
                # conta a palavra no texto do arquivo, então nem em comentário ela
                # pode aparecer. Ver teste_as_telas_abrem.py, seção 4.
                width="stretch", hide_index=True)
    
    # O AVISO DE DIVERGÊNCIA COM O CALENDÁRIO SAIU EM 23/09/2026, pedido do
    # auditor: "as datas que divergem no calendário não têm problema, não
    # precisa ter esse aviso porque o Calendário é algo organizacional apenas
    # para as analistas". Ele existiu de 15/09 a 23/09 e chegava a listar seis
    # datas seguidas de "sem linha no Calendário" num ciclo inteiro normal,
    # que é ruído, não achado: nada ali é evidência de auditoria, porque a
    # evidência mora na Monitoramento.
    #
    # O CRONOGRAMA PARA O WHATSAPP, LOGO ABAIXO, FICA. Foi dito no mesmo
    # pedido, e é outra coisa: aquilo é o relatório que o Marketing já manda.

    # --- o texto do cronograma para o WhatsApp do Marketing --------------------
    #
    # ESTE BLOCO NÃO TEM NADA A VER COM "FECHAR O CICLO" (11/09/2026). O auditor
    # corrigiu o entendimento: "fechar ciclo é uma coisa, essa mensagem não
    # existe, a de fechamento de ciclo não existe, o Financeiro olha a própria
    # planilha de monitoramento para efetuar o pagamento... o que eu quero é que
    # vc gere, cada post confirmado na planilha de calendário, aquele texto que dá
    # o check nas datas, que vai gerar o texto que vai pro whatsapp do próprio
    # marketing".
    #
    # O FORMATO É O DA MENSAGEM REAL que o auditor mostrou no início deste
    # trabalho (print de "Júnior EDS" no grupo do Marketing): um cabeçalho com
    # influenciador e ciclo, os dois horários combinados, e um checklist por data.
    # NADA de escopo contratado, situação do ciclo ou justificativa: aquilo é
    # conferência de auditoria, isto é o relatório que o Marketing já manda para
    # quem acompanha o cronograma.
    #
    # POR ISSO ESTE BLOCO NÃO ESTÁ ATRÁS DE FECHAMENTO_DE_CICLO_ATIVO, e continua
    # de pé com aquela chave desligada: as duas coisas não têm relação.
    #
    # O TEXTO TRAZ A JANELA INTEIRA, NÃO SÓ AS DATAS JÁ CONFIRMADAS (11/09/2026).
    # Primeira versão usava `cronograma_resolvido`, e o auditor corrigiu: "seria
    # possivel colocar todas as datas pra pessoa ir preenchendo a medida que forem
    # postando? pq assim que eles fazem". É o próprio formato do cronograma:
    # a lista sai pronta desde o início do ciclo, com data sem marca virando ✅ ou
    # ❌ conforme o Calendário é atualizado. Data PENDENTE (sem Status ainda)
    # aparece sem marca nenhuma, exatamente como as datas futuras do exemplo real.
    #
    # E COMO O TEXTO É GERADO NA HORA A PARTIR DO CALENDÁRIO, uma mudança lá
    # (Marketing marcando Publicada, ou remarcando uma data) aparece aqui na
    # próxima leitura, sem precisar de nada além de abrir a tela de novo. O cache
    # de `carregar_cronograma` é de 120 segundos (ver ali), então a defasagem
    # máxima é essa.
    st.divider()
    st.subheader("Cronograma pro WhatsApp do Marketing")
    
    if not cronograma:
        st.caption(
            "Sem cronograma para gerar o texto: ver o aviso na seção "
            "\"Cronograma do ciclo\" acima."
        )
    else:
        # OS DOIS CAMPOS DE HORÁRIO SAÍRAM EM 16/09/2026, e o argumento é de
        # economia de trabalho, não de estética. Eles nasceram em 11/09 porque
        # a mensagem real do Marketing abre com "Horário de postagem: entre 9h
        # e 20h" e "Horário limite para aprovação dos vídeos: 16h", que são
        # termo de contrato e não estão em planilha nenhuma que o programa
        # leia. Só que nada guardava o que era digitado: a pessoa teria que
        # redigitar a cada ciclo, e ela já vai colar o texto no WhatsApp, onde
        # digitar a mesma linha custa o mesmo. Campo que não poupa digitação
        # nenhuma não paga o espaço que ocupa.
        #
        # SE UM DIA VOLTAR, que volte guardando por influenciador (é o que
        # faria valer a pena), e não como campo em branco a cada visita.

        # A MARCA DO CABEÇALHO VEM DE TODAS AS QUE APARECEM NO CRONOGRAMA, e não de
        # uma escolhida. No dado real o mesmo ciclo mistura marcas (ver o
        # DESENHO_CALENDARIO.md, medido em @lucasguimaraes): inventar uma só
        # seria decidir por quem lê. Cada linha do checklist já mostra a marca
        # daquele post específico. Usa o cronograma INTEIRO, e não só o resolvido,
        # porque uma data ainda pendente também pode já ter marca no Calendário.
        _marcas_do_cronograma = sorted({i["marca"] for i in cronograma
                                        if i["marca"]}) or marcas
    
        def _texto_cronograma_whatsapp():
            """O checklist por data, no formato que o Marketing já usa.
    
            A JANELA INTEIRA ENTRA, PUBLICADA, NÃO POSTADA OU AINDA SEM MARCA
            (11/09/2026). Data pendente sai sem ✅ nem ❌, pronta para a pessoa
            preencher à medida que for postando, que é como o Marketing já usa
            esse texto: a lista existe desde o início do ciclo, o check chega
            depois. `linha_de_cronograma` já devolve só a data pelada nesse caso.
    
            SEM O TOTAL DE CICLOS DO CONTRATO ("CICLO 6/12" na mensagem real): essa
            contagem não existe em nenhuma fonte que o programa lê, e escrever um
            número que não foi medido é o que a auditoria nunca faz. Só o número
            do ciclo desta tela."""
            partes = [
                f"CRONOGRAMA DE POSTAGENS | "
                f"{', '.join(_marcas_do_cronograma).upper() or 'MARCA NÃO INFORMADA'} "
                f"| {handle.upper()} | CICLO {ciclo}",
            ]
            partes.append("")
            for item in cronograma:
                partes.append(linha_de_cronograma(item, para_mensagem=True))
            return "\n".join(partes)
    
        st.code(_texto_cronograma_whatsapp(), language=None)
        st.caption(
            f"Cronograma lido do Calendário em {_lido_em:%d/%m/%Y, %Hh%M}. Data "
            f"ainda sem marca aparece sem ✅ nem ❌; uma mudança no Calendário "
            f"aparece aqui na próxima leitura."
        )

# --- fechamento -----------------------------------------------------------
st.divider()

if not FECHAMENTO_DE_CICLO_ATIVO:
    # SÓ ESTA MENSAGEM APARECE COM A CHAVE DESLIGADA (11/09/2026). O resto da
    # seção continua logo abaixo, inteiro, dentro do `if` que segue.
    #
    # TEXTO CORRIGIDO EM 15/09/2026: dizia que o texto do WhatsApp também
    # estava fora do ar, o que ficou errado desde 11/09, quando aquele bloco
    # saiu de dentro de FECHAMENTO_DE_CICLO_ATIVO e passou a rodar sempre.
    st.caption(
        "**Fechar o ciclo está desligado por enquanto.** A tela segue "
        "conferindo escopo, entrega e cronograma acima; só a solicitação de "
        "pagamento está fora do ar. O texto para o WhatsApp, mais acima, "
        "continua funcionando normalmente."
    )

if FECHAMENTO_DE_CICLO_ATIVO:
    st.subheader("Fechar o ciclo")

    justificativa = ""
    # O FIM DA TELA VIROU UMA PERGUNTA SÓ, "SOLICITAR PAGAMENTO?" (09/09/2026).
    #
    # Antes existiam duas perguntas separadas, uma sobre a entrega e outra sobre
    # um rádio "Este ciclo já foi pago?". O auditor apontou o problema de fundo:
    # "o pagamento vem depois do ciclo fechado... essa mensagem é para pagamento
    # do ciclo, e não do escopo". Perguntar se já tinha sido pago pressupõe que
    # pagamento pode acontecer ANTES desta tela confirmar a entrega, que é
    # exatamente o que o fluxo correto evita (ESCOPO → ciclo entregue → SOLICITA
    # o pagamento → ciclo seguinte).
    #
    # A JUSTIFICATIVA VIROU UMA CONDIÇÃO SÓ EM 23/09/2026: o ciclo NÃO FECHOU.
    # Ela cobria também a composição fora do escopo, e o auditor mandou tirar
    # essa parte no mesmo dia, depois de eu levantar a ressalva. Composição
    # trocada e tipo abaixo do combinado passaram a ser registrados sozinhos
    # (ver escopo_e_entrega._nota_automatica), em vez de exigirem texto.
    if fechamento["exige_justificativa"]:
        st.error(
            "Este ciclo não fechou a cota contratada. Escreva o porquê antes "
            "de solicitar o pagamento: se o Marketing autorizou a diferença, "
            "quem autorizou e quando."
        )
        justificativa = st.text_area(
            "Por que solicitar o pagamento mesmo assim? *", height=90,
            placeholder="Ex: o Marketing pediu mais reels no lugar do feed porque o "
                        "retorno do formato foi melhor. Autorizado por [nome] em "
                        "[data].")

    # A CHAVE DO CRONOGRAMA, DESLIGADA POR PADRÃO (11/09/2026).
    #
    # Decisão do auditor, depois de apontar a volatilidade do Calendário: "essa
    # parte da planilha deles é bem volátil, sempre pode mudar... acho melhor
    # deixar essa parte do financeiro OFF por enquanto".
    #
    # DESLIGADA, A MENSAGEM VOLTA A SER SÓ A LISTA DE ENTREGAS, que é o formato de
    # 09/09/2026. O cronograma continua sendo montado, aparecendo na tela e sendo
    # congelado no registro do fechamento: o que a chave controla é apenas o que
    # sai desta máquina para outra área.
    #
    # LIGAR É DECISÃO DE QUEM FECHA, e depende de confirmar com o Marketing como
    # eles remarcam uma data (linha nova ou edição da mesma linha). Enquanto isso
    # não for confirmado, uma data remarcada pode aparecer como ❌ na mensagem.
    incluir_cronograma = st.checkbox(
        "Incluir o cronograma do ciclo na mensagem",
        value=False,
        # ENCURTADO EM 17/09/2026.
        help="Desligado por padrão: data remarcada no Calendário pode virar "
             "❌ sem ser problema de verdade.")

    if incluir_cronograma:
        # OS DOIS HORÁRIOS DO CABEÇALHO DO CRONOGRAMA (11/09/2026).
        #
        # O cronograma real que o Marketing manda abre com duas linhas: "Horário de
        # postagem: entre 9h e 20h" e "Horário limite para aprovação dos vídeos:
        # 16h".
        #
        # ELES SÃO CAMPO DIGITÁVEL, E NÃO TEXTO FIXO, por decisão do auditor no
        # mesmo dia. Esses horários são termo de contrato e não estão em planilha
        # nenhuma que o programa leia. Fixar um valor para todo influenciador seria
        # escrever um número que não foi medido, no texto que vai para outra área.
        # Vazio, não aparecem.
        _hora_esq, _hora_dir = st.columns(2)
        horario_postagem = _hora_esq.text_input(
            "Horário de postagem combinado", placeholder="ex: entre 9h e 20h",
            help="Do contrato. Fica de fora da mensagem se você não preencher.")
        horario_aprovacao = _hora_dir.text_input(
            "Horário limite para aprovação dos vídeos", placeholder="ex: 16h",
            help="Do contrato. Fica de fora da mensagem se você não preencher.")
    else:
        horario_postagem = horario_aprovacao = ""

    # O QUE JÁ ESTÁ NA MONITORAMENTO, MOSTRADO E NÃO USADO PARA DECIDIR
    # (04/09/2026, pedido do auditor). A coluna PAGAMENTO é do Marketing, por
    # POST, preenchida à mão na planilha; não tem relação com solicitar o
    # pagamento do CICLO, que é a pergunta desta tela.
    _contagem_pagamento = collections.Counter(
        (l.get("pagamento") or "").strip() or "(vazio)" for l in contagem["linhas"])
    if _contagem_pagamento:
        st.caption(
            "Na Monitoramento, coluna PAGAMENTO, para as "
            f"{len(contagem['linhas'])} tela(s) deste ciclo: "
            + ", ".join(f"{n} {v}" for v, n in _contagem_pagamento.most_common())
            + ". Isto é o pagamento **post a post**, o que já está lá, e "
              "não decide a solicitação abaixo."
        )

    falta_justificar = fechamento["exige_justificativa"] and not justificativa.strip()

    entregue_texto = ", ".join(
        f"{n} {t.lower()}" for t, n in sorted(contagem["entregue"].items())) or "nada"

    def texto_para_o_financeiro():
        """O aviso que a pessoa copia e cola no WhatsApp do Financeiro.

        O FORMATO MUDOU EM 09/09/2026, a pedido do auditor. Ele mostrou uma
        mensagem real que o próprio Marketing manda no grupo deles, um checklist
        de cronograma ("CRONOGRAMA VERNECK + EDS (CICLO 4/6)", uma linha numerada
        por data): "não tem aquela frase nem nada daquilo, é uma mensagem assim".
        O texto corrido de antes (situação explicada, motivos, decisões conferidas
        à mão, justificativa, assinatura) saiu inteiro. Nenhuma dessas informações
        se perdeu: elas continuam na planilha de fechamentos e no arquivo local
        (ver registro_fechamentos.py), só não vão mais para o texto do WhatsApp.

        O CHECKLIST É POR DATA, NÃO POR TIPO. O ✅ marca ENTREGA NA DATA, só isso.
        NÃO é o veredito de conformidade daquela peça, que é outra pergunta e mora
        na régua da portaria, não neste checklist, para não misturar as duas
        coisas.

        A LISTA PASSOU A SAIR DO CALENDÁRIO EM 11/09/2026, e antes saía só da
        Monitoramento. O auditor corrigiu a premissa: "essa mensagem é de acordo
        com essa planilha do calendário que automatizamos agora. a cada rodada de
        post eles marcam o check na data que consta na planilha do calendário que é
        anteriormente preenchida por eles". Com isso a mensagem ganhou as datas ❌,
        que a Monitoramento não tem porque nelas não houve download, e a linha sem
        marca no fim, que era a limitação escrita aqui antes ("este programa não
        tem essa data futura").

        O ✅ CONTINUA SENDO DO QUE A AUDITORIA TEM, e não do que a planilha deles
        diz. Ver ee.montar_cronograma para as quatro divergências medidas que
        motivaram essa escolha. Quando os dois discordam, a linha diz isso.

        A LINHA "SITUAÇÃO DO ESCOPO" fica sempre, pago ou não, para quem lê saber
        se está solicitando um ciclo que bateu com o contrato ou não.

        A MENSAGEM PASSOU A SER UMA SOLICITAÇÃO DE PAGAMENTO (09/09/2026), não
        mais um registro de "já foi pago?". Quando exige_justificativa é
        verdadeiro, o texto digitado por quem fecha entra aqui também, porque
        quem recebe a solicitação precisa saber por que ela está sendo pedida
        mesmo com o ciclo diferente do escopo.

        E ele não leva dado pessoal de ninguém: só o @ do perfil, que é público, a
        marca, o ciclo, a data de cada post e a situação do escopo."""
        partes = [
            f"*Fechamento de ciclo · @{handle}*",
            f"{', '.join(marcas) or 'marca não informada'} · Ciclo {ciclo}",
        ]
        if horario_postagem.strip():
            partes.append(f"Horário de postagem: {horario_postagem.strip()}")
        if horario_aprovacao.strip():
            partes.append("Horário limite para aprovação dos vídeos: "
                          f"{horario_aprovacao.strip()}")
        partes.append("")

        if incluir_cronograma and cronograma_resolvido:
            for item in cronograma_resolvido:
                partes.append(linha_de_cronograma(item, para_mensagem=True))
            partes.append("")
            # O CARIMBO DIZ QUE ISTO É UMA FOTO DE UM MOMENTO (11/09/2026), porque
            # o Calendário é planilha viva de outra área e pode ter mudado desde a
            # leitura. Sem a data, a lista se lê como estado permanente.
            partes.append(f"Cronograma lido do Calendário em "
                          f"{_lido_em:%d/%m/%Y, %Hh%M}.")
        else:
            # A LISTA DE ENTREGAS, que é o formato de 09/09/2026 e o que sai com a
            # chave do cronograma desligada.
            #
            # A MENSAGEM NÃO MENTE POR OMISSÃO: ela diz, na própria linha, que as
            # datas sem postagem ficaram de fora. Uma lista só de ✅ passaria a
            # impressão de cronograma cumprido, que é o contrário do que se sabe.
            for numero, post in enumerate(contagem["posts"], start=1):
                data_legivel = (f"{post['data']:%d/%m}"
                                if post["data"] else "data não legível")
                partes.append(f"{numero}º - {data_legivel} ✅")
            partes.append("")
            partes.append("(esta lista traz só as entregas, e não as datas sem "
                          "postagem)")
        if contagem["entregue_organico"]:
            organico_texto = ", ".join(
                f"{n} {t.lower()}" for t, n in sorted(contagem["entregue_organico"].items()))
            partes.append("")
            partes.append(f"Além disso, como orgânico: {organico_texto}")
        partes.append("")
        partes.append(f"Situação do escopo: {_ap['icone']} {_ap['curto'].upper()}")
        if justificativa.strip():
            partes.append(f"Justificativa: {justificativa.strip()}")
        return "\n".join(partes)

    if st.button("Solicitar pagamento, gerar texto para o Financeiro",
                 type="primary", disabled=falta_justificar,
                 help="Preencha a justificativa obrigatória." if falta_justificar else None):
        registro = {
            "quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quem": identidade.quem_sou_eu(),
            "influenciador": f"@{handle}",
            "ciclo": ciclo,
            "marca": ", ".join(marcas),
            "periodo": periodo,
            "escopo": texto_escopo,
            "entregue": entregue_texto,
            "situacao": fechamento["situacao"],
            "justificativa": justificativa.strip(),
            # AS ESCOLHAS QUE O PROGRAMA NÃO FAZ ficam gravadas junto, senão o
            # fechamento registraria o resultado sem registrar a decisão que levou
            # a ele.
            "decisoes": "; ".join(f"{k}: {v}" for k, v in decisoes.items() if v),
            "pecas_reprovadas": len(contagem["reprovadas"]),
            "pecas_sem_evidencia": len(contagem["sem_evidencia"]),
            "pecas_no_limite_da_automacao": len(contagem["limite_da_automacao"]),
            "pecas_sem_veredito": len(contagem["sem_veredito"]),
            # CONGELADO SEMPRE, com a chave da mensagem ligada ou desligada. Ver
            # cronograma_congelado() para o porquê.
            "cronograma_calendario": cronograma_congelado(),
        }
        try:
            _na_planilha, _motivo_planilha = gravar_fechamento(registro)
            st.session_state["fechamento_gravado"] = texto_para_o_financeiro()
            st.session_state["fechamento_na_planilha"] = _na_planilha
            st.session_state["fechamento_motivo_planilha"] = _motivo_planilha
        except OSError as e:
            st.error(f"Não consegui gravar o registro do fechamento: {str(e)[:160]}")

    if st.session_state.get("fechamento_gravado"):
        st.success("Fechamento registrado. Copie o texto abaixo e cole no WhatsApp "
                   "do Financeiro.")
        st.code(st.session_state["fechamento_gravado"], language=None)
        # DIZER ONDE FICOU, E DIZER QUANDO FICOU SÓ NUM LUGAR. O registro em cópia
        # única nesta máquina foi o problema que motivou a planilha; esconder que a
        # planilha falhou recriaria o problema em silêncio.
        if st.session_state.get("fechamento_na_planilha"):
            st.caption("Ficou na planilha de fechamentos e no arquivo local.")
        else:
            st.warning(
                "Ficou **só no arquivo local desta máquina**, não foi para a "
                f"planilha: {st.session_state.get('fechamento_motivo_planilha')}"
            )

    # --- histórico ---------------------------------------------------------
    if os.path.exists(ARQUIVO_FECHAMENTOS):
        with st.expander("Fechamentos já registrados"):
            try:
                with open(ARQUIVO_FECHAMENTOS, encoding="utf-8") as f:
                    anteriores = list(csv.DictReader(f))
                if anteriores:
                    st.dataframe(pd.DataFrame(anteriores[::-1]),
                                 use_container_width=True, hide_index=True)
                else:
                    st.caption("Nenhum ainda.")
            except Exception as e:
                st.caption(f"Não consegui ler o histórico: {str(e)[:120]}")
