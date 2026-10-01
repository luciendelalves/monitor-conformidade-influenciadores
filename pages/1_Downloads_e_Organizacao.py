# -*- coding: utf-8 -*-
"""
Página "Downloads e Organização" do app de validação (Streamlit multipágina).
Camada visual do fluxo de download/organização de vídeos — a lógica de
verdade mora em fluxo_downloads.py (mesmo código usado pela linha de comando).

ONDE O MATERIAL FICA, E ONDE O CICLO FICA (corrigido em 31/08/2026)

São dois lugares diferentes, e o texto daqui dizia que eram o mesmo:

    no Drive       bet / ano / mês / @influenciador
    na planilha    o ciclo, na coluna CICLO da Monitoramento

O ciclo NÃO é pasta. O Drive do Marketing é organizado por mês, e o ciclo só
existe na planilha deles. Antes este arquivo dizia "organizada por
influenciador e ciclo", o que faria alguém procurar uma pasta que não existe.

A pasta de ciclo continua existindo no layout de TESTE, porque ali a árvore é
nossa e é conveniente. É só isso.

TERCEIRO LAYOUT, FUTEBOL (12/09/2026): árvore própria, sem bet, sem ano, sem
pasta de tipo nem de marcação (`pasta do influenciador / DIVULGAÇÕES / mês`).
Os textos de ajuda sobre marca e marcação (`fluxo.ajuda_campo_marca`,
`fluxo.ajuda_campo_marcacao`, `fluxo.texto_destino_da_marcacao`) mudam de
frase sozinhos conforme o layout ativo, porque testando esse layout a
explicação fixa ("decide a pasta no Drive do Marketing") ficou errada sem
ninguém perceber. Ver LAYOUT_FUTEBOL em fluxo_downloads.py.
"""
import os
import sys

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import acesso
import baixadores
import estilo
import fila_trabalho
import fluxo_downloads as fluxo
import identidade
import painel_trabalhador

# QUEM PODE ABRIR, conferido AQUI também, e não só em painel.py (31/08/2026).
#
# Esta página é uma rota própria do Streamlit, por estar na pasta pages/. Em
# certas situações ela é executada sem que o painel.py rode antes, e nesse
# caminho a conferência de painel.py não acontece. Sem esta linha, a página
# ficaria alcançável por quem não passou pelo login. O porquê completo está em
# acesso.py, na seção da barreira como página.
acesso.exigir_login()


# REMOVIDO EM 14/09/2026 os atalhos "Abrir a Monitoramento"/"Abrir a pasta":
# pedido do auditor para expor menos a planilha crua na tela. A função
# `atalhos()` que existia aqui não tem mais nenhuma chamada no arquivo, e
# saiu junto (histórico dela no Git, commit anterior a esta data).

# A configuração da página fica em painel.py (só pode ser chamada uma vez).
estilo.cabecalho(
    "Downloads",
    # ENCURTADA DE NOVO EM 17/09/2026, a pedido do auditor: "não precisa
    # explicar sobre coluna ou sobre nada da auditoria" nos cabeçalhos das
    # telas. A ressalva sobre teste x modo real saiu daqui; continua
    # completa em `verificar_ambiente.py` e no INSTALAR.md, que é onde
    # importa checar antes de usar.
    "Baixa a peça, guarda no Drive e cria a linha na Monitoramento.",
)

# ------------------------------------------------------------------
# Painel
# ------------------------------------------------------------------
# SÓ ESTÁGIO "A" (24/09/2026), que é a fila de download por link, a única
# coisa que ESTA tela produz hoje. Antes filtrava só por status=="OK", sem
# olhar o estágio, e por isso contava também o que a tela de Uploads gera
# (estágio ENVIO) desde que ela se separou em 23/09. "Nomes não
# reconhecidos" saiu de aqui pelo mesmo motivo: quem gera esse status hoje é
# o envio de arquivo (nome de arquivo fora do padrão), não o link colado
# aqui. Foi para pages/5_Uploads.py.
log = fluxo.ler_log()
organizados = [l for l in log if l["status"] == "OK" and l.get("estagio") == "A"]

pode_instagram, motivo_conta, usados_hoje, restantes_hoje = fluxo.situacao_da_conta()

col1, col3, col4 = st.columns(3)
col1.metric("Vídeos organizados (acumulado)", len(organizados))
col3.metric("Ciclo a confirmar", sum(1 for l in organizados if "A CONFIRMAR" in (l["ciclo"] or "")))
col4.metric(f"Story hoje (conta @{fluxo.USUARIO_DOS_COOKIES}) · teto recomendado",
            f"{usados_hoje} de {fluxo.limite_diario_vigente()}",
            delta=f"{restantes_hoje} até o recomendado" if restantes_hoje else "acima do recomendado",
            # "off" NO LUGAR DE "inverse" (17/09/2026): o número deixou de
            # travar (ver situacao_da_conta), então passar dele não é mais
            # um estado de erro, é só informação. Vermelho aqui mentiria
            # sobre a gravidade.
            delta_color="normal" if restantes_hoje else "off")

if not pode_instagram:
    st.warning(
        f"**Download de Story está pausado.** {motivo_conta}\n\n"
        "Reels, posts de feed, YouTube e TikTok continuam funcionando normalmente, porque não "
        "usam conta nenhuma. Para Story, baixe no navegador e envie pela tela de Uploads."
    )
elif motivo_conta:
    # SÓ INFORMATIVO (17/09/2026): quando passa do teto recomendado, o
    # download continua funcionando (`pode_instagram` já é True nesse
    # caso), então isso não é mais aviso de bloqueio, é nota.
    estilo.nota(motivo_conta)

# ESTADO DAS PEÇAS DE DOWNLOAD, NUMA FAIXA SÓ (05/09/2026).
#
# Isto já foi três avisos separados: idade da biblioteca, suspeita de quebra e
# saúde dos últimos dias, cada um na sua caixa. O auditor cortou: "vc coloca
# muito aviso e fica poluindo a tela", e depois "não dá pra colocar tudo em uma
# faixa única não?". Estava certo nas duas vezes.
#
# A REGRA QUE PASSOU A VALER AQUI: uma faixa só, e a cor diz a gravidade.
# Vermelho quando o download pode ter parado (fato). Uma linha de texto simples
# quando é só versão envelhecendo (risco). O detalhe e o botão ficam no
# expansor, porque instrução só interessa a quem decidiu agir.
# Dois espacos e quebra de linha: e assim que o markdown do
# Streamlit quebra linha dentro da MESMA caixa, em vez de criar
# paragrafo novo com espaco em branco entre eles.
SEPARADOR = "  " + chr(10)
_saude = baixadores.saude_do_download(7)
baixadores.registrar_versoes_vistas()
_baixadores_velhos = baixadores.precisa_de_atencao()

if _saude["suspeita_de_quebra"] or _baixadores_velhos:
    _partes = []
    if _saude["suspeita_de_quebra"]:
        _partes.append("**O download pode ter parado de funcionar.** "
                       "Use a tela de Uploads enquanto isso.")
    if _baixadores_velhos:
        # AS DUAS IDADES DIZEM COISAS DIFERENTES, e por isso a frase muda.
        # `dias` vem da data embutida na versão (o yt-dlp versiona por data),
        # então é "quando essa versão saiu". `dias_parada` é quando o programa
        # viu essa versão pela primeira vez nesta máquina, então é "há quanto
        # tempo ninguém atualiza". Usar a mesma frase para as duas dizia algo
        # errado numa delas: "yt-dlp 2026.07.04 (de 64 dias)" não significa
        # nada em português.
        def _idade(b):
            if not b["presente"]:
                return f"{b['nome']}: não instalado"
            if b["dias"] is not None:
                return f"{b['nome']} {b['versao']}, lançada há {b['dias']} dias"
            if b["dias_parada"] is not None:
                return (f"{b['nome']} {b['versao']}, sem atualizar há "
                        f"{b['dias_parada']} dias")
            return f"{b['nome']} {b['versao']}"

        _partes.append("Vale atualizar: "
                       + ", ".join(_idade(b) for b in _baixadores_velhos) + ".")

    if _saude["suspeita_de_quebra"]:
        st.error(SEPARADOR.join(_partes))
    else:
        estilo.nota(SEPARADOR.join(_partes), "atencao")

    with st.expander("Cuidar das bibliotecas de download"):
        _de_pe, _ = fila_trabalho.trabalhador_de_pe()
        _nomes_velhos = [b["nome"] for b in _baixadores_velhos if b["presente"]]

        # A CONTAGEM POR CLASSE é o que distingue "biblioteca quebrada" de
        # "Instagram bloqueando" ou "perfis sem story": três causas com ações
        # completamente diferentes.
        st.caption(f"**Últimos 7 dias:** {_saude['motivo']}")
        if _saude["por_classe"]:
            _rotulos = {c: r for c, r, _ in baixadores.CLASSES_DE_RESULTADO}
            st.caption("  ·  ".join(
                f"**{n}** {_rotulos.get(c, c)}"
                for c, n in sorted(_saude["por_classe"].items(),
                                   key=lambda kv: -kv[1])))
        st.divider()

        if _de_pe:
            # BOTÃO AQUI, NÃO SÓ AVISO (17/09/2026): o "Atualizar agora" já
            # fica travado enquanto o processo está de pé (`disabled=_de_pe`
            # duas linhas abaixo); faltava dar o botão que resolve isso no
            # mesmo lugar, em vez de mandar a pessoa procurar lá embaixo, em
            # "Manutenção". Pedido do auditor: "deve ser uma condição para
            # atualizar" — já era; o que faltava era a ação estar aqui perto.
            painel_trabalhador.botao_encerrar(key_sufixo="_atualizar")
        if st.button("Atualizar agora", icon=":material/update:",
                     disabled=_de_pe or not _nomes_velhos,
                     key="atualizar_baixadores"):
            with st.spinner("Atualizando... isso leva um minuto."):
                _r = baixadores.atualizar(_nomes_velhos)
            if _r["mudou"]:
                st.success("Atualizado: " + ", ".join(
                    f"**{n}**: {_r['antes'][n]} → {_r['depois'][n]}"
                    for n in _r["mudou"]))
                for _n in _r["mudou"]:
                    _ok, _detalhe = baixadores.anotar_no_requirements(
                        _n, _r["depois"][_n])
                    if not _ok:
                        st.warning(f"Atualizei {_n}, mas não anotei no "
                                   f"requirements.txt: {_detalhe}")
                st.caption("**Reinicie as duas janelas** e baixe um Reel "
                           "para confirmar. Se der problema, volte com:")
                st.code(chr(10).join(
                    baixadores.comando_de_volta(_n, _r["antes"][_n])
                    for _n in _r["mudou"]), language=None)
            elif _r["ok"]:
                st.caption("Nenhuma versão mudou: já estava na mais nova.")
            else:
                st.error("A atualização falhou. Nada foi alterado.")
                st.code(_r["saida"] or "(sem saída)", language=None)

        st.caption("Prefere pelo terminal? " + baixadores.comando_de_atualizacao(
            [b["nome"] for b in _baixadores_velhos] or None))
        st.caption(baixadores.SAIDA_MANUAL)

painel_trabalhador.mostrar_situacao()

st.divider()

# ------------------------------------------------------------------
# Fila (estágio A)
# ------------------------------------------------------------------
# ZONA EM CIANO (15/09/2026): o formulário principal, o caminho normal desta
# tela. Mesma técnica das zonas do Financeiro, container com `key=` (ver
# estilo.py).
with st.container(key="dl_zona_principal"):
    # TEXTO ENXUGADO EM 16/09/2026: eram quatro linhas descrevendo o que os
    # próprios campos já dizem ("cole o link, escolha a marca e clique em
    # Baixar"). O que a pessoa não adivinha olhando a tela virou help, e o
    # aviso de YouTube/TikTok já aparece sozinho, em vermelho, quando alguém
    # cola um link desses (ver o st.warning mais abaixo).
    st.subheader(
        "Link do Instagram para baixar e analisar",
        # ENCURTADO EM 17/09/2026, pedido do auditor de resumir todo help=.
        help="Baixa, guarda no Drive, cria a linha na Monitoramento e manda "
             "pra análise. O @ e o ciclo são descobertos sozinhos.")
    
    # A CHAVE FICA AQUI, ANTES DO BOTÃO (01/09/2026).
    #
    # Ela estava embaixo, ao lado de um segundo botão que era o que realmente
    # mandava baixar. Com "Baixar" fazendo tudo num clique, a decisão precisa estar
    # visível ANTES dele, senão a pessoa clica sem ter visto a escolha.
    #
    # Fora do formulário de propósito: dentro dele, o valor só valeria depois do
    # envio, e o outro botão desta tela também lê esta mesma chave.
    #
    # SEMPRE LIGADA, SEM ESCOLHA (14/09/2026, endurecendo o que já valia desde
    # 31/08). Existia uma caixa "Analisar assim que baixar", desmarcável, e ela
    # era exatamente o furo que o parágrafo acima diz que não devia existir:
    # desmarcar deixava o vídeo baixado sem análise, sem motivo e sem deixar
    # rastro nenhum, o mesmo problema que "tirar da análise" resolve exigindo os dois.
    # Com a tela de escolher o que analisar saindo de circulação (a análise já
    # encadeia sozinha), manter essa caixa criaria vídeo baixado que nunca mais
    # seria analisado por ninguém, sem nenhum aviso. Analisar tudo o que entra,
    # sempre, com "tirar da análise" (dentro do Monitoramento) como único caminho
    # de exceção, motivo obrigatório.
    #
    # A VARIÁVEL QUE ESTAVA AQUI (`analisar_junto = True`) NUNCA ERA LIDA
    # (15/09/2026, achado ao investigar um "baixar de novo" que baixou mas não
    # analisou). O código do botão "Baixar" abaixo já grava True direto. Quem
    # lia era o "baixar de novo" em lote, lá embaixo, mas lendo
    # `st.session_state.get("analisar_junto")` — uma CHAVE DE SESSÃO, não esta
    # variável local, e não existe mais nenhum widget com essa key desde que a
    # caixa foi removida. Session state sem dono sempre devolve None, e
    # `bool(None)` é False: todo "baixar de novo" em lote saía sem analisar,
    # em silêncio, contradizendo esta mesma política. Corrigido lá embaixo.

    # AS TRÊS MARCAÇÕES, com o rótulo que aparece na tela (03/09/2026).
    #
    # A ordem importa: a primeira é a que vem escolhida, e é publi. Isso preserva o
    # comportamento antigo, em que quem não marcava nada caía direto no tipo, e o
    # tipo direto virou publi.
    #
    # MUDOU PARA fluxo_downloads.py EM 23/09/2026: "Enviar arquivo do post"
    # se mudou para a página de Uploads, e as duas telas (esta e a de lá)
    # precisam continuar usando a MESMA lista, senão uma acaba oferecendo
    # opção que a outra não tem.
    ROTULO_DA_MARCACAO = fluxo.ROTULO_DA_MARCACAO
    
    with st.form("adicionar_fila", clear_on_submit=True):
        # SÓ DOIS CAMPOS, DE PROPÓSITO (31/08/2026).
        #
        # Decisão do auditor, e o motivo não é conforto: quanto menos a pessoa
        # escolhe, menos a escolha dela influi no resultado da auditoria. Escolher
        # o @ à mão, por exemplo, permitia mandar o vídeo para a pasta de outro
        # influenciador sem que nada registrasse a troca.
        #
        # O campo do @ SAIU. Ele já era desnecessário no Instagram desde 30/08,
        # porque o programa descobre pelo endereço ou pelos dados do vídeo. Ficava
        # só para YouTube e TikTok, e o auditor confirmou que esses não são
        # baixados: para live de YouTube basta o link, que vai pela seção de
        # registro. Então esta seção é do Instagram, e ponto.
        #
        # A marca é o único campo que sobra porque não existe em lugar nenhum do
        # link nem do vídeo: é informação de contrato, e só uma pessoa sabe.
        # O CICLO GANHOU CAMPO AQUI EM 01/09/2026, a pedido do auditor.
        #
        # Ele existia só mais abaixo, na área das linhas pendentes, longe de onde o
        # link é colado. E definir ciclo não é exceção rara: os ciclos da
        # Monitoramento se sobrepõem, então o auditor precisa disso com frequência.
        #
        # É OPCIONAL, e isso preserva o princípio que tirou o campo do @ desta seção
        # em 31/08: quanto menos a pessoa escolhe, menos a escolha dela influi no
        # resultado da auditoria. Em branco, o ciclo sai da data do vídeo, que é o
        # padrão e continua sendo o caminho normal.
        #
        # E quando é digitado, isso FICA REGISTRADO (ver origem_ciclo em CAMPOS_LOG,
        # no fluxo_downloads): ciclo escolhido por alguém é discricionariedade, e a
        # ferramenta existe para deixar discricionariedade rastreável.
        # O QUE A PEÇA É: ESCOLHA DE TRÊS, ACIMA DOS CAMPOS (03/09/2026).
        #
        # Era uma caixa de marcar "Este post é orgânico". O auditor pediu a terceira
        # opção e explicou o que separa as três:
        #
        #   "a tela de orgânico é quando o usuário mostra só alguma coisa da marca,
        #   uma garrafa com a logo da lottu ou da EDS, ou Ona, e link é quando ele
        #   anuncia os jogos e coloca os avisos da portaria e tudo mais, porém ele
        #   coloca tbm o link que redireciona pra bet"
        #
        # ESCOLHA ÚNICA, E NÃO DUAS CAIXAS, porque pelas definições dele as três são
        # excludentes: orgânico não anuncia, publi e link anunciam, e link é publi
        # com redirecionamento. Uma peça não pode ser duas.
        #
        # Acima e não abaixo pelo mesmo motivo que tirou a chave de análise de baixo
        # do botão: decisão que muda o destino do arquivo tem que estar visível antes
        # de a pessoa clicar em Baixar.
        #
        # DENTRO DO FORMULÁRIO, e isso é proteção e não estilo. Fora dele a escolha
        # ficaria guardada entre um envio e outro, então quem marcasse orgânico num
        # link mandaria os dez seguintes para orgânico sem ver. Com clear_on_submit,
        # ela volta ao padrão a cada link.
        #
        # O PADRÃO É PUBLI, e isso preserva o comportamento antigo: quem não marcava
        # nada caía no tipo direto, e o tipo direto virou publi.
        #
        # O TEXTO NÃO AFIRMA O QUE O CONTRATO DIZ (01/09/2026). Ele dizia que post
        # orgânico "não é entrega do escopo do contrato" e que a marcação "permite não
        # contar como cumprimento de cota". O auditor cortou: às vezes pode estar no
        # contrato, e isso pode mudar. Regra de contrato não é a tela que decide, e
        # texto de ajuda que afirma regra fica errado sem ninguém perceber.
        marcacao_nova = st.radio(
            "O que é esta peça?",
            options=list(ROTULO_DA_MARCACAO),
            format_func=lambda chave: ROTULO_DA_MARCACAO[chave],
            horizontal=True,
            help=fluxo.ajuda_campo_marcacao())
        c1, c2, c3, c4 = st.columns([4.4, 2, 1.2, 1.4])
        link_novo = c1.text_input("Link do Instagram",
                                  placeholder="https://www.instagram.com/...")
        # O JOGO É DIGITADO, E NÃO RECONHECIDO (11/09/2026). O Calendário de
        # Divulgações do Marketing tem coluna Jogo, e reconhecer qual jogo aparece
        # no vídeo seria capacidade nova de visão, com chance real de errar. O
        # auditor decidiu que vira campo aqui, no mesmo clique do link.
        # SÓ CAIXA ALTA (15/09/2026), pedido do auditor: a coluna Jogo do
        # Calendário deles só tem valor em maiúscula (conferido na planilha
        # real). O `text-transform` é só aparência, força na hora de digitar;
        # quem cola texto minúsculo ou vem de outro caminho é normalizado de
        # verdade logo abaixo e de novo dentro do módulo que grava a fila,
        # porque aparência não é validação.
        with c1.container(key="dl_campo_jogo"):
            jogo_novo = st.text_input(
                "Jogo",
                placeholder="ex: CHUTE PREMIADO + AVIATOR",
                # ENCURTADO EM 17/09/2026, pedido do auditor de resumir todo help=.
                help="O que a peça divulga. Em branco, alguém preenche à mão.")
        jogo_novo = jogo_novo.strip().upper()
        marca_nova = c2.selectbox("Marca *", options=[""] + fluxo.MARCAS,
                                  format_func=lambda m: "escolher..." if not m else fluxo.ROTULO_MARCA[m],
                                  help=fluxo.ajuda_campo_marca())
        ciclo_novo = c3.text_input("Ciclo", placeholder=fluxo.PLACEHOLDER_CAMPO_CICLO,
                                   help=fluxo.ajuda_campo_ciclo())
        # UM CLIQUE SÓ, E O BOTÃO DIZ O QUE FAZ (01/09/2026).
        #
        # Era "Adicionar", e depois era preciso clicar num segundo botão, "Baixar e
        # analisar agora", que ficava mais abaixo na tela. Pedido do auditor: "o
        # usuário coloca o link e clica em BAIXAR".
        #
        # A fila NÃO deixou de existir, e isso é importante para quem vier depois: é
        # ela que faz o download acontecer no trabalhador em vez de dentro da aba do
        # navegador, o que resolveu em 29/08 os processos órfãos e o lote morrendo
        # quando alguém fechava a aba. O que saiu foi a fila como CONCEITO na tela.
        enviar = c4.form_submit_button("Baixar", icon=":material/download:",
                                       type="primary")
        if enviar and link_novo:
            handle_do_proprio_link = fluxo.handle_do_link(link_novo)
            e_instagram = "instagram.com" in (link_novo or "").lower()
            # Uma vez, e não a cada ramo: ela lê um arquivo em disco, e chamar três
            # vezes o mesmo teste é o tipo de coisa que depois discorda de si mesma.
            link_serve, aviso_do_link = fluxo.conferir_link_antes_da_fila(link_novo)
            if not marca_nova:
                # A MARCA É OBRIGATÓRIA DESDE 30/08/2026.
                #
                # Ela é a pasta de cima no Drive do Marketing. Em branco, o
                # programa antes montava "00. SEM BET DEFINIDA", e a conferência
                # contra o Drive real mostrou que essa pasta não existe lá: seria
                # criada na raiz deles, que é exatamente o que a regra de não criar
                # pasta existe para evitar.
                st.warning(fluxo.aviso_marca_vazia())
            elif not e_instagram:
                # Barrar aqui, e não deixar falhar no download: sem o campo do @,
                # link de fora do Instagram não tem de onde tirar o influenciador,
                # e a falha apareceria minutos depois, na fila, sem explicar nada.
                st.warning(
                    "Esta seção é só para links do Instagram. YouTube e TikTok não são "
                    "baixados: para live e vídeo do YouTube, use **Link só para registrar**, "
                    "logo abaixo, que grava o endereço na Monitoramento sem baixar."
                )
            # ENDEREÇO DE STORY SEM O NÚMERO DA PEÇA (01/09/2026).
            #
            # Era pendência desde 31/08 e o auditor cobrou hoje: "como ficou a
            # questão de ter que passar de storie e voltar para aparecer um link
            # válido?".
            #
            # O endereço só ganha o número quando a pessoa navega entre os stories do
            # perfil. Sem o número e sem conhecer o perfil, o programa precisaria
            # perguntar ao Instagram o número interno dele, que é a consulta mais
            # arriscada que ele faz: em 31/08 respondeu 429 e a chamada foi gasta sem
            # baixar nada.
            #
            # A conferência custa ZERO chamada, porque é texto do endereço mais o
            # arquivo de perfis já conhecidos. Por isso ela cabe aqui, no clique, e
            # não depois. Ver conferir_link_antes_da_fila para os dois casos.
            elif not link_serve:
                st.warning(aviso_do_link)
            else:
                # QUEM PEDIU VIAJA NA LINHA DA FILA (02/09/2026), e não na tarefa do
                # trabalhador. Uma tarefa processa TODOS os links pendentes, que
                # podem ter sido colados por pessoas diferentes, então quem pediu é
                # informação de linha. Daqui ela vai para a coluna PEDIDO_POR da
                # Monitoramento e para o campo `quem` do log.
                add, dup = fluxo.adicionar_na_fila(
                    [("", link_novo, ciclo_novo, marca_nova, marcacao_nova,
                      identidade.quem_sou_eu(), jogo_novo)])
                if add and aviso_do_link:
                    # Segue, mas avisa: é o caso do perfil conhecido sem o número na
                    # URL, que funciona com um story só e para com vários.
                    st.info(aviso_do_link)
                if add:
                    # MANDA BAIXAR NO MESMO CLIQUE (01/09/2026).
                    #
                    # Só cria tarefa se ainda não há uma esperando. Cada tarefa de
                    # download processa TODOS os links pendentes, não só o que
                    # acabou de entrar, então uma segunda tarefa não teria trabalho
                    # e as pausas entre links continuam valendo dentro da rodada.
                    #
                    # Isso não é economia de tarefa, é o que impede a rajada: se
                    # cada clique gerasse uma tarefa própria de um link, as pausas
                    # deixariam de existir entre eles, porque elas acontecem dentro
                    # de uma rodada e não entre tarefas.
                    ja_tem_trabalho = fila_trabalho.ha_trabalho(fila_trabalho.BAIXAR_FILA)
                    if not ja_tem_trabalho:
                        fila_trabalho.criar(
                            fila_trabalho.BAIXAR_FILA,
                            {"analisar_depois": True},
                            rotulo="baixar o que está na fila · analisa em seguida",
                            criada_por=identidade.quem_sou_eu())
    
                    partes = ["**Baixando.**"]
                    if handle_do_proprio_link:
                        partes.append(f"O @ foi lido do próprio link: @{handle_do_proprio_link}.")
                    else:
                        partes.append("O @ vai sair dos dados do vídeo.")
                    # Dizer o que vai acontecer com o ciclo, nos dois casos: em
                    # branco lê como "esqueci de preencher" se a tela não avisar que
                    # é o caminho normal.
                    ciclo_lido = fluxo.normalizar_ciclo(ciclo_novo)
                    if ciclo_lido:
                        partes.append(f"O {ciclo_lido} foi informado à mão, e fica registrado "
                                      f"assim em vez de sair da data do vídeo.")
                    else:
                        partes.append("O ciclo sai da data do vídeo.")
                    # Dizer o que a marcação fez, e onde ela vai aparecer: sem isso,
                    # quem escolheu não tem como conferir se pegou. Diz SEMPRE qual
                    # foi, e não só quando é orgânico: com três opções e uma delas
                    # como padrão, o silêncio não distingue escolha de esquecimento.
                    partes.append(fluxo.texto_destino_da_marcacao(marcacao_nova))
                    partes.append("Vai para a análise assim que terminar.")
                    if ja_tem_trabalho:
                        partes.append("Entra na rodada que já está em andamento, com a pausa "
                                      "de propósito entre links do Instagram.")
                    partes.append("O trabalho continua mesmo se você fechar a aba.")
                    st.success(" ".join(partes))
                else:
                    # O LINK JÁ ESTAVA NA FILA, E A TELA PRECISA DIZER QUAL LINHA
                    # (02/09/2026).
                    #
                    # Pergunta do auditor, olhando a tela: "só estou conseguindo
                    # baixar depois de limpar a fila, pq?".
                    #
                    # A fila não aceita o mesmo endereço duas vezes, e essa recusa é
                    # proposital: ela existe para não gastar duas chamadas ao
                    # Instagram no mesmo vídeo, que é o recurso escasso do programa.
                    # Errada estava a mensagem. Ela dizia "já foi baixado ou já está
                    # na vez", que são duas situações diferentes, com ações
                    # diferentes, sem dizer qual era o caso, sem dizer que NADA foi
                    # baixado, e mandando procurar um controle mais abaixo na tela.
                    #
                    # Limpar a fila funcionava porque apagava o endereço conhecido, e
                    # é o pior caminho: leva embora o registro do que já passou por
                    # aqui, que é justamente o que impede a repetição.
                    #
                    # Uma leitura a mais da planilha aqui não incomoda: este é o
                    # caminho de exceção, e sem ela a tela não sabe de qual linha
                    # está falando.
                    repetida = next((x for x in fluxo.ler_fila()
                                     if x["link"] == link_novo), None)
                    if repetida is None:
                        st.info("Esse link já está na fila, então não entrou de novo. "
                                "Nada foi baixado agora.")
                    elif not repetida["status"]:
                        st.info(f"Esse link já estava esperando a vez, na linha "
                                f"{repetida['numero_linha']}, então não entrou duas "
                                f"vezes. Ele vai ser baixado sem você precisar fazer "
                                f"mais nada.")
                    else:
                        # A OFERTA DE BAIXAR DE NOVO FICA FORA DO FORMULÁRIO, porque
                        # o Streamlit não aceita botão dentro de um. Aqui só guarda
                        # qual foi o link; o bloco logo abaixo desenha o aviso e o
                        # botão. Ver o comentário lá para o porquê.
                        st.session_state["link_repetido"] = link_novo

# ZONA EM ÂMBAR (15/09/2026): as ferramentas de exceção e conserto. Ensinar
# perfil, marcar que não postou, o link repetido, o histórico da fila,
# reabrir linha, ajustar ciclo, limpar a fila e baixar pendentes são todos
# sobre a MESMA pergunta, o que fazer com o que não seguiu o caminho normal
# da zona principal acima. Mesma técnica das zonas do Financeiro, container
# com `key=` (ver estilo.py).
#
# O ACOMPANHAMENTO AO VIVO (mais abaixo, `acompanhar_download()`) FICA DE
# FORA DE PROPÓSITO: as funções que ele usa (`resumo_da_tarefa`,
# `_listar_dos_dois`) precisam continuar no nível do arquivo, sem
# indentação, porque há teste que confere isso por texto
# (teste_manutencao_e_atalhos.py: "se voltar para dentro da função de tela,
# deixa de ser testável"). Zona colorida aqui quebraria esse teste sem
# mudar nada de verdade, e a régua deste repositório é não tocar teste para
# a mudança visual passar.
with st.container(key="dl_zona_excecoes"):
    # ENSINAR UM PERFIL AO PROGRAMA (02/09/2026).
    #
    # POR QUE ESTE CONTROLE EXISTE, e é uma correção de percurso.
    #
    # Story de perfil que o programa não conhece é barrado, porque descobrir o
    # número interno do perfil pelo @ é a consulta que o Instagram limita com mais
    # rigor. A tela oferecia duas saídas, e o auditor esbarrou nas duas em 02/09:
    #
    #   passar para o story seguinte e voltar    "o story é único no momento, não
    #                                            consigo passar pro próximo". E o
    #                                            número da peça não resolveria isso
    #                                            de todo jeito, era explicação errada
    #                                            na mensagem.
    #   colar um Reel dele na fila               resolve, mas BAIXA o vídeo e cria
    #                                            linha na Monitoramento: material
    #                                            entrando na auditoria só para o
    #                                            programa aprender um número.
    #
    # Aqui o perfil é aprendido sem baixar nada e sem tocar na Monitoramento. Fica
    # num expansor fechado porque é conserto de primeira vez, não caminho normal.
    with st.expander("Ensinar um perfil ao programa (sem baixar nada)"):
        # ENCURTADO EM 17/09/2026, e o motivo voltou no mesmo dia: sem ele
        # nem o próprio auditor entendia por que "ensinar" é preciso.
        st.caption(
            "Para o primeiro story de um perfil que o programa ainda não "
            "conhece. Cole um link de **Reel ou post** dele: aprende o "
            "número do perfil, sem baixar nada nem criar linha na "
            "Monitoramento. Existe porque o Instagram limita a consulta que "
            "descobre esse número, então o programa evita repetir a cada story."
        )
        c_ap1, c_ap2 = st.columns([5, 1.4])
        link_para_aprender = c_ap1.text_input(
            "Link de Reel ou post", key="link_para_aprender",
            placeholder="https://www.instagram.com/PERFIL/reel/CODIGO/",
            label_visibility="collapsed")
        if c_ap2.button("Aprender", disabled=not link_para_aprender,
                        use_container_width=True):
            try:
                _handle_ap, _uid, _gastou = fluxo.aprender_perfil_por_link(
                    link_para_aprender)
            except Exception as e:
                # Sem traceback na tela: as mensagens dessa função já dizem o que
                # fazer, e o que não é dela (conta pausada, teto do dia) vem com o
                # texto próprio do controle da conta.
                st.error(str(e)[:400])
            else:
                # DIZER SE O TETO DO DIA ANDOU. A tentativa anônima é gratuita e é a
                # que costuma responder, mas quem clica não tem como saber qual das
                # duas aconteceu, e chamada ao Instagram é o recurso que este
                # programa administra.
                quanto = ("sem gastar chamada nenhuma" if not _gastou
                          else f"gastando {_gastou} chamada do teto de hoje")
                st.success(f"Agora conheço @{_handle_ap}, {quanto}. Já pode colar o "
                           f"story dele lá em cima.")
    
    # MARCAR QUEM NÃO POSTOU (11/09/2026).
    #
    # Desenho do próprio auditor: "caso não tenha sido publicada, deve ter um espaço
    # no programa apenas para colocar o handle do influencer e marcar como não
    # publicado (pq ai nao vai baixar nada pq a pessoa não postou)".
    #
    # Fica num expansor fechado, como o de ensinar perfil: é o caminho da exceção,
    # não o do dia a dia. E NÃO GASTA CHAMADA AO INSTAGRAM, porque não há vídeo.
    with st.expander("Marcar que alguém não postou (sem baixar nada)"):
        st.caption(
            "Quando o influenciador não publicou no dia combinado. Escreve "
            "**Não Postada** na linha dele no Calendário de Divulgações do "
            "Marketing. Não baixa vídeo e não gasta chamada do Instagram."
        )
        _np1, _np2, _np3 = st.columns([2.4, 1.4, 1.4])
        _handle_np = _np1.text_input("@ do influenciador", key="handle_nao_postou",
                                     placeholder="ex: giroquue")
        _marca_np = _np2.selectbox(
            "Marca", options=[""] + fluxo.MARCAS, key="marca_nao_postou",
            format_func=lambda m: "escolher..." if not m else fluxo.ROTULO_MARCA[m])
        _data_np = _np3.date_input("Data combinada", key="data_nao_postou",
                                   format="DD/MM/YYYY")
        if st.button("Marcar como não postada", key="botao_nao_postou"):
            if not str(_handle_np).strip() or not _marca_np:
                st.warning("Preencha o @ e a marca.")
            else:
                _gravou_np, _motivo_np = fluxo.marcar_nao_postou(
                    _handle_np, _marca_np, _data_np, identidade.quem_sou_eu())
                if _gravou_np:
                    st.success("Marcado no Calendário.")
                else:
                    st.warning(_motivo_np)
    
    try:
        fila = fluxo.ler_fila()
    except Exception as e:
        st.error(f"Não consegui ler a fila de teste agora: {e}")
        fila = []
    
    pendentes = [x for x in fila if x["link"] and not x["status"]]
    
    # COLOU UM LINK QUE JÁ ESTAVA NA FILA: O PEDIDO FICA AQUI, A UM CLIQUE
    # (02/09/2026).
    #
    # O auditor, depois de um dia inteiro de testes: "para baixar qualquer vídeo eu
    # tive que limpar a fila, sempre antes de baixar algum vídeo tive que limpar a
    # fila".
    #
    # A recusa do link repetido está certa e FICA: é ela que impede gastar duas
    # chamadas ao Instagram no mesmo vídeo, e chamada é o recurso escasso deste
    # programa. O que estava errado era o que sobrava para a pessoa fazer.
    #
    # Primeiro a tela só dizia "esse link já foi baixado ou já está na vez". Depois
    # passou a dizer qual linha e a apontar "Baixar de novo", logo abaixo. Ainda era
    # achar uma linha numa lista, e limpar a fila inteira continuava sendo o caminho
    # mais curto na tela. E limpar é o pior caminho: leva embora o registro do que já
    # passou por aqui, que é justamente o que impede a repetição.
    #
    # O CLIQUE EXISTE DE PROPÓSITO, e não é fricção esquecida: baixar de novo gasta
    # chamada do teto do dia, cria arquivo novo no Drive e linha nova na
    # Monitoramento. Isso não pode acontecer só porque alguém colou o mesmo endereço
    # duas vezes. Um clique é o preço; limpar a fila não deveria ser.
    _repetido = st.session_state.get("link_repetido")
    if _repetido:
        _linha_repetida = next((x for x in fila if x["link"] == _repetido), None)
        if _linha_repetida is None or not _linha_repetida["status"]:
            # A linha saiu da fila, ou já está esperando a vez. Nos dois casos não há
            # o que oferecer, e deixar o aviso na tela seria mentira.
            st.session_state.pop("link_repetido", None)
        else:
            _ja_teve_sucesso = fluxo.e_status_sucesso(_linha_repetida["status"])
    
            def _rebaixar_o_colado():
                """Reabre a linha do link colado e manda baixar, no mesmo clique.
    
                Roda como AÇÃO do botão, e não depois dele, pelo mesmo motivo
                registrado em _reabrir_escolhidas: o Streamlit recusa alterar campo
                já desenhado, e limpar o estado depois do clique dá erro."""
                numero = st.session_state.get("linha_do_repetido")
                if not numero:
                    return
                # RECONFERE AQUI, e não só no desenho do botão (15/09/2026): campo
                # desabilitado é aparência, a autorização precisa valer onde a
                # ação acontece de fato, mesmo cuidado já tomado no Cadastro.
                _linha_agora = next((x for x in fila if x["numero_linha"] == numero), None)
                if _linha_agora and fluxo.e_status_sucesso(_linha_agora["status"]):
                    _pode_agora, _, _ = acesso.autorizacao_para_qualquer(
                        acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
                    if not _pode_agora:
                        return
                motivo = (st.session_state.get("motivo_rebaixar_colado") or "").strip()
                fluxo.reabrir_na_fila([numero], quem=identidade.quem_sou_eu(),
                                      motivo=motivo or None)
                # Só cria tarefa se não houver uma, igual ao formulário: cada tarefa
                # processa TODOS os links pendentes, e é dentro da rodada que as
                # pausas entre chamadas ao Instagram acontecem.
                ja_ha = fila_trabalho.ha_trabalho(fila_trabalho.BAIXAR_FILA)
                if not ja_ha:
                    fila_trabalho.criar(
                        fila_trabalho.BAIXAR_FILA,
                        {"analisar_depois": True},
                        rotulo="baixar de novo 1 linha",
                        criada_por=identidade.quem_sou_eu())
                # Reusa a mensagem de "Baixar de novo", que já distingue o caso de
                # ter pegado carona numa rodada em andamento.
                st.session_state["reabertas"] = (1, ja_ha)
                st.session_state.pop("link_repetido", None)
                st.session_state.pop("linha_do_repetido", None)
                st.session_state.pop("motivo_rebaixar_colado", None)
    
            st.session_state["linha_do_repetido"] = _linha_repetida["numero_linha"]
            _c_rep1, _c_rep2 = st.columns([4, 1.4])
            _c_rep1.warning(
                f"**Nada foi baixado.** Esse link já está na linha "
                f"{_linha_repetida['numero_linha']}, com status "
                f"*{_linha_repetida['status']}*, e a fila não aceita o mesmo endereço "
                f"duas vezes para não gastar duas chamadas no mesmo vídeo. Baixar de "
                f"novo gasta uma chamada do teto de hoje, e gera arquivo novo no Drive "
                f"e linha nova na Monitoramento."
            )
            # SUPERVISÃO OU COORDENAÇÃO PASSOU A SER EXIGIDA (15/09/2026), além
            # do motivo. Pedido do Marketing na reunião de go live: "impedir
            # novos downloads de links já processados com sucesso". Bloqueio
            # total sem exceção deixaria sem saída um caso legítimo (vídeo
            # certo, mas apagado do Drive por engano, por exemplo); a saída
            # escolhida foi a mesma já usada no Cadastro, quem usa a tela no
            # dia a dia não vê a opção, só quem tem um desses dois papéis, e
            # mesmo assim com motivo obrigatório e registrado.
            _motivo_bloqueia = False
            if _ja_teve_sucesso:
                _pode_reprocessar_sucesso, _motivo_papel_sucesso, _ = acesso.autorizacao_para_qualquer(
                    acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
                if not _pode_reprocessar_sucesso:
                    st.info(_motivo_papel_sucesso)
                    _motivo_bloqueia = True
                else:
                    st.text_input(
                        "Por que baixar de novo algo que já teve sucesso?",
                        key="motivo_rebaixar_colado",
                        placeholder="ex: o vídeo foi apagado do Drive por engano",
                    )
                    _motivo_bloqueia = not (st.session_state.get("motivo_rebaixar_colado") or "").strip()
            _c_rep2.button("Baixar de novo", icon=":material/replay:",
                           key="rebaixar_o_colado", disabled=_motivo_bloqueia,
                           on_click=_rebaixar_o_colado, use_container_width=True)
    
    if fila:
        # A TABELA É O REGISTRO DO QUE JÁ PASSOU POR AQUI (renomeada em 01/09/2026).
        #
        # Ela sempre foi isso, e era chamada de fila. Com o botão "Baixar" mandando
        # no mesmo clique, chamar de fila passou a confundir: a pessoa não precisa
        # mais saber que existe uma fila, e o que ela quer olhar aqui é o que já foi
        # baixado e o que deu problema.
        #
        # Sem a coluna de destino: ela saiu da planilha em 31/08/2026 por ser escrita
        # e exibida sem nunca ser usada. O endereço do arquivo no Drive aparece em
        # "Últimos organizados", no fim desta tela, que lê do registro.
        st.caption(f"**O que já passou por aqui** ({len(fila)} linha(s)). "
                   + ("Tudo baixado." if not pendentes
                      else f"{len(pendentes)} ainda sem baixar."))
        # A coluna da marcação entrou aqui em 01/09/2026 junto com a marcação, e a
        # do jogo em 15/09/2026, mesmo motivo: quem escolhe precisa poder conferir
        # depois o que foi gravado, e a tabela é o único lugar da tela que mostra o
        # que já passou. Sem a coluna, o jogo digitado só aparecia se a pessoa fosse
        # conferir na planilha do Calendário, e mesmo lá só quando a célula estivesse
        # vazia (a automação nunca escreve por cima de conteúdo já existente).
        st.dataframe(pd.DataFrame(fila)[["influenciador", "link", "status", "ciclo",
                                         "marca", "marcacao", "jogo"]],
                     use_container_width=True)
    
    # --- reabrir qualquer linha já processada ---
    processadas = [x for x in fila if x["status"]]
    if processadas:
        # TEXTO ENXUGADO EM 16/09/2026: eram seis linhas, e quatro delas
        # explicavam o que o próprio campo já cobra na hora (o motivo só é
        # pedido quando a linha deu certo, e o botão fica travado sem ele). O
        # que sobra é o que a pessoa precisa saber ANTES de clicar: sai um
        # arquivo novo e uma linha nova, não é um "desfazer".
        # ENCURTADO EM 17/09/2026, e ENCURTADO DEMAIS: virou "reabrir sucesso
        # exige motivo", que não é português (ninguém reabre um sucesso). O
        # auditor apontou em 23/09/2026 lendo a tela. O conteúdo estava certo,
        # a redação é que tinha perdido o sujeito da frase: o que se reabre é
        # uma LINHA que já deu certo.
        st.caption(
            "Gera arquivo e linha novos. Reabrir uma linha que já deu certo "
            "exige motivo escrito, e papel de supervisão ou coordenação."
        )
        def _reabrir_escolhidas():
            """Reabre as linhas e limpa a seleção.
    
            Isto roda como AÇÃO DO BOTÃO, não depois dele, de propósito: o
            Streamlit recusa alterar o valor de um campo já desenhado na tela, e
            limpar a seleção logo após o clique dava o erro "cannot be modified
            after the widget is instantiated". Dentro da ação do botão, a alteração
            acontece antes da tela ser redesenhada e é aceita.
    
            Limpar importa: se a seleção continuasse marcada, a escolha seguinte
            reabriria de novo o que já tinha sido reaberto."""
            escolhidas = st.session_state.get("reabrir_escolhidas") or []
            if not escolhidas:
                return
            # RECONFERE AQUI, e não só no desenho do botão (15/09/2026), mesmo
            # cuidado do bloco de link colado logo acima: campo desabilitado é
            # aparência, a autorização precisa valer onde a ação acontece.
            _numeros_sucesso_agora = {x["numero_linha"] for x in fila
                                      if fluxo.e_status_sucesso(x["status"])}
            if any(n in _numeros_sucesso_agora for n in escolhidas):
                _pode_agora, _, _ = acesso.autorizacao_para_qualquer(
                    acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
                if not _pode_agora:
                    return
            motivo = (st.session_state.get("motivo_reabrir_escolhidas") or "").strip()
            # Passa QUEM pediu (01/09/2026). Isso vira duas coisas: o rastro de que
            # o material entrou duas vezes por decisão de alguém, e o que faz o
            # envio não tratar o arquivo repetido como peça reaproveitada pelo
            # influenciador, que seria acusação de contrato indevida.
            fluxo.reabrir_na_fila(escolhidas, quem=identidade.quem_sou_eu(),
                                  motivo=motivo or None)
    
            # E BAIXA NO MESMO CLIQUE (02/09/2026).
            #
            # É o mesmo motivo que fez o botão "Baixar" do formulário mandar baixar
            # em 01/09. Aqui ainda eram três passos: achar a linha na lista, clicar
            # em "Baixar de novo", e então descobrir um terceiro botão mais abaixo.
            # Era isso que fazia o auditor preferir limpar a fila inteira e colar o
            # link outra vez, que é o caminho que apaga o registro.
            #
            # Só cria tarefa se não houver uma, igual ao formulário: cada tarefa
            # processa TODOS os links pendentes, e é DENTRO da rodada que as pausas
            # entre chamadas ao Instagram acontecem. Duas tarefas ao mesmo tempo
            # tirariam a pausa de entre os links.
            ja_ha_download = fila_trabalho.ha_trabalho(fila_trabalho.BAIXAR_FILA)
            if not ja_ha_download:
                # SEMPRE True (15/09/2026, corrigido): lia uma chave de sessão
                # de uma caixa que não existe mais desde 14/09, sempre vindo
                # None -> False. Analisar tudo que entra é a política do
                # projeto, sem exceção por aqui (ver o comentário lá em cima,
                # perto de onde a caixa antiga foi removida).
                fila_trabalho.criar(
                    fila_trabalho.BAIXAR_FILA,
                    {"analisar_depois": True},
                    rotulo=f"baixar de novo {len(escolhidas)} linha(s)",
                    criada_por=identidade.quem_sou_eu())
            # Guarda também se pegou carona numa rodada que já corria: nesse caso o
            # programa NÃO garante que ela vá pegar estas linhas, porque a rodada lê
            # a fila quando começa. Prometer que já está baixando seria mentira, e o
            # botão dos pendentes continua ali como saída.
            st.session_state["reabertas"] = (len(escolhidas), ja_ha_download)
            st.session_state["reabrir_escolhidas"] = []
            st.session_state["motivo_reabrir_escolhidas"] = ""
    
        c1, c2 = st.columns([4, 1])
        escolhidas = c1.multiselect(
            "Baixar de novo",
            options=[x["numero_linha"] for x in processadas],
            format_func=lambda n: next(
                f"{x['influenciador'] or 'sem nome'} · {x['link'][:50]} · {x['status'][:34]}"
                for x in processadas if x["numero_linha"] == n
            ),
            label_visibility="collapsed",
            key="reabrir_escolhidas",
            # Sem isto o Streamlit escreve "Choose options" em inglês no campo
            # vazio, que foi o que apareceu na tela em 29/08/2026.
            placeholder="Escolha as linhas para baixar de novo",
        )
        # SUPERVISÃO OU COORDENAÇÃO, ALÉM DO MOTIVO (15/09/2026), quando
        # alguma escolhida já tinha dado certo. Mesmo raciocínio do bloco de
        # _rebaixar_o_colado, acima: falha continua sem fricção, sucesso pede
        # papel autorizado e justificativa registrada.
        _numeros_sucesso = {x["numero_linha"] for x in processadas
                            if fluxo.e_status_sucesso(x["status"])}
        _tem_sucesso_escolhido = any(n in _numeros_sucesso for n in escolhidas)
        _motivo_bloqueia_lote = False
        if _tem_sucesso_escolhido:
            _pode_reprocessar_lote, _motivo_papel_lote, _ = acesso.autorizacao_para_qualquer(
                acesso.PAPEL_SUPERVISAO, acesso.PAPEL_COORDENACAO)
            if not _pode_reprocessar_lote:
                st.info(_motivo_papel_lote)
                _motivo_bloqueia_lote = True
            else:
                st.text_input(
                    "Por que baixar de novo algo que já teve sucesso?",
                    key="motivo_reabrir_escolhidas",
                    placeholder="ex: o vídeo foi apagado do Drive por engano",
                )
                _motivo_bloqueia_lote = not (st.session_state.get("motivo_reabrir_escolhidas") or "").strip()
        c2.button("Baixar de novo", icon=":material/replay:",
                  disabled=not escolhidas or _motivo_bloqueia_lote,
                  on_click=_reabrir_escolhidas)
    
    if st.session_state.get("reabertas"):
        # Texto corrigido em 01/09/2026: dizia "clique em processar", e não existe
        # mais um botão com esse nome. Em 02/09 o botão passou a baixar no mesmo
        # clique, então a mensagem deixou de mandar clicar em outro lugar.
        n, pegou_carona = st.session_state.pop("reabertas")
        if pegou_carona:
            st.info(f"{n} linha(s) voltaram para a fila. Já havia um download em "
                    f"andamento, e ele pode não pegar estas linhas, porque a rodada "
                    f"lê a fila quando começa. Se elas ficarem esperando, use "
                    f"**Baixar os que ficaram pendentes**, logo abaixo.")
        else:
            st.success(f"**Baixando de novo.** {n} linha(s) voltaram para a fila e o "
                       f"download já foi mandado. Cada uma gera um arquivo novo no "
                       f"Drive e uma linha nova na Monitoramento.")
    
    # --- escolher o ciclo de uma linha que ficou esperando ---
    #
    # FICOU DENTRO DE UM EXPANSOR EM 01/09/2026, e o motivo é bom: desde que o ciclo
    # passou a ser informado na primeira seção, junto do link, este bloco deixou de
    # ser caminho normal e virou conserto. O auditor viu os dois na tela e apontou a
    # redundância.
    #
    # NÃO foi removido porque ainda tem um uso real: linha que ficou pendente sem
    # ninguém ter pedido, por exemplo barrada pelo teto do dia ou reaberta por
    # "Baixar de novo". Nesse caso o link já está na fila e não há como voltar e
    # informar o ciclo na seção 1.
    if pendentes:
        with st.expander(f"Ajustar o ciclo de uma das {len(pendentes)} linha(s) que ficaram "
                         f"esperando"):
            st.caption(
                "O normal é o ciclo vir da data do vídeo, ou de você informar ao colar o link. "
                "Isto aqui serve para linha que já está esperando e cujo ciclo precisa ser "
                "outro, o que acontece quando os ciclos da Monitoramento se sobrepõem."
            )
            c1, c2, c3 = st.columns([4, 1, 1])
            linha_ciclo = c1.selectbox(
                "Linha",
                options=[x["numero_linha"] for x in pendentes],
                format_func=lambda n: next(
                    f"{x['influenciador'] or 'sem nome'} · {x['link'][:58]}"
                    + (f" · hoje: {x['ciclo']}" if x["ciclo"] else "")
                    for x in pendentes if x["numero_linha"] == n
                ),
                label_visibility="collapsed",
            )
            ciclo_fila = c2.text_input("Ciclo", placeholder=fluxo.PLACEHOLDER_CAMPO_CICLO,
                                       help=fluxo.ajuda_campo_ciclo(),
                                       label_visibility="collapsed")
            if c3.button("Definir ciclo", icon=":material/numbers:",
                         disabled=not ciclo_fila):
                fluxo.definir_ciclo_na_fila(linha_ciclo, ciclo_fila)
                st.rerun()
    
    c_proc, c_limpa = st.columns([3, 2])
    with c_limpa:
        if fila:
            with st.popover(f"Limpar a fila ({len(fila)} linha(s))",
                                icon=":material/delete:", use_container_width=True):
                # A fila de downloads é COMPARTILHADA: os links que aparecem aqui
                # foram colados por qualquer uma das pessoas que usam o programa.
                # Antes a tela não dizia isso, e limpar parecia arrumação própria
                # (aviso acrescentado em 29/08/2026).
                _nao_processadas = sum(1 for x in fila if not x["status"])
                st.warning(
                    f"**Isto alcança todo mundo.** A fila é compartilhada, e as {len(fila)} linhas "
                    "podem ter sido coladas por outras pessoas."
                    + (f" **{_nao_processadas} ainda não foram baixadas** e seriam perdidas."
                       if _nao_processadas else "")
                )
                st.caption(
                    "Apaga todas as linhas da fila, inclusive as já processadas. Os vídeos que já foram "
                    "pro Drive e as linhas já gravadas na Monitoramento **não** são afetados."
                )
                confirmou = st.checkbox("Sei que isso apaga a fila inteira, de todas as pessoas")
                if st.button("Apagar agora", type="primary", disabled=not confirmou):
                    apagadas = fluxo.limpar_fila()
                    st.session_state["fila_apagada"] = apagadas
                    st.rerun()
    
    if st.session_state.pop("fila_apagada", None):
        st.success("Fila limpa.")
    
    # MUDANÇA DE 29/08/2026: o download saiu de dentro da aba do navegador.
    #
    # Antes, clicar aqui baixava tudo dentro da sessão de quem clicou, e a tela
    # ficava presa até terminar. Com as pausas de propósito entre links do
    # Instagram, de 45 a 120 segundos cada, isso podia prender a tela por muitos
    # minutos, e fechar a aba no meio deixava trabalho pela metade.
    #
    # O motivo mais forte, porém, não é conforto: é que duas pessoas baixando ao
    # mesmo tempo furam o teto diário do Instagram, porque cada uma conta as
    # chamadas por conta própria. Agora existe uma fila só e um trabalhador só,
    # então as chamadas ao Instagram voltam a sair em fila indiana.
    ja_baixando = fila_trabalho.ha_trabalho(fila_trabalho.BAIXAR_FILA)
    ja_enviando = fila_trabalho.ha_trabalho(fila_trabalho.ENVIAR_ARQUIVOS)
    
    # ESTE BOTÃO DEIXOU DE SER O CAMINHO NORMAL (01/09/2026).
    #
    # Desde que "Baixar" manda no mesmo clique, ele só serve para o que ficou
    # pendente sem ninguém ter pedido: link barrado pelo teto do dia, ou linha
    # reaberta com "Baixar de novo". Fora disso não há o que ele faça, então ele
    # aparece SÓ quando há pendência de verdade, em vez de ficar na tela dizendo
    # "0 pendente(s)" e convidando ao clique inútil.
    processar = False
    if pendentes:
        with c_proc:
            processar = st.button(
                f"Baixar os {len(pendentes)} que ficaram pendentes",
                disabled=ja_baixando,
                # O TEXTO EXPLICA O ESPAÇAMENTO (06/09/2026, encurtado
                # 17/09/2026). O auditor achou que um link tinha travado; era
                # só a pausa de propósito entre links, pra não levar bloqueio
                # do Instagram. Os números continuam aqui por isso mesmo.
                help=(f"Já tem um download rodando, e vai pegar estes: os "
                      f"links são espaçados de propósito "
                      f"({int(fluxo.PAUSA_INSTAGRAM_MIN_SEG)} a "
                      f"{int(fluxo.PAUSA_INSTAGRAM_MAX_SEG)}s, até "
                      f"{int(fluxo.PAUSA_ENTRE_RODADAS_MAX_SEG // 60)}min "
                      f"entre rodadas), pra não levar bloqueio."
                      if ja_baixando else
                      f"O trabalhador pega sozinho em até "
                      f"{int(fila_trabalho.SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO)}"
                      f"s. Este botão só serve pra não esperar."))
    if processar:
        fila_trabalho.criar(fila_trabalho.BAIXAR_FILA,
                            {"analisar_depois": True},
                            rotulo=f"{len(pendentes)} link(s) pendente(s) · analisa em seguida",
                            criada_por=identidade.quem_sou_eu())
        st.session_state["download_mandado"] = True
        st.rerun()
    
    if st.session_state.pop("download_mandado", None):
        # Ver o comentário igual na tela de Validação: "pode fechar esta aba" lia
        # como instrução para fechar, e a intenção é o contrário.
        # Texto ajustado em 01/09/2026: dizia "Mandado para a fila", que era o
        # vocabulário de quando a fila era um passo visível na tela. Agora este
        # caminho só atende o que ficou pendente.
        st.success("Baixando os pendentes. Cada um segue para a análise assim que "
                   "terminar, sem precisar de outro clique. O trabalho continua "
                   "mesmo se você fechar a aba.")
    
    
# Acompanhamento do download em andamento. Igual ao da tela de validação, este
# bloco se atualiza sozinho sem redesenhar a página inteira, que aqui é ainda
# mais importante: o topo desta tela lê a fila na planilha a cada desenho.
# Parado, se atualiza mais devagar em vez de parar: é assim que uma pessoa vê
# que a outra mandou baixar, sem recarregar a página.
_intervalo_download = 3 if (ja_baixando or ja_enviando) else 15

# SÓ BAIXAR_FILA DESDE 23/09/2026: ENVIAR_ARQUIVOS (e o novo ENVIAR_VIDEO_BRUTO)
# se mudaram para a página de Uploads, com o próprio acompanhamento lá. Até
# essa data os dois tipos apareciam juntos aqui, porque para quem olhava a
# tela era tudo "o programa está trabalhando no meu material"; a separação em
# duas páginas levou o acompanhamento de cada um para a página onde ele mora.
_TIPOS_DESTA_TELA = (fila_trabalho.BAIXAR_FILA,)


def _listar_dos_dois(situacao):
    tarefas = []
    for tipo in _TIPOS_DESTA_TELA:
        tarefas.extend(fila_trabalho.listar(situacao, tipo))
    tarefas.sort(key=lambda t: t.get("criada_em") or "")
    return tarefas


# resumo_da_tarefa MUDOU-SE PARA fluxo_downloads.py EM 23/09/2026, quando a
# seção "Enviar arquivo do post" se mudou para a página de Uploads: a mesma
# função passou a servir as duas páginas, e função de tela não é importável
# sem rodar a tela inteira. Ver o comentário completo lá.
resumo_da_tarefa = fluxo.resumo_da_tarefa


@st.fragment(run_every=_intervalo_download)
def acompanhar_download():
    em_andamento = _listar_dos_dois(fila_trabalho.RODANDO)
    esperando = _listar_dos_dois(fila_trabalho.PENDENTE)

    tem_trabalho = bool(em_andamento or esperando)
    tinha_trabalho = st.session_state.get("tinha_download_na_fila", False)
    st.session_state["tinha_download_na_fila"] = tem_trabalho

    if esperando and not em_andamento:
        # "ESPERANDO" SÓ É TRANQUILIZADOR SE ALGUÉM FOR PEGAR (06/09/2026).
        #
        # O auditor viu a fila parada e perguntou por que: "não é a primeira
        # vez, ai preciso limpar a fila". Os números estavam certos e não havia
        # bug: o trabalhador estava fora do ar, então a tarefa esperava por
        # alguém que não existia. Mas a tela dizia isso em caixa AZUL, no tom de
        # "está tudo em ordem, aguarde".
        #
        # O aviso vermelho de trabalhador fora do ar existe, e fica no TOPO da
        # página. Quem está mexendo na fila está lá embaixo, lê "esperando" e
        # conclui que é normal. Informação certa no lugar errado.
        #
        # E LIMPAR A FILA NÃO RESOLVE, embora pareça: apaga a linha e zera o
        # pendente, mas a tarefa órfã continua na fila do trabalhador e a causa
        # não é tocada. Por isso a mensagem diz o que resolve.
        _de_pe_agora, _ = fila_trabalho.trabalhador_de_pe()
        if _de_pe_agora:
            st.info(f"{len(esperando)} na fila, esperando o processo pegar.")
        else:
            st.error(
                f"**{len(esperando)} na fila, e ninguém vai pegar:** o "
                f"processo está fora do ar. Suba ele (dois cliques em "
                f"`iniciar_trabalhador.bat`) e ele pega sozinho o que ficou "
                f"esperando. Limpar a fila não resolve isto."
            )

    # A ESPERA PROPOSITAL FICA VISÍVEL (06/09/2026). Sem esta linha, quem olha a
    # tela durante a pausa vê "1 ainda sem baixar" e conclui que o link foi
    # esquecido. Ele não foi: o programa está esperando de propósito.
    if em_andamento and any(t.get("tipo") == fila_trabalho.BAIXAR_FILA
                            for t in em_andamento):
        # AS DUAS PAUSAS APARECEM, E NÃO SÓ A MENOR (08/09/2026).
        #
        # Este texto citava só a pausa entre links, de 30 a 180 segundos. Só que
        # existe uma SEGUNDA pausa, maior, entre rodadas, de 180 a 420 segundos.
        # Quem lia a tela esperava no máximo 3 minutos e ficava esperando 6, e
        # concluía que travou. Aconteceu em uso real em 08/09/2026: a pausa
        # sorteada foi de 356 segundos, e o único lugar que dizia isso era a
        # janela do trabalhador, que não é onde a pessoa está olhando. É o mesmo
        # defeito que a correção de 06/09 tentou resolver, com o número errado.
        st.caption(
            f"Links do Instagram são baixados **um por vez**, com pausa de "
            f"{int(fluxo.PAUSA_INSTAGRAM_MIN_SEG)} a "
            f"{int(fluxo.PAUSA_INSTAGRAM_MAX_SEG)} segundos entre um link e o "
            f"próximo, e de "
            f"{int(fluxo.PAUSA_ENTRE_RODADAS_MIN_SEG // 60)} a "
            f"{int(fluxo.PAUSA_ENTRE_RODADAS_MAX_SEG // 60)} minutos antes de "
            f"começar uma rodada nova. É de propósito, para não levar bloqueio. "
            f"Se ainda há linha sem baixar, ela está na vez, e a espera pode "
            f"chegar a "
            f"{int(fluxo.PAUSA_ENTRE_RODADAS_MAX_SEG // 60)} minutos."
        )

    for tarefa in em_andamento:
        verbo = ("Baixando" if tarefa.get("tipo") == fila_trabalho.BAIXAR_FILA
                 else "Organizando os arquivos enviados")
        st.caption(f"{verbo} desde {tarefa.get('comecou_em', '')[11:16]}, "
                   f"pedido por {tarefa.get('criada_por', '')}.")
        mensagens = tarefa.get("mensagens") or []
        if mensagens:
            st.code("\n".join(mensagens[-25:]), language=None)

    if tinha_trabalho and not tem_trabalho:
        # Terminou: redesenha a página inteira uma vez para a fila da planilha
        # e o log refletirem o que acabou de acontecer.
        st.rerun(scope="app")

    # COM TRABALHO EM ANDAMENTO, O RESULTADO ANTERIOR NÃO APARECE.
    #
    # Pedido do auditor em 31/08/2026, olhando a tela: apareciam dois blocos de
    # registro, um embaixo do outro, e lia como se fosse o mesmo histórico
    # repetido. Não era: o de cima é a tarefa que está rodando agora, e o de
    # baixo era a última que terminou. Duas coisas diferentes com a mesma
    # aparência é pior que uma só, e durante o trabalho o que interessa é o
    # trabalho. Quando a fila esvazia, o resultado aparece.
    if tem_trabalho:
        return

    # Só o último aparece. Antes cada download terminado virava um bloco com
    # expansor próprio, e eles iam empilhando na tela sem que o mais recente se
    # destacasse (apontado pelo auditor em 29/08/2026, com três blocos
    # visíveis). Depois disso o resto foi para um expansor de histórico,
    # "Anteriores", e em 31/08/2026 esse expansor também saiu, no mesmo pedido
    # de simplificar a tela. Quem precisa de histórico tem o registro completo
    # do fluxo no fim desta tela, que é mais detalhado e não desaparece.
    #
    # Como só o mais recente é mostrado, basta pedir um de cada tipo e comparar
    # os dois. Antes eram oito de cada, e sete de cada dez arquivos lidos eram
    # descartados na hora. Este bloco relê a cada 3 a 15 segundos, para cada
    # pessoa com a tela aberta, então ler menos importa quando forem cinco.
    ultimas = sorted(
        [t for tipo in _TIPOS_DESTA_TELA
         for t in fila_trabalho.ultimas_terminadas(tipo, quantas=1)],
        key=lambda t: t.get("terminou_em") or "", reverse=True,
    )
    if ultimas:
        recente = ultimas[0]
        aparencia, texto, motivos = resumo_da_tarefa(recente)
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
        # Sem o "▾" no rótulo: o Streamlit já desenha a seta dele, e apareciam
        # duas (visto na tela pelo auditor em 31/08/2026).
        #
        # SEM MENSAGEM, SEM EXPANSOR (02/09/2026). Ele abria e mostrava "sem
        # registro", que o auditor leu como defeito. Expansor vazio é convite
        # para abrir e não achar nada; a explicação, quando existe, já sobe como
        # legenda acima.
        mensagens_da_tarefa = [str(m) for m in (recente.get("mensagens") or [])]
        if mensagens_da_tarefa:
            with st.expander("Ver o que aconteceu"):
                st.code("\n".join(mensagens_da_tarefa), language=None)

        # Sem botão de limpar aqui, pelo mesmo motivo registrado na tela de
        # Validação: a lista é compartilhada, e quem limpasse limparia o
        # acompanhamento das outras pessoas. Some sozinha em 48 horas.
        # A SEGUNDA FRASE SAIU EM 16/09/2026 porque ficou mentirosa: ela
        # mandava ver "o registro completo do fluxo no final desta tela", e o
        # final da tela deixou de ter isso em 14/09, quando a seção
        # "Organizado no Drive" (com o log inteiro) foi removida.
        st.caption("Some sozinha depois de 48 horas.")


acompanhar_download()

st.divider()

# A ZONA VERDE (registro de link sem baixar, e envio de arquivo do post da
# supervisão) SE MUDOU PARA A PÁGINA DE UPLOADS EM 23/09/2026, pedido do
# auditor: separar o que É download automatizado do Instagram (esta página)
# do que são as entradas manuais de material (a outra). A pasta vigiada no
# computador, removida em 28/08/2026 e só citada aqui, se mudou junto — ver
# pages/5_Uploads.py, e fluxo.processar_watch continua em fluxo_downloads.py
# sem nenhuma tela chamando.

st.divider()

# ------------------------------------------------------------------
# A seção "Organizado no Drive" (contagem por influenciador/ciclo, o atalho
# da pasta do Drive, "Tirar material de teste", "Últimos organizados" e o log
# completo do fluxo) saiu em 14/09/2026, pedido do auditor para a tela ficar
# mais limpa. A limpeza de material de teste continua disponível por fora,
# com `py ferramentas\limpar_teste.py @handle` (chama a mesma
# `fluxo.remover_material_de_teste`). As métricas do topo desta página (linhas
# ~104-117) usam as mesmas listas `log`/`organizados`, calculadas de forma
# independente, e não dependem do que saiu daqui.
#
# O ATALHO DO CALENDÁRIO SAIU TAMBÉM EM 15/09/2026, a pedido do auditor: era
# mais um link pra planilha crua na tela, e a diretriz do dia é ter o mínimo
# disso possível. Tinha entrado sozinho em 14/09 junto da limpeza de
# "Organizado no Drive", mas por pouco tempo.

# A SEÇÃO "MANUTENÇÃO" SAIU DAQUI EM 17/09/2026: era uma segunda cópia do
# mesmo botão de encerrar, parada no fim da tela, longe de onde a decisão de
# atualizar acontece. O auditor apontou a duplicidade duas vezes no mesmo
# dia. O botão continua existindo, só que num lugar só: dentro de "Cuidar
# das bibliotecas de download", ali em cima, perto do "Atualizar agora" que
# ele destrava.
