# -*- coding: utf-8 -*-
"""
Prova o atalho de abrir os dois processos com um clique só.

POR QUE ESTE TESTE EXISTE (10/09/2026)

`abrir_programa.bat` e `ferramentas\\criar_atalho_area_de_trabalho.ps1` foram
criados em 09/09/2026, pedido do auditor para facilitar a vida de quem não
acompanhou a história dos dois processos, como a analista de Marketing que vai
testar o programa até 30/09. Os dois foram testados NA MÃO naquele dia (o
auditor confirmou por processo real que trabalhador e tela sobem), mas
nenhuma das duas peças tinha teste automatizado, diferente de todo o resto do
mecanismo de dois processos (ver `teste_manutencao_e_atalhos.py`).

O QUE ESTE TESTE PROTEGE, e cada item é um jeito real de quebrar em silêncio:

  - o atalho da Área de Trabalho apontar para UM dos dois `iniciar_*.bat`
    direto, em vez de `abrir_programa.bat` — voltaria a exigir saber qual
    janela abrir quando, e em que ordem
  - o script do atalho ter caminho de máquina específica gravado dentro dele
    (usuário, letra de unidade). Ele PRECISA ser genérico, porque é para
    rodar em qualquer máquina onde alguém queira o atalho, começando pela da
    analista, que não é a do auditor
  - o `.bat` abrir a tela ANTES do trabalhador, ou sem nenhum respiro entre
    os dois — a tela avisa sozinha se o trabalhador não estiver de pé, mas
    não há motivo para arriscar a corrida
  - o `.bat` usar `call` num dos dois `start` — bloquearia esperando aquele
    processo terminar, e o trabalhador não termina sozinho em uso normal

NÃO EXECUTA os `.bat` nem o `.ps1` de verdade: rodar o `.ps1` de verdade cria
um atalho na Área de Trabalho real de quem roda o teste, e isso é efeito
colateral visível que um teste automatizado não deveria ter. A conferência é
toda por texto do arquivo, como já é feito em outras partes do projeto para
regra que não pode custar chamada nem efeito colateral (ver
`teste_registro_de_fechamentos.py`, seção 7).

    py testes\\teste_atalho_de_abrir_o_programa.py
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    caminho_bat = os.path.join(BASE, "abrir_programa.bat")
    caminho_ps1 = os.path.join(BASE, "ferramentas", "criar_atalho_area_de_trabalho.ps1")
    caminho_instalar = os.path.join(BASE, "INSTALAR.md")

    print("--- 1. abrir_programa.bat existe e sobe os dois, na ordem certa ---")
    conferir(os.path.exists(caminho_bat), "abrir_programa.bat existe")
    with open(caminho_bat, encoding="utf-8") as f:
        bat = f.read()

    conferir('cd /d "%~dp0"' in bat,
             "roda a partir da própria pasta, não da pasta de onde foi chamado",
             "sem isso, um atalho que aponte pra ele de outro lugar não acharia os .bat vizinhos")

    pos_trabalhador = bat.find('"iniciar_trabalhador.bat"')
    pos_tela = bat.find('"iniciar_validacao_influenciadores.bat"')
    conferir(pos_trabalhador != -1 and pos_tela != -1,
             "chama os dois .bat de sempre, pelo nome",
             f"trabalhador={pos_trabalhador} tela={pos_tela}")
    conferir(0 <= pos_trabalhador < pos_tela,
             "e chama o TRABALHADOR antes da TELA",
             "a tela avisa sozinha se o trabalhador não estiver de pé, mas não há razão pra arriscar a corrida")

    pos_timeout = bat.find("timeout")
    conferir(pos_trabalhador < pos_timeout < pos_tela,
             "há um respiro (timeout) entre o trabalhador e a tela",
             "sem isso as duas janelas competem por aparecer primeiro na tela de quem está olhando")

    conferir("call " not in bat.lower(),
             "não usa 'call' em nenhum dos dois",
             "'call' esperaria aquele processo terminar, e o trabalhador não termina sozinho em uso normal")

    print()
    print("--- 2. o script do atalho aponta para abrir_programa.bat, não para um dos dois isolado ---")
    conferir(os.path.exists(caminho_ps1), "criar_atalho_area_de_trabalho.ps1 existe")
    with open(caminho_ps1, encoding="utf-8") as f:
        ps1 = f.read()

    conferir('"abrir_programa.bat"' in ps1,
             "o alvo do atalho é abrir_programa.bat")
    for isolado in ("iniciar_trabalhador.bat", "iniciar_validacao_influenciadores.bat"):
        conferir(f'"{isolado}"' not in ps1,
                 f"e NÃO aponta direto para {isolado}",
                 "apontar pra um dos dois isolado faria o atalho abrir só metade do programa")

    print()
    print("--- 3. nada de caminho de UMA máquina específica gravado no script ---")
    # O script tem que rodar igual na máquina do auditor e na da analista. Um
    # caminho absoluto de usuário aqui seria a mesma armadilha da conta do
    # Instagram fixa no código (ver fluxo_downloads.py): funciona sozinho na
    # máquina de quem escreveu, e quebra sem avisar em qualquer outra.
    conferir("$PSScriptRoot" in ps1,
             "calcula a própria pasta a partir de $PSScriptRoot, não de um caminho fixo")
    conferir("Users\\" not in ps1 and "Users/" not in ps1,
             "não tem caminho de usuário do Windows escrito no meio do script",
             "isso travaria o atalho na conta de quem escreveu o script")
    conferir('GetFolderPath("Desktop")' in ps1,
             "acha a Área de Trabalho de quem roda, não um caminho fixo de Desktop")

    print()
    print("--- 4. falha cedo e clara se abrir_programa.bat não estiver do lado ---")
    conferir("Test-Path $alvo" in ps1 or "Test-Path $alvo)" in ps1,
             "confere se o alvo existe antes de criar o atalho")
    conferir("exit 1" in ps1,
             "e sai com erro em vez de criar atalho quebrado",
             "sem isso, rodar da pasta errada criaria um atalho que só avisa quando alguém clicar nele")

    print()
    print("--- 5. WorkingDirectory do atalho é a pasta do programa, coerente com o alvo ---")
    conferir("$atalho.WorkingDirectory = $pastaDoPrograma" in ps1,
             "a pasta de trabalho do atalho é a mesma pasta onde abrir_programa.bat está")

    print()
    print("--- 6. INSTALAR.md aponta para o nome de arquivo real, não um apelido desatualizado ---")
    with open(caminho_instalar, encoding="utf-8") as f:
        instalar = f.read()
    conferir("criar_atalho_area_de_trabalho.ps1" in instalar,
             "INSTALAR.md cita o script pelo nome exato",
             "um nome errado aqui manda quem instala procurar um arquivo que não existe")
    conferir("abrir_programa.bat" in instalar or "Abrir Monitoramento de Influenciadores" in instalar,
             "e explica o que o atalho abre")


if __name__ == "__main__":
    print("=" * 74)
    print("  Atalho de abrir os dois processos com um clique só")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
