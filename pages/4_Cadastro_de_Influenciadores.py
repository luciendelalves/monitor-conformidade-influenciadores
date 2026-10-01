# -*- coding: utf-8 -*-
"""
Consulta do cadastro de influenciadores, dentro do programa.

DESDE 14/09/2026, ESTA TELA TAMBÉM CORRIGE CAMPO DO CADASTRO, célula por
célula, pedido do auditor para reduzir o uso direto da planilha. A escrita
passa por `cadastro.corrigir_campo_no_cadastro`, no mesmo padrão de
`fluxo_downloads.corrigir_ciclo_na_monitoramento`: lê o valor atual antes de
gravar, só grava se mudou de verdade, e registra quem mudou o quê. Só as
colunas de `COLUNAS_PERMITIDAS` podem ser corrigidas, nunca as de
`COLUNAS_OMITIDAS_POR_PRIVACIDADE` — a função recusa por conta própria, e
não depende só do filtro da tela.

O NETLEX SAIU DAQUI EM 14/09/2026 (a coluna calculada e a consulta de
histórico). Era dado próprio da Auditoria, não da Dados_influ, e não tinha
mais função na tela de cadastro do Marketing.

DESDE 23/09/2026, A TELA NUNCA ESCREVE NA DADOS_INFLU REAL, nem por engano:
a conta do programa só tem permissão de leitura nela (confirmado consultando
a API, `capabilities.canEdit` voltou False). Antes de mostrar qualquer
coisa, a tela lê a real e espelha o conteúdo inteiro numa cópia de teste
(planilha nossa, dona somos nós), e as três escritas (Adicionar, Corrigir,
Excluir) só miram essa cópia, nunca a real. Ver
`cadastro.espelhar_cadastro_para_teste` para o porquê de ESPELHAR em vez de
manter a cópia vazia: Corrigir e Excluir apontam a linha por número, e esse
número só é confiável quando leitura e escrita vêm exatamente da mesma
planilha.

POR QUE ESTA PÁGINA EXISTE (31/08/2026)

Pedido do auditor, como primeiro passo da aba de cadastro. A ideia inicial era
CRIAR um cadastro na ferramenta, e a medição das fontes mostrou que isso seria
copiar 20 colunas que já existem: a Dados_influ tem 203 linhas, com escopo,
status, categoria, responsável interno e a janela de contrato.

O que a aba de cadastro vai acrescentar depois é só o que falta lá, que é o
número do contrato no Netlex, e ele entra como campo OPCIONAL numa planilha
NOSSA, nunca na deles. Isso está registrado no PROMPT_CONTINUACAO.

O QUE ESTA PÁGINA NÃO FAZ, DE PROPÓSITO

Ela não decide quem está ativo. Medido em 31/08/2026: a coluna STATUS diz 79
ATIVO, e o auditor informou que a operação trabalha com 45. Nenhum recorte da
planilha dá 45 (ATIVO com contrato em vigor são 60; com os sem data de fim,
70). Enquanto o critério dos 45 não estiver combinado, a tela mostra o que a
planilha diz e deixa a contagem por status à vista, para a conversa ser sobre o
dado e não sobre o número.

DADO PESSOAL FICA DE FORA, E POR LISTA DE PERMISSÃO

A Dados_influ tem colunas sem função na auditoria de publicidade: ID_CONTA,
CONTA, CONTATO_AGENTE, ENDERECO, ANIVERSARIO e MEDIDAS. Influenciador é pessoa
física, então trazer isso para a tela seria coletar mais do que a finalidade
exige (princípio da necessidade, LGPD art. 6º, III).

As colunas são escolhidas por LISTA DE PERMISSÃO, e não bloqueando as
indesejadas. É o mesmo critério do .gitignore deste projeto e pelo mesmo motivo:
numa lista de bloqueio, esquecer um nome expõe o dado; numa lista de permissão,
esquecer significa não mostrar, que é o erro seguro. Se o Marketing acrescentar
uma coluna nova, ela não aparece aqui até alguém liberar de propósito.
"""
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import acesso
import cadastro
import estilo
import identidade

# QUEM PODE ABRIR, conferido aqui também. Ver a seção da barreira como página em
# acesso.py: cada página confere por conta própria, porque esta é uma rota
# própria do Streamlit e em certas situações roda sem passar pelo painel.
acesso.exigir_login()

import sheets_client

PASTA_TESTE = os.path.join(BASE, "teste_watch_folder")

# O identificador vem de ARQUIVO, seguindo o padrão do projeto: trocar de
# planilha é trocar o conteúdo do arquivo, sem mexer no código.
#
# ESTE ARQUIVO É SÓ DESTA TELA, DESDE 23/09/2026, e a mudança nasceu de um
# incidente. Antes esta tela lia o MESMO arquivo que
# `fluxo_downloads.ARQUIVO_CADASTRO_ID` usa para a trava de criar pasta
# (`impedimento_para_criar_pasta`, que só cria pasta pra @ que está no
# cadastro). Apontar esse arquivo para uma cópia de teste, pra poder testar
# "Adicionar" sem gravar na Dados_influ real, deixou o download real cego
# para os 208 influenciadores de verdade por alguns minutos: a trava passou
# a achar que NENHUM @ estava cadastrado, porque a cópia de teste estava
# vazia. Foi revertido rápido, mas o motivo de existirem dois arquivos
# agora é justamente não deixar isso acontecer de novo: esta tela pode
# apontar pra onde quiser, testando o que quiser, sem arriscar o portão de
# segurança que o download usa pra valer.
#
# ESTE ARQUIVO APONTA PARA A PLANILHA REAL, e é usado só como FONTE de
# leitura, nunca de escrita (desde 23/09/2026, ver ARQUIVO_ID_COPIA_TESTE
# abaixo e `cadastro.espelhar_cadastro_para_teste`). A conta do programa só
# tem permissão de ver esta planilha, e é isso que confirma que a tela nunca
# escreve nela: o Google recusaria.
ARQUIVO_ID = os.path.join(PASTA_TESTE, "cadastro_planilha_id_tela.txt")

# A CÓPIA QUE A TELA DE VERDADE LÊ E ESCREVE, DESDE 23/09/2026. É planilha
# nossa, o programa é dono. A cada abertura da tela, ela é APAGADA e
# REESCRITA com o conteúdo atual da real (só leitura na real, permitida),
# antes de qualquer coisa aparecer na tela. Isso resolve dois problemas de
# uma vez: Adicionar/Corrigir/Excluir nunca arriscam a Dados_influ real
# (impossível, porque nem apontam pra ela), e Corrigir/Excluir continuam
# certos sobre qual linha é qual, porque a cópia acabou de nascer igual à
# real (sem isso, a linha 5 da tela podia não ser a linha 5 da cópia).
ARQUIVO_ID_COPIA_TESTE = os.path.join(PASTA_TESTE, "cadastro_planilha_id_copia_teste.txt")
ABA = "Dados_influ"

# Colunas que aparecem, na ordem em que aparecem. LISTA DE PERMISSÃO: o que não
# está aqui não é mostrado, mesmo que exista na planilha. Ver o cabeçalho.
#
# AGENTE E ESTADO ENTRARAM EM 23/09/2026, achado pelo auditor comparando com
# a planilha original: a Dados_influ tem 19 colunas nomeadas, e só 17
# apareciam aqui, 11 mostradas mais 6 em COLUNAS_OMITIDAS_POR_PRIVACIDADE.
# As duas que sobravam não estavam em NENHUMA das duas listas, ou seja,
# tinham sumido por esquecimento, não por decisão de privacidade.
#
# CONFERIDO O CONTEÚDO REAL antes de decidir, porque "sumiu por esquecimento"
# não é o mesmo que "seguro pra mostrar":
#   AGENTE   "Nexa", "Interno" — nome da agência que representa o
#            influenciador, ou "Interno" quando não tem agência. É
#            classificação comercial, do mesmo tipo de PLATAFORMA e
#            CATEGORIA, que já apareciam.
#   ESTADO   "CE", "RJ", "SP"... — a sigla do estado do influenciador. Isto
#            É dado pessoal dele (localização), diferente de AGENTE. Mas o
#            influenciador é contraparte comercial, não apostador, e a
#            sigla do estado é bem mais grosseira que o ENDERECO completo
#            (que continua omitido). Entra, e fica registrado aqui o
#            porquê, para quem revisar esta linha depois ter o raciocínio à
#            mão, não só a conclusão.
COLUNAS_PERMITIDAS = [
    "INFLU",
    "STATUS",
    "CATEGORIA",
    "RESPONSAVEL",
    "AGENTE",
    "PLATAFORMA",
    "ESTADO",
    "NUM_SEGUIDORES",
    "ESCOPO",
    "INÍCIO_CONTRATO",
    "FIM_CONTRATO",
    "LINKS_DIVULGAÇÃO",
    "Documentos",
]

# Ditas na tela para ninguém supor que a planilha só tem o que aparece aqui.
COLUNAS_OMITIDAS_POR_PRIVACIDADE = [
    "ID_CONTA", "CONTA", "CONTATO_AGENTE", "ENDERECO", "ANIVERSARIO", "MEDIDAS",
]

# SÓ PARA O FORMULÁRIO DE ADICIONAR, DESDE 23/09/2026: "Documentos" saiu de
# lá, pedido do auditor, porque aquele campo leva para outra planilha
# (Netlex) e digitar algo à mão ali, sem saber a convenção de link, não
# ajuda ninguém. A TABELA E O SELETOR DE CORREÇÃO CONTINUAM COM ELA: são
# outra pergunta, "o que já está gravado" e "corrigir o que já está
# gravado", não "inventar um valor novo do zero".
COLUNAS_FORA_DO_FORM_DE_ADICIONAR = ["Documentos"]

# QUAL WIDGET CADA COLUNA GANHA NO FORMULÁRIO DE ADICIONAR, DESDE 23/09/2026.
#
# Pedido do auditor: "o que der para ter a opção de Escolher, fica mais
# prático". Os valores de cada select vieram de MEDIR a planilha real
# (13uLhupENDl6bSHfRioaQz0mcZUio_IOojp1_c1CFhQU, aba Dados_influ, 208
# linhas em 23/09/2026), não de suposição.
#
# FICARAM DE FORA DO SELECT, DE PROPÓSITO, alguns valores que apareceram só
# uma vez e parecem erro de digitação, não opção de verdade: "MICRO" e "SEO"
# em CATEGORIA (esses dois são vocabulário de NUM_SEGUIDORES e de
# RESPONSAVEL, não de categoria), e "MÉDIA" em NUM_SEGUIDORES (parece só a
# flexão de "MÉDIO"). Um select com essas opções ensinaria o erro como se
# fosse uma escolha válida. Isto não corrige o que já está gravado, só não
# oferece o erro como opção nova.
#
# RESPONSAVEL FICOU DE FORA, DE PROPÓSITO: são pessoas do time, e esse
# grupo muda com mais frequência que uma categoria de negócio. Uma lista
# fixa aqui ficaria errada no primeiro desligamento ou contratação. "O que
# não der, pode tirar" — aqui não deu.
#
# ESTADO USA A LISTA OFICIAL DAS 27 UNIDADES DA FEDERAÇÃO, não só as 18 que
# já apareceram na planilha: um influenciador novo pode vir de um estado
# que ainda não teve nenhum cadastrado.
#
# NENHUMA DESSAS LISTAS É FECHADA PARA SEMPRE, e essa dúvida do auditor
# ("não sei se AGENTE muda ou se é padrão") é justa: CATEGORIA, AGENTE e
# PLATAFORMA são classificação de negócio, e negócio ganha opção nova (uma
# agência nova, uma categoria nova) sem pedir licença ao código. Por isso
# TODO select desta lista ganha a opção OPCAO_OUTRO (abaixo), que troca o
# select por um campo de texto na hora. ESTADO é o único caso realmente
# fechado (as 27 UFs não mudam), mas ganha a mesma saída, por segurança e
# simplicidade de manter um comportamento só.
OPCOES_DO_CAMPO = {
    "STATUS": ["ATIVO", "INATIVO", "EM ELABORAÇÃO", "EM RENOVAÇÃO"],
    "CATEGORIA": ["INFLUENCIADOR", "STREAMER", "FUTEBOL", "AFILIADOS",
                 "BRANDING", "EMBAIXADOR"],
    "AGENTE": ["Interno", "Nexa", "krew"],
    "PLATAFORMA": ["LOTTU", "EDS", "ONA", "TODAS", "ONA + LOTTU", "EDS + LOTTU"],
    "NUM_SEGUIDORES": ["NANO", "MICRO", "MÉDIO", "MACRO", "PREMIUM"],
    "ESTADO": ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
              "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
              "RS", "RO", "RR", "SC", "SP", "SE", "TO"],
}

OPCAO_OUTRO = "outro (digitar)"

# QUAIS COLUNAS SÃO DATA, para ganhar calendário em vez de texto livre. As
# duas trocam de INÍCIO_CONTRATO/FIM_CONTRATO no formato DD/MM/AAAA que a
# planilha já usa, sem depender de quem digita acertar a barra e a ordem.
COLUNAS_DE_DATA = ["INÍCIO_CONTRATO", "FIM_CONTRATO"]


def _identificador():
    """Lê o identificador da planilha do arquivo.

    utf-8-sig, e NÃO utf-8: quem grava esse arquivo pelo PowerShell ou pelo
    Bloco de Notas deixa uma marca invisível no começo (o BOM), e o Python a
    entrega como parte do texto. O `.strip()` não a remove, porque ela não é
    espaço em branco.

    Aconteceu na primeira vez que esta tela rodou, em 31/08/2026: o endereço
    montado ficou com `%EF%BB%BF` antes do identificador e o Google respondeu
    404 dizendo que não existe. O erro na tela apontava para permissão, que era
    a suspeita errada.

    Vale um lstrip do caractere por cima, porque utf-8-sig só remove a marca
    quando ela está no primeiro byte, e arquivo regravado por cima de outro
    pode ficar com ela em outro lugar."""
    try:
        with open(ARQUIVO_ID, encoding="utf-8-sig") as f:
            valor = f.read()
        return valor.replace("﻿", "").strip() or None
    except OSError:
        return None


def _identificador_copia_teste():
    """Mesma leitura de `_identificador()`, para o arquivo da cópia de teste."""
    try:
        with open(ARQUIVO_ID_COPIA_TESTE, encoding="utf-8-sig") as f:
            valor = f.read()
        return valor.replace("﻿", "").strip() or None
    except OSError:
        return None


def _com_arroba(valor):
    """Garante o "@" na frente do handle, sem dobrar.

    SEM DOBRAR O @ (15/09/2026, virou função só em 23/09/2026): 202 das 206
    linhas já guardam o INFLU com "@" na frente, e sempre acrescentar um na
    frente dava "@@handle" pra elas, só as poucas sem @ ficavam certas.
    Achado de novo em 23/09/2026 na tela de Excluir, que tinha o mesmo
    f"@{...}" sem essa checagem: cada lugar da tela que mostra o handle
    precisa passar por aqui, não repetir a conta."""
    texto = str(valor or "").strip()
    return texto if texto.startswith("@") else f"@{texto}"


def _ler_data(texto):
    """Lê as formas que aparecem em planilha de Marketing.

    Devolve None quando não dá para ler, e quem chama trata isso como
    desconhecido, NUNCA como vencido: chutar vencido criaria alerta falso sobre
    contrato, que é o pior tipo de erro para esta tela."""
    t = str(texto or "").strip()
    if not t:
        return None
    t = t.split()[0]
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(t, formato).date()
        except ValueError:
            continue
    if t.isdigit() and len(t) == 5:
        # Serial do Sheets, dias desde 30/12/1899.
        try:
            return date(1899, 12, 30) + timedelta(days=int(t))
        except (ValueError, OverflowError):
            return None
    return None


# Guarda por 10 minutos. A planilha do Marketing muda algumas vezes por dia, e
# sem isso cada clique na tela viraria uma leitura da planilha inteira, para cada
# pessoa com a página aberta.
@st.cache_data(ttl=600, show_spinner="Lendo o cadastro na planilha do Marketing...")
def carregar(planilha_id):
    resp = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha_id, range=f"'{ABA}'!A1:T",
        ).execute()
    )
    valores = resp.get("values", [])
    if not valores:
        return pd.DataFrame(), []
    cabecalho = [str(c).strip() for c in valores[0]]
    linhas = valores[1:]
    largura = len(cabecalho)
    normalizadas = [(linha + [""] * largura)[:largura] for linha in linhas]
    tabela = pd.DataFrame(normalizadas, columns=cabecalho)
    return tabela, cabecalho


estilo.cabecalho(
    "Cadastro de influenciadores",
    # ENCURTADA DE NOVO EM 17/09/2026, mesmo pedido da tela de Downloads. A
    # ressalva de dado pessoal continua valendo no código (COLUNAS_OMITIDAS_
    # POR_PRIVACIDADE), só saiu do texto da tela.
    "Consulta o cadastro que o Marketing mantém, com correção controlada de campo.",
)

_planilha_real = _identificador()
_planilha_copia = _identificador_copia_teste()
if not _planilha_real or not _planilha_copia:
    _faltando = ([os.path.basename(ARQUIVO_ID)] if not _planilha_real else []) + (
        [os.path.basename(ARQUIVO_ID_COPIA_TESTE)] if not _planilha_copia else [])
    st.error(
        "**Não sei em qual planilha está o cadastro.** Falta o identificador "
        f"em `{' e '.join(_faltando)}`, na pasta `teste_watch_folder`.\n\n"
        "Isso é de propósito: o programa não guarda identificador de planilha no "
        "código, para trocar de planilha ser trocar o conteúdo de um arquivo."
    )
    st.stop()


@st.cache_data(ttl=600, show_spinner="Atualizando a cópia de teste com o cadastro real...")
def _espelhar(planilha_real_id, planilha_teste_id):
    # Cacheado pelos mesmos 10 minutos de `carregar`, de propósito: sem isso,
    # cada clique na tela (o Streamlit reexecuta a página inteira a cada
    # interação) reespelharia a planilha de novo, gastando chamada à toa.
    return cadastro.espelhar_cadastro_para_teste(planilha_real_id, planilha_teste_id, ABA)


# BOTÃO "ATUALIZAR AGORA", MESMO PADRÃO DA MONITORAMENTO E DO FINANCEIRO
# (23/09/2026, pedido do auditor: "como nas outras"). Precisa limpar as DUAS
# caches, não só uma: `carregar` guarda a leitura da cópia, `_espelhar`
# guarda o espelhamento em si. Limpar só a primeira mostraria de novo a
# cópia velha, porque o espelhamento (mais caro) continuaria valendo os 10
# minutos que faltam.
_topo_esq, _topo_dir = st.columns([4, 1])
_topo_esq.caption(
    "Consulta a Dados_influ do Marketing, espelhada numa cópia antes de "
    "abrir. Os dados ficam guardados por 10 minutos."
)
if _topo_dir.button("Atualizar agora", icon=":material/refresh:",
                    use_container_width=True):
    carregar.clear()
    _espelhar.clear()
    st.rerun()

try:
    _espelhar(_planilha_real, _planilha_copia)
except Exception as e:
    st.error(
        f"**Não consegui atualizar a cópia de teste a partir do cadastro real.** "
        f"{type(e).__name__}: {str(e)[:300]}\n\n"
        "Se for erro de permissão, confira se a conta do programa continua com "
        "acesso de leitura à planilha do Marketing e de escrita na cópia de teste."
    )
    st.stop()

planilha = _planilha_copia

try:
    tabela, cabecalho = carregar(planilha)
except Exception as e:
    st.error(
        f"**Não consegui ler o cadastro.** {type(e).__name__}: {str(e)[:300]}\n\n"
        "Se for erro de permissão, confira se a conta do programa continua com "
        "acesso de leitura à planilha do Marketing."
    )
    st.stop()

if tabela.empty:
    st.warning("A aba está vazia depois de espelhar o cadastro real. Confira se a "
               "Dados_influ real também está vazia.")
    st.stop()

# ZONA DE CONSULTA (15/09/2026): cards de status, conferência de vencimento,
# filtros e a tabela, tudo o que é SÓ LEITURA nesta tela, num só bloco visual
# para separar da zona de escrita mais abaixo.
with st.container(key="cad_zona_consulta"):
    # --- Contagem por status, antes de qualquer filtro ---
    #
    # Fica no topo de propósito, e é o primeiro número que a tela mostra. Em
    # 31/08/2026 a planilha dizia 79 ATIVO enquanto a operação trabalhava com 45, e
    # esse tipo de diferença precisa aparecer sozinha, não depois de alguém
    # desconfiar.
    coluna_status = "STATUS" if "STATUS" in tabela.columns else None
    # CARDS CLICÁVEIS REMOVIDOS EM 15/09/2026. A ideia (clicar no card filtra
    # a tabela, igual ao seletor "Situação" logo abaixo) tentou dois desenhos
    # diferentes no mesmo dia, e os dois saíram do padrão visual do resto do
    # app: primeiro um contraste forte demais (card ativo em navy sólido),
    # depois uma tentativa de deixar sutil que ficou inconsistente na tela
    # (marcador do ativo sumindo ou aparecendo errado, por depender de
    # detalhe interno do Streamlit que não dava pra confirmar sem abrir a
    # tela de verdade num navegador). O auditor topou o caminho mais seguro:
    # voltar pro `st.metric`, sem clique, e o seletor "Situação" logo abaixo
    # continua fazendo o mesmo filtro, de forma manual.
    if coluna_status:
        contagem = tabela[coluna_status].str.strip().str.upper().replace("", "(vazio)")
        resumo = contagem.value_counts()
        colunas_metrica = st.columns(min(len(resumo), 5) + 1)
        colunas_metrica[0].metric("No cadastro", len(tabela))
        for coluna, (nome, quantos) in zip(colunas_metrica[1:], resumo.items()):
            coluna.metric(nome.title(), int(quantos))
    
    # --- Contrato vencido contra status, que é conferência e não filtro ---
    #
    # Não muda a tabela nem classifica ninguém: só conta e avisa. As duas
    # combinações abaixo foram medidas em 31/08/2026 e nenhuma delas é
    # necessariamente erro (contrato pode ter sido encerrado sem baixa na planilha,
    # ou renovado sem encerrar o anterior, o que o auditor já apontou como comum).
    # Por isso o texto diz "conferir", nunca "irregular".
    if coluna_status and "FIM_CONTRATO" in tabela.columns:
        hoje = date.today()
        datas = tabela["FIM_CONTRATO"].map(_ler_data)
        status_limpo = tabela[coluna_status].str.strip().str.upper()
        ativo_vencido = int(((status_limpo == "ATIVO") & datas.map(
            lambda d: bool(d) and d < hoje)).sum())
        inativo_em_vigor = int(((status_limpo == "INATIVO") & datas.map(
            lambda d: bool(d) and d >= hoje)).sum())
        if ativo_vencido or inativo_em_vigor:
            partes = []
            if ativo_vencido:
                partes.append(f"**{ativo_vencido}** com status ATIVO e data de fim já passada")
            if inativo_em_vigor:
                partes.append(f"**{inativo_em_vigor}** com status INATIVO e data de fim no futuro")
            st.info(
                "Vale conferir: " + " e ".join(partes) + ". Nenhuma das duas coisas é "
                "necessariamente erro. Contrato pode ter terminado sem alguém dar baixa "
                "na planilha, ou ter sido renovado sem encerrar o anterior. A tela só "
                "conta e mostra, não classifica ninguém."
            )
    
    st.divider()
    
    # --- Filtros ---
    col_a, col_b, col_c = st.columns([2, 2, 3])
    
    opcoes_status = ["Todos"]
    if coluna_status:
        # MAIÚSCULO, PRA CASAR COM OS CARDS DE CIMA (15/09/2026): os cards mostram
        # o status já normalizado (upper), e os dois precisam falar do mesmo jeito
        # pra clicar no card refletir no seletor, e vice-versa.
        opcoes_status += sorted({v.strip().upper() for v in tabela[coluna_status] if str(v).strip()})
    escolha_status = col_a.selectbox("Situação", opcoes_status, key="cad_filtro_situacao")
    
    opcoes_categoria = ["Todas"]
    if "CATEGORIA" in tabela.columns:
        opcoes_categoria += sorted(
            v for v in tabela["CATEGORIA"].str.strip().unique() if v
        )
    escolha_categoria = col_b.selectbox("Categoria", opcoes_categoria)
    
    busca = col_c.text_input("Procurar", placeholder="parte do @ ou do nome do responsável")
    
    filtrada = tabela
    if coluna_status and escolha_status != "Todos":
        filtrada = filtrada[filtrada[coluna_status].str.strip().str.upper() == escolha_status]
    if "CATEGORIA" in tabela.columns and escolha_categoria != "Todas":
        filtrada = filtrada[filtrada["CATEGORIA"].str.strip() == escolha_categoria]
    if busca.strip():
        termo = busca.strip().lower()
        alvo = [c for c in ("INFLU", "RESPONSAVEL") if c in filtrada.columns]
        if alvo:
            casa = pd.Series(False, index=filtrada.index)
            for coluna in alvo:
                casa = casa | filtrada[coluna].str.lower().str.contains(termo, na=False)
            filtrada = filtrada[casa]
    
    # --- Tabela, só com as colunas permitidas ---
    #
    # A comparação ignora espaço no fim porque a planilha tem título com espaço
    # sobrando ("LINKS_DIVULGAÇÃO "), e perder a coluna por causa de um espaço seria
    # o tipo de defeito que ninguém encontra olhando a tela.
    por_nome_limpo = {str(c).strip(): c for c in filtrada.columns}
    visiveis = [por_nome_limpo[c] for c in COLUNAS_PERMITIDAS if c in por_nome_limpo]
    faltantes = [c for c in COLUNAS_PERMITIDAS if c not in por_nome_limpo]
    
    st.caption(f"{len(filtrada)} de {len(tabela)} no cadastro.")
    
    _col_influ = por_nome_limpo.get("INFLU")
    
    para_mostrar = filtrada[visiveis].copy()
    
    st.dataframe(
        para_mostrar, use_container_width=True, hide_index=True,
        column_config={
            "LINKS_DIVULGAÇÃO ": st.column_config.TextColumn("Links de divulgação"),
            "ESCOPO": st.column_config.TextColumn(
                # ENCURTADO EM 17/09/2026.
                "Escopo", help="Como está escrito no contrato, sem conversão "
                               "automática em número."),
        },
    )
    
    if faltantes:
        st.caption("Colunas que a tela esperava e não encontrou na planilha: "
                   + ", ".join(faltantes)
                   + ". Isso costuma querer dizer que o título mudou lá.")
    
    omitidas_presentes = [c for c in COLUNAS_OMITIDAS_POR_PRIVACIDADE if c in por_nome_limpo]
    if omitidas_presentes:
        # ENCURTADO EM 17/09/2026.
        st.caption(
            "Esta tela não mostra dado pessoal: " + ", ".join(omitidas_presentes) + "."
        )

st.divider()

# ZONA DE ESCRITA (15/09/2026, perdeu a cor em 24/09/2026): as três escritas
# desta tela ficam separadas visualmente da consulta acima. Container com
# `key=` continua igual, sem cor própria (ver o comentário de
# .st-key-cad_zona_escrita em estilo.py para o porquê).
with st.container(key="cad_zona_escrita"):
    # EXIGE SUPERVISÃO OU COORDENAÇÃO (15/09/2026), pedido do auditor: as três
    # escritas abaixo mexem na planilha do Marketing (hoje, na cópia
    # espelhada dela), e quem faz precisa poder responder por isso, mesmo
    # controle já usado no envio de arquivo em Downloads (ver
    # acesso.autorizacao_para_qualquer).
    #
    # SÓ NO MOMENTO DE CADA ESCRITA, DESDE 24/09/2026: antes havia também um
    # aviso fixo aqui no topo da zona, sempre visível, e um `disabled=` nos
    # três botões que desligava tudo de antemão para quem não tinha o papel.
    # O auditor pediu para a restrição só aparecer quando a pessoa realmente
    # tentar preencher algo, não como aviso permanente na tela. A checagem
    # de verdade continua a cada clique, mais abaixo, em cada uma das três
    # ações: só mudou o que a tela mostra ANTES do clique.

    # --- corrigir um campo do cadastro (14/09/2026) -----------------------------
    #
    # ÚNICA ESCRITA DESTA TELA, E É NA PLANILHA DO MARKETING: pedido do auditor
    # para reduzir o uso direto dela ("a ideia é não se usar a planilha
    # diretamente ou reduzir o uso"). Célula por célula, nunca grade editável, no
    # mesmo formato do "Corrigir o ciclo de uma linha" do Monitoramento. A escrita
    # de verdade mora em cadastro.corrigir_campo_no_cadastro, que recusa qualquer
    # coluna fora de COLUNAS_PERMITIDAS por conta própria, mesmo que esta tela já
    # filtre o selectbox abaixo só com elas.
    with st.expander("Corrigir um campo do cadastro"):
        # ENCURTADO EM 17/09/2026.
        st.caption(
            "Corrige uma célula. Fica registrado quem, quando e o valor "
            "trocado. Nunca mexe em dado pessoal."
        )
        if _col_influ is None or filtrada.empty:
            st.caption("Sem linha disponível para corrigir com os filtros de cima.")
        else:
            _linhas_cadastro = list(filtrada.index)
    
            def _rotulo_linha_cadastro(indice):
                return _com_arroba(filtrada.loc[indice, _col_influ])
    
            cf1, cf2, cf3, cf4 = st.columns([2.4, 1.6, 2.4, 1])
            linha_cadastro = cf1.selectbox(
                "Linha", options=_linhas_cadastro, format_func=_rotulo_linha_cadastro,
                key="linha_corrigir_cadastro")
            coluna_cadastro = cf2.selectbox(
                "Coluna", options=[c for c in COLUNAS_PERMITIDAS if c in por_nome_limpo],
                key="coluna_corrigir_cadastro")
            valor_atual_cadastro = str(filtrada.loc[linha_cadastro, por_nome_limpo[coluna_cadastro]]
                                       or "").strip()
            # A KEY DEPENDE DA LINHA E DA COLUNA (15/09/2026), de propósito, ao
            # contrário do bug dos cards de status: aqui cada (linha, coluna)
            # é um alvo de edição DIFERENTE, e trocar a seleção precisa mesmo
            # esquecer o texto anterior. Com key fixa, o Streamlit ignorava o
            # `value=` depois da primeira vez e o campo continuava mostrando
            # o texto de uma seleção antiga, arriscando gravar o valor errado
            # numa linha diferente da que estava escrito.
            #
            # MESMO SELETOR DO "ADICIONAR", DESDE 23/09/2026 (pedido do
            # auditor: "me parece que são sempre os mesmos padrões de
            # valor"). Só entra na lista quando o valor atual bate com uma
            # das opções OU quando a coluna nem tem valor ainda: um valor
            # atípico (ex.: "MICRO" em CATEGORIA, já visto na planilha real)
            # continua editável por texto, para não forçar a troca dele por
            # um valor da lista sem a pessoa ter pedido isso.
            #
            # E TODA LISTA GANHA OPCAO_OUTRO (mesma dúvida do auditor sobre
            # AGENTE: "não sei se essa categoria muda ou se é padrão"). Nem
            # STATUS, CATEGORIA, AGENTE, PLATAFORMA, NUM_SEGUIDORES nem
            # ESTADO são garantidos para sempre, então digitar continua
            # possível, só não é mais o padrão.
            _chave_corrigir = f"valor_corrigir_cadastro_{linha_cadastro}_{coluna_cadastro}"
            if coluna_cadastro in OPCOES_DO_CAMPO and (
                    not valor_atual_cadastro or valor_atual_cadastro in OPCOES_DO_CAMPO[coluna_cadastro]):
                _opcoes_corrigir = [""] + OPCOES_DO_CAMPO[coluna_cadastro] + [OPCAO_OUTRO]
                _escolha_corrigir = cf3.selectbox(
                    "Valor novo", options=_opcoes_corrigir,
                    index=_opcoes_corrigir.index(valor_atual_cadastro) if valor_atual_cadastro in _opcoes_corrigir else 0,
                    format_func=lambda v: "escolher..." if not v else v,
                    key=_chave_corrigir)
                if _escolha_corrigir == OPCAO_OUTRO:
                    valor_novo_cadastro = cf3.text_input(
                        f"{coluna_cadastro} (outro valor)", key=f"{_chave_corrigir}_outro")
                else:
                    valor_novo_cadastro = _escolha_corrigir
            elif coluna_cadastro in COLUNAS_DE_DATA:
                _data_corrigir = cf3.date_input(
                    "Valor novo", value=_ler_data(valor_atual_cadastro), format="DD/MM/YYYY",
                    key=_chave_corrigir)
                valor_novo_cadastro = _data_corrigir.strftime("%d/%m/%Y") if _data_corrigir else ""
            else:
                valor_novo_cadastro = cf3.text_input(
                    "Valor novo", value=valor_atual_cadastro, key=_chave_corrigir)
            if cf4.button("Corrigir", use_container_width=True,
                          disabled=valor_novo_cadastro.strip() == valor_atual_cadastro):
                _pode_agora, _motivo_agora, _ = acesso.autorizacao_para_qualquer(
                    acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
                if not _pode_agora:
                    st.info(_motivo_agora)
                else:
                    numero_linha_planilha = linha_cadastro + 2  # cabeçalho na 1, dado a partir da 2
                    try:
                        resultado = cadastro.corrigir_campo_no_cadastro(
                            planilha, ABA, numero_linha_planilha, coluna_cadastro,
                            cabecalho, valor_novo_cadastro, COLUNAS_PERMITIDAS,
                            quem=identidade.quem_sou_eu())
                    except Exception as e:
                        st.error(f"Não consegui corrigir: {type(e).__name__}: {str(e)[:200]}")
                    else:
                        if resultado is None:
                            st.info("Nada mudou: esse já é o valor da célula.")
                        else:
                            antigo, novo = resultado
                            st.success(f"{coluna_cadastro}: trocado de \"{antigo or '(vazio)'}\" "
                                       f"para \"{novo}\". A troca ficou registrada. Use "
                                       f"**Atualizar a página** para a tabela refletir.")
                            carregar.clear()
    
    # --- adicionar um influenciador novo (15/09/2026) ---------------------------
    #
    # Mesma proteção da correção de campo: só as colunas de COLUNAS_PERMITIDAS
    # podem ser preenchidas, cadastro.adicionar_linha_no_cadastro recusa qualquer
    # outra por conta própria. INFLU é o único campo obrigatório, porque é o que
    # identifica a linha; o resto nasce vazio se não for preenchido aqui.
    with st.expander("Adicionar um influenciador"):
        # ENCURTADO EM 17/09/2026.
        st.caption("Cria uma linha nova. Fica registrado quem adicionou e quando.")
        # "Documentos" SAIU DE AQUI EM 23/09/2026 (ver COLUNAS_FORA_DO_FORM_DE_ADICIONAR):
        # aquele campo leva pra outra planilha (Netlex), e digitar algo à mão
        # sem saber a convenção de link não ajuda. A tabela e a correção de
        # campo continuam mostrando/corrigindo o que já está gravado.
        _colunas_do_form = [c for c in COLUNAS_PERMITIDAS
                           if c in por_nome_limpo and c not in COLUNAS_FORA_DO_FORM_DE_ADICIONAR]
        _valores_novo = {}
        for _i in range(0, len(_colunas_do_form), 3):
            _cols_linha = st.columns(3)
            for _c, _nome_col in zip(_cols_linha, _colunas_do_form[_i:_i + 3]):
                _rotulo = f"{_nome_col} *" if _nome_col == "INFLU" else _nome_col
                # WIDGET POR COLUNA, DESDE 23/09/2026 (pedido do auditor: "o
                # que der para ter a opção de Escolher, fica mais prático").
                # As opções vieram de medir a planilha real, não de suposição
                # (ver o comentário de OPCOES_DO_CAMPO).
                if _nome_col in OPCOES_DO_CAMPO:
                    # GANHA OPCAO_OUTRO DESDE 23/09/2026: nenhuma dessas listas
                    # é garantida para sempre (dúvida do próprio auditor sobre
                    # AGENTE), então digitar continua possível quando a lista
                    # não previu o valor, só não é mais o padrão.
                    _escolha_nova = _c.selectbox(
                        _rotulo, options=[""] + OPCOES_DO_CAMPO[_nome_col] + [OPCAO_OUTRO],
                        format_func=lambda v: "escolher..." if not v else v,
                        key=f"novo_cad_{_nome_col}")
                    if _escolha_nova == OPCAO_OUTRO:
                        _valor = _c.text_input(f"{_nome_col} (outro valor)",
                                               key=f"novo_cad_{_nome_col}_outro")
                    else:
                        _valor = _escolha_nova
                elif _nome_col in COLUNAS_DE_DATA:
                    _data = _c.date_input(_rotulo, value=None, format="DD/MM/YYYY",
                                          key=f"novo_cad_{_nome_col}")
                    _valor = _data.strftime("%d/%m/%Y") if _data else ""
                else:
                    _valor = _c.text_input(_rotulo, key=f"novo_cad_{_nome_col}")
                _valores_novo[_nome_col] = _valor
        if st.button("Adicionar", disabled=not _valores_novo.get("INFLU", "").strip()):
            _pode_agora, _motivo_agora, _ = acesso.autorizacao_para_qualquer(
                acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
            if not _pode_agora:
                st.info(_motivo_agora)
            else:
                try:
                    cadastro.adicionar_linha_no_cadastro(
                        planilha, ABA, cabecalho, _valores_novo, COLUNAS_PERMITIDAS,
                        quem=identidade.quem_sou_eu())
                except Exception as e:
                    st.error(f"Não consegui adicionar: {type(e).__name__}: {str(e)[:200]}")
                else:
                    st.success(f"{_com_arroba(_valores_novo['INFLU'])} adicionado. Use "
                               f"**Atualizar a página** para a tabela refletir.")
                    carregar.clear()
    
    # --- excluir uma linha do cadastro (15/09/2026) -----------------------------
    #
    # Destrutivo e sem desfazer por este programa, por isso exige confirmação
    # explícita antes do botão liberar, mesmo padrão de "Tirar material de teste"
    # na tela de Downloads.
    with st.expander("Excluir um influenciador do cadastro"):
        # NÃO ENCURTAR O AVISO DE IRREVERSIBILIDADE (17/09/2026): é ação
        # destrutiva sem desfazer, isso precisa continuar bem visível.
        st.caption(
            "Apaga a linha inteira. **Não tem volta por aqui.** Fica "
            "registrado quem excluiu e quando."
        )
        if _col_influ is None or filtrada.empty:
            st.caption("Sem linha disponível para excluir com os filtros de cima.")
        else:
            _ce1, _ce2 = st.columns([3, 1.4])
            _linha_excluir = _ce1.selectbox(
                "Linha", options=list(filtrada.index),
                format_func=lambda i: _com_arroba(filtrada.loc[i, _col_influ]),
                key="linha_excluir_cadastro")
            _confirmou_exclusao = _ce1.checkbox(
                f"Confirmo excluir {_com_arroba(filtrada.loc[_linha_excluir, _col_influ])} do cadastro",
                key="confirma_excluir_cadastro")
            if _ce2.button("Excluir", type="primary",
                           disabled=not _confirmou_exclusao,
                           use_container_width=True):
                _pode_agora, _motivo_agora, _ = acesso.autorizacao_para_qualquer(
                    acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
                if not _pode_agora:
                    st.info(_motivo_agora)
                else:
                    _handle_excluido = _com_arroba(filtrada.loc[_linha_excluir, _col_influ])
                    try:
                        cadastro.excluir_linha_no_cadastro(
                            planilha, ABA, _linha_excluir + 2, identificacao=_handle_excluido,
                            quem=identidade.quem_sou_eu())
                    except Exception as e:
                        st.error(f"Não consegui excluir: {type(e).__name__}: {str(e)[:200]}")
                    else:
                        st.success(f"{_handle_excluido} excluído. Use **Atualizar a página** "
                                   f"para a tabela refletir.")
                        carregar.clear()
