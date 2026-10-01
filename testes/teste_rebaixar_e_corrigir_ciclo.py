# -*- coding: utf-8 -*-
"""
Prova que rebaixar a pedido não vira acusação de contrato, e que corrigir ciclo
não exige rebaixar.

POR QUE ESTE TESTE EXISTE (01/09/2026)

O auditor perguntou o que acontece quando alguém joga um link, dá erro (a
internet cai, por exemplo), e além disso quer mudar o ciclo: ela consegue
rebaixar? A resposta era sim, e com dois estragos.

PRIMEIRO ESTRAGO, e é o grave. Ao baixar o mesmo vídeo de novo, o envio compara
o conteúdo, acha o arquivo idêntico no Drive e marcava "VÍDEO REAPROVEITADO:
reaproveitar peça é vedado em contrato". Essa marca existe para um achado real,
o influenciador republicando peça antiga como nova, e não distinguia isso de uma
analista rebaixando por decisão interna. Ou seja: uma operação de rotina
produzia uma acusação de descumprimento contratual.

SEGUNDO ESTRAGO. Mudar o ciclo obrigava a rebaixar, o que gasta uma chamada ao
Instagram (o recurso escasso do programa) e cria uma linha duplicada na
Monitoramento, para trocar um campo de planilha que não tem nada a ver com o
arquivo.

O que este teste cobre:

  1. o pedido de rebaixamento é guardado com quem pediu e quando
  2. ele é CONSUMIDO no uso, e não vale para sempre: um reaproveitamento de
     verdade, meses depois, não pode ser silenciado por um pedido antigo
  3. quem não foi pedido continua sendo tratado como reaproveitamento
  4. a correção de ciclo escreve na planilha e REGISTRA a troca, porque ela é
     exceção à regra de nunca sobrescrever coluna do Marketing
  5. corrigir para o mesmo valor não registra troca que não houve

Nada aqui fala com o Google: a planilha é dublê.

    py testes\teste_rebaixar_e_corrigir_ciclo.py
"""
import os
import sys
import tempfile

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


LINK = "https://www.instagram.com/stories/exemplo/12345/"


def rodar():
    import fluxo_downloads as fluxo

    pasta = tempfile.mkdtemp(prefix="rebaixar_")
    arquivo_original = fluxo.ARQUIVO_REBAIXAMENTOS
    log_original = fluxo.ARQUIVO_LOG
    fluxo.ARQUIVO_REBAIXAMENTOS = os.path.join(pasta, "rebaixamentos_pedidos.json")
    fluxo.ARQUIVO_LOG = os.path.join(pasta, "log_fluxo_completo.csv")

    try:
        print("--- 1. o pedido guarda quem pediu e quando ---")
        quantos = fluxo.marcar_rebaixamento_pedido([LINK], quem="alguem@empresa.com")
        conferir(quantos == 1, "marcou um pedido", str(quantos))
        pedido = fluxo.consumir_rebaixamento_pedido(LINK)
        conferir(pedido is not None, "e o pedido é encontrado pelo endereço")
        conferir(pedido.get("quem") == "alguem@empresa.com",
                 "com quem pediu", str(pedido))
        conferir(bool(pedido.get("quando")), "e quando", str(pedido))

        print()
        print("--- 2. o pedido é CONSUMIDO, não fica valendo para sempre ---")
        # Este é o ponto que evita o silenciamento permanente: se o pedido
        # ficasse guardado, um reaproveitamento de verdade meses depois seria
        # tratado como rebaixamento interno.
        de_novo = fluxo.consumir_rebaixamento_pedido(LINK)
        conferir(de_novo is None,
                 "o segundo uso do mesmo endereço não encontra pedido nenhum",
                 "senão um reaproveitamento real seria silenciado depois")

        print()
        print("--- 3. endereço que ninguém pediu não tem pedido ---")
        conferir(fluxo.consumir_rebaixamento_pedido("https://outro/link/") is None,
                 "endereço sem pedido devolve nada")
        conferir(fluxo.consumir_rebaixamento_pedido("") is None,
                 "e endereço vazio também, sem quebrar")

        print()
        print("--- 4. arquivo ilegível não derruba download ---")
        # Registro corrompido não pode impedir alguém de baixar. O pior caso
        # passa a ser o aviso de reaproveitado, que é conservador.
        with open(fluxo.ARQUIVO_REBAIXAMENTOS, "w", encoding="utf-8") as f:
            f.write("isto não é json")
        conferir(fluxo.consumir_rebaixamento_pedido(LINK) is None,
                 "com o arquivo corrompido, devolve nada em vez de levantar erro")

        print()
        print("--- 5. a tela e o fluxo estão ligados ---")
        fonte_fluxo = open(os.path.join(BASE, "fluxo_downloads.py"),
                           encoding="utf-8").read()
        conferir("consumir_rebaixamento_pedido(link_original)" in fonte_fluxo,
                 "o envio consulta o pedido antes de acusar reaproveitamento")
        conferir("Rebaixado a pedido" in fonte_fluxo,
                 "e tem uma mensagem própria para esse caso")
        conferir("NÃO é peça reaproveitada pelo influenciador" in fonte_fluxo,
                 "que diz explicitamente que não é reaproveitamento",
                 "quem lê a planilha precisa saber que aquela marca não vale ali")
        # A MARCA VIROU "PEÇA REAPROVEITADA" EM 02/09/2026. Era "VÍDEO
        # REAPROVEITADO", e passou a alcançar imagem quando story de foto deixou
        # de ser recusado no download. A conferência olha o radical, para não
        # travar na palavra exata de novo.
        conferir("REAPROVEITAD" in fonte_fluxo,
                 "e a acusação continua existindo para o caso de verdade",
                 "tirar a marca seria pior que o falso positivo")
        conferir("VÍDEO REAPROVEITADO" not in fonte_fluxo,
                 "sem chamar de vídeo o que pode ser foto",
                 "a marca vai para a planilha da auditoria")

        fonte_pagina = open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
                            encoding="utf-8").read()
        conferir("reabrir_na_fila(escolhidas, quem=" in fonte_pagina,
                 "a tela passa quem pediu ao reabrir a linha",
                 "sem o nome, o rastro do rebaixamento fica anônimo")

        print()
        print("--- 6. corrigir ciclo escreve na planilha e REGISTRA ---")
        escritas = []
        lidas = {"valor": "Ciclo 3"}

        class SheetsFalso:
            @staticmethod
            def ler_coluna(planilha, aba, coluna, linhas):
                return {linhas[0]: lidas["valor"]}

            @staticmethod
            def escrever_lote(planilha, aba, coluna, atualizacoes):
                escritas.append((coluna, atualizacoes))

        import types
        falso = types.ModuleType("sheets_client")
        falso.ler_coluna = SheetsFalso.ler_coluna
        falso.escrever_lote = SheetsFalso.escrever_lote
        antigo = sys.modules.get("sheets_client")
        sys.modules["sheets_client"] = falso

        guardado_id = fluxo._planilha_monitoramento_id
        fluxo._planilha_monitoramento_id = lambda: "planilha_de_mentira"
        try:
            resultado = fluxo.corrigir_ciclo_na_monitoramento(
                42, "9", quem="coordenadora@empresa.com")
            # A PLANILHA GUARDA NÚMERO PURO, NÃO "Ciclo N" (corrigido em
            # 05/09/2026). "Ciclo N" é o formato das PASTAS do Drive; a coluna
            # CICLO da Monitoramento usa o número, medido nas 19.999 linhas da
            # planilha real, todas sem prefixo. Antes disso, criar a linha
            # gravava "9" e corrigir gravava "Ciclo 9": a mesma coluna em dois
            # formatos, conforme o caminho.
            conferir(resultado == ("Ciclo 3", "9"),
                     "devolve o ciclo antigo como está na célula e o novo já "
                     "no formato que foi gravado", str(resultado))
            conferir(len(escritas) == 1, "escreveu uma vez na planilha", str(escritas))
            conferir(escritas[0][1] == [(42, "9")],
                     "na linha certa e com o número puro, do jeito que o "
                     "Marketing escreve", str(escritas[0]))

            registro = fluxo.ler_log()
            correcoes = [l for l in registro if l.get("estagio") == "correcao"]
            conferir(len(correcoes) == 1, "e registrou a troca uma vez",
                     str(len(correcoes)))
            if correcoes:
                texto = correcoes[0].get("status") or ""
                conferir("Ciclo 3" in texto and '"9"' in texto,
                         "com o valor antigo E o novo no registro, e o novo "
                         "exatamente como foi escrito na célula",
                         texto[:110])
                conferir("coordenadora@empresa.com" in texto,
                         "e com quem fez a troca", texto[:110])
                conferir(correcoes[0].get("origem_ciclo") == "corrigido à mão",
                         "marcando que o ciclo foi corrigido à mão",
                         str(correcoes[0].get("origem_ciclo")))

            print()
            print("--- 7. corrigir para o mesmo valor não inventa troca ---")
            escritas.clear()
            lidas["valor"] = "Ciclo 9"
            conferir(fluxo.corrigir_ciclo_na_monitoramento(42, "9") is None,
                     "não faz nada quando o ciclo já é aquele",
                     "célula no formato antigo, com prefixo")
            conferir(not escritas,
                     "e não escreve na planilha à toa", str(escritas))

            # O CASO QUE ESTAVA QUEBRADO ATÉ 05/09/2026, e que é o formato
            # NORMAL da planilha: a célula tem "9" e alguém corrige para 9. A
            # comparação era feita contra "Ciclo 9", dava diferente, e o
            # programa gravava por cima trocando o formato e registrando uma
            # correção que não aconteceu. Ninguém veria o erro: a célula
            # continuaria "certa" aos olhos de quem lê, só que num formato que
            # nenhuma das 19.999 linhas reais usa, e com um registro falso na
            # trilha de auditoria.
            escritas.clear()
            lidas["valor"] = "9"
            conferir(fluxo.corrigir_ciclo_na_monitoramento(42, "9") is None,
                     "nem quando a célula já está no formato da planilha",
                     "célula com número puro, que é o formato real")
            conferir(not escritas,
                     "e também não escreve nesse caso", str(escritas))
            conferir(len([l for l in fluxo.ler_log()
                          if l.get("estagio") == "correcao"]) == 1,
                     "e a trilha continua com uma correção só, a de verdade",
                     "gravar aqui inventaria uma troca que não houve")
            correcoes_depois = [l for l in fluxo.ler_log()
                                if l.get("estagio") == "correcao"]
            conferir(len(correcoes_depois) == 1,
                     "nem registra uma troca que não houve",
                     str(len(correcoes_depois)))

            print()
            print("--- 8. valor que não é ciclo é recusado ---")
            conferir(fluxo.corrigir_ciclo_na_monitoramento(42, "   ") is None,
                     "ciclo vazio não passa")

            print()
            print("--- 9. o link abre NA ABA certa, não no Sumário ---")
            # Achado pelo auditor em 01/09/2026: "Abrir a Monitoramento" levava à
            # planilha, e ela abria no Sumário, porque a aba Monitoramento é a
            # QUARTA do arquivo. Quem clica ali quer ver as linhas.
            fluxo._gid_das_abas.clear()
            fluxo._gid_das_abas[("planilha_de_mentira",
                                 fluxo.ABA_MONITORAMENTO)] = 628608277
            link = fluxo.link_planilha_monitoramento()
            conferir(str(link).endswith("#gid=628608277"),
                     "o endereço termina com o número da aba", str(link))
            conferir("/edit#gid=" in str(link),
                     "e usa /edit antes do gid, senão o Google ignora a aba",
                     str(link))

            # Falha segura: sem conseguir o número da aba, devolve o link da
            # planilha em vez de não devolver nada. Botão que abre na aba errada
            # é bem melhor que botão que não abre.
            fluxo._gid_das_abas.clear()
            fluxo._gid_das_abas[("planilha_de_mentira",
                                 fluxo.ABA_MONITORAMENTO)] = None
            sem_gid = fluxo.link_planilha_monitoramento()
            conferir(sem_gid and "#gid=" not in sem_gid,
                     "sem o número da aba, ainda devolve o link da planilha",
                     str(sem_gid))
        finally:
            fluxo._gid_das_abas.clear()
            fluxo._planilha_monitoramento_id = guardado_id
            if antigo is not None:
                sys.modules["sheets_client"] = antigo
            else:
                sys.modules.pop("sheets_client", None)
    finally:
        fluxo.ARQUIVO_REBAIXAMENTOS = arquivo_original
        fluxo.ARQUIVO_LOG = log_original


if __name__ == "__main__":
    print("=" * 74)
    print("  Rebaixar a pedido, e corrigir ciclo sem rebaixar")
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
