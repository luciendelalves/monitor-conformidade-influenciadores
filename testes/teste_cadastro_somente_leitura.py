# -*- coding: utf-8 -*-
"""
Prova que a aba de Cadastro só escreve pelo caminho golden, e que dado
pessoal não chega à tela nem à escrita.

POR QUE ESTE TESTE EXISTE (31/08/2026, mudou de premissa em 14/09/2026)

A aba de Cadastro lê a Dados_influ da Monitoramento REAL do Marketing, e desde
14/09/2026 também corrige campo, célula por célula, pedido do auditor para
reduzir o uso direto da planilha. São as duas coisas que mais podem dar errado
neste projeto ao mesmo tempo:

  1. escrever na planilha real fora de um caminho controlado. Em 26/08 dois
     arquivos foram apagados de vez no Drive e não houve como recuperar, e é
     dessa família de erro que se trata aqui. Por isso a ESCRITA NÃO SAI DA
     TELA: mora em cadastro.py, testável sem subir o Streamlit
  2. trazer dado pessoal de influenciador para uma tela que cinco pessoas do
     Marketing usam, e agora também deixar esse dado ser corrigido. A aba tem
     ID_CONTA, CONTA, CONTATO_AGENTE, ENDERECO, ANIVERSARIO e MEDIDAS, e
     nenhuma delas tem função na auditoria de publicidade

As duas primeiras seções conferem lendo o código da página, e isso é de
propósito: uma página de Streamlit não dá para importar sem executar a tela, e
o que interessa aqui é uma propriedade do arquivo, não um resultado de
execução. As seções 11 e 12, novas, chamam `cadastro.corrigir_campo_no_cadastro`
de verdade, porque agora existe lógica de escrita para testar, não só ausência
dela.

DESDE 23/09/2026 (seções 6b e 14), a tela nunca escreve na Dados_influ real: a
conta só tem permissão de leitura nela. Antes de abrir, a tela espelha a real
numa cópia de teste (planilha nossa) e as três escritas miram só essa cópia.
A seção 14 prova que `cadastro.espelhar_cadastro_para_teste` só LÊ do id real
e só LIMPA/ESCREVE no id da cópia.

A escolha por LISTA DE PERMISSÃO também é conferida. Numa lista de bloqueio,
esquecer um nome expõe o dado; numa lista de permissão, esquecer significa não
mostrar. É o mesmo critério do .gitignore deste projeto.

    py testes\teste_cadastro_somente_leitura.py
"""
import inspect
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# Renomeado de 3_ para 4_ em 03/09/2026: o Financeiro também nasceu com prefixo
# 3_, e dois arquivos disputando a mesma posição é um número que não ordena
# nada. Quem manda na ordem é o st.navigation, mas este programa já caiu uma vez
# no menu automático da pasta pages/ (ver painel.py), e nesse caminho o
# desempate entre dois 3_ é alfabético.
PAGINA = os.path.join(BASE, "pages", "4_Cadastro_de_Influenciadores.py")

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


# Tudo o que escreve numa planilha do Google, no cliente que este projeto usa.
ESCRITAS_DE_PLANILHA = (
    "escrever_lote", "adicionar_linhas", "apagar_linhas",
    ".update(", "batchUpdate", "values().append", "values().update",
)


def rodar():
    fonte = open(PAGINA, encoding="utf-8").read()

    print("--- 1. a página não chama escrita de planilha direto (só pelo caminho golden) ---")
    for termo in ESCRITAS_DE_PLANILHA:
        conferir(termo not in fonte,
                 f"não usa {termo}",
                 "a escrita mora em cadastro.py, testado nas seções 11 e 12")
    conferir("import cadastro" in fonte,
             "a página importa o módulo de escrita",
             "sem isso não haveria como corrigir campo nenhum")

    print()
    print("--- 2. e não escreve no Drive ---")
    for termo in ("files().create", "files().update", "files().delete", "upload"):
        conferir(termo not in fonte, f"não usa {termo}")

    print()
    print("--- 3. dado pessoal não chega à tela ---")
    import importlib.util

    # Carrega só as constantes, sem executar a tela: lê o arquivo e roda apenas
    # as atribuições de lista no topo. Mais simples e honesto que importar.
    permitidas = re.search(r"COLUNAS_PERMITIDAS = \[(.*?)\]", fonte, re.S)
    omitidas = re.search(r"COLUNAS_OMITIDAS_POR_PRIVACIDADE = \[(.*?)\]", fonte, re.S)
    conferir(bool(permitidas), "a lista de colunas permitidas existe")
    conferir(bool(omitidas), "a lista de colunas omitidas existe")
    if not permitidas:
        return

    nomes_permitidos = re.findall(r'"([^"]+)"', permitidas.group(1))
    print(f"       colunas que a tela mostra: {len(nomes_permitidos)}")

    PESSOAIS = ["ID_CONTA", "CONTA", "CONTATO_AGENTE", "ENDERECO",
                "ANIVERSARIO", "MEDIDAS"]
    for coluna in PESSOAIS:
        conferir(coluna not in nomes_permitidos,
                 f"{coluna} NÃO está entre as colunas mostradas",
                 "influenciador é pessoa física; isso não tem função aqui")

    # CONTA é caso especial e merece conferência própria: o nome dela está
    # contido em outros títulos que SÃO legítimos, e uma comparação frouxa
    # deixaria passar.
    conferir("CONTA" not in nomes_permitidos,
             "CONTA não entra nem por comparação frouxa",
             str(nomes_permitidos))

    print()
    print("--- 4. o que a tela precisa mostrar está lá ---")
    for coluna in ("INFLU", "STATUS", "ESCOPO", "INÍCIO_CONTRATO", "FIM_CONTRATO"):
        conferir(coluna in nomes_permitidos, f"{coluna} está entre as mostradas")

    print()
    print("--- 4b. AGENTE e ESTADO entraram em 23/09/2026, e não são acidente ---")
    # ACHADO PELO AUDITOR: a Dados_influ tem 19 colunas nomeadas, e só 17
    # apareciam nesta tela (11 mostradas + 6 omitidas por privacidade).
    # AGENTE e ESTADO não estavam em NENHUMA das duas listas: tinham sumido
    # por esquecimento na hora de montar as listas, não por decisão.
    #
    # Conteúdo real conferido antes de decidir: AGENTE guarda "Nexa" ou
    # "Interno" (a agência que representa o influenciador, ou nenhuma),
    # classificação comercial como PLATAFORMA e CATEGORIA. ESTADO guarda a
    # sigla do estado ("SP", "RJ"...), que É dado pessoal do influenciador,
    # mas ele é contraparte comercial, e a sigla é bem mais grosseira que o
    # ENDERECO completo, que continua fora.
    conferir("AGENTE" in nomes_permitidos,
             "AGENTE aparece: é o nome da agência, não dado pessoal")
    conferir("ESTADO" in nomes_permitidos,
             "ESTADO aparece: decisão consciente, registrada no comentário "
             "de COLUNAS_PERMITIDAS, não um esquecimento novo")
    # E CONTINUAM FORA DA LISTA DE OMISSÃO: se algum dia entrarem lá por
    # engano, o aviso "esta tela não mostra dado pessoal" passaria a citar
    # uma coluna que a tabela também mostra, o que seria uma contradição na
    # própria tela.
    if omitidas:
        nomes_omitidos = re.findall(r'"([^"]+)"', omitidas.group(1))
        conferir("AGENTE" not in nomes_omitidos and "ESTADO" not in nomes_omitidos,
                 "e nenhuma das duas está (também) na lista de omitidas",
                 str(nomes_omitidos))

    print()
    print("--- 5. a escolha é por lista de permissão, não de bloqueio ---")
    # Se um dia alguém inverter a lógica, a tela passa a mostrar coluna nova da
    # planilha sozinha, inclusive coluna de dado pessoal criada depois.
    conferir("COLUNAS_PERMITIDAS" in fonte and "c in por_nome_limpo" in fonte,
             "a tabela é montada a partir das colunas permitidas")
    conferir("filtrada[visiveis]" in fonte,
             "e a tabela desenhada usa só essas colunas",
             "mostrar filtrada inteira exporia tudo o que a planilha tem")
    # A TABELA TINHA UMA COLUNA NOSSA (o contrato Netlex), REMOVIDA em
    # 14/09/2026 junto com o resto do Netlex nesta tela. Hoje `para_mostrar` é
    # só `filtrada[visiveis]`, sem nada acrescentado; esta conferência garante
    # que isso não volta a crescer sem ninguém perceber.
    acrescentadas = re.findall(r"para_mostrar\[([^\]]+)\]\s*=", fonte)
    conferir(not acrescentadas,
             "nenhuma coluna é acrescentada à tabela além das permitidas",
             str(acrescentadas))

    print()
    print("--- 6. o identificador da planilha vem de arquivo, não do código ---")
    # A regra do projeto: trocar de planilha é trocar o conteúdo de um arquivo.
    # Identificador fixo no código é o que faz alguém apontar para produção sem
    # perceber.
    ids_no_codigo = re.findall(r'["\'][0-9A-Za-z_\-]{40,}["\']', fonte)
    conferir(not ids_no_codigo,
             "não há identificador de planilha escrito no código",
             str(ids_no_codigo)[:120])
    # O NOME DO ARQUIVO MUDOU EM 23/09/2026, e não por acaso: esta tela lia o
    # MESMO arquivo que fluxo_downloads.ARQUIVO_CADASTRO_ID usa para a trava
    # de criar pasta (impedimento_para_criar_pasta). Apontar esse arquivo
    # para uma cópia de teste, pra testar "Adicionar" sem gravar na Dados_influ
    # real, deixou o download real cego para os 208 influenciadores de
    # verdade por alguns minutos: a trava passou a achar que NENHUM @ estava
    # cadastrado. O arquivo próprio existe para esta tela poder apontar pra
    # onde quiser sem arriscar aquele portão de segurança de novo.
    conferir("ARQUIVO_ID" in fonte and "cadastro_planilha_id_tela.txt" in fonte,
             "o identificador é lido de cadastro_planilha_id_tela.txt, "
             "arquivo PRÓPRIO desta tela")
    conferir("cadastro_planilha_id.txt" not in fonte,
             "e não é mais o arquivo que o download real também usa",
             "esse era o arquivo compartilhado que causou o incidente")

    print()
    print("--- 6b. a escrita nunca mira a planilha real, só a cópia espelhada (23/09/2026) ---")
    # A tela lê a real (permitido) e espelha numa cópia (nossa) antes de
    # decidir qual id é "planilha". As três escritas usam essa variável, e
    # ela precisa vir da cópia, nunca do identificador real.
    conferir("ARQUIVO_ID_COPIA_TESTE" in fonte and "cadastro_planilha_id_copia_teste.txt" in fonte,
             "existe um arquivo de identificador PRÓPRIO para a cópia de teste")
    conferir("cadastro.espelhar_cadastro_para_teste" in fonte,
             "a tela chama cadastro.espelhar_cadastro_para_teste antes de ler")
    conferir(re.search(r"planilha\s*=\s*_planilha_copia\b", fonte) is not None,
             "a variável \"planilha\", usada por Adicionar/Corrigir/Excluir, "
             "vem da cópia, não da real")

    print()
    print("--- 7. a página exige login por conta própria ---")
    conferir("acesso.exigir_login()" in fonte,
             "chama exigir_login",
             "é rota própria do Streamlit, alcançável sem o painel")
    # E a ordem importa: exigir antes de ler a planilha do Marketing.
    pos_login = fonte.find("acesso.exigir_login()")
    pos_leitura = fonte.find("def carregar")
    conferir(pos_login != -1 and pos_login < pos_leitura,
             "e exige login ANTES de definir a leitura da planilha")

    print()
    print("--- 8. a página está declarada na navegação ---")
    painel = open(os.path.join(BASE, "painel.py"), encoding="utf-8").read()
    conferir("4_Cadastro_de_Influenciadores.py" in painel,
             "o painel.py declara a aba de Cadastro",
             "sem isso ela só apareceria pelo menu automático")
    # E ela fica na seção de consulta, não no fluxo do dia (03/09/2026).
    conferir('"Consulta"' in painel,
             "e a declara na seção de Consulta",
             "a lista corrida misturava passo do dia com tela de consulta")
    conferir(painel.find('"Fluxo do dia"') < painel.find('"Consulta"'),
             "com o fluxo do dia antes da consulta")

    print()
    print("--- 9. o identificador é lido apesar da marca invisível (BOM) ---")
    # ACHADO NO PRIMEIRO USO DESTA TELA, em 31/08/2026. O arquivo do
    # identificador tinha sido criado pelo PowerShell, que grava uma marca
    # invisível no começo. O Python entregou essa marca como parte do texto, o
    # `.strip()` não a removeu (não é espaço em branco), e o endereço saiu com
    # `%EF%BB%BF` na frente do identificador. O Google respondeu 404 e a
    # mensagem na tela sugeria falta de permissão, que era a pista errada.
    #
    # O projeto JÁ tinha aprendido isso em 30/08, e está escrito em
    # baixador_local/baixador.py, mas a lição não havia chegado aos leitores de
    # identificador.
    conferir('encoding="utf-8-sig"' in fonte,
             "a leitura do identificador usa utf-8-sig",
             "com utf-8 puro, arquivo gravado no Windows quebra a leitura")

    # A prova de verdade: rodar a função com um arquivo que TEM a marca.
    import importlib.util
    import tempfile

    spec_fonte = re.search(r"def _identificador\(\):.*?(?=\ndef |\n@)", fonte, re.S)
    conferir(bool(spec_fonte), "consegui isolar a função _identificador")
    if spec_fonte:
        pasta = tempfile.mkdtemp(prefix="id_com_bom_")
        caminho = os.path.join(pasta, "cadastro_planilha_id.txt")
        esperado = "1T4xV2oSDoae6Ahe4nNLIoI2CrqpZtZtmSRBna7y3fG0"
        # utf-8-sig na ESCRITA é o que produz a marca, igual ao PowerShell.
        with open(caminho, "w", encoding="utf-8-sig") as f:
            f.write(esperado + "\n")

        ambiente = {"ARQUIVO_ID": caminho, "os": os}
        exec(compile(spec_fonte.group(0), "pedaco", "exec"), ambiente)
        lido = ambiente["_identificador"]()
        conferir(lido == esperado,
                 "identificador com marca invisível é lido limpo",
                 f"leu {lido!r}, esperava {esperado!r}")

        # E o caso normal continua funcionando.
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(esperado)
        conferir(ambiente["_identificador"]() == esperado,
                 "e arquivo sem a marca continua sendo lido")

        # Arquivo vazio devolve None, para a tela poder explicar em vez de
        # tentar ler uma planilha chamada "".
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("   \n")
        conferir(ambiente["_identificador"]() is None,
                 "arquivo vazio devolve nada, e a tela explica o que falta")

    print()
    print("--- 10. a leitura de data não chuta vencido ---")
    # Chutar "vencido" quando não dá para ler a data criaria alerta falso sobre
    # contrato, que é o pior erro possível nesta tela.
    conferir("return None" in fonte and "_ler_data" in fonte,
             "a leitura de data devolve None quando não consegue ler")
    conferir("NUNCA como vencido" in fonte,
             "e o motivo está escrito no código, para não ser desfeito depois")

    print()
    print("--- 11. a escrita recusa coluna de dado pessoal, por conta própria ---")
    import cadastro
    for coluna_pessoal in PESSOAIS:
        try:
            cadastro.corrigir_campo_no_cadastro(
                "planilha_de_mentira", "Dados_influ", 2, coluna_pessoal,
                ["INFLU", coluna_pessoal], "valor novo", nomes_permitidos)
        except ValueError:
            conferir(True, f"recusa corrigir {coluna_pessoal}")
        except Exception as e:
            conferir(False, f"recusa corrigir {coluna_pessoal}",
                     f"levantou {type(e).__name__} em vez de ValueError")
        else:
            conferir(False, f"recusa corrigir {coluna_pessoal}",
                     "não levantou nada, e deveria recusar antes de tocar a planilha")

    print()
    print("--- 12. escreve e registra quando muda, e não faz nada quando não muda ---")
    import types
    import fluxo_downloads as fluxo

    escritas = []
    lidas = {"valor": "valor antigo"}

    class SheetsFalso:
        @staticmethod
        def ler_coluna(planilha, aba, coluna, linhas):
            return {linhas[0]: lidas["valor"]}

        @staticmethod
        def escrever_lote(planilha, aba, coluna, atualizacoes):
            escritas.append((coluna, atualizacoes))

    falso = types.ModuleType("sheets_client")
    falso.ler_coluna = SheetsFalso.ler_coluna
    falso.escrever_lote = SheetsFalso.escrever_lote
    sys.modules["sheets_client"] = falso

    cabecalho_de_mentira = ["INFLU", "STATUS", "ESCOPO"]
    try:
        resultado = cadastro.corrigir_campo_no_cadastro(
            "planilha_de_mentira", "Dados_influ", 5, "ESCOPO",
            cabecalho_de_mentira, "valor novo", nomes_permitidos,
            quem="coordenadora@empresa.com")
        conferir(resultado == ("valor antigo", "valor novo"),
                 "devolve o valor antigo e o novo", str(resultado))
        conferir(len(escritas) == 1, "escreveu uma vez na planilha", str(escritas))
        conferir(escritas[0] == ("C", [(5, "valor novo")]),
                 "na coluna e linha certas", str(escritas[0]))

        registro = fluxo.ler_log()
        correcoes = [l for l in registro if l.get("estagio") == "correcao_cadastro"]
        conferir(bool(correcoes), "a correção ficou no log geral")
        if correcoes:
            conferir("coordenadora@empresa.com" in correcoes[-1].get("status", ""),
                     "o log diz quem corrigiu", correcoes[-1].get("status", ""))

        # A fake `ler_coluna` sempre devolve "valor antigo", então pedir esse
        # MESMO valor de novo é o caso "nada mudou" (a fake não guarda estado
        # do que foi escrito antes, só simula o que está na célula agora).
        escritas.clear()
        resultado_igual = cadastro.corrigir_campo_no_cadastro(
            "planilha_de_mentira", "Dados_influ", 5, "ESCOPO",
            cabecalho_de_mentira, "valor antigo", nomes_permitidos,
            quem="coordenadora@empresa.com")
        conferir(resultado_igual is None,
                 "corrigir para o mesmo valor não escreve nada", str(resultado_igual))
        conferir(len(escritas) == 0,
                 "e não gerou escrita nenhuma na planilha", str(escritas))
    finally:
        sys.modules.pop("sheets_client", None)

    print()
    print("--- 13. adicionar e excluir linha: recusa dado pessoal, e chamam o certo ---")
    for coluna_pessoal in PESSOAIS:
        try:
            cadastro.adicionar_linha_no_cadastro(
                "planilha_de_mentira", "Dados_influ", ["INFLU", coluna_pessoal],
                {coluna_pessoal: "valor"}, nomes_permitidos)
        except ValueError:
            conferir(True, f"adicionar recusa {coluna_pessoal}")
        else:
            conferir(False, f"adicionar recusa {coluna_pessoal}",
                     "não levantou nada, e deveria recusar antes de tocar a planilha")

    apagadas = []

    # DUBLÊ REESCRITO EM 23/09/2026, junto com a correção do defeito que ele
    # não tinha como pegar: `adicionar_linha_no_cadastro` deixou de chamar
    # `sheets_client.adicionar_linhas` (o append da API, que desloca a linha
    # uma coluna pro lado quando a coluna A está vazia, como está na Dados_influ
    # real — provado com escrita de verdade numa cópia de teste, não só
    # deduzido) e passou a gravar em POSIÇÃO EXPLÍCITA, do mesmo jeito que
    # fluxo_downloads.registrar_na_monitoramento já fazia por ter passado pelo
    # mesmo problema antes. Este dublê simula essa leitura (quantas linhas já
    # existem) e essa escrita (em qual linha exata), para o teste continuar
    # provando o CAMINHO DE VERDADE, e não um caminho que o código já abandonou.
    escritas_explicitas = []

    class _ValoresFalso:
        def get(self, spreadsheetId, range):
            self._eh_leitura_de_contagem = True
            return self

        def update(self, spreadsheetId, range, valueInputOption, body):
            escritas_explicitas.append((range, body["values"]))
            return self

        def execute(self):
            # A "planilha" de mentira já tem 5 linhas de dado (linhas 2 a 6),
            # então a próxima entra na linha 7. Simula só o que a leitura de
            # contagem precisa: uma lista com 5 elementos, o conteúdo não importa.
            return {"values": [[""]] * 5}

    class _SpreadsheetsFalso:
        def values(self):
            return _ValoresFalso()

    class _ServiceFalso:
        def spreadsheets(self):
            return _SpreadsheetsFalso()

    falso2 = types.ModuleType("sheets_client")
    falso2.get_service = lambda: _ServiceFalso()
    falso2.executar = lambda fn, **kw: fn()
    falso2._neutralizar_formula = lambda v: v
    falso2.apagar_linhas = lambda planilha, aba, linhas: apagadas.append(linhas)
    sys.modules["sheets_client"] = falso2
    try:
        cadastro.adicionar_linha_no_cadastro(
            "planilha_de_mentira", "Dados_influ", ["INFLU", "STATUS", "ESCOPO"],
            {"INFLU": "novoinflu", "STATUS": "ATIVO"}, nomes_permitidos,
            quem="coordenadora@empresa.com")
        conferir(len(escritas_explicitas) == 1,
                 "adicionar escreveu uma vez, em posição explícita",
                 str(escritas_explicitas))
        conferir(escritas_explicitas == [("'Dados_influ'!A7:C7", [["novoinflu", "ATIVO", ""]])],
                 "na linha certa (5 já existiam, entra na 7), colunas na ordem do "
                 "cabeçalho, não preenchidas vazias",
                 str(escritas_explicitas))
        conferir("sheets_client.adicionar_linhas(" not in
                 inspect.getsource(cadastro.adicionar_linha_no_cadastro),
                 "e o caminho vulnerável (append) não é mais CHAMADO aqui",
                 "o nome pode continuar citado no comentário, explicando por que "
                 "não se usa mais; o que não pode voltar é a CHAMADA")
        registro = fluxo.ler_log()
        novos = [l for l in registro if l.get("estagio") == "cadastro_novo"]
        conferir(bool(novos), "a inclusão ficou no log geral")

        cadastro.excluir_linha_no_cadastro(
            "planilha_de_mentira", "Dados_influ", 7, identificacao="@novoinflu",
            quem="coordenadora@empresa.com")
        conferir(apagadas == [[7]], "excluir chamou apagar_linhas na linha certa",
                 str(apagadas))
        registro = fluxo.ler_log()
        exclusoes = [l for l in registro if l.get("estagio") == "cadastro_exclusao"]
        conferir(bool(exclusoes), "a exclusão ficou no log geral")
    finally:
        sys.modules.pop("sheets_client", None)

    print()
    print("--- 14. espelhar_cadastro_para_teste: só lê da real, só escreve na cópia (23/09/2026) ---")
    # Prova a peça que resolveu o "falta um botão" de 23/09/2026: a tela não
    # pode escrever na Dados_influ real (a conta só tem leitura), e Corrigir/
    # Excluir apontam linha por número, então leitura e escrita precisam vir
    # da MESMA planilha. A saída foi espelhar a real numa cópia antes de abrir
    # a tela. Este teste prova que a função só LÊ do id real e só LIMPA/ESCREVE
    # no id da cópia, nunca o contrário.
    chamadas_leitura = []
    chamadas_limpeza = []
    chamadas_escrita = []

    class _ValoresEspelho:
        def get(self, spreadsheetId, range):
            chamadas_leitura.append((spreadsheetId, range))
            return self

        def clear(self, spreadsheetId, range, body):
            chamadas_limpeza.append((spreadsheetId, range))
            return self

        def update(self, spreadsheetId, range, valueInputOption, body):
            chamadas_escrita.append((spreadsheetId, range, body["values"]))
            return self

        def execute(self):
            return {"values": [
                ["INFLU", "STATUS", "ESCOPO"],
                ["@um", "ATIVO", "2 posts"],
                ["@dois", "INATIVO", "1 post"],
            ]}

    class _SpreadsheetsEspelho:
        def values(self):
            return _ValoresEspelho()

    class _ServiceEspelho:
        def spreadsheets(self):
            return _SpreadsheetsEspelho()

    falso3 = types.ModuleType("sheets_client")
    falso3.get_service = lambda: _ServiceEspelho()
    falso3.executar = lambda fn, **kw: fn()
    falso3._neutralizar_formula = lambda v: v
    sys.modules["sheets_client"] = falso3
    try:
        quantas = cadastro.espelhar_cadastro_para_teste("id_real", "id_copia", "Dados_influ")
        conferir(quantas == 2, "devolve quantas linhas de dado foram copiadas", quantas)
        conferir(chamadas_leitura == [("id_real", "'Dados_influ'!A1:T")],
                 "só lê da planilha real", str(chamadas_leitura))
        conferir(bool(chamadas_limpeza) and all(c[0] == "id_copia" for c in chamadas_limpeza),
                 "só limpa a cópia, nunca a real", str(chamadas_limpeza))
        conferir(bool(chamadas_escrita) and all(c[0] == "id_copia" for c in chamadas_escrita),
                 "só escreve na cópia, nunca a real", str(chamadas_escrita))
        conferir(chamadas_escrita[0][2][0] == ["INFLU", "STATUS", "ESCOPO"],
                 "o cabeçalho espelhado é o mesmo da real", str(chamadas_escrita))
        conferir(not any(c[0] == "id_real" for c in chamadas_limpeza + chamadas_escrita),
                 "em nenhum momento a real é alvo de limpeza ou escrita")
    finally:
        sys.modules.pop("sheets_client", None)

    print()
    print("--- 15. o handle nunca dobra o @, em lugar nenhum da tela (23/09/2026) ---")
    # Achado ao vivo: a tela de Excluir mostrava "@@auditor" porque tinha o
    # mesmo f"@{...}" cru que já tinha sido corrigido em Corrigir (15/09),
    # sem passar pela mesma checagem. A correção virou função única
    # (_com_arroba), pra não existir um segundo lugar pra esquecer de novo.
    conferir("def _com_arroba(" in fonte,
             "existe uma função só para isso, e não uma conta repetida em cada tela")
    conferir(fonte.count("_com_arroba(") >= 5,
             "usada em pelo menos 5 lugares (Corrigir, Adicionar, e as três de Excluir)",
             f"achei {fonte.count('_com_arroba(')}")
    # NENHUM DOS PONTOS QUE JÁ DOBROU O @ PODE VOLTAR À FORMA CRUA. Não vale
    # banir a string f"@{" inteira: ela aparece de propósito dentro da
    # própria _com_arroba (o fallback seguro, já protegido pelo startswith)
    # e no comentário que explica o incidente.
    conferir('f"@{filtrada' not in fonte and 'f"@{_handle_excluido' not in fonte
             and "f\"@{_valores_novo" not in fonte,
             "os pontos que dobravam o @ (Excluir e o sucesso do Adicionar) "
             "não voltaram à forma crua")

    print()
    print("--- 16. nenhuma lista de OPCOES_DO_CAMPO trava quem digita algo novo (23/09/2026) ---")
    # O auditor perguntou se AGENTE é padrão fixo ou pode mudar. Resposta:
    # nenhuma lista aqui é garantida para sempre, então toda select ganha uma
    # saída pra digitar (OPCAO_OUTRO), tanto em Adicionar quanto em Corrigir.
    conferir("OPCAO_OUTRO" in fonte, "existe a opção de digitar fora da lista")
    conferir(fonte.count("OPCAO_OUTRO]") >= 2,
             "ela entra nas duas listas de opção (Adicionar e Corrigir)",
             f"achei {fonte.count('OPCAO_OUTRO]')}")

    print()
    print("--- 17. o botão Atualizar agora limpa as duas caches (23/09/2026) ---")
    # Pedido do auditor: "como nas outras" (Monitoramento e Financeiro já
    # tinham). Aqui precisa limpar DUAS, não uma: `carregar` (leitura da
    # cópia) e `_espelhar` (o espelhamento em si). Só a primeira mostraria a
    # cópia de novo, sem reespelhar da real.
    pos_botao = fonte.find('"Atualizar agora"')
    conferir(pos_botao != -1, "o botão Atualizar agora existe")
    trecho_botao = fonte[pos_botao:pos_botao + 300]
    conferir("carregar.clear()" in trecho_botao and "_espelhar.clear()" in trecho_botao,
             "e limpa as duas caches, não só a leitura", trecho_botao[:200])


if __name__ == "__main__":
    print("=" * 74)
    print("  Aba de Cadastro: só leitura, e sem dado pessoal na tela")
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
