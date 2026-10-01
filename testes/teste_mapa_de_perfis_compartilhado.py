# -*- coding: utf-8 -*-
"""
O que uma máquina aprende sobre um perfil, as outras passam a saber.

POR QUE ESTE TESTE EXISTE (23/09/2026)

O mapa @ → número interno do perfil (`instagram_userids.json`) sempre foi um
arquivo LOCAL de cada instalação. O auditor perguntou, pensando na subida:
"no servidor vamos precisar dessa opção? porque o programa vai rodar em várias
máquinas". A pergunta expôs o problema: com seis pessoas baixando cada uma no
próprio notebook, o mesmo influenciador podia ser descoberto seis vezes.

E DESCOBRIR ESSE NÚMERO É A CHAMADA MAIS ARRISCADA DO PROGRAMA: medido em
28/08/2026, a conta levou bloqueio com TRÊS chamadas nesse endereço num dia,
contra um teto diário de 20 para tudo. Pagar seis vezes pelo mesmo
conhecimento é exatamente o padrão que já marcou conta de verdade.

A saída documentada até aqui era manual ("vale copiar entre máquinas", no
COMECE_AQUI), e proteção que depende de alguém lembrar falha no dia corrido.

AS TRÊS REGRAS QUE ESTE TESTE GUARDA:

1. aprender grava LOCAL primeiro e só depois sobe. Se a rede falhar, esta
   máquina não pode perder o que já descobriu;
2. a sincronia SÓ ACRESCENTA. O número local foi descoberto aqui e vale tanto
   quanto o de lá; uma linha errada na planilha não pode apagar conhecimento
   bom de todo mundo;
3. a planilha só é consultada quando o mapa local NÃO SABE. É o único momento
   em que a consulta se paga, porque é o momento em que a alternativa é a
   chamada perigosa.

Não fala com a rede: a planilha é dublê.

    py testes\\teste_mapa_de_perfis_compartilhado.py
"""
import json
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    guardados = {
        "arquivo": fluxo.ARQUIVO_USERIDS,
        "pasta": fluxo.PASTA_TESTE,
        "registrar": fluxo._registrar_perfil_compartilhado,
        "ler_partilha": fluxo._perfis_compartilhados,
        "quando": dict(fluxo._ULTIMA_SINCRONIA_PERFIS),
    }
    pasta_tmp = tempfile.mkdtemp(prefix="teste_perfis_")
    subidos = []
    na_planilha = {}

    try:
        fluxo.PASTA_TESTE = pasta_tmp
        fluxo.ARQUIVO_USERIDS = os.path.join(pasta_tmp, "instagram_userids.json")
        fluxo._registrar_perfil_compartilhado = (
            lambda handle, userid: subidos.append((handle, userid)))
        fluxo._perfis_compartilhados = lambda: dict(na_planilha)

        print("--- 1. aprender grava local E sobe para as outras máquinas ---")
        fluxo.guardar_userid("@Fulano", 123)
        conferir(fluxo._ler_userids() == {"fulano": 123},
                 "gravou no mapa local, com o @ normalizado",
                 str(fluxo._ler_userids()))
        conferir(subidos == [("fulano", 123)],
                 "e subiu para a aba compartilhada", str(subidos))

        print()
        print("--- 2. o que a máquina já sabe NÃO custa leitura de planilha ---")
        leituras = {"n": 0}

        def contar_leitura():
            leituras["n"] += 1
            return dict(na_planilha)

        fluxo._perfis_compartilhados = contar_leitura
        fluxo._ULTIMA_SINCRONIA_PERFIS["quando"] = 0.0
        conferir(fluxo.userid_guardado("@fulano") == 123, "responde do arquivo local")
        conferir(leituras["n"] == 0,
                 "sem tocar na planilha, porque já sabia", str(leituras["n"]))

        print()
        print("--- 3. o que ela NÃO sabe, ela busca com as outras ---")
        na_planilha["beltrano"] = 456
        fluxo._ULTIMA_SINCRONIA_PERFIS["quando"] = 0.0
        conferir(fluxo.userid_guardado("@beltrano") == 456,
                 "achou o perfil que outra máquina descobriu")
        conferir(leituras["n"] == 1, "com UMA leitura de planilha", str(leituras["n"]))
        conferir(fluxo._ler_userids().get("beltrano") == 456,
                 "e guardou no mapa local, para não perguntar de novo")

        print()
        print("--- 4. a leitura é limitada por tempo, não é por chamada ---")
        fluxo.userid_guardado("@naoexiste")
        fluxo.userid_guardado("@outro")
        conferir(leituras["n"] == 1,
                 "várias perguntas seguidas não viram várias leituras",
                 str(leituras["n"]))

        print()
        print("--- 5. a sincronia SÓ ACRESCENTA, nunca corrige o que é daqui ---")
        # O número local foi descoberto por esta máquina. Se a planilha
        # trouxer outro para o mesmo @, o daqui manda: linha errada lá não
        # pode apagar conhecimento bom de todo mundo.
        na_planilha["fulano"] = 999
        fluxo._ULTIMA_SINCRONIA_PERFIS["quando"] = 0.0
        fluxo.userid_guardado("@ninguem")  # força a sincronia
        conferir(fluxo._ler_userids().get("fulano") == 123,
                 "o número local sobreviveu à sincronia",
                 str(fluxo._ler_userids().get("fulano")))

        print()
        print("--- 6. planilha fora do ar não derruba nem apaga nada ---")
        def explodir():
            raise RuntimeError("sem rede")

        fluxo._perfis_compartilhados = explodir
        fluxo._ULTIMA_SINCRONIA_PERFIS["quando"] = 0.0
        conferir(fluxo.userid_guardado("@fulano") == 123,
                 "quem já estava no mapa continua respondendo")
        fluxo._ULTIMA_SINCRONIA_PERFIS["quando"] = 0.0
        conferir(fluxo.userid_guardado("@inexistente") is None,
                 "e quem não está devolve 'não sei', que é a resposta segura",
                 "'não sei' leva ao aviso; um número errado levaria a download errado")
        conferir(fluxo._ler_userids().get("fulano") == 123,
                 "e o mapa local ficou intacto")

        print()
        print("--- 7. falha ao SUBIR não faz o aprendizado se perder ---")
        def explodir_subida(handle, userid):
            raise RuntimeError("sem rede")

        fluxo._registrar_perfil_compartilhado = explodir_subida
        try:
            fluxo.guardar_userid("@novato", 789)
            subiu_sem_estourar = True
        except Exception:
            subiu_sem_estourar = False
        conferir(subiu_sem_estourar,
                 "guardar_userid não estoura quando a planilha está fora do ar")
        conferir(fluxo._ler_userids().get("novato") == 789,
                 "e o número fica gravado localmente do mesmo jeito",
                 "perder isso significaria gastar de novo a chamada perigosa")

    finally:
        fluxo.ARQUIVO_USERIDS = guardados["arquivo"]
        fluxo.PASTA_TESTE = guardados["pasta"]
        fluxo._registrar_perfil_compartilhado = guardados["registrar"]
        fluxo._perfis_compartilhados = guardados["ler_partilha"]
        fluxo._ULTIMA_SINCRONIA_PERFIS.clear()
        fluxo._ULTIMA_SINCRONIA_PERFIS.update(guardados["quando"])

    print()
    print("--- 8. a aba é própria, e não mistura com a de estado da conta ---")
    conferir(fluxo.ABA_PERFIS_INSTAGRAM != fluxo.ABA_ESTADO_INSTAGRAM,
             "perfil e estado da conta moram em abas diferentes",
             "as colunas são outras: aqui é @ e número, lá é conta e pausa")
    conferir("handle" in fluxo.CAMPOS_PERFIS_INSTAGRAM
             and "userid" in fluxo.CAMPOS_PERFIS_INSTAGRAM,
             "e as colunas dizem o que guardam")
    conferir(fluxo.SEGUNDOS_ENTRE_SINCRONIAS_PERFIS
             > fluxo.SEGUNDOS_ENTRE_SINCRONIAS_ESTADO_COMPARTILHADO,
             "perfil sincroniza mais devagar que pausa, e isso é de propósito",
             "pausa é urgente; número de perfil não muda depois de descoberto")


if __name__ == "__main__":
    print("=" * 74)
    print("  Mapa de perfis compartilhado entre as máquinas")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
