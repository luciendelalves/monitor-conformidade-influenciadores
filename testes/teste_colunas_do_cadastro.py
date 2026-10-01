# -*- coding: utf-8 -*-
r"""
Prova que as colunas C a J vêm do cadastro, e que quem pediu não vira responsável.

O QUE O AUDITOR PERCEBEU EM 02/09/2026, olhando a planilha: "o time de marketing
está preenchendo essa parte aqui também de acordo com a planilha dados_influ".

Medido, e o alinhamento é exato, posição por posição:

    Monitoramento              Dados_influ
    B  @doinflu                B  INFLU
    C  ID DA CONTA             C  ID_CONTA
    D  Nº SEGUIDORES           D  NUM_SEGUIDORES
    E  CATEGORIA               E  CATEGORIA
    F  RESPONSÁVEL INTERNO     F  RESPONSAVEL
    G  INICIO CONTRATO         G  INÍCIO_CONTRATO
    H  FIM CONTRATO            H  FIM_CONTRATO
    I  STATUS                  I  STATUS
    J  ESCOPO                  J  ESCOPO

Eles copiavam coluna por coluna à mão. O programa passou a fazer o mesmo, com
autorização dele: "pode escrever em todas as colunas que conseguir, pois os dados
já estão lá".

O PERIGO QUE ESTE TESTE GUARDA

O mapeamento é POSICIONAL, e tem que ser: quatro dos oito títulos são escritos
diferente nas duas planilhas, então casar por nome deixaria metade de fora.

Só que posicional só é seguro enquanto ninguém inserir coluna em nenhuma das
duas. Se alguém inserir, tudo desloca, e o programa gravaria por exemplo a data
de fim de contrato dentro da coluna ESCOPO. **Isso corromperia dado de auditoria
em silêncio**, sem erro na tela, e o valor errado ficaria lá parecendo certo.

Por isso o programa confere o alinhamento antes de copiar, usando os títulos que
são escritos IGUAL nas duas, e DESISTE de copiar se algum não bater. É o que a
seção 3 prova.

E A OUTRA METADE: quem pediu o download NÃO vai para a coluna RESPONSÁVEL
INTERNO. Ver a seção 5.

    py testes\teste_colunas_do_cadastro.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []

# Cabeçalhos REAIS das duas planilhas, lidos em 02/09/2026.
CAB_CADASTRO = ["", "INFLU", "ID_CONTA", "NUM_SEGUIDORES", "CATEGORIA",
                "RESPONSAVEL", "INÍCIO_CONTRATO", "FIM_CONTRATO", "STATUS",
                "ESCOPO", "ANIVERSARIO", "MEDIDAS", "ESTADO", "CONTA",
                "PLATAFORMA", "LINKS_DIVULGAÇÃO", "AGENTE", "CONTATO_AGENTE",
                "ENDERECO", "Documentos"]
CAB_MONITORAMENTO = ["", "@doinflu", "ID DA CONTA", "Nº SEGUIDORES", "CATEGORIA",
                     "RESPONSÁVEL INTERNO", "INICIO CONTRATO", "FIM CONTRATO",
                     "STATUS", "ESCOPO", "MES", "ANO", "DATA_POST", "CICLO",
                     "TIPO", "POST", "CRONOGRAMA", "MARCA", "PAGAMENTO", "LINK",
                     "HORAS_LIVE", "OBS"]

# Uma linha de cadastro, com valor em cada uma das colunas C a J.
LINHA_CADASTRO = ["", "@fulano", "id-123", "48000", "Esporte", "Responsável C",
                  "01/01/2026", "31/12/2026", "ATIVO", "4 stories por mês"]


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. a faixa copiada é C a J ---")
    conferir(fluxo.PRIMEIRA_COLUNA_CADASTRO == 3
             and fluxo.ULTIMA_COLUNA_CADASTRO == 10,
             "copia da coluna C até a J",
             f"{fluxo.PRIMEIRA_COLUNA_CADASTRO} a {fluxo.ULTIMA_COLUNA_CADASTRO}")
    conferir(fluxo.letra_da_coluna(fluxo.PRIMEIRA_COLUNA_CADASTRO) == "C"
             and fluxo.letra_da_coluna(fluxo.ULTIMA_COLUNA_CADASTRO) == "J",
             "e as letras são C e J")

    print()
    print("--- 2. com as duas planilhas alinhadas, copia os oito valores ---")
    guardado = fluxo._ler_cadastro_completo
    try:
        fluxo._ler_cadastro_completo = lambda recarregar=False: (
            CAB_CADASTRO, {"fulano": LINHA_CADASTRO})
        valores, motivo = fluxo.dados_de_cadastro_para_a_linha(
            "@fulano", CAB_MONITORAMENTO)
        conferir(valores is not None, f"copiou", motivo)
        if valores:
            print(f"       {dict((fluxo.letra_da_coluna(n), v) for n, v in sorted(valores.items()))}")
            conferir(len(valores) == 8, "os oito valores", str(len(valores)))
            # O ponto do teste: cada valor na coluna certa.
            esperado = {3: "id-123", 4: "48000", 5: "Esporte", 6: "Responsável C",
                        7: "01/01/2026", 8: "31/12/2026", 9: "ATIVO",
                        10: "4 stories por mês"}
            for numero, texto in esperado.items():
                letra = fluxo.letra_da_coluna(numero)
                conferir(valores.get(numero) == texto,
                         f"{letra} ({CAB_MONITORAMENTO[numero - 1]}) = {texto!r}",
                         f"veio {valores.get(numero)!r}")

        print()
        print("--- 3. COLUNA INSERIDA faz o programa DESISTIR de copiar ---")
        # É a proteção que impede corromper dado em silêncio. Simula alguém
        # inserindo uma coluna no cadastro: tudo desloca uma casa para a direita.
        cab_torto = CAB_CADASTRO[:2] + ["COLUNA NOVA"] + CAB_CADASTRO[2:]
        linha_torta = LINHA_CADASTRO[:2] + ["algo"] + LINHA_CADASTRO[2:]
        fluxo._ler_cadastro_completo = lambda recarregar=False: (
            cab_torto, {"fulano": linha_torta})
        valores, motivo = fluxo.dados_de_cadastro_para_a_linha(
            "@fulano", CAB_MONITORAMENTO)
        conferir(valores is None,
                 "não copia nada quando o alinhamento quebrou",
                 f"copiou {valores}")
        conferir("coluna" in (motivo or "").lower(),
                 "e explica qual coluna deixou de bater", str(motivo)[:110])
        conferir("errada" in (motivo or "").lower() or "posição" in (motivo or "").lower(),
                 "dizendo o risco: gravar valor na coluna errada", str(motivo)[:110])

        print()
        print("--- 4. influenciador fora do cadastro não inventa valor ---")
        fluxo._ler_cadastro_completo = lambda recarregar=False: (
            CAB_CADASTRO, {"fulano": LINHA_CADASTRO})
        valores, motivo = fluxo.dados_de_cadastro_para_a_linha(
            "@naoexiste", CAB_MONITORAMENTO)
        conferir(valores is None, "devolve vazio", str(valores))
        conferir("cadastro" in (motivo or "").lower(),
                 "dizendo que ele não está no cadastro", str(motivo)[:90])

        print()
        print("--- 4b. célula vazia no cadastro continua vazia ---")
        # Não escrever nada é diferente de escrever "". A automação só escreve em
        # célula vazia, e um valor em branco vindo do cadastro não deve ocupar a
        # célula de quem for preencher à mão depois.
        magra = ["", "@magro", "", "", "Esporte", "", "", "", "ATIVO", ""]
        fluxo._ler_cadastro_completo = lambda recarregar=False: (
            CAB_CADASTRO, {"magro": magra})
        valores, _m = fluxo.dados_de_cadastro_para_a_linha("@magro", CAB_MONITORAMENTO)
        conferir(sorted(valores or {}) == [5, 9],
                 "só as duas colunas preenchidas viajam", str(valores))
    finally:
        fluxo._ler_cadastro_completo = guardado

    print()
    print("--- 4c. contrato cadastrado agora não fica com escopo em branco ---")
    # ACHADO EM 23/09/2026: até esta correção, dados_de_cadastro_para_a_linha
    # lia só o que já estava em memória. Se o trabalhador já estivesse de pé
    # quando um contrato novo entrasse na Dados_influ, a pasta era criada
    # (aquela checagem relia, ver impedimento_para_criar_pasta), mas a linha
    # da Monitoramento nascia com ESCOPO e contrato em branco, porque este
    # ponto não tinha a mesma segunda chance. Simula exatamente isso: a
    # primeira leitura não conhece @novocontrato, e só a releitura (que uma
    # planilha de verdade devolveria depois do cadastro ser salvo) o traz.
    chamadas = {"n": 0}

    def cadastro_que_so_atualiza_na_releitura(recarregar=False):
        chamadas["n"] += 1
        if recarregar:
            return (CAB_CADASTRO, {"fulano": LINHA_CADASTRO,
                                   "novocontrato": LINHA_CADASTRO})
        return (CAB_CADASTRO, {"fulano": LINHA_CADASTRO})

    fluxo._ler_cadastro_completo = cadastro_que_so_atualiza_na_releitura
    try:
        valores, motivo = fluxo.dados_de_cadastro_para_a_linha(
            "@novocontrato", CAB_MONITORAMENTO)
        conferir(valores is not None,
                 "achou o contrato novo relendo, sem esperar reiniciar o trabalhador",
                 motivo)
        conferir(chamadas["n"] == 2,
                 "e leu duas vezes: a de memória, depois a atualizada",
                 str(chamadas["n"]))

        print()
        print("--- 4d. @ que de fato não existe não fica relendo à toa ---")
        chamadas["n"] = 0
        valores, motivo = fluxo.dados_de_cadastro_para_a_linha(
            "@naoexistemesmo", CAB_MONITORAMENTO)
        conferir(valores is None, "continua vazio", str(valores))
        conferir(chamadas["n"] == 2,
                 "releu uma vez para ter certeza, e não ficou insistindo mais",
                 str(chamadas["n"]))
    finally:
        fluxo._ler_cadastro_completo = guardado

    print()
    print("--- 5. QUEM PEDIU não vira RESPONSÁVEL INTERNO ---")
    # A ideia do auditor foi ligar o login à coluna F. Aquela coluna diz quem
    # CUIDA do influenciador; o login diz quem FEZ a ação. Quando as duas
    # divergem, a divergência é o sinal, e escrever o login ali apagaria o sinal.
    conferir(fluxo.COL_MON["pedido_por"] == 29,
             "quem pediu vai para a coluna AC, no bloco da automação",
             str(fluxo.COL_MON.get("pedido_por")))
    conferir(fluxo.letra_da_coluna(fluxo.COL_MON["pedido_por"]) == "AC",
             "e a letra é AC")
    conferir(6 not in [fluxo.COL_MON[c] for c in fluxo.COL_MON],
             "e a automação NÃO escreve na coluna F (responsável interno)",
             "F é atribuição de carteira, e vem do cadastro")
    titulos = {chave: titulo for chave, _letra, titulo, _p in fluxo.BLOCO_AUTOMACAO}
    conferir(titulos.get("pedido_por") == "PEDIDO_POR",
             "o título da coluna é PEDIDO_POR")

    print()
    print("--- 6. o rastro de quem pediu sobrevive à limpeza da fila ---")
    # Era o buraco: quem pediu ficava só no arquivo da tarefa do trabalhador, e a
    # limpeza de 02/09/2026 apagou 50 dessas tarefas.
    conferir("quem" in fluxo.CAMPOS_LOG,
             "o log de fluxo tem campo de quem",
             str(fluxo.CAMPOS_LOG))
    # A POSIÇÃO DE QUEM PEDIU É O QUE IMPORTA, e não ela ser a última coluna
    # (corrigido em 11/09/2026). A versão antiga exigia
    # ULTIMA_COLUNA_FILA == "G", e caiu quando a coluna `jogo` entrou no fim,
    # sem que nada tivesse quebrado: quem pediu continua na G. O teste estava
    # guardando o tamanho da fila, não a regra.
    conferir(fluxo.COL_FILA.get("quem_pediu") == 6
             and fluxo.letra_da_coluna_fila("quem_pediu") == "G",
             f"{fluxo.COL_FILA} / {fluxo.ULTIMA_COLUNA_FILA}")

    print()
    print("--- 7. quem pediu viaja na LINHA da fila, não na tarefa ---")
    # Uma tarefa processa TODOS os links pendentes, que podem ter sido colados
    # por pessoas diferentes. Se quem pediu viesse da tarefa, todos os links do
    # lote sairiam com o nome de quem clicou por último.
    import inspect
    fonte_fila = inspect.getsource(fluxo.processar_fila)
    conferir('pedido_por=item.get("quem_pediu")' in fonte_fila,
             "o download lê quem pediu do item da fila",
             "não da tarefa, que é do lote inteiro")
    with open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
              encoding="utf-8") as f:
        tela = f.read()
    conferir("identidade.quem_sou_eu()" in tela and "adicionar_na_fila" in tela,
             "e a tela põe a identidade na linha ao enfileirar")


if __name__ == "__main__":
    print("=" * 74)
    print("  Colunas C a J do cadastro, e quem pediu o download")
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
