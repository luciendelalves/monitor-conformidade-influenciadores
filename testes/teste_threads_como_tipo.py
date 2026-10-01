# -*- coding: utf-8 -*-
"""
Threads como tipo de post, no mesmo grupo de X/Twitter e TikTok.

POR QUE ESTE ARQUIVO EXISTE (04/09/2026)

Pedido do auditor: "acho que é bom botar Threads como opção de rede social
tbm, né?". Threads entra na MESMA categoria de X/Twitter, TikTok e YouTube: é
registrado no "Link só para registrar" (fluxo_downloads.py), e a
régua da portaria não o analisa, porque o programa só valida peça do
Instagram. Sem entrar em TIPOS_NAO_VALIDAVEIS, um escopo que citasse Threads
nunca fecharia a cota, pelo mesmo motivo já documentado ali para os outros
quatro tipos: só peça CONFORME conta, e Threads nunca recebe veredito.

Rodar:

    py testes\teste_threads_como_tipo.py
"""
import os
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
    import escopo_e_entrega as ee
    import fluxo_downloads as fluxo

    print("--- 1. Threads está nos vocabulários da Monitoramento ---")
    conferir("THREADS" in fluxo.TIPOS,
             "THREADS está no vocabulário geral de tipo", str(fluxo.TIPOS))
    conferir("THREADS" in fluxo.TIPOS_VIDEO_EXTERNO,
             "e é oferecido no registro de link externo",
             str(fluxo.TIPOS_VIDEO_EXTERNO))

    print()
    print("--- 2. o link de Threads sugere o tipo sozinho ---")
    conferir(fluxo.tipo_pelo_link("https://www.threads.net/@fulano/post/abc")
             == "THREADS",
             "threads.net vira THREADS")
    conferir(fluxo.tipo_pelo_link("https://www.threads.com/@fulano/post/abc")
             == "THREADS",
             "e o domínio novo threads.com também")

    print()
    print("--- 3. a régua da portaria não bloqueia a cota por causa dele ---")
    conferir("THREADS" in ee.TIPOS_NAO_VALIDAVEIS,
             "Threads está na lista dos tipos que a régua não alcança",
             str(ee.TIPOS_NAO_VALIDAVEIS))
    lido = ee.ler_escopo("12 STORIES + 4 THREADS")
    conferir(lido["contratado"] == {"STORIES": 12},
             "só o que a régua alcança entra na cota", str(lido["contratado"]))
    conferir(lido["contratado_nao_validavel"].get("THREADS") == 4,
             "e Threads fica separado, com a quantidade preservada",
             str(lido["contratado_nao_validavel"]))

    print()
    print("--- 4. entregar Threads contratado não vira 'fora do escopo' ---")
    entregas = [{"handle": "@t", "ciclo": "1", "tipo": "THREADS", "post": i,
                "data_post": f"{i:02d}/09/2026", "marcacao": "LINK",
                "validacao": "NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)"}
               for i in range(1, 5)]
    contagem = ee.contar_entregas(entregas, "@t", "1")
    fechamento = ee.fechar_ciclo(lido, contagem)
    conferir("THREADS" not in fechamento["fora_do_escopo"],
             "Threads contratado não aparece como entrega fora do escopo",
             str(fechamento["fora_do_escopo"]))


if __name__ == "__main__":
    print("=" * 74)
    print("  Threads como tipo de post")
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
