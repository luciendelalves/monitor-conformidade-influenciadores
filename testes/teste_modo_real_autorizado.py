# -*- coding: utf-8 -*-
"""
Escrever nos sistemas REAIS do Marketing exige os três arquivos, não um só.

POR QUE ESTE TESTE EXISTE (08/09/2026)

Até aqui, escrever na Monitoramento e no Drive era sempre para o id que
estivesse gravado num arquivo só, sem nenhuma checagem própria no caminho de
escrita. Combinado com o Marketing, o programa passou a poder escrever de
verdade nos sistemas deles, quando a analista instalar. Isso não pode
depender de um único arquivo trocado por engano: por isso são três
(`ARQUIVO_AUTORIZACAO_ESCRITA_REAL`, `ARQUIVO_MONITORAMENTO_REAL_ID`,
`ARQUIVO_DRIVE_RAIZ_REAL_ID`), e faltando qualquer um o programa continua na
cópia de teste, sem avisar.

Este teste prova as duas direções com arquivos temporários, sem tocar nos
arquivos reais do projeto nem gastar chamada de API: a existência do id não
avisa nada por si, e o modo real nunca cria pasta sozinho no Drive.

    py testes\teste_modo_real_autorizado.py
"""
import os
import shutil
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def _escrever(caminho, conteudo):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)


def rodar():
    import fluxo_downloads as fluxo

    pasta_temp = tempfile.mkdtemp(prefix="teste_modo_real_")
    # GUARDA OS CAMINHOS ORIGINAIS, para devolver no fim. Este teste troca
    # constantes do módulo de propósito (é a forma mais simples de testar as
    # duas situações sem tocar nos arquivos reais do projeto), e precisa
    # devolver tudo, senão o resto da bateria passaria a ler do lugar errado.
    originais = {
        nome: getattr(fluxo, nome)
        for nome in (
            "ARQUIVO_MONITORAMENTO_ID", "ARQUIVO_DRIVE_RAIZ_ID",
            "ARQUIVO_MONITORAMENTO_REAL_ID", "ARQUIVO_DRIVE_RAIZ_REAL_ID",
            "ARQUIVO_AUTORIZACAO_ESCRITA_REAL",
        )
    }
    try:
        fluxo.ARQUIVO_MONITORAMENTO_ID = os.path.join(pasta_temp, "monitoramento_teste_id.txt")
        fluxo.ARQUIVO_DRIVE_RAIZ_ID = os.path.join(pasta_temp, "drive_teste_pasta_raiz_id.txt")
        fluxo.ARQUIVO_MONITORAMENTO_REAL_ID = os.path.join(pasta_temp, "monitoramento_id.txt")
        fluxo.ARQUIVO_DRIVE_RAIZ_REAL_ID = os.path.join(pasta_temp, "drive_pasta_raiz_id.txt")
        fluxo.ARQUIVO_AUTORIZACAO_ESCRITA_REAL = os.path.join(
            pasta_temp, "AUTORIZO_ESCREVER_NOS_SISTEMAS_REAIS_DO_MARKETING.txt")

        _escrever(fluxo.ARQUIVO_MONITORAMENTO_ID, "id-de-teste-monitoramento")
        _escrever(fluxo.ARQUIVO_DRIVE_RAIZ_ID, "id-de-teste-drive")

        print("--- 1. sem nenhum dos três arquivos reais, cai em teste ---")
        conferir(not fluxo.modo_real_autorizado(),
                 "modo_real_autorizado() é False de partida")
        conferir(fluxo._planilha_monitoramento_id() == "id-de-teste-monitoramento",
                 "a Monitoramento usada é a de teste")
        conferir(fluxo._pasta_raiz_drive() == "id-de-teste-drive",
                 "a pasta do Drive usada é a de teste")

        print()
        print("--- 2. só os dois identificadores reais, SEM autorização: continua em teste ---")
        _escrever(fluxo.ARQUIVO_MONITORAMENTO_REAL_ID, "id-real-monitoramento")
        _escrever(fluxo.ARQUIVO_DRIVE_RAIZ_REAL_ID, "id-real-drive")
        conferir(not fluxo.modo_real_autorizado(),
                 "identificador real sozinho não liga o modo real")
        conferir(fluxo._planilha_monitoramento_id() == "id-de-teste-monitoramento",
                 "e a Monitoramento continua sendo a de teste")

        print()
        print("--- 3. só a autorização, SEM os identificadores reais: continua em teste ---")
        os.remove(fluxo.ARQUIVO_MONITORAMENTO_REAL_ID)
        os.remove(fluxo.ARQUIVO_DRIVE_RAIZ_REAL_ID)
        _escrever(fluxo.ARQUIVO_AUTORIZACAO_ESCRITA_REAL, "")
        conferir(not fluxo.modo_real_autorizado(),
                 "autorização sozinha, sem identificador, não liga o modo real")

        print()
        print("--- 4. os três presentes: liga o modo real ---")
        _escrever(fluxo.ARQUIVO_MONITORAMENTO_REAL_ID, "id-real-monitoramento")
        _escrever(fluxo.ARQUIVO_DRIVE_RAIZ_REAL_ID, "id-real-drive")
        conferir(fluxo.modo_real_autorizado(),
                 "com os três presentes e preenchidos, liga")
        conferir(fluxo._planilha_monitoramento_id() == "id-real-monitoramento",
                 "e a Monitoramento passa a ser a real")
        conferir(fluxo._pasta_raiz_drive() == "id-real-drive",
                 "e a pasta do Drive passa a ser a real")

        print()
        print("--- 5. no modo real, nunca cria pasta sozinho ---")
        # Troca a função de criar pasta por uma que reprova o teste se for
        # chamada. Se `_pasta_raiz_drive()` tentar criar algo no modo real,
        # isso pega na hora, em vez de descobrir depois de já ter criado uma
        # pasta indevida dentro do Drive do Marketing.
        import drive_client_upload
        chamou = []
        original_criar = getattr(drive_client_upload, "obter_ou_criar_pasta", None)
        drive_client_upload.obter_ou_criar_pasta = (
            lambda *a, **k: chamou.append(1) or "NAO-DEVERIA-CRIAR")
        try:
            fluxo._pasta_raiz_drive()
        finally:
            if original_criar is not None:
                drive_client_upload.obter_ou_criar_pasta = original_criar
        conferir(not chamou,
                 "obter_ou_criar_pasta não foi chamada no modo real")

        print()
        print("--- 6. identificador real some no meio do caminho: erra, não inventa pasta ---")
        os.remove(fluxo.ARQUIVO_DRIVE_RAIZ_REAL_ID)
        # A autorização e o id da Monitoramento continuam, então
        # modo_real_autorizado() já deveria estar False de novo (falta um dos
        # três), e a função tem que voltar a usar a cópia de teste.
        conferir(not fluxo.modo_real_autorizado(),
                 "identificador real removido tira o modo real, não deixa em estado inválido")
        conferir(fluxo._pasta_raiz_drive() == "id-de-teste-drive",
                 "e volta a usar a pasta de teste, em vez de travar ou inventar uma")
    finally:
        for nome, valor in originais.items():
            setattr(fluxo, nome, valor)
        shutil.rmtree(pasta_temp, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 74)
    print("  Modo real: só liga com os três arquivos, nunca cria pasta sozinho")
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
