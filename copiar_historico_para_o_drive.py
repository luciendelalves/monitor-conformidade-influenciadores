# -*- coding: utf-8 -*-
"""
Guarda o histórico inteiro do programa num arquivo único, para cópia de
segurança fora desta máquina.

POR QUE ASSIM, E NÃO NO GITHUB (decidido em 29/08/2026)

O repositório é local. Isso já dá histórico e permite voltar atrás, mas não
protege contra perder o computador. A proteção contra perda pede uma cópia em
outro lugar.

Hospedar em conta pessoal do GitHub resolveria, mas tiraria a custódia do
código de auditoria interna da EGB para uma conta que a empresa não controla
nem consegue revogar. Enquanto não houver repositório em conta da empresa, a
cópia vai para o Drive corporativo, que a EGB já administra.

O QUE ELE GERA

Um arquivo `.bundle`, que é o repositório inteiro (todos os commits, toda a
história) dentro de um único arquivo. Para recuperar, em qualquer máquina:

    git clone historico_do_programa.bundle pasta-nova

O arquivo não contém credencial nenhuma, porque o repositório não versiona
credencial nenhuma (ver .gitignore).

USO

    py copiar_historico_para_o_drive.py

Ele grava numa pasta local de saída. Subir para o Drive é o passo manual, de
propósito: a credencial de escrita deste programa tem escopo restrito ao que
ele mesmo cria, e usar a sua conta para isso misturaria as coisas.
"""
import os
import subprocess
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_SAIDA = os.path.join(BASE, "..", "backup")

# O git instalado pelo winget fica na pasta do usuário e nem sempre está no
# caminho de busca do sistema, então procuramos nos lugares conhecidos antes
# de confiar no nome solto.
CANDIDATOS_GIT = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "cmd", "git.exe"),
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files (x86)\Git\cmd\git.exe",
    "git",
]


def achar_git():
    for caminho in CANDIDATOS_GIT:
        if caminho == "git" or os.path.exists(caminho):
            try:
                subprocess.run([caminho, "--version"], capture_output=True, check=True)
                return caminho
            except (OSError, subprocess.CalledProcessError):
                continue
    return None


def main():
    git = achar_git()
    if not git:
        print("Não achei o git instalado. Instale com: winget install --id Git.Git -e")
        return 1

    if not os.path.isdir(os.path.join(BASE, ".git")):
        print("Esta pasta não é um repositório. Nada a copiar.")
        return 1

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    nome = f"historico_programa_influenciadores_{datetime.now():%Y%m%d_%H%M}.bundle"
    destino = os.path.abspath(os.path.join(PASTA_SAIDA, nome))

    print("Empacotando o histórico inteiro...")
    resultado = subprocess.run([git, "bundle", "create", destino, "--all"],
                               cwd=BASE, capture_output=True, text=True)
    if resultado.returncode != 0 or not os.path.exists(destino):
        print("Não deu:")
        print(resultado.stderr[:500])
        return 1

    # Confere que o arquivo gerado é recuperável, em vez de confiar que deu
    # certo porque não deu erro. Cópia de segurança que ninguém testa é o
    # tipo de coisa que só falha no dia em que é necessária.
    conferencia = subprocess.run([git, "bundle", "verify", destino],
                                 cwd=BASE, capture_output=True, text=True)
    if conferencia.returncode != 0:
        print("O arquivo foi gerado mas NÃO passou na conferência. Não confie nele.")
        print(conferencia.stderr[:500])
        return 1

    commits = subprocess.run([git, "rev-list", "--count", "--all"],
                             cwd=BASE, capture_output=True, text=True).stdout.strip()
    tamanho = os.path.getsize(destino) / 1024

    print()
    print(f"Pronto: {destino}")
    print(f"  {commits} commit(s), {tamanho:.0f} KB, conferido e recuperável.")
    print()
    print("AGORA O PASSO MANUAL: suba esse arquivo para a pasta da Auditoria no")
    print("Drive corporativo. É ele que protege contra perder este computador.")
    print()
    print("Para recuperar em qualquer máquina:")
    print(f"    git clone {nome} pasta-nova")
    return 0


if __name__ == "__main__":
    sys.exit(main())
