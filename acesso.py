# -*- coding: utf-8 -*-
"""
Quem pode abrir o programa.

POR QUE ISTO EXISTE (30/08/2026)

Até aqui o programa não pedia senha. Enquanto ele roda na máquina de trabalho,
escutando só em 127.0.0.1, isso é aceitável: quem alcança a tela já está
sentado na máquina. No servidor deixa de ser, e o motivo não é a tela em si.

O que está atrás da tela são as credenciais do Google que ficam no servidor, de
escopo amplo, e a conta do Instagram. Quem abrir a tela usa as duas sem
precisar provar nada. Por isso o par que importa é este:

    escuta só em 127.0.0.1  +  sem login   ->  aceitável, é o de hoje
    escuta na rede          +  sem login   ->  NÃO, é entregar as credenciais
    escuta na rede          +  com login   ->  é o que se quer no servidor

Este módulo cuida do segundo e do terceiro caso. Ele NÃO liga o login sozinho:
enquanto não houver a configuração, o programa segue funcionando como hoje,
para não travar o teste. O que ele faz é impedir a combinação perigosa passar
despercebida.

COMO LIGAR, QUANDO A EMPRESA DER O REGISTRO DO APLICATIVO

O Streamlit fala OpenID Connect, que é o que o Microsoft 365 da empresa usa.
Criar .streamlit/secrets.toml (que NÃO vai para o repositório, a lista de
permissão já bloqueia) com:

    [auth]
    redirect_uri = "https://ENDERECO-DO-SERVIDOR/oauth2callback"
    cookie_secret = "uma frase longa e aleatória, só deste servidor"
    client_id = "..."
    client_secret = "..."
    server_metadata_url = "https://login.microsoftonline.com/TENANT/v2.0/.well-known/openid-configuration"

O TENANT, o client_id e o client_secret saem do registro do aplicativo no Entra
ID, que é pedido para quem cuida do Microsoft 365. O redirect_uri precisa ser
cadastrado lá igualzinho, senão a volta do login falha.

DÁ PARA USAR A CONTA GOOGLE NO LUGAR (perguntado pelo auditor em 31/08/2026)

Sim, e sem mexer em código: este módulo não sabe qual é o provedor, só precisa
dos cinco campos acima. Para Google, muda uma linha:

    server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

O client_id e o client_secret saem de uma credencial OAuth do tipo APLICATIVO DA
WEB, criada no Google Cloud Console. A credencial que o projeto já usa NÃO
serve: ela é de aplicativo instalado (ver `autorizar_drive.py`, que usa
InstalledAppFlow) e esse tipo não aceita volta de login web.

DUAS ARMADILHAS DO CAMINHO DO GOOGLE, e a primeira é séria:

1. O Entra ID de uma empresa só deixa entrar quem é daquela empresa, porque o
   endereço do provedor já é o do inquilino dela. O `accounts.google.com` é
   GLOBAL: aceita qualquer conta Google do mundo, inclusive pessoal. Por isso
   este módulo passou a exigir domínio (ver DOMINIOS_AUTORIZADOS abaixo).
   Sem isso, ligar o login com Google seria pior que não ter login, porque
   pareceria protegido.

2. Tanto o Google quanto a Microsoft só aceitam volta de login em endereço
   HTTPS, com uma exceção: `http://localhost`. Então o login funciona na máquina
   de trabalho hoje mesmo, e no servidor exige HTTPS ou um nome com certificado.
   Isso vale para os dois provedores, não é limitação do Google.

Assim que esse arquivo existir, o login passa a ser exigido sozinho, o campo de
nome declarado da barra lateral some (ver identidade.py) e a coluna "Pedido
por" passa a trazer e-mail verificado em vez de nome digitado.

QUEM PODE ENTRAR

Ter conta na empresa não é o mesmo que poder usar esta ferramenta. LISTA_DE_
PERMISSAO limita a quem de fato trabalha nisso.

Quando ela está vazia, entra quem tem conta de um DOMÍNIO autorizado
(DOMINIOS_AUTORIZADOS, que já vem com o da empresa). Antes de 31/08/2026, lista
vazia significava "qualquer pessoa autenticada", o que só era seguro porque o
provedor previsto era o Entra ID da empresa. Com a possibilidade de usar Google,
que é provedor global, esse padrão passaria a aceitar o mundo inteiro.

Se as DUAS listas estiverem vazias, ninguém entra, e a mensagem diz o que
configurar. A porta de entrada falha FECHADA de propósito: aqui, negar acesso
indevidamente é problema de dez minutos, e conceder é incidente.
"""
import os

import streamlit as st

# E-mails que podem usar, um por linha na variável de ambiente, separados por
# vírgula. Vazio quer dizer "qualquer pessoa autenticada".
LISTA_DE_PERMISSAO = [
    e.strip().lower()
    for e in (os.environ.get("EMAILS_AUTORIZADOS") or "").split(",")
    if e.strip()
]

# Domínios cujas contas podem entrar quando não há lista de e-mails. Vem com o
# da empresa preenchido, e não vazio, porque vazio é o valor perigoso: ver o
# item 1 das armadilhas do Google, no topo deste arquivo.
DOMINIOS_AUTORIZADOS = [
    d.strip().lower().lstrip("@")
    for d in (os.environ.get("DOMINIOS_AUTORIZADOS") or "grupoegb.com").split(",")
    if d.strip()
]


# AS CINCO CHAVES SÃO UMA CONSTANTE, e não uma lista escrita aqui dentro
# (07/09/2026). O verificador de ambiente passou a conferir as mesmas chaves, e
# duas listas iguais escritas em dois arquivos divergem na primeira mudança. Se
# divergirem, o verificador diria que o login está configurado e o programa
# abriria sem pedir login, que é exatamente a falha silenciosa que este bloco
# existe para evitar.
CHAVES_DO_LOGIN = ("client_id", "client_secret", "server_metadata_url",
                   "redirect_uri", "cookie_secret")


def login_configurado():
    """Se existe configuração de login neste servidor.

    Lê os segredos com cuidado: sem o arquivo secrets.toml, tocar em st.secrets
    levanta erro, e isso não pode derrubar o programa."""
    try:
        auth = st.secrets.get("auth")
    except Exception:
        return False
    if not auth:
        return False
    # Só considera configurado quando o essencial está lá. Configuração pela
    # metade falharia no meio do login, com mensagem que não ajuda ninguém.
    try:
        return all(auth.get(c) for c in CHAVES_DO_LOGIN)
    except Exception:
        return False


def esta_logado():
    try:
        return bool(getattr(st.user, "is_logged_in", False))
    except Exception:
        return False


def email_de_quem_entrou():
    try:
        return str(getattr(st.user, "email", "") or "").lower() or None
    except Exception:
        return None


# ------------------------------------------------------------------
# PAPÉIS, E O QUE CADA UM PODE (01/09/2026)
#
# Pedido do auditor, por controle interno, e a primeira aplicação é a seção de
# ENVIO MANUAL de arquivo. Ela é o único caminho em que a pessoa escolhe tudo (o
# @, a data, o ciclo e o número da tela), então é onde a discricionariedade é
# máxima; no resto da tela o programa descobre sozinho. Por isso ela passa a
# exigir papel de coordenação.
#
# AUTORIZAÇÃO POR IDENTIDADE, e não por senha da seção. Decisão dele entre as
# duas. Senha compartilhada não identifica ninguém: o registro passaria a dizer
# "alguém que sabia a senha", e é justamente o registro que dá sentido ao
# controle. Com identidade, quem envia fica gravado com e-mail verificado.
#
# A LISTA VEM DE CONFIGURAÇÃO, uma variável de ambiente por papel, porque o SSO
# da empresa ainda não expõe grupos. Quando expuser, só esta parte muda: quem
# chama pergunta "tem esse papel?" e não sabe de onde veio a resposta.
PAPEL_COORDENACAO = "coordenação"
PAPEL_SUPERVISAO = "supervisão"


def _emails_da_variavel(nome):
    return [e.strip().lower()
            for e in (os.environ.get(nome) or "").split(",") if e.strip()]


EMAILS_POR_PAPEL = {
    PAPEL_COORDENACAO: _emails_da_variavel("EMAILS_COORDENACAO"),
    PAPEL_SUPERVISAO: _emails_da_variavel("EMAILS_SUPERVISAO"),
}

# Chave de escape para TESTE, e ela grita na tela quando está ligada.
#
# Existe porque a alternativa era pior: sem login configurado, como hoje em
# localhost, a seção ficaria intransitável e não daria para testar nem para usar
# na instalação local que o auditor citou como plano B se o Compliance não
# liberar a plataforma. Com a chave, o trabalho não trava e a tela deixa claro
# que ali NÃO há prova de identidade.
LIBERAR_PAPEL_SEM_LOGIN = os.environ.get(
    "LIBERAR_PAPEL_SEM_LOGIN", "0") not in ("0", "false", "False")


def papeis_de(email):
    """Papéis daquele e-mail, pela configuração. Conjunto vazio se não tem
    nenhum, que é o caso da maioria das pessoas."""
    alvo = str(email or "").strip().lower()
    if not alvo:
        return set()
    return {papel for papel, emails in EMAILS_POR_PAPEL.items() if alvo in emails}


def autorizacao_para(papel):
    """Se quem está usando pode agir naquele papel.

    Devolve (pode, motivo, sem_prova_de_identidade). O terceiro valor é o que a
    tela usa para avisar em vermelho: ele é True quando a liberação veio da
    chave de teste, e não de alguém autenticado.

    FALHA FECHADA, igual à porta de entrada: na dúvida, não libera. Aqui negar
    indevidamente custa um pedido à coordenação, e liberar indevidamente custa
    material entrando na auditoria sem quem responda por ele."""
    if login_configurado() and esta_logado():
        email = email_de_quem_entrou()
        if papel in papeis_de(email):
            return True, "", False
        if not EMAILS_POR_PAPEL.get(papel):
            return (False,
                    f"Ninguém está configurado com o papel de {papel} neste servidor. "
                    f"Quem cuida dele precisa preencher a lista de e-mails desse papel. "
                    f"O porquê está em `acesso.py`.",
                    False)
        return (False,
                f"Esta parte é de {papel}. Você entrou como **{email}**, que não tem "
                f"esse papel. Isso é controle interno, não desconfiança: aqui a pessoa "
                f"escolhe o influenciador, a data e o ciclo à mão, então quem faz "
                f"precisa poder responder por isso.",
                False)

    if LIBERAR_PAPEL_SEM_LOGIN:
        return (True,
                f"Liberado sem login por configuração de teste. **Não há prova de quem "
                f"está usando**, então o que for enviado aqui fica registrado com o "
                f"usuário do computador, e não com uma pessoa. Em uso de verdade, esta "
                f"parte é de {papel}.",
                True)

    return (False,
            f"Esta parte é de {papel} e depende do login, que não está configurado "
            f"neste servidor. Sem saber quem está usando, o programa não tem como "
            f"registrar quem enviou o material, e é esse registro que dá sentido ao "
            f"controle. Para liberar durante teste, existe `LIBERAR_PAPEL_SEM_LOGIN`, "
            f"e a tela avisa quando ela está ligada.",
            False)


def autorizacao_para_qualquer(*papeis):
    """Se quem está usando pode agir em QUALQUER UM destes papéis (15/09/2026).

    Existe para quando mais de um papel cobre a mesma ação, por exemplo
    "supervisão ou coordenação" na correção do cadastro. Mesmo formato de
    autorizacao_para: (pode, motivo, sem_prova_de_identidade). Confere cada
    papel na ordem dada e libera assim que um deles aceitar.

    Quando nenhum aceita, reaproveita o motivo do primeiro papel checado
    (mesma explicação de fundo: login, configuração, ou falta de papel), só
    trocando o nome do papel citado pela lista dos aceitos, para não
    duplicar as três explicações de autorizacao_para."""
    primeiro_motivo, primeiro_sem_prova = None, False
    for papel in papeis:
        pode, motivo, sem_prova = autorizacao_para(papel)
        if pode:
            return pode, motivo, sem_prova
        if primeiro_motivo is None:
            primeiro_motivo, primeiro_sem_prova = motivo, sem_prova
    nomes = " ou ".join(papeis)
    motivo_combinado = primeiro_motivo.replace(papeis[0], nomes, 1)
    return False, motivo_combinado, primeiro_sem_prova


def dominio_de(email):
    """O que vem depois do @, em minúsculas. Devolve None se não houver."""
    texto = str(email or "").strip().lower()
    if texto.count("@") != 1:
        return None
    dominio = texto.split("@")[1]
    return dominio or None


def pode_entrar(email):
    """Quem pode usar a ferramenta, entre os que conseguiram se autenticar.

    A lista de e-mails, quando existe, manda: é a permissão mais específica.
    Sem ela, vale o domínio. Sem os dois, ninguém entra.

    O "sem os dois" mudou em 31/08/2026. Antes devolvia True, o que era
    aceitável enquanto o provedor previsto era o Entra ID da empresa, que já não
    deixa entrar quem é de fora. Com a conta Google, o provedor é global, e um
    padrão permissivo aceitaria qualquer conta do mundo numa ferramenta que
    guarda credencial de escopo amplo."""
    texto = str(email or "").strip().lower()
    if not texto:
        return False
    if LISTA_DE_PERMISSAO:
        return texto in LISTA_DE_PERMISSAO
    dominio = dominio_de(texto)
    if not dominio:
        return False
    return dominio in DOMINIOS_AUTORIZADOS


def escuta_a_rede():
    """Se a tela é alcançável de fora desta máquina.

    É metade da combinação perigosa, e a que costuma mudar sem ninguém
    lembrar da outra metade."""
    try:
        endereco = st.get_option("server.address")
    except Exception:
        endereco = None
    # Sem endereço definido, o Streamlit escuta em todas as interfaces, que é
    # justamente o caso a tratar como exposto.
    if not endereco:
        return True
    return str(endereco) not in ("127.0.0.1", "localhost", "::1")


def exigir_login():
    """Porta de entrada. Chamada uma vez, em painel.py, antes de qualquer aba.

    Com login configurado, interrompe a página até a pessoa entrar. Sem login
    configurado, deixa passar, mas avisa quando a combinação é a perigosa."""
    if not login_configurado():
        if escuta_a_rede():
            # Aqui o programa PARA de propósito. É o único caso em que travar é
            # melhor que avisar: com a tela na rede e sem login, qualquer pessoa
            # que alcance o endereço usa as credenciais que estão no servidor.
            st.error(
                "**O programa está acessível pela rede e não tem login.**\n\n"
                "Nesta situação, qualquer pessoa que alcance este endereço usa as "
                "credenciais do Google e a conta do Instagram que estão neste "
                "servidor, sem precisar provar quem é.\n\n"
                "Duas saídas, e as duas estão descritas em `acesso.py`: configurar "
                "o login em `.streamlit/secrets.toml`, ou voltar a escutar só em "
                "`127.0.0.1` no `.streamlit/config.toml`."
            )
            st.stop()
        return  # máquina de trabalho, escutando só ela mesma: segue como hoje

    if not esta_logado():
        # Título trocado em 01/09/2026: dizia "Auditoria de Influenciadores", e a
        # ferramenta passa a ser do Marketing de influência. O nome da área
        # deixou de aparecer na tela de entrada.
        st.title("Monitoramento de Influenciadores")
        st.write("Entre com a sua conta da empresa para usar a ferramenta.")
        st.button("Entrar", type="primary", on_click=st.login)
        st.stop()

    email = email_de_quem_entrou()
    if not pode_entrar(email):
        if not LISTA_DE_PERMISSAO and not DOMINIOS_AUTORIZADOS:
            # Falha fechada, e a mensagem precisa dizer que o problema é de
            # configuração deste servidor, não da conta de quem tentou entrar.
            # Sem isso a pessoa vai procurar a Auditoria por um erro que está
            # numa variável de ambiente.
            st.error(
                "**Este servidor não tem ninguém liberado para entrar.** Não há "
                "lista de e-mails nem domínio autorizado configurado, e nesse "
                "caso o programa não deixa ninguém passar, de propósito.\n\n"
                "Quem cuida do servidor precisa definir `EMAILS_AUTORIZADOS` ou "
                "`DOMINIOS_AUTORIZADOS`. O porquê está em `acesso.py`."
            )
        else:
            # Não cita mais a Auditoria Interna (01/09/2026): a ferramenta passou
            # a ser do Marketing de influência, e mandar a pessoa procurar a área
            # errada só custa tempo dela.
            st.error(
                f"A conta **{email}** entrou, mas não está liberada para usar esta "
                f"ferramenta. Fale com quem administra o programa para ser incluída."
            )
        st.button("Sair", on_click=st.logout)
        st.stop()


# ------------------------------------------------------------------
# A BARREIRA COMO PÁGINA (31/08/2026)
#
# ACHADO NO PRIMEIRO USO REAL DO LOGIN, e revisão de código não tinha pegado.
#
# O `exigir_login` acima interrompe a página com st.stop(). Em painel.py isso
# acontece ANTES de st.navigation(), e aí o Streamlit não recebe a lista de
# abas: ele cai no menu automático, que lista o script principal e os arquivos
# da pasta pages/. Dois estragos, e o segundo é o grave:
#
#   1. a aba "Validação Regulatória" DESAPARECE, porque o arquivo dela está na
#      raiz e não em pages/. Ela só existe pela navegação declarada.
#
#   2. as páginas de pages/ são rotas próprias e continuam alcançáveis pelo
#      menu, inclusive no caso em que o programa deveria estar travado, tela na
#      rede sem login. A trava protegia a porta e deixava as janelas abertas.
#
# A correção tem duas camadas, e as duas são necessárias:
#
#   - painel.py chama st.navigation SEMPRE. Quando o acesso não está liberado,
#     a lista tem UMA página só, esta daqui, e nenhuma rota de pages/ é
#     registrada
#   - cada página chama exigir_login por conta própria, porque no menu
#     automático o Streamlit executa a página sem passar pelo painel
# ------------------------------------------------------------------

LIBERADO = "liberado"
PRECISA_ENTRAR = "precisa_entrar"
BLOQUEADO = "bloqueado"


def situacao():
    """Em que estado está o acesso, sem desenhar nada nem interromper.

    Serve para painel.py decidir a navegação antes de qualquer coisa aparecer
    na tela."""
    if not login_configurado():
        return BLOQUEADO if escuta_a_rede() else LIBERADO
    if not esta_logado():
        return PRECISA_ENTRAR
    if not pode_entrar(email_de_quem_entrou()):
        return BLOQUEADO
    return LIBERADO


def pagina_de_barreira():
    """A única página que existe quando o acesso não está liberado.

    Reaproveita exigir_login para não haver duas versões do mesmo texto: as
    mensagens e as regras continuam num lugar só."""
    exigir_login()


def botao_de_sair():
    """Desenha o botão de sair na barra lateral, quando há login."""
    if login_configurado() and esta_logado():
        with st.sidebar:
            st.button("Sair", on_click=st.logout, use_container_width=True)
