# -*- coding: utf-8 -*-
"""
Lógica pura (sem Streamlit) do fluxo de download e organização de vídeos de
influenciadores — mesma filosofia do pipeline_influenciadores.py: o app e a
linha de comando usam EXATAMENTE o mesmo código.

FASE 2 (atual): fila e organização em ambiente de teste real, mas ainda
isolado de qualquer coisa do Marketing:
  - fila = planilha de TESTE "TESTE - Fila de Downloads - Não Usar";
  - "Drive" = pasta de TESTE de verdade no Google Drive, criada por este
    app (token de escopo drive.file), com a estrutura <influenciador>/
    Ciclo <N>/ (espelhando por ciclo como o Marketing usa);
  - pasta monitorada = teste_watch_folder/downloads_simulado (continua local,
    simulando a pasta Downloads real da máquina do Marketing).

Estágio A: baixa o link da fila (yt-dlp); tenta anônimo primeiro e, se tiver
cookies configurados (ver ARQUIVO_COOKIES/NAVEGADOR_COOKIES), também tenta
logado — importante pra Stories, que o Instagram só mostra pra quem está
logado. O que mesmo assim a plataforma bloquear vira "BAIXAR MANUALMENTE".
Estágio B: reconhece arquivos largados na pasta monitorada pelo padrão de
nome, descobre o ciclo pela Monitoramento e organiza sozinho.
"""
import csv
import http.cookiejar
import os
import re
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.append(BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import trava

PASTA_TESTE = os.path.join(BASE, "teste_watch_folder")
PASTA_MONITORADA = os.path.join(PASTA_TESTE, "downloads_simulado")
ARQUIVO_FILA_ID = os.path.join(PASTA_TESTE, "fila_downloads_id.txt")
ARQUIVO_LOG = os.path.join(PASTA_TESTE, "log_fluxo_completo.csv")

DRIVE_TESTE_RAIZ_NOME = "TESTE - Drive Downloads Influenciadores - Não Usar"
ARQUIVO_DRIVE_RAIZ_ID = os.path.join(PASTA_TESTE, "drive_teste_pasta_raiz_id.txt")

# ESCRITA NOS SISTEMAS REAIS DO MARKETING (08/09/2026)
#
# Até aqui a escrita ia sempre para o id que estivesse nos dois arquivos
# acima, e não havia NENHUMA checagem própria no caminho: se um id apontasse
# para a Monitoramento ou o Drive real do Marketing, o programa escreveria lá
# sem perguntar nada. A proteção inteira era disciplina de qual id estava
# escrito no arquivo.
#
# Combinado com o Marketing em 08/09/2026: o programa PODE passar a escrever
# de verdade, quando a analista instalar e usar. Por isso são TRÊS arquivos
# para ligar isso, não um, e os três moram fora de `teste_watch_folder` de
# propósito, porque misturar id de produção dentro de uma pasta chamada
# "teste" é o tipo de armadilha que este projeto já pagou caro por outras
# vezes. Faltando qualquer um dos três, cai sempre em teste, sem avisar: o
# padrão seguro é o de hoje, e só muda por decisão explícita, não por
# arquivo esquecido pela metade.
PASTA_PRODUCAO_MARKETING = os.path.join(BASE, "marketing_producao")
ARQUIVO_MONITORAMENTO_REAL_ID = os.path.join(
    PASTA_PRODUCAO_MARKETING, "monitoramento_id.txt")
ARQUIVO_DRIVE_RAIZ_REAL_ID = os.path.join(
    PASTA_PRODUCAO_MARKETING, "drive_pasta_raiz_id.txt")
# O NOME DO ARQUIVO É A PRÓPRIA CONFIRMAÇÃO, de propósito: alguém olhando a
# pasta pelo Explorer, sem abrir nada, já vê o que está ligado ali.
ARQUIVO_AUTORIZACAO_ESCRITA_REAL = os.path.join(
    PASTA_PRODUCAO_MARKETING,
    "AUTORIZO_ESCREVER_NOS_SISTEMAS_REAIS_DO_MARKETING.txt")


def modo_real_autorizado():
    """Se o programa está autorizado a escrever nos sistemas REAIS do
    Marketing, em vez da cópia de teste.

    Só True com os três presentes: o arquivo de autorização (a existência
    dele já basta, o conteúdo não importa) e os dois identificadores reais
    preenchidos. Ver o comentário acima de PASTA_PRODUCAO_MARKETING para o
    porquê de três em vez de um."""
    if not os.path.isfile(ARQUIVO_AUTORIZACAO_ESCRITA_REAL):
        return False
    return bool(ler_identificador(ARQUIVO_MONITORAMENTO_REAL_ID)) and \
        bool(ler_identificador(ARQUIVO_DRIVE_RAIZ_REAL_ID))


def ler_identificador(caminho):
    """Lê de um arquivo o identificador de uma planilha ou de uma pasta do Drive.

    EXISTE POR CAUSA DE UM DEFEITO REAL (31/08/2026), e o defeito é invisível:
    arquivo gravado pelo PowerShell ou pelo Bloco de Notas ganha uma marca de
    codificação no começo (o BOM). O Python entrega essa marca como parte do
    texto, e `.strip()` NÃO a remove, porque ela não é espaço em branco.

    O sintoma foi um 404 do Google com o endereço trazendo `%EF%BB%BF` antes do
    identificador, e a mensagem de erro na tela apontava para falta de
    permissão, que era a pista errada. Custou tempo justamente porque o
    caractere não aparece em lugar nenhum.

    E ISSO ERA UMA ARMADILHA ARMADA, não um acidente isolado: o procedimento
    documentado para apontar o programa para outra planilha é reescrever esses
    arquivos, e reescrever no Windows é exatamente o que cria a marca. Os quatro
    leitores usavam utf-8 puro. O projeto já havia aprendido isso em 30/08, e
    está escrito em `baixador_local/baixador.py`, mas a lição não tinha chegado
    aqui.

    Devolve None quando o arquivo não existe ou está vazio, para quem chama
    poder explicar o que falta em vez de tentar usar um identificador vazio."""
    if not os.path.exists(caminho):
        return None
    try:
        with open(caminho, "r", encoding="utf-8-sig") as f:
            texto = f.read()
    except OSError:
        return None
    # O lstrip por cima do utf-8-sig cobre o arquivo que foi regravado por cima
    # de outro e ficou com a marca fora do primeiro byte.
    return texto.replace("﻿", "").strip() or None

# O DESTINO DE VERDADE É A PASTA NO GOOGLE DRIVE. A cópia local abaixo é só um
# espelho de teste, para conferir os arquivos na máquina sem abrir o navegador.
# Ela não faz parte do fluxo: nada lê dela, nada depende dela.
#
# No servidor precisa estar DESLIGADA, e não só por arrumação: lá o disco é
# compartilhado, e guardar uma segunda cópia dos vídeos ocupa espaço à toa e
# espalha material que já está no Drive por mais um lugar.
#
# DESLIGADA POR PADRÃO DESDE 30/08/2026, por decisão do auditor.
#
# O que pesou foi a medição: 495 MB acumulados em poucos dias, com uma pessoa
# só usando. No servidor, com cinco, é dobrar o consumo de disco para guardar
# de novo o que já está no Drive. E disco cheio no meio de um lote é o tipo de
# falha que não avisa antes.
#
# Ligar de volta é COPIA_LOCAL_DE_TESTE=1, sem mexer no código. Vale quando
# alguém estiver conferindo arquivo por arquivo na máquina.
MANTER_COPIA_LOCAL_DE_TESTE = os.environ.get("COPIA_LOCAL_DE_TESTE", "0") not in ("0", "false", "False")
DRIVE_SIMULADO = os.path.join(PASTA_TESTE, "drive_simulado")

# Autenticação opcional pro download (só entra em jogo pra links que o modo
# anônimo não consegue, ex: Stories do Instagram). Decisão do usuário
# (24/08/2026): usar a sessão de uma conta real assumindo o risco de ToS
# descrito na conversa — a conta usada pode ser desafiada/restrita pelo
# Instagram por comportamento automatizado.
# Prioridade: 1) arquivo de cookies exportado (ARQUIVO_COOKIES, formato
# Netscape/cookies.txt — mais portátil, funciona também num servidor sem
# navegador); 2) navegador instalado nesta máquina (NAVEGADOR_COOKIES).
# NUNCA versionar o arquivo de cookies — é equivalente a uma senha.
ARQUIVO_COOKIES = os.path.join(PASTA_TESTE, "cookies_instagram.txt")

# Firefox, e não Chrome (corrigido em 30/08/2026). Medido em 29/08: Chrome e
# Edge, da versão 127 em diante, cifram os cookies de um jeito que impede a
# leitura por fora, e nesta máquina o Chrome nem deixa copiar o banco. O
# Firefox não faz isso. Num servidor não há navegador nenhum, e aí o programa
# usa o arquivo (ver _opcoes_cookies).
NAVEGADOR_COOKIES = "firefox"

# Com que navegador o programa se apresenta ao Instagram. Tem que ser o mesmo
# de onde vêm os cookies, e é Firefox desde 30/08/2026 (ver acima).
#
# POR QUE ISTO EXISTE (22/09/2026): estava incoerente, e a incoerência é o que
# denuncia. Medido nesta data: o download dizia ser Chrome 146, o instaloader
# dizia ser Chrome 142 no Linux, e os cookies vinham de um Firefox no Windows.
# Sessão de Firefox chegando com cara de Chrome é justamente o tipo de
# contradição que um sistema antiautomação procura, porque navegador de gente
# não faz isso. Agora as três frentes contam a mesma história.
#
PERFIL_DE_DISFARCE = "firefox"

# O que o perfil de disfarce manda sozinho, MEDIDO em 22/09/2026 contra um
# servidor local, não copiado de lugar nenhum. Serve de reserva: é o que vale
# quando não há Firefox instalado para consultar, como num servidor.
IDENTIFICACAO_DO_DISFARCE = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:147.0) "
    "Gecko/20100101 Firefox/147.0"
)


def _versao_do_firefox_instalado():
    """Versão principal do Firefox desta máquina, ou None. Não abre o navegador."""
    for caminho in (r"C:\Program Files\Mozilla Firefox\application.ini",
                    r"C:\Program Files (x86)\Mozilla Firefox\application.ini"):
        try:
            with open(caminho, encoding="utf-8", errors="replace") as arquivo:
                for linha in arquivo:
                    if linha.lower().startswith("version="):
                        return linha.split("=", 1)[1].strip().split(".")[0]
        except OSError:
            continue
    return None


def _montar_identificacao_do_navegador():
    """Com que navegador o programa se apresenta, dizendo o da própria máquina.

    POR QUE ISTO NÃO É UM TEXTO FIXO (22/09/2026): o perfil de disfarce
    disponível é de Firefox no **macOS**, e as máquinas são Windows. Conferido
    nas versões instalada (curl_cffi 0.15.0) e mais nova (0.16.3) da
    biblioteca: NENHUMA traz Firefox no Windows, então atualizar não resolve.
    Ficaria dizendo macOS numa máquina Windows, com cookies criados por um
    Firefox de Windows, e o Instagram guarda o navegador de quem fez o login.

    A parte que a biblioteca decide, a forma como a conexão segura é aberta,
    continua sendo a do perfil dela. Mas o que vai ESCRITO dá para acertar, e
    é o que se faz aqui: lê a versão do Firefox instalado e monta o texto dele.

    O FORMATO FOI MEDIDO, não deduzido: em 22/09/2026 o Firefox desta máquina
    foi aberto sem janela contra um servidor local e mandou
    `Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101
    Firefox/155.0`, enquanto o arquivo de instalação dizia `Version=155.0.1`.
    Daí o formato abaixo: só o número principal, sempre seguido de `.0`. O
    `Windows NT 10.0` é assim mesmo em Windows 11, o Firefox congelou esse
    pedaço de propósito, e a máquina medida era Windows 11.

    Cada máquina passa a dizer o Firefox DELA, que é o certo: as instalações
    têm versões diferentes entre si."""
    if os.name == "nt":
        versao = _versao_do_firefox_instalado()
        if versao:
            return (f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{versao}.0) "
                    f"Gecko/20100101 Firefox/{versao}.0")
    return IDENTIFICACAO_DO_DISFARCE


IDENTIFICACAO_DO_NAVEGADOR = _montar_identificacao_do_navegador()
# Nome de usuário da conta dona dos cookies acima. O instaloader só se
# considera logado se esse campo estiver preenchido (`is_logged_in` é
# literalmente `bool(username)`), e chamada anônima tem limite bem mais
# rígido que chamada autenticada — deixar isso vazio foi o que fez as
# primeiras tentativas saírem como anônimas e baterem em 429 rápido.
# Precisa bater com a conta dona do arquivo de cookies acima: sempre que o
# cookie for trocado, trocar este nome junto (confirmado por test_login() em
# 26/08/2026).
# PRECISA bater com a conta de onde os cookies foram exportados. Se não bater,
# a biblioteca trata a sessão como ANÔNIMA sem avisar, e os limites do
# Instagram ficam muito mais duros. Foi o que provavelmente causou o primeiro
# bloqueio, em 25/08/2026.
#
# SAIU DO CÓDIGO EM 02/09/2026, E ISSO ERA UM ACIDENTE ESPERANDO ACONTECER.
#
# O comentário acima já dizia: "Se mais de uma pessoa for usar o programa, isso
# deveria sair do código e virar configuração por pessoa". Encontrado ao preparar
# a instalação na máquina da primeira colaboradora: o nome estava escrito fixo, e
# na máquina dela apontaria para a conta de OUTRA pessoa.
#
# O estrago não seria um erro na tela, seria pior. Com o nome errado, a sessão
# dela seria tratada como anônima, os limites ficariam muito mais duros, e a
# conta dela correria o risco de bloqueio pelo mesmo caminho de 25/08/2026, sem
# nada avisando.
#
# A ORDEM: arquivo, depois variável, depois o valor antigo como último recurso.
# O arquivo vem primeiro porque é o padrão do projeto para configuração por
# máquina (ver os quatro identificadores de planilha). O valor antigo continua
# como reserva para não quebrar a máquina de origem, e verificar_ambiente.py
# MOSTRA qual conta está valendo, para quem instala perceber na hora se está
# usando a conta de outra pessoa.
ARQUIVO_CONTA_INSTAGRAM = os.path.join(PASTA_TESTE, "conta_instagram.txt")
USUARIO_DOS_COOKIES = (
    ler_identificador(ARQUIVO_CONTA_INSTAGRAM)
    or os.environ.get("USUARIO_INSTAGRAM")
    or "candyboxconfeitaria"
)

# O Instagram identifica perfil por um número interno que nunca muda. Descobrir
# esse número a partir do @ passa por um endereço que o Instagram limita com
# muito rigor (foi ele, e só ele, que ficou travado horas nos testes de
# 25/08/2026). Por isso guardamos o número aqui: descobre uma vez por
# influenciador, reusa pra sempre, e o caminho travado deixa de ser usado.
ARQUIVO_USERIDS = os.path.join(PASTA_TESTE, "instagram_userids.json")

# Monitoramento de TESTE (cópia vazia da planilha do Marketing, no Drive).
# Cada vídeo organizado vira uma linha nela, com o link do Drive na coluna
# LINK. A planilha real do Marketing continua intocada.
ARQUIVO_MONITORAMENTO_ID = os.path.join(PASTA_TESTE, "monitoramento_teste_id.txt")
ABA_MONITORAMENTO = "Monitoramento"

# Vocabulários lidos das próprias listas de seleção da planilha do Marketing,
# pra escrever exatamente o que eles escrevem. Repare que os meses pulam a
# letra K: novembro é "L NOVEMBRO" e dezembro "M DEZEMBRO".
MARCAS = ["EDS", "LOTTU", "ONA", "EDSCAP"]
ROTULO_MARCA = {"EDS": "EDS", "LOTTU": "LOTTU", "ONA": "Onabet", "EDSCAP": "EDSCAP"}
TIPOS = ["STORIES", "FEED", "X/TWITTER", "LIVE", "REELS", "SOCIAL", "YOUTUBE",
         "GRAVAÇÃO/DIÁRIA", "TIKTOK", "COLLAB", "TRÁFEGO", "THREADS"]

# Tipos oferecidos no registro de link de vídeo que não é baixado (ver
# registrar_link_externo). Fica de fora tudo que é do Instagram (STORIES, FEED
# e REELS), porque esse caminho existe justamente pro que vem de fora dele, e
# também os rótulos que não descrevem um vídeo em si (SOCIAL, COLLAB,
# TRÁFEGO). Oferecer opção que nunca cabe ali só atrapalha quem preenche.
#
# THREADS ENTROU EM 04/09/2026, a pedido do auditor. Mesma categoria de
# X/TWITTER e TIKTOK: rede social de fora do Instagram, cuja peça só é
# registrada, nunca baixada nem validada pela régua da portaria (ver
# escopo_e_entrega.TIPOS_NAO_VALIDAVEIS).
TIPOS_VIDEO_EXTERNO = ["YOUTUBE", "LIVE", "GRAVAÇÃO/DIÁRIA", "TIKTOK",
                      "X/TWITTER", "THREADS"]
MESES = ["A JANEIRO", "B FEVEREIRO", "C MARÇO", "D ABRIL", "E MAIO", "F JUNHO",
         "G JULHO", "H AGOSTO", "I SETEMBRO", "J OUTUBRO", "L NOVEMBRO", "M DEZEMBRO"]

# Colunas da Monitoramento que a automação preenche (1 = coluna A).
#
# HORAS_LIVE (coluna U, 21) ENTROU EM 04/09/2026, e é uma exceção de propósito
# à regra geral. O comentário de registrar_na_monitoramento já dizia: "só o que
# a automação não tem de onde tirar continua vazio: cronograma, pagamento,
# horas de live e observação". Isso continua verdade para os outros três, mas
# deixou de valer para horas de live no registro de LINK EXTERNO: ali a pessoa
# já digita o tipo à mão, e quando o tipo é LIVE ela também sabe quantas horas
# durou, porque acabou de assistir ou de receber o aviso do influenciador. Sem
# campo pra isso, a informação existia na cabeça de quem registrava e se perdia
# no caminho até a planilha.
# CRONOGRAMA E PAGAMENTO SÃO PREENCHIDAS À MÃO, NA PLANILHA (05/09/2026).
#
# Por um dia o programa gravou PAGAMENTO como "Pendente" ao criar a linha, e
# ofereceu edição das duas colunas por tela. O auditor decidiu voltar atrás:
# "CRONOGRAMA e PAGAMENTO continuam manuais na planilha nas linhas individuais,
# cada entrega de video por enquanto vai continuar sendo preenchida a mão como
# não pago ou pago, cronograma sim ou não".
#
# Então a automação NÃO escreve nenhuma das duas, em nenhum momento. Elas
# continuam no COL_MON abaixo, porque o programa LÊ as duas para mostrar (na
# tabela do Monitoramento e na contagem do Financeiro), e ler não é escrever.
#
# A DIREÇÃO DE LONGO PRAZO NÃO MUDOU: a intenção é a planilha virar banco de
# dados e o programa ser a única interface. O que mudou foi o prazo. Quando
# isso voltar, o caminho é curto, porque estas são as ÚNICAS duas colunas que
# sobram para a mão humana: o programa já preenche todas as outras ao criar a
# linha, e o trabalhador preenche o bloco de análise. Falta antes confirmar com
# o Marketing o que CRONOGRAMA significa, que segue sem resposta.

# CRONOGRAMA (Q, 17) E PAGAMENTO (S, 19) ESTÃO AQUI SÓ PARA LEITURA. Todas as
# outras chaves deste dicionário são posições onde a automação ESCREVE; estas
# duas são as únicas que ela apenas LÊ, para poder mostrá-las na tabela do
# Monitoramento e na contagem do Financeiro. Quem as preenche é uma pessoa, à
# mão, na planilha. Ver o comentário acima.
COL_MON = dict(handle=2, mes=11, ano=12, data_post=13, ciclo=14, tipo=15,
               post=16, cronograma=17, marca=18, pagamento=19, link=20,
               horas_live=21,
               # Bloco da automação, colunas W a AC (ver abaixo).
               data_download=23, situacao=24,
               validacao=25, evidencia=26, validado_em=27, marcacao=28,
               pedido_por=29, arquivo=30)

# AS COLUNAS DE CADASTRO, C a J, QUE O MARKETING PREENCHE À MÃO (02/09/2026).
#
# O auditor percebeu, olhando a planilha: "o time de marketing está preenchendo
# essa parte aqui também de acordo com a planilha dados_influ". Medido, e o
# alinhamento é EXATO, posição por posição:
#
#     Monitoramento              Dados_influ
#     B  @doinflu                B  INFLU
#     C  ID DA CONTA             C  ID_CONTA
#     D  Nº SEGUIDORES           D  NUM_SEGUIDORES
#     E  CATEGORIA               E  CATEGORIA
#     F  RESPONSÁVEL INTERNO     F  RESPONSAVEL
#     G  INICIO CONTRATO         G  INÍCIO_CONTRATO
#     H  FIM CONTRATO            H  FIM_CONTRATO
#     I  STATUS                  I  STATUS
#     J  ESCOPO                  J  ESCOPO
#
# Por isso eles copiam coluna por coluna: as duas planilhas começam iguais. O
# programa passa a fazer o mesmo, autorizado pelo auditor ("pode escrever em
# todas as colunas que conseguir, pois os dados já estão lá").
#
# POR QUE VALE MAIS QUE CONSISTÊNCIA VISUAL: duas dessas colunas alimentam achado
# que a auditoria já tem. Com INICIO e FIM CONTRATO na própria linha, conferir se
# o post caiu dentro da vigência vira comparação de colunas em vez de cruzamento
# entre planilhas. E ESCOPO na linha é a base da aba de financeiro, escopo contra
# entrega.
#
# E TEM EFEITO BOM PARA AUDITORIA: a linha passa a ser retrato do momento do
# post. Se o contrato for renovado depois, a linha antiga guarda a janela que
# valia quando a peça foi publicada, que é o que se quer num papel de trabalho.
#
# O MAPEAMENTO É POSICIONAL, e não por nome, porque quatro dos oito títulos são
# escritos diferente nas duas planilhas (ID DA CONTA x ID_CONTA, Nº SEGUIDORES x
# NUM_SEGUIDORES, RESPONSÁVEL INTERNO x RESPONSAVEL). Casar por nome deixaria
# metade de fora.
PRIMEIRA_COLUNA_CADASTRO = 3    # C
ULTIMA_COLUNA_CADASTRO = 10     # J

# GUARDA CONTRA O PIOR ERRO POSSÍVEL AQUI, que é gravar o valor de uma coluna na
# coluna de outra: escrever a data de fim de contrato dentro de ESCOPO corrompe
# dado de auditoria em silêncio, e ninguém percebe olhando a tela.
#
# Mapeamento posicional só é seguro enquanto as duas planilhas estiverem
# alinhadas. Se alguém inserir uma coluna em qualquer uma das duas, tudo desloca.
# Então antes de copiar, o programa CONFERE o alinhamento nos títulos que são
# escritos igual nas duas, e desiste de copiar se algum não bater.
TITULOS_QUE_PROVAM_ALINHAMENTO = {
    5: "CATEGORIA",       # E
    9: "STATUS",          # I
    10: "ESCOPO",         # J
}

# A Monitoramento do Marketing vai de A a V e todas as 22 colunas já têm dono
# (contrato, seguidores, cronograma, pagamento, horas de live, observação).
# Nada do que a automação produz cabia ali, então ela usa um bloco PRÓPRIO de
# colunas novas, da W em diante, acrescentado em 28/08/2026 na planilha de
# TESTE. A separação é de propósito: coluna do Marketing a automação só lê,
# coluna da automação o Marketing só lê.
#
# ANTES DE USAR NA PLANILHA REAL isso precisa de acordo com o Marketing, por
# ser mudança no FORMATO da planilha deles, não só no conteúdo.
# A coluna LINK_ARQUIVO foi RETIRADA em 29/08/2026.
#
# Ela existia para apontar o vídeo específico, porque a coluna LINK do
# Marketing aponta para a pasta do mês. Só que nas linhas criadas pela
# automação o link do arquivo já vai na própria coluna LINK, então o mesmo
# endereço aparecia duas vezes na planilha, lado a lado. Foi o auditor quem
# apontou, olhando a planilha de teste.
#
# O que ela também fazia, e precisou ser substituído: era ela o GATILHO da
# fila de validação. "Tem link de arquivo" queria dizer "há o que analisar".
# Esse papel passou para a coluna SITUACAO, que já carregava exatamente essa
# informação (ver tem_arquivo_para_analisar). Nada se perdeu, e a planilha
# deixou de repetir o mesmo endereço.
BLOCO_AUTOMACAO = [
    # (chave em COL_MON, letra, título na planilha, para que serve)
    ("data_download", "W", "DATA_DOWNLOAD",
     "quando o material foi capturado, que é diferente da data do post: "
     "conteúdo de rede social muda e some, então a data da captura é parte da "
     "evidência"),
    ("situacao", "X", "SITUACAO",
     "em que ponto do fluxo a linha está: N/A (sem arquivo para conferir), "
     "AGUARDANDO VALIDAÇÃO ou VALIDADO. É por aqui que a análise sabe em "
     "quais linhas há arquivo para conferir"),
    ("validacao", "Y", "VALIDACAO",
     "veredito da análise, juntando o que foi lido na tela e o que foi dito "
     "no áudio"),
    ("evidencia", "Z", "EVIDENCIA",
     "o que faltou e em qual arquivo. Existe para quem contestar o veredito "
     "ter como conferir"),
    ("validado_em", "AA", "VALIDADO_EM", "quando a análise rodou"),
    # ENTROU EM 01/09/2026 como ORGANICO, e VIROU MARCACAO em 03/09/2026.
    #
    # Por que a marcação existe nos DOIS lugares, pasta e coluna: pasta serve
    # para achar o arquivo olhando o Drive, e não dá para filtrar nem contar por
    # ela. É esta coluna que responde "quantos posts orgânicos entraram neste
    # ciclo", e é por ela que quem confere cota consegue separar os grupos.
    #
    # POR QUE DEIXOU DE SER SIM/VAZIO: passaram a existir três marcações
    # (orgânico ou link), definidas pelo auditor por GRAU DE PEÇA
    # PUBLICITÁRIA e não por origem. Com três, vazio deixaria de ter significado
    # próprio: não diria se a peça é link ou se ninguém marcou nada.
    #
    # As linhas gravadas até 02/09 têm "SIM" nesta coluna, e continuam sendo
    # lidas como orgânico (ver LEITURA_DA_MARCACAO). Sem isso, a marcação delas
    # se perderia sem ninguém perceber.
    #
    # O QUE ESTE CAMPO NÃO DIZ: se cada grupo conta como entrega do contrato.
    # Cortado em 01/09/2026 a pedido do auditor, e o motivo dele é direto: às
    # vezes pode estar no contrato, e isso pode mudar. Regra de contrato não é o
    # programa que decide, e afirmar regra num texto de tela ou de coluna fica
    # errado sem ninguém perceber.
    ("marcacao", "AB", "MARCACAO",
     "ORGANICO quando a peça só mostra algo da marca, sem falar de jogo e sem "
     "link, e LINK quando é a peça publicitária, que anuncia e leva o endereço "
     "da bet. Peça orgânica e peça com link no mesmo dia contam como DOIS posts, "
     "porque são entregas diferentes. É escolhido por uma pessoa na hora de "
     "baixar, então é o único campo desta faixa que não sai de um cálculo"),
    # ENTROU EM 02/09/2026, e fecha um buraco de rastro que era grave.
    #
    # O auditor propôs ligar o login à coluna RESPONSÁVEL INTERNO. Aquela coluna
    # tem outro dono: ela diz QUEM CUIDA daquele influenciador, que é a
    # atribuição de carteira e vem do cadastro. O login diz QUEM FEZ a ação.
    #
    # Nos casos normais as duas coincidem, porque quem baixa é quem cuida. Mas
    # quando divergem, a divergência é o sinal: ou alguém cobriu a colega, ou a
    # atribuição está desatualizada. Escrever o login naquela coluna faria as
    # duas serem a mesma coisa por construção, e o sinal desapareceria. Pior: a
    # coluna passaria a significar atribuição quando preenchida pelo Marketing e
    # ator quando preenchida pelo programa, e coluna com dois significados não
    # serve para achado.
    #
    # ONDE ESTAVA ANTES, e por que era falha de fundo: quem pediu cada download
    # ficava SÓ no arquivo da tarefa do trabalhador, que é o lugar mais efêmero
    # de todos. Conferido em 02/09/2026: o log não tinha campo de quem, a
    # Monitoramento não tinha coluna de ator, e a limpeza daquele dia apagou 50
    # tarefas concluídas. Ou seja, o rastro de quem pediu cada download de agosto
    # já tinha se perdido, e nada avisava. Numa ferramenta cujo propósito é
    # deixar discricionariedade rastreável, isso não pode ficar no lugar
    # temporário.
    ("pedido_por", "AC", "PEDIDO_POR",
     "quem pediu aquele download, pela identidade do login. É diferente do "
     "RESPONSÁVEL INTERNO da coluna F, que diz quem CUIDA do influenciador: "
     "comparar as duas permite achar post pedido por quem não é o responsável "
     "pela carteira, o que hoje é impossível levantar"),
    # ENTROU EM 03/09/2026, e ela é a CONSEQUÊNCIA de a coluna LINK passar a
    # apontar para a PASTA. Pedido do auditor, repassando o Marketing: "o link
    # deveria ir pra pasta onde estão os vídeos e não o link exato do vídeo. O
    # link exato do vídeo é bom para mostrar a evidência de não conformidade ou
    # conformidade na parte de validação regulatória".
    #
    # POR QUE O ARQUIVO PRECISA DE LUGAR PRÓPRIO, e não é preferência: com LINK
    # virando pasta, DUAS coisas quebrariam em silêncio.
    #
    #   1. a conferência de linha repetida comparava a coluna LINK. Com a pasta
    #      ali, a segunda peça do mesmo dia seria lida como repetida e a linha
    #      NÃO seria criada: material no Drive sem linha na planilha, que é o
    #      pior resultado possível aqui.
    #   2. a análise lê o endereço do arquivo da coluna LINK, e ela sabe abrir
    #      pasta (DRIVE_FOLDER). Com a pasta ali, cada linha do dia analisaria
    #      TODOS os arquivos do dia: quatro peças viram dezesseis análises, e o
    #      veredito de cada linha misturaria as quatro. Justamente a evidência
    #      por peça que o pedido quer preservar é que se perderia.
    #
    # ELA NÃO É A ANTIGA LINK_ARQUIVO DE VOLTA. Aquela saiu em 29/08/2026 por ser
    # cópia da coluna LINK, escrita e exibida sem nunca decidir nada. Esta existe
    # porque LINK deixou de identificar o arquivo, então a informação passou a
    # ter dois donos diferentes: a pasta é do post, o arquivo é da peça.
    ("arquivo", "AD", "ARQUIVO",
     "endereço do arquivo exato daquela peça no Drive. A coluna LINK aponta para "
     "a PASTA do post, porque entrega do mesmo dia é um post só; este é o "
     "arquivo daquela tela, e é dele que a análise tira o veredito e a "
     "evidência"),
]

# O TEXTO MUDOU DE "SEM ARQUIVO" PARA "N/A" NA PLANILHA (17/09/2026), a
# pedido do auditor: "SEM ARQUIVO" lia como defeito (algo que devia ter
# baixado e não baixou), quando na verdade é proposital (LIVE e YouTube nunca
# são baixados). O NOME PYTHON DA CONSTANTE FICOU O MESMO DE PROPÓSITO: o
# significado continua "esta linha não tem arquivo para a análise conferir",
# só o texto que aparece para humano mudou, igual já valia para
# VALIDACAO/VALIDADO_EM (que já usavam "N/A" para o mesmo caso, ver mais
# abaixo). Linha antiga que ainda tem o texto velho "SEM ARQUIVO" continua
# sendo reconhecida do mesmo jeito por `tem_arquivo_para_analisar`, ver lá.
SEM_ARQUIVO = "N/A"
AGUARDANDO_VALIDACAO = "AGUARDANDO VALIDAÇÃO"
VALIDADO = "VALIDADO"


def tem_arquivo_para_analisar(situacao):
    """Se aquela linha tem um arquivo baixado que a análise pode conferir.

    É o gatilho da fila de validação desde 29/08/2026, no lugar da antiga
    coluna LINK_ARQUIVO. A regra é: a automação escreveu alguma situação ali,
    e essa situação não é "sem arquivo" (hoje escrito como "N/A" na planilha,
    ver o comentário de SEM_ARQUIVO).

    RECONHECE OS DOIS TEXTOS, o novo e o velho (17/09/2026): linha criada
    antes da troca de texto ainda tem "SEM ARQUIVO" escrito na célula de
    verdade (a migração trocou o que já existia na cópia de teste, mas uma
    outra máquina ou uma linha fora do alcance da migração pode continuar com
    o texto antigo), e ela precisa continuar de fora da fila do mesmo jeito.

    Vale para VALIDADO também, de propósito. Sem isso, apagar a célula de
    VALIDACAO para pedir reprocessamento deixaria de funcionar, porque a linha
    continuaria marcada como validada e nunca voltaria para a fila.

    Linha do Marketing preenchida à mão tem esta coluna vazia, então continua
    fora da fila, exatamente como antes. Isso é limitação conhecida, não
    efeito desta mudança: o link dela aponta para a pasta do mês e não
    identifica o post (ver as pendências no PROMPT_CONTINUACAO)."""
    return str(situacao or "").strip() not in ("", SEM_ARQUIVO, "SEM ARQUIVO")

PRIMEIRA_COLUNA_AUTOMACAO = BLOCO_AUTOMACAO[0][1]
ULTIMA_COLUNA_MON = BLOCO_AUTOMACAO[-1][1]
# Largura da linha, em número de colunas. Sai da última entrada do bloco, e não
# de uma chave escrita à mão: quando a coluna ORGANICO entrou em 01/09/2026,
# quem estava escrito à mão era "validado_em", e a linha gravada teria ficado uma
# coluna mais curta que a faixa pedida ao Google, que é erro de API e não de dado.
LARGURA_LINHA_MON = COL_MON[BLOCO_AUTOMACAO[-1][0]]


def letra_da_coluna(numero):
    """1 vira A, 26 vira Z, 27 vira AA. Precisa passar do Z porque o bloco da
    automação chega até a AB."""
    letras = ""
    while numero > 0:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(ord("A") + resto) + letras
    return letras

# Só pra Instagram: espaça as tentativas e limita quanto processa por rodada,
# pra reduzir o quão "em rajada" o padrão de chamada parece. Decisão do
# usuário (25/08/2026) depois de um teste real ter batido rate limit (HTTP
# 429) na conta usada, após vários downloads seguidos sem pausa nenhuma.
# Faixa alargada em 29/08/2026, de 45 a 120 para 30 a 180 segundos.
#
# O raciocínio mudou. Antes a pausa era vista só como "ir mais devagar", e aí
# o que importava era o mínimo. Mas REGULARIDADE também é sinal: ninguém clica
# com precisão de relógio, e uma pausa sempre dentro da mesma faixa estreita
# desenha um padrão. Alargar sobe a média (de 82 para 105 segundos) e sobe a
# variação, que ajuda nos dois sentidos.
#
# Isso ataca o RITMO das chamadas. Não ataca o volume do dia, que é outro
# fator, nem a aparência da chamada, que é tratada em opcoes_de_disfarce.
#
# CONFIGURÁVEL POR VARIÁVEL DE AMBIENTE (11/09/2026), mesmo padrão dos três
# vizinhos abaixo. Ver o histórico do 429 de 25/08 acima antes de baixar demais
# este número: ele existe por causa daquele episódio, e é distinto do teto
# diário logo abaixo.
#
# DE 30-180 PARA 20-45 EM 11/09/2026, A PEDIDO DO AUDITOR, em duas etapas no
# mesmo dia: primeiro 15-90, e depois ele pediu "30 segundos". O que motivou foi
# o trabalho real dele: dois stories do mesmo influenciador, colados um atrás do
# outro, e o segundo vídeo demorando demais para ficar disponível para os passos
# que ele faz depois. A média cai de 105 para cerca de 32 segundos.
#
# É FAIXA, E NÃO OS 30 SEGUNDOS EXATOS QUE ELE PEDIU, pelo motivo que já está
# escrito acima e que justificou alargar a faixa em 29/08: pausa sempre igual
# desenha padrão de robô, e regularidade também é sinal. Uma faixa estreita em
# volta de 30 entrega a velocidade pedida sem virar relógio.
#
# O freio automático continua de pé: se o Instagram pedir para ir devagar, o
# programa pausa sozinho, dobra a pausa a cada reincidência e registra. Se
# aparecer sinal desses, o caminho de volta é ESTE número, e não o teto do dia:
# são fatores diferentes.
PAUSA_INSTAGRAM_MIN_SEG = int(os.environ.get("PAUSA_INSTAGRAM_MIN_SEG", "20"))
PAUSA_INSTAGRAM_MAX_SEG = int(os.environ.get("PAUSA_INSTAGRAM_MAX_SEG", "45"))
LIMITE_INSTAGRAM_POR_RODADA = int(os.environ.get("LIMITE_INSTAGRAM_POR_RODADA", "3"))

# RODADAS SEGUIDAS, SEM PEDIR CLIQUE (01/09/2026).
#
# POR QUE MUDOU: o auditor mandou 4 links, o programa processou 3, deixou 1 e
# ESPEROU UM NOVO CLIQUE. Ele pediu primeiro para subir o limite por rodada de 3
# para 5, e desistiu ao ver que 5 resolve o caso de 4 links e volta a pedir
# clique a partir de 6. O incômodo era o clique, não o número.
#
# Então o limite por rodada continua 3, porque ele controla RAJADA e isso não
# mudou de importância, e quem passou a se repetir é a rodada.
#
# A PAUSA ENTRE RODADAS É MAIOR QUE A PAUSA ENTRE LINKS, e não é enfeite: sem
# ela, encadear rodadas produziria 6 chamadas seguidas com espaçamento de rajada
# curta, que é PIOR do que simplesmente subir o limite para 5. A rodada seguinte
# tem que parecer outra sessão de trabalho, não a continuação da mesma.
PAUSA_ENTRE_RODADAS_MIN_SEG = 180
PAUSA_ENTRE_RODADAS_MAX_SEG = 420

# Rede de segurança, não regra de negócio. Uma fila que não anda nunca deveria
# chegar aqui, porque a rodada só se repete quando houve progresso; isto existe
# para o caso de algo que ninguém previu, e o programa avisa quando para por
# este motivo em vez de parar calado.
MAXIMO_RODADAS_SEGUIDAS = int(os.environ.get("MAXIMO_RODADAS_SEGUIDAS", "12"))

# Teto diário por conta e freio automático depois de um bloqueio.
#
# Por que existe: nos testes de 25 e 26/08/2026 duas contas foram sinalizadas
# pelo Instagram. O que mais pesou não foi a quantidade de vídeos, foi
# INSISTIR depois do primeiro bloqueio. Um limite temporário vira sinalização
# de conta quando o programa continua tentando. Então, ao tomar bloqueio, o
# programa para de falar com o Instagram por aquela conta e só volta depois
# do prazo abaixo, sem repetir tentativa.
#
# DE 12 PARA 20 EM 30/08/2026, PRIMEIRA ETAPA DE UMA SUBIDA MEDIDA.
#
# O 12 foi escolhido quando um story custava 3 a 4 chamadas e uma delas ia
# para a consulta por @, que é o endereço que o Instagram limita com muito
# mais rigor. Desde 29/08 o story é baixado pelo yt-dlp: são 2 chamadas e
# nenhuma naquele endereço, que sobrou só no caminho de reserva. O mesmo teto
# passou a comprar cerca do dobro de vídeos, ou seja, ficou mais conservador
# do que foi projetado para ser.
#
# O que o registro mostra sobre o dia em que a conta foi sinalizada, e que
# desfaz a leitura fácil de "34 é muito": das 34 chamadas de 25/08, apenas 10
# deram certo. As outras 24 foram falha, boa parte delas nova tentativa em
# cima de perfil sem story no ar, e três na consulta por @. Não foram 34
# downloads espaçados; foi insistência num endereço sensível.
#
# POR QUE DÁ PARA EXPERIMENTAR: porque o freio existe. Se o Instagram pedir
# para ir devagar, o programa pausa sozinho, dobra a pausa se insistir e
# registra tudo. O pior caso é uma pausa que se resolve sozinha e fica
# documentada. Antes do freio, subir seria imprudência.
#
# COMO CONTINUAR A SUBIDA, e isto é para quem vier depois: uma semana de uso
# real em 20, sem nenhum sinal de "vá devagar" no registro, autoriza ir a 30.
# Acima de 15 por dia não existe dado nenhum no regime novo, então cada etapa
# precisa da semana de observação antes da próxima. Ir direto ao volume que o
# Marketing pede (25 por pessoa por dia) seria extrapolar além de tudo o que
# se mediu.
LIMITE_DIARIO_INSTAGRAM = int(os.environ.get("LIMITE_DIARIO_INSTAGRAM", "20"))

# TETO DE FIM DE SEMANA, criado em 12/09/2026, a pedido do auditor.
#
# No plantão de sábado e domingo, UMA pessoa cobre sozinha, na própria conta,
# o que nos dias de semana seis contas dividem entre si. O teto de 20 por
# conta continua valendo de segunda a sexta; só muda no fim de semana, e só
# para a conta que estiver logada.
#
# POR QUE 30 E NÃO OUTRO NÚMERO: é ESCOLHA, não medição. É o mesmo próximo
# degrau que já estava autorizado no comentário acima desde 30/08/2026 ("uma
# semana de uso real em 20, sem nenhum sinal de 'vá devagar', autoriza ir a
# 30"), reaproveitado aqui porque nunca houve medição de volume de fim de
# semana (o que existe medido, 18 influenciadores por dia com 15 tendo story,
# é de dias úteis, 31/08 a 04/09). Continua valendo o mesmo protocolo: sem
# sinal de alerta no registro depois de alguns fins de semana em 30, subir de
# novo é decisão de quem administra a conta, não automática.
#
# O freio contra insistência (pausa que dobra, recuo em bloqueio) continua
# valendo igual, isso aqui só move o teto, não desliga proteção nenhuma.
LIMITE_DIARIO_INSTAGRAM_FIM_DE_SEMANA = int(
    os.environ.get("LIMITE_DIARIO_INSTAGRAM_FIM_DE_SEMANA", "30"))
ARQUIVO_ESTADO_CONTA = os.path.join(PASTA_TESTE, "estado_conta_instagram.json")


def limite_diario_vigente(agora=None):
    """O teto de hoje para a conta em uso. Sábado e domingo usam o teto de
    plantão; segunda a sexta usam o de sempre. Função própria (em vez de ler
    a constante direto) para não duplicar o dia-da-semana em cada lugar que
    decide o teto, e para o teste conseguir conferir o mesmo valor que a
    aplicação usa, não um número recalculado à parte.

    `agora` existe só para o teste poder simular um sábado ou domingo sem
    depender do dia real em que a bateria é rodada; a aplicação sempre chama
    sem argumento, e cai no `datetime.now()` de verdade."""
    agora = agora or datetime.now()
    return (LIMITE_DIARIO_INSTAGRAM_FIM_DE_SEMANA
            if agora.weekday() >= 5
            else LIMITE_DIARIO_INSTAGRAM)


# COMPARTILHAR A PAUSA ENTRE MÁQUINAS QUE USAM A MESMA CONTA (22/09/2026)
#
# POR QUE ISTO EXISTE: confirmado em 21/09/2026 que a conta da Responsável A é usada
# por 5 ou mais máquinas físicas, prática antiga da empresa (conta nova
# negada pela chefe dela). O teto de volume acima (LIMITE_DIARIO_INSTAGRAM)
# já não bloqueia nada desde 17/09/2026, então ele não precisa de nada disto.
# O que continua travando de verdade é a pausa depois de um bloqueio real
# (`pausada_ate`, gravada por _acionar_freio), e ela só existia no arquivo
# LOCAL de cada máquina (ARQUIVO_ESTADO_CONTA). Se o Instagram sinalizasse a
# conta numa das cinco, as outras quatro não sabiam de nada e continuavam
# batendo nela, que é o mesmo padrão que o comentário do botão "ignorar
# bloqueio" (mais abaixo) já descreve como o jeito de transformar bloqueio
# temporário em conta marcada.
#
# COMO FUNCIONA: cada pausa ou liberação vira uma LINHA NOVA numa aba própria
# (ABA_ESTADO_INSTAGRAM), nunca uma célula atualizada por cima da anterior.
# Só acrescentar evita reconstruir aqui a proteção contra corrida entre
# máquinas que registrar_na_monitoramento precisou construir em 18/09:
# sheets_client.adicionar_linhas já usa values().append(), atômico do lado do
# Google, então duas máquinas gravando quase ao mesmo tempo não se
# sobrescrevem. Para saber o estado atual de uma conta, basta olhar a linha
# mais recente dela.
#
# ONDE FICA: na MESMA planilha de fechamentos (fechamentos_planilha_id.txt),
# para não criar um sexto identificador de planilha neste projeto. A aba
# nasce sozinha na primeira gravação, mesmo padrão de
# registro_fechamentos.garantir_cabecalho.
#
# CUSTO CONTROLADO: a LEITURA da planilha só acontece a cada
# SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO, não a cada chamada de
# situacao_da_conta (que roda várias vezes por rodada). Entre uma sincronia e
# outra vale o que já está no arquivo local. Isso limita o atraso a "uma
# máquina pode demorar até um minuto para saber que outra pausou a conta",
# aceitável porque o bloqueio real dura horas.
#
# SE A PLANILHA DE FECHAMENTOS NÃO ESTIVER CONFIGURADA, este mecanismo inteiro
# fica inerte e o programa volta ao comportamento de hoje (pausa só local),
# sem avisar: mesma convenção do resto do projeto para identificador ausente.
ABA_ESTADO_INSTAGRAM = "Estado_Instagram"
SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO = 60
CAMPOS_ESTADO_INSTAGRAM = ("quando", "conta", "maquina", "evento", "pausada_ate", "motivo")
_ULTIMA_SINCRONIA_ESTADO_COMPARTILHADO = {"quando": 0.0}


def _planilha_fechamentos_id():
    import registro_fechamentos
    return registro_fechamentos.planilha_id()


def _registrar_evento_compartilhado(evento, pausada_ate="", motivo=""):
    """Acrescenta uma linha em Estado_Instagram contando o que aconteceu com
    a conta atual. Falha em silêncio: é rede de segurança além da pausa
    local, que já aconteceu antes desta chamada, então uma falha aqui não
    pode fazer parecer que o download em si falhou."""
    try:
        import registro_fechamentos
        import sheets_client
        planilha = _planilha_fechamentos_id()
        if not planilha:
            return
        registro_fechamentos.garantir_cabecalho(
            planilha, CAMPOS_ESTADO_INSTAGRAM, aba=ABA_ESTADO_INSTAGRAM)
        letra_fim = registro_fechamentos._letra(len(CAMPOS_ESTADO_INSTAGRAM))
        maquina = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or ""
        sheets_client.adicionar_linhas(
            planilha, ABA_ESTADO_INSTAGRAM, f"A:{letra_fim}",
            [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), USUARIO_DOS_COOKIES,
              maquina, evento, pausada_ate or "", str(motivo)[:200]]])
    except Exception:
        pass


def _evento_mais_recente_compartilhado(conta, eventos):
    """Lê Estado_Instagram inteira e devolve a LINHA mais recente daquela
    conta cujo evento esteja em `eventos` (ex.: ("pausa", "liberada")), ou
    None quando não há planilha configurada, não há linha nenhuma, ou a
    leitura falhou. Uma função só, reaproveitada por quem lê pausa
    (_pausa_mais_recente_compartilhada) e por quem lê uso em andamento
    (_uso_em_andamento_de_outra_maquina), em vez de repetir o mesmo laço de
    leitura duas vezes."""
    planilha = _planilha_fechamentos_id()
    if not planilha:
        return None
    try:
        import sheets_client
        linhas = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha,
                range=f"'{ABA_ESTADO_INSTAGRAM}'!A2:F20000").execute()
        ).get("values", [])
    except Exception:
        return None
    mais_recente = None
    for linha in linhas:
        if len(linha) >= 4 and linha[1] == conta and linha[3] in eventos:
            mais_recente = linha
    return mais_recente


def _pausa_mais_recente_compartilhada(conta):
    """Lê Estado_Instagram e devolve (pausada_ate, motivo) do evento mais
    recente daquela conta, ou (None, None) quando o mais recente foi uma
    liberação, ou não há planilha configurada, ou não há linha nenhuma."""
    linha = _evento_mais_recente_compartilhado(conta, ("pausa", "liberada"))
    if not linha or linha[3] != "pausa":
        return None, None
    pausada_ate = linha[4] if len(linha) > 4 else ""
    motivo = linha[5] if len(linha) > 5 else ""
    return (pausada_ate or None), motivo


def _sincronizar_pausa_compartilhada():
    """Traz para o arquivo local a pausa que OUTRA máquina registrou para
    esta mesma conta, se ela for mais restritiva que a que já havia aqui.
    Só consulta a planilha a cada
    SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO: chamar isto a cada
    situacao_da_conta() sem esse freio gastaria uma chamada de rede a cada
    link da fila, só para, na maioria das vezes, não achar nada novo."""
    import time
    agora = time.time()
    if (agora - _ULTIMA_SINCRONIA_ESTADO_COMPARTILHADO["quando"]
            < SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO):
        return
    _ULTIMA_SINCRONIA_ESTADO_COMPARTILHADO["quando"] = agora
    pausada_ate_str, motivo = _pausa_mais_recente_compartilhada(USUARIO_DOS_COOKIES)
    if not pausada_ate_str:
        return
    try:
        pausada_ate_dt = datetime.strptime(pausada_ate_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return
    with trava.travar(ARQUIVO_ESTADO_CONTA):
        estado, conta = _estado_da_conta()
        atual = conta.get("pausada_ate")
        atual_dt = datetime.strptime(atual, "%Y-%m-%d %H:%M:%S") if atual else None
        if atual_dt is None or pausada_ate_dt > atual_dt:
            conta["pausada_ate"] = pausada_ate_str
            conta["ultimo_bloqueio"] = motivo or conta.get("ultimo_bloqueio")
            conta["tipo_ultima_pausa"] = "compartilhada de outra máquina"
            _gravar_estado_conta(estado)


# CONTADOR "USADOS HOJE" SOMADO ENTRE MÁQUINAS (24/09/2026)
#
# POR QUE ISTO EXISTE: pendência levantada em 22/09 e adiada pra 23/09, que
# não deu tempo. `conta["usados"]` (o "X de Y hoje" da tela) é só desta
# MÁQUINA. Com a conta da Responsável A dividida entre 5 ou mais máquinas físicas
# (ver a decisão de negócio de 22/09, mesmo comentário do bloco de
# serialização abaixo), cada tela mostra a própria metade, achando que tem
# o teto inteiro disponível: se cinco máquinas fizerem 15 chamadas cada,
# cada uma mostra "15 de 20, restam 5" e a conta de verdade levou 75.
#
# CONTINUA SENDO RECOMENDAÇÃO, NÃO TRAVA (decisão de 17/09, mesmo motivo do
# `restantes == 0` em situacao_da_conta): o número certo importa para quem
# decide se continua ou não, não para bloquear ninguém.
#
# COMO FUNCIONA: cada chamada de verdade já grava uma linha em
# Estado_Instagram (reaproveita o mesmo mecanismo append-only da pausa
# compartilhada, evento "uso" em vez de "pausa"/"liberada"). Para saber o
# total do dia, soma quantas linhas "uso" daquela conta têm a data de hoje,
# em vez de olhar só o arquivo local. MESMO INTERVALO DE SINCRONIA da pausa
# (SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO): chamar isto a cada link
# da fila sem o freio gastaria uma leitura da planilha inteira por link.
#
# NUNCA VOLTA PRA TRÁS: o valor salvo localmente é o MAIOR entre o que já
# havia e o que a planilha soma agora, nunca o menor. Isso cobre a corrida
# entre esta própria chamada gravar sua linha e a leitura seguinte ainda não
# vê-la (é rede, o append pode não ter propagado ainda para a mesma leitura
# que o disparou).
_ULTIMA_SINCRONIA_USO_COMPARTILHADO = {"quando": 0.0}


def _uso_compartilhado_hoje(conta):
    """Quantas chamadas aquela conta já fez hoje, somando toda máquina que
    grava em Estado_Instagram. None quando a planilha de fechamentos não
    está configurada ou a leitura falhou, e quem chama cai no contador só
    local, sem avisar (mesma convenção do resto deste bloco)."""
    planilha = _planilha_fechamentos_id()
    if not planilha:
        return None
    try:
        import sheets_client
        linhas = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha,
                range=f"'{ABA_ESTADO_INSTAGRAM}'!A2:F20000").execute()
        ).get("values", [])
    except Exception:
        return None
    hoje = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for linha in linhas
              if len(linha) >= 4 and linha[1] == conta and linha[3] == "uso"
              and str(linha[0]).startswith(hoje))


def _sincronizar_uso_compartilhado():
    """Traz para o arquivo local a soma de todas as máquinas, no mesmo
    ritmo e pelo mesmo motivo de _sincronizar_pausa_compartilhada."""
    import time
    agora = time.time()
    if (agora - _ULTIMA_SINCRONIA_USO_COMPARTILHADO["quando"]
            < SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO):
        return
    _ULTIMA_SINCRONIA_USO_COMPARTILHADO["quando"] = agora
    total = _uso_compartilhado_hoje(USUARIO_DOS_COOKIES)
    if total is None:
        return
    with trava.travar(ARQUIVO_ESTADO_CONTA):
        estado, conta = _estado_da_conta()
        conta["usados"] = max(conta["usados"], total)
        _gravar_estado_conta(estado)


# SERIALIZAR O ACESSO ENTRE MÁQUINAS (22/09/2026), a segunda metade do que
# foi combinado com o auditor em 21/09 (a primeira foi a pausa compartilhada
# acima, commitada sozinha porque esta ainda não tinha sido escrita).
#
# POR QUE ISTO É DIFERENTE DA PAUSA COMPARTILHADA: a pausa só reage DEPOIS
# de o Instagram já ter sinalizado a conta. Isto age ANTES: evita que duas
# ou mais máquinas automatizem chamada na MESMA conta ao mesmo tempo, que é
# o padrão mais parecido com "conta comprometida" que existe, pior do que
# qualquer volume (investigado na mesma sessão de 21/09: o loop de captcha
# na conta da Responsável A continuou acontecendo mesmo com toda automação
# desligada, então o histórico de uso simultâneo por várias pessoas
# provavelmente pesa mais do que qualquer chamada isolada da automação).
#
# COMO: mesma aba Estado_Instagram, dois eventos novos ("inicio_uso" e
# "fim_uso"), mesmo princípio de só acrescentar linha. Quem quer falar com
# o Instagram olha a linha mais recente da conta: se for um "inicio_uso" de
# OUTRA máquina sem "fim_uso" depois, espera; senão, grava o próprio
# "inicio_uso" e segue. LIMITE DE ESPERA: dez minutos. Acima disso, trata
# como processo que caiu no meio do caminho sem gravar o fim, e segue
# mesmo assim — sem isso, uma máquina que travou deixaria as outras
# esperando pra sempre, que é pior do que o problema que isto resolve.
SEGUNDOS_ENTRE_TENTATIVAS_VEZ_DA_CONTA = 15
SEGUNDOS_LIMITE_ESPERA_VEZ_DA_CONTA = 600


def fila_tem_link_do_instagram():
    """Se a fila de downloads de agora tem algum link do Instagram. Serve só
    para decidir se vale a pena esperar a vez da conta: link de outra
    plataforma não disputa a mesma conta com ninguém, e chamar
    aguardar_vez_da_conta à toa custaria uma leitura de planilha por nada."""
    try:
        return any("instagram.com" in (item.get("link") or "") for item in ler_fila())
    except Exception:
        return True  # na dúvida, trata como se tivesse: é o lado seguro


def _uso_em_andamento_de_outra_maquina(conta):
    """Nome da máquina que está usando esta conta agora, se o evento mais
    recente dela for "inicio_uso" sem "fim_uso" depois e não for esta
    própria máquina. None quando está livre, quando a planilha não está
    configurada, ou quando a leitura falhou (na dúvida, não trava
    ninguém: é preferível arriscar a corrida rara a travar todo mundo por
    causa de uma leitura que falhou)."""
    linha = _evento_mais_recente_compartilhado(conta, ("inicio_uso", "fim_uso"))
    if not linha or linha[3] != "inicio_uso":
        return None
    maquina = linha[2]
    aqui = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or ""
    return maquina if maquina and maquina != aqui else None


def aguardar_vez_da_conta(log_fn=None):
    """Espera até nenhuma outra máquina estar com a MESMA conta em uso, antes
    de começar a falar com o Instagram.

    Devolve True se marcou que está usando (quem chamou PRECISA chamar
    liberar_vez_da_conta() depois, num finally, senão a marca fica presa até
    o limite de espera de outra máquina expirar). Devolve False quando a
    planilha de fechamentos não está configurada: nada a esperar nem a
    liberar, é o comportamento de sempre."""
    if not _planilha_fechamentos_id():
        return False
    import time
    dizer = log_fn or (lambda m: None)
    inicio = time.time()
    avisou = False
    while True:
        dono = _uso_em_andamento_de_outra_maquina(USUARIO_DOS_COOKIES)
        if not dono:
            break
        if time.time() - inicio > SEGUNDOS_LIMITE_ESPERA_VEZ_DA_CONTA:
            dizer(f"A máquina {dono} está com a conta @{USUARIO_DOS_COOKIES} "
                  f"marcada como em uso há mais de "
                  f"{SEGUNDOS_LIMITE_ESPERA_VEZ_DA_CONTA // 60} minutos. "
                  f"Seguindo mesmo assim: pode ter sido um processo que caiu "
                  f"no meio do caminho sem gravar o fim.")
            break
        if not avisou:
            dizer(f"Esperando: a máquina {dono} está usando a conta "
                  f"@{USUARIO_DOS_COOKIES} agora.")
            avisou = True
        time.sleep(SEGUNDOS_ENTRE_TENTATIVAS_VEZ_DA_CONTA)
    _registrar_evento_compartilhado("inicio_uso")
    return True


def liberar_vez_da_conta():
    """Fecha o uso marcado por aguardar_vez_da_conta(). Chamar sempre num
    finally, mesmo quando o processamento falhou no meio: outra máquina só
    para de esperar vendo este evento, ou pelo limite de tempo acima."""
    _registrar_evento_compartilhado("fim_uso")


# Sinais de que o Instagram barrou o acesso, e não de que o vídeo não existe.
# Separados em DOIS grupos desde 28/08/2026, porque não são a mesma coisa e
# tratar igual custava um dia de trabalho à toa.
#
# ESPERA: o Instagram pedindo pra ir mais devagar naquele endereço específico.
# Passa em pouco tempo e NÃO quer dizer que a conta está em apuros. Medido em
# 28/08/2026: a conta levou 429 com apenas 3 chamadas no dia, e ao mesmo tempo
# estava perfeitamente normal no celular, sem aviso nenhum.
#
# CONTA MARCADA: o Instagram desconfiando da conta em si. É o que gerou o aviso
# de comportamento suspeito em 25/08/2026, depois de 34 chamadas num dia.
SINAIS_DE_ESPERA = ("429", "too many requests", "rate limit", "rate-limit",
                    "please wait a few minutes", "invalid request",
                    # "This content is unreachable" é o que o yt-dlp diz quando
                    # não acha os dados do perfil na página. Pode ser sessão
                    # recusada, mas também pode ser perfil privado que a conta
                    # não segue, ou perfil que não existe.
                    #
                    # Fica na lista BRANDA por causa dessa ambiguidade: uma
                    # hora de pausa é recuperável, e a mensagem diz as duas
                    # possibilidades em vez de acusar a conta.
                    "this content is unreachable")

# "You need to log in to access this content" NÃO é bloqueio, e essa confusão
# custou caro em 30/08/2026.
#
# Eu tinha acrescentado esse texto à lista de bloqueios em 29/08, achando que
# significava sessão recusada. Lendo o código do yt-dlp, ele o emite quando a
# busca de stories volta VAZIA, ou seja, quando o perfil não tem story no ar:
#
#     videos = ... /feed/reels_media/?reel_ids=...
#     if not videos:
#         self.raise_login_required('You need to log in to access this content')
#
# Recusa de sessão de verdade dá outra mensagem: "This content is unreachable".
#
# O estrago do engano: a conta ficou pausada por horas, com a espera dobrando
# a cada tentativa, por causa de perfis que simplesmente não tinham story. E
# me levou a duas hipóteses erradas seguidas (cookies velhos, conta marcada).
SEM_STORY_NO_AR = "need to log in to access this content"
SESSAO_RECUSADA = "this content is unreachable"
SINAIS_DE_CONTA_MARCADA = ("401", "unauthorized", "challenge", "checkpoint")
SINAIS_DE_BLOQUEIO = SINAIS_DE_ESPERA + SINAIS_DE_CONTA_MARCADA

# Quanto o programa espera em cada caso.
#
# A espera curta DOBRA a cada vez que acontece no mesmo dia (1h, 2h, 4h...),
# limitada a 24h. É o que mantém a segurança: um pedido de "vá devagar"
# ignorado e repetido é justamente o caminho pra virar bloqueio de verdade.
# Se for coisa passageira, você volta em uma hora; se o Instagram estiver
# mesmo incomodado, o programa recua sozinho, cada vez mais.
HORAS_PAUSA_APOS_BLOQUEIO = 24      # conta marcada: para o dia
HORAS_PAUSA_PRIMEIRA_ESPERA = 1     # primeiro "vá devagar" do dia
HORAS_PAUSA_ESPERA_MAXIMA = 24

# Começo do status escrito na fila quando a linha parou porque a CONTA estava
# em pausa, não porque o link tem problema. Serve pra reconhecer essas linhas
# e retomá-las sozinhas quando a pausa vencer.
AVISO_CONTA_PAUSADA = "AGUARDANDO A CONTA LIBERAR"

# Trecho fixo dentro da mensagem de teto atingido, pelo mesmo motivo do
# MARCA_DE_RECUO logo abaixo: serve para RECONHECER que a linha parou por causa
# da conta, e não por defeito do link.
#
# ACHADO EM 01/09/2026, ao escrever o teste das rodadas seguidas. A detecção
# reconhecia a pausa por bloqueio e NÃO reconhecia o teto do dia, então a linha
# barrada pelo teto era marcada como FALHA. Falha é permanente: aquela linha não
# voltava sozinha no dia seguinte, quando o contador zera, e alguém teria que
# apagar o status à mão sem nunca saber por quê.
#
# O teto é tão temporário quanto a pausa: os dois vencem, um em 24h e o outro na
# virada do dia. Tratar diferente era distinção sem motivo.
MARCA_DE_TETO = "teto combinado"

# ------------------------------------------------------------------
# A cópia da Monitoramento de onde saem os ciclos
# ------------------------------------------------------------------
# É de um arquivo Excel parado, e não da planilha viva, de propósito: os ciclos
# não mudam de hora em hora e ler a planilha inteira a cada download seria caro.
# A contrapartida é que este arquivo envelhece, e por isso o programa avisa a
# idade dele em vez de deixar passar em silêncio.
#
# DEIXOU DE SER CAMINHO FIXO EM 30/08/2026. Antes apontava para uma pasta dentro
# de c:\Users\auditor, que não existe em outra máquina. Era o item 03 do
# checklist de subida, marcado como bloqueio, e é dele que sai o ciclo de cada
# vídeo: sem o arquivo, todo vídeo cairia em "Ciclo A CONFIRMAR".
#
# A ordem de procura é: variável de ambiente, depois a pasta de contexto do
# próprio projeto. Quem monta o servidor define a variável e não precisa mexer
# em código.
_RAIZ_PROJETO = os.path.dirname(os.path.dirname(BASE))
PASTA_CONTEXTO_PADRAO = os.path.join(
    _RAIZ_PROJETO, "contexto", "Auditoria-MKT de influencers")


def _achar_monitoramento():
    """Caminho da cópia da Monitoramento, ou None se não houver nenhuma.

    Aceita nome com data no fim ("... _2026-08-19.xlsx") e pega a mais recente,
    que é como os arquivos chegam do Marketing."""
    indicado = os.environ.get("ARQUIVO_MONITORAMENTO")
    if indicado:
        # Indicado à mão vale mesmo se não existir: melhor falhar dizendo que o
        # arquivo apontado não está lá do que procurar outro pelas costas.
        return indicado
    pasta = os.environ.get("PASTA_CONTEXTO") or PASTA_CONTEXTO_PADRAO
    if not os.path.isdir(pasta):
        return None
    candidatos = [
        os.path.join(pasta, n) for n in os.listdir(pasta)
        if n.lower().endswith(".xlsx") and "monitoramento" in n.lower()
        and not n.startswith("~$")  # arquivo temporário que o Excel deixa aberto
    ]
    if not candidatos:
        return None
    return max(candidatos, key=os.path.getmtime)


MONITORAMENTO = _achar_monitoramento()

ABA_FILA = "Fila"
EXTENSOES_VIDEO = {".mp4", ".mov", ".webm", ".m4v"}
# Fotos passaram a ser aceitas no envio pela tela em 28/08/2026. Vão pras
# mesmas pastas de post no Drive que os vídeos. O analisador já lê os dois
# formatos, então quando as fotos entrarem na fila de análise não há nada a
# mudar do lado dele.
EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg"}
EXTENSOES_ENVIO = EXTENSOES_VIDEO | EXTENSOES_IMAGEM

PADROES = [
    {
        "nome": "apostrofo_s_story",
        "regex": re.compile(
            r"^(?P<handle>[a-zA-Z0-9_.]+)'s(?P<ano>\d{4})-(?P<mes>\d{1,2})-(?P<dia>\d{1,2})-\d{1,2}\.\d{1,2}\.\d+ story",
            re.IGNORECASE,
        ),
        "tipo": "STORIES",
    },
    {
        "nome": "underscore_numero_data",
        "regex": re.compile(
            r"^(?P<handle>[a-zA-Z0-9_.]+?)_\d{10,}_(?P<ano>\d{4})-(?P<mes>\d{1,2})-(?P<dia>\d{1,2})",
        ),
        "tipo": None,
    },
]


# ------------------------------------------------------------------
# Ciclo pela Monitoramento
# ------------------------------------------------------------------
_ciclos_cache = None


def carregar_ciclos():
    """handle (minúsculo, sem @) -> lista de (ciclo, data_min, data_max)."""
    global _ciclos_cache
    if _ciclos_cache is not None:
        return _ciclos_cache
    import openpyxl
    if not MONITORAMENTO or not os.path.exists(MONITORAMENTO):
        # Sem o arquivo, todo vídeo cairia em "Ciclo A CONFIRMAR" sem ninguém
        # entender por quê. Melhor devolver vazio e deixar o aviso registrado,
        # que é o que a tela mostra, do que derrubar o download inteiro.
        print(f"[aviso] não achei a cópia da Monitoramento para descobrir os "
              f"ciclos. Procurei em {os.environ.get('PASTA_CONTEXTO') or PASTA_CONTEXTO_PADRAO}. "
              f"Aponte com a variável ARQUIVO_MONITORAMENTO ou PASTA_CONTEXTO. "
              f"Enquanto isso, os vídeos vão para 'Ciclo A CONFIRMAR'.")
        _ciclos_cache = defaultdict(list)
        return _ciclos_cache
    wb = openpyxl.load_workbook(MONITORAMENTO, read_only=True, data_only=True)
    ws = wb["Monitoramento"]
    datas = defaultdict(list)
    for row in ws.iter_rows(min_row=2, values_only=True):
        h, d, c = row[1], row[12], row[13]
        if not h or c is None or not d:
            continue
        d = d.date() if hasattr(d, "date") else d
        datas[(str(h).strip().lstrip("@").lower(), c)].append(d)
    ciclos = defaultdict(list)
    for (h, c), ds in datas.items():
        ciclos[h].append((c, min(ds), max(ds)))
    for h in ciclos:
        ciclos[h].sort(key=lambda x: x[2])
    _ciclos_cache = ciclos
    return ciclos


def _rotulo(c):
    return f"Ciclo {int(c) if isinstance(c, float) and c.is_integer() else c}"


def inferir_ciclo(handle, data_video):
    ciclos = carregar_ciclos().get(str(handle).strip().lstrip("@").lower())
    if not ciclos:
        return "Ciclo A CONFIRMAR"
    if data_video is None:
        return _rotulo(ciclos[-1][0])
    for c, dmin, dmax in ciclos:
        if dmin <= data_video <= dmax:
            return _rotulo(c)
    if data_video > ciclos[-1][2]:
        return _rotulo(ciclos[-1][0])
    return "Ciclo A CONFIRMAR"


def _numero_do_ciclo(bruto):
    """O ciclo como texto comparável: 6, 6.0 e 'Ciclo 6' viram '6'."""
    texto = re.sub(r"(?i)^ciclo\s*", "", str(bruto or "")).strip()
    try:
        numero = float(texto)
        return str(int(numero)) if numero.is_integer() else texto
    except ValueError:
        return texto


def janela_do_ciclo(handle, ciclo):
    """De quando até quando vai o ciclo, para poder olhar o Calendário.

    POR QUE ISTO EXISTE (11/09/2026): o cronograma que o Marketing manda lista
    também as datas em que o influenciador NÃO postou, e essas datas só existem
    no Calendário de Divulgações. Para saber quais delas pertencem a ESTE ciclo
    é preciso uma janela, e nenhuma das duas planilhas tem coluna de início e
    fim de ciclo. O número do ciclo só aparece colado em linhas que já viraram
    post.

    A JANELA SAI DO QUE EXISTE, e não de um palpite: começa no dia seguinte ao
    último post do ciclo anterior e termina na véspera do primeiro post do ciclo
    seguinte. Assim as datas sem post que ficam entre dois ciclos caem no ciclo
    certo, que é o que o cronograma real mostra (no exemplo medido, 13/08 e
    15/08 ❌ antes do primeiro ✅ em 16/08).

    A PONTA FINAL DO ÚLTIMO CICLO É UMA ESCOLHA, não uma medida: vai até o fim
    do mês do último post. Sem ciclo seguinte não existe nada que diga onde
    parar, e o Calendário é organizado em uma aba por mês. Quem quiser mudar
    isso muda aqui, num lugar só.

    O NÚMERO DE CICLO SE REPETE EM PERÍODOS BEM SEPARADOS (11/09/2026), e isso
    foi visto na tela: um ciclo pediu para ler o Calendário de abril a julho, e
    a régua real do Marketing só existe a partir de dezembro. Medido na cópia
    da Monitoramento: 1.032 ciclos ao todo, 54% com até 30 dias de posts e mais
    19,7% até 60 (a faixa de ciclo remontado já documentada, com até ~50 dias
    de vão no meio), mas **12,6% com mais de 365 dias** de posts sob o MESMO
    número de ciclo, o que é o mesmo número reaproveitado em períodos bem
    distintos do influenciador, não um ciclo remontado de verdade. Sem limite,
    a janela herdava esse reaproveitamento e saía com anos de largura, tentando
    ler aba de ano que o Calendário nunca teve.

    Duas travas, as duas em dias corridos e as duas com o motivo acima:

    - Se os próprios posts DESTE ciclo já passam de
      `LIMITE_DIAS_PROPRIO_CICLO`, o número foi reaproveitado e não dá para
      confiar nele: a janela vira (None, None), mesmo comportamento de handle
      sem ciclo.
    - A vizinhança com o ciclo anterior e o seguinte nunca estica mais que
      `PAD_MAXIMO_DIAS` além do que foi medido NESTE ciclo, não importa o que o
      vizinho diga. Um vizinho também vítima do reaproveitamento não
      contamina a janela deste.

    Devolve (primeira, ultima) como datas, ou (None, None) quando não há base
    para calcular, seja por falta de ciclo na cópia da Monitoramento, seja por
    o próprio ciclo ser largo demais para confiar."""
    LIMITE_DIAS_PROPRIO_CICLO = 90
    PAD_MAXIMO_DIAS = 45
    lista = carregar_ciclos().get(str(handle).strip().lstrip("@").lower())
    if not lista:
        return None, None
    alvo = _numero_do_ciclo(ciclo)
    posicao = next((i for i, (c, _, _) in enumerate(lista)
                    if _numero_do_ciclo(c) == alvo), None)
    if posicao is None:
        return None, None
    _, dmin, dmax = lista[posicao]
    if (dmax - dmin).days > LIMITE_DIAS_PROPRIO_CICLO:
        return None, None
    primeira_bruta = (lista[posicao - 1][2] + timedelta(days=1)) if posicao else dmin
    if posicao + 1 < len(lista):
        ultima_bruta = lista[posicao + 1][1] - timedelta(days=1)
    else:
        # Fim do mês do último post. Ver o parágrafo acima: é escolha.
        virada = (date(dmax.year + 1, 1, 1) if dmax.month == 12
                  else date(dmax.year, dmax.month + 1, 1))
        ultima_bruta = virada - timedelta(days=1)
    primeira_com_teto = max(primeira_bruta, dmin - timedelta(days=PAD_MAXIMO_DIAS))
    ultima_com_teto = min(ultima_bruta, dmax + timedelta(days=PAD_MAXIMO_DIAS))
    # A JANELA NUNCA PODE CORTAR OS PRÓPRIOS POSTS DO CICLO. Ciclos remontados
    # se sobrepõem no dado real (a auditoria registrou um que vai de 27/03 a
    # 16/05), e aí a conta acima pode devolver um começo depois do primeiro post
    # ou um fim antes do último. Nesse caso vale o que foi medido.
    return min(primeira_com_teto, dmin), max(ultima_com_teto, dmax)


# ------------------------------------------------------------------
# Organização no Drive de teste e log
# ------------------------------------------------------------------
_pastas_drive_cache = {}


def _pasta_raiz_drive():
    if modo_real_autorizado():
        # NUNCA CRIA PASTA SOZINHO NO REAL. O "cria se estiver vazio" abaixo
        # é comportamento só da cópia de teste. No modo real, id vazio é
        # erro de configuração, não motivo para inventar uma pasta nova
        # dentro do Drive do Marketing. modo_real_autorizado() já confere
        # que este id não está vazio; o erro aqui é rede de segurança para
        # o caso de o arquivo mudar entre uma chamada e outra.
        id_real = ler_identificador(ARQUIVO_DRIVE_RAIZ_REAL_ID)
        if id_real:
            return id_real
        raise RuntimeError(
            "Modo real autorizado, mas o identificador da pasta raiz do "
            "Drive real ficou vazio. Confira "
            f"{os.path.basename(ARQUIVO_DRIVE_RAIZ_REAL_ID)}.")
    import drive_client_upload
    id_salvo = ler_identificador(ARQUIVO_DRIVE_RAIZ_ID)
    if id_salvo:
        return id_salvo
    id_raiz = drive_client_upload.obter_ou_criar_pasta(DRIVE_TESTE_RAIZ_NOME)
    os.makedirs(PASTA_TESTE, exist_ok=True)
    with open(ARQUIVO_DRIVE_RAIZ_ID, "w", encoding="utf-8") as f:
        f.write(id_raiz)
    return id_raiz


def link_de_pasta_no_drive(id_pasta):
    """Endereço de uma pasta do Drive, para a coluna LINK da Monitoramento.

    Entrou em 03/09/2026, quando a coluna LINK passou a apontar para a pasta do
    post em vez do arquivo. Devolve None sem id: aí a coluna LINK recebe o
    arquivo, que é o comportamento de antes e o que vale para link externo."""
    return f"https://drive.google.com/drive/folders/{id_pasta}" if id_pasta else None


def link_pasta_raiz_drive():
    """Devolve a URL da pasta raiz de teste no Drive, sem criar nada — só lê o
    ID já salvo (usado pela UI). None se a pasta ainda não foi criada."""
    id_raiz = ler_identificador(ARQUIVO_DRIVE_RAIZ_ID)
    return f"https://drive.google.com/drive/folders/{id_raiz}" if id_raiz else None


# ONDE CADA SEÇÃO DA TELA GUARDA O QUE RECEBE (31/08/2026).
#
# Pedido do auditor: cada seção mostrar onde vai o que ela recebe, para a
# pessoa conferir sem sair procurando.
#
# LINK, e nunca abrir pasta na máquina. Os botões que usavam os.startfile
# saíram em 28/08 porque abririam o arquivo NO SERVIDOR, onde ninguém está
# olhando, e a função nem existe fora do Windows. Era o item 01 do checklist de
# subida, marcado como bloqueio. Link do Drive abre no navegador de quem
# clicou, que é o que a pessoa precisa.
# O ENDEREÇO PRECISA ABRIR NA ABA CERTA (01/09/2026).
#
# Achado pelo auditor clicando em "Abrir a Monitoramento": o link levava à
# planilha, mas ela abria no Sumário, porque a aba Monitoramento é a QUARTA do
# arquivo. Quem clicou queria ver as linhas, e caía numa aba que não tem nada a
# ver com o trabalho.
#
# O número da aba (gid) é pedido à API uma vez por processo e guardado aqui. Ele
# não muda: é o identificador interno da aba, e continua o mesmo se alguém
# renomear ou reordenar. Sem o cache, cada desenho da tela faria uma chamada só
# para montar um link.
_gid_das_abas = {}


def _gid_da_aba(planilha_id, aba):
    """Número interno da aba, para o link abrir nela. None se não der para
    descobrir, e aí quem chama monta o endereço sem essa parte: link que abre na
    aba errada é bem melhor que botão que não abre nada."""
    if not planilha_id or not aba:
        return None
    chave = (planilha_id, aba)
    if chave in _gid_das_abas:
        return _gid_das_abas[chave]
    try:
        import sheets_client
        gid = sheets_client.id_da_aba(planilha_id, aba)
    except Exception:
        gid = None
    _gid_das_abas[chave] = gid
    return gid


def _link_de_planilha(planilha_id, aba=None):
    if not planilha_id:
        return None
    endereco = f"https://docs.google.com/spreadsheets/d/{planilha_id}/edit"
    gid = _gid_da_aba(planilha_id, aba) if aba else None
    return f"{endereco}#gid={gid}" if gid is not None else endereco


def link_planilha_fila():
    """URL da planilha da fila de downloads. None se não estiver configurada."""
    return _link_de_planilha(_planilha_fila_id(), ABA_FILA)


def link_planilha_monitoramento():
    """URL da Monitoramento de teste, na aba Monitoramento, que é onde a linha de
    cada peça nasce."""
    return _link_de_planilha(_planilha_monitoramento_id(), ABA_MONITORAMENTO)


# ------------------------------------------------------------------
# Layout das pastas no Drive
# ------------------------------------------------------------------
# Existem dois, e a escolha é de configuração, não de código, porque o destino
# muda quando o programa sair da máquina de teste pro servidor.
#
#   "teste"      @influenciador / Ciclo N
#                É o que a pasta de TESTE usa hoje.
#
#   "marketing"  01. EDS / 2026 / 08. Agosto / @influenciador
#                É a estrutura real do Marketing, vista em 28/08/2026:
#                INFLUENCIADORES > VÍDEOS INFLUENCIADORES > [bet] > [ano] >
#                [mês] > [@influenciador]. A BET é o nível de cima, e por isso
#                o mesmo influenciador aparece em lugares diferentes conforme
#                a bet do contrato.
#
# Para trocar sem mexer no código, use a variável de ambiente
# LAYOUT_PASTAS_DRIVE. A raiz também não é fixa: o identificador dela fica em
# teste_watch_folder/drive_teste_pasta_raiz_id.txt, então apontar o programa
# pra outra pasta é trocar o conteúdo desse arquivo.
LAYOUT_TESTE = "teste"
LAYOUT_MARKETING = "marketing"

# TERCEIRO LAYOUT, criado em 12/09/2026, para a analista que cobre sozinha a
# categoria FUTEBOL e organiza o Drive dela por conta própria, separado do
# Drive do Marketing. Só a pasta raiz muda de dono; Monitoramento, Dados_influ
# e Calendário continuam sendo as mesmas planilhas compartilhadas com o resto
# do time.
#
# ESTRUTURA MEDIDA NELA (12/09/2026, 22 pastas de influenciador lidas):
# [pasta do influenciador] / DIVULGAÇÕES / MM. MÊS / arquivo. Sem bet, sem ano,
# sem pasta de dia, sem tipo, sem marcação: tudo isso que os outros dois
# layouts têm ela simplesmente não tem.
#
# A VARIAÇÃO JÁ MEDIDA, e por isso tolerada (não é hipótese): "DIVULGAÇÕES" e
# "DIVULGAÇÃO" (Leo Lima, no singular), as duas com e sem espaço sobrando no
# fim. Também existem pastas irmãs que o programa deve ignorar por não
# procurar por elas: CONTRATO, PLANEJAMENTO, DOCUMENTOS, e pelo menos uma pasta
# ad-hoc (REELS VERNECK_12). Um caso (Náutico Mil Grau, mês de janeiro) tinha
# um nível de dia a mais dentro do mês; não é tratado aqui de propósito, é
# resquício de uma época anterior a essa organização, e o programa só desce
# pelos segmentos que ele mesmo monta, então não precisa saber que esse nível
# existe.
#
# A PASTA DO INFLUENCIADOR NÃO TEM RELAÇÃO NENHUMA COM O @: são nomes de
# pessoa ou de página de torcida (ex. "Rafa Lira" para @rafalirarl, "Central do
# Timão" para @centraldotimao). Por isso o @ → nome da pasta vive num mapa
# próprio (ver ARQUIVO_PASTA_FUTEBOL), igual em espírito ao mapa de número
# interno de perfil (ARQUIVO_USERIDS): guarda uma vez, por pessoa, e nunca
# adivinha.
LAYOUT_FUTEBOL = "futebol"

LAYOUT_PASTAS = os.environ.get("LAYOUT_PASTAS_DRIVE", LAYOUT_TESTE)

MESES_PASTA = ["01. Janeiro", "02. Fevereiro", "03. Março", "04. Abril",
               "05. Maio", "06. Junho", "07. Julho", "08. Agosto",
               "09. Setembro", "10. Outubro", "11. Novembro", "12. Dezembro"]
PASTA_DA_BET = {"EDS": "01. EDS", "ONA": "02. ONA",
                "LOTTU": "03. LOTTU", "EDSCAP": "04. EDSCAP"}

# MESES NO LAYOUT FUTEBOL: maiúsculo, e não Título como nos outros dois.
# JANEIRO a MAIO vieram de pasta real, lida em 12/09/2026 (ex. "04. ABRIL",
# "05. MAIO"); JUNHO a DEZEMBRO seguem o mesmo padrão por extrapolação, e não
# foram vistos ainda. Se algum vier diferente quando o mês chegar, é a
# comparação tolerante de sempre (achar_pasta_tolerante) que resolve, sem
# precisar mudar esta lista antes de criar a pasta errada.
MESES_PASTA_FUTEBOL = ["01. JANEIRO", "02. FEVEREIRO", "03. MARÇO",
                       "04. ABRIL", "05. MAIO", "06. JUNHO", "07. JULHO",
                       "08. AGOSTO", "09. SETEMBRO", "10. OUTUBRO",
                       "11. NOVEMBRO", "12. DEZEMBRO"]

# A pasta entre o influenciador e o mês, no layout futebol. Grafia canônica no
# plural, com a variação no singular (Leo Lima) tolerada por
# GRAFIAS_PASTA_DIVULGACOES, do mesmo jeito que "story"/"stories" já é.
PASTA_DIVULGACOES = "DIVULGAÇÕES"
GRAFIAS_PASTA_DIVULGACOES = (PASTA_DIVULGACOES, "DIVULGAÇÃO")

# O mapa @ -> nome exato da pasta, para o layout futebol. Não existe coluna de
# nome de exibição na Dados_influ (só o @, coluna INFLU), e as pastas dela são
# por apelido/nome de página, não por @. Sem esse mapa o programa não teria
# como achar a pasta sozinho. Seed inicial (12/09/2026) construído por leitura
# direta do Drive dela, achando o @ real dentro do nome de um arquivo já
# baixado em cada pasta; documentado no pedido que criou este layout.
ARQUIVO_PASTA_FUTEBOL = os.path.join(PASTA_TESTE, "pasta_por_handle_futebol.json")
_cache_pasta_futebol = None


def _pasta_por_handle_futebol(recarregar=False):
    """{@sem arroba: nome exato da pasta} do layout futebol. None se o
    arquivo ainda não existe ou está ilegível; quem chama trata None como
    "não sei", igual ao resto dos mapas deste módulo."""
    import json
    global _cache_pasta_futebol
    if recarregar or _cache_pasta_futebol is None:
        if not os.path.exists(ARQUIVO_PASTA_FUTEBOL):
            return None
        try:
            with open(ARQUIVO_PASTA_FUTEBOL, "r", encoding="utf-8") as f:
                _cache_pasta_futebol = json.load(f)
        except (OSError, ValueError):
            return None
    return _cache_pasta_futebol


def pasta_do_handle_futebol(handle_limpo):
    """Nome exato da pasta dela para este @, ou explica o que falta.

    NUNCA ADIVINHA: sem entrada no mapa, para. Inventar um nome de pasta a
    partir do @ criaria uma pasta nova e errada no Drive real dela, ao lado da
    pasta certa que já existe com outro nome."""
    mapa = _pasta_por_handle_futebol()
    if mapa is None:
        raise PastaNaoExisteNoDrive(
            f"Não consegui ler {os.path.basename(ARQUIVO_PASTA_FUTEBOL)}, o mapa "
            f"de pastas do layout futebol. Sem ele o programa não sabe em qual "
            f"pasta @{handle_limpo} entra.")
    nome = mapa.get(handle_limpo.lower())
    if not nome:
        raise PastaNaoExisteNoDrive(
            f"@{handle_limpo} não está em {os.path.basename(ARQUIVO_PASTA_FUTEBOL)}. "
            f"O layout futebol não adivinha o nome da pasta a partir do @, porque "
            f"as pastas dela são por apelido, não por @. Adicione a entrada "
            f"\"{handle_limpo.lower()}\": \"nome exato da pasta no Drive dela\" "
            f"nesse arquivo e mande de novo.")
    return nome


def pasta_do_mes_futebol(data_video):
    """Nome da pasta do mês no layout futebol (\"04. ABRIL\"), a partir da
    data do post. Mesma regra do MESES_PASTA de sempre, só que na grafia
    maiúscula que é a dela."""
    if not data_video:
        raise PastaNaoExisteNoDrive(
            "Sem a data do post não dá para saber em qual pasta de mês o "
            "material entra. Informe a data e tente de novo.")
    return MESES_PASTA_FUTEBOL[data_video.month - 1]


# ------------------------------------------------------------------
# Encontrar a pasta que JÁ EXISTE, em vez de criar outra
# ------------------------------------------------------------------
# Decidido em 29/08/2026, depois de ler as pastas reais do Marketing.
#
# O problema: a pasta de cada influenciador já existe no Drive deles, criada à
# mão ao longo de meses. Se o programa procurar pelo nome exato e não achar,
# ele CRIA, e aí passa a existir uma segunda pasta para o mesmo influenciador.
# Com 5 pessoas usando e 266 influenciadores, isso polui a estrutura deles
# rápido, e quem arruma depois é uma pessoa, na mão.
#
# O que medimos nas 720 pastas de 2026: 677 começam com @ e 43 não; 60 têm
# nome que não bate byte a byte com um @ do Instagram. Quase todas por três
# motivos cosméticos:
#
#   espaço sobrando na borda   '@feijhonys ', ' @Joaovictorr10'
#   maiúscula                  '@EUSOULUKINHAS', '@Lannaleticia'
#   sem o @                    'antonio_rafaski ', 'Debochad_a'
#
# Por isso a comparação ignora EXATAMENTE essas três coisas, e nada além. O @
# de Instagram não diferencia maiúscula de minúscula, então ignorar isso não
# junta pessoas diferentes. Já sublinhado e ponto SÃO significativos
# (@andreasantosof e @andreasantosof_ podem ser duas contas), então continuam
# valendo na comparação.
def chave_de_pasta(nome):
    """Reduz um nome de pasta ao que importa para comparar.

    IGNORA TODO ESPAÇO, e não só o das bordas (01/09/2026). Antes era só a borda,
    e foi uma medição que mostrou a diferença: das 19 pastas de mês de 2026 no
    Drive do Marketing, 18 eram encontradas e uma não, a "05.MAIO" da ONA, que
    não tem o espaço depois do ponto. O programa monta "05. Maio", com espaço.

    O efeito de não achar não é um erro na tela: é o programa concluir que falta
    a pasta do mês de maio da ONA, quando ela está lá com o material dentro.

    Nenhum dos nomes que o programa procura fica ambíguo sem os espaços: os doze
    meses continuam distintos, @ do Instagram não tem espaço, e "15/08" continua
    diferente de "15/08 - bruto", que é o que precisa continuar diferente."""
    return str(nome or "").strip().lstrip("@").lower().replace(" ", "")


def achar_pasta_tolerante(nome_desejado, subpastas):
    """Procura, entre as subpastas, uma que case com o nome desejado.

    `subpastas`: lista de dicionários com "name" e "id", como a API do Drive
    devolve. Retorna (id, nome_real) ou (None, None).

    Função pura de propósito: não fala com o Drive, então dá para testar
    contra a lista real de pastas sem tocar em nada."""
    alvo = chave_de_pasta(nome_desejado)
    if not alvo:
        return None, None
    for pasta in subpastas:
        if chave_de_pasta(pasta.get("name")) == alvo:
            return pasta.get("id"), pasta.get("name")
    return None, None


class PastaNaoExisteNoDrive(RuntimeError):
    """Uma pasta do caminho não existe no Drive do Marketing, e o programa NÃO
    vai criar nenhuma.

    AMPLIADO EM 30/08/2026 para TODO o caminho, não só a pasta do
    influenciador. O motivo está nos números lidos do Drive real: das 18
    pastas de mês que existem em 2026, três não batem letra por letra com o
    que o programa monta ("01. Janeiro " e "03. Março " com espaço no fim,
    "08. AGOSTO" em maiúsculas na ONA). Criar em vez de barrar produziria duas
    pastas de mesmo nome aparente lado a lado, e o material daquele mês
    ficaria dividido entre as duas. No nível do mês isso é pior que no do
    influenciador, porque atinge todos os influenciadores de uma vez.

    O texto abaixo é a decisão original, que continua valendo.

    Decisão do auditor em 29/08/2026: o programa cria o que ele mesmo sabe
    nomear com certeza (bet, ano, mês, que vêm de uma tabela fixa) e nunca o
    que uma pessoa nomeou. Falhar aqui é proposital: é o que impede a
    automação de encher o Drive do Marketing de pasta duplicada quando o nome
    da pasta deles está diferente do @ do Instagram.

    Quem receber este erro precisa saber o que fazer, então a mensagem diz
    qual pasta falta e onde."""


# Nome antigo, de quando a regra valia só para a pasta do influenciador.
PastaDoInfluenciadorNaoExiste = PastaNaoExisteNoDrive


class BetNaoInformada(RuntimeError):
    """Sem a bet não há como saber em qual das quatro árvores o material entra.

    Até 30/08/2026 o programa inventava uma pasta "00. SEM BET DEFINIDA" nesse
    caso. Conferido contra o Drive real: essa pasta NÃO existe lá, então ela
    seria criada na raiz do Marketing, que é exatamente o que a regra de não
    criar pasta existe para evitar. Agora a bet é obrigatória e o programa
    para antes de baixar."""


def exigir_bet(marca):
    """Devolve o nome da pasta da bet, ou explica o que falta.

    Separado de propósito: assim a tela consegue barrar ANTES de baixar, sem
    repetir a tabela de nomes."""
    bet = PASTA_DA_BET.get(str(marca or "").strip().upper())
    if not bet:
        raise BetNaoInformada(
            "Informe a bet (EDS, ONA, LOTTU ou EDSCAP). Ela decide em qual pasta "
            "do Drive o material entra, e o programa não tem como adivinhar.")
    return bet


def caminho_ate_influenciador(handle_limpo, data_video, marca=None):
    """Pastas, da raiz até a do influenciador.

    OS DOIS LAYOUTS MONTAM OS MESMOS QUATRO NÍVEIS DESDE 01/09/2026, e essa é a
    correção de uma incoerência que o auditor apontou.

    O comentário de pastas_dentro_do_influenciador já dizia que os dois layouts
    têm a mesma estrutura "para o layout de teste servir de ensaio de verdade".
    Só que aqui o de teste devolvia apenas ["@handle"], sem bet, ano e mês. O
    teste real de 01/09 produziu "@teste.organico.0109 / 01/09 / story", e nele
    os três níveis de cima simplesmente não apareceram: o ensaio não ensaiava a
    parte da árvore onde estão as regras mais delicadas, que são a comparação
    tolerante de nome de mês e a proibição de criar na raiz.

    O QUE CONTINUA DIFERENTE, e deve continuar: no Drive de teste TUDO pode ser
    criado, porque a árvore é nossa e começa vazia. No do Marketing, bet e ano só
    são encontrados. Quem decide isso é _descer_criando, não esta função.

    EFEITO COLATERAL ACEITO: a bet passa a ser obrigatória também no layout de
    teste. É desejável, porque na tela ela já é obrigatória desde 30/08, e sem
    isso o ensaio não exercitava o caminho em que ela falta.

    O LAYOUT FUTEBOL PASSOU A SEGUIR O MESMO CAMINHO DA RESPONSÁVEL A (21/09/2026),
    decisão do auditor que substitui de vez o desenho de 12/09 (pasta por
    apelido, achada num mapa @->pasta). A pasta do influenciador volta a ser
    pelo @, igual ao Marketing. As duas diferenças que sobram: SEM O NÍVEL DE
    ANO (decisão explícita do auditor), e a raiz configurada para a Responsável B
    passa a ser uma pasta "Divulgações", criada por ela, que fica no lugar de
    onde a bet mora direto (por isso não precisa de código novo pra isso, só
    apontar `drive_pasta_raiz_id.txt`/`drive_teste_pasta_raiz_id.txt` pra
    essa pasta). O mês continua na grafia própria do futebol
    (pasta_do_mes_futebol, "04. ABRIL"), confirmado que fica assim."""
    bet = exigir_bet(marca)
    if not data_video:
        # Mês sai da data do post. Sem data não dá para escolher a pasta do
        # mês, e chutar o mês corrente colocaria material de agosto dentro de
        # setembro na virada.
        raise PastaNaoExisteNoDrive(
            "Sem a data do post não dá para saber em qual pasta de mês o "
            "material entra. Informe a data e tente de novo.")
    if LAYOUT_PASTAS == LAYOUT_FUTEBOL:
        return [bet, pasta_do_mes_futebol(data_video), "@" + handle_limpo]
    ano = str(data_video.year)
    mes = MESES_PASTA[data_video.month - 1]
    return [bet, ano, mes, "@" + handle_limpo]


# A PASTA DO TIPO DE MÍDIA, dentro da pasta do dia (01/09/2026).
#
# Estrutura, informada pelo auditor e conferida no Drive deles:
#
#     bet / ano / mês / @influenciador / DD/MM / <tipo> [ / orgânico ]
#
# OS NOMES VÊM DE MEDIÇÃO, E NÃO DE ESCOLHA NOSSA.
#
# Varredura só de leitura no Drive do Marketing em 01/09/2026, restrita aos
# influenciadores com STATUS ATIVO na Dados_influ (50 deles têm pasta em 2026),
# contando os nomes de pasta dentro da pasta do dia:
#
#     283x "vídeo bruto"   273x "story"     93x "stories"   43x "bruto"
#      25x "brutas"         24x "brutos"    14x "Story"     13x "Vídeo bruto"
#      11x "ENTREGAS"       10x "DADOS"     10x "orgânico"   6x "link"
#       4x "STORY"           3x "Stories"    2x "REELS"      2x "Bruto"
#       2x "vídeos brutos"   1x "VÍDEO BRUTO"
#
# POR QUE SÓ OS ATIVOS: a primeira varredura pegou os 120 primeiros
# influenciadores que apareceram nas pastas de 2026, e o auditor apontou que
# muita gente ali não pertence mais à casa. Pasta de quem saiu registra a grafia
# de outra época, e o que interessa é a que o time usa hoje. Os números mudaram
# de verdade: "stories" parecia caso isolado (2 em 120) e é 93 entre os ativos.
#
# O PADRÃO É "story", minúsculo e no singular, com 273 contra 93 da variação
# plural. E não é margem folgada: um quarto do material está na outra grafia, o
# que faz a lista de sinônimos abaixo ser necessária, e não precaução.
#
# "link" E "orgânico" EXISTEM, minúsculos, mas hoje estão AO LADO da pasta de
# story e não dentro dela. Contando tudo o que existe dentro da VÍDEOS
# INFLUENCIADORES, são 16 pastas "orgânico" e 12 "link", as 28 dentro de uma
# pasta de data. O auditor definiu em 01/09/2026 que orgânico passa a ficar
# dentro, então a partir de agora convivem os dois arranjos: as 28 antigas ao
# lado, e as novas dentro.
#
# E "link" NÃO guarda endereço, apesar do nome: as 12 têm 22 vídeos mp4 e 2
# imagens dentro. A hipótese de que fossem endereços de mídia que não pode ser
# baixada foi testada e não se sustenta, e reforçando: dentro da VÍDEOS
# INFLUENCIADORES não existe UM arquivo ou pasta com "live", "youtube",
# "twitch", "tiktok" ou "twitter" no nome. "link" é categoria de arquivamento
# por origem, igual a "orgânico".
#
# FEED não apareceu nenhuma vez, e REELS apareceu 2, em maiúsculas. Para esses
# dois a grafia continua sendo palpite. Ficam minúsculos por coerência com
# "story", e a comparação tolerante encontra o "REELS" deles de qualquer forma.
PASTA_STORY = "story"
PASTA_REELS = "reels"
PASTA_FEED = "feed"

# Material não editado. O programa NÃO ANALISA o que está dentro (ver
# NOMES_SUBPASTA_IGNORADA no cliente do Drive). O auditor confirmou em
# 01/09/2026 que material bruto é fora do escopo da auditoria; a redação
# original desta nota dizia que ele iria para OUTRO Drive, e por isso o
# programa só ignorava pasta já existente, nunca escrevia.
#
# PASSOU A ESCREVER AQUI EM 23/09/2026 (enviar_video_bruto, pedido do
# Marketing): confirmado com o auditor que o destino é o MESMO Drive de
# sempre, não um segundo Drive, porque não há credencial nem raiz configurada
# para outro. Isto não desfaz a decisão de 01/09, só a precisa: o que
# continua valendo é NUNCA ANALISAR o que está aqui, e é por isso que a
# proteção abaixo (e_pasta_de_bruto, usada por procurar_arquivo_repetido) não
# mudou nada. Vídeo bruto sobe, fica visível pra conferência humana, nunca
# ganha linha na Monitoramento nem entra na fila de validação.
#
# A regra procurava só "bruto" e por isso deixava passar as 25 pastas chamadas
# "brutas", no feminino, que a varredura dos ativos encontrou. Corrigido junto.
PASTA_BRUTO = "vídeo bruto"


def e_pasta_de_bruto(nome):
    """Se aquela pasta é de material não editado.

    Usa a MESMA lista de termos que a análise usa (NOMES_SUBPASTA_IGNORADA, no
    cliente do Drive), de propósito: duas listas separadas para a mesma regra é
    como uma pasta acaba ignorada num lugar e visitada no outro.

    Compara por pedaço do nome e não por igualdade, e é isso que faz as grafias
    medidas no Drive deles caírem todas aqui: "vídeo bruto", "VÍDEO BRUTO",
    "Vídeo bruto", "vídeos brutos", "vído bruto", "bruto", "Bruto", "brutos" e
    "brutas"."""
    import drive_client
    texto = str(nome or "").lower()
    return any(termo in texto for termo in drive_client.NOMES_SUBPASTA_IGNORADA)

# O QUE A PEÇA É, um nível ACIMA do tipo de mídia (03/09/2026).
#
# ESTA PARTE FOI REFEITA DUAS VEZES NO MESMO DIA, e a segunda versão é esta. Vale
# guardar as duas, porque a diferença entre elas é o que a auditoria classifica.
#
# PRIMEIRA VERSÃO, pela manhã. O auditor descreveu:
#
#   "a tela de orgânico é quando o usuário mostra só alguma coisa da marca, uma
#   garrafa com a logo da lottu ou da EDS, ou Ona, e link é quando ele anuncia os
#   jogos e coloca os avisos da portaria e tudo mais, porém ele coloca tbm o link
#   que redireciona pra bet"
#
# E pediu um terceiro lugar "pra colocar feed/reels/story que não for organico e
# nem link". Disso saíram orgânico, publi e link, com publi sendo a peça que
# anuncia sem redirecionar.
#
# ELE MESMO CORRIGIU, logo depois: "eu errei agora.... Publi e Link são a mesma
# coisa, pq a publi contem o LINK com a marca, só o orgânico que muda". Então
# publi não era uma terceira categoria: era o mesmo que link.
#
# E completou com o caso que faltava: "pode ser que nesse post onde ele apenas
# mostra uma garrafa com a marca, que é algo organico e sem falar de jogo, ele
# mostre o LINK que encaminha para o site da bet, portanto, são 3 categorias:
# ORGÂNICO, LINK, LINK + ORGÂNICO".
#
# TERCEIRA E ÚLTIMA VERSÃO, depois de ele conversar com o Marketing:
#
#   "a peça orgânica nunca pode ser link ao mesmo tempo, além disso, elas não
#   contam como MESMO POST como é o caso do story em sequencia por exemplo, são
#   tipos de entrega diferentes mesmo"
#
# Então SÃO DUAS, e não três:
#
#   orgânico   só mostra algo da marca, sem falar de jogo e sem link
#   link       a peça publicitária: anuncia, traz os avisos e leva o link
#
# "link + orgânico" existiu por menos de uma hora, como categoria de peça e
# depois como nome de pasta para o dia misto. Caiu por duas razões dele: peça
# orgânica nunca é link ao mesmo tempo, e um orgânico e um link no mesmo dia são
# entregas DIFERENTES, não o mesmo post.
#
# E ESSA SEGUNDA PARTE É O QUE IMPORTA MAIS, porque muda a contagem de post e não
# só o nome de pasta: a marcação passou a SEPARAR POSTS. Ver _numero_do_post.
# Sequência de stories do mesmo dia é um post só; um orgânico e um link no mesmo
# dia são dois posts.
#
# O PADRÃO É "link", porque é a peça publicitária comum, e é o que o material
# baixado costuma ser. Antes desta mudança quem não marcava nada caía no tipo
# direto, e é esse caso que "link" agora ocupa.
#
# SÃO EXCLUDENTES, e por isso a tela é uma escolha só: as duas descrevem a peça
# inteira, e arquivo mora num lugar só.
#
# POR QUE ACIMA DO TIPO, E NÃO DENTRO DELE: era dentro, e a medição de 02/09/2026
# mostrou que na pasta deles NÃO EXISTE nível nenhum abaixo do tipo, em 60
# influenciadores lidos. Ou seja, a pasta "orgânico" dentro de "story" era um
# nível a mais do que eles usam. Com a marcação acima, o tipo continua sendo o
# último nível antes do arquivo, como lá.
#
# A MARCAÇÃO TAMBÉM VAI PARA A PLANILHA (ver BLOCO_AUTOMACAO), e essa é a parte
# que importa para a auditoria: pasta serve para achar o arquivo olhando o Drive,
# e não dá para filtrar nem contar por ela. Sem a coluna, "quantos posts
# orgânicos entraram neste ciclo" só se responderia varrendo o Drive à mão.
#
# E ELA VAI VALER PARA A RÉGUA DA ANÁLISE, o que é mais sério que organização de
# arquivo. O auditor já decidiu sobre orgânico: "orgânico não é fazendo
# propaganda, logo, ele não precisa colocar os avisos regulatórios pq ele ta so
# mostrando o patrocinio". ISSO AINDA NÃO FOI APLICADO na classificação: a régua
# continua exigindo os quatro avisos de tudo, então peça orgânica é reprovada por
# definição. Ver PROMPT_CONTINUACAO.
PASTA_ORGANICO = "orgânico"
PASTA_LINK = "link"

# Chave interna -> nome da pasta. A chave é sem acento de propósito: ela viaja
# pela planilha da fila e por arquivo de tarefa, e acento nesses caminhos já
# causou problema em Windows antes.
PASTA_DA_MARCACAO = {
    "organico": PASTA_ORGANICO,
    "link": PASTA_LINK,
}
MARCACAO_PADRAO = "link"

# O RÓTULO QUE APARECE NA TELA, para o rádio de marcação (03/09/2026).
#
# CENTRALIZADO AQUI, e não repetido em cada página: até 23/09/2026 vivia como
# variável local dentro de pages/1_Downloads_e_Organizacao.py, e servia tanto
# à seção de link do Instagram quanto à de "Enviar arquivo do post" NA MESMA
# página. Quando "Enviar arquivo do post" se mudou para uma página de Uploads
# própria (pedido do auditor, mesma data), duas cópias da mesma lista em dois
# arquivos é exatamente o que o comentário original já avisava: "é como uma
# tela passa a oferecer opção que a outra não tem".
ROTULO_DA_MARCACAO = {
    "link": "Link: anuncia os jogos e leva o link da bet",
    "organico": "Orgânico: só mostra a marca, sem falar de jogo e sem link",
}

# O QUE UMA CÉLULA DE PLANILHA QUER DIZER. Aceita o que gente escreve à mão e o
# que o programa já escreveu antes:
#
#   "SIM"     é o que a coluna ORGANICO guardava até 02/09/2026, então continua
#             querendo dizer orgânico. Sem isso, as linhas já gravadas passariam
#             a ser lidas como link e a marcação delas se perderia sem ninguém
#             perceber.
#   "PUBLI"   existiu por algumas horas em 03/09/2026, na primeira versão desta
#             parte, e quer dizer link, porque foi assim que ele corrigiu.
#             Conferido na planilha: nenhuma linha foi gravada com esse valor,
#             então isto é rede de segurança e não migração.
#
# "LINK + ORGANICO" NÃO ENTRA AQUI, de propósito. Ele existiu por menos de uma
# hora e caiu porque peça orgânica nunca é link ao mesmo tempo. Célula com esse
# texto cai no padrão, que é link, e é a leitura menos errada das duas: a peça
# tem link, e o que a marcação decide é a régua dos avisos.
LEITURA_DA_MARCACAO = {
    "organico": "organico", "orgânico": "organico", "organica": "organico",
    "orgânica": "organico", "sim": "organico", "s": "organico", "x": "organico",
    "true": "organico", "verdadeiro": "organico", "1": "organico",
    "link": "link", "links": "link", "com link": "link",
    "publi": "link", "publicidade": "link", "publipost": "link",
}


def marcacao_de_celula(valor):
    """Qual das três marcações aquele texto de célula quer dizer.

    Vazio é MARCACAO_PADRAO, que é link: é a peça publicitária comum, e é o caso
    em que caía quem não marcava nada antes desta parte existir. Texto que não se
    reconhece também cai nele, e isso é decisão consciente: parar o download
    porque alguém digitou outra coisa na planilha gastaria a chamada ao
    Instagram, que é o recurso escasso, sem guardar nada."""
    texto = str(valor or "").strip().lower()
    if not texto:
        return MARCACAO_PADRAO
    return LEITURA_DA_MARCACAO.get(texto, MARCACAO_PADRAO)


def pasta_da_marcacao(marcacao):
    """Nome da PASTA daquela marcação. Marcação desconhecida cai no padrão.

    Note que a pasta de orgânico tem acento ("orgânico"), porque é assim que está
    escrito no Drive deles. Para o valor que vai para PLANILHA, use
    texto_da_marcacao, que é sem acento."""
    chave = str(marcacao or "").strip().lower()
    return PASTA_DA_MARCACAO.get(chave, PASTA_DA_MARCACAO[MARCACAO_PADRAO])


# TEXTOS DE TELA QUE PRECISAM SABER O LAYOUT (12/09/2026).
#
# Encontrado testando o layout futebol: a tela de Downloads afirmava "vai para
# a pasta X, acima da pasta do tipo" e "é a pasta de cima no Drive do
# Marketing" sempre, mesmo rodando num layout que não tem pasta de tipo nem de
# bet. A explicação ficava errada sem ninguém perceber, porque nada no texto
# dependia do layout ativo. Centralizado aqui para os dois formulários da tela
# (link do Instagram e upload de arquivo) usarem o mesmo texto, em vez de cada
# um decidir por conta própria e um dia discordar do outro.
def ajuda_campo_marcacao(forma_curta=False):
    """Texto de ajuda do rádio orgânico/publi/link.

    ENCURTADO EM 17/09/2026, pedido do auditor de resumir todo help= da
    tela: a explicação de onde cada escolha grava (pasta, coluna) saiu,
    ficou só a definição que ajuda a escolher certo."""
    if forma_curta:
        return "Vale para todos os arquivos deste envio."
    return ("Orgânico: só mostra algo da marca, uma garrafa com a logo. "
            "Publi: anuncia os jogos com os avisos. Link: anuncia e ainda "
            "leva o endereço que redireciona para a bet.")


def texto_destino_da_marcacao(marcacao):
    """Frase que diz para onde a marcação escolhida vai, usada na confirmação
    de \"Baixando...\". No layout futebol não existe pasta de marcação."""
    if LAYOUT_PASTAS == LAYOUT_FUTEBOL:
        return (f"Marcação **{pasta_da_marcacao(marcacao)}**, só na coluna "
                f"da Monitoramento (este layout não tem pasta de marcação).")
    return f"Vai para a pasta **{pasta_da_marcacao(marcacao)}**, acima da pasta do tipo."


def ajuda_campo_marca(forma_curta=False):
    """Texto de ajuda do campo de marca (bet).

    ENCURTADO EM 17/09/2026, mesmo pedido da ajuda_campo_marcacao: saiu a
    explicação de pasta/coluna, ficou o motivo de ser obrigatório."""
    if forma_curta:
        return "Obrigatória: é dado do contrato, o programa não descobre sozinho."
    return ("Obrigatória, e é o único campo que o programa não consegue "
            "descobrir sozinho: é informação de contrato, não está no link "
            "nem no vídeo.")


def aviso_marca_vazia():
    """Aviso mostrado quando a marca não foi escolhida, nos dois formulários."""
    if LAYOUT_PASTAS == LAYOUT_FUTEBOL:
        return ("Escolha a marca. Sem ela a Monitoramento fica sem essa "
                "informação, que o programa não descobre sozinho.")
    return ("Escolha a marca. Ela é a pasta de cima no Drive do Marketing "
            "(01. EDS, 02. ONA, 03. LOTTU, 04. EDSCAP), então sem ela o "
            "programa não tem onde guardar o vídeo.")


# TEXTO ÚNICO DO CAMPO CICLO, EM VEZ DE QUATRO DIFERENTES (14/09/2026).
#
# Os quatro formulários de download tinham cada um o seu: dois com um texto de
# ajuda parecido mas escrito diferente, dois sem ajuda nenhuma, e o placeholder
# variava entre "pela data" e "ex: 9". "Pela data" sozinho, sem explicar que
# significa "deixe vazio", foi apontado como confuso pelo auditor. Centralizado
# aqui, no mesmo padrão de `ajuda_campo_marca`, para os quatro formulários
# usarem a mesma frase.
PLACEHOLDER_CAMPO_CICLO = "número do ciclo"


def ajuda_campo_ciclo():
    """Texto de ajuda do campo Ciclo, igual nos quatro formulários de
    download.

    ENCURTADO EM 17/09/2026, pedido do auditor de resumir todo help=."""
    return ("Deixe em branco pra descobrir pela data, que é o caso normal. "
            "Preencha só se souber que é outro ciclo.")


def texto_da_marcacao(marcacao):
    """O que vai para a CÉLULA da planilha: ORGANICO ou LINK.

    SEM ACENTO, E ISSO NÃO É DETALHE (corrigido em 03/09/2026, pego por teste).
    A primeira versão gravava o nome da pasta em maiúscula, e o nome da pasta de
    orgânico tem acento porque é assim que está no Drive deles. O resultado era
    "ORGÂNICO" na planilha, ao lado de "LINK" sem acento.

    Por que importa mais que aparência: esta célula é lida de volta pelo programa
    e comparada por quem filtra na planilha. Valor com acento numa coluna cujos
    outros valores não têm é o tipo de coisa que faz um filtro do Google Sheets
    não casar, e a pessoa concluir que não há orgânicos naquele ciclo.

    A chave interna já é sem acento de propósito, então é dela que sai o texto.

    ACEITA CHAVE OU TEXTO DE CÉLULA, e isso é correção de uma armadilha que me
    pegou em 03/09/2026, ao padronizar a coluna na planilha de teste.

    A versão anterior só reconhecia CHAVE ("organico", "link"). Recebendo o
    conteúdo de uma célula antiga, "SIM", ela não achava a chave e caía no
    padrão: devolvia "LINK" para uma peça ORGÂNICA. Numa rotina de padronização
    isso trocaria a marcação de uma linha em silêncio, e como a marcação decide
    se a peça passa pela régua dos avisos, a linha voltaria a ser julgada por
    ela. Pego pela conferência antes de escrever, e não em produção.

    Passar por marcacao_de_celula primeiro resolve os dois casos com a mesma
    regra, e a de célula já sabe ler "SIM"."""
    return marcacao_de_celula(marcacao).upper()

# Tipo da Monitoramento -> nome da pasta. Só os três do Instagram: os outros
# tipos (YOUTUBE, LIVE, TIKTOK) não são baixados, entram pelo registro de link
# externo e não têm pasta.
PASTAS_POR_TIPO = {
    "STORIES": PASTA_STORY,
    "REELS": PASTA_REELS,
    "FEED": PASTA_FEED,
}

# GRAFIAS QUE VALEM AO PROCURAR, e isto não é firula.
#
# A comparação de nomes (ver chave_de_pasta) ignora espaço na borda e
# maiúscula, e nada além: para ela "story" e "stories" são palavras diferentes.
# As duas existem no Drive deles, medidas acima. Sem esta lista, o programa
# criaria uma pasta "story" ao lado da "stories" que já tem material, e o
# material do mesmo dia ficaria dividido entre as duas.
#
# A PRIMEIRA DA LISTA É A QUE O PROGRAMA CRIA quando nenhuma existe; as outras
# ele só aceita se encontrar. Story/stories é a variação MEDIDA, e ela vale 93
# pastas entre os ativos. Reel/reels e feed/feeds não foram medidos, e estão aqui
# por analogia com o que aconteceu no story: se a variação existir, é melhor
# achar a pasta deles do que criar uma segunda.
GRAFIAS_DA_PASTA_DE_TIPO = {
    PASTA_STORY: (PASTA_STORY, "stories"),
    PASTA_REELS: (PASTA_REELS, "reel"),
    PASTA_FEED: (PASTA_FEED, "feeds"),
}


def pasta_do_tipo(tipo):
    """Nome da pasta de mídia para um TIPO da Monitoramento.

    Tipo desconhecido ou vazio cai em "story", e isso é decisão consciente:
    esta parte do programa só baixa do Instagram, e na varredura dos ativos em
    01/09/2026 as pastas de tipo eram 387 de story contra 2 de reels e nenhuma
    de feed. Chutar o caso dominante deixa o arquivo junto do resto do dia;
    parar o download porque o tipo não foi reconhecido gastaria a chamada ao
    Instagram, que é o recurso escasso, sem guardar nada."""
    return PASTAS_POR_TIPO.get(str(tipo or "").strip().upper(), PASTA_STORY)


# A TRAVA QUE PERMITE O PROGRAMA CRIAR A PASTA DO INFLUENCIADOR (01/09/2026).
#
# POR QUE A REGRA MUDOU. Até hoje o programa não criava NADA de bet até
# influenciador, e o motivo era o erro de digitação no @: ali ele não tem como
# distinguir "@ escrito errado" de "influenciador novo", então criar produz pasta
# órfã que ninguém procura.
#
# O que mudou é que existe uma terceira via, e ela não é confiar em quem digita.
# São duas coisas juntas:
#
#   1. desde 30/08/2026 o @ NÃO É MAIS DIGITADO no caminho normal: sai do próprio
#      endereço do post ou dos dados que vêm com o vídeo
#   2. a Dados_influ é uma LISTA FECHADA de quem existe, com 203 linhas
#
# Então a proteção deixa de ser "nunca criar" e passa a ser "criar só para quem
# está no cadastro". No caso normal isso é zero clique, e continua barrando a
# pasta órfã, que era o que a regra antiga protegia.
#
# O QUE ISSO EVITA, medido: dos influenciadores com STATUS ATIVO, 29 não têm
# pasta nenhuma em 2026. Com a regra antiga, o primeiro download de cada um
# desses falha DEPOIS de a chamada ao Instagram já ter sido gasta, e alguém tem
# que ir ao Drive criar pasta à mão. Chamada ao Instagram é o recurso escasso do
# programa, e essa era a pior forma de gastá-la: sem guardar nada.
#
# NÃO EXIGE ESTAR ATIVO, de propósito. O que a trava precisa provar é que o @ é
# de uma pessoa real, e estar no cadastro já prova. Exigir ATIVO barraria
# download de quem postou e está com o status desatualizado na planilha, o que
# transformaria uma falha de cadastro numa falha de download.
ARQUIVO_CADASTRO_ID = os.path.join(PASTA_TESTE, "cadastro_planilha_id.txt")
ABA_CADASTRO = "Dados_influ"
COLUNA_CADASTRO_HANDLE = "INFLU"

# Níveis que o programa NUNCA cria: a bet e o ano. Não é conservadorismo, é que
# não há nada a ganhar: são 4 pastas de bet e 1 de ano por bet, todas já
# existentes, e criar errado na RAIZ do Drive deles é o erro mais caro possível.
NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA = 2

_cadastro_handles_cache = None


def handles_do_cadastro(recarregar=False):
    """Conjunto de @ (minúsculo, sem @) que existem na Dados_influ.

    Devolve None quando não consegue ler, e quem chama trata None como "não sei",
    NUNCA como "não está lá": falha de leitura não pode virar autorização para
    criar pasta, e também não deve virar acusação de @ inexistente."""
    global _cadastro_handles_cache
    if _cadastro_handles_cache is not None and not recarregar:
        return _cadastro_handles_cache
    planilha = ler_identificador(ARQUIVO_CADASTRO_ID)
    if not planilha:
        return None
    try:
        import sheets_client
        valores = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha, range=f"'{ABA_CADASTRO}'!A1:T",
            ).execute()).get("values", [])
        if not valores:
            return None
        cabecalho = [str(c).strip().upper() for c in valores[0]]
        indice = cabecalho.index(COLUNA_CADASTRO_HANDLE)
    except Exception:
        return None
    achados = set()
    for linha in valores[1:]:
        if len(linha) > indice:
            chave = chave_de_pasta(linha[indice])
            if chave:
                achados.add(chave)
    _cadastro_handles_cache = achados
    return achados


_cadastro_linhas_cache = None


def _ler_cadastro_completo(recarregar=False):
    """(cabeçalho, {handle: linha}) da Dados_influ. None quando não dá para ler.

    Guardado em memória por execução: um lote de downloads consulta isso uma vez
    por vídeo, e a planilha tem 203 linhas.

    QUEM CHAMA E QUER SABER SE UM @ ESPECÍFICO EXISTE precisa reler antes de
    desistir, do mesmo jeito que handles_do_cadastro já fazia (ver
    impedimento_para_criar_pasta). Até 23/09/2026 esta função não tinha essa
    segunda chance, e o efeito era pior que o da pasta: contrato novo
    cadastrado enquanto o trabalhador já estava de pé criava a pasta certo
    (aquela checagem relia), mas a linha da Monitoramento entrava com ESCOPO
    e datas de contrato em branco, porque dados_de_cadastro_para_a_linha lia
    só o que já estava em memória. Corrigido ali, chamando esta função com
    recarregar=True quando o @ não é achado na primeira tentativa."""
    global _cadastro_linhas_cache
    if _cadastro_linhas_cache is not None and not recarregar:
        return _cadastro_linhas_cache
    planilha = ler_identificador(ARQUIVO_CADASTRO_ID)
    if not planilha:
        return None
    try:
        import sheets_client
        valores = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha, range=f"'{ABA_CADASTRO}'!A1:T",
            ).execute()).get("values", [])
    except Exception:
        return None
    if not valores:
        return None
    cabecalho = [str(c).strip() for c in valores[0]]
    indice_handle = COL_MON["handle"] - 1
    por_handle = {}
    for linha in valores[1:]:
        if len(linha) <= indice_handle:
            continue
        chave = chave_de_pasta(linha[indice_handle])
        if chave and chave not in por_handle:
            por_handle[chave] = linha
    _cadastro_linhas_cache = (cabecalho, por_handle)
    return _cadastro_linhas_cache


def _cadastro_esta_alinhado(cabecalho_cadastro, cabecalho_monitoramento):
    """Se as duas planilhas continuam com as colunas na mesma posição.

    POR QUE CONFERIR ANTES DE COPIAR: o mapeamento é posicional, e posicional só
    é seguro enquanto ninguém inserir coluna em nenhuma das duas. Se alguém
    inserir, tudo desloca, e o programa gravaria por exemplo a data de fim de
    contrato dentro da coluna ESCOPO. Isso corromperia dado de auditoria em
    silêncio, sem erro nenhum na tela.

    A conferência usa os títulos que são escritos IGUAL nas duas planilhas
    (CATEGORIA, STATUS, ESCOPO). Os outros quatro não servem para isso, porque a
    grafia difere, e é justamente por isso que o mapeamento é posicional."""
    def normal(texto):
        return "".join(c for c in str(texto or "").lower() if c.isalnum())

    for numero, esperado in TITULOS_QUE_PROVAM_ALINHAMENTO.items():
        indice = numero - 1
        no_cadastro = normal(cabecalho_cadastro[indice]
                             if indice < len(cabecalho_cadastro) else "")
        no_monitoramento = normal(cabecalho_monitoramento[indice]
                                  if indice < len(cabecalho_monitoramento) else "")
        if no_cadastro != normal(esperado) or no_monitoramento != normal(esperado):
            return False, (
                f"a coluna {letra_da_coluna(numero)} deveria ser {esperado!r} nas "
                f"duas planilhas, e está {cabecalho_cadastro[indice] if indice < len(cabecalho_cadastro) else '(vazia)'!r} "
                f"no cadastro e {cabecalho_monitoramento[indice] if indice < len(cabecalho_monitoramento) else '(vazia)'!r} "
                f"na Monitoramento. Alguém inseriu ou removeu coluna, e copiar "
                f"por posição gravaria valor na coluna errada.")
    return True, ""


def dados_de_cadastro_para_a_linha(handle, cabecalho_monitoramento):
    """Valores das colunas C a J para aquele influenciador, ou (None, motivo).

    Devolve {numero_da_coluna: valor}, pronto para ser posto na linha nova.
    Nunca inventa: influenciador que não está no cadastro devolve vazio, e
    coluna vazia no cadastro continua vazia aqui."""
    lido = _ler_cadastro_completo()
    if not lido:
        return None, "não consegui ler o cadastro (Dados_influ)"
    cabecalho_cadastro, por_handle = lido

    alinhado, motivo = _cadastro_esta_alinhado(cabecalho_cadastro,
                                               cabecalho_monitoramento)
    if not alinhado:
        return None, motivo

    chave = chave_de_pasta(handle)
    linha_cadastro = por_handle.get(chave)
    if linha_cadastro is None:
        # ERRA UMA VEZ E RELÊ ANTES DE DESISTIR (23/09/2026), mesma regra de
        # impedimento_para_criar_pasta: contrato cadastrado agora só passa a
        # existir para quem já leu a planilha há horas se houver esta segunda
        # chance.
        lido_de_novo = _ler_cadastro_completo(recarregar=True)
        if lido_de_novo:
            _, por_handle = lido_de_novo
            linha_cadastro = por_handle.get(chave)
    if linha_cadastro is None:
        return None, f"@{chave} não está no cadastro"

    valores = {}
    for numero in range(PRIMEIRA_COLUNA_CADASTRO, ULTIMA_COLUNA_CADASTRO + 1):
        indice = numero - 1
        if indice < len(linha_cadastro):
            texto = str(linha_cadastro[indice]).strip()
            if texto:
                valores[numero] = texto
    return valores, ""


def impedimento_para_criar_pasta(nome):
    """Motivo para NÃO criar aquela pasta, ou None quando pode criar.

    Só olha a pasta do influenciador, que é a que começa com @. Os outros níveis
    criáveis (mês, data, tipo, orgânico) não dependem de ninguém digitar: o mês e
    a data vêm do vídeo, o tipo vem do endereço, e orgânico é sim ou não."""
    if not str(nome or "").startswith("@"):
        return None
    procurado = chave_de_pasta(nome)
    conhecidos = handles_do_cadastro()
    if conhecidos is None:
        return (f"Não consegui ler o cadastro de influenciadores para conferir se "
                f"\"{nome}\" existe, então não vou criar a pasta. O programa só cria "
                f"pasta de influenciador para quem está na Dados_influ, porque um @ "
                f"escrito errado cria pasta que ninguém procura. Confira o acesso à "
                f"planilha do cadastro e mande de novo.")
    if procurado in conhecidos:
        return None
    # ERRA UMA VEZ E CONFERE DE NOVO ANTES DE BARRAR. Influenciador novo entra no
    # cadastro deles a qualquer momento, e o conjunto fica guardado na memória do
    # trabalhador, que roda por horas. Sem esta releitura, alguém acrescentado
    # hoje só passaria depois de reiniciar o programa.
    conhecidos = handles_do_cadastro(recarregar=True)
    if conhecidos and procurado in conhecidos:
        return None
    return (f"\"{nome}\" não está no cadastro de influenciadores (aba "
            f"{ABA_CADASTRO}), então o programa não criou a pasta. Duas coisas "
            f"causam isso: o @ está diferente do que está cadastrado, ou é alguém "
            f"que ainda não foi cadastrado. Se o @ está certo, peça o cadastro ao "
            f"Marketing; se está errado, corrija a linha e mande de novo. A pasta "
            f"não é criada de propósito: @ errado espalha o mesmo influenciador "
            f"por várias pastas do Drive, e nada avisa quando isso acontece.")


def nome_de_pasta_a_conferir(nome):
    """Se vale avisar na tela quando o programa CRIAR uma pasta com esse nome.

    Só as pastas de PALAVRA, que são a do tipo e as três de marcação. A pasta do
    dia fica de fora de propósito: ela é criada uma vez por influenciador por
    dia, então avisar sobre ela seriam dezenas de linhas iguais por rodada, e
    aviso que aparece sempre é aviso que ninguém lê.

    A diferença entre elas é grafia. "01/09" só tem uma forma de escrever;
    "story" tem pelo menos três no Drive deles, e para "reels" e "feed" nem há
    grafia medida ainda.

    As três de marcação entram aqui com motivo reforçado (03/09/2026): a medição
    daquele dia mostrou que só existiam "orgânico" e "link" AO LADO do tipo, e
    nenhum nível abaixo dele, na pasta
    deles, em 60 influenciadores lidos. São nomes novos, escolhidos por nós, e
    nome novo é justamente o que precisa ser conferido na primeira vez."""
    alvo = str(nome or "").strip().lower()
    return (alvo in GRAFIAS_DA_PASTA_DE_TIPO
            or alvo in set(PASTA_DA_MARCACAO.values()))


def nomes_aceitos_de_pasta(nome):
    """Nomes que valem como a pasta `nome` na hora de PROCURAR no Drive.

    Devolve sempre uma sequência, com o nome pedido na frente. Para pasta que
    não tem variação conhecida, devolve só ela mesma, então o resto do caminho
    (bet, ano, mês, @influenciador, DD/MM) continua exigindo o nome exato, a
    menos da tolerância de sempre a espaço e maiúscula.

    DIVULGAÇÕES/DIVULGAÇÃO (layout futebol, 12/09/2026) é tolerância à parte,
    e não entra em GRAFIAS_DA_PASTA_DE_TIPO porque não é uma pasta de TIPO."""
    chave = str(nome or "").strip().lower()
    if chave == PASTA_DIVULGACOES.lower():
        return GRAFIAS_PASTA_DIVULGACOES
    return GRAFIAS_DA_PASTA_DE_TIPO.get(chave, (nome,))


def pasta_da_data(data_video):
    """Nome da pasta do dia, no formato que o Marketing já usa nas pastas
    "DD/MM - bruto" deles.

    A BARRA É PROPOSITAL E É UM RISCO CONHECIDO: no Google Drive ela é nome
    válido, no Windows é separador de pasta, e isso já quebrou o programa três
    vezes num dia. Aqui ela só vai para o Drive. Quem gravar em disco tem que
    passar por nome_para_disco."""
    return data_video.strftime("%d/%m") if data_video else "sem-data"


def pastas_dentro_do_influenciador(rotulo_ciclo, data_video=None, tipo=None,
                                   marcacao=None):
    """Pastas entre a do influenciador e o arquivo.

    MUDOU EM 01/09/2026, e a mudança é a maior desta parte: a pasta de CICLO
    DEIXOU DE EXISTIR NO DRIVE. O ciclo passa a viver só na coluna CICLO da
    Monitoramento, que é onde ele sempre foi usado de verdade.

    POR QUE ISSO FAZ SENTIDO: pasta de ciclo e pasta de data guardavam a mesma
    informação por caminhos diferentes, e os ciclos se sobrepõem, então o mesmo
    dia podia pertencer a dois. Data é fato do vídeo; ciclo é interpretação de
    contrato. Fato vira pasta, interpretação vira campo de planilha.

    O `rotulo_ciclo` continua no parâmetro porque quem chama já o tem em mão, e
    tirá-lo obrigaria a mexer em todas as chamadas sem ganho nenhum. Ele
    simplesmente não entra mais no caminho.

    Os dois layouts passam a ter a MESMA estrutura, de propósito: o de teste
    existe para ensaiar o do Marketing, e com árvores diferentes ele deixaria de
    ensaiar coisa nenhuma.

    `tipo`: o TIPO da Monitoramento (STORIES, REELS, FEED), que decide a pasta
    de mídia. Ele não é digitado por ninguém: sai do próprio endereço do post
    (ver tipo_pelo_link), então esta pasta não depende de alguém acertar.

    `marcacao`: o que a peça é, orgânico ou link. Ela fica
    ACIMA do tipo desde 03/09/2026, e antes era uma pasta "orgânico" ABAIXO dele.
    Os dois motivos da inversão estão no comentário de PASTA_ORGANICO: a medição
    mostrou que a pasta deles não tem nível nenhum abaixo do tipo, e as três
    marcações são excludentes, então elas descrevem a peça inteira e não um
    detalhe do tipo.

    Este é o único dos níveis que depende de uma pessoa marcar, e é por isso que
    ele também é gravado na planilha, onde dá para conferir e filtrar. Vazio cai
    em link, que é a peça publicitária comum (ver marcacao_de_celula).

    O LAYOUT FUTEBOL PASSOU A TER OS MESMOS TRÊS NÍVEIS (21/09/2026), pela
    mesma decisão registrada em caminho_ate_influenciador: o desenho de
    12/09 (sem pasta de dia, sem marcação, sem tipo, só DIVULGAÇÕES / MM.
    MÊS) foi substituído. Por isso este ramo especial saiu, e os três
    layouts caem todos na mesma linha de baixo."""
    return [pasta_da_data(data_video), pasta_da_marcacao(marcacao),
            pasta_do_tipo(tipo)]


def descer_pelo_caminho(id_raiz, segmentos, listar, criar=None,
                        percorrido_inicial="Drive", criar_somente_ultimos=None,
                        avisar=None, autorizar=None,
                        pasta_conhecida=None, lembrar_pasta=None):
    """Desce a árvore de pastas, e devolve o id da última.

    `listar(id_pai)` -> lista de {"name", "id"}. `criar(nome, id_pai)` -> id,
    ou None para proibir a criação. Recebe as duas de fora de propósito: sem
    isso não haveria como testar a regra sem falar com o Drive.

    `pasta_conhecida(nome, id_pai)` -> id já visto antes, ou None, e
    `lembrar_pasta(nome, id_pai, id)` para gravar (25/09/2026, achado ao
    vivo). SEM ISSO, toda pasta que já existe passa pela BUSCA de novo em
    toda chamada, para sempre, mesmo tendo sido achada mil vezes antes. Isso
    não é só desperdício: com duas pastas de mesmo nome já existindo como
    irmãs (aconteceu de verdade com "03. LOTTU", sobra de dois dias de
    teste), a busca por listagem pode devolver uma ou outra em ordem
    diferente a cada chamada, e cada chamada nova corre o risco de escolher
    a pasta errada de novo, mesmo depois de ter escolhido a certa da última
    vez. `pasta_conhecida` é consultada ANTES de listar (pula a busca ao
    vivo inteira quando já sabe a resposta), e `lembrar_pasta` grava assim
    que a pasta é achada por listagem, não só quando é criada (a criação já
    tinha essa proteção, ver obter_ou_criar_pasta). As duas são opcionais,
    de propósito: sem elas, o comportamento é o de antes de 25/09/2026,
    sempre perguntando ao Drive.

    A comparação é a tolerante (ver chave_de_pasta): ignora maiúscula e TODO
    espaço, e nada além. É o que faz o programa encontrar "01. Janeiro ",
    "08. AGOSTO" e "05.MAIO", que existem assim no Drive do Marketing, em vez de
    criar uma segunda pasta ao lado de cada uma.

    Com criar=None, uma pasta que falta interrompe tudo, dizendo qual é e onde
    ela deveria estar.

    `criar_somente_ultimos`: quantos segmentos DO FIM podem ser criados. None
    quer dizer "todos", que é o comportamento do layout de teste.

    QUEM CRIA O QUÊ, E POR QUÊ (revisado em 01/09/2026)

    A premissa do projeto é facilitar a vida de quem usa: quanto menos o analista
    tiver que criar, melhor. E o custo de errar por falta de pasta não é uma
    mensagem na tela: o vídeo já foi baixado quando o envio falha, então a chamada
    ao Instagram, que é o recurso escasso do programa, foi gasta para nada.

    Então o corte é por QUEM ESCOLHE O NOME, e não por nível:

        bet, ano                   nunca cria. São 5 pastas que já existem, então
                                   não há nada a ganhar, e criar errado na raiz do
                                   Drive deles é o erro mais caro possível
        mês                        cria. Medido em 01/09/2026: a comparação
                                   tolerante encontra TODAS as 19 pastas de mês
                                   que existem em 2026, então criar só acontece
                                   quando o mês de fato não existe, que é dia 1º
        @influenciador             cria, com a trava do cadastro. Ver
                                   impedimento_para_criar_pasta
        data, tipo, orgânico       cria. Nenhum depende de alguém digitar: a data
                                   vem do vídeo, o tipo vem do endereço do post,
                                   orgânico é sim ou não

    `autorizar(nome)` (01/09/2026): chamada só no momento de criar, devolve um
    motivo para não criar, ou None. É por ela que a trava do cadastro entra, sem
    esta função precisar saber o que é um influenciador.

    `avisar` (01/09/2026): recebe uma frase por pasta CRIADA. Existe porque criar
    pasta em silêncio é o que transforma um nome errado em quarenta pastas
    duplicadas antes de alguém notar. A pasta do tipo tem grafia variável no
    Drive deles (medido: "story" 411, "stories" 133), e para reels e feed não há
    grafia medida, só a palavra. Com o aviso, um nome fora do padrão aparece na
    tela no primeiro dia."""
    id_atual = id_raiz
    percorrido = percorrido_inicial
    total = len(segmentos)
    for indice, nome in enumerate(segmentos):
        # O CACHE VEM ANTES DE QUALQUER LISTAGEM (25/09/2026): se este nível
        # já foi resolvido antes, nem pergunta ao Drive. Sem isso, uma pasta
        # já conhecida ainda passava pela busca de novo em toda chamada, e
        # com duplicata já existente (ver docstring) essa busca podia trocar
        # de resposta a cada vez.
        if pasta_conhecida:
            id_ja_sabido = pasta_conhecida(nome, id_atual)
            if id_ja_sabido:
                id_atual = id_ja_sabido
                percorrido = f"{percorrido} / {nome}"
                continue
        # Uma listagem só, e depois as grafias aceitas para este nível. Nos
        # níveis sem variação conhecida isso é exatamente o que era antes; na
        # pasta de tipo, é o que faz "story" encontrar a "stories" deles em vez
        # de criar uma segunda pasta ao lado (ver nomes_aceitos_de_pasta).
        id_pai_deste_nivel = id_atual
        subpastas = listar(id_atual)
        achado = nome_real = None
        for candidato in nomes_aceitos_de_pasta(nome):
            achado, nome_real = achar_pasta_tolerante(candidato, subpastas)
            if achado:
                break
        if achado:
            id_atual = achado
            percorrido = f"{percorrido} / {nome_real}"
            if lembrar_pasta:
                lembrar_pasta(nome, id_pai_deste_nivel, achado)
            continue
        pode_criar_aqui = criar is not None and (
            criar_somente_ultimos is None
            or indice >= total - criar_somente_ultimos)
        if not pode_criar_aqui:
            raise PastaNaoExisteNoDrive(
                f"A pasta \"{nome}\" não existe em {percorrido}. O programa não cria "
                f"pasta nesse nível deste Drive, de propósito: criar quando "
                f"o nome está só um pouco diferente produz duas pastas para a mesma "
                f"coisa. Crie \"{nome}\" ali e mande de novo.")
        # A CONFERÊNCIA ACONTECE AQUI, e não antes de descer: só interessa quando
        # a pasta de fato não existe. Influenciador que já tem pasta não precisa
        # de conferência nenhuma, e conferir de qualquer jeito custaria uma
        # leitura da planilha do cadastro em todo download.
        if autorizar:
            impedimento = autorizar(nome)
            if impedimento:
                raise PastaNaoExisteNoDrive(impedimento)
        onde = percorrido
        id_atual = criar(nome, id_atual)
        percorrido = f"{percorrido} / {nome}"
        if avisar and nome_de_pasta_a_conferir(nome):
            avisar(f"[Drive] criei a pasta \"{nome}\" em {onde}. Se esse não é o nome "
                   f"que o time usa, avise: renomear hoje é simples, e em um mês "
                   f"seriam dezenas de pastas duplicadas ao lado das certas.")
    return id_atual


def _descer_criando(segmentos, criar_somente_ultimos=0, avisar=None,
                    autorizar=None):
    """Caminho até a pasta de destino.

    No layout do Marketing, só os `criar_somente_ultimos` últimos níveis podem
    ser criados; o resto tem que existir, porque são pastas deles. Com 0, que é
    o padrão, nada é criado.

    No layout de teste tudo é criado, porque ali a árvore é nossa. Isso NÃO
    significa árvore diferente: desde 01/09/2026 a estrutura é a mesma nos dois,
    para o layout de teste servir de ensaio de verdade.

    A TRAVA DO CADASTRO (`autorizar`) VALE NO LAYOUT DO MARKETING E NO
    FUTEBOL (12/09/2026), e a escolha tem motivo. Ela existe para proteger o
    Drive de quem não é nosso de pasta órfã; no Drive de teste não há nada a
    proteger. E ligada nos três, ela impediria o ensaio de todo o resto: o
    teste real da árvore feito em 01/09/2026 usou @teste.hierarquia.0109, que
    obviamente não está no cadastro do Marketing, e seria barrado antes de
    exercitar estrutura, nome de arquivo e numeração de tela. No layout
    futebol, desde o redesenho de 21/09/2026, a pasta do influenciador
    também é achada pelo @ (igual ao Marketing), então a trava passou a
    valer do mesmo jeito nos dois: antes, com a pasta achada pelo mapa
    @->apelido, era o mapa que protegia aquele nível, não esta trava.

    A regra em si não fica sem prova: ela é conferida com dublê de cadastro em
    testes\teste_pastas_do_marketing.py, seções 7 e 8, que testam mais fundo do
    que um ensaio no Drive conseguiria (inclui cadastro ilegível, que não dá para
    provocar de propósito)."""
    import drive_client_upload
    listar = lambda id_pai: drive_client_upload.listar_arquivos(id_pai, so_pastas=True)
    if LAYOUT_PASTAS in (LAYOUT_MARKETING, LAYOUT_FUTEBOL):
        # Só cosmético, para a mensagem de erro citar o nome certo da raiz
        # configurada. No futebol, desde 21/09/2026, essa raiz é a pasta
        # "Divulgações" que a Responsável B mantém, e é dentro dela que a bet
        # (LOTTU, EDS, ...) já existe.
        rotulo_raiz = ("VÍDEOS INFLUENCIADORES" if LAYOUT_PASTAS == LAYOUT_MARKETING
                       else "Divulgações")
        return descer_pelo_caminho(
            _pasta_raiz_drive(), segmentos, listar,
            criar=(drive_client_upload.obter_ou_criar_pasta
                   if criar_somente_ultimos else None),
            percorrido_inicial=rotulo_raiz,
            criar_somente_ultimos=criar_somente_ultimos, avisar=avisar,
            autorizar=autorizar,
            pasta_conhecida=drive_client_upload.pasta_conhecida,
            lembrar_pasta=drive_client_upload.lembrar_pasta)
    return descer_pelo_caminho(_pasta_raiz_drive(), segmentos, listar,
                               criar=drive_client_upload.obter_ou_criar_pasta,
                               avisar=avisar,
                               pasta_conhecida=drive_client_upload.pasta_conhecida,
                               lembrar_pasta=drive_client_upload.lembrar_pasta)


def _pasta_do_influenciador(handle_limpo, data_video, marca=None, criar=True):
    """Pasta do influenciador, no layout configurado. Com criar=False devolve
    None se ela ainda não existir, em vez de criar uma vazia."""
    import drive_client_upload
    try:
        segmentos = caminho_ate_influenciador(handle_limpo, data_video, marca)
    except (BetNaoInformada, PastaNaoExisteNoDrive):
        # Com criar=False a pergunta é "a pasta existe?". Se nem dá para montar
        # o caminho (falta a bet ou a data), a resposta é não, e quem pergunta
        # não deve receber uma exceção no meio de uma conferência.
        if not criar:
            return None
        raise
    if criar:
        return _descer_criando(segmentos)
    # Mesma comparação tolerante da descida que cria: procurar de um jeito e
    # criar de outro faria o programa não achar "01. Janeiro " e concluir que
    # não há nada lá, quando há.
    id_atual = _pasta_raiz_drive()
    for nome in segmentos:
        id_atual, _real = achar_pasta_tolerante(
            nome, drive_client_upload.listar_arquivos(id_atual, so_pastas=True))
        if not id_atual:
            return None
    return id_atual


def _pasta_de_destino_drive(handle_limpo, rotulo_ciclo, data_video=None,
                            marca=None, tipo=None, marcacao=None, avisar=None):
    """Pasta onde o arquivo vai ficar. Cache em memória por execução, já que
    vários vídeos do mesmo influenciador costumam ser processados na mesma
    rodada.

    QUEM É CRIADO E QUEM NÃO É (revisado em 01/09/2026): só a bet e o ano NÃO são
    criados. Mês, influenciador, data, marcação e tipo são criados quando
    faltarem, e o do influenciador passa pela trava do cadastro.

    POR QUE A BET E O ANO FICAM DE FORA: são 4 pastas de bet e 1 de ano por bet,
    todas já existentes, então criar não pouparia trabalho de ninguém, e criar
    errado na RAIZ do Drive deles é o erro mais caro que este programa pode
    cometer.

    POR QUE O MÊS ENTROU: medido em 01/09/2026, a comparação tolerante encontra
    TODAS as 19 pastas de mês que existem em 2026, inclusive "01. Janeiro ",
    "08. AGOSTO" e "05.MAIO". Então criar só acontece quando o mês de fato não
    existe, que é dia 1º, e nesse dia alguém teria que criar de qualquer jeito.

    POR QUE O INFLUENCIADOR ENTROU, com trava: ver impedimento_para_criar_pasta.

    O QUE A MUDANÇA POUPA, em número: eram cerca de 49 pastas por mês para alguém
    criar à mão (uma por influenciador ativo, mais a do mês em cada bet), e dos
    influenciadores com STATUS ATIVO 29 não tinham pasta nenhuma em 2026. Cada um
    desses era um download que falhava DEPOIS de gastar a chamada ao Instagram,
    que é o recurso escasso do programa.

    Quantos níveis podem ser criados sai do TAMANHO do caminho, e não de um número
    escrito à mão. Isso já teria evitado um defeito: quando a pasta de orgânico
    entrou, um 2 fixo aqui passaria a permitir criar a pasta do influenciador sem
    que ninguém tivesse decidido isso.

    NO LAYOUT FUTEBOL (21/09/2026, redesenho que substituiu o de 12/09) SÓ A
    BET FICA DE FORA, não bet e ano como nos outros dois: a raiz configurada
    para a Responsável B já é a pasta "Divulgações" dela, então a bet (LOTTU, EDS,
    ...) é o único nível que já existe de antemão e nunca deve ser criado, e
    não existe nível de ano nesse layout para proteger. Por isso protege só 1
    nível, em vez de `NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA` (calibrado para bet e
    ano juntos, que só vale para os outros dois)."""
    chave = (handle_limpo, LAYOUT_PASTAS,
             data_video.strftime("%Y-%m-%d") if data_video else "",
             str(marca or ""), pasta_do_tipo(tipo), pasta_da_marcacao(marcacao))
    if chave in _pastas_drive_cache:
        return _pastas_drive_cache[chave]
    dentro = pastas_dentro_do_influenciador(rotulo_ciclo, data_video, tipo, marcacao)
    segmentos = caminho_ate_influenciador(handle_limpo, data_video, marca) + dentro
    if LAYOUT_PASTAS == LAYOUT_FUTEBOL:
        niveis_criaveis = max(0, len(segmentos) - 1)  # só a bet fica de fora
    else:
        niveis_criaveis = max(0, len(segmentos) - NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA)
    destino = _descer_criando(
        segmentos,
        criar_somente_ultimos=niveis_criaveis,
        avisar=avisar, autorizar=impedimento_para_criar_pasta)
    _pastas_drive_cache[chave] = destino
    return destino


# Nome antigo, mantido por um tempo para não quebrar chamada de fora. O nome
# novo diz o que a função faz agora: o destino não é mais uma pasta de ciclo.
_pasta_ciclo_drive = _pasta_de_destino_drive

_pastas_bruto_cache = {}


def _pasta_de_video_bruto(handle_limpo, data_video, marca=None, avisar=None):
    """Pasta "vídeo bruto" do dia, para o material que o influenciador manda
    antes só para conferência informal, sem edição.

    PEDIDO DO MARKETING, TRAZIDO PELO AUDITOR EM 22-23/09/2026: uma sessão que
    só pede @ e o arquivo, sobe para "a pasta daquele handle ou cria uma,
    mesmo esquema de como já funciona", e a pasta de vídeo bruto fica dentro
    da pasta do dia.

    ISTO NÃO CONTRADIZ A DECISÃO DE 01/09/2026 de que material bruto é fora
    do escopo do programa (ver PASTA_BRUTO, e_pasta_de_bruto). Aquela decisão
    é sobre ANÁLISE: o programa nunca abre pasta de bruto para conferir aviso
    de jogo responsável, e continua sem abrir, porque a listagem que soube
    disso (procurar_arquivo_repetido) já pula qualquer pasta com esse nome, e
    esta função escreve exatamente numa pasta com esse nome. O vídeo sobe,
    fica visível para quem confere manualmente, e nunca entra na fila de
    validação nem ganha linha na Monitoramento, porque quem chama esta função
    (enviar_video_bruto) não faz nenhuma das duas coisas.

    SEM MARCAÇÃO E SEM TIPO, de propósito: esta pasta não é sobre orgânico,
    link, story ou reels, é sobre o material não ter passado por edição
    nenhuma ainda. Por isso o caminho é
    caminho_ate_influenciador(...) + [pasta_da_data(...), PASTA_BRUTO], e não
    pastas_dentro_do_influenciador, que é para o material já editado.

    A trava do cadastro (impedimento_para_criar_pasta) vale aqui do mesmo
    jeito que em todo resto do programa: pasta de @ errado não é criada."""
    chave = (handle_limpo, LAYOUT_PASTAS,
             data_video.strftime("%Y-%m-%d") if data_video else "", str(marca or ""))
    if chave in _pastas_bruto_cache:
        return _pastas_bruto_cache[chave]
    segmentos = caminho_ate_influenciador(handle_limpo, data_video, marca) + [
        pasta_da_data(data_video), PASTA_BRUTO]
    if LAYOUT_PASTAS == LAYOUT_FUTEBOL:
        niveis_criaveis = max(0, len(segmentos) - 1)  # só a bet fica de fora
    else:
        niveis_criaveis = max(0, len(segmentos) - NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA)
    destino = _descer_criando(
        segmentos, criar_somente_ultimos=niveis_criaveis,
        avisar=avisar, autorizar=impedimento_para_criar_pasta)
    _pastas_bruto_cache[chave] = destino
    return destino


def enviar_video_bruto(nome_arquivo, dados, handle_manual, marca, data_video=None,
                       log_fn=print, pedido_por=None):
    """Sobe um vídeo NÃO editado, para a pasta "vídeo bruto" do dia.

    NÃO VALIDA, NÃO CRIA LINHA NA MONITORAMENTO, de propósito (pedido do
    Marketing, 22-23/09/2026): é só o influenciador confirmando com o próprio
    time que o material está certo antes de editar, e não a peça publicitária
    final. Tratar isso como entrega criaria linha de auditoria para um vídeo
    que ainda vai virar outra coisa.

    `data_video` sem valor cai em hoje: quem manda a peça antes está mandando
    agora, não numa data futura que ainda não existe."""
    nome = os.path.basename(str(nome_arquivo))
    agora_texto = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_video = data_video or datetime.now().date()

    def _registrar(**campos):
        registro = dict(quando=agora_texto, estagio="BRUTO", origem=nome,
                        handle="", data_video="", ciclo="", destino="", status="",
                        quem=pedido_por or "")
        registro.update(campos)
        gravar_log([registro])
        return registro

    if os.path.splitext(nome)[1].lower() not in EXTENSOES_VIDEO:
        log_fn(f"[Bruto] {nome}: formato não aceito (só vídeo).")
        return _registrar(status="FORMATO NAO ACEITO")

    handle = str(handle_manual or "").strip().lstrip("@").lower()
    if not handle:
        log_fn(f"[Bruto] {nome}: informe o influenciador antes de enviar.")
        return _registrar(status="SEM HANDLE")

    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, nome_para_disco(nome))
            with open(caminho, "wb") as f:
                f.write(dados)
            import drive_client_upload
            id_pasta = _pasta_de_video_bruto(handle, data_video, marca, avisar=log_fn)
            _id_arquivo, link = drive_client_upload.enviar_arquivo(caminho, nome_para_disco(nome), id_pasta)
    except Exception as e:
        log_fn(f"[Bruto] {nome}: falhou ao subir pro Drive. {str(e)[:160]}")
        return _registrar(handle="@" + handle, data_video=str(data_video),
                          status=f"FALHA: {str(e)[:160]}")

    log_fn(f"[Bruto] {nome}: @{handle}, {data_video}. Subiu pra pasta de vídeo bruto do dia.")
    return _registrar(handle="@" + handle, data_video=str(data_video),
                      destino=link, status="OK")


def _impressao_digital(caminho):
    """Impressão digital do conteúdo do arquivo, no mesmo formato que o Drive
    usa. É o que reconhece o mesmo vídeo mesmo salvo com outro nome.

    MD5 AQUI NÃO É ESCOLHA DE SEGURANÇA, É COMPATIBILIDADE: é o algoritmo que a
    API do Drive expõe como `md5Checksum` de cada arquivo, e comparar com ele é
    o que permite achar duplicata sem baixar o arquivo de novo. Não defende
    contra ataque nenhum, só identifica conteúdo repetido; por isso o
    `usedforsecurity=False`, que documenta a intenção em vez de deixar
    ferramenta de análise estática marcar como uso criptográfico de MD5
    (achado do parecer de cibersegurança de 04/09/2026, severidade "alta" no
    Bandit por classificação genérica, não por risco real)."""
    import hashlib
    h = hashlib.md5(usedforsecurity=False)
    with open(caminho, "rb") as f:
        for pedaco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(pedaco)
    return h.hexdigest()


# Nome de arquivo no padrão que o Marketing já usa nas pastas deles, visto em
# 28/08/2026: "27/08 - @dudafreiret - tela 2". Adotado para que o material que
# a automação sobe fique indistinguível do que eles sobem à mão, e para que dê
# pra ligar uma LINHA da Monitoramento ao ARQUIVO certo: o link da planilha
# aponta pra pasta do mês inteiro, então sem data e número de tela no nome não
# há como saber a qual post um veredito se refere.
_REGEX_NOME_MARKETING = re.compile(
    r"^(?P<dia>\d{2})/(?P<mes>\d{2})\s*-\s*@(?P<handle>[^\s-]+)\s*-\s*tela\s*(?P<tela>\d+)",
    re.IGNORECASE,
)

# O PADRÃO NOVO, SEM A DATA NO NOME (01/09/2026): "@handle - tela N".
#
# A data saiu do nome porque passou a existir pasta do dia no caminho, então ela
# não se perdeu: mudou de lugar. Guardar a mesma informação duas vezes é o que
# cria divergência quando alguém corrige uma das duas.
#
# O SEPARADOR " - " ENTROU EM 02/09/2026, a pedido do auditor, para ficar igual
# ao que o Marketing escreve à mão. E ESTA REGRA ACEITA OS DOIS: com hífen e sem.
# Sem isso, os arquivos que o programa já criou hoje, no formato "@handle Tela N",
# deixariam de ser reconhecidos, e a numeração recomeçaria do 1 em cima deles.
#
# A LEITURA ACEITA TRAÇO, SUBLINHADO OU ESPAÇO, a pedido do auditor ("colocar um
# traço ou underline"). Escrever é sempre com o traço, que é o que está na pasta
# deles; a folga é para ler o que vier de quem sobe à mão.
#
# O sublinhado convive com @ que tem sublinhado, como @ranchodomaia__ e
# @lf_freitas, porque o @ é ganancioso: ele fica com o pedaço mais longo, e sobra
# para o separador só o sublinhado que vem imediatamente antes de "tela".
#
# O separador é EXIGIDO, ainda que possa ser qualquer um dos três. Torná-lo
# opcional fazia "@fulanotela3" ser lido como tela 3 do @fulano, e um arquivo com
# nome parecido entraria na contagem de outro influenciador.
#
# O PADRÃO ANTIGO DO MARKETING CONTINUA SENDO RECONHECIDO à parte, e isso não é
# gentileza: as pastas deles estão cheias de arquivos "DD/MM - @handle - tela N",
# e é lendo esses nomes que o programa sabe em qual número de tela continuar.
_REGEX_NOME_NOVO = re.compile(
    r"^@?(?P<handle>[A-Za-z0-9_.]+)(?:\s*[-_]\s*|\s+)tela\s*(?P<tela>\d+)",
    re.IGNORECASE,
)


def ler_nome_de_arquivo(nome):
    """Devolve (handle, tela) de um nome de arquivo, nos dois padrões, ou None.

    Não devolve a data de propósito: no padrão novo ela não está no nome, e quem
    precisa da data usa a pasta em que o arquivo está."""
    texto = str(nome or "").strip()
    m = _REGEX_NOME_MARKETING.match(texto)
    if m:
        return m.group("handle").lower(), int(m.group("tela"))
    m = _REGEX_NOME_NOVO.match(texto)
    if m:
        return m.group("handle").lower(), int(m.group("tela"))
    return None


def nome_para_disco(nome):
    """Mesmo nome, mas gravável no Windows.

    O padrão do Marketing é "DD/MM - @handle - tela N", e a barra é válida como
    nome de arquivo no Google Drive, que não é sistema de arquivos. No Windows
    ela é separador de pasta: gravar assim faz o programa procurar uma pasta
    "14" que não existe e falhar com "caminho não encontrado". Só a cópia local
    de teste passa por aqui; o nome no Drive continua exatamente o do
    Marketing, senão o casamento por nome deixaria de funcionar."""
    for proibido in '/\\:*?"<>|':
        nome = nome.replace(proibido, "-")
    return nome


def nome_no_padrao_marketing(handle_limpo, data_video, tela, caminho_origem):
    """Monta o nome do arquivo: "@handle - tela N", com a extensão no fim para o
    arquivo continuar abrindo direito.

    O SEPARADOR VIROU " - " EM 02/09/2026, a pedido do auditor olhando o arquivo
    no Drive: "pode deixar o padrão do nome algo como @ranchodomaia__ - tela 1?".
    Era "@handle Tela N". O ganho é ficar igual ao que o Marketing escreve à mão,
    que é "DD/MM - @handle - tela N": mesmo separador, mesma caixa em "tela".

    A DATA CONTINUA FORA DO NOME, e isso é decisão de 01/09/2026, não descuido:
    ela é a pasta do dia no caminho, então não se perdeu, mudou de lugar. Guardar
    a mesma informação nos dois lugares é o que cria divergência quando alguém
    corrige só um deles.

    Quem mexer aqui tem que mexer em _REGEX_NOME_NOVO junto: é ela que lê esses
    nomes de volta para saber em qual número de tela continuar. Nome que o
    programa escreve e não consegue ler faz a numeração recomeçar do 1 e criar
    dois "tela 1" no mesmo dia."""
    extensao = os.path.splitext(str(caminho_origem))[1].lower()
    return f"@{handle_limpo} - tela {int(tela)}{extensao}"


def proxima_tela(handle_limpo, data_video, marca=None):
    """Próximo número de tela livre daquele influenciador naquela data.

    Olha os arquivos que já estão na pasta dele e pega o maior número de tela
    usado para aquele dia, somando um. Assim a numeração continua de onde o
    Marketing parou, em vez de recomeçar do 1 e criar dois "tela 1" no mesmo
    dia.

    COMO A DATA É DECIDIDA MUDOU EM 01/09/2026. Antes ela vinha do NOME do
    arquivo, porque o nome a trazia e todos os arquivos do influenciador ficavam
    juntos. Agora existe pasta do dia, e o nome novo não tem data: então o que
    define "aquele dia" é a PASTA em que o arquivo está.

    Isso é mais confiável que antes, e não menos: nome pode ser digitado errado
    por quem sobe à mão, pasta não, porque ela é o caminho de fato.

    Continua contando os arquivos no padrão antigo, que existem às centenas nas
    pastas do Marketing. Sem isso a numeração recomeçaria do 1 e criaria dois
    "Tela 1" no mesmo dia.

    Falha segura: se não der pra consultar o Drive, devolve 1. O número pode
    ser corrigido à mão na tela."""
    if not data_video:
        return 1
    pasta_do_dia = pasta_da_data(data_video)
    usados = []
    try:
        for pasta, arquivo in _arquivos_do_influenciador(handle_limpo, data_video, marca):
            lido = ler_nome_de_arquivo(arquivo.get("name", ""))
            if not lido:
                continue
            handle_do_nome, numero_tela = lido
            if handle_do_nome != handle_limpo:
                continue
            # Conta o que está na pasta do dia, e também o que está na pasta do
            # influenciador com o nome antigo (que carrega a data nele) e casa
            # com este dia. As duas coisas convivem enquanto houver material
            # antigo nas pastas deles.
            na_pasta_do_dia = str(pasta or "").strip().startswith(pasta_do_dia)
            m_antigo = _REGEX_NOME_MARKETING.match(str(arquivo.get("name", "")))
            do_mesmo_dia_pelo_nome = bool(
                m_antigo and f"{m_antigo.group('dia')}/{m_antigo.group('mes')}" == pasta_do_dia)
            if na_pasta_do_dia or do_mesmo_dia_pelo_nome:
                usados.append(numero_tela)
    except Exception:
        return 1
    return max(usados) + 1 if usados else 1


def procurar_arquivo_repetido(handle_limpo, nome_no_drive, caminho_local,
                              data_video=None, marca=None):
    """Confere se esse vídeo já está no Drive, em QUALQUER ciclo daquele
    influenciador. Devolve o arquivo encontrado (com nome e link) ou None.

    Olha todos os ciclos, não só o de destino, de propósito: já aconteceu de o
    mesmo vídeo cair em ciclo errado, e conferir só a pasta de destino deixaria
    passar exatamente esse caso. Custa uma listagem a mais por envio.

    Confere por duas vias, e basta uma delas bater:

    1. Nome do arquivo, que é determinístico (vem do identificador do post na
       origem), então o mesmo post baixado de novo gera o mesmo nome.
    2. Conteúdo, comparando a impressão digital que o Drive já calcula. Pega o
       caso do mesmo vídeo salvo com nome diferente.

    Falha segura ao contrário das outras funções: se a consulta ao Drive der
    errado, devolve None (deixa subir). Impedir um envio legítimo por causa de
    uma falha de rede seria pior que um arquivo repetido, que é visível e dá
    pra apagar."""
    try:
        digital = _impressao_digital(caminho_local)
        for pasta_nome, arquivo in _arquivos_do_influenciador(handle_limpo, data_video, marca):
            mesmo_nome = bool(nome_no_drive) and arquivo.get("name") == nome_no_drive
            mesmo_conteudo = bool(digital) and arquivo.get("md5Checksum") == digital
            if mesmo_nome or mesmo_conteudo:
                # "onde" e não "ciclo" (31/08/2026): o que vem aqui é o nome da
                # pasta em que o arquivo está, e no layout do Marketing não
                # existe pasta de ciclo. Ali isto é o nome da pasta do
                # influenciador ou de uma pasta "DD/MM - bruto", e chamar de
                # ciclo fazia a mensagem dizer o que não era.
                return {**arquivo, "onde": pasta_nome, "ciclo": pasta_nome,
                        "por": "nome" if mesmo_nome else "conteúdo"}
    except Exception:
        return None
    return None


def _arquivos_do_influenciador(handle_limpo, data_video=None, marca=None,
                               profundidade=3):
    """Percorre os arquivos da pasta do influenciador e das subpastas dela,
    devolvendo (nome_da_pasta, arquivo).

    DESCE TRÊS NÍVEIS DESDE 01/09/2026, E ISSO JÁ ERA UM DEFEITO DE VERDADE
    QUANDO ERA UM.

    Ela descia UM nível, o que bastava quando a árvore era
    "@influenciador / Ciclo N / arquivos". Com a estrutura nova, os arquivos
    ficam em "@influenciador / DD/MM / story / arquivos", dois níveis abaixo, e
    a função não os enxergava. O terceiro nível entrou junto com a pasta de
    orgânico, que fica dentro da do tipo: sem ele, arquivo de post orgânico
    ficaria invisível exatamente como os outros ficaram.

    O CUSTO É REAL E CONHECIDO: é uma listagem por pasta visitada, e um
    influenciador com um mês de material tem dezenas delas. Isso pesa em cada
    envio, porque tanto a numeração de tela quanto a conferência de vídeo
    repetido passam por aqui. Reduzir a profundidade não é o caminho: foi
    justamente o que fez os dois defeitos abaixo.

    O QUE REDUZ O CUSTO SEM PERDER NADA é pular as pastas de material bruto, e
    foi a medição do Drive deles que mostrou o tamanho disso: das pastas dentro
    da pasta do dia, 127 eram de bruto e 124 de story, então pular bruto corta
    metade das visitas. E não é só economia: material bruto está FORA do escopo
    do programa por decisão registrada, a análise já o ignorava (é a mesma lista
    de termos, NOMES_SUBPASTA_IGNORADA), e o auditor confirmou em 01/09/2026 que
    os brutos vão para outro Drive. Descer neles só criaria a chance de acusar
    reaproveitamento comparando um vídeo publicado com a versão não editada dele.

    O sintoma que apareceu no primeiro teste real: dois arquivos do mesmo dia
    saíram os dois como "Tela 1", porque proxima_tela não via o primeiro e
    respondia 1 sempre.

    O ESTRAGO MAIOR ERA OUTRO, e não aparecia no teste: procurar_arquivo_repetido
    usa esta mesma função. Sem ver os arquivos, a detecção de vídeo reaproveitado
    parava de funcionar em silêncio, e reaproveitamento é achado de contrato.

    Continua servindo para as duas árvores, a nova e o que já está lá: no
    Marketing existem arquivos soltos na pasta do influenciador, e todos
    aparecem.

    O nome devolvido é o caminho relativo da pasta onde o arquivo está, e não só
    o último nome. Quem precisa saber o dia compara com o COMEÇO desse caminho,
    porque a pasta do tipo e a de orgânico ficam dentro da pasta do dia."""
    import drive_client_upload
    id_handle = _pasta_do_influenciador(handle_limpo, data_video, marca, criar=False)
    if not id_handle:
        return

    def descer(id_pasta, rotulo, resta):
        for arquivo in drive_client_upload.listar_arquivos(id_pasta):
            if arquivo.get("mimeType") != "application/vnd.google-apps.folder":
                yield rotulo, arquivo
        if resta <= 0:
            return
        for sub in drive_client_upload.listar_arquivos(id_pasta, so_pastas=True):
            if e_pasta_de_bruto(sub.get("name")):
                continue
            # O rótulo carrega o caminho relativo, e não só o último nome: sem
            # isso, um arquivo dentro de "01/09 / story" seria devolvido como
            # estando em "story", e quem conta telas do dia não teria como saber
            # de qual dia era.
            yield from descer(sub["id"], f"{rotulo} / {sub['name']}"
                              if rotulo != "@" + handle_limpo else sub["name"],
                              resta - 1)

    yield from descer(id_handle, "@" + handle_limpo, profundidade)


def normalizar_ciclo(valor):
    """Aceita o que a pessoa digitar ("9", "Ciclo 9", " ciclo 9 ") e devolve
    sempre no formato usado nas pastas do Drive. Vazio devolve None, que quer
    dizer "deixa o programa descobrir"."""
    txt = str(valor or "").strip()
    if not txt:
        return None
    numero = re.sub(r"(?i)^ciclo\s*", "", txt).strip()
    if re.fullmatch(r"\d+(\.0)?", numero):
        return f"Ciclo {int(float(numero))}"
    return f"Ciclo {numero}" if not txt.lower().startswith("ciclo") else txt


def enviar_para_drive(caminho_video, handle, data_video, ciclo_manual=None,
                      marca=None, tipo=None, link_original=None, log_fn=None,
                      tela=None, marcacao=None, pedido_por=None):
    """Sobe o vídeo para a pasta do dia do influenciador. Devolve
    (link_do_arquivo_no_drive, rotulo_do_ciclo).

    O DESTINO MUDOU EM 03/09/2026, e a marcação subiu para cima do tipo:

        bet / ano / mês / @influenciador / DD/MM / {orgânico|link} / story

    Antes era `... / DD/MM / story [ / orgânico ]`. Ver o comentário de
    PASTA_ORGANICO para os dois motivos, que são medição e definição, não gosto.

    O `rotulo_do_ciclo` continua sendo devolvido, e continua importando: é ele
    que vai para a coluna CICLO da Monitoramento. O que ele deixou de ser é
    pasta. Ciclo é interpretação de contrato e vive na planilha; data é fato do
    vídeo e vive no caminho.

    `marcacao`: o que a peça é, uma das três. Vira pasta E coluna MARCACAO na
    Monitoramento. As duas coisas no mesmo ato de propósito: a pasta é para achar
    o arquivo no Drive, a coluna é para filtrar e contar, e é a coluna que a
    análise lê. Se isso conta ou não como entrega de contrato não é o programa
    que diz.

    ciclo_manual: quando vem preenchido, manda no lugar do ciclo que o programa
    descobriria sozinho. Existe porque os ciclos na Monitoramento se sobrepõem
    com frequência (medido em 26/08/2026: metade dos influenciadores tem faixas
    sobrepostas, e cerca de um terço dos posts de 2026 cabe em mais de um
    ciclo), então a descoberta automática acerta na maioria mas não sempre.

    marca: a bet do influenciador (EDS, LOTTU, ONA ou EDSCAP), que vai pra
    coluna MARCA da Monitoramento. tipo e link_original servem pra preencher a
    coluna TIPO; sem eles, o tipo é deduzido do endereço."""
    import drive_client_upload
    avisar = log_fn or (lambda m: None)
    handle_limpo = str(handle).strip().lstrip("@").lower()
    rotulo_ciclo = normalizar_ciclo(ciclo_manual) or inferir_ciclo(handle_limpo, data_video)

    # O TIPO É DECIDIDO AQUI, UMA VEZ SÓ (01/09/2026).
    #
    # Ele era deduzido do endereço lá dentro de registrar_na_monitoramento, e só
    # servia para a coluna TIPO. Agora ele também decide a PASTA, então precisa
    # ser o mesmo valor nos dois lugares. Deduzir duas vezes, em dois lugares,
    # é como coluna e pasta acabam discordando.
    tipo = (tipo or tipo_pelo_link(link_original) or "").upper() or None

    # Confere repetição ANTES de reservar número de tela: se o vídeo já está
    # lá, gastar um número criaria um buraco na sequência. A conferência aqui
    # vai sem nome de propósito, e vale pelo conteúdo do arquivo: com a
    # numeração de tela, o mesmo vídeo enviado de novo ganharia um nome
    # diferente, então nome deixou de ser sinal confiável de repetição.
    repetido = procurar_arquivo_repetido(handle_limpo, None, caminho_video,
                                         data_video=data_video, marca=marca)
    if repetido:
        # PEÇA REAPROVEITADA: NÃO SOBE DE NOVO, MAS A LINHA TEM QUE EXISTIR.
        #
        # CORRIGIDO EM 31/08/2026, e o que havia aqui era o contrário do que a
        # auditoria precisa. Antes esta função RETORNAVA aqui, sem criar a linha
        # na Monitoramento. O efeito, quando o influenciador republicava um
        # vídeo antigo numa data nova:
        #
        #   o segundo post não ganhava linha e nunca era auditado
        #   o reaproveitamento não ficava registrado em lugar nenhum
        #   a fila marcava "BAIXADO E ORGANIZADO", que lê como sucesso
        #
        # Ou seja: o programa engolia em silêncio exatamente o achado que
        # deveria levantar. Reaproveitar vídeo é vedado em CONTRATO, conforme o
        # auditor confirmou, então o segundo post é uma peça publicitária nova,
        # numa data nova, e precisa de linha própria e veredito próprio.
        #
        # O arquivo, esse não se duplica: a linha nova aponta para o que já
        # está lá. Duas cópias idênticas no Drive não ajudariam ninguém.
        nome_antigo = repetido.get("name") or "(sem nome)"

        # PEDIDO DE DENTRO NÃO É REAPROVEITAMENTO (01/09/2026).
        #
        # Mesma detecção, reação diferente, e a diferença importa: acusar
        # descumprimento de contrato por causa de uma operação de rotina é pior
        # que não acusar nada, porque quem lê a planilha não tem como saber que
        # aquela marca não valia.
        #
        # O pedido é consumido aqui: vale para este download e não para sempre.
        pedido = consumir_rebaixamento_pedido(link_original)
        if pedido:
            quem_pediu = pedido.get("quem") or "alguém do time"
            avisar(f"[Rebaixado a pedido] Este arquivo é igual, byte a byte, a "
                   f"\"{nome_antigo}\", que já está na pasta \"{repetido['onde']}\". "
                   f"NÃO é peça reaproveitada pelo influenciador: o rebaixamento foi "
                   f"pedido em {pedido.get('quando')} por {quem_pediu}. O arquivo não "
                   f"é duplicado, e a linha aponta para o que já existe.")
        else:
            # "PEÇA" E NÃO "VÍDEO" (02/09/2026): desde que story de foto passou a
            # ser baixado, esta acusação alcança imagem também, e chamar foto de
            # vídeo numa marca que vai para a planilha da auditoria é dizer
            # errado sobre a peça que está sendo acusada.
            avisar(f"[ATENÇÃO] PEÇA REAPROVEITADA: este arquivo é byte a byte igual a "
                   f"\"{nome_antigo}\", que já está na pasta \"{repetido['onde']}\". "
                   f"Reaproveitar peça é vedado em contrato. A linha vai ser criada "
                   f"assim mesmo, apontando para o arquivo que já existe, para o post "
                   f"novo não ficar sem auditoria.")
        link_existente = repetido.get("webViewLink")
        try:
            numero_linha = registrar_na_monitoramento(
                handle_limpo, data_video, rotulo_ciclo, link_existente,
                marca=marca, tipo=tipo, link_original=link_original,
                marcacao=marcacao, pedido_por=pedido_por, avisar=avisar)
            if numero_linha:
                avisar(f"[Monitoramento] linha {numero_linha} criada para o post "
                       f"reaproveitado, aguardando validação.")
            else:
                avisar("[Monitoramento] esse post já tinha linha na planilha, não dupliquei.")
        except Exception as e:
            avisar(f"[Monitoramento] ATENÇÃO: não consegui criar a linha do post "
                   f"reaproveitado: {str(e)[:200]}")
        # O segundo valor devolvido é o rótulo do ciclo, que vai para a planilha.
        # Vale o ciclo que ESTE envio calculou, e não o nome da pasta onde o
        # arquivo estava: no layout do Marketing aquele nome não é ciclo nenhum.
        return link_existente, rotulo_ciclo

    id_pasta_ciclo = _pasta_de_destino_drive(handle_limpo, rotulo_ciclo, data_video,
                                             marca, tipo=tipo, marcacao=marcacao,
                                             avisar=avisar)
    numero_tela = int(tela) if str(tela or "").strip().isdigit() else \
        proxima_tela(handle_limpo, data_video, marca=marca)
    nome_arquivo = nome_no_padrao_marketing(handle_limpo, data_video, numero_tela, caminho_video)
    _id_arquivo, link = drive_client_upload.enviar_arquivo(caminho_video, nome_arquivo, id_pasta_ciclo)

    if MANTER_COPIA_LOCAL_DE_TESTE:
        # Espelho local de teste. Falhar aqui NÃO pode derrubar o envio: o
        # vídeo já está no Drive, que é o destino de verdade, e a cópia é só
        # conveniência de conferência.
        try:
            destino_dir = os.path.join(DRIVE_SIMULADO, "@" + handle_limpo, rotulo_ciclo)
            os.makedirs(destino_dir, exist_ok=True)
            shutil.copy2(caminho_video,
                         os.path.join(destino_dir, nome_para_disco(nome_arquivo)))
        except OSError as e:
            avisar(f"[Drive] vídeo salvo no Drive, mas não consegui guardar a cópia "
                   f"local de teste: {str(e)[:120]}")

    # O vídeo fica na pasta do Drive, e a linha vai para a Monitoramento de
    # teste com DOIS endereços: a pasta na coluna LINK e o arquivo na coluna
    # ARQUIVO. Ver ("arquivo", "AD") em BLOCO_AUTOMACAO para o porquê.
    try:
        numero_linha = registrar_na_monitoramento(
            handle_limpo, data_video, rotulo_ciclo, link,
            marca=marca, tipo=tipo, link_original=link_original,
            marcacao=marcacao, pedido_por=pedido_por,
            link_pasta=link_de_pasta_no_drive(id_pasta_ciclo), avisar=avisar)
        if numero_linha:
            # DIZ QUAL DAS TRÊS, e não só quando é orgânico: a marcação agora
            # decide a pasta E vai valer para a régua da análise, então quem
            # está olhando a tela precisa ver o que foi gravado.
            avisar(f"[Monitoramento] linha {numero_linha} criada, aguardando "
                   f"validação. Marcada como {texto_da_marcacao(marcacao)}.")
        else:
            avisar("[Monitoramento] esse vídeo já tinha linha na planilha, não dupliquei.")
    except Exception as e:
        # Falhar aqui não pode perder o vídeo, que já está no Drive. Mas TAMBÉM
        # não pode passar em branco: antes esta falha só ia pro console, que
        # ninguém lê, e o resultado era vídeo no Drive sem linha na planilha,
        # sem nada na tela explicando. Aconteceu em 28/08/2026 e levou tempo
        # pra descobrir, porque o registro dizia "OK".
        avisar(f"[Monitoramento] ATENÇÃO: o vídeo subiu pro Drive, mas NÃO consegui "
               f"criar a linha na planilha: {str(e)[:200]}. Ele não vai entrar na fila "
               f"de validação até isso ser resolvido.")

    return link, rotulo_ciclo


# ------------------------------------------------------------------
# Registro na Monitoramento de teste
# ------------------------------------------------------------------
def _planilha_monitoramento_id():
    if modo_real_autorizado():
        return ler_identificador(ARQUIVO_MONITORAMENTO_REAL_ID)
    return ler_identificador(ARQUIVO_MONITORAMENTO_ID)


# HORAS DE LIVE NO FORMATO HH:MM:SS, e não em número decimal (04/09/2026,
# pedido do auditor: "é exatamente como tá na planilha deles"). Guardar como
# texto no mesmo formato que o Marketing já usa evita duas representações
# distintas da mesma coisa dentro da mesma coluna: uma live registrada aqui
# como "1:30:00" e outra digitada por eles como "01:45:20" continuam
# comparáveis e ordenáveis do mesmo jeito.
REGEX_HORAS_LIVE = re.compile(r"^(\d{1,3}):([0-5]\d):([0-5]\d)$")

# H:MM OU HH:MM, SEM SEGUNDO (16/09/2026, achado testando a formatação
# automática): antes, digitar "01:00" pensando em 1 hora saía errado e CALADO,
# virando "00:01:00" (1 minuto). O motivo é que só existia o atalho "só
# dígitos" logo abaixo, e ele lê os dois-pontos como se não estivessem lá,
# reagrupando os 4 dígitos "0100" como minuto e segundo, sobrando hora zero.
# Só que quem digita "01:00" com os dois-pontos está dizendo hora e minuto, não
# minuto e segundo. Esta regex nova trata esse caso ANTES do atalho de
# dígitos, completando com ":00" de segundo. NÃO É CHUTE: a pessoa disse
# explicitamente onde a hora termina e o minuto começa, colocando o
# dois-pontos; falta só o segundo, que fica zero por convenção, igual ao
# atalho de dígitos já faz.
REGEX_HORAS_LIVE_SEM_SEGUNDO = re.compile(r"^(\d{1,3}):([0-5]\d)$")


def normalizar_horas_live(texto):
    """HH:MM:SS com hora, minuto e segundo com dois dígitos, ou vazio.

    NÃO CHUTA: "90 min" ou lixo qualquer devolve vazio em vez de uma conversão
    adivinhada. Duração de live é dado que vai para o mesmo lugar que o
    Marketing usa para calcular horas contratadas; inventar segundo ou minuto
    que ninguém digitou seria pior do que pedir para digitar de novo.

    ACEITA SÓ OS DÍGITOS SEGUIDOS, sem os dois-pontos (16/09/2026, pedido do
    auditor: "só colocar o número e a configuração fica automática"). "13000"
    ou "013000" viram "01:30:00": os dois últimos pares são segundo e minuto, o
    que sobra é a hora. Continua sem chutar quando o resultado não é minuto ou
    segundo válido (ex: "13099" teria segundo 99).

    SÓ COM 5 OU 6 DÍGITOS (17/09/2026, mesmo defeito do comentário de
    REGEX_HORAS_LIVE_SEM_SEGUNDO, achado de novo pelo auditor: "0150" pensando
    em 1 hora e 50 minutos saía CALADO como "00:01:50", 1 minuto e 50). Com
    menos de 5 dígitos, "os dois últimos pares são segundo e minuto" vira uma
    leitura tão válida quanto a que a pessoa tinha na cabeça (poderia ser
    HH:MM sem os zeros), e não tem como saber qual das duas é a certa. Sem
    dígito suficiente para decidir sozinho, devolve vazio e deixa a tela
    pedir para tentar de novo, com os dois-pontos (1:50) ou os 6 dígitos
    (015000) — os dois já sem essa ambiguidade."""
    bruto = str(texto or "").strip()
    achado = REGEX_HORAS_LIVE.match(bruto)
    if achado:
        h, m, s = achado.groups()
        return f"{int(h):02d}:{m}:{s}"
    achado_sem_segundo = REGEX_HORAS_LIVE_SEM_SEGUNDO.match(bruto)
    if achado_sem_segundo:
        h, m = achado_sem_segundo.groups()
        return f"{int(h):02d}:{m}:00"
    apenas_digitos = re.sub(r"\D", "", bruto)
    if apenas_digitos and len(apenas_digitos) in (5, 6):
        h, m, s = apenas_digitos[:-4] or "0", apenas_digitos[-4:-2], apenas_digitos[-2:]
        if int(m) < 60 and int(s) < 60:
            return f"{int(h):02d}:{m}:{s}"
    return ""



def tipo_pelo_link(link):
    """TIPO da Monitoramento deduzido do endereço, no vocabulário deles."""
    texto = str(link or "").lower()
    if "/stories/" in texto:
        return "STORIES"
    if "/reel/" in texto or "/reels/" in texto:
        return "REELS"
    if "instagram.com" in texto and "/p/" in texto:
        return "FEED"
    if "youtu" in texto:
        return "YOUTUBE"
    if "tiktok" in texto:
        return "TIKTOK"
    if "twitter" in texto or "x.com" in texto:
        return "X/TWITTER"
    if "threads.net" in texto or "threads.com" in texto:
        return "THREADS"
    return None


# ---------------------------------------------------------------------------
# LER DATA DE CÉLULA, EM VEZ DE COMPARAR TEXTO
# ---------------------------------------------------------------------------
# POR QUE ISTO EXISTE (07/09/2026)
#
# O auditor baixou duas telas do mesmo story, no mesmo dia, e elas saíram como
# POST 1 e POST 2: "cada pacote de story conta como 1 post, ou seja, aqui era
# para estar post 1 e 1". Ele estava certo, e o efeito é grave: a cota do
# contrato é contada em POSTS, então duas telas do mesmo dia viravam duas
# entregas onde houve uma, inflando a conferência de cota sem ninguém perceber.
#
# A REGRA ESTAVA CERTA, A COMPARAÇÃO ESTAVA ERRADA. `_numero_do_post` já
# reaproveitava o número do mesmo dia desde 03/09/2026. O que falhava era como
# ela reconhecia "mesmo dia": comparando TEXTO.
#
# O programa grava "06/09/2026". O Google Sheets reconhece aquilo como DATA,
# guarda como número de série e, na leitura, devolve no formato de exibição da
# coluna: "06/09/26". Então "06/09/26" != "06/09/2026", cada tela parecia um dia
# diferente, e o número incrementava.
#
# NUNCA COMPARAR DATA COMO TEXTO quando a planilha é a camada de guarda: o
# formato de exibição é do Marketing, muda quando eles quiserem, e não é
# contrato de dado. Compara-se a DATA.
# A REGRA MORA EM data_de_planilha.py DESDE 07/09/2026. Ela saiu daqui porque
# a revisao do dia mostrou que a correcao tinha ficado pela metade em dois
# outros lugares, e um deles e o escopo_e_entrega.py, que e modulo puro. Os
# nomes ficam reexportados para nao mexer em quem ja chamava.
import data_de_planilha

_FORMATOS_DE_DATA = data_de_planilha.FORMATOS
data_de_celula = data_de_planilha.data_de_celula
mesmo_dia = data_de_planilha.mesmo_dia
chave_de_dia = data_de_planilha.chave_de_dia

def _numero_do_post(linhas, handle, ciclo, tipo, data_post, marcacao=None):
    """A coluna POST numera o POST dentro do ciclo, por tipo E POR MARCAÇÃO.

    ENTREGA DO MESMO DIA É O MESMO POST (03/09/2026), e isso mudou a conta.

    O Marketing sinalizou ao auditor, e ele repassou: "em entregas no mesmo dia
    (sequencia de stories por exemplo), eles devem ser considerados o mesmo post,
    ex: esses dois da Jubrasil deveriam ser POST 1 E 1".

    Antes esta função contava LINHAS e somava um, então uma sequência de três
    stories do mesmo dia saía como POST 1, 2 e 3. Passou a contar DIAS
    DISTINTOS: as peças do mesmo dia recebem o mesmo número, e cada dia novo
    ganha o próximo.

    POR QUE ISSO IMPORTA MAIS QUE ARRUMAÇÃO: a cota do contrato é contada em
    posts. Com a conta antiga, um influenciador que publicasse cinco telas num
    dia aparecia como cinco posts entregues, e a conferência de cota ficava
    inflada sem ninguém perceber.

    A MARCAÇÃO SEPARA POSTS, e isso é decisão dele depois de falar com o
    Marketing, no mesmo dia: "a peça orgânica nunca pode ser link ao mesmo tempo,
    além disso, elas não contam como MESMO POST como é o caso do story em
    sequencia por exemplo, são tipos de entrega diferentes mesmo".

    Ou seja, um orgânico e um link no MESMO dia são DOIS posts, e não um. Sem a
    marcação na chave, os dois cairiam no mesmo número e a cota contaria uma
    entrega onde houve duas, que é o erro contrário ao que esta função conserta.

    Reaproveita o número que JÁ ESTÁ na planilha para aquele dia, em vez de
    recalcular: se alguém corrigiu o número à mão, a correção dele manda."""
    i_h = COL_MON["handle"] - 1
    i_c = COL_MON["ciclo"] - 1
    i_t = COL_MON["tipo"] - 1
    i_d = COL_MON["data_post"] - 1
    i_p = COL_MON["post"] - 1
    i_m = COL_MON["marcacao"] - 1
    alvo = str(handle).strip().lstrip("@").lower()
    dia_alvo = data_de_celula(data_post)
    marcacao_alvo = marcacao_de_celula(marcacao)

    outros_dias = []
    for linha in linhas:
        def campo(i):
            return str(linha[i]).strip() if len(linha) > i and linha[i] is not None else ""
        if (campo(i_h).lstrip("@").lower() != alvo
                or campo(i_t).upper() != tipo
                or campo(i_c).replace(".0", "") != str(ciclo)
                # Passa pela leitura de célula, e não por comparação de texto: a
                # coluna tem "SIM" nas linhas de até 02/09 e "ORGANICO" nas
                # novas, e as duas querem dizer orgânico.
                or marcacao_de_celula(campo(i_m)) != marcacao_alvo):
            continue
        dia = campo(i_d)
        if dia_alvo and mesmo_dia(dia, dia_alvo):
            # Mesmo dia: usa o número que já está lá. Só se for número mesmo,
            # porque célula vazia ou com texto não responde nada.
            ja_gravado = campo(i_p).replace(".0", "")
            if ja_gravado.isdigit():
                return int(ja_gravado)
            # O DIA ALVO NÃO ENTRA NA CONTAGEM, e isto é correção de um defeito
            # que o teste pegou antes de rodar em produção. Ele entrava, e o dia
            # que já existia sem número usável recebia o número SEGUINTE: a
            # segunda peça do mesmo dia saía como 2, que é exatamente o que esta
            # função existe para evitar.
            continue
        # OS OUTROS DIAS TAMBÉM SE CONTAM COMO DATA (07/09/2026). A revisão do
        # dia pegou a correção pela metade: o dia ALVO já passava pelo leitor de
        # data, mas esta lista ainda deduzia por TEXTO. Com "05/09/26" numa
        # linha e "05/09/2026" em outra, o mesmo dia entrava duas vezes,
        # `len(outros_dias) + 1` devolvia um número maior que a posição real e a
        # cota, que é contada em POSTS, voltava a inflar. Mesmo defeito, mesma
        # causa, outro lugar.
        chave_do_dia = chave_de_dia(dia)
        if chave_do_dia and chave_do_dia not in outros_dias:
            outros_dias.append(chave_do_dia)

    # Conta os OUTROS dias e soma um. Com o dia alvo já presente, isso devolve a
    # posição dele na sequência; com dia novo, o próximo número.
    #
    # Sem data, cada peça vira um post próprio, porque não há como saber se é do
    # mesmo dia de outra, e agrupar por engano juntaria peças de dias diferentes
    # sob o mesmo post.
    return len(outros_dias) + 1


def garantir_cabecalhos_automacao(planilha):
    """Escreve os títulos do bloco da automação (W a AB) nos que ainda não
    tiverem um.

    Essas colunas são acrescentadas pela automação, então na primeira vez elas
    não existem na planilha. Escrever só o título, e só onde está vazio, evita
    coluna sem nome que alguém confunda com sujeira. NUNCA sobrescreve título
    existente: se alguém renomeou, a escolha da pessoa manda."""
    import sheets_client
    try:
        faixa = f"'{ABA_MONITORAMENTO}'!{PRIMEIRA_COLUNA_AUTOMACAO}1:{ULTIMA_COLUNA_MON}1"
        atuais = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha, range=faixa).execute()).get("values", [[]])
        atuais = (atuais[0] if atuais else []) + [""] * len(BLOCO_AUTOMACAO)
        novos, faltava = [], False
        for i, (_chave, _letra, titulo, _para_que) in enumerate(BLOCO_AUTOMACAO):
            tem = str(atuais[i]).strip()
            novos.append(tem or titulo)
            faltava = faltava or not tem
        if not faltava:
            return
        sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().update(
            spreadsheetId=planilha, range=faixa,
            valueInputOption="USER_ENTERED", body={"values": [novos]},
        ).execute())
    except Exception:
        pass  # título é cosmético: não pode impedir o registro da linha


def _caminho_trava_entre_instalacoes(planilha_id):
    """Trava ENTRE PROCESSOS, e não só entre threads (18/09/2026).

    POR QUE ESTA EXISTE, além da trava de 16/09 já feita em
    registrar_na_monitoramento: aquela usa sheets_client._TRAVA_DA_API, que é
    um threading.RLock. Um RLock vive na memória de UM processo só. No
    servidor, as instalações do Marketing e do Futebol são dois processos
    `trabalhador.py`/`painel.py` diferentes escrevendo na MESMA Monitoramento
    real (mesmo id de planilha, layouts de Drive diferentes), e cada processo
    tem a sua própria cópia do RLock na memória: uma não sabe que a outra
    está no meio da leitura+escrita. É a mesma corrida que a trava de 16/09
    fechou, um nível acima (processo, não thread), achada ao planejar a
    subida de duas instalações lado a lado no mesmo servidor.

    O arquivo de trava fica FORA da pasta de qualquer instalação, em
    %ProgramData% (cai na pasta temporária se a variável não existir), que é
    o mesmo lugar físico para qualquer processo desta máquina, de qualquer
    pasta. Nomeado pelo ID DA PLANILHA, não pelo layout: as duas instalações
    que escrevem na mesma Monitoramento caem sozinhas no mesmo arquivo, sem
    precisar de nenhuma configuração igual nas duas cópias, e planilha de
    teste nunca disputa a mesma trava que a planilha real."""
    import tempfile
    pasta_base = os.environ.get("ProgramData") or tempfile.gettempdir()
    pasta = os.path.join(pasta_base, "AuditoriaInfluenciadores")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, f"monitoramento_{planilha_id}.lock")


def registrar_na_monitoramento(handle, data_video, rotulo_ciclo, link_drive,
                               marca=None, tipo=None, link_original=None,
                               analisavel=True, marcacao=None,
                               pedido_por=None, link_pasta=None, avisar=None,
                               horas_live=None, pagamento=None):
    """Acrescenta uma linha na Monitoramento de TESTE com o que a automação
    sabe do vídeo: influenciador, mês, ano, data, ciclo, tipo, número do post,
    marca, onde o material está no Drive e a data em que ele foi capturado.

    `link_drive` é o arquivo EXATO daquela peça, e vai para a coluna ARQUIVO.
    `link_pasta` é a pasta do post, e vai para a coluna LINK. Quando a pasta não
    vem, a coluna LINK recebe o arquivo, que é o comportamento de antes de
    03/09/2026 e o que vale para link externo, que não tem pasta.

    POR QUE SÃO DUAS COLUNAS: ver o comentário de ("arquivo", "AD") em
    BLOCO_AUTOMACAO. Em resumo: entrega do mesmo dia é UM post, então a coluna
    que o Marketing lê aponta para a pasta do dia; a análise e a evidência
    precisam da peça exata.

    `marcacao`: escreve na coluna MARCACAO qual das três a peça é (ORGANICO,
    ou LINK). É por esta coluna que quem confere cota separa os grupos, e é
    ela que vai valer para a régua da análise. O quanto cada grupo conta como
    entrega de contrato é decisão de quem lê o contrato, não daqui.

    `pedido_por`: identidade de quem pediu o download, que vai para a coluna
    PEDIDO_POR. NÃO é o mesmo que o RESPONSÁVEL INTERNO da coluna F: aquele diz
    quem cuida do influenciador, este diz quem fez a ação. Ver BLOCO_AUTOMACAO.

    AS COLUNAS C A J TAMBÉM SÃO PREENCHIDAS, do cadastro (02/09/2026). O
    Marketing as preenchia à mão copiando da Dados_influ, coluna por coluna,
    porque as duas planilhas começam com as mesmas colunas na mesma ordem. O
    auditor autorizou o programa a fazer o mesmo. Ver PRIMEIRA_COLUNA_CADASTRO.

    Só o que a automação não tem de onde tirar continua vazio: CRONOGRAMA,
    PAGAMENTO e observação. As duas primeiras são preenchidas à mão na
    planilha, por decisão do auditor em 05/09/2026 (ver o comentário perto de
    COL_MON). HORAS DE LIVE é a única exceção: quando `horas_live` vem
    preenchido (registro de link externo do tipo LIVE, onde a pessoa digita à
    mão), ele vai para a coluna própria.

    `pagamento` continua aceito como parâmetro, e nasce None. Nenhum caminho do
    programa passa valor nele hoje. Ele fica porque a coluna existe e um dia o
    programa pode voltar a preenchê-la; passar valor aqui é escolha explícita
    de quem chama, nunca o padrão.

    Devolve o número da linha criada, ou None se a planilha de teste não
    estiver configurada.

    TENTA DE NOVO SOB COLISÃO ENTRE MÁQUINAS (18/09/2026). As travas acima
    (RLock de 16/09, trava de arquivo de 18/09) só valem dentro desta máquina.
    Duas instalações em máquinas FÍSICAS diferentes (o caso real da Responsável A e
    da Responsável B, mesma Monitoramento real, credencial e Drive já compartilhados
    por elas) não caem no mesmo arquivo de trava nenhuma das duas, então a
    corrida de calcular a mesma próxima linha continua possível entre elas.
    Por isso, depois de escrever, esta função RELÊ a própria linha: se o que
    está lá não é o que ela mandou, outra instalação escreveu por cima no
    meio do caminho, e ela tenta tudo de novo, com a contagem de linhas
    renovada. Ver _uma_tentativa_de_registro mais abaixo."""
    import random
    import time
    import sheets_client
    dizer = avisar or (lambda m: None)
    planilha = _planilha_monitoramento_id()
    if not planilha:
        return None

    tipo = (tipo or tipo_pelo_link(link_original) or "").upper() or None
    handle_limpo = "@" + str(handle).strip().lstrip("@").lower()
    ciclo_num = re.sub(r"(?i)^ciclo\s*", "", str(rotulo_ciclo or "")).strip()

    garantir_cabecalhos_automacao(planilha)

    # ATRASO SÓ PARA O TESTE DE REPRODUÇÃO DA CORRIDA (18/09/2026), inerte em
    # uso normal: a variável só existe quando ferramentas\testar_corrida_...
    # a define, para alargar de propósito a janela entre ler e escrever e
    # tornar a colisão determinística em vez de depender da sorte do tempo de
    # rede. Sem a variável, `_atraso_teste` é 0 e este trecho não faz nada.
    _atraso_teste = float(os.environ.get("AUDITORIA_TESTE_ATRASO_CORRIDA_MONITORAMENTO") or 0)

    def _uma_tentativa_de_registro():
        """Uma rodada de ler, montar a linha e escrever. Devolve
        ("ja_registrada", None), ("colidiu", None) ou ("ok", numero_linha).
        "colidiu" é o sinal para quem chamou tentar de novo."""
        # SOB A TRAVA DA API, DO LEITURA ATE A ESCRITA (16/09/2026), achado
        # respondendo pergunta do auditor sobre o servidor com varios
        # analistas ao mesmo tempo. SEM ISSO: esta funcao le quantas linhas
        # a Monitoramento tem, calcula a proxima linha vazia, e SO DEPOIS
        # escreve nela; cada sheets_client.executar() prende a trava so
        # durante a propria chamada, entao entre o "ler quantas linhas tem"
        # e o "escrever na linha seguinte" a trava fica solta. Duas
        # chamadas quase juntas (duas pessoas registrando link ao mesmo
        # tempo, ou o pipeline mais um link manual) podem calcular a MESMA
        # proxima linha e uma sobrescrever a outra, caladamente. Hoje isso
        # nao acontece pelo caminho de download normal, que ja e serializado
        # num so worker (ver linha_de_download em trabalhador.py), mas
        # registrar_link_externo chama esta funcao direto da tela, sem
        # fila, entao duas pessoas registrando link externo ao mesmo tempo
        # ja corriam esse risco antes desta trava. A RLock e reentrante de
        # proposito (ver o comentario dela em sheets_client.py): as chamadas
        # de sheets_client.executar() aqui dentro pegam a mesma trava de
        # novo, na mesma thread, sem travar sozinhas.
        #
        # POR CIMA, TRAVA ENTRE PROCESSOS (18/09/2026, ver
        # _caminho_trava_entre_instalacoes): a RLock acima so vale dentro deste
        # processo. Com duas instalacoes (Marketing e Futebol) escrevendo na
        # MESMA Monitoramento real no servidor, cada uma e um processo python
        # separado, com sua propria RLock na memoria, e a corrida que a RLock
        # fechou em 16/09 volta a existir um nivel acima. trava.travar() usa
        # trava de arquivo do sistema operacional, que funciona entre processos
        # (e ja e o mecanismo usado pelo estado da conta do Instagram).
        with trava.travar(_caminho_trava_entre_instalacoes(planilha)), \
             sheets_client._TRAVA_DA_API:
            atuais = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha,
                range=f"'{ABA_MONITORAMENTO}'!A2:{ULTIMA_COLUNA_MON}20000").execute()).get("values", [])

            # NÃO REGISTRA A MESMA PEÇA DUAS VEZES, e a conferência passou a olhar a
            # coluna ARQUIVO (03/09/2026).
            #
            # Ela comparava a coluna LINK. Com LINK apontando para a PASTA do post, a
            # segunda peça do mesmo dia seria lida como repetida e a linha NÃO seria
            # criada: material no Drive sem linha na planilha, calado. Peça é arquivo, e
            # é por arquivo que se sabe se ela já está lá.
            #
            # Olha as DUAS colunas de propósito: as linhas criadas até 02/09 têm o
            # arquivo na coluna LINK e a coluna ARQUIVO vazia. Sem olhar as duas, baixar
            # de novo uma peça antiga criaria linha repetida.
            i_arquivo = COL_MON["arquivo"] - 1
            i_link = COL_MON["link"] - 1
            for linha in atuais:
                for indice in (i_arquivo, i_link):
                    if len(linha) > indice and linha[indice] and linha[indice] == link_drive:
                        return "ja_registrada", None

            valores = [""] * LARGURA_LINHA_MON
            valores[COL_MON["handle"] - 1] = handle_limpo
            if data_video:
                valores[COL_MON["mes"] - 1] = MESES[data_video.month - 1]
                valores[COL_MON["ano"] - 1] = data_video.year
                valores[COL_MON["data_post"] - 1] = data_video.strftime("%d/%m/%Y")
            valores[COL_MON["ciclo"] - 1] = ciclo_num
            if tipo:
                valores[COL_MON["tipo"] - 1] = tipo
                valores[COL_MON["post"] - 1] = _numero_do_post(
                    atuais, handle_limpo, ciclo_num, tipo, data_video, marcacao)
            if marca:
                valores[COL_MON["marca"] - 1] = marca
            if pagamento:
                valores[COL_MON["pagamento"] - 1] = pagamento
            if horas_live:
                # SÓ QUANDO A PESSOA DIGITOU, e nunca inventado a partir do tipo: um
                # registro do tipo LIVE sem número de horas fica com a coluna vazia
                # mesmo, para não sugerir que o programa mediu uma duração que ninguém
                # informou.
                valores[COL_MON["horas_live"] - 1] = horas_live
            # LINK É A PASTA DO POST; ARQUIVO É A PEÇA (03/09/2026). Sem pasta, as duas
            # recebem o mesmo endereço: é o caso do link externo, que não tem pasta, e o
            # comportamento de antes desta mudança.
            valores[COL_MON["link"] - 1] = link_pasta or link_drive
            valores[COL_MON["arquivo"] - 1] = link_drive
            # Data em que o material foi capturado, que não é a data do post. Numa
            # auditoria as duas importam e são coisas diferentes.
            valores[COL_MON["data_download"] - 1] = datetime.now().strftime("%d/%m/%Y")
            # A situação é o que diz à análise se há arquivo para conferir naquela
            # linha. O endereço do arquivo está na coluna ARQUIVO desde 03/09/2026, e
            # antes disso ficava na LINK (ver BLOCO_AUTOMACAO).
            #
            # Link de YouTube e de live entram com analisavel=False: eles não são
            # baixados de propósito (arquivo grande demais), então não há o que
            # analisar e a linha fica como "N/A" (SEM_ARQUIVO, texto trocado em
            # 17/09/2026, ver o comentário da constante), para a conferência
            # humana saber que aquela peça depende dela.
            valores[COL_MON["situacao"] - 1] = (
                AGUARDANDO_VALIDACAO if (analisavel and link_drive) else SEM_ARQUIVO)
            # VALIDACAO, VALIDADO_EM E EVIDENCIA FICAVAM VAZIAS NUMA LINHA
            # analisavel=False (16/09/2026, achado ao testar o registro de link do
            # YouTube). Vazio ali lia como "ainda não", quando na verdade é "nunca
            # vai ser analisado por aqui", coisa bem diferente para quem olha a
            # planilha depois. "N/A" (pedido do auditor, no lugar do "NÃO SE APLICA"
            # do primeiro rascunho) marca as duas colunas: EVIDENCIA recebe o
            # próprio endereço, porque não existe outro material, e é o link que a
            # conferência humana vai abrir.
            if not analisavel:
                valores[COL_MON["validacao"] - 1] = "N/A"
                valores[COL_MON["validado_em"] - 1] = "N/A"
                valores[COL_MON["evidencia"] - 1] = link_drive
            # A MARCAÇÃO É ESCRITA SEMPRE, e isso mudou em 03/09/2026.
            #
            # Antes a coluna era ORGANICO e só recebia "SIM" quando o post era orgânico,
            # porque célula vazia já queria dizer "entrega normal". Com três marcações,
            # vazio deixou de ter significado próprio: não diria se a peça é link ou se
            # ninguém marcou nada. E como a marcação vai valer para a régua da análise,
            # célula ambígua na coluna que decide conformidade é o pior lugar possível
            # para uma omissão.
            valores[COL_MON["marcacao"] - 1] = texto_da_marcacao(marcacao)
            if pedido_por:
                valores[COL_MON["pedido_por"] - 1] = str(pedido_por)

            # AS COLUNAS C A J, COPIADAS DO CADASTRO (02/09/2026).
            #
            # Falhar aqui NÃO pode impedir a linha de existir: o vídeo já está no Drive,
            # e linha sem o contexto do cadastro é bem melhor que vídeo sem linha. Por
            # isso o motivo é apenas AVISADO, e o registro segue.
            #
            # O cabeçalho da própria Monitoramento é lido para conferir o alinhamento
            # com o cadastro antes de copiar. Ver _cadastro_esta_alinhado: sem essa
            # conferência, uma coluna inserida em qualquer das duas planilhas faria o
            # programa gravar o valor de uma coluna dentro de outra, em silêncio.
            try:
                cabecalho_mon = sheets_client.executar(
                    lambda: sheets_client.get_service().spreadsheets().values().get(
                        spreadsheetId=planilha,
                        range=f"'{ABA_MONITORAMENTO}'!A1:{ULTIMA_COLUNA_MON}1",
                    ).execute()).get("values", [[]])
                cabecalho_mon = cabecalho_mon[0] if cabecalho_mon else []
                do_cadastro, motivo = dados_de_cadastro_para_a_linha(handle_limpo, cabecalho_mon)
                if do_cadastro:
                    for numero, texto in do_cadastro.items():
                        valores[numero - 1] = texto
                    dizer(f"[Monitoramento] preenchi do cadastro as colunas "
                          f"{', '.join(letra_da_coluna(n) for n in sorted(do_cadastro))}.")
                elif motivo and motivo.endswith("não está no cadastro"):
                    # AVISO MAIS FORTE PARA ESTE CASO ESPECÍFICO (15/09/2026), achado
                    # ao testar: um post em colaboração trouxe o @ de uma conta
                    # SECUNDÁRIA de uma influenciadora que já estava cadastrada com
                    # outro @, e a linha entrou calada, sem cadastro nenhum, órfã e
                    # sem escopo/contrato pra bater. Antes isso só aparecia como nota
                    # neutra ("colunas ficaram vazias"), fácil de passar batido no meio
                    # do log de um download. Não bloqueia: quem está baixando pode não
                    # saber ainda que é o mesmo influenciador, e barrar sem alternativa
                    # seria pior que avisar e deixar a linha existir, exatamente pela
                    # mesma razão de "peça reaproveitada" mais abaixo neste arquivo.
                    dizer(f"[ATENÇÃO] {motivo}, então as colunas de cadastro (C a J) "
                          f"ficaram vazias e a linha entrou sem escopo nem contrato "
                          f"associado. Confira se este @ não é uma conta secundária ou "
                          f"de colaboração de alguém que já está cadastrado com outro "
                          f"@: se for, corrija o @ desta linha na Monitoramento.")
                elif motivo:
                    dizer(f"[Monitoramento] as colunas de cadastro (C a J) ficaram vazias: "
                          f"{motivo}")
            except Exception as e:
                dizer(f"[Monitoramento] não copiei as colunas de cadastro: {str(e)[:150]}")

            # Grava em posição explícita em vez de usar acréscimo automático: a coluna
            # A da Monitoramento é vazia no cabeçalho, e o Google entende que a tabela
            # começa na B, empurrando a linha inteira uma coluna pro lado. NÃO trocar
            # por sheets_client.adicionar_linhas por causa disso: já foi tentado e
            # revertido (ver PROMPT_CONTINUACAO.md), é este o motivo de a proteção
            # contra corrida aqui ser reler-e-tentar-de-novo, e não o append atômico
            # que resolveria de graça numa planilha sem essa coluna A vazia.
            numero_linha = len(atuais) + 2
            largura = LARGURA_LINHA_MON
            # NEUTRALIZA FÓRMULA ANTES DE GRAVAR (04/09/2026, achado do parecer de
            # cibersegurança). Esta escrita é feita direto por values().update(), sem
            # passar por sheets_client.escrever_lote/adicionar_linhas, que já ganharam
            # essa trava; aqui ela precisa ser repetida porque é este o caminho que
            # grava o @handle e as horas de live DIGITADOS por uma pessoa. sheets_client
            # é importado lá em cima da função, então a chamada é qualificada pelo
            # módulo, não por nome solto.
            linha_segura = [sheets_client._neutralizar_formula(v)
                            for v in valores + [""] * (largura - len(valores))]
            if _atraso_teste:
                time.sleep(_atraso_teste)
            sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().update(
                spreadsheetId=planilha,
                range=f"'{ABA_MONITORAMENTO}'!A{numero_linha}:{ULTIMA_COLUNA_MON}{numero_linha}",
                valueInputOption="USER_ENTERED",
                body={"values": [linha_segura]},
            ).execute())

            # CONFERE SE A ESCRITA CONTINUA DE PÉ (18/09/2026). Entre esta trava
            # ser soltada por OUTRA instalação (máquina diferente, fora do
            # alcance de trava.travar() e da RLock daqui) e este ponto, a
            # planilha pode ter recebido outra escrita na MESMA linha, com o
            # mesmo número calculado a partir de uma leitura igualmente velha.
            # Relê só a coluna ARQUIVO desta linha e compara com o que
            # acabamos de mandar: se bater, a escrita ficou de pé; se não
            # bater, outra instalação sobrescreveu no meio do caminho, e quem
            # chamou esta função tenta tudo de novo, com a contagem renovada.
            confirmacao = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha,
                range=f"'{ABA_MONITORAMENTO}'!{letra_da_coluna(COL_MON['arquivo'])}{numero_linha}",
            ).execute()).get("values", [[]])
            valor_gravado = confirmacao[0][0] if confirmacao and confirmacao[0] else None
            if valor_gravado != link_drive:
                return "colidiu", None
            return "ok", numero_linha

    MAXIMO_TENTATIVAS_CORRIDA = 4
    for tentativa in range(1, MAXIMO_TENTATIVAS_CORRIDA + 1):
        status, numero_linha = _uma_tentativa_de_registro()
        if status == "ja_registrada":
            return None
        if status == "ok":
            return numero_linha
        dizer(f"[Monitoramento] outra instalação escreveu na mesma linha ao mesmo "
              f"tempo, tentando de novo ({tentativa}/{MAXIMO_TENTATIVAS_CORRIDA})...")
        time.sleep(random.uniform(0.5, 1.5) * tentativa)
    raise RuntimeError(
        "Não consegui gravar na Monitoramento depois de várias tentativas: outra "
        "instalação está escrevendo na mesma linha ao mesmo tempo, repetidamente. "
        "Tente de novo em alguns segundos.")


# AS COLUNAS DO REGISTRO DO FLUXO, num lugar só.
#
# `origem_ciclo` entrou em 01/09/2026, junto com o campo de ciclo na primeira
# seção da tela. Ele responde uma pergunta que antes não tinha resposta: aquele
# ciclo saiu da DATA do vídeo ou da mão de uma pessoa?
#
# Por que é registro de auditoria e não enfeite: ciclo escolhido por alguém é
# discricionariedade, e esta ferramenta existe para deixar discricionariedade
# rastreável. A coluna CICLO da planilha não serve, porque depois de processar
# ela é preenchida com o ciclo usado nos DOIS casos, e a distinção se perde.
#
# NÃO poluir o campo `ciclo` com um "(digitado)" foi decisão consciente: a tela
# agrupa por (handle, ciclo) para montar a estrutura de pastas, e procura
# "A CONFIRMAR" dentro dele. Texto extra ali quebraria as duas coisas.
#
# `quem` entrou em 02/09/2026, e é correção de uma falha de fundo. Quem pediu
# cada download ficava SÓ no arquivo da tarefa do trabalhador, que é temporário:
# a limpeza daquele dia apagou 50 tarefas concluídas, e com elas o rastro de
# quem pediu cada download de agosto. Nada avisou.
#
# Numa ferramenta cujo propósito é deixar discricionariedade rastreável, o ator
# não pode viver no lugar mais efêmero de todos. Aqui ele sobrevive à limpeza da
# fila, e na coluna PEDIDO_POR da planilha ele fica à vista de quem lê.
CAMPOS_LOG = ["quando", "estagio", "origem", "handle", "data_video", "ciclo",
              "destino", "status", "origem_ciclo", "quem"]


def _migrar_cabecalho_do_log():
    """Reescreve o registro com o cabeçalho atual, se ele estiver no antigo.

    Necessário porque o arquivo é lido por NOME de coluna: acrescentar campo no
    fim sem mexer no cabeçalho já gravado faria as linhas novas terem um valor a
    mais do que o cabeçalho declara, e a leitura jogaria esse valor fora, num
    campo que não existe.

    Roda dentro da trava de quem chamou, e o arquivo é pequeno: uma linha por
    vídeo processado."""
    if not os.path.exists(ARQUIVO_LOG):
        return
    with open(ARQUIVO_LOG, "r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        cabecalho = leitor.fieldnames or []
        if cabecalho == CAMPOS_LOG:
            return
        antigas = list(leitor)
    with open(ARQUIVO_LOG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_LOG, extrasaction="ignore")
        w.writeheader()
        for linha in antigas:
            w.writerow({c: (linha.get(c) or "") for c in CAMPOS_LOG})


def gravar_log(linhas):
    if not linhas:
        return
    # Travado desde 29/08/2026: acrescentar linha em arquivo aberto por dois
    # processos ao mesmo tempo pode misturar o conteúdo das duas na mesma
    # linha, e aí a leitura por coluna quebra o painel inteiro.
    with trava.travar(ARQUIVO_LOG):
        _migrar_cabecalho_do_log()
        novo = not os.path.exists(ARQUIVO_LOG)
        os.makedirs(PASTA_TESTE, exist_ok=True)
        with open(ARQUIVO_LOG, "a", encoding="utf-8", newline="") as f:
            # extrasaction="ignore" para o registro nunca ser o motivo de uma
            # falha: quem chama passa o dicionário que tem, e campo que sobra é
            # descartado em vez de derrubar um processamento já concluído.
            w = csv.DictWriter(f, fieldnames=CAMPOS_LOG, extrasaction="ignore")
            if novo:
                w.writeheader()
            w.writerows(linhas)


def ler_log():
    # utf-8-sig porque o arquivo pode ter ganhado marca de codificação no
    # começo se alguém reescreveu ele pelo PowerShell; sem isso o nome da
    # primeira coluna vem sujo e a leitura por nome falha.
    if not os.path.exists(ARQUIVO_LOG):
        return []
    with open(ARQUIVO_LOG, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# MOVIDO DE pages/1_Downloads_e_Organizacao.py EM 23/09/2026, quando a seção
# "Enviar arquivo do post" se mudou para uma página de Uploads própria. Esta
# função tem que continuar valendo para as duas páginas, e função de tela não
# é importável sem rodar a tela inteira (o motivo, junto com o caso real que
# a levou a existir, está no comentário original, preservado abaixo).
#
# NEM TUDO QUE TERMINA DEU CERTO, e até 31/08/2026 a tela dizia que sim.
#
# Visto na tela pelo auditor: um Story que era foto, e não vídeo, saiu como
# "✅ 0 de 1 baixados e organizados", com a marca verde de sucesso. A tarefa
# termina como concluída porque a rodada inteira rodou até o fim, e o arquivo
# que não veio é resultado dela, não erro dela. Mas quem lê a tela vê marca
# verde e zero, e marca verde com zero é pior que erro: parece que está tudo bem.
#
# Fica fora de qualquer tela para poder ser testada, porque a regra que importa
# aqui é de auditoria e não de desenho: material que entrou e não foi organizado
# tem que aparecer como pendência, com o motivo à vista. O motivo já existia no
# registro da tarefa (no caso da foto, "FALHA: Story é uma foto, não um vídeo"),
# então é trazido para cima em vez de ficar atrás de "Ver o que aconteceu".
def resumo_da_tarefa(tarefa):
    """Devolve (aparência, texto, motivos). Aparência: erro, atencao ou ok."""
    import fila_trabalho
    hora = str(tarefa.get("terminou_em") or "")[11:16]
    if tarefa.get("situacao") == fila_trabalho.FALHA:
        return "erro", f"{hora}: falhou. {str(tarefa.get('erro') or '')[:200]}", []

    r = tarefa.get("resultado") or {}
    organizados = r.get("organizados") or 0
    # ENVIAR_VIDEO_BRUTO ENTROU AQUI EM 23/09/2026: executar_video_bruto
    # devolve o mesmo formato de executar_envio ({"enviados", "organizados",
    # "problemas"}), então o mesmo texto de resumo vale para os dois.
    if tarefa.get("tipo") in (fila_trabalho.ENVIAR_ARQUIVOS, fila_trabalho.ENVIAR_VIDEO_BRUTO):
        entraram = r.get("enviados") or 0
        assunto = "enviados organizados"
    else:
        entraram = r.get("processados") or 0
        assunto = "baixados e organizados"

    # As linhas do registro que contam o que aconteceu com cada item, para a
    # pessoa saber o motivo sem abrir nada.
    #
    # A SELEÇÃO É PELA SETA, e não por palavra (corrigido em 31/08/2026, no
    # mesmo dia em que foi escrito). A primeira versão procurava a palavra
    # "FALHA", e na primeira falha real que apareceu a mensagem era "Ainda não
    # sei o número do perfil de @...", sem essa palavra em lugar nenhum: o
    # resumo saiu vermelho e certo, e o motivo ficou escondido.
    #
    # Procurar por lista de palavras seria o mesmo erro maior. A seta é o que o
    # fluxo usa para marcar o resultado de cada item processado, então ela pega
    # qualquer motivo, inclusive os que ninguém previu.
    #
    # AS DUAS LINHAS DE PURO SUCESSO SAEM DAQUI (25/09/2026, revisão do
    # comentário acima: "linha de sucesso não incomoda" deixou de valer na
    # prática). "subiu pro Drive de teste." e "Calendário preenchido (...)"
    # não dizem nada que o número em cima ("N de N baixados e organizados")
    # já não diga, e com vários arquivos na mesma rodada elas se repetiam
    # uma vez por arquivo, enchendo a tela sem informação nova. O que
    # continua subindo é qualquer coisa que precise de atenção (Calendário
    # NÃO preenchido, falta de bet, falta de pasta etc.), e repetida também
    # some, ficando só uma vez.
    #
    # PRECISA TIRAR O RELÓGIO ANTES DE COMPARAR (corrigido em 25/09/2026, no
    # mesmo dia, ao vivo: a primeira versão não tirava, e por isso nem a
    # exclusão nem a repetição funcionavam). `fila_trabalho.anotar` grava
    # cada mensagem já com "HH:MM:SS " na frente (linha 241 daquele
    # arquivo), então o texto real chega como "11:18:48    -> subiu pro
    # Drive de teste.", nunca começando pela seta. Sem tirar o relógio
    # primeiro, o `startswith` nunca batia, e duas mensagens iguais em
    # segundos diferentes nunca pareciam a mesma linha.
    _SUCESSO_PURO = ("subiu pro drive de teste.", "calendário preenchido")
    vistos = set()
    motivos = []
    for m in (tarefa.get("mensagens") or []):
        texto_m = str(m).strip()
        if "->" not in texto_m:
            continue
        sem_relogio = re.sub(r"^\d{1,2}:\d{2}:\d{2}\s*", "", texto_m)
        chave = sem_relogio.lower().lstrip("- >").strip()
        if any(chave.startswith(p) for p in _SUCESSO_PURO):
            continue
        if chave in vistos:
            continue
        vistos.add(chave)
        motivos.append(texto_m)
        if len(motivos) >= 6:
            break
    motivos += [str(p) for p in (r.get("problemas") or [])][:6]

    texto = f"{hora}: {organizados} de {entraram} {assunto}."

    # NADA A FAZER NÃO É SUCESSO NEM ERRO (02/09/2026).
    #
    # A tela dizia "0 de 0 baixados e organizados" em verde. O auditor leu isso
    # como defeito do programa, e com razão: a frase conta uma divisão que não
    # aconteceu, e o verde afirma que deu certo algo que não foi feito. Ele
    # chegou a suspeitar do Instagram aberto em mais de uma tela; a fila é que
    # não tinha nenhuma linha pendente.
    #
    # Aqui vão TODAS as mensagens da tarefa, e não só as que têm seta: a
    # explicação de por que não havia o que fazer não é resultado de item
    # nenhum, então não tem seta, e a seleção normal a deixaria escondida.
    # Selecionar por palavra ("nada para baixar") seria repetir o erro
    # registrado logo acima, de procurar texto certo em mensagem que muda.
    if not entraram and not organizados:
        return ("nada", f"{hora}: não havia nada para fazer.",
                [str(m).strip() for m in (tarefa.get("mensagens") or [])][:6])

    if entraram and not organizados:
        return "erro", f"{texto} Nenhum arquivo entrou.", motivos
    if organizados < entraram:
        return "atencao", f"{texto} {entraram - organizados} não entrou.", motivos
    return "ok", texto, motivos


# ------------------------------------------------------------------
# Fila (planilha de TESTE)
# ------------------------------------------------------------------
def _planilha_fila_id():
    # Levanta se não houver identificador, e não devolve None em silêncio: sem
    # a fila o estágio A não tem de onde ler, e falhar aqui com mensagem é
    # melhor que falhar mais adiante com erro da API do Google.
    valor = ler_identificador(ARQUIVO_FILA_ID)
    if not valor:
        raise RuntimeError(
            f"Não achei o identificador da planilha da fila em "
            f"{os.path.basename(ARQUIVO_FILA_ID)}. O programa não guarda "
            f"identificador no código: apontar para outra planilha é trocar o "
            f"conteúdo desse arquivo.")
    return valor


# AS COLUNAS DA FILA, num só lugar (31/08/2026).
#
# Antes os índices e as letras estavam espalhados por sete lugares do arquivo, e
# mexer numa coluna exigia achar todos. Agora quem mexer mexe aqui.
# A coluna da marcação entrou em 01/09/2026 como ORGANICO e virou MARCACAO em
# 03/09/2026. Ela precisa existir NA FILA, e não só no envio: quem marca é a
# pessoa na tela, quem grava no Drive é o trabalhador, e entre os dois só passa o
# que está escrito na linha da fila.
#
# A COLUNA CONTINUA SENDO A MESMA, a F, de propósito. Ela já tem "SIM" nas linhas
# antigas, e "SIM" continua sendo lido como orgânico (ver LEITURA_DA_MARCACAO).
# Criar uma coluna nova ao lado deixaria duas dizendo a mesma coisa, e a antiga
# viraria armadilha para quem lesse a planilha.
#
# `quem_pediu` entrou em 02/09/2026, e o lugar dele é AQUI e não na tarefa do
# trabalhador. A tarefa tem `criada_por`, mas uma tarefa processa TODOS os links
# pendentes, que podem ter sido colados por pessoas diferentes. Quem pediu é
# informação de LINHA, não de lote, então tem que viajar na linha.
#
# `jogo` entrou em 11/09/2026, e no FIM pelo mesmo motivo da `quem_pediu`: a
# fila é planilha com linhas já gravadas, e coluna nova no meio desloca tudo o
# que está lá, sem dar erro. É o jogo que a peça divulga (CHUTE PREMIADO +
# AVIATOR, Mega Odds, Jogo do Chapéu), digitado na tela porque reconhecer por
# visão foi descartado pelo auditor: erraria, e o custo não se paga. Daqui vai
# para a coluna Jogo do Calendário de Divulgações.
COL_FILA = {"influenciador": 0, "link": 1, "status": 2, "ciclo": 3, "marca": 4,
            "marcacao": 5, "quem_pediu": 6, "jogo": 7}
ULTIMA_COLUNA_FILA = "H"

# O que conta como sim numa célula de planilha preenchida por gente ou por
# programa. "TRUE" está aí porque é o que o Google escreve quando alguém
# transforma a célula em caixa de marcar, o que é bem possível que aconteça
# nessa coluna.
VALORES_DE_SIM = {"sim", "s", "x", "true", "verdadeiro", "1", "orgânico", "organico"}


def e_sim(valor):
    """Se o texto de uma célula quer dizer sim. Vazio quer dizer não."""
    return str(valor or "").strip().lower() in VALORES_DE_SIM


def letra_da_coluna_fila(nome):
    return chr(ord("A") + COL_FILA[nome])


def ler_fila():
    """Devolve lista de dicts: numero_linha, influenciador, link, status,
    ciclo, marca.

    A coluna Ciclo é preenchida pelo programa depois de organizar, mas se
    alguém preencher ANTES de processar, esse valor manda no lugar do ciclo que
    o programa descobriria sozinho.

    A COLUNA "LINK DO VÍDEO" SAIU EM 31/08/2026, e o motivo é o mesmo da
    LINK_ARQUIVO que saiu da Monitoramento em 30/08: ela era escrita pelo
    programa, exibida de volta pelo programa, e nunca usada para decidir nada.
    O mesmo endereço fica na Monitoramento e no registro em CSV, e é do CSV que
    a tela lê a lista de "Últimos organizados"."""
    import sheets_client
    resp = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
        spreadsheetId=_planilha_fila_id(),
        range=f"{ABA_FILA}!A2:{ULTIMA_COLUNA_FILA}1000").execute())
    itens = []
    for i, linha in enumerate(resp.get("values", [])):
        def pega(nome):
            indice = COL_FILA[nome]
            return linha[indice] if len(linha) > indice else ""
        itens.append(dict(
            numero_linha=i + 2,
            influenciador=pega("influenciador"),
            link=pega("link"),
            status=pega("status"),
            ciclo=pega("ciclo"),
            marca=pega("marca"),
            # Guarda o texto CRU da célula, e não a marcação já interpretada:
            # a tabela da tela mostra esta coluna, e ali o que interessa é o que
            # está escrito na planilha. Quem precisa da marcação chama
            # marcacao_de_celula.
            marcacao=pega("marcacao"),
            quem_pediu=pega("quem_pediu"),
            # O jogo que a peça divulga, digitado na tela. Vai para a coluna
            # Jogo do Calendário de Divulgações (11/09/2026).
            jogo=pega("jogo"),
        ))
    return [x for x in itens if x["influenciador"] or x["link"]]


# Onde fica a trava da fila de downloads. Arquivo local mesmo, ainda que a
# fila viva numa planilha: o que precisa ser serializado é o trecho de código,
# e todas as pessoas usam o mesmo servidor.
ARQUIVO_TRAVA_FILA = os.path.join(PASTA_TESTE, "fila_downloads")


def adicionar_na_fila(itens):
    """itens = (influenciador, link), e opcionalmente ciclo, marca, marcação,
    quem pediu e jogo, nessa ordem. Não duplica link já presente. Os cinco
    últimos são opcionais: quando vêm preenchidos, já entram na linha e valem na
    hora de organizar, de registrar na Monitoramento e de preencher o Calendário
    de Divulgações, sem precisar de um segundo passo.

    A marcação é uma das duas chaves de PASTA_DA_MARCACAO. Vazio cai em link,
    que é a peça publicitária comum.

    POR QUE ISTO É TRAVADO (30/08/2026).

    Ler a fila, decidir o que é novo e acrescentar são três passos, e entre o
    primeiro e o terceiro há duas chamadas à planilha, o que dá quase um
    segundo. Duas pessoas mandando o MESMO endereço dentro dessa janela leem
    as duas a fila sem ele, e as duas o acrescentam.

    A consequência não é uma linha feia na planilha: é uma segunda chamada ao
    Instagram para baixar o vídeo que já foi baixado. Chamada ao Instagram é o
    recurso escasso deste programa, o teto do dia conta chamada e não vídeo, e
    foi repetição de chamada que marcou duas contas em agosto.

    Não adianta a conferência de vídeo repetido que existe no envio: aquela
    compara o conteúdo do arquivo e só roda DEPOIS do download, então ela
    evita o arquivo duplicado no Drive, não a chamada.

    Descoberto ao conferir o teste de duas janelas de 30/08. O teste passou
    porque os dois cliques foram separados por segundos; simultâneo de
    verdade é que expõe."""
    import sheets_client
    with trava.travar(ARQUIVO_TRAVA_FILA):
        existentes = {x["link"] for x in ler_fila() if x["link"]}
        novos = []
        for item in itens:
            influ, link = item[0], item[1]
            ciclo = normalizar_ciclo(item[2]) if len(item) > 2 else None
            marca = item[3] if len(item) > 3 else None
            marcacao = marcacao_de_celula(item[4]) if len(item) > 4 else MARCACAO_PADRAO
            quem_pediu = str(item[5]).strip() if len(item) > 5 and item[5] else ""
            # SEMPRE MAIÚSCULA (15/09/2026): a coluna Jogo do Calendário deles só
            # tem valor em caixa alta, conferido na planilha real. A tela já força
            # visualmente, mas quem chamar esta função por outro caminho não pode
            # depender de CSS pra ter o dado certo.
            jogo = str(item[6]).strip().upper() if len(item) > 6 and item[6] else ""
            if link and link not in existentes:
                # A influenciador, B link, C status (vazia), D ciclo, E marca,
                # F marcação, G quem pediu, H jogo. A marcação vai por extenso
                # e em maiúscula (ORGANICO ou LINK), e não como código nem
                # True/False: esta linha é lida por gente na planilha da fila.
                novos.append([influ, link, "", ciclo or "", marca or "",
                              texto_da_marcacao(marcacao), quem_pediu, jogo])
                # Conta o que acabou de entrar, senão o mesmo endereço repetido
                # DENTRO da mesma chamada passaria duas vezes.
                existentes.add(link)
        if novos:
            sheets_client.adicionar_linhas(_planilha_fila_id(), ABA_FILA,
                                           f"A:{ULTIMA_COLUNA_FILA}", novos)
        return len(novos), len(itens) - len(novos)


def limpar_fila():
    """Apaga todas as linhas da fila, deixando só o cabeçalho. Não mexe nos
    vídeos já organizados no Drive nem no histórico: some só a lista de
    trabalho. Devolve quantas linhas foram apagadas."""
    import sheets_client
    quantas = len(ler_fila())
    if not quantas:
        return 0
    sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().clear(
        spreadsheetId=_planilha_fila_id(),
        range=f"{ABA_FILA}!A2:{ULTIMA_COLUNA_FILA}1000", body={}).execute())
    return quantas


def corrigir_ciclo_na_monitoramento(numero_linha, novo_ciclo, quem=None):
    """Troca o ciclo de uma linha JÁ criada na Monitoramento, e registra a troca.

    POR QUE EXISTE (01/09/2026)

    Levantado pelo auditor: alguém quer mudar o ciclo de um post já baixado. O
    único caminho era reabrir a linha e baixar de novo, o que gastava uma chamada
    ao Instagram, duplicava a linha e, pior, fazia o programa marcar o arquivo
    como peça REAPROVEITADA, que é acusação de descumprimento de contrato.

    Nada disso era necessário: o ciclo é um campo de planilha, e corrigi-lo não
    tem nada a ver com o arquivo no Drive.

    ISTO ABRE UMA EXCEÇÃO À REGRA DE NUNCA SOBRESCREVER, e a exceção é
    consciente. A regra existe para a automação não passar por cima do trabalho
    do Marketing nas colunas A a V. A coluna CICLO é uma dessas, e o programa já
    escreve nela ao criar a linha; o que não fazia era voltar e corrigir.

    Por isso o registro é PARTE da solução, e não enfeite: fica gravado quem
    trocou, quando, e de qual valor para qual. Sem esse rastro, a exceção seria
    a automação alterando dado do Marketing em silêncio.

    Devolve (ciclo_antigo, ciclo_novo), ou None se não houve o que fazer."""
    import sheets_client
    rotulo = normalizar_ciclo(novo_ciclo)
    if not rotulo:
        return None
    # A PLANILHA GUARDA O NÚMERO PURO, E NÃO "Ciclo N" (05/09/2026).
    #
    # `normalizar_ciclo` devolve "Ciclo 4", que é o formato das PASTAS do Drive,
    # e por isso ele continua sendo usado acima e no registro. Mas a coluna
    # CICLO da Monitoramento não usa esse formato: medido nas 19.999 linhas da
    # planilha real do Marketing, TODAS têm número puro ("1", "2", "3"), e
    # nenhuma tem o prefixo.
    #
    # ERA UMA INCOERÊNCIA DENTRO DO PRÓPRIO PROGRAMA: ao CRIAR a linha ele já
    # gravava o número puro (ver `ciclo_num` em registrar_na_monitoramento), e
    # só a correção gravava com prefixo. A mesma coluna, dois formatos, conforme
    # o caminho. O auditor viu na tela de correção: uma linha aparecia como
    # "hoje: Ciclo 4" no meio de outras como "hoje: 1".
    #
    # E ISSO TINHA UM SEGUNDO EFEITO, PIOR QUE O VISUAL: a comparação abaixo era
    # feita contra o texto com prefixo. Uma célula que já valia "4", corrigida
    # para 4, dava "4" != "Ciclo 4", então o programa gravava por cima e
    # registrava uma correção que não aconteceu.
    ciclo_para_planilha = re.sub(r"(?i)^ciclo\s*", "", rotulo).strip()
    planilha = _planilha_monitoramento_id()
    if not planilha:
        raise RuntimeError(
            "Não sei em qual planilha está a Monitoramento. O identificador vem "
            "de arquivo, em teste_watch_folder.")
    linha = int(numero_linha)
    letra = letra_da_coluna(COL_MON["ciclo"])

    atual = sheets_client.ler_coluna(planilha, ABA_MONITORAMENTO, letra, [linha])
    ciclo_antigo = str(atual.get(linha) or "").strip()
    # A COMPARAÇÃO TIRA O PREFIXO DOS DOIS LADOS, senão "4" e "Ciclo 4" pareceriam
    # valores diferentes sendo o mesmo ciclo. Mesma defesa que
    # escopo_e_entrega.contar_entregas já fazia ao casar as linhas.
    if (re.sub(r"(?i)^ciclo\s*", "", ciclo_antigo).strip().replace(".0", "")
            == ciclo_para_planilha):
        # Nada a fazer, e dizer isso é melhor que gravar o mesmo valor e
        # registrar uma troca que não houve.
        return None

    sheets_client.escrever_lote(planilha, ABA_MONITORAMENTO, letra,
                                [(linha, ciclo_para_planilha)])
    gravar_log([dict(
        quando=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        estagio="correcao",
        origem=f"Monitoramento linha {linha}",
        # O REGISTRO DIZ O QUE FOI ESCRITO NA CÉLULA, e não o rótulo de pasta.
        # Trilha de auditoria que descreve um valor diferente do que está na
        # planilha é pior que trilha nenhuma: quem confere depois não consegue
        # casar o registro com o dado, e não sabe qual dos dois está errado.
        handle="", data_video="", ciclo=ciclo_para_planilha, destino="",
        status=f"CICLO CORRIGIDO de \"{ciclo_antigo or '(vazio)'}\" para "
               f"\"{ciclo_para_planilha}\" por {quem or 'não identificado'}",
        origem_ciclo="corrigido à mão",
    )])
    return ciclo_antigo, ciclo_para_planilha


# NÃO EXISTE FUNÇÃO PARA ESCREVER CRONOGRAMA OU PAGAMENTO (05/09/2026).
#
# Elas existiram por um dia: `corrigir_coluna_na_monitoramento`, com lista de
# permissão e proteção contra colisão, mais dois atalhos por coluna. Foram
# removidas quando o auditor decidiu que as duas colunas continuam preenchidas
# à mão na planilha, linha por linha.
#
# NÃO É CÓDIGO PERDIDO, e é bom saber disso antes de reescrever do zero: está
# no histórico do Git, junto com os testes que provavam a proteção contra
# colisão e a recusa de qualquer coluna fora da lista. Quando a decisão voltar
# atrás, recuperar é mais barato e mais seguro que refazer, porque a parte
# difícil não era escrever a célula, era recusar a escrita quando alguém mudou
# o valor no meio do caminho.
#
# A CORREÇÃO DE CICLO (`corrigir_ciclo_na_monitoramento`, acima) NÃO foi
# afetada: ela é outra coisa, corrige um erro de leitura da automação, e
# continua sendo a única escrita por escolha humana na Monitoramento.


def definir_ciclo_na_fila(numero_linha, ciclo):
    """Grava o ciclo numa linha da fila, ANTES de processar, pra mandar no
    ciclo em vez de deixar o programa descobrir pela data."""
    import sheets_client
    rotulo = normalizar_ciclo(ciclo)
    if not rotulo:
        return None
    sheets_client.escrever_lote(_planilha_fila_id(), ABA_FILA,
                                letra_da_coluna_fila("ciclo"),
                                [(int(numero_linha), rotulo)])
    return rotulo


# REBAIXAMENTO PEDIDO DE DENTRO, e por que ele precisa ser marcado (01/09/2026).
#
# Levantado pelo auditor: "a pessoa jogou um link, deu erro, e ela também quer
# mudar o ciclo. Ela consegue rebaixar?"
#
# Conseguia, e produzia uma ACUSAÇÃO FALSA. Ao baixar o mesmo vídeo de novo, o
# envio compara o conteúdo, acha o arquivo idêntico no Drive e marca "VÍDEO
# REAPROVEITADO: reaproveitar peça é vedado em contrato".
#
# Essa marca existe para um achado real e grave, o influenciador republicando
# peça antiga como nova. Ela não distinguia isso de uma analista rebaixando o
# mesmo vídeo por decisão interna, e o resultado era uma acusação de
# descumprimento de contrato criada por operação de rotina.
#
# Quem reabre a linha está dizendo ao programa que o rebaixamento partiu de
# dentro. Essa informação é guardada aqui e consumida pelo envio.
ARQUIVO_REBAIXAMENTOS = os.path.join(PASTA_TESTE, "rebaixamentos_pedidos.json")


def _ler_rebaixamentos():
    if not os.path.exists(ARQUIVO_REBAIXAMENTOS):
        return {}
    import json
    try:
        with open(ARQUIVO_REBAIXAMENTOS, "r", encoding="utf-8-sig") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        # Arquivo ilegível não pode derrubar um download. Na dúvida, trata como
        # se não houvesse pedido nenhum, e o pior caso volta a ser o aviso de
        # reaproveitado, que é conservador.
        return {}


def marcar_rebaixamento_pedido(links, quem=None, motivo=None):
    """Anota que estes endereços vão ser baixados de novo A PEDIDO.

    Guarda quem pediu, quando e, desde 14/09/2026, o motivo: material que
    entrou duas vezes na auditoria precisa ter motivo e autor, e até aqui só o
    autor ficava. `motivo` é obrigatório na tela quando a linha reaberta já
    tinha dado certo (ver `reabrir_na_fila`); para linha que só falhou, chega
    vazio mesmo, sem exigir nada de quem está só tentando de novo."""
    import json
    links_validos = [str(l).strip() for l in (links or []) if str(l or "").strip()]
    if not links_validos:
        return 0
    with trava.travar(ARQUIVO_REBAIXAMENTOS):
        mapa = _ler_rebaixamentos()
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for link in links_validos:
            mapa[link] = {"quando": agora, "quem": str(quem or ""),
                          "motivo": str(motivo or "")}
        os.makedirs(PASTA_TESTE, exist_ok=True)
        # Grava dentro da trava, no mesmo padrão de guardar_userid. Não usa
        # trava.substituir aqui porque aquela função move um arquivo para outro,
        # e o que existe aqui é conteúdo, não arquivo de origem.
        with open(ARQUIVO_REBAIXAMENTOS, "w", encoding="utf-8") as f:
            json.dump(mapa, f, ensure_ascii=False, indent=2, sort_keys=True)
    return len(links_validos)


def consumir_rebaixamento_pedido(link):
    """Devolve o pedido daquele endereço, se houver, e o REMOVE.

    Consome de propósito: o pedido vale para o próximo download daquele
    endereço, não para sempre. Se ficasse guardado, um reaproveitamento de
    verdade, meses depois, seria silenciado por um pedido antigo."""
    import json
    alvo = str(link or "").strip()
    if not alvo:
        return None
    with trava.travar(ARQUIVO_REBAIXAMENTOS):
        mapa = _ler_rebaixamentos()
        pedido = mapa.pop(alvo, None)
        if pedido is not None:
            os.makedirs(PASTA_TESTE, exist_ok=True)
            with open(ARQUIVO_REBAIXAMENTOS, "w", encoding="utf-8") as f:
                json.dump(mapa, f, ensure_ascii=False, indent=2, sort_keys=True)
    return pedido


def e_status_sucesso(status):
    """Se este status de fila é de download com sucesso, e não uma falha
    (qualquer outro texto não vazio, tipo "FALTA A BET: ...").

    Usado para distinguir, no "Baixar de novo", a linha que só falhou (some
    reabrir sem fricção, é recurso normal) da linha que já teve sucesso e já
    foi analisada (reabrir precisa de motivo, ver `reabrir_na_fila`).

    CORRIGIDO EM 23/09/2026: comparava com "OK", que é o vocabulário do LOG
    de fluxo (log_fluxo_completo.csv), não da FILA. A ÚNICA coisa que a fila
    grava na coluna status quando o download dá certo é "BAIXADO E
    ORGANIZADO" (única gravação de sucesso em todo o arquivo, conferida em
    23/09/2026 contra a fila real: 14 linhas, todas com esse texto, nenhuma
    com "OK"). Com a comparação errada, esta função nunca reconhecia sucesso
    de verdade nenhum, e as quatro chamadas dela (pages/1_Downloads...) nunca
    exigiam motivo nem papel de supervisão/coordenação para "Baixar de novo"
    numa linha já concluída, mesmo com o pedido do Marketing no go live de
    "impedir novos downloads de links já processados com sucesso". A fricção
    existia no código e nunca chegava a acontecer na tela."""
    return str(status or "").strip().upper() == "BAIXADO E ORGANIZADO"


def reabrir_na_fila(numeros_linha, quem=None, motivo=None):
    """Limpa o status das linhas indicadas, pra elas voltarem a ser
    processadas.

    Vale pra qualquer linha, inclusive as que deram certo: alguém pode apagar
    o vídeo do Drive por engano e precisar baixar de novo. Sem isso ficava um
    beco sem saída, porque o programa só processa linha com status vazio e não
    aceita o mesmo link duas vezes.

    Baixar de novo gera um arquivo NOVO no Drive, com endereço próprio. O
    arquivo antigo, se ainda existir, continua lá, e a Monitoramento ganha uma
    linha nova, porque a trava de repetição compara o endereço do arquivo.

    Desde 01/09/2026 também MARCA o pedido, para o envio não tratar o mesmo
    arquivo como peça reaproveitada pelo influenciador. Ver
    ARQUIVO_REBAIXAMENTOS.

    Desde 14/09/2026, `motivo` também entra no LOG GERAL quando a linha
    reaberta já tinha sucesso (já baixada, já com veredito): a tela exige o
    motivo nesse caso antes de chamar esta função, mas quem garante que ele
    fica na trilha de auditoria, e não só num JSON à parte, é esta função. Foi
    o auditor quem pediu essa fricção, contra a possibilidade de alguém
    reprocessar um vídeo já com veredito sem ninguém saber por quê depois."""
    import sheets_client
    numeros = [int(n) for n in numeros_linha]
    if not numeros:
        return 0
    planilha = _planilha_fila_id()

    # Endereço e status ANTERIOR destas linhas, lidos antes de limpar: depois
    # de limpo não há como saber se a linha já tinha dado certo, nem marcar o
    # pedido de rebaixamento no endereço certo.
    fila_atual = {x["numero_linha"]: x for x in ler_fila()}
    por_numero = {n: fila_atual.get(n, {}).get("link") for n in numeros}
    marcar_rebaixamento_pedido([por_numero.get(n) for n in numeros], quem=quem,
                               motivo=motivo)

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reaberturas_de_sucesso = []
    for n in numeros:
        item = fila_atual.get(n, {})
        if e_status_sucesso(item.get("status")):
            reaberturas_de_sucesso.append(dict(
                quando=agora, estagio="reabertura",
                origem=item.get("link", ""), handle=item.get("influenciador", ""),
                data_video="", ciclo="", destino="",
                status=f"REABERTA (já tinha sucesso), motivo: {motivo or ''}",
                origem_ciclo="", quem=str(quem or "")))
    if reaberturas_de_sucesso:
        gravar_log(reaberturas_de_sucesso)

    # Só o status. O ciclo e a marca FICAM de propósito: quem reabre uma linha
    # normalmente quer o mesmo destino de antes, e apagar obrigaria a preencher
    # de novo. A coluna de destino, que também era limpa aqui, deixou de
    # existir em 31/08/2026.
    sheets_client.escrever_lote(planilha, ABA_FILA,
                                letra_da_coluna_fila("status"),
                                [(n, "") for n in numeros])
    return len(numeros)


def sessao_viva_do_navegador():
    """Devolve o nome do navegador cuja sessão do Instagram dá para ler agora,
    ou None.

    Só o Firefox serve, e isso foi medido em 29/08/2026: Chrome e Edge, da
    versão 127 em diante, cifram os cookies de um jeito que amarra a leitura
    ao próprio navegador. Nesta máquina o Chrome nem deixa copiar o banco."""
    if not NAVEGADOR_COOKIES:
        return None
    try:
        from yt_dlp.cookies import extract_cookies_from_browser
        jar = extract_cookies_from_browser(NAVEGADOR_COOKIES)
    except Exception:
        return None
    tem = any(c.name == "sessionid" and "instagram.com" in (c.domain or "")
              for c in jar)
    return NAVEGADOR_COOKIES if tem else None


def _opcoes_cookies():
    """Devolve as opções do yt-dlp para baixar autenticado, ou vazio se não
    houver sessão nenhuma disponível.

    A ORDEM MUDOU EM 30/08/2026: o navegador vem primeiro, e o arquivo é a
    reserva. Antes era o contrário.

    O motivo apareceu em uso real. O arquivo é uma fotografia de uma sessão
    tirada num dia; o navegador renova a dele sozinho, e a fotografia envelhece
    sem avisar. Foi o que aconteceu: comparando os dois, dos 7 cookies de mesmo
    nome só 1 tinha o mesmo valor, e o caminho do arquivo levou três recusas
    seguidas enquanto o baixador, que lê o navegador, baixava sem falhar.

    Isto vale enquanto o programa roda numa máquina com navegador. NUM
    SERVIDOR NÃO HÁ NAVEGADOR, e lá ele cai no arquivo sozinho, sem precisar de
    configuração. Mas fica a consequência, que precisa entrar no procedimento
    do servidor: lá alguém tem de renovar esse arquivo de tempos em tempos.

    Cuidado que vem junto: usando a sessão do navegador, sair do Instagram
    nele derruba o download do programa também, porque é a mesma sessão."""
    navegador = sessao_viva_do_navegador()
    if navegador:
        return {"cookiesfrombrowser": (navegador,)}
    if os.path.exists(ARQUIVO_COOKIES):
        return {"cookiefile": ARQUIVO_COOKIES}
    if NAVEGADOR_COOKIES:
        return {"cookiesfrombrowser": (NAVEGADOR_COOKIES,)}
    return {}


# ------------------------------------------------------------------
# Freio de mão: teto diário e pausa automática depois de bloqueio
# ------------------------------------------------------------------
def _ler_estado_conta():
    if not os.path.exists(ARQUIVO_ESTADO_CONTA):
        return {}
    import json
    try:
        with open(ARQUIVO_ESTADO_CONTA, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return {}


def _gravar_estado_conta(estado):
    import json
    os.makedirs(PASTA_TESTE, exist_ok=True)
    with open(ARQUIVO_ESTADO_CONTA, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


# Chave que guarda qual conta já usou o Instagram HOJE nesta máquina. Começa
# com "#" de propósito: nome de usuário do Instagram só aceita letra, número,
# ponto e sublinhado, então essa chave nunca colide com uma conta de verdade.
CHAVE_MAQUINA = "#maquina-do-dia"


def _estado_da_conta():
    """Estado de hoje da conta em uso: quantos downloads já foram e até quando
    ela está de castigo, se estiver."""
    estado = _ler_estado_conta()
    conta = estado.setdefault(USUARIO_DOS_COOKIES, {})
    hoje = datetime.now().strftime("%Y-%m-%d")
    if conta.get("dia") != hoje:
        conta["dia"], conta["usados"] = hoje, 0
    conta.setdefault("usados", 0)
    conta.setdefault("pausada_ate", None)
    return estado, conta


def conta_do_dia_nesta_maquina():
    """Qual conta já falou com o Instagram hoje, a partir desta máquina.
    Devolve None se ainda não houve nenhuma hoje."""
    marca = _ler_estado_conta().get(CHAVE_MAQUINA) or {}
    if marca.get("dia") != datetime.now().strftime("%Y-%m-%d"):
        return None
    return marca.get("conta")


def _marcar_conta_do_dia(estado):
    """Registra que foi ESTA conta que usou o Instagram hoje nesta máquina.
    Chamado junto com a contagem de uso, ou seja, só quando houve uso de
    verdade: trocar de conta sem baixar nada não prende a máquina."""
    estado[CHAVE_MAQUINA] = {"dia": datetime.now().strftime("%Y-%m-%d"),
                             "conta": USUARIO_DOS_COOKIES}


def situacao_da_conta():
    """Como está a conta agora, pra mostrar na tela e pra decidir se pode
    falar com o Instagram. Devolve (pode_usar, motivo, usados, restantes).

    CHAMA AS DUAS SINCRONIAS COMPARTILHADAS PRIMEIRO: se outra máquina
    pausou esta mesma conta (22/09/2026) ou já usou parte do teto de hoje
    (24/09/2026) e ainda não apareceu aqui, é aqui que aparece, respeitando
    o intervalo de SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO (ver os
    comentários grandes perto de ABA_ESTADO_INSTAGRAM e de
    _sincronizar_uso_compartilhado)."""
    _sincronizar_pausa_compartilhada()
    _sincronizar_uso_compartilhado()
    _, conta = _estado_da_conta()
    usados = conta["usados"]
    restantes = max(0, limite_diario_vigente() - usados)

    # Uma conta por dia por máquina. O teto diário é por conta, então trocar de
    # conta zerava o contador sem querer e a máquina fazia o dobro de chamadas
    # sem ninguém perceber. Foi o que aconteceu em 27/08/2026: duas contas
    # saíram do mesmo computador no mesmo dia, e uma delas foi barrada. Além do
    # contador, duas contas no mesmo endereço de rede é por si só um padrão que
    # a plataforma costuma sinalizar.
    dona_do_dia = conta_do_dia_nesta_maquina()
    if dona_do_dia and dona_do_dia != USUARIO_DOS_COOKIES:
        return (False,
                f"Hoje quem já usou o Instagram neste computador foi a conta "
                f"@{dona_do_dia}. Só uma conta por dia por máquina: usar a "
                f"@{USUARIO_DOS_COOKIES} agora faria as duas saírem do mesmo "
                f"endereço de rede no mesmo dia, que é justamente o padrão que "
                f"leva ao bloqueio. Volte para a @{dona_do_dia} ou espere o dia "
                f"virar.",
                usados, restantes)

    ate = conta.get("pausada_ate")
    if ate:
        quando = datetime.strptime(ate, "%Y-%m-%d %H:%M:%S")
        if datetime.now() < quando:
            falta = quando - datetime.now()
            horas = int(falta.total_seconds() // 3600)
            minutos = int((falta.total_seconds() % 3600) // 60)

            # O aviso da pausa também precisa dizer só o que se sabe
            # (corrigido em 30/08/2026, depois de a mensagem do bloqueio já ter
            # sido corrigida e esta ter ficado para trás, contradizendo a
            # outra na mesma tela). Ver mensagem_de_recuo.
            causa = str(conta.get("ultimo_bloqueio") or "")
            if any(s in causa.lower() for s in SINAIS_AMBIGUOS):
                porque = ("porque o Instagram respondeu que seria preciso entrar na "
                          "conta, mesmo com a sessão configurada. Isso costuma ser "
                          "recusa passageira daquele endereço, e não quer dizer que a "
                          "conta foi sinalizada")
                conselho = ("Se o aplicativo não mostrar aviso nenhum, dá para tirar "
                            "a pausa com fluxo.liberar_conta(). Vale conferir antes se "
                            "os cookies do arquivo ainda são os da sessão atual: eles "
                            "envelhecem sozinhos.")
            else:
                porque = "porque o Instagram barrou o acesso"
                conselho = ("Insistir agora é o que transforma bloqueio temporário em "
                            "conta sinalizada.")
            return (False,
                    f"A conta @{USUARIO_DOS_COOKIES} está em pausa até "
                    f"{quando:%d/%m às %H:%M} (faltam {horas}h{minutos:02d}) {porque}. "
                    f"{conselho}",
                    usados, restantes)
    if restantes == 0:
        # VIROU AVISO, NÃO TRAVA (17/09/2026, decisão do auditor, depois de
        # eu levantar a tensão com a metodologia de subida medida: sem a
        # trava, uma semana "em 20" deixa de provar que ficou em 20). O
        # NÚMERO CONTINUA SENDO ESCOLHA, NÃO MEDIÇÃO, e por isso vira só
        # recomendação: `pode_usar` agora é True mesmo tendo passado do
        # teto, então nenhuma chamada para de funcionar por causa disto.
        # As DUAS OUTRAS travas desta função (uma conta por dia, pausa
        # depois de bloqueio real do Instagram) CONTINUAM travando de
        # verdade: são proteção contra padrão que já sinalizou conta de
        # verdade em agosto de 2026, não um número de referência.
        return (True,
                f"A conta @{USUARIO_DOS_COOKIES} já passou do teto recomendado de "
                f"{limite_diario_vigente()} hoje ({usados} feitos). Continua "
                f"funcionando normalmente; é só um número de referência.",
                usados, 0)
    return True, "", usados, restantes


def _contar_uso_instagram():
    # A trava pega o ciclo inteiro de ler, somar e gravar, não só a gravação.
    # Sem ela, duas chamadas ao mesmo tempo leem o mesmo número, somam 1 cada
    # uma e gravam o mesmo valor: duas chamadas ao Instagram contam como uma
    # só, e o teto diário passa a valer pela metade sem nenhum aviso na tela.
    # Foi descuido com esse contador que marcou duas contas em agosto de 2026,
    # e ali havia uma pessoa só usando o programa (trava criada em 29/08/2026).
    with trava.travar(ARQUIVO_ESTADO_CONTA):
        estado, conta = _estado_da_conta()
        conta["usados"] += 1
        _marcar_conta_do_dia(estado)
        _gravar_estado_conta(estado)
    # FORA DA TRAVA LOCAL DE PROPÓSITO (24/09/2026): é chamada de rede, e
    # travar o arquivo local enquanto se espera o Google só prenderia outra
    # chamada desta mesma máquina sem motivo. Falha em silêncio, mesma
    # convenção de _registrar_evento_compartilhado: a chamada ao Instagram
    # já aconteceu antes desta função ser chamada, e uma falha aqui não pode
    # fazer parecer que o download em si falhou.
    _registrar_evento_compartilhado("uso")


class PerfilDesconhecido(RuntimeError):
    """Não foi possível descobrir o número do perfil daquele influenciador.

    É falha de UM influenciador, não da conta. Quem trata erro do Instagram
    precisa distinguir: pausar a conta por causa disso deixaria de baixar
    também os influenciadores cujo número já está guardado, que nem chegam a
    tocar no endereço que causou o problema."""


def e_so_espera(erro):
    """O Instagram pediu pra ir mais devagar, mas não desconfiou da conta.
    Se houver qualquer sinal de conta marcada, vale o tratamento severo."""
    texto = str(erro).lower()
    if any(s in texto for s in SINAIS_DE_CONTA_MARCADA):
        return False
    return any(s in texto for s in SINAIS_DE_ESPERA)


def _acionar_freio(motivo):
    """Chamado quando o Instagram barra: guarda a conta por um tempo em vez de
    deixar o programa tentar de novo.

    Quanto tempo depende do que aconteceu. Pedido de "vá devagar" custa uma
    hora na primeira vez do dia e DOBRA a cada repetição; desconfiança da conta
    custa o dia inteiro. Ver SINAIS_DE_ESPERA e SINAIS_DE_CONTA_MARCADA."""
    # Trava pelo mesmo motivo do contador: a contagem de esperas do dia é o
    # que dobra a pausa a cada repetição, e uma gravação em cima da outra
    # zeraria esse crescimento justamente quando ele mais importa.
    with trava.travar(ARQUIVO_ESTADO_CONTA):
        estado, conta = _estado_da_conta()

        if e_so_espera(motivo):
            anteriores = int(conta.get("esperas_hoje") or 0)
            horas = min(HORAS_PAUSA_PRIMEIRA_ESPERA * (2 ** anteriores),
                        HORAS_PAUSA_ESPERA_MAXIMA)
            conta["esperas_hoje"] = anteriores + 1
            conta["tipo_ultima_pausa"] = "espera"
        else:
            horas = HORAS_PAUSA_APOS_BLOQUEIO
            conta["tipo_ultima_pausa"] = "conta marcada"

        ate = datetime.now() + timedelta(hours=horas)
        conta["pausada_ate"] = ate.strftime("%Y-%m-%d %H:%M:%S")
        conta["ultimo_bloqueio"] = str(motivo)[:200]
        _gravar_estado_conta(estado)
    # AVISA AS OUTRAS MÁQUINAS (22/09/2026), fora da trava local: é chamada de
    # rede, e prender a trava de arquivo durante ela seguraria qualquer outra
    # thread desta máquina que só quisesse ler o estado. Ver o comentário
    # grande perto de ABA_ESTADO_INSTAGRAM.
    _registrar_evento_compartilhado("pausa", conta["pausada_ate"], motivo)
    return ate


def liberar_conta(usuario=None):
    """Tira a pausa de uma conta, para quando dá pra afirmar que ela está bem
    (por exemplo, olhando o aplicativo no celular e não vendo aviso nenhum).
    Devolve True se havia pausa pra tirar."""
    with trava.travar(ARQUIVO_ESTADO_CONTA):
        estado = _ler_estado_conta()
        conta = estado.get(usuario or USUARIO_DOS_COOKIES)
        if not conta or not conta.get("pausada_ate"):
            return False
        conta["pausada_ate"] = None
        conta["liberada_manualmente_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _gravar_estado_conta(estado)
    # QUEM LIBEROU AVISA AS OUTRAS MÁQUINAS TAMBÉM (22/09/2026), senão a
    # próxima sincronia (_sincronizar_pausa_compartilhada) reimporia a pausa
    # antiga que ainda está lá na planilha, porque ela só some quando alguém
    # grava um evento mais recente. Usa uma conta temporária ao chamar
    # _registrar_evento_compartilhado, já que ela sempre grava com
    # USUARIO_DOS_COOKIES; quando `usuario` é outra conta, a liberação daqui
    # é só local e a planilha compartilhada não reflete essa conta alheia.
    if not usuario or usuario == USUARIO_DOS_COOKIES:
        _registrar_evento_compartilhado("liberada")
    return True


def parece_bloqueio(erro):
    texto = str(erro).lower()
    return any(s in texto for s in SINAIS_DE_BLOQUEIO)


# Sinais que fazem o programa recuar mas NÃO dizem que a conta foi sinalizada.
SINAIS_AMBIGUOS = (SESSAO_RECUSADA,)


def e_perfil_sem_story(erro):
    """O perfil não tem story no ar agora. Não é bloqueio, não é culpa da
    conta, e NÃO pode acionar o freio (ver SEM_STORY_NO_AR)."""
    return SEM_STORY_NO_AR in str(erro).lower()

# Trecho fixo dentro da mensagem de recuo, usado para RECONHECER depois que a
# falha foi da conta e não do link (ver processar_fila).
#
# Existe porque a detecção era feita casando pedaços do texto da mensagem, e
# ao reescrever a mensagem em 30/08/2026 essa detecção teria quebrado em
# silêncio: linha que parou por causa da pausa seria marcada como defeito
# permanente do link, e nunca mais voltaria sozinha para a fila. Com o trecho
# numa constante, mudar o texto não quebra mais nada.
MARCA_DE_RECUO = "O programa recua"


def mensagem_de_recuo(erro, ate):
    """Texto para quando o programa recua depois de o Instagram recusar.

    Corrigido em 30/08/2026, e a correção é de honestidade, não de estilo.
    O texto anterior dizia "o Instagram barrou o acesso da conta" para
    qualquer sinal. Para 429 e checkpoint isso cabe. Para "you need to log in"
    não: o programa estava diagnosticando o que apenas observou.

    A diferença importa na prática. O auditor conferiu a conta no aplicativo
    depois de uma dessas recusas e não havia aviso nenhum, o que é evidência
    de que a conta NÃO foi sinalizada, já que o Instagram avisa quando
    desconfia. Uma mensagem alarmista leva a pessoa a tratar como incidente
    algo que provavelmente é recusa passageira daquele endereço.

    O programa recua igual nos dois casos, porque recuar é barato e insistir
    não é. O que muda é o que ele afirma."""
    texto = str(erro)
    if any(s in texto.lower() for s in SINAIS_AMBIGUOS):
        cabeca = (
            f"O Instagram não entregou os dados desse perfil para a conta "
            f"@{USUARIO_DOS_COOKIES}. Isso pode ser recusa passageira da sessão, mas "
            f"também pode ser perfil privado que a conta não segue, ou perfil que não "
            f"existe. NÃO quer dizer que a conta foi sinalizada: quando isso acontece, "
            f"o Instagram avisa no aplicativo."
        )
    else:
        cabeca = f"O Instagram barrou o acesso da conta @{USUARIO_DOS_COOKIES}."
    return (
        f"{cabeca} {MARCA_DE_RECUO} até {ate:%d/%m às %H:%M} por precaução, porque "
        f"insistir depois de uma recusa é o que transforma limite temporário em conta "
        f"sinalizada. Se você abrir o aplicativo e não houver aviso nenhum, dá para "
        f"tirar a pausa com fluxo.liberar_conta(). Detalhe técnico: {texto[:200]}"
    )


def _cookiejar():
    """Cookies exportados (formato Netscape/cookies.txt), prontos pra usar
    com qualquer lib que aceite um http.cookiejar (instaloader, requests).
    None se o arquivo não existir."""
    if not os.path.exists(ARQUIVO_COOKIES):
        return None
    cj = http.cookiejar.MozillaCookieJar(ARQUIVO_COOKIES)
    cj.load(ignore_discard=True, ignore_expires=True)
    return cj


# Palavras que aparecem na posição do @ no endereço e não são o @ de ninguém.
# O Instagram gera instagram.com/share/reel/CODIGO no "copiar link", e sem esta
# lista o programa criava uma pasta @share no Drive (achado em 30/08/2026).
NAO_SAO_HANDLE = {"p", "reel", "reels", "tv", "stories", "explore", "accounts",
                  "share", "s", "direct", "www"}

_REGEX_STORY = re.compile(r"instagram\.com/stories/(?P<handle>[^/]+)(?:/(?P<mediaid>\d+))?")
# Reel ou post normal, ex: instagram.com/feijhonys/reel/DMvHalbg8dD/
_REGEX_POST = re.compile(r"instagram\.com/(?P<handle>[^/]+)/(?:reel|reels|p|tv)/[\w-]+")

# O CÓDIGO DO POST, que é o que o instaloader precisa para baixar sem passar pelo
# número interno do perfil. Aceita com e sem o @ no caminho, porque o "copiar
# link" do Instagram gera as duas formas: instagram.com/p/CODIGO e
# instagram.com/perfil/p/CODIGO.
# O QUE TEM CARA DE @ E O QUE NÃO TEM (06/09/2026).
#
# O yt-dlp devolve, no campo "uploader", ora o @ do perfil, ora o NOME DE
# EXIBIÇÃO ("julya freitas", com espaço e maiúsculas). Guardar o número do
# perfil sob um nome de exibição quebra o cache em silêncio: na próxima vez o
# programa procura por "@julyafreitas" e não acha nada.
#
# Handle do Instagram só tem letra, número, ponto e sublinhado. Espaço nunca.
_REGEX_HANDLE_VALIDO = re.compile(r"^[a-z0-9._]{1,30}$")


def parece_handle(texto):
    """Se aquele texto pode ser um @ de perfil, e não um nome de exibição."""
    return bool(_REGEX_HANDLE_VALIDO.fullmatch(
        str(texto or "").strip().lstrip("@").lower()))


_REGEX_CODIGO_DO_POST = re.compile(
    r"instagram\.com/(?:[^/]+/)?(?:reel|reels|p|tv)/(?P<codigo>[\w-]+)")


def handle_dos_dados_do_video(info):
    """@ do influenciador tirado dos dados que a plataforma devolve junto com
    o vídeo.

    Existe desde 30/08/2026 para os endereços que NÃO trazem o @, que é o
    formato curto que o "copiar link" do Instagram gera
    (instagram.com/reel/CODIGO). Antes disso, esses casos obrigavam a pessoa a
    digitar o @ à mão, e cada letra trocada cria uma pasta separada no Drive para
    o mesmo influenciador. Ler o @ da fonte tira a digitação do caminho, e é isso
    que resolve, não a esperança de que ninguém erre.

    RECUSA em vez de limpar o que não parece @. Um @ do Instagram só tem
    letra, número, ponto e sublinhado; se o campo trouxer "Canal do Fulano" ou
    um número interno de perfil, é outra informação, e transformá-la à força
    num @ criaria pasta que não corresponde a ninguém."""
    for campo in ("channel", "uploader_id", "uploader"):
        valor = str((info or {}).get(campo) or "").strip().lstrip("@").strip().lower()
        if not re.fullmatch(r"[a-z0-9_.]+", valor or ""):
            continue
        if valor.isdigit() or valor in NAO_SAO_HANDLE:
            continue
        return valor
    return None


def handle_do_link(link):
    """@ verdadeiro do influenciador, lido da própria URL do Instagram.

    É mais confiável que o nome digitado na planilha: digitação erra, e cada
    erro criaria uma pasta separada no Drive pro mesmo influenciador. Devolve
    None pra link que não é do Instagram (YouTube, TikTok), onde só resta mesmo
    o nome digitado.

    ATENÇÃO AO QUE NÃO É @: no endereço, a posição do @ é ocupada por outras
    palavras em alguns formatos. O "copiar link" do Instagram gera
    instagram.com/share/reel/CODIGO, e até 30/08/2026 isso devolvia "share"
    como se fosse o nome do influenciador, criando uma pasta @share no Drive.
    Por isso a lista de recusa abaixo."""
    for regex in (_REGEX_STORY, _REGEX_POST):
        m = regex.search(link or "")
        if m:
            achado = m.group("handle").lower()
            if achado in NAO_SAO_HANDLE:
                return None
            return achado
    return None


# FUSO DE BRASÍLIA ESCRITO À MÃO, E NÃO VINDO DE BIBLIOTECA (11/09/2026).
#
# O Brasil não tem horário de verão desde 2019, então o deslocamento é fixo em
# -3. Usar zoneinfo traria dependência de base de fusos do sistema, que é uma
# coisa a mais para faltar numa máquina nova, para resolver um caso que não
# existe mais. Se o horário de verão voltar, este é o lugar de mexer.
FUSO_DE_BRASILIA = timezone(timedelta(hours=-3))


def hora_de_brasilia(quando):
    """A hora do post no horário de Brasília, ou None se não veio hora.

    POR QUE EXISTE (11/09/2026): o Calendário de Divulgações do Marketing tem
    coluna de Horário, e o auditor perguntou se dava para estimar. Não precisa:
    o Instagram já manda a hora exata, e o programa jogava fora com um
    `.date()` em três lugares.

    O Instagram entrega em UTC (`date_utc` do instaloader, `timestamp` do
    yt-dlp). Escrever isso direto na planilha sairia 3 horas adiantado, e é
    erro que ninguém percebe olhando: 22:17 e 19:17 são igualmente plausíveis
    para um story.

    Hora sem fuso declarado é tratada como UTC, que é o que o instaloader
    entrega em `date_utc`. Supor o contrário converteria duas vezes, ou
    nenhuma, dependendo da máquina."""
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return quando.astimezone(FUSO_DE_BRASILIA)


def mapa_de_posts_por_handle(links):
    """@handle -> link de um Reel/post dele, tirado da própria lista de links.
    Serve pra descobrir o número interno do perfil sem depender do endereço
    que o Instagram limita. Usa o @ que está na própria URL, não o que a
    pessoa digitou na planilha (que costuma vir com erro de digitação)."""
    mapa = {}
    for link in links:
        if not link:
            continue
        m = _REGEX_POST.search(link)
        if m:
            mapa.setdefault(m.group("handle").lower(), link)
    return mapa


def _ler_userids():
    if not os.path.exists(ARQUIVO_USERIDS):
        return {}
    import json
    with open(ARQUIVO_USERIDS, "r", encoding="utf-8") as f:
        return json.load(f)


# O MAPA DE PERFIS PASSOU A VIAJAR ENTRE AS MÁQUINAS (23/09/2026)
#
# POR QUE, e a pergunta foi do auditor pensando na subida: o mapa é um arquivo
# LOCAL de cada instalação, então o que uma máquina aprende as outras não
# sabem. Com seis pessoas baixando cada uma no próprio notebook, o mesmo
# influenciador podia ser descoberto seis vezes, e cada descoberta passa pelo
# endereço que o Instagram limita com mais rigor: medido em 28/08/2026, a
# conta levou bloqueio com TRÊS chamadas nele num dia.
#
# A saída documentada até aqui era manual ("vale copiar entre máquinas", no
# COMECE_AQUI). Funciona e depende de alguém lembrar, que é o tipo de proteção
# que falha justamente no dia corrido.
#
# ONDE FICA: mesma planilha de fechamentos e mesmo padrão de SÓ ACRESCENTAR
# LINHA da aba Estado_Instagram (ver o comentário grande dela). Aba própria, e
# não um evento novo naquela, porque as colunas são outras: aqui não há conta
# nem pausa, há @ e número.
#
# É INFORMAÇÃO PÚBLICA: o @ e o número interno do perfil aparecem pra qualquer
# um que abra a página. Não há dado pessoal de apostador envolvido, que é o que
# esta planilha nunca pode receber.
#
# SE A PLANILHA NÃO ESTIVER CONFIGURADA, tudo isto fica inerte e o programa
# volta ao comportamento de antes, com o mapa só local. Mesma convenção do
# resto do projeto.
ABA_PERFIS_INSTAGRAM = "Perfis_Instagram"
CAMPOS_PERFIS_INSTAGRAM = ("quando", "handle", "userid", "maquina")
# CINCO MINUTOS, e não um como a pausa: pausa é urgente (a outra máquina
# precisa parar agora), perfil não muda nunca depois de descoberto.
SEGUNDOS_ENTRE_SINCRONIAS_PERFIS = 300
_ULTIMA_SINCRONIA_PERFIS = {"quando": 0.0}


def _registrar_perfil_compartilhado(handle, userid):
    """Acrescenta o perfil na aba compartilhada, para as outras máquinas.

    Falha em silêncio, de propósito: o mapa local já foi gravado antes desta
    chamada, então uma falha aqui não pode fazer parecer que o aprendizado se
    perdeu. Ela custa, no máximo, outra máquina gastar a chamada de novo."""
    try:
        import registro_fechamentos
        import sheets_client
        planilha = _planilha_fechamentos_id()
        if not planilha:
            return
        registro_fechamentos.garantir_cabecalho(
            planilha, CAMPOS_PERFIS_INSTAGRAM, aba=ABA_PERFIS_INSTAGRAM)
        letra_fim = registro_fechamentos._letra(len(CAMPOS_PERFIS_INSTAGRAM))
        maquina = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or ""
        sheets_client.adicionar_linhas(
            planilha, ABA_PERFIS_INSTAGRAM, f"A:{letra_fim}",
            [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
              str(handle), str(userid), maquina]])
    except Exception:
        pass


def _perfis_compartilhados():
    """{handle: userid} da aba compartilhada, ou {} quando não dá para ler.

    Linha mais recente do mesmo @ manda, pelo mesmo motivo da aba de estado:
    só se acrescenta linha, nunca se corrige uma."""
    planilha = _planilha_fechamentos_id()
    if not planilha:
        return {}
    try:
        import sheets_client
        letra_fim = chr(ord("A") + len(CAMPOS_PERFIS_INSTAGRAM) - 1)
        linhas = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha,
                range=f"'{ABA_PERFIS_INSTAGRAM}'!A2:{letra_fim}20000").execute()
        ).get("values", [])
    except Exception:
        return {}
    achados = {}
    for linha in linhas:
        if len(linha) < 3:
            continue
        chave = str(linha[1]).strip().lstrip("@").lower()
        try:
            achados[chave] = int(str(linha[2]).strip())
        except (TypeError, ValueError):
            continue
    return achados


def _sincronizar_perfis_compartilhados():
    """Traz para o mapa local os perfis que OUTRA máquina já descobriu.

    SÓ ACRESCENTA, nunca corrige o que já está aqui: o número local foi
    descoberto por esta máquina e vale tanto quanto o de lá. Sem essa regra,
    uma linha errada na planilha apagaria conhecimento bom de todo mundo.

    Consulta a planilha no máximo a cada SEGUNDOS_ENTRE_SINCRONIAS_PERFIS."""
    import json
    import time
    agora = time.time()
    if agora - _ULTIMA_SINCRONIA_PERFIS["quando"] < SEGUNDOS_ENTRE_SINCRONIAS_PERFIS:
        return
    _ULTIMA_SINCRONIA_PERFIS["quando"] = agora
    de_fora = _perfis_compartilhados()
    if not de_fora:
        return
    with trava.travar(ARQUIVO_USERIDS):
        mapa = _ler_userids()
        novos = {h: u for h, u in de_fora.items() if h not in mapa}
        if not novos:
            return
        mapa.update(novos)
        os.makedirs(PASTA_TESTE, exist_ok=True)
        with open(ARQUIVO_USERIDS, "w", encoding="utf-8") as f:
            json.dump(mapa, f, ensure_ascii=False, indent=2, sort_keys=True)


def guardar_userid(handle, userid):
    """Guarda o número interno do perfil pra não precisar descobrir de novo.

    Trava o ciclo de ler e gravar (29/08/2026): descobrir esse número é a
    chamada mais cara e mais arriscada do programa, então perder um que já foi
    descoberto, porque outra gravação passou por cima, significa gastar de
    novo a chamada que costuma levar bloqueio.

    DESDE 23/09/2026 O APRENDIZADO TAMBÉM SOBE para a aba compartilhada, para
    as outras máquinas não pagarem de novo pelo mesmo número. O local é
    gravado ANTES, e a subida falha em silêncio: o que não pode é esta máquina
    perder o que descobriu por causa da rede."""
    import json
    chave = str(handle).strip().lstrip("@").lower()
    with trava.travar(ARQUIVO_USERIDS):
        mapa = _ler_userids()
        mapa[chave] = int(userid)
        os.makedirs(PASTA_TESTE, exist_ok=True)
        with open(ARQUIVO_USERIDS, "w", encoding="utf-8") as f:
            json.dump(mapa, f, ensure_ascii=False, indent=2, sort_keys=True)
    # A PROTEÇÃO É AQUI TAMBÉM, e não só dentro de quem sobe. Parece
    # redundante e não é: a regra que importa é "nada que aconteça com a
    # planilha pode fazer esta máquina perder o número que acabou de
    # descobrir", e ela não pode depender de uma função vizinha continuar
    # engolindo erro. O teste deste arquivo reprova se esta guarda sumir.
    try:
        _registrar_perfil_compartilhado(chave, int(userid))
    except Exception:
        pass


def userid_guardado(handle):
    """Número interno do perfil, se o programa já souber. None se não souber.

    SÓ CONSULTA A PLANILHA QUANDO NÃO SABE (23/09/2026), e é o momento exato
    de valer a pena: saber aqui evita a chamada mais arriscada do programa, e
    não saber não custa nada além de uma leitura já limitada por tempo."""
    chave = str(handle).strip().lstrip("@").lower()
    try:
        achado = _ler_userids().get(chave)
    except Exception:
        # Arquivo ilegível não pode derrubar a tela. "Não sei" é a resposta
        # segura: ela leva ao aviso, e não a um download que gasta chamada.
        return None
    if achado is not None:
        return achado
    try:
        _sincronizar_perfis_compartilhados()
        return _ler_userids().get(chave)
    except Exception:
        return None


def conferir_link_antes_da_fila(link):
    """Diz se vale enfileirar aquele link, e o que avisar. Devolve
    (pode_seguir, aviso), com aviso None quando não há nada a dizer.

    CUSTA ZERO CHAMADA AO INSTAGRAM: olha o texto do endereço e o arquivo de
    perfis que o programa já conhece. É isso que a torna possível na hora em que
    a pessoa cola o link, e não depois.

    O PROBLEMA QUE ELA RESOLVE (registrado como pendência em 31/08/2026, feito em
    01/09/2026)

    O endereço de story só ganha o número da mídia quando a pessoa NAVEGA entre
    os stories do perfil. Quem copia da barra sem navegar leva
    "instagram.com/stories/perfil/" e pronto. O auditor conhece o contorno,
    passar para o story seguinte e voltar, mas ninguém deveria precisar saber
    disso, e nada na tela dizia.

    O QUE ACONTECE SEM O NÚMERO, e são dois casos diferentes:

      perfil que o programa JÁ CONHECE  funciona SE houver um story só. Com
                                        vários, o programa não escolhe por conta
                                        própria qual peça auditar, e para.
      perfil DESCONHECIDO               precisa descobrir o número interno do
                                        perfil, que é a chamada mais arriscada
                                        do programa. Falhou assim em 31/08/2026
                                        com @andersonneiff: 429 Too Many
                                        Requests, e a chamada foi gasta à toa.

    Por isso o segundo caso BARRA e o primeiro apenas avisa. Barrar tudo tiraria
    o caso legítimo de quem tem um story só, que foi preservado de propósito
    quando essa parte foi escrita em 29/08."""
    texto = str(link or "").strip()
    achado = _REGEX_STORY.search(texto)
    if not achado or achado.group("mediaid"):
        return True, None

    handle = (achado.group("handle") or "").lower()
    como_pegar = (
        "Para pegar o endereço com o número: abra o story, **passe para o "
        "seguinte e volte** com as setas. O endereço na barra ganha o número, e "
        "fica parecido com `instagram.com/stories/"
        f"{handle}/3976150764074509695/`."
    )

    if userid_guardado(handle) is None:
        # A MENSAGEM MANDAVA FAZER O QUE NEM SEMPRE DÁ, E O QUE NÃO RESOLVIA
        # (corrigida em 02/09/2026).
        #
        # Ela pedia o número da peça, ensinando a passar para o story seguinte e
        # voltar. O auditor respondeu o caso que ela não previa: "nesse caso, o
        # story é único no momento, não consigo passar pro próximo". Com um story
        # só, não há para onde passar, e o número não aparece na barra.
        #
        # Pior: o número NÃO resolveria este caso. Com perfil desconhecido o
        # programa precisa do número interno DO PERFIL de qualquer jeito, e é
        # essa consulta, pelo @, que o Instagram limita com rigor. O número da
        # peça serve para escolher entre vários stories ativos, e é outra coisa.
        # Ou seja, a mensagem explicava a recusa por um motivo errado e apontava
        # uma saída que não levava a lugar nenhum.
        #
        # A saída real é ensinar o perfil, que ficou barata de propósito: ver
        # aprender_perfil_por_link.
        return False, (
            f"**Ainda não conheço o perfil @{handle}, então não vou tentar esse "
            f"story.**\n\n"
            f"Para story de perfil novo o programa precisa do número interno do "
            f"perfil, e descobrir isso pelo @ é a consulta que o Instagram "
            f"limita com mais rigor: em 31/08 respondeu *429 Too Many Requests* "
            f"e a chamada foi gasta sem baixar nada. O número da peça no endereço "
            f"não substitui isso, então passar para o story seguinte e voltar não "
            f"ajuda aqui.\n\n"
            f"**O caminho:** use **Ensinar um perfil ao programa**, logo abaixo, "
            f"com um link de Reel ou post de @{handle}. Ele lê só o número do "
            f"perfil, não baixa o vídeo, não cria linha na Monitoramento, e na "
            f"maioria das vezes nem gasta chamada. Depois disso os stories desse "
            f"perfil funcionam.\n\n"
            f"Se @{handle} não tiver nenhum Reel ou post, baixe o story pelo "
            f"navegador e mande o arquivo pela seção de envio, que não fala com "
            f"o Instagram."
        )

    return True, (
        f"Este endereço não tem o número da peça. Como eu já conheço o perfil "
        f"@{handle}, vou tentar, **mas isso só funciona se ele tiver UM story no "
        f"ar**. Com vários, o programa para em vez de escolher por conta própria "
        f"qual peça auditar.\n\n{como_pegar}"
    )


def userid_por_link_de_post(link_post):
    """Descobre o número interno do perfil a partir de um link de Reel ou post
    dele, lendo os dados do próprio vídeo.

    DEIXOU DE SER ANÔNIMO em 28/08/2026. O Instagram passou a responder
    "resposta de mídia vazia" para acesso sem login: medido em 16 links reais,
    14 falharam anonimamente. Com os cookies configurados, o mesmo link
    responde na hora. Então tenta anônimo primeiro, porque quando funciona não
    custa nada, e só cai pro autenticado se precisar.

    A tentativa autenticada CONTA no teto diário, como qualquer outra conversa
    com o Instagram usando a conta. Antes não contava, e isso era um buraco: o
    programa achava que tinha feito menos chamadas do que realmente fez."""
    import yt_dlp

    def _extrair(opcoes):
        with yt_dlp.YoutubeDL({**opcoes, "quiet": True, "no_warnings": True,
                               "skip_download": True}) as ydl:
            return ydl.extract_info(link_post, download=False)

    info = None
    try:
        info = _extrair({})
    except Exception:
        pass

    if not info or not str(info.get("uploader_id") or "").isdigit():
        if not os.path.exists(ARQUIVO_COOKIES):
            raise RuntimeError(
                f"Não consegui ler o número do perfil nesse link sem estar logado, e não há "
                f"cookies configurados: {link_post}")
        pode, motivo, _usados, _restantes = situacao_da_conta()
        if not pode:
            raise RuntimeError(motivo)
        _contar_uso_instagram()
        info = _extrair({"cookiefile": ARQUIVO_COOKIES})

    uploader_id = info.get("uploader_id") if info else None
    if not uploader_id or not str(uploader_id).isdigit():
        raise RuntimeError(f"Não consegui ler o número do perfil nesse link: {link_post}")
    return int(uploader_id)


def userid_e_handle_por_link_de_post(link_post):
    """O número interno E o @ de quem publicou, da mesma leitura.

    POR QUE OS DOIS JUNTOS (06/09/2026)

    O endereço canônico do Instagram, o que sai do botão de compartilhar, é
    `instagram.com/p/CODIGO` e NÃO traz o @. Para guardar o número no cache é
    preciso saber sob que nome, e a única fonte confiável desse nome é o
    próprio post: pegar de outro lugar seria confiar em quem colou o link.

    UM @ ERRADO ENVENENA O CACHE de um jeito silencioso e feio: os Stories
    daquele nome passariam a vir de OUTRA pessoa, e nada na tela indicaria isso.
    Por isso o handle do post manda sobre o da URL.

    Devolve (userid, handle) — handle pode vir None se o Instagram não o
    entregar, e nesse caso quem chama decide o que fazer."""
    import yt_dlp

    def _extrair(opcoes):
        with yt_dlp.YoutubeDL({**opcoes, "quiet": True, "no_warnings": True,
                               "skip_download": True}) as ydl:
            return ydl.extract_info(link_post, download=False)

    info = None
    try:
        info = _extrair({})
    except Exception:
        pass

    if not info or not str(info.get("uploader_id") or "").isdigit():
        # ANTES DE GASTAR A CHAMADA, VER SE O PERFIL JÁ É CONHECIDO
        # (07/09/2026).
        #
        # A tentativa anônima acima é de graça e costuma trazer o @ de quem
        # publicou mesmo quando não traz o número interno. Se aquele @ já está no
        # mapa de perfis, o número já é sabido, e a conversa autenticada abaixo
        # seria gastar a chamada mais limitada do Instagram para descobrir uma
        # coisa que o programa já tem escrita em disco.
        #
        # QUEM CAI AQUI: link no formato curto, instagram.com/p/CODIGO, que é o
        # que o botão de compartilhar do Instagram gera. Ele não traz o @ no
        # endereço, então quem chama não tinha como consultar o cache antes, e
        # esse era o caso descrito na pendência.
        #
        # O @ vem de handle_dos_dados_do_video, que RECUSA nome de exibição e
        # número. Aceitar qualquer coisa aqui devolveria o perfil errado, que é
        # muito pior do que gastar uma chamada.
        handle_anonimo = handle_dos_dados_do_video(info)
        if handle_anonimo:
            guardado = userid_guardado(handle_anonimo)
            if guardado:
                return int(guardado), handle_anonimo
        if not os.path.exists(ARQUIVO_COOKIES):
            raise RuntimeError(
                f"Não consegui ler o número do perfil nesse link sem estar "
                f"logado, e não há cookies configurados: {link_post}")
        pode, motivo, _usados, _restantes = situacao_da_conta()
        if not pode:
            raise RuntimeError(motivo)
        _contar_uso_instagram()
        # DENTRO DE try, porque a falha aqui NÃO é o fim do caminho: post de
        # foto faz o yt-dlp estourar "No video formats found", e é exatamente
        # esse caso que o instaloader resolve logo abaixo. Sem o try, o erro
        # subia e o recuo nunca era alcançado.
        try:
            info = _extrair({"cookiefile": ARQUIVO_COOKIES})
        except Exception:
            info = None

    uploader_id = info.get("uploader_id") if info else None
    if uploader_id and str(uploader_id).isdigit():
        # O yt-dlp entrega o @ em "uploader" ou "channel", conforme o extrator.
        bruto = (info.get("uploader") or info.get("channel") or "").strip()
        limpo = bruto.lstrip("@").lower()
        # SÓ DEVOLVE SE FOR HANDLE DE VERDADE. Quando o yt-dlp entrega o nome de
        # exibição, é melhor devolver None e deixar quem chama usar o @ do
        # endereço do que guardar "julya freitas" como se fosse um perfil.
        return int(uploader_id), (limpo if parece_handle(limpo) else None)

    # RECUO PELO INSTALOADER, PARA POST DE FOTO (06/09/2026).
    #
    # O auditor mandou `instagram.com/p/DccPQahHaLs/?img_index=1`, um post de
    # FOTOS, e o yt-dlp respondeu "No video formats found!". Ele é extrator de
    # vídeo: post sem vídeo nenhum não tem formato para ele achar. Já era achado
    # conhecido (02/09/2026) no caminho de download; faltava aqui, no de
    # aprender o perfil.
    #
    # E APRENDER O PERFIL NÃO PRECISA DE VÍDEO: só do dono do post. O
    # instaloader lê isso pelo código do post, que está no próprio endereço, sem
    # passar pela consulta por @ que o Instagram limita com rigor.
    return _userid_e_handle_pelo_instaloader(link_post)


def _userid_e_handle_pelo_instaloader(link_post):
    """O dono de um post, lido pelo código do post. Serve para post de foto,
    que o yt-dlp não devolve."""
    import instaloader
    achado = _REGEX_CODIGO_DO_POST.search(str(link_post or ""))
    if not achado:
        raise RuntimeError(f"Não achei o código do post em: {link_post}")
    if not os.path.exists(ARQUIVO_COOKIES):
        raise RuntimeError(
            "Post de foto exige login para ler o dono, e não há cookies "
            "configurados.")
    pode, motivo, _u, _r = situacao_da_conta()
    if not pode:
        raise RuntimeError(motivo)

    cj = _cookiejar()
    # user_agent: sem isso o instaloader se anuncia como Chrome no Linux, que
    # não é nem o navegador dos cookies nem o do disfarce (22/09/2026).
    L = instaloader.Instaloader(max_connection_attempts=1, sleep=False, quiet=True,
                                user_agent=IDENTIFICACAO_DO_NAVEGADOR)
    L.load_session(USUARIO_DOS_COOKIES,
                   {c.name: c.value for c in cj if "instagram.com" in c.domain})
    disfarcar_sessao_do_instaloader(L)  # depois de load_session, sempre
    # Conta antes de falar: o que o Instagram vê é a chamada, e ela acontece
    # mesmo quando a resposta não vem.
    _contar_uso_instagram()
    post = instaloader.Post.from_shortcode(L.context, achado.group("codigo"))
    dono = (getattr(post, "owner_username", "") or "").strip().lstrip("@").lower()
    # owner_username do instaloader É o @, mas passa pela mesma peneira: uma
    # fonte só de verdade sobre o que conta como handle.
    return int(post.owner_id), (dono if parece_handle(dono) else None)


def aprender_perfil_por_link(link_post):
    """Descobre e guarda o número interno de um perfil a partir de um link de
    Reel ou post dele, SEM baixar nada e SEM criar linha na Monitoramento.

    Devolve (handle, userid, quantas_chamadas_gastou).

    POR QUE EXISTE (02/09/2026)

    O auditor colou um story de @ranchodomaia__, perfil desconhecido, e a tela
    barrou. Das duas saídas que a mensagem oferecia, uma não servia para o caso
    dele ("o story é único no momento, não consigo passar pro próximo") e a
    outra, colar um Reel na fila, resolve o perfil mas BAIXA o vídeo e cria
    linha na Monitoramento: material entrando na auditoria só para o programa
    aprender um número, o que depois alguém tem que explicar ou desfazer.

    Aqui o aprendizado acontece sozinho, e é o caminho mais barato que existe:
    só extrai os dados do link (skip_download, nada de vídeo) e tenta ANÔNIMO
    primeiro, que não conta no teto do dia. Cai para a tentativa autenticada só
    se o anônimo não responder, e aí conta uma chamada, como qualquer conversa
    com o Instagram usando a conta. Por isso devolve quantas gastou: quem clica
    tem direito de saber se o teto do dia andou.

    Perfil que já é conhecido não gasta nada e não consulta ninguém."""
    texto = str(link_post or "").strip()
    # ACEITA O FORMATO SEM O @ NO ENDEREÇO (06/09/2026).
    #
    # O auditor colou `instagram.com/p/DccPQahHaLs/` e o programa recusou,
    # dizendo que não era link de post. Era: esse é o formato CANÔNICO do
    # Instagram, o que sai do botão de compartilhar. O que tem o @ no caminho
    # (`instagram.com/PERFIL/p/CODIGO`) é o formato de quando se navega pelo
    # perfil. Os dois existem e apontam para a mesma coisa.
    #
    # A validação usava _REGEX_POST, que EXIGE o @, enquanto o resto do programa
    # já usava _REGEX_CODIGO_DO_POST, em que o @ é opcional. Duas réguas para o
    # mesmo endereço, e a mais estreita estava justamente na porta de entrada.
    #
    # QUANDO NÃO HÁ @ NO ENDEREÇO, O HANDLE VEM DO PRÓPRIO POST, lido junto com
    # o número do perfil. Isso é mais seguro do que parece: guardar o número sob
    # um nome vindo da URL seria confiar em quem colou; vindo do post, é o
    # Instagram dizendo de quem é. Sem isso, um link colado com o @ errado
    # envenenaria o cache e os Stories daquele nome viriam de outra pessoa.
    achado = _REGEX_POST.search(texto)
    se_codigo = _REGEX_CODIGO_DO_POST.search(texto)
    if not achado and not se_codigo:
        raise ValueError(
            "Esse endereço não é de Reel nem de post. Preciso de um link no "
            "formato instagram.com/p/CODIGO, instagram.com/reel/CODIGO, ou com "
            "o perfil no caminho, porque é dele que o número interno do perfil "
            "é lido. Endereço de story não serve, que é justamente o que não dá "
            "para resolver sem isto.")

    handle = achado.group("handle").lower() if achado else None
    if handle:
        guardado = userid_guardado(handle)
        if guardado:
            return handle, int(guardado), 0

    # Lido antes e depois em vez de deduzido: quem decide se a tentativa
    # autenticada aconteceu é o userid_por_link_de_post, por dentro, e supor
    # aqui faria a tela mentir sobre o teto do dia em um dos dois casos.
    _pode, _motivo, usados_antes, _restantes = situacao_da_conta()
    userid, handle_do_post = userid_e_handle_por_link_de_post(texto)
    # O HANDLE DO POST MANDA sobre o da URL, quando os dois existem: quem
    # publicou é o Instagram que diz, não o endereço que alguém colou.
    handle = (handle_do_post or handle or "").lower()
    if not handle:
        raise RuntimeError(
            "Achei o número do perfil, mas não o @ de quem publicou, então não "
            "sei sob que nome guardar. Use um link com o perfil no caminho.")
    guardar_userid(handle, userid)
    _pode, _motivo, usados_depois, _restantes = situacao_da_conta()
    return handle, int(userid), max(0, usados_depois - usados_antes)


# TENTATIVA DESCARTADA, 28/08/2026: ler o número do perfil no HTML da página
# pública do influenciador, sem login. Não funciona mais. A página responde
# 200 e vem com 626 mil caracteres, mas é só o esqueleto do aplicativo: os
# dados do perfil são carregados depois, pelo navegador, e o HTML não traz o
# número. Os únicos números longos que aparecem ali são de sessão e de registro
# de erro, não do perfil. Testado contra @dendele_fc, cujo número já era
# conhecido, e não bateu.
#
# Não vale tentar de novo sem antes conferir se o HTML mudou: a chamada custa
# uma requisição e alguns segundos, e devolveria None de qualquer jeito.


def resolver_userid(handle, contexto_instaloader=None, link_post=None):
    """Número interno do perfil, na ordem mais barata e menos arriscada:
    1) o que já está guardado; 2) a partir de um link de post dele, se vier um;
    3) por último, a consulta pelo @ (a que o Instagram limita com rigor)."""
    handle_limpo = str(handle).strip().lstrip("@").lower()
    guardado = _ler_userids().get(handle_limpo)
    if guardado:
        return int(guardado)

    if link_post:
        userid = userid_por_link_de_post(link_post)
        guardar_userid(handle_limpo, userid)
        return userid

    if contexto_instaloader is not None:
        import instaloader
        try:
            perfil = instaloader.Profile.from_username(contexto_instaloader, handle_limpo)
        except Exception as e:
            # Erro genérico aqui confunde muito (parece que o Story sumiu, quando
            # na verdade só faltou saber o número do perfil). Diz o que fazer.
            #
            # Erro PRÓPRIO, e não um genérico, porque quem chama precisa saber
            # que a falha foi na consulta do perfil e NÃO no download. São
            # endereços diferentes: o Instagram limita a consulta por @ com
            # muito mais rigor. Tratar os dois igual pausava a conta inteira por
            # causa de um influenciador sem número guardado, travando junto os
            # que já tinham e que nem passam por esse endereço.
            raise PerfilDesconhecido(
                f"Ainda não sei o número do perfil de @{handle_limpo}, e a consulta pelo @ não respondeu agora "
                f"({str(e)[:80]}). Adicione na fila um link de Reel ou post desse mesmo influenciador: com ele "
                f"o número é descoberto pelo caminho comum e fica guardado pras próximas vezes."
            ) from e
        guardar_userid(handle_limpo, perfil.userid)
        return perfil.userid

    raise PerfilDesconhecido(
        f"Ainda não sei o número do perfil de @{handle_limpo}. Adicione na fila um link de Reel ou post "
        f"desse mesmo influenciador pra eu descobrir e guardar."
    )


def baixar_story_instaloader(link, pasta_destino, link_post_do_perfil=None):
    """Baixa um Story do Instagram via instaloader. Existe como caminho
    separado do yt-dlp porque o extrator de Story do yt-dlp tem um bug
    conhecido e sem previsão de correção pelos mantenedores: ele devolve uma
    "playlist vazia" (0 itens) mesmo com o Story ativo, em vez de dar erro,
    ver memória do projeto (achado de 25/08/2026). Exige cookies configurados,
    já que Story só é visível pra quem está logado.

    link_post_do_perfil: link de um Reel ou post do MESMO influenciador, usado
    só na primeira vez, pra descobrir o número interno do perfil sem passar
    pelo endereço que o Instagram limita com rigor. Depois disso fica guardado."""
    import instaloader

    pode, motivo, _usados, _restantes = situacao_da_conta()
    if not pode:
        raise RuntimeError(motivo)

    cj = _cookiejar()
    if cj is None:
        raise RuntimeError("Sem cookies configurados — Story exige login, não dá pra baixar anônimo")

    m = _REGEX_STORY.search(link)
    if not m:
        raise RuntimeError(f"Link não reconhecido como Story do Instagram: {link}")
    handle = m.group("handle")
    mediaid_alvo = m.group("mediaid")

    L = instaloader.Instaloader(
        dirname_pattern=pasta_destino,
        filename_pattern="{mediaid}",
        save_metadata=False,
        download_comments=False,
        download_video_thumbnails=False,  # senão vem um .jpg de miniatura junto, sem serventia aqui
        post_metadata_txt_pattern="",
        max_connection_attempts=1,  # falha rápido em vez de ficar tentando de novo por minutos sozinho
        sleep=False,  # desliga a espera/retentativa automática do instaloader (mesmo motivo)
        quiet=True,
        # Mesmo navegador dos cookies e do disfarce (22/09/2026, ver
        # IDENTIFICACAO_DO_NAVEGADOR). Sem isto, ia como Chrome no Linux.
        user_agent=IDENTIFICACAO_DO_NAVEGADOR,
    )
    # load_session() é o jeito oficial: monta a sessão E marca o usuário como
    # logado. Só encher os cookies na sessão na mão não basta, porque o
    # instaloader continua se achando anônimo (`is_logged_in` = bool(username)).
    L.load_session(USUARIO_DOS_COOKIES, {c.name: c.value for c in cj if "instagram.com" in c.domain})
    disfarcar_sessao_do_instaloader(L)  # depois de load_session, sempre

    # Cada conversa com o Instagram conta no teto do dia, mesmo que o vídeo
    # não venha: o que o Instagram vê é a chamada, não o resultado.
    _contar_uso_instagram()
    try:
        userid = resolver_userid(handle, contexto_instaloader=L.context, link_post=link_post_do_perfil)
        itens = [item for story in L.get_stories(userids=[userid]) for item in story.get_items()]
    except PerfilDesconhecido:
        # Falha de UM influenciador, não da conta. Não aciona o freio: o
        # endereço que recusou foi o de consulta por @, que o Instagram limita
        # com muito mais rigor que o de Story. Pausar a conta aqui travava
        # também os influenciadores cujo número já está guardado, que nem
        # passam por lá. Aconteceu em 28/08/2026 com a @cassinha.161.
        raise
    except Exception as e:
        if parece_bloqueio(e):
            raise RuntimeError(
                mensagem_de_recuo(e, _acionar_freio(e))
                + " Enquanto isso, Story precisa ser baixado no navegador e enviado pela tela."
            ) from e
        raise

    if mediaid_alvo:
        itens = [i for i in itens if str(i.mediaid).startswith(mediaid_alvo)]
    if not itens:
        raise RuntimeError("Nenhum Story ativo encontrado (expirado, sem Story agora, ou sem acesso à conta)")
    if not mediaid_alvo and len(itens) > 1:
        raise RuntimeError(
            f"{len(itens)} Stories ativos pra @{handle} — cole o link de um Story específico, não da vitrine"
        )

    # FOTO DEIXOU DE SER RECUSADA (02/09/2026).
    #
    # Aqui havia: se não for vídeo, "Story é uma foto, não um vídeo, fora do
    # escopo atual da automação". Era recusa de política, não limite técnico: o
    # item já está em mão neste ponto, e baixar foto é a mesma chamada.
    #
    # O auditor perguntou duas vezes, a segunda já esperando um não: "NÃO DÁ pra
    # baixar foto pelo mesmo link do vídeo não né?". Dá, e o resto do caminho já
    # estava pronto: a análise tem escada de OCR para imagem, mede nitidez,
    # pergunta à visão no próprio arquivo e pula o áudio; o envio pela tela já
    # aceita PNG e JPG; e o nome do arquivo preserva a extensão que vier.
    #
    # Peça publicitária em foto tem os mesmos deveres da em vídeo: aviso da
    # portaria, +18, "aposta não é investimento" e declaração de publicidade não
    # dependem de a peça se mover. Recusar foto era deixar fora da auditoria uma
    # peça que a Portaria alcança igual.
    #
    # Foto é até mais simples de analisar: uma tela só, sem amostragem de
    # quadros, então sem o risco que existiu até 29/08 de todos os quadros
    # saírem do primeiro segundo.
    item = itens[0]
    L.download_storyitem(item, target=handle)
    aceitas = tuple(EXTENSOES_VIDEO | EXTENSOES_IMAGEM)
    candidatos = [
        f for f in os.listdir(pasta_destino)
        if f.startswith(str(item.mediaid)) and f.lower().endswith(aceitas)
    ]
    if not candidatos:
        raise RuntimeError(
            "instaloader não gerou o arquivo esperado (nem vídeo nem imagem)")
    # Com foto, o instaloader pode gravar mais de um arquivo com o mesmo começo.
    # A ordem alfabética não escolhe nada de propósito, então prefere o vídeo
    # quando houver os dois, e é só isso que esta linha faz.
    candidatos.sort(key=lambda f: 0 if os.path.splitext(f)[1].lower()
                    in EXTENSOES_VIDEO else 1)
    # O terceiro item é o @ do influenciador. Aqui ele vem do próprio endereço,
    # que no formato de Story sempre o traz (ver handle_dos_dados_do_video para
    # o porquê de as três funções de download devolverem isso).
    #
    # O QUARTO ITEM É A HORA (11/09/2026). Antes esta linha fazia
    # `item.date_utc.date()` e a hora morria aqui. Ela vai para a coluna
    # Horário do Calendário de Divulgações. Ver hora_de_brasilia.
    quando = hora_de_brasilia(getattr(item, "date_utc", None))
    return (os.path.join(pasta_destino, candidatos[0]),
            quando.date() if quando else None, handle, quando)


def _chave_natural(nome):
    """Ordena "_2" antes de "_10", que a ordem alfabética inverte.

    Importa porque a ordem dos arquivos de um carrossel vira o número da tela, e
    tela trocada aponta o achado para a imagem errada."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", nome)]


def baixar_post_instaloader(link, pasta_destino):
    """Baixa post de FEED pelo instaloader, inclusive quando é foto.

    Devolve (LISTA de caminhos, data, handle, hora). A lista tem mais de um item
    quando o post é carrossel, e é por isso que esta função devolve lista onde as
    outras devolvem um caminho só. A hora entrou em 11/09/2026, para a coluna
    Horário do Calendário de Divulgações, e é None quando a origem não informa.

    POR QUE EXISTE (02/09/2026)

    O auditor testou e trouxe o erro exato do caminho normal, com um post de
    carrossel:

        ERROR: [Instagram] DcT0RkaCHbc: No video formats found!

    O yt-dlp é extrator de vídeo, então post sem vídeo nenhum não tem formato
    para ele achar. No mesmo teste, story de foto funcionou, porque story já
    tinha caminho próprio pelo instaloader. Post de feed passou a ter também.

    BAIXA PELO CÓDIGO DO POST, que está no próprio endereço, e não pelo número
    interno do perfil. A diferença não é de estilo: o número do perfil vem do
    endereço que o Instagram limita com mais rigor, e foi ele que respondeu 429
    em 31/08. Aqui esse endereço não é tocado, então perfil desconhecido também
    funciona.

    CARROSSEL VIRA VÁRIAS TELAS, e é o que a auditoria precisa: cada imagem é uma
    tela que tem que carregar os avisos por conta própria. Baixar só a primeira
    deixaria as outras sem auditoria, e nada avisaria. A numeração de tela sai da
    ordem dos arquivos, então ela é ordenada de forma natural: "_2" antes de
    "_10", que é onde a ordem alfabética erra."""
    import instaloader

    pode, motivo, _usados, _restantes = situacao_da_conta()
    if not pode:
        raise RuntimeError(motivo)

    cj = _cookiejar()
    if cj is None:
        raise RuntimeError(
            "Sem cookies configurados. Post de foto precisa de sessão do "
            "Instagram, porque o caminho anônimo do yt-dlp não devolve imagem.")

    achado = _REGEX_CODIGO_DO_POST.search(str(link or ""))
    if not achado:
        raise RuntimeError(f"Link não reconhecido como post do Instagram: {link}")
    codigo = achado.group("codigo")

    L = instaloader.Instaloader(
        dirname_pattern=pasta_destino,
        filename_pattern="{shortcode}",
        save_metadata=False,
        download_comments=False,
        download_video_thumbnails=False,  # senão vem miniatura junto, sem serventia aqui
        post_metadata_txt_pattern="",
        max_connection_attempts=1,  # falha rápido em vez de insistir sozinho
        sleep=False,
        quiet=True,
        # Mesmo navegador dos cookies e do disfarce (22/09/2026, ver
        # IDENTIFICACAO_DO_NAVEGADOR). Sem isto, ia como Chrome no Linux.
        user_agent=IDENTIFICACAO_DO_NAVEGADOR,
    )
    L.load_session(USUARIO_DOS_COOKIES,
                   {c.name: c.value for c in cj if "instagram.com" in c.domain})
    disfarcar_sessao_do_instaloader(L)  # depois de load_session, sempre

    # Conta antes de falar, como em todo caminho que fala com o Instagram: o que
    # ele vê é a chamada, e ela acontece mesmo quando o arquivo não vem.
    _contar_uso_instagram()
    try:
        post = instaloader.Post.from_shortcode(L.context, codigo)
    except Exception as e:
        if parece_bloqueio(e):
            raise RuntimeError(mensagem_de_recuo(e, _acionar_freio(e))) from e
        raise

    # O QUE APARECEU DE NOVO NA PASTA, em vez de adivinhar o nome que o
    # instaloader deu. Ele muda o sufixo conforme o post ser único ou carrossel,
    # e depender desse detalhe é o tipo de coisa que quebra numa atualização da
    # biblioteca sem ninguém entender por quê.
    antes = set(os.listdir(pasta_destino))
    L.download_post(post, target=post.owner_username)
    aceitas = tuple(EXTENSOES_VIDEO | EXTENSOES_IMAGEM)
    novos = sorted((f for f in os.listdir(pasta_destino)
                    if f not in antes and f.lower().endswith(aceitas)),
                   key=_chave_natural)
    if not novos:
        raise RuntimeError(
            "instaloader não gerou arquivo para esse post (nem vídeo nem imagem)")

    # A HORA VIAJA JUNTO DESDE 11/09/2026. Ver hora_de_brasilia: ela ia para o
    # lixo aqui, e é o que preenche a coluna Horário do Calendário.
    quando = hora_de_brasilia(getattr(post, "date_utc", None))
    data = quando.date() if quando else None
    return ([os.path.join(pasta_destino, f) for f in novos], data,
            post.owner_username, quando)


# Se o disfarce funciona nesta máquina. None enquanto não se sabe.
_disfarce_funciona = None

# Caminho do pacote de certificados já montado nesta máquina, para não
# reconstruir a cada chamada. None enquanto não se tentou.
_caminho_ca_bundle = None


def _ca_bundle_com_repositorio_windows():
    """Junta os certificados públicos normais (certifi) com os que o WINDOWS
    desta máquina já confia, num arquivo só. Devolve o caminho, ou None se não
    der (por exemplo, fora do Windows).

    POR QUE ISTO EXISTE (21/09/2026), depois de o auditor perguntar se dava
    para evitar coletar certificado máquina por máquina.

    A biblioteca de disfarce (curl_cffi) tem sua PRÓPRIA lista de
    certificados confiáveis, separada da lista do Windows. Numa máquina com
    antivírus corporativo que inspeciona HTTPS (medido: Kaspersky Endpoint
    Security, presente em toda a empresa), o Windows já confia no
    certificado daquele antivírus, mas o curl_cffi não, e a conexão do
    disfarce é recusada antes de chegar ao Instagram.

    MEDIDO EM 21/09/2026: esse certificado do Kaspersky é DIFERENTE em cada
    máquina (número de série próprio, gerado localmente), então um único
    arquivo coletado à mão não serve para todas. Coletar um por máquina
    funcionaria, mas é trabalho manual que se repete a cada máquina nova.

    A SAÍDA: em vez de coletar à mão, ler TUDO que o Windows desta própria
    máquina já confia (`ssl.enum_certificates("ROOT")`, disponível só no
    Windows) e somar à lista pública do certifi. Isso pega o certificado do
    Kaspersky sozinho, sem precisar saber o nome dele, e continua pegando
    automaticamente se a empresa um dia trocar de antivírus ou adicionar
    outro certificado corporativo, sem precisar mexer neste código de novo.

    AINDA SEM CONFIRMAÇÃO CONTRA O INSTAGRAM DE VERDADE: o mecanismo de ler o
    repositório do Windows e montar o arquivo foi testado e funciona; o que
    falta confirmar é se o curl_cffi realmente aceita e usa esse arquivo pela
    variável CURL_CA_BUNDLE nesta versão dele. Só um teste na máquina afetada,
    de verdade, prova isso."""
    global _caminho_ca_bundle
    if _caminho_ca_bundle:
        return _caminho_ca_bundle
    import ssl
    if os.name != "nt" or not hasattr(ssl, "enum_certificates"):
        return None
    try:
        import certifi
        import tempfile
        publicos = open(certifi.where(), encoding="utf-8").read()
        locais = []
        for der, _codificacao, _confianca in ssl.enum_certificates("ROOT"):
            locais.append(ssl.DER_cert_to_PEM_cert(der))
        destino = os.path.join(tempfile.gettempdir(),
                                "auditoria_influenciadores_ca_bundle.pem")
        with open(destino, "w", encoding="utf-8") as f:
            f.write(publicos)
            f.write("\n".join(locais))
        _caminho_ca_bundle = destino
        return destino
    except Exception:
        return None


def opcoes_de_disfarce():
    """Faz o programa se apresentar como um navegador de verdade, quando dá.

    POR QUE (29/08/2026): a extensão que o Marketing usa hoje pega o vídeo que
    o NAVEGADOR já carregou. O nosso programa faz requisições próprias, com os
    mesmos cookies, mas com a assinatura de um script Python, que é bem mais
    fácil de distinguir de uma pessoa navegando. O próprio extrator do
    Instagram no yt-dlp tem suporte a esse disfarce, e ele só estava desligado
    por falta da biblioteca curl-cffi.

    NEM SEMPRE DÁ, e descobrimos na prática: a rede da empresa inspeciona o
    tráfego HTTPS, e a biblioteca do disfarce traz a própria lista de
    autoridades certificadoras, que não conhece o certificado da empresa. O
    caminho normal funciona porque usa a lista do Windows, onde esse
    certificado está instalado. Resultado: com disfarce, a conexão é recusada
    antes mesmo de sair da rede.

    Por isso o disfarce RECUA SOZINHO (ver desligar_disfarce). O que NÃO se
    faz, em hipótese nenhuma, é desligar a verificação de certificado para
    forçar: isso abriria de verdade a brecha que a revisão de segurança de
    28/08/2026 concluiu não existir neste programa.

    TENTATIVA DE NÃO RECUAR, ACRESCENTADA EM 21/09/2026: antes de aceitar que
    o disfarce vai falhar por certificado, dá pro curl_cffi um pacote de
    certificados que já inclui os do Windows desta máquina (ver
    _ca_bundle_com_repositorio_windows), pela variável CURL_CA_BUNDLE, que é
    a convenção que o curl e as bibliotecas baseadas nele costumam respeitar.
    Se der certo, o disfarce nem chega a precisar recuar.

    DE CHROME PARA FIREFOX EM 22/09/2026: os cookies saem de um Firefox, então
    o disfarce tinha que ser de Firefox também. Ver PERFIL_DE_DISFARCE, no topo
    do arquivo, onde está a medição e o que ficou faltando."""
    # O NAVEGADOR VAI DITO MESMO SEM O DISFARCE (22/09/2026). Medido nesta
    # data: quando o disfarce recua, o yt-dlp volta a se apresentar como Chrome
    # no Windows, sozinho, e a sessão é de Firefox. Continua não sendo um
    # disfarce de verdade, porque a parte que denuncia está abaixo do HTTP, mas
    # pelo menos para de contradizer o navegador dono dos cookies.
    opcoes = {"http_headers": {"User-Agent": IDENTIFICACAO_DO_NAVEGADOR}}
    if _disfarce_funciona is False:
        return opcoes
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        pacote = _ca_bundle_com_repositorio_windows()
        if pacote:
            os.environ["CURL_CA_BUNDLE"] = pacote
        opcoes["impersonate"] = ImpersonateTarget(PERFIL_DE_DISFARCE)
        return opcoes
    except Exception:
        return opcoes


def e_problema_de_certificado(erro):
    """Falha de conexão por certificado, não recusa do Instagram.

    Importante distinguir: aqui a chamada nem chegou ao Instagram, então não
    é bloqueio e não deve acionar o freio da conta."""
    texto = str(erro).lower()
    return any(s in texto for s in (
        "certificate", "certificateverify", "ssl", "curl: (60)", "curl: (35)",
        "unable to get local issuer"))


def desligar_disfarce(motivo=""):
    """Desiste do disfarce até o programa ser reiniciado."""
    global _disfarce_funciona
    if _disfarce_funciona is not False:
        _disfarce_funciona = False
        print(f"[aviso] o disfarce de navegador não funciona nesta rede, seguindo "
              f"sem ele. {str(motivo)[:160]}")


# ---------------------------------------------------------------------------
# O MESMO DISFARCE PARA O INSTALOADER (22/09/2026)
#
# POR QUE, e é o buraco maior que restava: o disfarce acima só valia para o
# yt-dlp. O instaloader, que é quem busca Story e quem descobre o número do
# perfil, os dois endereços que o Instagram vigia com mais rigor, continuava
# falando por uma biblioteca de Python comum. E a diferença aparece ANTES do
# HTTP: a forma como a conexão segura é aberta já denuncia Python, e nenhum
# cabeçalho conserta isso, porque a assinatura está abaixo deles. Medido em
# 22/09: era o único caminho que ainda chegava com essa cara.
#
# POR QUE PRECISA DE ADAPTADOR: a biblioteca do disfarce entrega os cookies em
# formato diferente do que o instaloader espera. Ele percorre a lista de
# cookies procurando o de nome "csrftoken", e do outro lado vem só o nome, em
# texto. As duas classes abaixo existem só para arrumar isso. Se um dia o
# instaloader for atualizado e passar a pedir outra coisa da sessão, quebra
# ALTO, com erro de atributo, e não em silêncio.
# ---------------------------------------------------------------------------

class _CookieComNome:
    """Um cookie no formato que o instaloader espera percorrer."""
    __slots__ = ("name", "value")

    def __init__(self, name, value):
        self.name = name
        self.value = value


class _CookiesParaInstaloader:
    def __init__(self, originais):
        object.__setattr__(self, "_originais", originais)

    def __iter__(self):
        for nome, valor in self._originais.get_dict().items():
            yield _CookieComNome(nome, valor)

    def get_dict(self, *args, **kwargs):
        return self._originais.get_dict(*args, **kwargs)

    def __getattr__(self, nome):
        return getattr(self._originais, nome)


class _SessaoComDisfarce:
    """A sessão disfarçada, com a de sempre guardada atrás dela.

    RECUO SOZINHO, pelo mesmo motivo do disfarce do yt-dlp: a rede da empresa
    inspeciona o tráfego seguro, e isso aparece de forma INTERMITENTE (medido
    em 22/09/2026: o mesmo endereço recusou numa chamada e passou na seguinte).
    Quando a recusa é de certificado, a chamada nem saiu da rede, então repetir
    pela sessão de sempre não gasta nada com o Instagram. O que não se faz, em
    hipótese nenhuma, é desligar a verificação de certificado."""

    def __init__(self, disfarcada, reserva):
        object.__setattr__(self, "_disfarcada", disfarcada)
        object.__setattr__(self, "_reserva", reserva)

    @property
    def _em_uso(self):
        return self._reserva if _disfarce_funciona is False else self._disfarcada

    @property
    def cookies(self):
        atual = self._em_uso
        if atual is self._reserva:
            return atual.cookies
        return _CookiesParaInstaloader(atual.cookies)

    def _chamar(self, nome, *args, **kwargs):
        atual = self._em_uso
        if atual is self._reserva:
            return getattr(atual, nome)(*args, **kwargs)
        try:
            return getattr(atual, nome)(*args, **kwargs)
        except Exception as e:
            if not e_problema_de_certificado(e):
                raise
            desligar_disfarce(e)
            return getattr(self._reserva, nome)(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._chamar("get", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._chamar("post", *args, **kwargs)

    def __getattr__(self, nome):
        return getattr(self._em_uso, nome)

    def __setattr__(self, nome, valor):
        setattr(self._disfarcada, nome, valor)
        setattr(self._reserva, nome, valor)


def disfarcar_sessao_do_instaloader(L):
    """Troca a sessão do instaloader por uma com cara de navegador.

    Chamar SEMPRE depois de load_session, nunca antes: é load_session que monta
    a sessão, e trocar antes seria desfeito por ele.

    Devolve True se o disfarce entrou. Se qualquer coisa der errado na troca,
    devolve False e o instaloader segue como sempre foi: o download continua
    funcionando, só sem o disfarce. Preferir isso a deixar o programa parar por
    causa de uma proteção."""
    if _disfarce_funciona is False:
        return False
    try:
        from curl_cffi import requests as requisicoes_disfarcadas
        antiga = L.context._session

        pacote = _ca_bundle_com_repositorio_windows()
        if pacote:
            os.environ["CURL_CA_BUNDLE"] = pacote

        nova = requisicoes_disfarcadas.Session(impersonate=PERFIL_DE_DISFARCE)
        # Só os cabeçalhos que são do Instagram, e não do navegador: quem
        # responde por "qual navegador é este" é o perfil do disfarce, e copiar
        # os do instaloader por cima desfaria justamente o que se quer.
        for nome, valor in antiga.headers.items():
            if nome.lower().startswith("x-") or nome.lower() == "referer":
                nova.headers[nome] = valor
        for nome, valor in antiga.cookies.get_dict().items():
            nova.cookies.set(nome, valor, domain=".instagram.com")

        L.context._session = _SessaoComDisfarce(nova, antiga)
        return True
    except Exception as e:
        print(f"[aviso] seguindo sem disfarce no instaloader. {str(e)[:160]}")
        return False


def baixar_story_ytdlp(link, pasta_destino):
    """Baixa um Story pelo yt-dlp, SEM precisar do número interno do perfil.

    DESCOBERTO EM 29/08/2026, e derruba uma restrição inteira do programa.

    Até aqui, Story só era baixado pelo instaloader, que exige o número
    interno do perfil. Descobrir esse número passa por um endereço que o
    Instagram limita com muito rigor (deu 429 com 3 chamadas numa conta nova),
    e por isso existia todo o contorno de "baixar um Reel primeiro para
    aprender o número" e a lista de perfis com número guardado.

    O extrator de Story do yt-dlp não usa esse endereço: ele lê o número
    interno da PRÓPRIA PÁGINA do Story. Confirmado em 29/08/2026 com dois
    perfis, um deles (@juremafox) sem número guardado e sem Reel baixado
    antes: as duas stories apareceram normalmente.

    SUTILEZA IMPORTANTE: o yt-dlp devolve TODAS as stories atuais do perfil,
    não só a do endereço pedido, porque por dentro ele busca a lista inteira
    pelo número do perfil. Como aqui uma linha da planilha corresponde a um
    vídeo, filtramos pela que foi pedida. O endereço traz o número da mídia e
    as entradas trazem o código curto, que são a mesma coisa em duas
    representações; o instaloader converte uma na outra."""
    import yt_dlp
    from instaloader.structures import Post

    m = _REGEX_STORY.search(link)
    mediaid = m.group("mediaid") if m else None

    # ENDEREÇO SEM O NÚMERO DA MÍDIA (achado do auditor em 29/08/2026).
    #
    # O Instagram só acrescenta o número ao endereço quando a pessoa NAVEGA
    # entre os stories do perfil. Quem tem um story só nunca consegue navegar,
    # e o endereço fica em instagram.com/stories/perfil/ e pronto. Exigir o
    # número deixaria justamente esse caso de fora.
    #
    # Sem o número, olhamos primeiro o que existe, sem baixar:
    #   um story só  -> não há ambiguidade nenhuma, é esse mesmo
    #   vários       -> aí sim é preciso dizer qual, senão o programa
    #                   escolheria por conta própria qual peça auditar
    procurado = Post.mediaid_to_shortcode(int(mediaid)) if mediaid else None

    opcoes = {
        "outtmpl": os.path.join(pasta_destino, "%(id)s.%(ext)s"),
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        # Story nunca funciona sem sessão. Sem cookies nem tenta, para não
        # gastar uma chamada à toa e não sujar o contador.
        **_opcoes_cookies(),
        **opcoes_de_disfarce(),
    }
    if "cookiefile" not in opcoes and "cookiesfrombrowser" not in opcoes:
        raise RuntimeError("Story exige sessão do Instagram, e não há cookies configurados.")

    # O FREIO VALE AQUI TAMBÉM.
    #
    # Este caminho é novo (29/08/2026) e por um instante ficou sem as três
    # proteções que o caminho antigo já tinha, o que é exatamente o tipo de
    # buraco silencioso que marcou duas contas em agosto: o programa passaria
    # por cima de uma pausa ativa, não contaria a chamada no teto do dia, e
    # não recuaria ao levar bloqueio.
    pode, motivo, _usados, _restantes = situacao_da_conta()
    if not pode:
        raise RuntimeError(motivo)

    # Conta antes de falar, não depois: o que o Instagram vê é a chamada, e ela
    # acontece mesmo quando o vídeo não vem.
    _contar_uso_instagram()

    # UMA CONVERSA SÓ COM O INSTAGRAM (corrigido em 29/08/2026).
    #
    # A primeira versão disto perguntava duas vezes quando o endereço vinha sem
    # o número: uma para descobrir quantos stories existiam, outra para baixar.
    # Eram 4 chamadas onde bastam 2, e chamada a mais é justamente o fator que
    # pausa nenhuma resolve. Agora extrai uma vez sem baixar, escolhe, e baixa
    # a escolhida a partir do que já veio, sem falar com o Instagram de novo.
    tentativas = [opcoes]
    if opcoes.get("impersonate") is not None:
        # Segunda tentativa sem o disfarce, para a rede que o recusa. Isso NÃO
        # é uma segunda chamada ao Instagram quando a primeira falha por
        # certificado: ali a conexão nem sai da rede da empresa.
        tentativas.append({k: v for k, v in opcoes.items() if k != "impersonate"})

    for numero, tentativa in enumerate(tentativas, 1):
        try:
            return _extrair_e_baixar_story(link, tentativa, procurado)
        except Exception as e:
            # Recusa do Instagram e erro de uso já chegam aqui como RuntimeError,
            # tratados lá dentro. Só o problema de certificado merece segunda
            # tentativa, e nesse caso a chamada nem chegou ao Instagram.
            if (not isinstance(e, RuntimeError)
                    and e_problema_de_certificado(e)
                    and numero < len(tentativas)):
                desligar_disfarce(e)
                continue
            raise


def _extrair_e_baixar_story(link, opcoes, procurado):
    """Uma conversa só com o Instagram: extrai a lista, escolhe, e baixa a
    escolhida a partir do que já veio."""
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(link, download=False)

            entradas = [e for e in (info.get("entries") or [info]) if e]
            if not entradas:
                raise RuntimeError(
                    "Esse perfil não tem story no ar agora. Story dura 24 horas.")

            if procurado:
                escolhida = next((e for e in entradas if e.get("id") == procurado), None)
                if escolhida is None:
                    raise RuntimeError(
                        f"O perfil tem {len(entradas)} story(ies) no ar, mas nenhuma é "
                        "a do endereço pedido. Story dura 24 horas: provavelmente esta "
                        "já saiu.")
            elif len(entradas) == 1:
                escolhida = entradas[0]
            else:
                raise RuntimeError(
                    f"Esse perfil tem {len(entradas)} stories no ar, e o endereço não "
                    "diz qual é o que deve ser conferido. Abra o story no navegador, "
                    "passe para o próximo e volte: o Instagram acrescenta o número ao "
                    "endereço, e aí ele fica no formato "
                    "instagram.com/stories/perfil/1234567890/. Cole esse.")

            baixada = ydl.process_ie_result(dict(escolhida), download=True)
    except RuntimeError:
        raise
    except Exception as e:
        # Perfil sem story vem antes do freio: o yt-dlp relata isso com uma
        # mensagem que PARECE falta de login, e tratar como bloqueio pausava a
        # conta por horas à toa (ver SEM_STORY_NO_AR).
        if e_perfil_sem_story(e):
            raise RuntimeError(
                "Esse perfil não tem story no ar agora. Story dura 24 horas, então "
                "ou já saiu, ou nunca houve. A conta NÃO foi bloqueada e nada "
                "precisa ser feito."
            ) from e
        if parece_bloqueio(e):
            raise RuntimeError(mensagem_de_recuo(e, _acionar_freio(e))) from e
        raise

    escolhida = baixada or escolhida
    caminho = ydl.prepare_filename(escolhida)
    if not os.path.exists(caminho):
        raise RuntimeError("Nenhum arquivo gerado para essa story.")

    # A HORA VEM DO `timestamp`, E A ORDEM MUDOU POR ISSO (11/09/2026).
    #
    # Antes o `upload_date` era tentado primeiro, e ele é só data (formato
    # AAAAMMDD), sem hora nenhuma. Com ele resolvendo, o `timestamp`, que tem
    # a hora, nunca era olhado. Agora o timestamp vem primeiro, e o
    # upload_date fica como reserva para quando ele não vier.
    #
    # E `fromtimestamp` SEM fuso usa o fuso da máquina, que muda de computador
    # para computador. Com timezone.utc o resultado é o mesmo em qualquer
    # máquina, e a conversão para Brasília fica explícita.
    data = None
    quando = None
    if escolhida.get("timestamp"):
        try:
            quando = hora_de_brasilia(
                datetime.fromtimestamp(int(escolhida["timestamp"]),
                                       tz=timezone.utc))
            data = quando.date()
        except (ValueError, OSError):
            quando = None
    if data is None and escolhida.get("upload_date"):
        try:
            # Só data, e é honesto: este formato não carrega hora.
            data = datetime.strptime(escolhida["upload_date"], "%Y%m%d").date()
        except ValueError:
            pass
    return caminho, data, handle_dos_dados_do_video(escolhida), quando


def baixar_video(link, pasta_destino, link_post_do_perfil=None):
    """Baixa o vídeo do link.

    Devolve (caminho, data, handle, hora_post). `caminho` é um texto, ou uma
    LISTA quando o post é carrossel.

    A HORA ENTROU EM 11/09/2026 como quarto item, e `data` continua sendo
    `date` de propósito: `inferir_ciclo` compara `dmin <= data <= dmax` contra
    datas vindas da Monitoramento, e comparar datetime com date levanta erro em
    Python. Então a data continua data, e a hora viaja ao lado. Ela é None
    quando a origem não informa hora (é o caso do `upload_date` do yt-dlp, que
    é só data).

    Story do Instagram: tenta primeiro pelo yt-dlp, que não precisa do número
    interno do perfil (ver baixar_story_ytdlp, e o porquê disso importar). Só
    cai no instaloader se aquele caminho falhar, e aí sim volta a valer a
    exigência do número.

    Para o resto: tenta anônimo primeiro (não usa conta nenhuma, serve pra
    maioria do YouTube/TikTok/X e até parte do Instagram público); se falhar e
    houver cookies configurados, tenta de novo autenticado."""
    if _REGEX_STORY.search(link):
        try:
            return baixar_story_ytdlp(link, pasta_destino)
        except Exception as e:
            # Bloqueio não é motivo para tentar o outro caminho: seria uma
            # segunda chamada logo depois de o Instagram ter dito não, que é
            # exatamente o comportamento que marca conta.
            if parece_bloqueio(e):
                raise
            return baixar_story_instaloader(link, pasta_destino, link_post_do_perfil)

    import yt_dlp

    opcoes_base = {
        "outtmpl": os.path.join(pasta_destino, "%(id)s.%(ext)s"),
        # MELHOR QUALIDADE DISPONÍVEL (30/08/2026). Estava em "worst" desde a
        # fase de teste, quando o que importava era ir rápido.
        #
        # O que a medição mostrou, e vale registrar porque contraria o que eu
        # esperava: no Instagram isso não mudava nada. Os 54 vídeos já baixados
        # pelo caminho do servidor com "worst" têm a mesma resolução dos que
        # vieram pelo baixador local, que usa o padrão: 720x1280 nos dois. O
        # Instagram entrega um formato só, então lá "worst" e "best" são a
        # mesma coisa.
        #
        # A troca vale mesmo assim, porque a seção 1 aceita qualquer endereço,
        # e em YouTube e TikTok há vários formatos: ali "worst" traria a pior
        # resolução de verdade. E resolução baixa custa leitura: o mesmo vídeo
        # reduzido a 360p perdeu o único aviso que o OCR conseguia ler a
        # 720x1280.
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        # Aparecer como navegador vale para todo download, não só para Story
        # (ver opcoes_de_disfarce, 29/08/2026).
        **opcoes_de_disfarce(),
    }

    def _tentar(opcoes):
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(link, download=True)
            caminho = ydl.prepare_filename(info)
            if not os.path.exists(caminho):
                # Story/vídeo que já saiu do ar (ex: Story expirado depois de
                # 24h) não dá erro no yt-dlp, só devolve uma "playlist vazia" —
                # sem essa checagem, isso passaria como sucesso sem arquivo.
                raise RuntimeError("Nenhum arquivo gerado — conteúdo pode ter expirado ou saído do ar")
            # MESMA ORDEM DO CAMINHO DE STORY (11/09/2026): o timestamp vem
            # primeiro porque carrega a HORA, e o upload_date é só data. Ver
            # hora_de_brasilia.
            data = None
            quando = None
            if info.get("timestamp"):
                try:
                    quando = hora_de_brasilia(
                        datetime.fromtimestamp(int(info["timestamp"]),
                                               tz=timezone.utc))
                    data = quando.date()
                except (ValueError, OSError):
                    quando = None
            if data is None and info.get("upload_date"):
                try:
                    data = datetime.strptime(info["upload_date"], "%Y%m%d").date()
                except ValueError:
                    pass
            # O @ vem junto com o vídeo. É o que faz os endereços curtos do
            # Instagram (instagram.com/reel/CODIGO), que não trazem o @ no
            # texto, dispensarem a digitação à mão.
            return caminho, data, handle_dos_dados_do_video(info), quando

    try:
        return _tentar(opcoes_base)
    except Exception as falha_anonima:
        opcoes_cookies = _opcoes_cookies()
        ultima = falha_anonima
        if opcoes_cookies:
            # O FREIO PASSA A VALER PARA REEL E POST DE FEED (07/09/2026).
            #
            # A tentativa abaixo usa os cookies da conta, ou seja, é o Instagram
            # conversando com a pessoa logada. Ela não passava por nenhuma das
            # três proteções: ignorava pausa ativa, não entrava no teto do dia e
            # o programa seguia achando que tinha budget de sobra.
            #
            # É o MESMO buraco que foi tapado no caminho do Story em 29/08/2026,
            # e o comentário de lá descreve exatamente isto. A correção não
            # chegou aqui na época porque o Story tinha função própria e o Reel
            # e o post de feed dividem esta, junto com YouTube, TikTok e X.
            #
            # POR QUE IMPORTA MAIS AGORA: quem vai usar o programa todo dia é o
            # Marketing, com a conta deles. Contador que subestima o uso é como
            # se marca uma conta, e foi assim em 25/08 e 27/08.
            #
            # SÓ PARA O INSTAGRAM. O teto é da conta do Instagram: contar um
            # download de YouTube ali gastaria budget que não é dele e faria o
            # programa parar de baixar do Instagram sem motivo.
            #
            # A TENTATIVA ANÔNIMA ACIMA CONTINUA DE GRAÇA, e está certo: ela não
            # manda cookie nenhum, então não é a conta que está falando.
            if "instagram.com" in str(link or "").lower():
                pode, motivo, _usados, _restantes = situacao_da_conta()
                if not pode:
                    # Recusar aqui é o mesmo que baixar_post_instaloader faria
                    # logo adiante, e evita a chamada extra. A mensagem que
                    # importa é a da conta, não a da falha anônima.
                    raise RuntimeError(motivo) from falha_anonima
                # Conta antes de falar, pelo motivo registrado em
                # baixar_story_ytdlp: o que o Instagram vê é a chamada, e ela
                # acontece mesmo quando o vídeo não vem. Contar a mais deixa o
                # programa mais cauteloso; contar a menos é o que marca conta.
                _contar_uso_instagram()
            try:
                return _tentar({**opcoes_base, **opcoes_cookies})
            except Exception as falha_autenticada:
                ultima = falha_autenticada

        # POST DE FOTO: O yt-dlp NÃO DEVOLVE (medido em 02/09/2026).
        #
        # O auditor testou e trouxe o erro exato, com um post de carrossel:
        #
        #     ERROR: [Instagram] DcT0RkaCHbc: No video formats found!
        #
        # Ele é um extrator de VÍDEO: post que não tem vídeo nenhum não tem
        # formato para ele achar. E o mesmo teste dele mostrou que story de foto
        # funciona, porque story tem caminho próprio pelo instaloader.
        #
        # Então post de feed passa a ter o mesmo recuo: o instaloader baixa pelo
        # CÓDIGO do post, que está no próprio endereço, sem precisar do número
        # interno do perfil. Isso importa porque o número do perfil é a consulta
        # que o Instagram limita com mais rigor.
        #
        # O recuo NÃO acontece em caso de bloqueio, pela mesma razão registrada
        # no caminho do story: seria uma segunda chamada logo depois de o
        # Instagram ter dito não, que é o comportamento que marca conta.
        if _REGEX_CODIGO_DO_POST.search(link) and not parece_bloqueio(ultima):
            return baixar_post_instaloader(link, pasta_destino)
        raise ultima


def registrar_no_calendario(handle, marca, data_video, hora_post, jogo, quem):
    """Preenche a linha do Calendário de Divulgações do Marketing.

    SEGUNDO DESTINO, E NÃO O PRINCIPAL (11/09/2026). A evidência da auditoria
    é a Monitoramento, e ela é gravada antes desta chamada. O Calendário é
    conveniência para o Marketing, então falhar aqui AVISA E SEGUE: vídeo
    baixado e organizado não pode virar falha porque a planilha de outra área
    estava fora do ar. É a mesma postura já usada no registro de fechamentos.

    Devolve (gravou, motivo)."""
    import calendario_divulgacoes as cal
    if not data_video:
        return False, "Sem a data do post não dá para achar a linha."
    aba = cal.aba_do_mes(data_video)
    try:
        linhas = cal.ler_aba(aba)
    except Exception as e:
        return False, f"não consegui ler o Calendário: {e}"

    numero, motivo = cal.achar_linha(linhas, handle, marca, data_video)
    if numero is None:
        return False, motivo

    # O NOME SÓ VAI SE JÁ EXISTIR NAQUELA COLUNA. Com login, quem_sou_eu
    # devolve e-mail, e a coluna deles é de apelidos (Responsável F, Responsável A, Responsável G,
    # Responsável E). Vazio é melhor do que sujar a coluna com um valor que ninguém
    # usa, e a planilha deles é a fonte do vocabulário.
    monitorado = ""
    if str(quem or "").strip().lower() in cal.apelidos_conhecidos(linhas):
        monitorado = str(quem).strip()

    return cal.escrever(aba, numero, {
        # SEMPRE MAIÚSCULA (15/09/2026), mesmo motivo de adicionar_na_fila:
        # a coluna Jogo do Calendário deles só tem valor em caixa alta.
        "jogo": str(jogo or "").strip().upper(),
        "status": cal.STATUS_PUBLICADA,
        "horario": hora_post.strftime("%H:%M") if hora_post else "",
        "monitorado": monitorado,
    })


def marcar_nao_postou(handle, marca, data, quem):
    """Marca no Calendário que o influenciador não postou no dia combinado.

    Desenho do auditor em 11/09/2026: "caso não tenha sido publicada, deve ter
    um espaço no programa apenas para colocar o handle do influencer e marcar
    como não publicado (pq ai nao vai baixar nada pq a pessoa não postou)".

    NÃO FALA COM O INSTAGRAM, de propósito: não existe vídeo para baixar, e
    chamada é o recurso escasso do programa (teto de 20 por dia por conta).

    Devolve (gravou, motivo)."""
    import calendario_divulgacoes as cal
    if not data:
        return False, "Sem a data não dá para achar a linha."
    aba = cal.aba_do_mes(data)
    try:
        linhas = cal.ler_aba(aba)
    except Exception as e:
        return False, f"não consegui ler o Calendário: {e}"
    numero, motivo = cal.achar_linha(linhas, handle, marca, data)
    if numero is None:
        return False, motivo
    monitorado = ""
    if str(quem or "").strip().lower() in cal.apelidos_conhecidos(linhas):
        monitorado = str(quem).strip()
    return cal.escrever(aba, numero, {
        "status": cal.STATUS_NAO_POSTADA,
        "monitorado": monitorado,
    })


def processar_fila(log_fn=print, analisar_depois=True):
    """Estágio A. Devolve a lista de registros de log (também gravada em CSV).

    Links do Instagram são limitados por RODADA (LIMITE_INSTAGRAM_POR_RODADA) e
    espaçados no tempo (PAUSA_INSTAGRAM_*), pra não bater vários seguidos sem
    pausa — foi assim que um teste real esbarrou em rate limit (HTTP 429) na
    conta usada. Links de outras plataformas seguem sem essa limitação.

    DESDE 01/09/2026 AS RODADAS SE REPETEM SOZINHAS até a fila esvaziar, com uma
    pausa MAIOR entre elas (PAUSA_ENTRE_RODADAS_*). Antes o programa parava no
    limite da rodada e esperava um novo clique, o que o auditor encontrou ao
    mandar 4 links e ter um sobrando.

    A repetição para quando: a fila esvaziou; nada foi processado na rodada
    (fila que não anda não se repete); o teto do dia acabou ou a conta entrou em
    pausa; ou o número de rodadas seguidas bateu em MAXIMO_RODADAS_SEGUIDAS, que
    é rede de segurança. Em todos esses casos o programa DIZ por que parou.

    analisar_depois: manda para a fila de análise, sozinho, o que baixou. É o
    padrão desde 31/08/2026, a pedido do auditor. Ver enfileirar_analise para o
    porquê de isso ser mais que economia de clique.

    Atenção a uma consequência de a análise ser enfileirada no FIM: com rodadas
    encadeadas, o material da primeira rodada só entra na análise quando todas
    terminarem. Enfileirar por arquivo está registrado como frente no
    PROMPT_CONTINUACAO, e é o que resolve isso."""
    import random
    import tempfile
    import time
    import sheets_client
    planilha_id = _planilha_fila_id()
    log = []
    rodada = 0

    # AS RODADAS SE REPETEM SOZINHAS ATÉ A FILA ESVAZIAR (01/09/2026).
    #
    # Antes o programa processava o limite da rodada, deixava o resto e esperava
    # um novo clique. O limite existe para controlar rajada, e continua; o que
    # não precisava era pedir clique. Ver PAUSA_ENTRE_RODADAS_* para o cuidado
    # que faz essa mudança não piorar o padrão de chamada.
    while True:
        rodada += 1
        fila = ler_fila()
        # Reels/posts que já estão na fila servem pra descobrir o número interno
        # do perfil de quem tem Story ali também, sem usar o endereço limitado.
        posts_por_handle = mapa_de_posts_por_handle([x["link"] for x in fila])
        pode_agora, _motivo, _u, _r = situacao_da_conta()

        # QUEM ENTRA NESTA RODADA, DECIDIDO ANTES DE COMEÇAR (01/09/2026).
        #
        # Isto era feito dentro do laço de processamento, e por isso o programa
        # não sabia se ainda havia próximo link do Instagram. A consequência era
        # a pausa acontecer DEPOIS DO ÚLTIMO LINK, à toa: medido em 31/08 com um
        # link só na fila, o programa esperou 125 segundos por um próximo que
        # não existia, e a análise, que só é enfileirada no fim, atrasou esse
        # tempo inteiro sem motivo.
        #
        # A ordem original da fila é preservada de propósito: separar os links do
        # Instagram dos outros mudaria a ordem em que as linhas são atendidas, e
        # quem colocou primeiro espera ser atendido primeiro.
        vao_agora = []
        deixados_para_depois = 0
        # SEPARADO DE `deixados_para_depois` EM 11/09/2026, e a diferença entre
        # os dois é o que decide o tamanho da pausa no fim da rodada. Sobrar
        # fila por ter batido o limite de rajada é uma coisa; sobrar fila porque
        # alguém colou um link novo enquanto o primeiro baixava é outra. Ver a
        # escolha da pausa no fim desta função.
        barrados_pelo_limite = 0
        quantos_do_instagram = 0
        for item in fila:
            # Só processa linha ainda sem status (nunca tentada). Uma vez que
            # falhou ou deu certo, fica parada até alguém apagar o status da
            # linha na planilha pra pedir uma nova tentativa de propósito.
            #
            # Exceção: linha que parou porque a CONTA estava em pausa não é culpa
            # do link. Quando a pausa vence, ela volta sozinha, senão a pausa de
            # 24h viraria uma reprovação permanente e alguém teria que reabrir
            # cada linha na mão sem motivo.
            espera_conta = item["status"].startswith(AVISO_CONTA_PAUSADA)
            if not item["link"]:
                continue
            if item["status"] and not (espera_conta and pode_agora):
                continue
            if "instagram.com" in item["link"]:
                if quantos_do_instagram >= LIMITE_INSTAGRAM_POR_RODADA:
                    deixados_para_depois += 1
                    barrados_pelo_limite += 1
                    continue
                quantos_do_instagram += 1
            vao_agora.append((item, espera_conta))

        if not vao_agora:
            # NADA A FAZER TAMBÉM É RESULTADO, E TEM QUE SER DITO (02/09/2026).
            #
            # O auditor clicou em baixar três vezes e a tela respondeu "0 de 0
            # baixados e organizados" em verde, com "sem registro" dentro de
            # "Ver o que aconteceu". Ele achou que era defeito do programa, e
            # chegou a supor que fosse o Instagram aberto em mais de uma tela.
            # Não era nada disso: a fila não tinha nenhuma linha pendente, e o
            # trabalhador saía daqui sem escrever uma única mensagem.
            #
            # Silêncio no lugar de "não havia o que fazer" é pior que erro: erro
            # a pessoa investiga, silêncio ela interpreta. Só na primeira rodada,
            # porque da segunda em diante a fila esvaziar é o fim normal e já
            # tem mensagem própria.
            if rodada == 1:
                if not fila:
                    log_fn("Nada para baixar: a fila está vazia.")
                elif deixados_para_depois:
                    log_fn(f"Nada para baixar agora: {deixados_para_depois} link(s) "
                           f"do Instagram esperando a vez na próxima rodada.")
                else:
                    log_fn(f"Nada para baixar: as {len(fila)} linha(s) da fila já "
                           f"têm status, então nenhuma estava esperando. Para "
                           f"refazer alguma, apague o status dela na planilha da "
                           f"fila.")
            break

        if rodada > 1:
            log_fn(f"[Rodada {rodada}] {len(vao_agora)} link(s) desta vez"
                   + (f", {deixados_para_depois} ainda esperando" if deixados_para_depois else ""))

        processados_instagram = 0
        for posicao, (item, espera_conta) in enumerate(vao_agora):
            if espera_conta and pode_agora:
                log_fn(f"   (a conta voltou; retomando a linha {item['numero_linha']} sozinha)")
            eh_instagram = "instagram.com" in item["link"]
            n = item["numero_linha"]
            log_fn(f"[Fila linha {n}] {item['influenciador']} | {item['link']}")
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            m_story = _REGEX_STORY.search(item["link"])
            post_do_perfil = posts_por_handle.get(m_story.group("handle").lower()) if m_story else None
            # DE ONDE SAI O @ QUE VIRA NOME DE PASTA, em ordem de preferência:
            #
            #   1. do endereço, quando ele traz (story, /perfil/reel/CODIGO)
            #   2. dos dados que vêm junto com o vídeo (30/08/2026)
            #   3. do que foi digitado na planilha
            #
            # O digitado é o último de propósito: erro de digitação espalha o mesmo
            # influenciador por várias pastas no Drive, e o programa não tem como
            # perceber. O passo 2 é o que deixou de exigir digitação nos endereços
            # curtos do Instagram, que são o que o botão "copiar link" gera.
            handle_do_endereco = handle_do_link(item["link"])
            handle_pasta = handle_do_endereco or item["influenciador"]
            if handle_do_endereco and handle_do_endereco != item["influenciador"]:
                log_fn(f"   (organizando como @{handle_do_endereco}, que é o @ do próprio link)")
            ciclo_manual = normalizar_ciclo(item.get("ciclo"))
            # DE ONDE VEIO O CICLO, registrado (01/09/2026).
            #
            # Ciclo informado por uma pessoa é escolha; ciclo tirado da data é
            # cálculo. As duas coisas produzem o mesmo valor na planilha, e até
            # aqui não havia como saber qual foi. Ver CAMPOS_LOG.
            origem_do_ciclo = "digitado" if ciclo_manual else "pela data do vídeo"
            if ciclo_manual:
                log_fn(f"   (usando o {ciclo_manual} informado à mão, e não o da data "
                       f"do vídeo; fica registrado assim)")

            # BARRAR ANTES DE BAIXAR, e não depois (30/08/2026).
            #
            # A chamada ao Instagram é o recurso escasso: é ela que marca conta, e
            # o teto do dia conta chamada, não vídeo. Descobrir só depois do
            # download que faltava a bet gastaria uma chamada para jogar o arquivo
            # fora. Nem tudo dá para conferir antes, porque a pasta do mês depende
            # da data do post e a do influenciador depende do @, e os dois só
            # chegam com o vídeo. Mas a bet vem da própria linha, então essa dá.
            if LAYOUT_PASTAS == LAYOUT_MARKETING:
                try:
                    exigir_bet(item.get("marca"))
                except BetNaoInformada as e:
                    log_fn(f"   -> {e}")
                    sheets_client.escrever_lote(planilha_id, ABA_FILA, "C",
                                                [(n, f"FALTA A BET: {str(e)[:200]}")])
                    log.append(dict(quando=agora, estagio="A", origem=item["link"],
                                    handle=item["influenciador"], data_video="", ciclo="",
                                    destino="", status="FALTA A BET"))
                    continue

            try:
                with tempfile.TemporaryDirectory() as tmp:
                    baixado, data_video, handle_do_video, hora_post = baixar_video(
                        item["link"], tmp, post_do_perfil)
                    # UM LINK PODE TRAZER VÁRIOS ARQUIVOS (02/09/2026).
                    #
                    # Post de carrossel tem várias imagens, e cada uma é uma tela
                    # que precisa carregar os avisos por conta própria. Baixar só
                    # a primeira deixaria as outras sem auditoria, sem nada
                    # avisar, que é o pior resultado possível aqui.
                    #
                    # A conferência é por tipo e não por "tem len()": texto tem
                    # len() e seria percorrido letra por letra, criando uma linha
                    # na Monitoramento para cada caractere do caminho.
                    caminhos = ([baixado] if isinstance(baixado, str)
                                else list(baixado))
                    if not handle_do_endereco and handle_do_video:
                        handle_pasta = handle_do_video
                        if handle_do_video != item["influenciador"]:
                            log_fn(f"   (organizando como @{handle_do_video}, que veio junto "
                                   f"com o vídeo)")
                    if not str(handle_pasta or "").strip():
                        # Sem @ nenhum, parar aqui é melhor que seguir: seguir
                        # criaria uma pasta sem dono no Drive do Marketing, e
                        # descobrir depois de qual influenciador é cada vídeo lá
                        # dentro dá muito mais trabalho do que refazer a linha.
                        raise RuntimeError(
                            "Não foi possível descobrir de quem é esse vídeo. O endereço não "
                            "traz o @, os dados do vídeo também não, e a coluna do "
                            "influenciador está vazia. Preencha o @ na linha e apague o "
                            "status para tentar de novo.")
                    if len(caminhos) > 1:
                        log_fn(f"   (este post tem {len(caminhos)} imagens, e cada "
                               f"uma vira uma tela com linha própria: cada tela "
                               f"precisa carregar os avisos por conta própria)")
                    link_drive = ciclo = None
                    for indice, caminho in enumerate(caminhos, start=1):
                        if len(caminhos) > 1:
                            log_fn(f"   [imagem {indice} de {len(caminhos)}]")
                        link_drive, ciclo = enviar_para_drive(
                            caminho, handle_pasta, data_video, ciclo_manual,
                            marca=item.get("marca") or None,
                            link_original=item["link"],
                            # Escolhido na tela, no mesmo clique do link. Decide
                            # a pasta ACIMA da do tipo e a coluna MARCACAO.
                            marcacao=marcacao_de_celula(item.get("marcacao")),
                            # Quem colou o link, que vai para a coluna PEDIDO_POR.
                            # Vem da LINHA da fila e não da tarefa, porque uma
                            # tarefa processa links de pessoas diferentes.
                            pedido_por=item.get("quem_pediu"),
                            # sem isto, tudo que o envio tem a dizer (linha criada
                            # na Monitoramento, peça repetida, falha ao registrar)
                            # some sem aparecer na tela
                            log_fn=log_fn)
                        # SEM O LINK AQUI, DE PROPÓSITO (15/09/2026): esta
                        # mensagem aparece crua na tela de acompanhamento (ver
                        # pages/1_Downloads_e_Organizacao.py), e o auditor
                        # pediu para não ter link nenhum ali, clicável ou não.
                        # O endereço de verdade continua indo para a
                        # Monitoramento, no campo "destino" do log estruturado
                        # logo abaixo, que é onde ele tem função.
                        log_fn("   -> subiu pro Drive de teste.")
                        # UMA ENTRADA DE LOG POR ARQUIVO, e não por link. É dela
                        # que sai a fila de análise, então uma só faria as outras
                        # imagens do carrossel subirem e nunca serem analisadas.
                        log.append(dict(
                            quando=agora, estagio="A", origem=item["link"],
                            handle=handle_pasta,
                            data_video=str(data_video or ""), ciclo=ciclo,
                            destino=link_drive, status="OK",
                            origem_ciclo=origem_do_ciclo,
                            quem=item.get("quem_pediu") or ""))
                # O CALENDÁRIO DE DIVULGAÇÕES É O SEGUNDO DESTINO (11/09/2026),
                # e vem DEPOIS da Monitoramento de propósito: a Monitoramento é
                # a evidência da auditoria, o Calendário é conveniência para o
                # Marketing. Falhar aqui avisa e segue. Ver
                # registrar_no_calendario e DESENHO_CALENDARIO.md.
                gravou_cal, motivo_cal = registrar_no_calendario(
                    handle=handle_pasta,
                    marca=item.get("marca"),
                    data_video=data_video,
                    hora_post=hora_post,
                    jogo=item.get("jogo"),
                    quem=item.get("quem_pediu"))
                if gravou_cal:
                    log_fn(f"   -> Calendário preenchido ({motivo_cal})")
                else:
                    log_fn(f"   -> Calendário não preenchido: {motivo_cal}")
                sheets_client.escrever_lote(planilha_id, ABA_FILA,
                                            letra_da_coluna_fila("status"),
                                            [(n, "BAIXADO E ORGANIZADO")])
                sheets_client.escrever_lote(planilha_id, ABA_FILA,
                                            letra_da_coluna_fila("ciclo"), [(n, ciclo)])
                # O @ DESCOBERTO VOLTA PARA A PLANILHA (31/08/2026).
                #
                # Desde 30/08 o @ é descoberto sozinho no Instagram e quase ninguém
                # digita, então a coluna Influenciador ficava vazia na maioria das
                # linhas: 13 de 18 na conferência que o auditor fez. Lida como se
                # faltasse dado, quando estava tudo certo, e a informação existia,
                # só não era gravada.
                #
                # Escreve só quando difere, para não gastar uma chamada à planilha
                # confirmando o que já está lá.
                if handle_pasta and handle_pasta != item["influenciador"]:
                    sheets_client.escrever_lote(planilha_id, ABA_FILA,
                                                letra_da_coluna_fila("influenciador"),
                                                [(n, handle_pasta)])
                # A entrada de log deste download já foi acrescentada DENTRO do
                # laço dos arquivos, uma por arquivo (02/09/2026). Antes ela
                # ficava aqui, uma por link, e com carrossel isso mandaria para a
                # análise só a última imagem.
            except PastaNaoExisteNoDrive as e:
                # NÃO é defeito da linha nem da conta: falta uma pasta no Drive, e
                # quem cria pasta lá é o Marketing, à mão. O vídeo já foi baixado e
                # se perde aqui junto com a pasta temporária; a chamada ao
                # Instagram, essa não volta. Por isso o aviso diz exatamente qual
                # pasta criar, para a segunda tentativa não falhar pelo mesmo
                # motivo.
                rotulo = f"FALTA PASTA NO DRIVE: {str(e)[:300]}"
                log_fn(f"   -> {rotulo}")
                sheets_client.escrever_lote(planilha_id, ABA_FILA, "C", [(n, rotulo)])
                log.append(dict(quando=agora, estagio="A", origem=item["link"],
                                handle=handle_pasta, data_video="", ciclo="", destino="",
                                status="FALTA PASTA NO DRIVE"))
            except Exception as e:
                msg = str(e)[:160]
                if ("está em pausa até" in str(e) or MARCA_DE_RECUO in str(e)
                        or MARCA_DE_TETO in str(e)):
                    # A linha não tem defeito: a conta é que está de castigo, ou
                    # já gastou o teto do dia. Fica marcada de um jeito que o
                    # programa reconhece e retoma sozinho quando a pausa vencer
                    # ou o contador zerar. O teto entrou nesta condição em
                    # 01/09/2026: sem ele, linha barrada pelo teto virava FALHA
                    # permanente e não voltava no dia seguinte.
                    rotulo = f"{AVISO_CONTA_PAUSADA} — {str(e)[:200]}"
                elif "não tem story no ar" in str(e) or e_perfil_sem_story(e):
                    # Nem defeito da linha nem problema da conta: o perfil não tem
                    # story publicada. Rótulo próprio para quem lê a planilha não
                    # sair procurando defeito onde não há (30/08/2026).
                    rotulo = "SEM STORY NO AR (o perfil não tem story publicada agora)"
                elif "número do perfil" in str(e):
                    # Caso com solução clara: falta descobrir o número do perfil.
                    # Vale a mensagem inteira, senão a orientação se perde.
                    rotulo = str(e)[:300]
                elif any(s in msg.lower() for s in (
                    # "login" saiu daqui em 30/08/2026: ele casava com a mensagem
                    # de perfil sem story, que é tratada acima e não é bloqueio.
                    "cookies", "rate-limit", "rate limit", "429",
                    "too many requests", "not available", "empty media",
                    "unreachable",
                )):
                    rotulo = "BAIXAR MANUALMENTE (Instagram bloqueou ou exige login)"
                else:
                    # A FALHA GENÉRICA PASSA A DIZER QUE EXISTE SAÍDA
                    # (05/09/2026). Antes ela era só "FALHA: <erro técnico>", e
                    # quem lia a planilha ficava sem próximo passo. O caminho
                    # manual já existia e resolvia, mas nada apontava para ele:
                    # o pedido do auditor foi justamente pensar no plano B para
                    # quando a biblioteca de download parar de funcionar.
                    rotulo = f"FALHA, dá para subir o arquivo à mão: {msg}"
                log_fn(f"   -> {rotulo}")
                if rotulo.startswith("FALHA") or "BAIXAR MANUALMENTE" in rotulo:
                    log_fn("      (baixe o vídeo pelo navegador e use o envio "
                           "de arquivo, na tela de Downloads: o programa "
                           "organiza, analisa e registra igual)")
                sheets_client.escrever_lote(planilha_id, ABA_FILA, "C", [(n, rotulo)])
                log.append(dict(quando=agora, estagio="A", origem=item["link"], handle=item["influenciador"],
                                data_video="", ciclo="", destino="", status=rotulo))

            if eh_instagram:
                processados_instagram += 1
                # PAUSA SÓ QUANDO EXISTE PRÓXIMO LINK DO INSTAGRAM NESTA RODADA
                # (corrigido em 01/09/2026).
                #
                # Antes a condição era "ainda não cheguei ao limite da rodada", o
                # que não é a mesma pergunta: com um link só na fila, o programa
                # esperava por um próximo que não existia. Medido em 31/08: 125
                # segundos de espera à toa, e a análise, que só é enfileirada no
                # fim da tarefa, atrasou esse tempo inteiro.
                ha_proximo_do_instagram = any(
                    "instagram.com" in proximo["link"]
                    for proximo, _ in vao_agora[posicao + 1:]
                )
                if ha_proximo_do_instagram:
                    pausa = random.uniform(PAUSA_INSTAGRAM_MIN_SEG, PAUSA_INSTAGRAM_MAX_SEG)
                    log_fn(f"   (pausa de {pausa:.0f}s antes do próximo link do Instagram, de propósito)")
                    time.sleep(pausa)

        # FIM DA RODADA: continua sozinho ou para aqui?
        #
        # RELÊ A FILA ANTES DE DESISTIR (06/09/2026), e isto conserta uma
        # corrida real que o auditor pegou: "coloquei um video para baixar atras
        # do outros, mas o segundo não baixou, ja tinha percebido isso antes, eu
        # achei que ele ficava na fila mas que ele iria ser baixado".
        #
        # A EXPECTATIVA DELE ESTAVA CERTA e o programa prometia isso. O que
        # falhava era a janela entre duas coisas: quem cola um link só cria
        # tarefa de download se ainda NÃO existe uma (ver o comentário em
        # adicionar_na_fila na tela de Downloads, que evita rajada sem pausa).
        # Então, se o link entra enquanto uma tarefa está terminando, ninguém
        # cria tarefa nova E a tarefa em curso já passou da última leitura da
        # fila. O link fica órfão, esperando um clique que a pessoa não sabe
        # que precisa dar.
        #
        # `deixados_para_depois` conta só o que ESTA rodada viu ao ler a fila no
        # começo dela. Perguntar de novo à planilha é uma chamada barata, e é o
        # que fecha a janela: se apareceu linha nova, a rodada seguinte a pega.
        if not deixados_para_depois:
            chegou_no_meio = [x for x in ler_fila() if x["link"] and not x["status"]]
            if not chegou_no_meio:
                break
            log_fn(f"{len(chegou_no_meio)} link(s) entraram na fila enquanto eu "
                   f"trabalhava. Continuo.")
            deixados_para_depois = len(chegou_no_meio)

        # Sem progresso não se repete. Uma fila que não anda repetiria para
        # sempre, e o programa ficaria ocupado sem baixar nada.
        if not processados_instagram:
            log_fn("Nada foi processado nesta rodada, então paro aqui em vez de repetir.")
            break

        if rodada >= MAXIMO_RODADAS_SEGUIDAS:
            log_fn(f"{deixados_para_depois} link(s) ainda na fila, mas já foram "
                   f"{rodada} rodadas seguidas. Paro aqui por segurança; mande de "
                   f"novo para continuar.")
            break

        # O teto do dia e a pausa da conta mandam mais que a fila. Conferir ANTES
        # de esperar evita ficar minutos parado para descobrir depois que a conta
        # não pode falar com o Instagram.
        pode_continuar, motivo_parada, _u, _r = situacao_da_conta()
        if not pode_continuar:
            log_fn(f"{deixados_para_depois} link(s) ficam para depois: {motivo_parada}")
            break

        # QUAL PAUSA, E POR QUÊ (11/09/2026).
        #
        # A pausa MAIOR existe para conter rajada: rodada que bateu o limite de
        # links do Instagram, e a seguinte encadearia outro tanto. Nesse caso a
        # rodada seguinte tem que parecer outra sessão de trabalho.
        #
        # Só que ela estava sendo aplicada também quando não havia rajada
        # nenhuma a conter: a fila acabou, e um único link chegou no meio do
        # trabalho (o caminho de RELÊ A FILA ANTES DE DESISTIR, logo acima).
        # Era o caso real do auditor, com dois stories colados um atrás do
        # outro: o segundo esperava de 3 a 7 minutos, e ele viu 369s na tela.
        #
        # Continuar com a pausa ENTRE LINKS nesse caso produz exatamente o mesmo
        # ritmo de chamada de quem colou os dois links juntos, que é o ritmo já
        # aceito. Não é afrouxar a proteção: é deixar de cobrar pausa de rajada
        # de quem não fez rajada.
        if barrados_pelo_limite:
            espera = random.uniform(PAUSA_ENTRE_RODADAS_MIN_SEG,
                                    PAUSA_ENTRE_RODADAS_MAX_SEG)
            log_fn(f"{deixados_para_depois} link(s) ainda na fila. Pausa maior de "
                   f"{espera:.0f}s antes da próxima rodada, de propósito, para não "
                   f"virar uma rajada só.")
        else:
            espera = random.uniform(PAUSA_INSTAGRAM_MIN_SEG, PAUSA_INSTAGRAM_MAX_SEG)
            log_fn(f"{deixados_para_depois} link(s) ainda na fila. Pausa de "
                   f"{espera:.0f}s antes de continuar, o mesmo intervalo de quem "
                   f"cola os links juntos.")
        time.sleep(espera)

    gravar_log(log)

    if analisar_depois:
        enfileirar_analise(
            [r["destino"] for r in log if r.get("status") == "OK" and r.get("destino")],
            log_fn=log_fn)

    return log


def enfileirar_analise(links_no_drive, log_fn=print, criada_por=None):
    """Manda para a análise as linhas da Monitoramento destes arquivos.

    POR QUE EXISTE (31/08/2026)

    Pedido do auditor: "jogou o link lá, escolhe a marca, e ele baixa e já vai
    pra validação regulatória analisando". Antes era preciso ir na outra tela,
    escolher quais vídeos e mandar.

    O GANHO NÃO É SÓ DE CLIQUE, e é isso que faz valer a pena numa ferramenta
    de auditoria: escolher QUAIS vídeos analisar era discricionariedade que não
    deixava rastro. Quem escolhia podia deixar um de fora sem que nada
    registrasse a escolha. Analisando tudo o que entra, essa escolha deixa de
    existir. Tirar algo da análise continua possível, mas só pelo caminho que
    EXIGE motivo e fica gravado na planilha.

    SÓ AS LINHAS DESTE LOTE, e não tudo o que está pendente. Varrer os
    pendentes pegaria linhas antigas que alguém deixou de lado de propósito, e
    ninguém pediu isso."""
    alvos = {str(l).strip() for l in (links_no_drive or []) if str(l or "").strip()}
    if not alvos:
        return 0

    import fila_trabalho
    import pipeline_influenciadores as pipeline

    # Uma leitura da Monitoramento para o lote inteiro, e não uma por vídeo: a
    # planilha é lida por completo a cada chamada.
    try:
        linhas = pipeline.carregar_monitoramento()
    except Exception as e:
        log_fn(f"[Análise] não consegui ler a Monitoramento para enfileirar: {str(e)[:140]}")
        return 0

    ja_na_fila = fila_trabalho.links_em_andamento()
    por_link = defaultdict(list)
    for linha in linhas:
        if str(linha.get("link") or "").strip() in alvos:
            por_link[linha["link"]].append(linha)

    quantas = 0
    for link, do_link in por_link.items():
        if link in ja_na_fila:
            continue
        if str(do_link[0].get("veredito_na_planilha") or "").strip():
            # Já tem veredito. Acontece quando o vídeo era repetido e o envio
            # devolveu o arquivo que já existia.
            continue
        fila_trabalho.criar(
            fila_trabalho.VALIDAR,
            {"link": link,
             "excel_rows": [l["excel_row"] for l in do_link],
             "linha": do_link[0]},
            rotulo=f"{do_link[0]['influenciador']} · {do_link[0]['data'] or 'sem data'}",
            criada_por=criada_por or "automático (após o download)",
        )
        quantas += 1

    nao_achadas = len(alvos) - len(por_link)
    if quantas:
        log_fn(f"[Análise] {quantas} vídeo(s) já foram para a fila de análise, "
               f"sem precisar de clique.")
    if nao_achadas > 0:
        # Não é defeito: vídeo repetido não gera linha nova, então não há o que
        # analisar. Fica dito para ninguém procurar o que não existe.
        log_fn(f"[Análise] {nao_achadas} não geraram linha nova na Monitoramento "
               f"(vídeo repetido), então não há o que analisar neles.")
    return quantas


# ------------------------------------------------------------------
# Envio pela tela (estágio B moderno) e pasta monitorada (estágio B antigo)
# ------------------------------------------------------------------
def pastas_de_influenciador_no_teste(handle_limpo, profundidade=6):
    """Toda pasta do Drive DE TESTE que tem o nome daquele influenciador,
    onde ela estiver na árvore. Devolve [(caminho_legível, id)].

    POR QUE PROCURAR EM VEZ DE MONTAR O CAMINHO (01/09/2026)

    Antes bastava montar: no layout de teste o caminho era ["@handle"], então
    quem quisesse a pasta dele pedia e pronto. Quando os dois layouts passaram a
    montar bet / ano / mês / @handle, isso deixou de funcionar por dois motivos:
    o caminho passou a exigir bet e data, que quem limpa não tem, e o mesmo
    influenciador passou a ter UMA PASTA POR MÊS.

    O segundo motivo é o que importa e não é detalhe: @maumauzk tinha pasta em
    "08. Agosto" e em "09. Setembro" no mesmo dia de teste, porque os posts eram
    de 31/08 e de 01/09. Limpar só um mês deixaria metade do material para trás,
    e quem refizesse o teste esbarraria na conferência de vídeo repetido sem
    entender por quê."""
    import drive_client_upload
    alvo = chave_de_pasta(handle_limpo)
    achados = []

    def procurar(id_pasta, caminho, resta):
        for pasta in drive_client_upload.listar_arquivos(id_pasta, so_pastas=True):
            novo = caminho + [pasta["name"]]
            if chave_de_pasta(pasta["name"]) == alvo:
                achados.append((" / ".join(novo), pasta["id"]))
            elif resta > 0:
                procurar(pasta["id"], novo, resta - 1)

    procurar(_pasta_raiz_drive(), [], profundidade)
    return achados


def remover_material_de_teste(handles, log_fn=print, limpar_fila=True):
    """Tira do caminho o material de teste de um ou mais influenciadores: manda
    os arquivos e as pastas deles para a LIXEIRA do Drive, apaga as linhas
    correspondentes da Monitoramento de teste e, se pedido, as linhas da fila de
    downloads.

    AS TRÊS PONTAS JUNTAS DE PROPÓSITO, e cada uma tem um motivo:

    Apagar só o vídeo deixaria a linha da planilha apontando pro nada, e no fluxo
    atual ela ficaria como "aguardando validação" para sempre, sujando a contagem
    de pendentes.

    E a FILA entrou em 01/09/2026, porque sem ela a limpeza não serve para o que
    é pedida. Quem limpa quer refazer o teste com os MESMOS links, e
    adicionar_na_fila recusa link que já está lá. O resultado era a tela dizendo
    "esse link já foi baixado" sobre material que não existe mais.

    Nunca apaga de forma permanente: vai para a lixeira, onde o Drive guarda 30
    dias. E só alcança a pasta de TESTE, porque parte da raiz dela.

    NÃO MEXE em duas coisas, de propósito: a contagem de chamadas do Instagram do
    dia, que é a proteção contra conta marcada, e o número interno do perfil
    guardado, cuja redescoberta é a chamada mais cara e mais arriscada do
    programa. Limpar teste não pode custar isso.

    Devolve (arquivos_na_lixeira, linhas_apagadas)."""
    import drive_client_upload
    import sheets_client

    alvos = {str(h).strip().lstrip("@").lower() for h in handles if str(h).strip()}
    if not alvos:
        return 0, 0

    # --- Drive ---
    #
    # MANDA A PASTA DO INFLUENCIADOR PARA A LIXEIRA, E PRONTO. No Drive, o que
    # está dentro de uma pasta na lixeira vai com ela, então não é preciso
    # percorrer nível por nível.
    #
    # A versão anterior percorria dois níveis apagando arquivo por arquivo, e
    # isso passou a MENTIR no número quando a árvore ficou mais funda: os
    # arquivos ficam em "@handle / DD/MM / story", três níveis abaixo, então o
    # laço não os alcançava e o resultado dizia "0 arquivos na lixeira" depois de
    # remover material de verdade. Contar pasta, que é o que realmente foi
    # mandado, não tem esse problema com nenhuma profundidade.
    itens_removidos = 0
    try:
        for handle in sorted(alvos):
            pastas = pastas_de_influenciador_no_teste(handle)
            if not pastas:
                log_fn(f"[Limpeza] @{handle}: não tem pasta no Drive de teste.")
                continue
            for caminho, id_handle in pastas:
                drive_client_upload.mandar_para_lixeira(id_handle)
                itens_removidos += 1
                log_fn(f"[Limpeza] @{handle}: \"{caminho}\" foi pra lixeira do Drive, "
                       f"com tudo o que estava dentro.")
            # Arquivo solto na raiz de teste com o nome do influenciador. Não é o
            # caso normal, mas envio manual já deixou arquivo fora de pasta.
            for arquivo in drive_client_upload.listar_arquivos(_pasta_raiz_drive()):
                if chave_de_pasta(handle) in chave_de_pasta(arquivo.get("name")):
                    drive_client_upload.mandar_para_lixeira(arquivo["id"])
                    itens_removidos += 1
                    log_fn(f"[Limpeza] @{handle}: arquivo solto "
                           f"\"{arquivo.get('name')}\" foi pra lixeira.")
    except Exception as e:
        log_fn(f"[Limpeza] parei no Drive: {str(e)[:160]}")

    # --- Fila de downloads ---
    #
    # Antes da Monitoramento de propósito: se algo falhar no meio, é melhor ter
    # sobrado linha na planilha (que é visível e dá para apagar à mão) do que ter
    # sobrado link na fila, que barra o próximo teste com uma mensagem enganosa.
    if limpar_fila:
        try:
            itens = ler_fila()
            a_apagar = [x["numero_linha"] for x in itens
                        if chave_de_pasta(x["influenciador"]) in alvos
                        or any(f"/{h}/" in (x["link"] or "").lower() for h in alvos)]
            if a_apagar:
                apagadas = sheets_client.apagar_linhas(
                    _planilha_fila_id(), ABA_FILA, a_apagar)
                log_fn(f"[Limpeza] {apagadas} linha(s) apagadas da fila de downloads, "
                       f"para os mesmos links poderem entrar de novo.")
        except Exception as e:
            log_fn(f"[Limpeza] parei na fila: {str(e)[:160]}")

    # --- Monitoramento ---
    linhas_apagadas = 0
    try:
        planilha = _planilha_monitoramento_id()
        if planilha:
            ultima = ULTIMA_COLUNA_MON
            valores = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha,
                range=f"'{ABA_MONITORAMENTO}'!A2:{ultima}20000").execute()).get("values", [])
            i_handle = COL_MON["handle"] - 1
            a_apagar = [
                n for n, linha in enumerate(valores, start=2)
                if len(linha) > i_handle
                and str(linha[i_handle] or "").strip().lstrip("@").lower() in alvos
            ]
            linhas_apagadas = sheets_client.apagar_linhas(planilha, ABA_MONITORAMENTO, a_apagar)
            if linhas_apagadas:
                log_fn(f"[Limpeza] {linhas_apagadas} linha(s) apagadas da Monitoramento de teste.")
    except Exception as e:
        log_fn(f"[Limpeza] parei na planilha: {str(e)[:160]}")

    return itens_removidos, linhas_apagadas


def registrar_link_externo(link, handle, data_video, ciclo, marca, tipo,
                           horas_live=None, quem=None, log_fn=print):
    """Registra na Monitoramento um vídeo que NÃO é baixado, só apontado pelo
    endereço (criado em 28/08/2026 para o YouTube, principalmente lives).

    Motivo de existir: live de YouTube é grande demais pra baixar, e a
    conferência dela continua sendo manual. A linha entra na planilha com o
    endereço do próprio vídeo no lugar onde, num vídeo baixado, iria o link da
    pasta do Drive. Como a proteção contra duplicidade compara justamente essa
    coluna, o mesmo endereço não é registrado duas vezes.

    Influenciador, data, bet e tipo são obrigatórios, ao contrário do envio de
    arquivo: ali o programa deduz influenciador e data pelo nome do arquivo,
    aqui não existe arquivo nenhum de onde tirar isso.

    O CICLO NÃO É MAIS OBRIGATÓRIO (31/08/2026). Ele era, e a justificativa
    escrita aqui era a mesma dos outros campos: "não existe arquivo de onde
    deduzir". Só que o ciclo nunca foi deduzido do arquivo, e sim da DATA do
    post, que esta função já exige. A justificativa valia para o influenciador,
    não para ele.

    O resultado era uma diferença sem motivo: a fila de download descobre o
    ciclo pela data, o envio de arquivo também, e só aqui era preciso digitar.
    Percebido pelo auditor ao notar que o ciclo passou a viver só na planilha,
    porque o Drive do Marketing é organizado por mês.

    Vazio, o ciclo sai de inferir_ciclo. Preenchido, o que foi digitado manda,
    que é o mesmo comportamento das outras duas seções: os ciclos da
    Monitoramento se sobrepõem com frequência, então a descoberta automática
    acerta na maioria mas não sempre.

    HORAS DE LIVE ENTROU EM 04/09/2026. É EXIGIDO só quando `tipo` é LIVE, mas
    é GRAVADO sempre que vier preenchido e válido, seja qual for o tipo
    (corrigido em 16/09/2026: um teste com o tipo YOUTUBE escolhido, em vez de
    LIVE, tinha o valor digitado descartado em silêncio, porque só entrava na
    escrita dentro do `if` do tipo. A pessoa via o campo na tela, digitava, e a
    coluna U saía vazia mesmo assim).

    O CALENDÁRIO DE DIVULGAÇÕES PASSA A SER ATUALIZADO AQUI TAMBÉM (16/09/2026):
    antes esta função nunca chamava registrar_no_calendario, e um link
    registrado nunca marcava Status/Publicada nem "Monitorado por" na
    planilha deles. A coluna HORÁRIO fica de fora de propósito: sem vídeo
    baixado, não tem como o programa descobrir a que horas o post saiu
    sozinho (compare com hora_de_brasilia, usada no download), e pedir para
    digitar isso à mão foi tentado e descartado no mesmo dia, a pedido do
    auditor: essa hora continua sendo preenchida à mão por quem já faz isso
    hoje. `registrar_no_calendario` já sabe pular uma coluna vazia sem
    reclamar (ver `cal.escrever`).

    `quem` é a identidade de quem está registrando, e vai para a coluna
    PEDIDO_POR da Monitoramento e para "Monitorado por" no Calendário. Faltava
    aqui: as outras duas seções (fila de download, envio de arquivo) já
    passam isso, só o link externo ficava de fora.

    Devolve o registro de log, no mesmo formato das outras etapas."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    link = str(link or "").strip()

    def _registrar(**campos):
        registro = dict(quando=agora, estagio="LINK", origem=link, handle="", data_video="",
                        ciclo="", destino="", status="")
        registro.update(campos)
        gravar_log([registro])
        return registro

    faltando = [rotulo for valor, rotulo in (
        (link, "endereço do vídeo"), (handle, "influenciador"), (data_video, "data"),
        (marca, "bet"), (tipo, "tipo do post"),
    ) if not valor]
    # HORAS DE LIVE SÓ É OBRIGATÓRIO PARA O TIPO LIVE. Vídeo do YouTube,
    # gravação/diária, TikTok e X/Twitter não têm duração de transmissão: pedir
    # o campo ali seria exigir um número que não existe.
    horas_live_normalizado = normalizar_horas_live(horas_live)
    if str(tipo or "").strip().upper() == "LIVE":
        if not horas_live:
            faltando.append("horas de live")
        elif not horas_live_normalizado:
            log_fn(f"[Link] horas de live precisa estar no formato HH:MM:SS "
                  f"(ex: 01:30:00); recebi {horas_live!r}.")
            return _registrar(status="FORMATO DE HORAS INVALIDO")
    if faltando:
        log_fn(f"[Link] preencha antes de enviar: {', '.join(faltando)}.")
        return _registrar(status="FALTA PREENCHER")

    if not re.match(r"(?i)^https?://", link):
        log_fn(f"[Link] {link}: não parece um endereço de vídeo (precisa começar com http).")
        return _registrar(status="ENDERECO INVALIDO")

    handle_limpo = str(handle).strip().lstrip("@").lower()
    # Digitado manda; vazio, descobre pela data. Mesma regra das outras seções.
    rotulo_ciclo = normalizar_ciclo(ciclo) or inferir_ciclo(handle_limpo, data_video)
    if not normalizar_ciclo(ciclo):
        log_fn(f"[Link] ciclo descoberto pela data do post: {rotulo_ciclo}.")
    try:
        numero_linha = registrar_na_monitoramento(
            handle_limpo, data_video, rotulo_ciclo, link,
            marca=marca, tipo=tipo, link_original=link,
            # não é arquivo baixado: nada a analisar, fica pra conferência humana
            analisavel=False,
            # GRAVADO SEMPRE QUE VÁLIDO, não só quando tipo é LIVE (16/09/2026,
            # ver docstring). Continua não inventando nada: sem valor digitado
            # ou digitado errado, horas_live_normalizado já é "".
            horas_live=horas_live_normalizado,
            pedido_por=quem)
    except Exception as e:
        log_fn(f"[Link] não consegui registrar na Monitoramento: {str(e)[:160]}")
        return _registrar(handle="@" + handle_limpo, ciclo=rotulo_ciclo, status="ERRO AO REGISTRAR")

    if numero_linha is None:
        log_fn(f"[Link] esse endereço já estava registrado na Monitoramento, nada a fazer.")
        return _registrar(handle="@" + handle_limpo, ciclo=rotulo_ciclo, status="JA REGISTRADO")

    log_fn(f"[Link] registrado na Monitoramento, linha {numero_linha}.")
    # O CALENDÁRIO É O SEGUNDO DESTINO AQUI TAMBÉM (16/09/2026), mesma lógica
    # de registrar_no_calendario no caminho de download: falha ali avisa e
    # segue, nunca desfaz o que já foi gravado na Monitoramento. SEM
    # hora_post DE PROPÓSITO: ver o comentário no topo desta função sobre a
    # coluna HORÁRIO continuar preenchida à mão.
    gravou_cal, motivo_cal = registrar_no_calendario(
        handle=handle_limpo, marca=marca, data_video=data_video,
        hora_post=None, jogo=None, quem=quem)
    if gravou_cal:
        log_fn(f"   -> Calendário preenchido ({motivo_cal})")
    else:
        log_fn(f"   -> Calendário não preenchido: {motivo_cal}")
    return _registrar(handle="@" + handle_limpo,
                      data_video=data_video.strftime("%Y-%m-%d") if data_video else "",
                      ciclo=rotulo_ciclo, destino=f"Monitoramento linha {numero_linha}",
                      status="OK")


PASTA_ENVIOS = os.path.join(PASTA_TESTE, "envios_aguardando")


def guardar_envio(nome_arquivo, dados):
    """Grava um arquivo que a pessoa enviou pela tela, para o trabalhador
    processar depois.

    POR QUE (30/08/2026): o envio rodava dentro da tela, um arquivo por vez.
    Cada um lista o Drive algumas vezes e lê a Monitoramento INTEIRA, então
    com 25 arquivos a tela ficava presa por minutos e a planilha era lida 25
    vezes. Agora a tela só guarda os arquivos e cria uma tarefa; quem trabalha
    é o trabalhador, como em todo o resto do programa.

    Guarda em pasta com carimbo de hora e um número, para dois envios ao mesmo
    tempo não se misturarem nem sobrescreverem arquivo de mesmo nome.

    ISTO É ÁREA DE PASSAGEM NO SERVIDOR, NÃO O DESTINO. O destino continua
    sendo o Drive compartilhado, um só para todas as pessoas, organizado por
    bet, ano, mês e influenciador. Esta pasta existe só porque o servidor é um
    só: se duas pessoas enviarem ao mesmo tempo um arquivo de mesmo nome, um
    apagaria o outro enquanto esperam o trabalhador pegar. Some assim que a
    tarefa termina."""
    import uuid
    pasta = os.path.join(PASTA_ENVIOS,
                         f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome_para_disco(os.path.basename(str(nome_arquivo))))
    with open(caminho, "wb") as f:
        f.write(dados)
    return caminho


def processar_arquivo_no_disco(caminho_arquivo, nome_original=None, handle_manual=None,
                               data_manual=None, ciclo_manual=None, marca=None,
                               tipo=None, log_fn=print, tela=None,
                               marcacao=None, pedido_por=None):
    """Mesma coisa que processar_arquivo_enviado, mas o arquivo já está em
    disco. É o que o trabalhador usa.

    `nome_original` existe porque o nome em disco pode ter sido ajustado para
    o Windows aceitar (a barra do padrão do Marketing vira hífen), e é do nome
    ORIGINAL que se descobre o influenciador e a data."""
    with open(caminho_arquivo, "rb") as f:
        dados = f.read()
    return processar_arquivo_enviado(
        nome_original or os.path.basename(caminho_arquivo), dados,
        handle_manual=handle_manual, data_manual=data_manual,
        ciclo_manual=ciclo_manual, marca=marca, tipo=tipo, log_fn=log_fn, tela=tela,
        marcacao=marcacao, pedido_por=pedido_por)


def processar_arquivo_enviado(nome_arquivo, dados, handle_manual=None, data_manual=None,
                              ciclo_manual=None, marca=None, tipo=None, log_fn=print,
                              tela=None, marcacao=None, pedido_por=None):
    """Recebe um vídeo que a pessoa enviou pela própria tela do app (nome
    original + conteúdo), descobre o ciclo e organiza no Drive, igual ao que a
    pasta monitorada faz.

    É o caminho pensado pro Story que a pessoa baixou no navegador dela (já
    estava logada assistindo), e é o único que funciona com o programa num
    servidor, onde não existe pasta de Downloads compartilhada entre as
    máquinas de cada pessoa.

    O influenciador, a data e o ciclo digitados na tela têm prioridade; se
    vierem vazios, o programa tenta descobrir (influenciador e data pelo nome
    do arquivo, ciclo pela Monitoramento). Devolve o registro de log."""
    import tempfile

    nome = os.path.basename(str(nome_arquivo))
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _registrar(**campos):
        registro = dict(quando=agora, estagio="ENVIO", origem=nome, handle="", data_video="",
                        ciclo="", destino="", status="")
        registro.update(campos)
        gravar_log([registro])
        return registro

    if os.path.splitext(nome)[1].lower() not in EXTENSOES_ENVIO:
        log_fn(f"[Envio] {nome}: formato não aceito (só vídeo ou foto PNG/JPG).")
        return _registrar(status="FORMATO NAO ACEITO")

    handle = str(handle_manual or "").strip().lstrip("@").lower()
    data_video = data_manual
    if not handle or data_video is None:
        handle_do_nome, data_do_nome = identificar_por_nome(nome)
        handle = handle or (handle_do_nome or "")
        if data_video is None:
            data_video = data_do_nome

    if not handle:
        log_fn(f"[Envio] {nome}: não deu pra saber de quem é o vídeo. Informe o influenciador na tela e envie de novo.")
        return _registrar(status="NAO RECONHECIDO")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = os.path.join(tmp, nome_para_disco(nome))
            with open(caminho, "wb") as f:
                f.write(dados)
            link_drive, ciclo = enviar_para_drive(caminho, handle, data_video, ciclo_manual,
                                                  marca=marca, tipo=tipo, log_fn=log_fn,
                                                  tela=tela, marcacao=marcacao,
                                                  pedido_por=pedido_por)
    except Exception as e:
        log_fn(f"[Envio] {nome}: falhou ao subir pro Drive. {str(e)[:160]}")
        return _registrar(handle="@" + handle, data_video=str(data_video or ""),
                          status=f"FALHA: {str(e)[:160]}")

    log_fn(f"[Envio] {nome}: @{handle}, {data_video or 'sem data'}, {ciclo}. Subiu pro Drive.")
    return _registrar(handle="@" + handle, data_video=str(data_video or ""),
                      ciclo=ciclo, destino=link_drive, status="OK")


def identificar_por_nome(nome_arquivo):
    base = os.path.splitext(nome_arquivo)[0]
    for padrao in PADROES:
        m = padrao["regex"].match(base)
        if m:
            g = m.groupdict()
            try:
                data = datetime(int(g["ano"]), int(g["mes"]), int(g["dia"])).date()
            except ValueError:
                continue
            return g["handle"], data
    return None, None


def processar_watch(log_fn=print):
    """Estágio B. Devolve a lista de registros de log (também gravada em CSV)."""
    os.makedirs(PASTA_MONITORADA, exist_ok=True)
    ja = {l["origem"] for l in ler_log() if l["estagio"] == "B"}
    log = []
    for nome in sorted(os.listdir(PASTA_MONITORADA)):
        caminho = os.path.join(PASTA_MONITORADA, nome)
        if not os.path.isfile(caminho) or os.path.splitext(nome)[1].lower() not in EXTENSOES_VIDEO:
            continue
        if nome in ja:
            continue
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        handle, data_video = identificar_por_nome(nome)
        if not handle:
            log_fn(f"[Watch] {nome} -> nome fora dos padrões conhecidos (revisão manual)")
            log.append(dict(quando=agora, estagio="B", origem=nome, handle="", data_video="",
                            ciclo="", destino="", status="NAO RECONHECIDO"))
            continue
        try:
            link_drive, ciclo = enviar_para_drive(caminho, handle, data_video,
                                                  log_fn=log_fn)
        except Exception as e:
            log_fn(f"[Watch] {nome} -> FALHA ao subir pro Drive: {str(e)[:160]}")
            log.append(dict(quando=agora, estagio="B", origem=nome, handle="@" + handle,
                            data_video=str(data_video), ciclo="", destino="", status=f"FALHA: {str(e)[:160]}"))
            continue
        log_fn(f"[Watch] {nome} -> @{handle} {data_video} -> Drive: {link_drive}")
        log.append(dict(quando=agora, estagio="B", origem=nome, handle="@" + handle,
                        data_video=str(data_video), ciclo=ciclo, destino=link_drive, status="OK"))
    gravar_log(log)
    return log
