"""
Porta de entrada do programa. Este arquivo não faz trabalho nenhum: ele só
monta a barra lateral e dá nome a cada aba.

Existe porque, sem ele, o Streamlit usa o NOME DO ARQUIVO como nome da aba, e
aí a barra lateral mostrava coisas como "app validacao influenciadores". Com
st.navigation o nome da aba é escrito aqui, e os arquivos podem continuar com
nomes sem acento, que é o que não dá problema num servidor Linux.

A configuração da página (título da janela, ícone, largura) também mora só
aqui: o Streamlit aceita essa chamada uma única vez, então nenhuma das abas
pode repetir.

Rodar: py -m streamlit run painel.py
"""

# CONFIA NO CERTIFICADO DO WINDOWS, NÃO SÓ NO DA BIBLIOTECA (16/09/2026).
#
# ACHADO NA INSTALAÇÃO DA RESPONSÁVEL A AGUIAR: o login (acesso.py, via Authlib)
# falhava sempre em loop, voltando pro botão "Entrar" sem aviso nenhum na
# tela. O motivo real só apareceu no terminal:
#
#   httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify
#   failed: self-signed certificate in certificate chain
#
# É a MESMA classe de problema já documentada no requirements.txt pro
# curl_cffi: rede corporativa com inspeção de HTTPS, que troca o certificado
# de verdade do Google por um da própria empresa no meio do caminho. O
# Windows já confia nesse certificado (por isso o navegador funciona normal),
# mas o httpx usa uma lista de certificados própria (certifi), que não inclui
# o certificado da empresa, e recusa a conexão.
#
# `truststore` faz o `ssl` do Python usar o MESMO repositório de certificados
# do Windows, em vez do embutido na biblioteca. Continua verificando
# certificado normalmente (NUNCA desligar essa verificação, é regra do
# projeto): só passa a confiar em quem o próprio Windows já confia. Precisa
# rodar antes de qualquer chamada HTTPS do programa, por isso é a primeira
# coisa deste arquivo, antes até do import do Streamlit.
import ssl  # noqa: F401  (garante que o módulo ssl já existe antes do patch)
import truststore

truststore.inject_into_ssl()

import streamlit as st

# Nome da janela trocado em 01/09/2026, por decisão do auditor: a ferramenta
# passa a ser do Marketing de influência, então o nome da área da Auditoria saiu
# daqui, do rótulo acima dos títulos (ver estilo.cabecalho) e da tela de entrada.
# Se o Marketing preferir outro nome, é só trocar nestes três lugares.
st.set_page_config(
    page_title="Monitoramento de Influenciadores",
    page_icon=":material/fact_check:",
    layout="wide",
)

import estilo

# A identidade visual é aplicada aqui, antes das abas, para valer nas três.
# Cores e fontes vêm do design system do EGB, não foram escolhidas no programa.
estilo.aplicar()

# QUEM PODE ABRIR, antes de qualquer coisa (30/08/2026).
#
# Na máquina de trabalho, escutando só em 127.0.0.1, isto não faz nada e o
# programa segue como sempre. No servidor, ou exige o login da conta da
# empresa, ou trava a tela dizendo o que falta configurar. O porquê da regra
# está em acesso.py.
import acesso

# A NAVEGAÇÃO É DECLARADA SEMPRE, e isso mudou em 31/08/2026 depois do primeiro
# uso real do login. Antes o exigir_login interrompia a página aqui, antes do
# st.navigation, e o Streamlit caía no menu automático da pasta pages/, com as
# páginas de pages/ alcançáveis por rota própria, sem passar por esta porta. O
# raciocínio inteiro está em acesso.py.
situacao_do_acesso = acesso.situacao()

if situacao_do_acesso != acesso.LIBERADO:
    # Uma página só. Nenhuma rota de pages/ é registrada, então não há por onde
    # entrar de lado.
    st.navigation([
        st.Page(acesso.pagina_de_barreira, title="Entrar", icon=":material/lock:", default=True),
    ]).run()
    st.stop()

# Quem está usando. Fica aqui, e não dentro de cada aba, porque a barra
# lateral é a única parte da tela que as três compartilham. Não é login, é
# nome declarado; o porquê de existir está em identidade.py.
import identidade

identidade.campo_na_barra_lateral()
acesso.botao_de_sair()

# A ORDEM É A DA DEPENDÊNCIA DE DADOS, e não uma preferência: Downloads escreve
# na Monitoramento, que é o registro (e, desde 14/09/2026, também onde se
# acompanha a análise e se tira algo dela, ver pages/2_Monitoramento.py), e o
# Financeiro lê o registro para fechar o ciclo contra o escopo. Ninguém
# consegue usar uma aba antes de a anterior ter rodado, então a barra lateral
# conta a mesma história que o programa faz. O fluxo virou este em 28/08/2026, e
# o Financeiro entrou no fim dele em 03/09/2026.
#
# A TELA "VALIDAÇÃO REGULATÓRIA" SAIU DAQUI EM 14/09/2026 (era
# app_validacao_influenciadores.py, arquivo apagado). O motor de análise
# (pipeline_influenciadores.py + trabalhador.py) roda fora do Streamlit e
# continua sozinho: o download já encadeia análise automaticamente. A única
# coisa que só a tela fazia, escolher manualmente o que analisar, deixou de
# ser necessária por isso, e o pouco que sobrava de essencial (acompanhar,
# tirar da análise, tentar de novo) migrou para dentro do Monitoramento, de
# forma mais simples.
#
# AS SEÇÕES ENTRARAM EM 03/09/2026, e o motivo é que a lista corrida misturava
# duas coisas de natureza diferente: quatro passos do trabalho do dia e uma tela
# de consulta. O Cadastro estar por último já estava certo, mas nada na tela
# dizia por quê, e aí a posição dele parecia arbitrária para quem abre o
# programa pela primeira vez. Com a seção, a ordem para de depender de o leitor
# adivinhar o critério.
abas = {
    "Fluxo do dia": [
        st.Page("pages/1_Downloads_e_Organizacao.py",
                title="Downloads", icon=":material/download:", default=True),
        # UPLOADS ENTROU EM 23/09/2026, separada de Downloads: aqui ficam as
        # três formas de entrar com material sem o programa ir buscar
        # sozinho (vídeo bruto, link só para registrar, envio de arquivo já
        # baixado). Fica entre Downloads e Monitoramento porque, como
        # Downloads, é material chegando antes da validação.
        st.Page("pages/5_Uploads.py",
                title="Uploads", icon=":material/upload:"),
        st.Page("pages/2_Monitoramento.py",
                title="Monitoramento", icon=":material/table_rows:"),
        # A EDIÇÃO DE CRONOGRAMA E PAGAMENTO TEVE TELA PRÓPRIA POR UM DIA
        # (04/09/2026) E FOI ABSORVIDA PELO FINANCEIRO (05/09/2026). Ela saiu do
        # Monitoramento, que voltou a ser só leitura, e por um dia ficou numa
        # página separada. O auditor perguntou se não dava para juntar com o
        # Financeiro sem ficar confuso, e dava: o fluxo real é olhar os posts,
        # marcar o que mudou, ver escopo contra entrega e fechar, tudo sobre o
        # mesmo influenciador e o mesmo ciclo. Uma tela a menos, e o passo de
        # marcar deixou de exigir troca de página no meio do trabalho.
        st.Page("pages/3_Financeiro.py",
                title="Financeiro", icon=":material/payments:"),
    ],
    # Só leitura, acrescentada em 31/08/2026. Quem abre o programa vem baixar ou
    # validar; aqui se vem tirar dúvida de contrato ou de escopo.
    "Consulta": [
        st.Page("pages/4_Cadastro_de_Influenciadores.py",
                title="Cadastro", icon=":material/badge:"),
    ],
}

st.navigation(abas).run()
