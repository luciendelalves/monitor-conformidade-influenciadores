# -*- coding: utf-8 -*-
r"""
Levantamento de um termo nas peças que já foram analisadas.

SOMENTE LEITURA. Baixa cada arquivo do Drive pelo identificador do cache e relê
com Tesseract. Zero chamada ao Instagram.

    py ferramentas\levantar_termos.py portaria      qual número de portaria as peças citam
    py ferramentas\levantar_termos.py publi         quais termos de publicidade aparecem
    py ferramentas\levantar_termos.py "18\+"        qualquer expressão

PARA QUE SERVE, com o caso que a criou

O auditor pediu em 02/09/2026: "faça um levantamento para analisar quais estão
sendo os avisos de portaria nas análises que fizemos". O cache não responde
isso, porque ele guarda só o PEDAÇO que casou com o regex, e o regex casa na
primeira alternativa: a evidência diz sempre "portaria: 'PORTARIA'" e nunca o
número. Para saber QUAL portaria a peça cita, é preciso reler o texto.

O levantamento respondeu: todas as peças citam 136/25, nenhuma cita número
diferente. E de passagem encontrou um defeito no meu próprio padrão de captura,
que lia "N2136/25" como o número 2136/25.

CUSTO: um download e três leituras de Tesseract por peça. Com algumas dezenas de
peças isso leva minutos, então vale rodar em segundo plano.
"""
import os
import re
import shutil
import sys
import tempfile
from collections import Counter

from _base import cabecalho, contagem, linha, pedir_argumento, secao

import pipeline_influenciadores as pipeline
import validar_avisos_portaria136 as motor

E_TESTE = re.compile(r"teste[._]|arvore|organico\.0109|hierarquia", re.IGNORECASE)

# Modos prontos. Cada um sabe extrair o que interessa do texto lido, em vez de
# só dizer "achou" ou "não achou".
MODOS = {
    "portaria": {
        "titulo": "Número de portaria citado nas peças",
        "extrair": lambda texto: ([motor.numero_da_portaria(texto)]
                                  if motor.numero_da_portaria(texto) else []),
        "trecho": re.compile(r"PORTARIA[^.]{0,40}", re.IGNORECASE),
    },
    "publi": {
        "titulo": "Termos de declaração de publicidade encontrados",
        "extrair": lambda texto: [m.group(0).lower()
                                  for m in motor.REGEX_PUBLI.finditer(texto)],
        "trecho": None,
    },
    "fazenda": {
        "titulo": "Qual das três frases do Ministério da Fazenda aparece",
        "extrair": lambda texto: [m.group(0).lower() for m in
                                  motor.REGEX_MINISTERIO_FAZENDA.finditer(texto)],
        "trecho": None,
    },
}


def main():
    pedido = pedir_argumento(1, "portaria", "modo (portaria, publi, fazenda) ou regex")
    modo = MODOS.get(pedido)
    if modo is None:
        try:
            regex = re.compile(pedido, re.IGNORECASE)
        except re.error as e:
            raise SystemExit(f"{pedido!r} não é um modo conhecido nem uma expressão "
                             f"válida: {e}. Modos: {', '.join(MODOS)}")
        modo = {
            "titulo": f"Ocorrências de {pedido!r}",
            "extrair": lambda texto: [m.group(0).lower() for m in regex.finditer(texto)],
            "trecho": None,
        }

    cache = pipeline.carregar_cache()
    alvos = [r for r in cache.values()
             if r.get("drive_id")
             and not E_TESTE.search(f"{r.get('arquivo') or ''} "
                                    f"{r.get('influenciador') or ''}")]
    cabecalho(modo["titulo"], f"{len(alvos)} peça(s) com arquivo no Drive")
    if not alvos:
        print("   Nada a levantar. O cache está vazio ou só tem material de teste.")
        return 0
    print("   Só Tesseract, e cada arquivo é apagado do disco depois de lido.")
    print()

    import drive_client
    encontrados = Counter()
    trechos = Counter()
    sem_nada = []

    for i, registro in enumerate(alvos, start=1):
        nome = str(registro.get("arquivo") or registro["drive_id"])
        pasta = tempfile.mkdtemp(prefix="termo_")
        try:
            local = os.path.join(pasta, re.sub(r"[^\w.@-]", "_", nome))
            try:
                drive_client.download_file(registro["drive_id"], local)
            except Exception as e:
                print(f"   {i:>3}. {nome}: não baixei ({str(e)[:60]})")
                continue
            duracao = motor.duracao_do_video(local)
            quadros = motor.extract_frames(local, pasta) if duracao else [local]
            texto = " ".join(" ".join((motor.ocr_image_rapido(q) or "").split())
                             for q in quadros)
            achados = sorted(set(modo["extrair"](texto)))
            if modo["trecho"]:
                for m in modo["trecho"].finditer(texto):
                    trechos[" ".join(m.group(0).split())[:60]] += 1
            if achados:
                for a in achados:
                    encontrados[a] += 1
                print(f"   {i:>3}. {nome}: {', '.join(achados)}")
            else:
                sem_nada.append(nome)
                print(f"   {i:>3}. {nome}: nada  [{len(texto)} caracteres lidos]")
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    secao("resumo")
    if encontrados:
        contagem("encontrado (por peça)", encontrados, limite=25)
    else:
        print("   Nenhuma peça trouxe o que foi procurado.")
    if trechos:
        secao("como o OCR entregou o texto ao redor")
        contagem("trecho", trechos, limite=15)
    secao("peças sem nada")
    linha("quantas", len(sem_nada))
    for nome in sem_nada[:15]:
        print(f"      {nome}")
    if len(sem_nada) > 15:
        print(f"      ... e mais {len(sem_nada) - 15}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
