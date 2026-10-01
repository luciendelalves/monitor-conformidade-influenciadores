# -*- coding: utf-8 -*-
"""
Prova que o programa ENCONTRA a pasta que já existe e BARRA quando ela falta.

POR QUE ESTE TESTE EXISTE (30/08/2026)

O Drive do Marketing é organizado por bet, ano e mês, e as pastas são criadas
por eles, à mão. Lendo a árvore real, três das 18 pastas de mês de 2026 não
batem letra por letra com o que o programa monta:

    existe [01. Janeiro ]   com espaço no fim
    existe [03. Março ]     com espaço no fim
    existe [08. AGOSTO]     em maiúsculas, na ONA

Se o programa procurar pelo nome exato e criar quando não achar, passam a
existir duas pastas de mesmo nome aparente lado a lado, e o material do mês
fica dividido entre as duas. No nível do mês isso atinge todos os
influenciadores de uma vez, o que é pior que o caso já conhecido da pasta do
influenciador.

A decisão do auditor em 30/08/2026: o Marketing cria as pastas, e o programa
só encontra. Faltando qualquer uma, ele para e diz qual criar.

A REGRA FOI REVISADA EM 01/09/2026, E ESTE TESTE FOI AMPLIADO PARA COBRIR ISSO

O auditor lembrou a premissa maior do projeto: facilitar a vida dos analistas,
e quanto menos eles tiverem que criar, melhor. E o custo de faltar pasta não é
uma mensagem na tela: o vídeo já foi baixado quando o envio falha, então a
chamada ao Instagram foi gasta para nada.

Duas medições de 01/09/2026 permitiram afrouxar sem perder proteção:

  1. a comparação tolerante, depois de passar a ignorar TODO espaço, encontra
     TODAS as 19 pastas de mês que existem em 2026, inclusive "05.MAIO", que
     era a única que faltava. Então criar pasta de mês só acontece quando o mês
     realmente não existe, que é dia 1º
  2. dos influenciadores com STATUS ATIVO, 29 não têm pasta nenhuma em 2026, e
     cada um deles era um download que falhava depois de gastar a chamada

A regra passou a ser:

    bet, ano                       NUNCA cria. São 5 pastas que já existem, e
                                   errar na raiz do Drive deles é o pior erro
    mês                            cria quando faltar
    @influenciador                 cria, se o @ estiver na Dados_influ
    data, tipo, orgânico           cria quando faltar

A seção 5 cobre a política; as seções 1 a 3 cobrem o mecanismo, e continuam
valendo do jeito que estavam, porque o mecanismo não mudou.

Este teste não fala com o Drive: a listagem é uma função de mentira, e é por
isso que a regra pode ser conferida sem tocar em nada lá. O cadastro também é
dublê, senão o teste passaria a depender da planilha do Marketing.

    py testes\teste_pastas_do_marketing.py
"""
import os
import sys

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


# Árvore de mentira, copiada dos nomes REAIS lidos do Drive em 30/08/2026,
# com os defeitos de nome preservados de propósito.
ARVORE = {
    "raiz": [{"name": "01. EDS", "id": "eds"},
             {"name": "02. ONA", "id": "ona"},
             {"name": "03. LOTTU", "id": "lottu"},
             {"name": "04. EDSCAP", "id": "edscap"}],
    "eds": [{"name": "2025", "id": "eds2025"}, {"name": "2026", "id": "eds2026"}],
    "eds2026": [{"name": "01. Janeiro ", "id": "eds_jan"},     # espaço no fim
                {"name": "03. Março ", "id": "eds_mar"},       # espaço no fim
                {"name": "08. Agosto", "id": "eds_ago"}],
    "eds_ago": [{"name": "@jojotodynho", "id": "p_jojo"},
                {"name": "@Juremafox", "id": "p_jurema"},      # maiúscula
                {"name": "lomma ", "id": "p_lomma"}],          # sem @ e com espaço
    "ona": [{"name": "2026", "id": "ona2026"}],
    "ona2026": [{"name": "08. AGOSTO", "id": "ona_ago"}],      # maiúsculas
    "ona_ago": [],
}

criadas = []


def listar(id_pai):
    return list(ARVORE.get(id_pai, []))


def criar(nome, id_pai):
    criadas.append((nome, id_pai))
    novo = f"nova_{len(criadas)}"
    ARVORE.setdefault(id_pai, []).append({"name": nome, "id": novo})
    return novo


def descer(segmentos, deixar_criar=False):
    return fluxo.descer_pelo_caminho(
        "raiz", segmentos, listar,
        criar=(criar if deixar_criar else None),
        percorrido_inicial="VÍDEOS INFLUENCIADORES")


def rodar():
    print("--- 1. encontra a pasta que existe com o nome torto ---")
    casos = [
        (["01. EDS", "2026", "01. Janeiro"], "eds_jan", "mês com espaço no fim"),
        (["01. EDS", "2026", "03. Março"], "eds_mar", "outro mês com espaço"),
        (["02. ONA", "2026", "08. Agosto"], "ona_ago", "mês em MAIÚSCULAS"),
        (["01. EDS", "2026", "08. Agosto"], "eds_ago", "mês que bate certinho"),
        (["01. EDS", "2026", "08. Agosto", "@juremafox"], "p_jurema",
         "influenciador com maiúscula na pasta"),
        (["01. EDS", "2026", "08. Agosto", "@lomma"], "p_lomma",
         "influenciador sem @ e com espaço na pasta"),
    ]
    for segmentos, esperado, oque in casos:
        try:
            veio = descer(segmentos)
        except Exception as e:
            veio = f"ERRO: {str(e)[:60]}"
        conferir(veio == esperado, f"{oque}", f"veio {veio!r}, esperado {esperado!r}")

    conferir(not criadas, "e não criou NADA no caminho", str(criadas))

    print()
    print("--- 2. barra quando a pasta falta, dizendo qual ---")
    faltando = [
        (["01. EDS", "2026", "09. Setembro"], "09. Setembro", "mês que ainda não existe"),
        (["01. EDS", "2026", "08. Agosto", "@andersonneiff"], "@andersonneiff",
         "influenciador sem pasta naquele mês"),
        (["04. EDSCAP", "2026", "08. Agosto"], "2026", "bet sem nenhum ano"),
    ]
    for segmentos, nome_que_falta, oque in faltando:
        try:
            descer(segmentos)
            conferir(False, oque, "não barrou")
        except fluxo.PastaNaoExisteNoDrive as e:
            conferir(nome_que_falta in str(e),
                     f"{oque}: diz que falta \"{nome_que_falta}\"", str(e)[:90])
        except Exception as e:
            conferir(False, oque, f"erro errado: {type(e).__name__}: {e}")

    conferir(not criadas, "continua sem criar nada", str(criadas))

    print()
    print("--- 3. no layout de teste, criar continua valendo ---")
    veio = descer(["01. EDS", "2026", "09. Setembro"], deixar_criar=True)
    conferir(bool(veio) and criadas == [("09. Setembro", "eds2026")],
             "cria só o que falta, quando a criação é permitida", str(criadas))

    print()
    print("--- 4. a bet é obrigatória ---")
    for valor in ("", None, "   ", "BET QUE NAO EXISTE"):
        try:
            fluxo.exigir_bet(valor)
            conferir(False, f"bet {valor!r} deveria ser recusada")
        except fluxo.BetNaoInformada:
            conferir(True, f"bet {valor!r} recusada")
    for sigla, pasta in fluxo.PASTA_DA_BET.items():
        conferir(fluxo.exigir_bet(sigla) == pasta, f"{sigla} -> {pasta}")
    conferir(fluxo.exigir_bet("eds") == "01. EDS", "aceita a sigla em minúscula")

    print()
    print("--- 5. a pasta inventada não existe mais ---")
    import inspect
    fonte = inspect.getsource(fluxo.caminho_ate_influenciador)
    conferir("SEM BET DEFINIDA" not in fonte,
             "o programa não monta mais \"00. SEM BET DEFINIDA\"",
             "essa pasta não existe no Drive do Marketing e seria criada na raiz deles")

    print()
    print("--- 6. A POLÍTICA: o que o programa cria, e o que ele nunca cria ---")
    # POR QUE ESTA SEÇÃO EXISTE. As seções 1 a 3 chamam descer_pelo_caminho com a
    # criação DESLIGADA, então elas provam o mecanismo e não a política. Quando a
    # política mudou em 01/09/2026, todas continuaram passando, e passar sem
    # cobrir é pior que falhar: dá a impressão de que a mudança foi conferida.
    conferir(fluxo.NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA == 2,
             "a bet e o ano continuam fora, e são só eles",
             str(fluxo.NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA))

    caminho = ["01. EDS", "2026", "09. Setembro", "@quemquerqueseja",
               "01/09", "story"]
    permitidos = len(caminho) - fluxo.NIVEIS_QUE_O_PROGRAMA_NUNCA_CRIA
    conferir(permitidos == 4,
             "num caminho de seis níveis, quatro podem ser criados", str(permitidos))

    print()
    print("--- 7. a TRAVA DO CADASTRO no lugar do \"nunca criar\" ---")
    # A trava substitui a regra antiga no nível do @, e o que ela precisa provar
    # é que continua barrando o caso que a regra antiga barrava: um @ que não
    # corresponde a ninguém. Sem isso, afrouxar a regra teria sido só afrouxar.
    original = fluxo.handles_do_cadastro
    try:
        fluxo.handles_do_cadastro = lambda recarregar=False: {"juremafox", "lomma"}
        conferir(fluxo.impedimento_para_criar_pasta("@juremafox") is None,
                 "@ que está no cadastro pode ter pasta criada")
        conferir(fluxo.impedimento_para_criar_pasta("@JuremaFox ") is None,
                 "e a comparação é a tolerante, igual à das pastas")
        barrado = fluxo.impedimento_para_criar_pasta("@juremafoxx")
        conferir(bool(barrado) and "@juremafoxx" in barrado,
                 "@ digitado errado é barrado, dizendo qual é", str(barrado)[:90])
        conferir(bool(barrado) and "Dados_influ" in barrado,
                 "e a mensagem diz onde conferir, senão ninguém sabe o que fazer")

        # OS OUTROS NÍVEIS NÃO PASSAM PELA TRAVA: nenhum deles depende de alguém
        # digitar, então travar ali só criaria falha sem motivo.
        for nome in ("09. Setembro", "01/09", "story", "orgânico"):
            conferir(fluxo.impedimento_para_criar_pasta(nome) is None,
                     f"{nome!r} não passa pela trava do cadastro")

        # FALHA FECHADA: cadastro ilegível não autoriza a criação. Se autorizasse,
        # bastaria uma falha de rede para a proteção deixar de existir, e ela
        # deixaria de existir exatamente quando ninguém está olhando.
        fluxo.handles_do_cadastro = lambda recarregar=False: None
        sem_cadastro = fluxo.impedimento_para_criar_pasta("@juremafox")
        conferir(bool(sem_cadastro),
                 "cadastro ilegível NÃO autoriza criar, mesmo para @ conhecido",
                 str(sem_cadastro)[:90])
        conferir(bool(sem_cadastro) and "não vou criar" in sem_cadastro,
                 "e a mensagem diz que não criou, em vez de acusar o @ de não existir")
    finally:
        fluxo.handles_do_cadastro = original

    print()
    print("--- 8. a trava BARRA a descida inteira, e não cria nada ---")
    # A prova de que a trava está ligada no caminho de verdade, e não só existe
    # como função solta.
    criadas.clear()
    original = fluxo.handles_do_cadastro
    try:
        fluxo.handles_do_cadastro = lambda recarregar=False: {"juremafox"}
        try:
            fluxo.descer_pelo_caminho(
                "raiz", ["01. EDS", "2026", "08. Agosto", "@naoexistemesmo",
                         "01/09", "story"],
                listar, criar=criar, criar_somente_ultimos=4,
                autorizar=fluxo.impedimento_para_criar_pasta)
            conferir(False, "deveria ter barrado no @ que não está no cadastro")
        except fluxo.PastaNaoExisteNoDrive as e:
            conferir("@naoexistemesmo" in str(e), "barrou e disse qual @", str(e)[:90])
            conferir(not criadas,
                     "e não criou NADA, nem os níveis que já estavam liberados",
                     str(criadas))

        # E com o @ conhecido, cria os quatro níveis liberados.
        #
        # OUTUBRO, e não setembro: a seção 3 já criou "09. Setembro" na árvore de
        # mentira, então com setembro o mês seria ENCONTRADO e a lista de criadas
        # sairia com três nomes. Foi o que aconteceu na primeira vez que este
        # teste rodou, e a expectativa estava errada, não o código.
        criadas.clear()
        veio = fluxo.descer_pelo_caminho(
            "raiz", ["01. EDS", "2026", "10. Outubro", "@juremafox",
                     "01/10", "story"],
            listar, criar=criar, criar_somente_ultimos=4,
            autorizar=fluxo.impedimento_para_criar_pasta)
        nomes_criados = [n for n, _pai in criadas]
        conferir(bool(veio) and nomes_criados == ["10. Outubro", "@juremafox",
                                                 "01/10", "story"],
                 "com o @ no cadastro, cria mês, influenciador, dia e tipo",
                 str(nomes_criados))
    finally:
        fluxo.handles_do_cadastro = original

    print()
    print("--- 9. a BET e o ANO continuam intocáveis, mesmo com criação ligada ---")
    # É o único nível onde "nunca cria" continua absoluto, e o motivo não é
    # medo: são 5 pastas que já existem, então criar não pouparia trabalho de
    # ninguém, e criar errado na RAIZ do Drive deles é o erro mais caro possível.
    criadas.clear()
    try:
        fluxo.descer_pelo_caminho(
            "raiz", ["05. BET QUE NAO EXISTE", "2026", "09. Setembro"],
            listar, criar=criar, criar_somente_ultimos=1)
        conferir(False, "deveria ter barrado na bet")
    except fluxo.PastaNaoExisteNoDrive as e:
        conferir("05. BET QUE NAO EXISTE" in str(e), "barra na bet que não existe")
        conferir(not criadas, "e não cria pasta na raiz do Drive deles", str(criadas))


if __name__ == "__main__":
    print("=" * 74)
    print("  Pastas do Drive do Marketing: encontrar, nunca criar")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
