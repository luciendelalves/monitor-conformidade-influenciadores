# -*- coding: utf-8 -*-
"""
Duas chamadas quase juntas a obter_ou_criar_pasta não podem criar pasta
duplicada, e uma pasta já conhecida nunca mais passa pela busca ao vivo.

POR QUE ESTE TESTE EXISTE (25/09/2026)

Achado ao vivo, não em teoria, em dois momentos do mesmo dia:

1. Duas pastas "03. LOTTU" na raiz de teste, criadas em dias DIFERENTES (22
   e 23/09), cada uma com a árvore inteira embaixo. Processando um link do
   Carlinhos, um dos arquivos achou a LOTTU errada, criando uma segunda
   árvore só pra ele, e essa linha saiu "SEM ACESSO À PASTA" na análise.
2. Poucos minutos depois de corrigir isso com uma trava, aconteceu de novo:
   duas pastas "story" criadas com 751 MILISSEGUNDOS de diferença, já
   dentro da trava (uma esperou a outra terminar de verdade), e mesmo assim
   a segunda não achou a que a primeira tinha acabado de criar. O índice de
   busca do Drive (`files().list`) não é imediatamente consistente com uma
   criação recém-feita, e isso a trava sozinha não resolve: ela ordena as
   chamadas, não obriga o Google a já saber da anterior.

A CORREÇÃO FINAL tem duas partes: `trava.travar()` por cima do trecho
inteiro (busca e criação juntas, mesma técnica de
`registrar_na_monitoramento` para a Monitoramento), e um CACHE PERSISTENTE
(`pastas_conhecidas.json`) que guarda a resposta a primeira vez e nunca
mais deixa a busca ao vivo decidir de novo, do mesmo jeito que o programa
já faz para o número de perfil do Instagram e o mapa de pastas do futebol.

ESTRUTURAL, E NÃO DE CONCORRÊNCIA DE VERDADE: simular duas threads batendo
na API do Google gastaria cota e seria instável. O que se prova aqui é que
a ordem certa existe no código-fonte (cache, depois trava, depois busca,
depois criação, todos dentro do mesmo bloco), e que o cache funciona de
verdade contra um arquivo local (sem falar com o Drive).

    py testes\\teste_trava_criacao_de_pasta.py
"""
import inspect
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import drive_client_upload as dcu

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def conferir_estrutura():
    fonte = inspect.getsource(dcu.obter_ou_criar_pasta)

    trava_pos = fonte.find("trava.travar(_ARQUIVO_TRAVA_PASTA)")
    cache_pos = fonte.find("_ler_cache_pastas()")
    busca_pos = fonte.find("files().list(")
    criacao_pos = fonte.find("files().create(")
    grava_pos = fonte.rfind("json.dump(cache")

    conferir(0 < trava_pos < cache_pos < busca_pos < criacao_pos < grava_pos,
             "ordem certa: trava, depois cache, depois busca, depois criação, depois grava",
             f"trava {trava_pos}, cache {cache_pos}, busca {busca_pos}, "
             f"criação {criacao_pos}, grava {grava_pos}")

    # NENHUMA LINHA DO TRECHO CRÍTICO PODE ESCAPAR DO RECUO DA TRAVA: travar só
    # parte do caminho deixaria uma chamada furar a fila no meio.
    fim_pos = fonte.rfind("return id_pasta")
    trecho_critico = fonte[trava_pos:fim_pos]
    linhas_do_trecho = trecho_critico.split("\n")[1:]
    linha_da_trava = fonte[:trava_pos].rfind("\n")
    recuo_da_trava = trava_pos - linha_da_trava - 1 - len(fonte[linha_da_trava + 1:trava_pos].lstrip(" "))
    recuo_de_dentro = recuo_da_trava + 4
    fora_da_trava = [l for l in linhas_do_trecho
                     if l.strip() and (len(l) - len(l.lstrip(" "))) < recuo_de_dentro]
    conferir(not fora_da_trava,
             "cache, busca, decisão, criação e gravação continuam dentro do with",
             fora_da_trava[:3])

    conferir(hasattr(dcu, "_ARQUIVO_TRAVA_PASTA"),
             "existe um caminho de trava fixo, reaproveitado em toda chamada")
    conferir("teste_watch_folder" in dcu._ARQUIVO_TRAVA_PASTA,
             "a trava vive dentro da própria instalação (Marketing e Futebol nunca disputam a mesma pasta)",
             dcu._ARQUIVO_TRAVA_PASTA)
    conferir(hasattr(dcu, "_ARQUIVO_CACHE_PASTAS") and "teste_watch_folder" in dcu._ARQUIVO_CACHE_PASTAS,
             "existe um arquivo de cache fixo, também dentro da própria instalação",
             getattr(dcu, "_ARQUIVO_CACHE_PASTAS", None))


def conferir_cache_de_verdade():
    """Prova o cache contra um arquivo de teste próprio, sem tocar no Drive
    nem no arquivo que o programa usa de verdade."""
    caminho_original = dcu._ARQUIVO_CACHE_PASTAS
    caminho_trava_original = dcu._ARQUIVO_TRAVA_PASTA
    caminho_teste = os.path.join(BASE, "teste_watch_folder", "pastas_conhecidas_TESTE_UNITARIO.json")
    trava_teste = caminho_teste + ".trava_teste"
    if os.path.exists(caminho_teste):
        os.remove(caminho_teste)
    dcu._ARQUIVO_CACHE_PASTAS = caminho_teste
    dcu._ARQUIVO_TRAVA_PASTA = trava_teste
    chamadas = {"busca": 0, "criacao": 0}

    def _executar_falso(construir_e_chamar):
        # Não chama a API de verdade: só conta quantas vezes uma busca ou
        # criação TENTARIAM sair, pelo texto da própria chamada.
        return None

    def _list_falso(**kwargs):
        chamadas["busca"] += 1
        class _Resp:
            def execute(self_inner):
                return {"files": []}
        return _Resp()

    def _create_falso(**kwargs):
        chamadas["criacao"] += 1
        class _Resp:
            def execute(self_inner):
                return {"id": "id-fake-de-teste"}
        return _Resp()

    class _FilesFalso:
        def list(self, **kwargs):
            return _list_falso(**kwargs)

        def create(self, **kwargs):
            return _create_falso(**kwargs)

    class _ServiceFalso:
        def files(self):
            return _FilesFalso()

    servico_original = dcu.get_service
    dcu.get_service = lambda: _ServiceFalso()
    try:
        primeiro = dcu.obter_ou_criar_pasta("pasta de teste", "pai-fake")
        conferir(primeiro == "id-fake-de-teste",
                 "primeira chamada busca/cria de verdade e devolve o id",
                 primeiro)
        conferir(chamadas["busca"] == 1 and chamadas["criacao"] == 1,
                 "primeira chamada passou pela busca e pela criação, uma vez cada",
                 chamadas)

        segundo = dcu.obter_ou_criar_pasta("pasta de teste", "pai-fake")
        conferir(segundo == "id-fake-de-teste",
                 "segunda chamada devolve o MESMO id, do cache",
                 segundo)
        conferir(chamadas["busca"] == 1 and chamadas["criacao"] == 1,
                 "segunda chamada NÃO bateu no Drive de novo, nem busca nem criação",
                 chamadas)

        conferir(os.path.exists(caminho_teste),
                 "o cache ficou gravado em arquivo, sobrevive a reiniciar o processo")
        with open(caminho_teste, encoding="utf-8") as f:
            gravado = json.load(f)
        conferir(gravado.get("pai-fake::pasta de teste") == "id-fake-de-teste",
                 "a chave gravada junta a pasta-mãe e o nome, não só o nome",
                 gravado)
    finally:
        dcu.get_service = servico_original
        dcu._ARQUIVO_CACHE_PASTAS = caminho_original
        dcu._ARQUIVO_TRAVA_PASTA = caminho_trava_original
        for sobra in (caminho_teste, trava_teste):
            try:
                os.remove(sobra)
            except OSError:
                pass


def rodar():
    conferir_estrutura()
    conferir_cache_de_verdade()


if __name__ == "__main__":
    print("=" * 70)
    print("  obter_ou_criar_pasta: trava + cache persistente")
    print("=" * 70)
    print()
    rodar()
    print()
    print("=" * 70)
    if falhas:
        print(f"  {len(falhas)} FALHA(S):")
        for f in falhas:
            print(f"    - {f}")
    else:
        print("  PASSOU.")
    print("=" * 70)
    sys.exit(1 if falhas else 0)
