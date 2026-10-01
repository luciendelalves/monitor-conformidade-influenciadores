# -*- coding: utf-8 -*-
r"""
Prova que "não havia o que fazer" é dito, e que filtro sem resultado não derruba
a tela.

OS DOIS DEFEITOS QUE O AUDITOR ENCONTROU EM 02/09/2026, um atrás do outro:

1. Ele clicou em baixar e a tela respondeu, em VERDE, "16:16: 0 de 0 baixados e
   organizados", com um expansor "Ver o que aconteceu" que abria e mostrava "sem
   registro". Ele leu como defeito do programa e chegou a supor que fosse o
   Instagram do influenciador aberto em mais de uma tela. Não era: a fila tinha
   duas linhas, as duas já com status, então nenhuma estava pendente. O
   trabalhador saía do laço sem escrever uma única mensagem, e a tela mostrava
   uma divisão que não aconteceu, pintada de sucesso.

   Silêncio é pior que erro: erro a pessoa investiga, silêncio ela interpreta.

2. A aba Monitoramento caía inteira com
   "ValueError: invalid literal for int() with base 10: ''".

   Causa medida: com filtro que não casa com nenhuma linha, a coluna vem sem
   valor nenhum, e aí o .map() do pandas não tem como saber que o resultado é
   sim/não, então devolve a coluna ainda como TEXTO. Somar coluna de texto junta
   os textos em vez de contar, o resultado é "", e int("") derruba a página.

   Apareceu ao filtrar orgânico sem nenhum orgânico na planilha, mas o defeito
   não era do filtro de orgânico: QUALQUER combinação de filtros sem resultado
   fazia o mesmo. É comportamento do pandas 3, e a seção 3 deixa isso medido
   para ninguém "simplificar" a conta de volta.

    py testes\teste_quando_nao_tem_nada_para_fazer.py
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


def ler_tela(nome):
    with open(os.path.join(BASE, "pages", nome), encoding="utf-8") as f:
        return f.read()


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. fila sem pendência DIZ que não tinha o que fazer ---")
    # Roda o processamento de verdade, com a fila trocada por uma que só tem
    # linhas já atendidas. Nenhuma chamada ao Instagram acontece: o programa
    # nem chega ao download.
    guardados = {"ler_fila": fluxo.ler_fila, "gravar_log": fluxo.gravar_log}
    try:
        fila_atendida = [
            dict(numero_linha=2, influenciador="fulano", status="BAIXADO E ORGANIZADO",
                 link="https://www.instagram.com/stories/fulano/123/", ciclo="Ciclo 1",
                 marca="LOTTU", organico="", quem_pediu="alguem@empresa.com"),
            dict(numero_linha=3, influenciador="fulano", status="BAIXADO E ORGANIZADO",
                 link="https://www.instagram.com/stories/fulano/456/", ciclo="Ciclo 1",
                 marca="LOTTU", organico="", quem_pediu=""),
        ]
        fluxo.ler_fila = lambda: fila_atendida
        fluxo.gravar_log = lambda registros: None

        ditas = []
        resultado = fluxo.processar_fila(log_fn=ditas.append, analisar_depois=False)
        conferir(resultado == [], "nada foi processado", str(resultado))
        conferir(bool(ditas), "e o programa NÃO ficou calado",
                 "era isso que fazia a tela parecer defeituosa")
        for linha in ditas:
            print(f"       {linha}")
        junto = " ".join(ditas).lower()
        conferir("nada para baixar" in junto,
                 "a mensagem diz que não havia o que baixar", junto[:120])
        conferir("status" in junto,
                 "e diz o MOTIVO: as linhas já têm status", junto[:120])
        conferir("apague o status" in junto,
                 "e diz o que fazer para tentar de novo", junto[:120])

        print()
        print("--- 2. fila totalmente vazia também fala ---")
        fluxo.ler_fila = lambda: []
        ditas = []
        fluxo.processar_fila(log_fn=ditas.append, analisar_depois=False)
        conferir(bool(ditas), "diz alguma coisa", str(ditas))
        conferir("vazia" in " ".join(ditas).lower(),
                 "e a mensagem é a da fila vazia, não a de status", str(ditas))
    finally:
        for nome, funcao in guardados.items():
            setattr(fluxo, nome, funcao)

    print()
    print("--- 3. o pandas devolve TEXTO ao contar coluna sem nenhuma linha ---")
    # Isto não é teste do nosso código: é a medição do comportamento que causou
    # a queda da aba. Fica aqui porque é o que justifica a conta ser em Python.
    import pandas as pd
    df = pd.DataFrame({"ORGANICO": ["SIM", ""]})
    vazia = df[df["ORGANICO"] == "NAO EXISTE"]
    somado = vazia["ORGANICO"].map(fluxo.e_sim).sum()
    conferir(somado == "", f"pandas {pd.__version__}: a soma da coluna vazia é "
             f"texto, e não zero", repr(somado))
    explodiu = False
    try:
        int(somado)
    except ValueError:
        explodiu = True
    conferir(explodiu, "e int() nessa soma derruba mesmo", "era o erro da tela")

    print()
    print("--- 4. a conta que a tela usa agora aguenta os dois casos ---")
    def contar(coluna):
        return sum(1 for v in coluna if fluxo.e_sim(v))
    conferir(contar(vazia["ORGANICO"]) == 0, "sem nenhuma linha, responde 0")
    conferir(contar(df["ORGANICO"]) == 1, "com um SIM, responde 1")
    conferir(contar(pd.Series(["s", "X", "TRUE", "", None])) == 3,
             "e continua lendo as outras grafias de sim")

    print()
    print("--- 5. a tela de Monitoramento não voltou para o int(...sum()) ---")
    monitoramento = ler_tela("2_Monitoramento.py")
    # Olha a LINHA DE CÓDIGO, e não o arquivo inteiro: o comentário ao lado da
    # correção cita o padrão antigo de propósito, para explicar o defeito, e
    # procurar no texto todo reprovaria justamente a explicação.
    linha_da_conta = [l.strip() for l in monitoramento.splitlines()
                      if l.strip().startswith("_organicos =")]
    conferir(len(linha_da_conta) == 1, "a conta de orgânicos está num lugar só",
             str(linha_da_conta))
    conferir(linha_da_conta and ".sum()" not in linha_da_conta[0],
             "e não usa mais a soma do pandas",
             "esse padrão é exatamente o que derrubava a aba")
    conferir(linha_da_conta and "sum(1 for v in" in linha_da_conta[0],
             "e conta em Python, que não depende do tipo da coluna",
             str(linha_da_conta))
    # A MÁSCARA DEIXOU DE EXISTIR EM 03/09/2026, e o defeito que ela podia trazer
    # também. Com a marcação virando três valores, o filtro passou a ser uma
    # lista de escolha, e ela entrou no mesmo laço dos outros filtros, que usa
    # `.isin(...)`. Comparação e isin sempre devolvem sim/não, então o problema
    # do tipo não se aplica a eles: era o `.map` sozinho que dependia do tipo.
    conferir("filtro_marcacao" in monitoramento,
             "o filtro da marcação existe")
    conferir("(col_de[\"marcacao\"], filtro_marcacao)" in monitoramento,
             "e ele entra no laço dos outros filtros, que usa isin",
             "isin devolve sim/não sempre, então não há máscara de texto")
    # OLHA SÓ LINHA DE CÓDIGO, e não o arquivo todo. Foi a TERCEIRA vez em dois
    # dias que uma conferência minha reprovou o comentário que registra a
    # correção: o comentário cita `.map(fluxo.e_sim)` de propósito, para explicar
    # o defeito que derrubava a aba. Varrer o arquivo inteiro por um trecho de
    # código proíbe também falar dele.
    codigo_da_tela = [l for l in monitoramento.splitlines()
                      if l.strip() and not l.strip().startswith("#")]
    conferir(not any(".map(fluxo.e_sim)" in l for l in codigo_da_tela),
             "e o e_sim saiu do código da tela, junto com o filtro de dois estados",
             "era ele que dependia do tipo da coluna")
    conferir("Nenhuma linha com esses filtros" in monitoramento,
             "e filtro sem resultado explica em vez de deixar tabela muda")

    print()
    print("--- 6. a tela de Downloads não mostra mais 'sem registro' ---")
    downloads = ler_tela("1_Downloads_e_Organizacao.py")
    conferir("sem registro" not in downloads,
             "o texto 'sem registro' saiu da tela",
             "era o que aparecia no lugar da explicação")
    # A REGRA SE MUDOU PARA fluxo_downloads.py EM 23/09/2026, dentro de
    # resumo_da_tarefa: a mesma função passou a servir duas páginas
    # (Downloads e Uploads), então deixou de poder viver dentro de uma tela
    # só. Quem continua na tela é só o DESENHO (a cor e o texto que aparecem
    # para cada aparência), e é isso que os dois conferem abaixo.
    fonte_motor = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir('if not entraram and not organizados:' in fonte_motor,
             "existe um caminho próprio para 'nada entrou'")
    conferir('"nada"' in fonte_motor and 'aparencia == "nada"' in downloads,
             "com aparência própria, tratada na hora de desenhar",
             "sem isso o caso cairia no verde de sucesso")
    conferir('st.info(texto)' in downloads,
             "e ela é azul de aviso, não verde de sucesso",
             "verde afirmava que deu certo algo que não foi feito")

    print()
    print("--- 7. colar o mesmo link NÃO baixa de novo, e isso é proposital ---")
    # A pergunta do auditor em 02/09/2026: "só estou conseguindo baixar depois de
    # limpar a fila, pq?". A recusa do link repetido é o que impede gastar duas
    # chamadas ao Instagram no mesmo vídeo, então ela FICA. O que mudou foi a
    # tela dizer qual linha e o que fazer.
    import sheets_client
    guardados = {"ler_fila": fluxo.ler_fila}
    escritas = []
    original_adicionar = sheets_client.adicionar_linhas
    try:
        link = "https://www.instagram.com/stories/fulano/123/"
        fluxo.ler_fila = lambda: [
            dict(numero_linha=2, influenciador="fulano", link=link,
                 status="BAIXADO E ORGANIZADO", ciclo="Ciclo 1", marca="LOTTU",
                 organico="", quem_pediu="")]
        sheets_client.adicionar_linhas = (
            lambda *a, **k: escritas.append(a) or None)

        add, dup = fluxo.adicionar_na_fila([("", link, "", "LOTTU", False, "eu")])
        conferir((add, dup) == (0, 1),
                 "o mesmo link não entra outra vez", f"add={add} dup={dup}")
        conferir(not escritas, "e nada é escrito na planilha da fila",
                 str(escritas))

        outro = "https://www.instagram.com/stories/fulano/456/"
        add2, dup2 = fluxo.adicionar_na_fila([("", outro, "", "LOTTU", False, "eu")])
        conferir((add2, dup2) == (1, 0), "link diferente entra normalmente",
                 f"add={add2} dup={dup2}")
    finally:
        sheets_client.adicionar_linhas = original_adicionar
        for nome, funcao in guardados.items():
            setattr(fluxo, nome, funcao)

    conferir("Nada foi baixado" in downloads,
             "a tela diz que nada foi baixado",
             "antes ela só dizia que o link já era conhecido")
    conferir("repetida['numero_linha']" in downloads
             or 'repetida["numero_linha"]' in downloads,
             "e diz em qual linha o link já está")
    # Procura a MENSAGEM, e não a frase em qualquer lugar do arquivo: o
    # comentário que registra a correção cita o texto antigo de propósito, e
    # varrer o arquivo todo reprovaria a própria explicação. Foi o mesmo tropeço
    # da seção 5, no mesmo dia.
    conferir('st.info("Esse link já foi baixado' not in downloads,
             "a mensagem que juntava duas situações diferentes saiu",
             "situações com ações diferentes não podem ter a mesma mensagem")

    print()
    print("--- 8. 'Baixar de novo' baixa no mesmo clique ---")
    # Eram três passos: achar a linha, clicar em Baixar de novo, e então achar um
    # terceiro botão mais abaixo. Era isso que fazia limpar a fila parecer o
    # caminho mais curto, e limpar a fila apaga o registro do que já passou.
    corpo = downloads.split("def _reabrir_escolhidas")[1].split("\n    c1, c2")[0]
    conferir("reabrir_na_fila" in corpo, "reabre a linha")
    conferir("fila_trabalho.criar" in corpo, "e manda baixar no mesmo clique",
             "sem isto a linha voltava para a fila e ficava lá parada")
    conferir("ha_trabalho" in corpo,
             "mas não cria uma segunda tarefa se já há download andando",
             "duas tarefas juntas tirariam a pausa entre chamadas ao Instagram")
    conferir("pegou_carona" in downloads,
             "e a tela não promete que já está baixando quando pegou carona",
             "a rodada lê a fila quando começa, então pode não pegar a linha")

    print()
    print("--- 9. link repetido: o pedido fica onde a recusa aparece ---")
    # O auditor, depois de um dia de testes: "para baixar qualquer vídeo eu tive
    # que limpar a fila, sempre antes de baixar algum vídeo tive que limpar a
    # fila". Apontar "Baixar de novo, logo abaixo" ainda obrigava a achar a linha
    # numa lista, e limpar a fila continuava sendo o caminho mais curto na tela.
    # Limpar é o pior: leva embora o registro do que já passou.
    conferir('st.session_state["link_repetido"] = link_novo' in downloads,
             "o formulário guarda qual link foi recusado",
             "botão não pode ficar dentro de formulário no Streamlit")
    conferir("_rebaixar_o_colado" in downloads,
             "e existe uma ação para baixar aquele link de novo")
    # CORTE POR CONTEÚDO, NÃO POR ESPAÇO NO INÍCIO DA LINHA (15/09/2026): era
    # "\n        st.session_state[...]", com oito espaços fixos, e quebrou
    # quando a seção ganhou mais um nível de recuo (zona colorida, pedido do
    # auditor no mesmo dia). O nível de recuo pode mudar de novo; o texto que
    # marca o fim da função não muda.
    corpo = downloads.split("def _rebaixar_o_colado")[1].split(
        'st.session_state["linha_do_repetido"] = _linha_repetida')[0]
    conferir("reabrir_na_fila" in corpo,
             "que reabre a linha daquele link")
    conferir("fila_trabalho.criar" in corpo,
             "e manda baixar no mesmo clique")
    conferir("ha_trabalho" in corpo,
             "sem criar segunda tarefa se já há download andando",
             "duas tarefas juntas tirariam a pausa entre chamadas ao Instagram")
    conferir("limpar_fila" not in corpo,
             "e NÃO limpa a fila para conseguir baixar",
             "limpar apaga o registro do que já passou, que é o que evita repetir")
    # A recusa em si continua existindo: ela é o que impede gastar duas chamadas
    # ao Instagram no mesmo vídeo. Provado na seção 7.
    conferir("Baixar de novo" in downloads,
             "o botão diz o que faz")
    conferir("gasta uma chamada do teto de hoje" in downloads,
             "e o aviso diz o custo antes do clique",
             "quem clica precisa saber que isso consome o recurso escasso")


if __name__ == "__main__":
    print("=" * 74)
    print("  Quando não tem nada para fazer, e quando o filtro não casa com nada")
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
