# -*- coding: utf-8 -*-
"""
Prova que o nome de quem usa é guardado, recuperado, e usado no que importa.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O nome não é enfeite: é ele que separa "tirar da fila o que EU mandei" de
"tirar o que todo mundo mandou", e é ele que aparece na coluna de quem pediu
cada análise. Se ele se perder ao recarregar a página, a pessoa volta a ser
indistinguível das outras sem perceber, e o botão de tirar da fila volta a
alcançar o trabalho alheio.

Confere também a regra mais importante: guardar é POR NAVEGADOR, nunca num
arquivo do servidor. O servidor é um só; nome guardado nele valeria para as
cinco pessoas, que é justamente o problema que este campo resolve.

    py testes\teste_identidade.py
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


class SessaoFalsa(dict):
    pass


class EnderecoFalso(dict):
    """Imita st.query_params: o que fica no endereço da página."""


def rodar():
    import identidade

    # Substitui o Streamlit por objetos simples. O que interessa é a regra,
    # não o desenho da tela.
    sessao, endereco = SessaoFalsa(), EnderecoFalso()

    class StreamlitFalso:
        session_state = sessao
        query_params = endereco
        user = None

    identidade.st = StreamlitFalso

    print("--- 1. sem nome, o programa sabe que não sabe ---")
    conferir(not identidade.tenho_nome(), "reconhece que não há nome declarado")
    padrao = identidade.quem_sou_eu()
    conferir(padrao == identidade.usuario_do_computador(),
             "sem nome, cai no usuário do computador", padrao)

    print()
    print("--- 2. digitou o nome, ele vai para o endereço ---")
    sessao[identidade.CHAVE] = "Ana"
    identidade._guardar_no_endereco()
    conferir(endereco.get(identidade.CHAVE_NO_ENDERECO) == "Ana",
             "o nome foi guardado no endereço da página", str(dict(endereco)))
    conferir(identidade.quem_sou_eu() == "Ana", "quem_sou_eu devolve o nome digitado")
    conferir(identidade.tenho_nome(), "reconhece que agora há nome")

    print()
    print("--- 3. recarregou a página: a sessão zera, o endereço fica ---")
    sessao.clear()
    conferir(not identidade.tenho_nome(), "a sessão realmente zerou")
    identidade._ler_do_endereco()
    conferir(sessao.get(identidade.CHAVE) == "Ana",
             "o nome voltou sozinho, vindo do endereço", str(dict(sessao)))
    conferir(identidade.quem_sou_eu() == "Ana", "e vale de novo")

    print()
    print("--- 4. outra pessoa, outro navegador, outro endereço ---")
    sessao2, endereco2 = SessaoFalsa(), EnderecoFalso()
    StreamlitFalso.session_state = sessao2
    StreamlitFalso.query_params = endereco2
    identidade._ler_do_endereco()
    conferir(not sessao2.get(identidade.CHAVE),
             "quem abre sem o nome no endereço NÃO herda o nome da outra pessoa",
             str(dict(sessao2)))

    print()
    print("--- 5. apagou o nome: some do endereço também ---")
    StreamlitFalso.session_state = sessao
    StreamlitFalso.query_params = endereco
    sessao[identidade.CHAVE] = "   "
    identidade._guardar_no_endereco()
    conferir(identidade.CHAVE_NO_ENDERECO not in endereco,
             "o nome saiu do endereço quando o campo foi esvaziado",
             str(dict(endereco)))

    print()
    print("--- 6. a regra que não pode ser quebrada ---")
    fonte = open(os.path.join(BASE, "identidade.py"), encoding="utf-8").read()
    grava_em_arquivo = any(t in fonte for t in ("open(", "json.dump", "write("))
    conferir(not grava_em_arquivo,
             "o nome NÃO é gravado em arquivo do servidor",
             "servidor é um só; arquivo valeria para as cinco pessoas")


if __name__ == "__main__":
    print("=" * 70)
    print("  Identificação de quem usa o programa")
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
