# -*- coding: utf-8 -*-
"""
Onde está o arquivo de credencial OAuth que os três autorizar_*.py usam.

POR QUE ISTO EXISTE (02/09/2026)

Os três scripts tinham o caminho ESCRITO FIXO dentro deles:

    CLIENT_SECRETS_PATH = r"C:\\Users\\auditor\\Documents\\COAF\\oauth_client.json"

Ou seja: o caminho da máquina de UMA pessoa, e de outro projeto (COAF). Em
qualquer outra máquina os três falham com "Não achei o client OAuth do projeto
COAF em: C:\\Users\\auditor\\...", que é uma mensagem que não ajuda quem
está instalando: o problema não é o arquivo faltar, é o caminho não ser dela.

Descoberto ao escrever o guia de instalação para a primeira colaboradora. Sem
isso, o guia mandaria rodar um comando que falha na máquina dela.

A ORDEM DE BUSCA, e o motivo de cada passo:

  1. a variável CLIENT_OAUTH_JSON, se a pessoa apontar à mão. Vem primeiro
     porque escolha explícita tem que ganhar de qualquer descoberta automática.
  2. o arquivo dentro de _drive_credenciais, que é o lugar natural: é a pasta do
     assunto, e o .gitignore já protege *oauth*.json ali.
  3. Documentos\\COAF\\oauth_client.json do usuário ATUAL, que é onde ele está na
     máquina de origem. Montado com a pasta do usuário corrente, e não com o nome
     de ninguém.
  4. a pasta de Downloads, porque é onde um arquivo baixado do Google Cloud
     Console cai por padrão.

O ARQUIVO NÃO É VERSIONADO, e não pode ser: ele tem client_id e client_secret
dentro. Ver o .gitignore. Quem instala numa máquina nova precisa recebê-lo por um
canal seguro, ou criar uma credencial nova no Google Cloud Console.
"""
import os

NOME_PADRAO = "oauth_client.json"
VARIAVEL = "CLIENT_OAUTH_JSON"


def candidatos():
    """Os lugares onde o arquivo pode estar, na ordem em que são tentados."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    perfil = os.path.expanduser("~")
    lugares = []

    indicado = os.environ.get(VARIAVEL)
    if indicado:
        lugares.append(indicado)

    lugares.append(os.path.join(aqui, NOME_PADRAO))
    lugares.append(os.path.join(perfil, "Documents", "COAF", NOME_PADRAO))
    lugares.append(os.path.join(perfil, "Documentos", "COAF", NOME_PADRAO))
    lugares.append(os.path.join(perfil, "Downloads", NOME_PADRAO))
    return lugares


def achar():
    """Caminho do arquivo, ou None se ele não estiver em nenhum dos lugares."""
    for caminho in candidatos():
        if caminho and os.path.exists(caminho):
            return caminho
    return None


def exigir():
    """Caminho do arquivo, ou uma explicação de como resolver.

    A mensagem diz onde foi procurado e o que fazer, porque quem vê este erro
    está instalando o programa numa máquina nova e não conhece o projeto."""
    caminho = achar()
    if caminho:
        return caminho
    linhas = [
        "Não achei o arquivo de credencial OAuth (client_id e client_secret).",
        "",
        "Procurei, nesta ordem:",
    ]
    for lugar in candidatos():
        linhas.append(f"   {lugar}")
    linhas += [
        "",
        "Como resolver, escolhendo UMA das duas:",
        "",
        f"  1. coloque o arquivo {NOME_PADRAO} na pasta _drive_credenciais",
        "     (ele NÃO vai para o repositório: o .gitignore já o protege)",
        "",
        f"  2. ou aponte onde ele está, pela variável {VARIAVEL}:",
        f"     set {VARIAVEL}=C:\\caminho\\para\\{NOME_PADRAO}",
        "",
        "O arquivo tem client_id e client_secret dentro, então ele não é",
        "versionado e precisa chegar à máquina por um canal seguro, ou ser",
        "criado de novo no Google Cloud Console.",
    ]
    raise SystemExit("\n".join(linhas))
