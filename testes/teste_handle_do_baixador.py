# -*- coding: utf-8 -*-
"""
Prova que o baixador descobre o @ certo do influenciador.

POR QUE ESTE TESTE EXISTE (30/08/2026)

No primeiro uso real, um download de story saiu com o nome
"4777871830_..." em vez de "lomma_...". O Instagram devolveu o NÚMERO interno
do perfil no campo do autor, e o baixador usou como se fosse o @.

Isso não é detalhe estético. O nome do arquivo é o que liga o vídeo ao
influenciador quando a pessoa arrasta na tela: com o número no lugar do @, o
programa procuraria uma pasta @4777871830, que não existe no Drive de
ninguém, e o material iria para o lugar errado ou pararia.

O endereço que a pessoa colou traz o @ escrito por gente, então ele passou a
vir primeiro. Este teste fixa essa ordem e os casos que confundem: o "reel" e
o "p" que aparecem na mesma posição do @, e o número puro.

    py testes\teste_handle_do_baixador.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "baixador_local"))

import baixador

falhas = []

CASOS = [
    # (o que a pessoa colou, o que o Instagram devolveu, o @ esperado, por quê)
    ("https://www.instagram.com/stories/lomma/3974246092618411433/",
     {"uploader_id": "4777871830", "uploader": "Lomma"},
     "lomma",
     "story: o autor vem como número, o endereço tem o @ de verdade"),

    ("https://www.instagram.com/lomma/reel/DcoCDQKjjB2/",
     {"uploader_id": "4777871830"},
     "lomma",
     "reel com @ no endereço"),

    ("https://www.instagram.com/reel/DcoCDQKjjB2/",
     {"uploader_id": "juremafox"},
     "juremafox",
     "endereço sem o @: cai para o campo do autor"),

    ("https://www.instagram.com/p/ABC123/",
     {"channel": "wandre.rochaa", "uploader_id": "998877"},
     "wandre.rochaa",
     "o 'p' do endereço não é o @ de ninguém"),

    ("https://www.instagram.com/stories/andreasantosof_/123/",
     {},
     "andreasantosof_",
     "sublinhado no fim faz parte do @ e precisa sobreviver"),

    ("https://www.instagram.com/Debochad_A/reel/XYZ/",
     {},
     "debochad_a",
     "maiúscula vira minúscula, porque o @ não diferencia"),

    ("https://www.youtube.com/watch?v=abc",
     {"uploader_id": "12345", "uploader": "Canal do Fulano"},
     "",
     "só número e nome com espaço: nenhum serve como @"),

    ("https://www.instagram.com/stories/12345678/",
     {"uploader_id": "12345678"},
     "",
     "número puro é recusado em qualquer origem"),
]


def rodar():
    for link, entrada, esperado, porque in CASOS:
        obtido = baixador.descobrir_handle(link, entrada)
        if obtido == esperado:
            print(f"[  ok  ] {porque}")
        else:
            print(f"[ FALHA] {porque}")
            print(f"         esperava {esperado!r}, veio {obtido!r}")
            print(f"         endereço: {link}")
            falhas.append(porque)


if __name__ == "__main__":
    print("=" * 72)
    print("  De onde o baixador tira o @ do influenciador")
    print("=" * 72)
    print()
    rodar()
    print()
    print("=" * 72)
    if falhas:
        print(f"  {len(falhas)} FALHA(S). Nome de arquivo errado leva o vídeo")
        print("  para a pasta errada, ou para pasta nenhuma.")
    else:
        print("  PASSOU.")
    print("=" * 72)
    sys.exit(1 if falhas else 0)
