"""
Consulta da Monitoramento dentro do programa, para não precisar abrir a
planilha só para conferir alguma coisa.

A TELA É PRINCIPALMENTE LEITURA, com uma exceção pequena e consciente: a
correção de ciclo, que resolve um problema real (concorrência entre pessoa e
processo de fundo, valor conferido antes de gravar) sem virar edição de
rotina.

A EDIÇÃO DE PAGAMENTO ESTEVE AQUI E SAIU (04/09/2026). Ter escrita de rotina
numa tela que se anuncia como só leitura obrigava a enfraquecer a própria regra
declarada aqui. CRONOGRAMA e PAGAMENTO, as duas únicas colunas que uma pessoa
muda depois de a linha existir, agora ficam juntas na tela "Cronograma e
Pagamento". Aqui as duas continuam VISÍVEIS e filtráveis, só não editáveis, que
é o que uma tela de conferência precisa.

A TELA "VALIDAÇÃO REGULATÓRIA" SAIU EM 14/09/2026, e o único essencial que
sobrava dela (acompanhar quantos vídeos estão sendo analisados) migrou pra cá.
"TIRAR DA ANÁLISE / DEVOLVER / TENTAR DE NOVO" chegou a migrar também, e SAIU
DE NOVO em 15/09/2026: vídeo analisado por engano não é problema, fica lá com
veredito, e quem quiser o vídeo certo usa o "Baixar de novo" de Downloads. O
motor de análise continua fora do Streamlit, em pipeline_influenciadores.py e
trabalhador.py.
"""

import os
import sys

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import acesso
# O motor do fechamento é importado só pelas duas categorias de gap, para esta
# tela e o Financeiro não escreverem a mesma regra duas vezes.
import escopo_e_entrega as escopo
import estilo
# Entrou em 14/09/2026, com o que migrou da tela de Validação Regulatória:
# acompanhar quantos vídeos estão sendo analisados. O motor de verdade
# continua rodando fora do Streamlit, no processo de fundo; esta tela só lê.
import fila_trabalho
import fluxo_downloads as fluxo
# Entrou em 01/09/2026, com a correção de ciclo: é o que grava QUEM fez a troca,
# e sem esse nome a exceção à regra de não sobrescrever não se sustentaria.
import identidade
import sheets_client

# QUEM PODE ABRIR, conferido aqui também (31/08/2026). Ver a seção da barreira
# como página em acesso.py. Ser só leitura não dispensa a conferência: esta
# página mostra a Monitoramento inteira, que é dado da operação.
acesso.exigir_login()

# A configuração da página fica em painel.py (só pode ser chamada uma vez).
estilo.cabecalho(
    "Monitoramento",
    # ENCURTADA EM 17/09/2026, mesmo pedido da tela de Downloads.
    "Consulta a planilha de Monitoramento sem sair do programa.",
)

# Colunas que a automação preenche, na ordem em que fazem sentido para leitura.
# As outras existem e continuam disponíveis no botão de ver todas.
# "marcacao" fica ao lado de "tipo" de propósito: uma diz o grau de publicidade
# da peça, a outra diz o formato, e as duas juntas é que a descrevem.
# A coluna ARQUIVO entrou aqui em 03/09/2026, ao lado da LINK. As duas apontam
# para lugares diferentes desde aquele dia, e é a de arquivo que serve para
# conferir a peça: LINK é a pasta do post, ARQUIVO é a tela exata.
COLUNAS_PRINCIPAIS = ["handle", "data_post", "ciclo", "tipo", "marcacao", "post",
                      "cronograma", "marca", "pagamento", "situacao",
                      "validacao", "evidencia",
                      "arquivo", "link", "data_download", "validado_em"]
ROTULOS = {
    "handle": "Influenciador", "mes": "Mês", "ano": "Ano", "data_post": "Data do post",
    "ciclo": "Ciclo", "tipo": "Tipo", "post": "Post", "marca": "Marca",
    "cronograma": "Cronograma",
    # Era "Link", passou a "Vídeo" em 29/08/2026 e passou a "Pasta do post" em
    # 03/09/2026, quando a coluna deixou de apontar para o arquivo: entrega do
    # mesmo dia é um post só, então ela aponta para onde as telas do post estão.
    #
    # NAS LINHAS CRIADAS ATÉ 02/09 ELA AINDA APONTA PARA O ARQUIVO, porque são
    # anteriores à mudança. O rótulo fala do que a coluna é hoje, que é o que
    # vale para tudo o que entra daqui em diante.
    "link": "Pasta do post",
    "arquivo": "Arquivo",
    "data_download": "Baixado em", "situacao": "Situação",
    "validacao": "Validação", "evidencia": "Evidência", "validado_em": "Validado em",
    # "Marcação" e não "Tipo de entrega": a coluna guarda uma das duas palavras
    # (ORGANICO ou LINK), e o rótulo tem que dizer o que ela guarda, não
    # afirmar o que aquilo significa em contrato.
    "marcacao": "Marcação",
}


# 60 SEGUNDOS, ERAM 300 (06/09/2026). O auditor: "pq aqui demora tanto
# para atualizar? la na planilha em si já está OK". Cinco minutos de cache
# fazia a tela mostrar dado velho justamente depois de o trabalhador
# terminar uma análise, que é quando a pessoa vem olhar. Ler a planilha é
# uma chamada; a cada minuto é barato e não bate em limite de API.
@st.cache_data(ttl=60, show_spinner="Lendo a Monitoramento...")
def carregar(planilha_id):
    """Lê a planilha inteira de uma vez. Guardado por 1 minuto para não
    consultar o Google a cada clique de filtro."""
    valores = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha_id,
            # Sem teto de linha (07/09/2026): a Monitoramento real já passou de
            # 24.334 linhas e o teto de 20000 fazia a linha desaparecer da
            # consulta sem aviso.
            range=f"'{fluxo.ABA_MONITORAMENTO}'!A1:{fluxo.ULTIMA_COLUNA_MON}",
        ).execute()
    ).get("values", [])
    if not valores:
        return pd.DataFrame(), []

    cabecalho = valores[0]
    # A largura mínima é a última coluna que a automação usa, não um número
    # fixo: o bloco dela cresceu de W para AB e a conta antiga quebrava a tela
    # com "índice fora do intervalo" ao montar os nomes das colunas.
    minimo = max(fluxo.COL_MON.values())
    largura = max(len(cabecalho), max((len(l) for l in valores[1:]), default=0), minimo)
    nomes = []
    for i in range(largura):
        bruto = cabecalho[i].strip() if i < len(cabecalho) and cabecalho[i] else ""
        nomes.append(bruto or f"coluna {i + 1}")
    # nome repetido quebra o DataFrame; numera o repetido em vez de recusar
    vistos = {}
    for i, nome in enumerate(nomes):
        if nome in vistos:
            vistos[nome] += 1
            nomes[i] = f"{nome} ({vistos[nome]})"
        else:
            vistos[nome] = 1

    linhas = [l + [""] * (largura - len(l)) for l in valores[1:]]
    df = pd.DataFrame(linhas, columns=nomes)
    df.insert(0, "Linha", range(2, len(df) + 2))
    df = df[df[nomes[fluxo.COL_MON["handle"] - 1]].astype(str).str.strip() != ""]
    return df, nomes


planilha_id = fluxo._planilha_monitoramento_id()
if not planilha_id:
    st.error(
        "A planilha de Monitoramento de teste ainda não foi configurada. "
        "Rode algo na fila ou no envio primeiro, que ela é criada e o "
        "identificador fica guardado."
    )
    st.stop()

topo_esq, topo_dir = st.columns([4, 1])
# TEXTO CORRIGIDO EM 16/09/2026: dizia "Nada nesta tela altera a planilha",
# e isso deixou de ser verdade quando "Corrigir o ciclo de uma linha" entrou
# (01/09/2026), lá embaixo. A frase estava a dois cliques de ser desmentida
# pela própria tela. O que continua valendo, e é o que importa dizer, é que a
# correção é a exceção, célula por célula, e fica registrada.
topo_esq.caption(
    "Consulta. A única alteração que sai daqui é a correção de ciclo, lá "
    "embaixo, e ela fica registrada. Os dados ficam guardados por 1 minuto."
)
if topo_dir.button("Atualizar agora", icon=":material/refresh:",
                   use_container_width=True):
    carregar.clear()
    st.rerun()

try:
    df, nomes = carregar(planilha_id)
except Exception as e:
    st.error(f"Não consegui ler a Monitoramento agora: {str(e)[:200]}")
    st.stop()

if df.empty:
    st.info("A Monitoramento está vazia.")
    st.stop()

col_de = {chave: nomes[fluxo.COL_MON[chave] - 1] for chave in fluxo.COL_MON}
ROTULOS["pagamento"] = "Pagamento"


def opcoes(chave):
    return sorted(v for v in df[col_de[chave]].astype(str).str.strip().unique() if v)


# FILTRO POR VEREDITO, ACRESCENTADO EM 01/09/2026, a pedido do auditor.
#
# A tabela COLORE por veredito desde antes e tem legenda explicando as cores,
# mas não dava para filtrar por ele: só por Situação, que é outra coisa (diz em
# que ponto do fluxo a linha está, não o resultado da análise).
#
# O veredito é texto livre, do tipo "NÃO CONFORME (Falta aviso de publicidade)",
# então filtrar por valor exato daria uma lista com dezenas de variações. Aqui
# ele é agrupado nas três classificações que a auditoria usa, mais o caso de
# ainda não ter veredito. É o mesmo agrupamento que o resumo da tela de
# Validação faz, e pelo mesmo motivo: o motivo específico continua na célula.
# "FALTA EVIDÊNCIA" ENTROU EM 03/09/2026, do cruzamento com a aba Achado03 do
# papel de trabalho, que separa os casos não validados em duas categorias com a
# contagem fechando exatamente: Evidência Inacessível 223 e Limitação de
# Validação Automatizada 118. Antes disso, "SEM ACESSO À PASTA" e "PASTA VAZIA"
# caíam em "Outro texto" nesta tela, ou seja, no balaio do que ninguém
# reconhece, quando são 77 e 6 linhas de um problema muito claro: falta o
# arquivo. A ação é outra, e por isso a categoria é outra.
CATEGORIAS_VEREDITO = ["Conforme", "Não Conforme", "Falta evidência",
                       "Requer Verificação", "Orgânico (fora da régua)",
                       "Sem veredito"]


def categoria_do_veredito(texto):
    """Em qual das classificações aquele veredito cai.

    A ordem das comparações importa: "NÃO CONFORME" contém "CONFORME", então
    testar conforme primeiro classificaria não conforme como conforme. Foi por
    isso que ficou explícito, e não por gosto.

    "POST ORGÂNICO, NÃO VALIDADO" entrou em 03/09/2026 e vem ANTES das outras,
    por dois motivos: ela contém "NÃO", e sem categoria própria cairia em "Outro
    texto", que é onde vai o que ninguém reconhece. Peça orgânica não é resto:
    ela é um grupo que a auditoria conta à parte, porque a régua dos avisos não
    se aplica a ela (decisão do auditor).

    AS DUAS CATEGORIAS DE GAP vêm do motor (escopo_e_entrega.categoria_do_gap),
    e não são reescritas aqui: o fechamento do ciclo e esta tela têm que dizer a
    mesma coisa sobre a mesma peça."""
    t = str(texto or "").strip().upper()
    if not t:
        return "Sem veredito"
    if "ORGÂNICO" in t or "ORGANICO" in t:
        return "Orgânico (fora da régua)"
    if "NÃO CONFORME" in t or "NAO CONFORME" in t:
        return "Não Conforme"
    gap = escopo.categoria_do_gap(t)
    if gap == escopo.CATEGORIA_GAP_EVIDENCIA:
        return "Falta evidência"
    if gap == escopo.CATEGORIA_GAP_LIMITACAO:
        return "Requer Verificação"
    if "REQUER" in t:
        return "Requer Verificação"
    if "CONFORME" in t:
        return "Conforme"
    # Qualquer outra coisa escrita ali por uma pessoa, inclusive as retiradas da
    # análise com motivo. Não invento categoria: fica visível como o que é.
    return "Outro texto"


# OS NÚMEROS FICAM EM CIMA, E OS FILTROS EMBAIXO (01/09/2026, pedido do auditor).
#
# O espaço é reservado aqui e preenchido depois de os filtros serem aplicados.
# Sem isso, métrica desenhada antes do filtro mostraria o total da planilha e
# não o que está na tela, o que seria pior que a ordem antiga: número em cima
# que não corresponde à tabela embaixo.
espaco_dos_numeros = st.container()

f1, f2, f3, f4, f5, f6, f7 = st.columns([1.8, 1.2, 1.2, 0.85, 0.85, 0.85, 1.05])
filtro_influ = f1.multiselect("Influenciador", opcoes("handle"))
filtro_situacao = f2.multiselect("Situação", opcoes("situacao"),
                                 help="Em que ponto do fluxo a linha está")
categorias_presentes = [c for c in (CATEGORIAS_VEREDITO + ["Outro texto"])
                        if c in set(df[col_de["validacao"]].map(categoria_do_veredito))]
filtro_veredito = f3.multiselect("Validação", categorias_presentes,
                                 # ENCURTADO EM 17/09/2026.
                                 help="O resultado da análise, agrupado em três "
                                      "categorias.")
filtro_ciclo = f4.multiselect("Ciclo", opcoes("ciclo"))
filtro_marca = f5.multiselect("Marca", opcoes("marca"))
filtro_tipo = f6.multiselect("Tipo", opcoes("tipo"))
# FILTRO DA MARCAÇÃO (01/09/2026), que é a razão de a coluna existir.
#
# A marcação também vira pasta no Drive, mas pasta não se filtra nem se conta. A
# pergunta que a auditoria faz é "quantos posts deste ciclo eram orgânicos", e é
# aqui que ela fica possível.
#
# VIROU LISTA DE ESCOLHA EM 03/09/2026, quando a coluna deixou de ser sim/não.
# Era um rádio de três estados (todos, só orgânicos, sem orgânicos). Lista de
# escolha aguenta a coluna crescer sem virar outro controle, e mostra os valores
# que EXISTEM na planilha, incluindo o "SIM" das linhas de até 02/09.
#
# O TEXTO NÃO AFIRMA REGRA DE CONTRATO. Ele dizia que post orgânico não é entrega
# do escopo e que "sem orgânicos" era a visão de conferência de cota. O auditor
# cortou: às vezes pode estar no contrato, e isso pode mudar. A tela oferece o
# recorte; quem decide o que ele significa é quem tem o contrato.
filtro_marcacao = f7.multiselect("Marcação", opcoes("marcacao"),
                                 # ENCURTADO EM 17/09/2026.
                                 help="ORGANICO: só mostra a marca. LINK: anuncia "
                                      "e leva o endereço da bet.")

# FILTRO DE PAGAMENTO REMOVIDO EM 15/09/2026. Tinha entrado em 04/09 a pedido
# do auditor, mas na prática a coluna PAGAMENTO costuma estar vazia neste
# ponto do fluxo (é preenchida pelo Marketing depois, à mão), e o filtro só
# mostrava "nenhuma opção pra escolher", confuso sem explicação nenhuma ao
# lado. Pagamento continua visível e conferível na tabela, só não filtra mais
# sozinho aqui.

visao = df
for coluna, escolhido in ((col_de["handle"], filtro_influ), (col_de["situacao"], filtro_situacao),
                          (col_de["ciclo"], filtro_ciclo),
                          (col_de["marca"], filtro_marca), (col_de["tipo"], filtro_tipo),
                          (col_de["marcacao"], filtro_marcacao)):
    if escolhido:
        visao = visao[visao[coluna].astype(str).str.strip().isin(escolhido)]

if filtro_veredito:
    visao = visao[visao[col_de["validacao"]].map(categoria_do_veredito).isin(filtro_veredito)]

ver_tudo = st.toggle("Ver todas as colunas", value=False,
                     help="Por padrão mostra só as colunas que a automação preenche.")
if ver_tudo:
    tabela = visao.copy()
else:
    # SÓ AS CHAVES QUE FORAM ACHADAS, e não todo COLUNAS_PRINCIPAIS: "pagamento"
    # entra na lista sem estar em COL_MON, então ela só existe em col_de quando
    # o cabeçalho "PAGAMENTO" foi encontrado de verdade (ver acima). Sem este
    # filtro, uma planilha de teste sem essa coluna derrubaria a tela inteira
    # com "chave não encontrada" em vez de simplesmente mostrar sem ela.
    colunas = ["Linha"] + [col_de[c] for c in COLUNAS_PRINCIPAIS if c in col_de]
    tabela = visao[[c for c in colunas if c in visao.columns]].copy()

# SITUAÇÃO VAZIA VIRA "N/A" NA EXIBIÇÃO (17/09/2026), pedido do auditor,
# mesmo padrão já usado em VALIDACAO/VALIDADO_EM: linha antiga, de antes da
# automação preencher essa coluna, ficava em branco, e branco lê como "ainda
# não sei", diferente de "esta linha nunca teve situação calculada". Só
# muda o que aparece na TELA; a célula na planilha continua como estava.
#
# "SEM ARQUIVO" TAMBÉM VIROU "N/A" (17/09/2026, mesmo dia): primeiro só na
# tela, depois o auditor pediu a célula de verdade também, porque o texto
# "SEM ARQUIVO" lia como defeito (algo que devia ter baixado e não baixou),
# quando é proposital (LIVE e YouTube não são baixados). `fluxo.SEM_ARQUIVO`
# JÁ VALE "N/A" AGORA (ver o comentário da constante em fluxo_downloads.py):
# linha nova nasce direto com "N/A" na célula, sem passar por aqui. Esta
# comparação continua só por causa de linha ANTIGA, de antes da migração
# feita na cópia de teste no mesmo dia, que ainda tenha ficado com o texto
# "SEM ARQUIVO" — rede de segurança, não o caminho normal.
if col_de["situacao"] in tabela.columns:
    _col_sit = col_de["situacao"]
    tabela[_col_sit] = tabela[_col_sit].apply(
        lambda v: "N/A" if not str(v or "").strip()
        or str(v).strip() == "SEM ARQUIVO" else v)

# QUANTOS ESPERAM ANÁLISE, no que está sendo mostrado (01/09/2026).
#
# É o número que decide o trabalho do dia, e antes era preciso contar na tela ou
# filtrar por Situação para saber. Conta em cima da visão FILTRADA de propósito:
# com um influenciador escolhido, o que interessa é quantos dele estão parados,
# e não o total da planilha.
_sem_veredito = int((visao[col_de["validacao"]].map(categoria_do_veredito)
                     == "Sem veredito").sum())
# Quantos dos exibidos estão marcados como orgânicos. Entra como número, e não
# só como filtro, porque é a parcela que muda a leitura de qualquer contagem por
# ciclo, e quem olha a tela precisa ver o tamanho dela sem ter que filtrar.
#
# A CONTA É EM PYTHON, E NÃO COM O .sum() DO pandas (corrigido em 02/09/2026).
#
# Era `int(visao[coluna].map(fluxo.e_sim).sum())`, e derrubava a aba inteira
# sempre que o filtro escolhido não casava com nenhuma linha. O motivo: sem
# nenhuma linha, o .map não tem valor nenhum para saber que o resultado é
# sim/não, então devolve a coluna ainda como texto. Somar coluna de texto junta
# os textos em vez de contar, o resultado é "", e int("") para a tela com
# "invalid literal for int()".
#
# Apareceu ao filtrar por orgânico sem nenhum orgânico na planilha, mas não era
# defeito do filtro de orgânico: qualquer combinação de filtros sem resultado
# fazia o mesmo. Contar em Python não depende do tipo da coluna e responde 0 no
# caso vazio, que é a resposta certa.
#
# Continua contando os ORGÂNICOS, e não as três (03/09/2026): das três marcações,
# é a orgânica que muda a leitura de qualquer contagem por ciclo, porque é a que
# o auditor decidiu que não exige os avisos da portaria. A outra está no filtro,
# e quem quiser o número dela filtra.
_organicos = sum(1 for v in visao[col_de["marcacao"]]
                 if fluxo.marcacao_de_celula(v) == "organico")

with espaco_dos_numeros:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Linhas exibidas", f"{len(tabela)}")
    m2.metric("Total na planilha", f"{len(df)}")
    m3.metric("Influenciadores",
              f"{visao[col_de['handle']].astype(str).str.strip().nunique()}")
    m4.metric("Esperando análise", f"{_sem_veredito}",
              help="Ainda não têm veredito.")
    m5.metric("Orgânicos", f"{_organicos}",
              help="Marcados como orgânicos no download.")

# OS DOIS ENDEREÇOS FICAM CLICÁVEIS (03/09/2026, pedido do auditor olhando a
# tela: "não tem como fazer clicável como na planilha?").
#
# Sem isto a célula mostrava o endereço inteiro em texto, e além de não abrir, ela
# empurrava a tabela para o lado. O nome curto ("abrir") resolve as duas coisas.
#
# A coluna de ARQUIVO é a que serve para conferir a peça, e é por isso que ela
# vem primeiro: LINK é a pasta do post, ARQUIVO é a tela exata que gerou o
# veredito. Ver o comentário de ("arquivo", "AD") em fluxo_downloads.
configuracao = {}
if col_de["arquivo"] in tabela.columns:
    configuracao[col_de["arquivo"]] = st.column_config.LinkColumn(
        ROTULOS["arquivo"], display_text="abrir",
        help="A tela exata que a análise conferiu.")
if col_de["link"] in tabela.columns:
    configuracao[col_de["link"]] = st.column_config.LinkColumn(
        ROTULOS["link"], display_text="abrir",
        help="A pasta com as telas daquele post.")
if col_de["evidencia"] in tabela.columns:
    # A evidência é texto longo. Na tabela ela fica cortada de qualquer jeito,
    # então aqui vale como sinal de que existe; a leitura inteira é no painel
    # de detalhe abaixo.
    configuracao[col_de["evidencia"]] = st.column_config.TextColumn("Evidência", width="medium")

# Cor carrega informação aqui, não é enfeite: o que está esperando análise
# precisa saltar da tela sem ninguém ler linha por linha. Cores do design
# system do EGB (âmbar de atenção, verde de conforme, vermelho de não
# conforme). O resto fica quieto de propósito, senão nada se destaca.
FUNDO_ESPERANDO = "background-color: #FEF3C7"     # âmbar claro
COR_CONFORME = "color: #059669; font-weight: 600"
COR_NAO_CONFORME = "color: #DC2626; font-weight: 600"
COR_ATENCAO = "color: #D97706; font-weight: 600"

col_situacao = col_de["situacao"]
col_validacao = col_de["validacao"]


def _pintar_linha(linha):
    """Devolve o estilo de cada célula da linha."""
    esperando = str(linha.get(col_situacao, "")).strip() == fluxo.AGUARDANDO_VALIDACAO
    estilos = [FUNDO_ESPERANDO if esperando else "" for _ in linha.index]
    if col_validacao in linha.index:
        veredito = str(linha[col_validacao] or "").upper()
        if veredito.startswith("CONFORME"):
            cor = COR_CONFORME
        elif veredito.startswith("NÃO CONFORME") or veredito.startswith("NAO CONFORME"):
            cor = COR_NAO_CONFORME
        elif veredito:
            cor = COR_ATENCAO
        else:
            cor = ""
        if cor:
            i = list(linha.index).index(col_validacao)
            estilos[i] = (estilos[i] + "; " + cor).strip("; ")
    return estilos


legenda = (
    f'<span style="{FUNDO_ESPERANDO}; padding:2px 8px; border-radius:4px">'
    f'{fluxo.AGUARDANDO_VALIDACAO.lower()}</span> &nbsp;·&nbsp; '
    f'<span style="{COR_CONFORME}">conforme</span> &nbsp;·&nbsp; '
    f'<span style="{COR_NAO_CONFORME}">não conforme</span> &nbsp;·&nbsp; '
    f'<span style="{COR_ATENCAO}">requer verificação</span>'
)
st.markdown(legenda, unsafe_allow_html=True)

# FILTRO QUE NÃO CASA COM NADA PRECISA DIZER ISSO (02/09/2026).
#
# Até hoje esse caso derrubava a aba (ver a contagem de orgânicos). Com o erro
# corrigido, o que sobrava era uma tabela vazia sem explicação, que lê como
# planilha vazia ou como programa travado. A tabela continua desenhada abaixo,
# com o cabeçalho, para a tela não mudar de forma.
if visao.empty and len(df):
    st.info("Nenhuma linha com esses filtros. Tire algum filtro para ver o resto.")

# Pintar linha a linha custa caro em tabela grande, então acima de 1500 linhas
# a cor é dispensada em vez de deixar a tela lenta. O filtro de Situação
# continua servindo pra achar o que espera análise.
if len(tabela) <= 1500 and col_situacao in tabela.columns:
    st.dataframe(tabela.style.apply(_pintar_linha, axis=1),
                 use_container_width=True, hide_index=True,
                 column_config=configuracao or None)
else:
    if len(tabela) > 1500:
        st.caption("Muitas linhas para colorir sem deixar a tela lenta. "
                   "Use o filtro de Situação para reduzir.")
    st.dataframe(tabela, use_container_width=True, hide_index=True,
                 column_config=configuracao or None)

# --- Acompanhar a análise ---------------------------------------------------
#
# MIGROU DA TELA DE VALIDAÇÃO REGULATÓRIA (14/09/2026), que saiu do menu. O
# motor de análise roda sozinho, fora do Streamlit (trabalhador.py +
# pipeline_influenciadores.py), e o download já encadeia análise automática.
#
# "TIRAR DA ANÁLISE / DEVOLVER / TENTAR DE NOVO" SAIU EM 15/09/2026, pedido do
# auditor: vídeo analisado por engano não é problema, ele fica lá com
# veredito, e quem quiser o vídeo certo usa o "Baixar de novo" de Downloads
# (que já pede motivo quando a linha reaberta tinha sucesso). O delicado
# nunca foi a análise em si, foi o download em duplicidade, e isso já tem
# tratamento próprio. Falha de análise por erro técnico continua recuperável
# por quem administra, com `reprocessar_linhas.py`.
st.divider()
# ZONA EM CIANO (15/09/2026): acompanhamento da análise, separado da tabela
# de consulta acima e da correção de ciclo (âmbar) logo abaixo.
with st.container(key="mon_zona_andamento"):
    _rodando_analise = fila_trabalho.listar(fila_trabalho.RODANDO, fila_trabalho.VALIDAR)
    _esperando_analise = fila_trabalho.listar(fila_trabalho.PENDENTE, fila_trabalho.VALIDAR)
    _concluidas_analise = sorted(
        fila_trabalho.listar(fila_trabalho.CONCLUIDA, fila_trabalho.VALIDAR),
        key=lambda t: t.get("terminou_em") or "", reverse=True)[:10]
    ca1, ca2 = st.columns(2)
    ca1.metric("Sendo analisados agora", len(_rodando_analise))
    ca2.metric("Esperando na fila de análise", len(_esperando_analise))
    if _concluidas_analise:
        st.success(f"{len(_concluidas_analise)} vídeo(s) analisado(s) recentemente. "
                   f"O veredito já está na tabela acima.")

# --- Corrigir o ciclo de uma linha ------------------------------------------
#
# POR QUE ISTO ESTÁ NUMA TELA QUE SE ANUNCIA COMO SÓ LEITURA (01/09/2026).
#
# Levantado pelo auditor: alguém quer mudar o ciclo de um post já baixado. O
# único caminho era reabrir a linha e baixar de novo, o que gastava chamada ao
# Instagram, duplicava a linha e fazia o programa marcar o arquivo como peça
# REAPROVEITADA, que é acusação de descumprimento de contrato por causa de uma
# operação de rotina.
#
# O ciclo é campo de planilha e não tem relação com o arquivo no Drive, então
# corrigir aqui é o caminho certo. Fica dentro de um expansor fechado, e o texto
# do topo da tela continua verdadeiro para tudo o mais: esta é a única coisa que
# altera a planilha, e ela deixa rastro.
st.divider()
# ZONA EM ÂMBAR (15/09/2026): é a única escrita desta tela, separada
# visualmente do acompanhamento (ciano) logo acima e da tabela de consulta,
# que fica sem zona de propósito (é o conteúdo central da tela).
with st.container(key="mon_zona_correcao"):
    with st.expander("Corrigir o ciclo de uma linha"):
        st.caption(
            "Serve para quando a data do post cai num ciclo diferente, o que acontece "
            "porque os ciclos se sobrepõem. **Não** é preciso baixar o vídeo de novo: o "
            "ciclo é informação da planilha. A troca fica registrada com quem fez, "
            "quando, e de qual valor para qual."
        )
        linhas_para_corrigir = list(visao["Linha"])
        if not linhas_para_corrigir:
            st.caption("Nenhuma linha no que está filtrado acima.")
        else:
            cc1, cc2, cc3 = st.columns([3, 1, 1])
    
            def _rotulo_ciclo(numero):
                achada = visao[visao["Linha"] == numero].iloc[0]
                atual = str(achada[col_de["ciclo"]] or "").strip() or "sem ciclo"
                return (f"Linha {numero} · {achada[col_de['handle']]} · "
                        f"{achada[col_de['data_post']]} · hoje: {atual}")
    
            linha_alvo = cc1.selectbox("Linha", options=linhas_para_corrigir,
                                       format_func=_rotulo_ciclo, key="linha_corrigir_ciclo")
            ciclo_alvo = cc2.text_input("Ciclo novo", placeholder="ex: 9",
                                        key="ciclo_novo_correcao")
            if cc3.button("Corrigir", disabled=not ciclo_alvo.strip(),
                          use_container_width=True):
                try:
                    resultado = fluxo.corrigir_ciclo_na_monitoramento(
                        linha_alvo, ciclo_alvo, quem=identidade.quem_sou_eu())
                except Exception as e:
                    st.error(f"Não consegui corrigir: {type(e).__name__}: {str(e)[:200]}")
                else:
                    if resultado is None:
                        st.info("Nada mudou: esse já é o ciclo da linha, ou o valor não "
                                "é um ciclo válido.")
                    else:
                        antigo, novo = resultado
                        st.success(f"Linha {linha_alvo}: ciclo trocado de "
                                   f"\"{antigo or '(vazio)'}\" para \"{novo}\". A troca "
                                   f"ficou registrada. Use **Atualizar agora**, no topo, "
                                   f"para a tabela refletir.")
                        carregar.clear()


# --- A EDIÇÃO DE PAGAMENTO SAIU DAQUI (04/09/2026) --------------------------
#
# Ela existiu nesta tela por um tempo, e foi um erro de lugar. Esta página se
# anuncia como SÓ LEITURA, e abrir uma exceção de escrita aqui obrigou a
# enfraquecer justamente a regra que ela declara. O auditor cortou o nó: "essa
# parte tem que sair de monitoramento tbm".
#
# CRONOGRAMA e PAGAMENTO ficam no FINANCEIRO, na tabela dos posts do ciclo, que
# é o único lugar do programa que grava na Monitoramento por escolha humana. São
# as duas únicas colunas que uma pessoa muda depois de a linha existir, então
# ter as duas no mesmo lugar é o que faz a regra desta tela voltar a ser
# verdadeira.
#
# ELAS TIVERAM TELA PRÓPRIA POR UM DIA (04/09/2026) e foram absorvidas pelo
# Financeiro em 05/09/2026, quando o auditor perguntou se não dava para juntar
# as duas sem ficar confuso. Dava: é o mesmo influenciador e o mesmo ciclo, e o
# Financeiro já mostrava a contagem de pagamento sem poder mexer nela.
#
# A CORREÇÃO DE CICLO, ACIMA, CONTINUA AQUI de propósito: ela é correção de um
# erro de leitura da automação, feita olhando a validação da própria linha, e
# não preenchimento de rotina. Quem corrige ciclo está no meio de conferir o
# que a automação leu, e é aqui que se confere isso.

# A seção "Detalhe da validação" (Veredito, "o que a análise leu e ouviu") e o
# botão "Abrir a planilha no Google Sheets" saíram em 14/09/2026, pedido do
# auditor para expor menos a planilha crua. Quem quiser conferir arquivo ou
# pasta de uma peça específica já consegue pela tabela acima, que tem as
# colunas Arquivo e Link clicáveis.
