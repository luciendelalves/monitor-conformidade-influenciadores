# -*- coding: utf-8 -*-
"""
Prova as regras de escrita no Calendário, e a separação teste x real.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário é planilha VIVA de outra área, preenchida à mão todo dia. As
regras existem para o programa nunca destruir trabalho de gente:

  1. nunca cria linha nova (se não achou, avisa)
  2. nunca escreve por cima de célula que já tem conteúdo, inclusive a sujeira
     medida na planilha real ("POSTADO NA LIVE", "-", "16:012", "18:40.")
  3. sem autorização de modo real, escreve na cópia de teste, sempre
  4. falha de rede devolve motivo, e não derruba o download

Nada aqui fala com o Google: a leitura e a escrita são dublês.

    py testes\\teste_calendario_escrita.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


# A linha 3 está vazia nas colunas do programa; a 4 já tem Horário escrito por
# gente, com um valor que o programa não entende e não precisa entender.
LINHAS = [
    ["giroquue", "LOTTU", "Responsável F", "", "", "11/09/2026", "", "", ""],
    ["maumauzk", "LOTTU", "Responsável A", "Mega Odds", "Publicada", "11/09/2026",
     "POSTADO NA LIVE", "Responsável A", ""],
]


class EscritaFalsa:
    def __init__(self):
        self.escritas = []

    def __call__(self, planilha, aba, coluna, atualizacoes):
        self.escritas.append((aba, coluna, list(atualizacoes)))

    def colunas(self):
        return [c for _, c, _ in self.escritas]


def rodar():
    import calendario_divulgacoes as cal

    print("--- 1. escreve nas colunas vazias ---")
    falsa = EscritaFalsa()
    guardado = (cal.ler_aba, cal._escrever_celulas, cal.planilha_id)
    try:
        cal.ler_aba = lambda aba: [list(l) for l in LINHAS]
        cal._escrever_celulas = falsa
        cal.planilha_id = lambda: "planilha_de_mentira"
        gravou, motivo = cal.escrever("SET.26", 3, {
            "jogo": "Mines", "status": cal.STATUS_PUBLICADA,
            "horario": "19:07", "monitorado": "Responsável F"})
        conferir(gravou, "grava na linha vazia", motivo)
        conferir(sorted(falsa.colunas()) == ["D", "E", "G", "H"],
                 "nas quatro colunas do programa, e em nenhuma outra",
                 str(sorted(falsa.colunas())))
        conferir(all(at[0][0] == 3 for _, _, at in falsa.escritas),
                 "sempre na linha pedida", str(falsa.escritas))
    finally:
        cal.ler_aba, cal._escrever_celulas, cal.planilha_id = guardado

    print()
    print("--- 2. NÃO escreve por cima do que já tem conteúdo ---")
    falsa = EscritaFalsa()
    guardado = (cal.ler_aba, cal._escrever_celulas, cal.planilha_id)
    try:
        cal.ler_aba = lambda aba: [list(l) for l in LINHAS]
        cal._escrever_celulas = falsa
        cal.planilha_id = lambda: "planilha_de_mentira"
        gravou, motivo = cal.escrever("SET.26", 4, {
            "horario": "19:07", "jogo": "Mines", "status": cal.STATUS_PUBLICADA})
        conferir("G" not in falsa.colunas(),
                 "a coluna Horário com 'POSTADO NA LIVE' fica intacta",
                 str(falsa.colunas()))
        conferir("D" not in falsa.colunas() and "E" not in falsa.colunas(),
                 "e Jogo e Status preenchidos também ficam",
                 str(falsa.colunas()))
        conferir(gravou is False and "já estavam preenchidas" in motivo,
                 "com nada a escrever, diz isso em vez de dizer que gravou",
                 f"{gravou} {motivo}")
    finally:
        cal.ler_aba, cal._escrever_celulas, cal.planilha_id = guardado

    print()
    print("--- 3. valor vazio não apaga nem escreve ---")
    # Hora None (origem sem hora) e jogo não digitado chegam como texto vazio.
    # Escrever vazio por cima seria apagar; pular é o certo.
    falsa = EscritaFalsa()
    guardado = (cal.ler_aba, cal._escrever_celulas, cal.planilha_id)
    try:
        cal.ler_aba = lambda aba: [list(l) for l in LINHAS]
        cal._escrever_celulas = falsa
        cal.planilha_id = lambda: "planilha_de_mentira"
        cal.escrever("SET.26", 3, {"status": cal.STATUS_PUBLICADA,
                                   "jogo": "", "horario": None})
        conferir(falsa.colunas() == ["E"],
                 "só a coluna que tinha valor de verdade foi escrita",
                 str(falsa.colunas()))
    finally:
        cal.ler_aba, cal._escrever_celulas, cal.planilha_id = guardado

    print()
    print("--- 4. falha de rede devolve motivo, e não levanta erro ---")
    guardado = cal.ler_aba
    try:
        def explode(aba):
            raise RuntimeError("rede fora")
        cal.ler_aba = explode
        gravou, motivo = cal.escrever("SET.26", 3,
                                      {"status": cal.STATUS_PUBLICADA})
        conferir(gravou is False, "devolve False em vez de estourar")
        conferir("rede fora" in motivo,
                 "e o motivo real, para a tela poder dizer", motivo)
    finally:
        cal.ler_aba = guardado

    print()
    print("--- 5. fora do modo real, é a cópia de teste ---")
    # CONFERE COM VALOR DE VERDADE NOS DOIS LADOS (11/09/2026). Comparar
    # planilha_id() com ler_id_real() sem dublê passaria por acidente numa
    # máquina onde os dois são None, que é justamente a máquina do auditor.
    import fluxo_downloads as fluxo
    guardado = (fluxo.modo_real_autorizado, fluxo.ler_identificador)
    try:
        fluxo.ler_identificador = lambda caminho: (
            "ID_REAL" if caminho == cal.ARQUIVO_ID_REAL else "ID_TESTE")

        fluxo.modo_real_autorizado = lambda: False
        conferir(cal.planilha_id() == "ID_TESTE",
                 "sem autorização, devolve a cópia de teste",
                 cal.planilha_id())

        fluxo.modo_real_autorizado = lambda: True
        conferir(cal.planilha_id() == "ID_REAL",
                 "com autorização, devolve a real", cal.planilha_id())

        # Autorizado, mas sem o identificador do Calendário: cai no teste.
        fluxo.ler_identificador = lambda caminho: (
            None if caminho == cal.ARQUIVO_ID_REAL else "ID_TESTE")
        conferir(cal.planilha_id() == "ID_TESTE",
                 "autorizado mas sem o id do Calendário, cai no teste",
                 "faltando qualquer peça, o seguro é a cópia de teste")
    finally:
        fluxo.modo_real_autorizado, fluxo.ler_identificador = guardado

    print()
    print("--- 6. o identificador real mora em marketing_producao ---")
    conferir("marketing_producao" in cal.ARQUIVO_ID_REAL,
             "junto dos outros três de produção", cal.ARQUIVO_ID_REAL)
    conferir("teste_watch_folder" in cal.ARQUIVO_ID_TESTE,
             "e o de teste junto dos outros de teste", cal.ARQUIVO_ID_TESTE)
    conferir(os.path.basename(cal.ARQUIVO_ID_REAL) == "calendario_id.txt",
             "com o nome que o INSTALAR.md manda criar",
             os.path.basename(cal.ARQUIVO_ID_REAL))

    print()
    print("--- 7. o atalho da tela aponta para a planilha que está VALENDO ---")
    # Pedido do auditor em 11/09/2026: link do Calendário dentro do programa.
    # O risco é o atalho abrir a planilha real enquanto o programa escreve na
    # cópia de teste: a pessoa conferiria a planilha errada e concluiria que o
    # programa não escreveu nada.
    import fluxo_downloads as fluxo
    guardado = (fluxo.modo_real_autorizado, fluxo.ler_identificador,
                cal.planilha_id)
    try:
        fluxo.ler_identificador = lambda caminho: (
            "ID_REAL" if caminho == cal.ARQUIVO_ID_REAL else "ID_TESTE")

        fluxo.modo_real_autorizado = lambda: False
        conferir("ID_TESTE" in (cal.link() or ""),
                 "fora do modo real, o atalho abre a cópia de teste",
                 str(cal.link()))
        conferir(cal.e_a_real() is False,
                 "e a tela sabe que não é a real, para rotular certo")

        fluxo.modo_real_autorizado = lambda: True
        conferir("ID_REAL" in (cal.link() or ""),
                 "no modo real, abre a real", str(cal.link()))
        conferir(cal.e_a_real() is True, "e a tela sabe que é a real")

        # Sem identificador nenhum não existe atalho para oferecer.
        fluxo.ler_identificador = lambda caminho: None
        fluxo.modo_real_autorizado = lambda: False
        conferir(cal.link() is None,
                 "sem identificador, não devolve endereço quebrado",
                 str(cal.link()))
    finally:
        (fluxo.modo_real_autorizado, fluxo.ler_identificador,
         cal.planilha_id) = guardado

    print()
    # SEÇÃO 8 REMOVIDA EM 15/09/2026: testava o atalho "Abrir o Calendário
    # real/de teste" na tela de Downloads, que saiu por pedido do auditor
    # (menos link pra planilha crua na tela). `calendario_divulgacoes.link()`
    # e `e_a_real()`, testados nas seções 6 e 7 acima, continuam existindo e
    # corretos; só não há mais atalho nenhum consumindo eles na tela.

    print()
    print("--- 9. a escrita não apaga nem reordena nada ---")
    fonte = open(os.path.join(BASE, "calendario_divulgacoes.py"),
                 encoding="utf-8").read()
    for proibido in (".clear(", "batchUpdate", "deleteDimension",
                     "apagar_linhas"):
        conferir(proibido not in fonte,
                 f"não usa {proibido}",
                 "planilha de outra área não é lugar de apagar nada")


if __name__ == "__main__":
    print("=" * 74)
    print("  Escrita no Calendário")
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
