# -*- coding: utf-8 -*-
"""
O motor de escrita controlada no cadastro (Dados_influ), separado da tela.

POR QUE ESTE ARQUIVO EXISTE (14/09/2026)

Até aqui, `pages\\4_Cadastro_de_Influenciadores.py` era só leitura, com teste
próprio provando isso (`testes\\teste_cadastro_somente_leitura.py`). Pedido do
auditor: dar um jeito de corrigir um campo do cadastro de dentro do programa,
"a ideia é não se usar a planilha diretamente ou reduzir o uso". Escrever
direto de dentro da tela misturaria motor com camada visual, o mesmo padrão
que este projeto já evita em outros lugares (`escopo_e_entrega.py`,
`pipeline_influenciadores.py`), e permite testar sem subir o Streamlit.

O MODELO É `fluxo_downloads.corrigir_ciclo_na_monitoramento`: lê o valor
atual da célula bem antes de gravar, não escreve se o valor novo já é igual
ao atual (evita registrar uma troca que não houve), e grava o log de quem
mudou o quê. `sheets_client.escrever_lote` já neutraliza texto que
começaria fórmula, então não precisa repetir isso aqui.

A SEGUNDA BARREIRA CONTRA DADO PESSOAL. A tela já esconde as colunas de
`COLUNAS_OMITIDAS_POR_PRIVACIDADE` da exibição, mas esta função recebe a
lista de colunas permitidas e recusa por conta própria qualquer coluna fora
dela, para a proteção não depender só do que a tela decide mostrar."""
import os


def corrigir_campo_no_cadastro(planilha_id, aba, numero_linha, nome_coluna,
                               cabecalho, valor_novo, colunas_permitidas,
                               quem=None):
    """Corrige UMA célula da planilha de cadastro, célula por célula.

    `cabecalho` é a lista de títulos da planilha, na ordem das colunas (a
    mesma que `carregar()` já lê na tela). `colunas_permitidas` é a lista de
    permissão da tela (nunca as de `COLUNAS_OMITIDAS_POR_PRIVACIDADE`).

    Devolve (valor_antigo, valor_novo), ou None se não havia o que fazer
    (coluna não encontrada, ou o valor novo já é o valor atual).

    Levanta ValueError se `nome_coluna` não estiver em `colunas_permitidas`:
    quem chama já devia ter filtrado isso na tela, mas esta função não
    confia só nisso."""
    if nome_coluna not in colunas_permitidas:
        raise ValueError(
            f"\"{nome_coluna}\" não está entre as colunas que esta função "
            f"pode corrigir.")

    import sheets_client
    import fluxo_downloads as fluxo

    titulos_limpos = [str(c).strip() for c in cabecalho]
    if nome_coluna not in titulos_limpos:
        return None
    indice = titulos_limpos.index(nome_coluna)
    letra = fluxo.letra_da_coluna(indice + 1)

    linha = int(numero_linha)
    valor_novo = str(valor_novo or "").strip()
    atual = sheets_client.ler_coluna(planilha_id, aba, letra, [linha])
    valor_antigo = str(atual.get(linha) or "").strip()
    if valor_antigo == valor_novo:
        # Nada a fazer, e dizer isso é melhor que gravar o mesmo valor e
        # registrar uma troca que não houve (mesma regra de
        # corrigir_ciclo_na_monitoramento).
        return None

    sheets_client.escrever_lote(planilha_id, aba, letra, [(linha, valor_novo)])

    from datetime import datetime
    fluxo.gravar_log([dict(
        quando=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        estagio="correcao_cadastro",
        origem=f"Cadastro linha {linha}, coluna {nome_coluna}",
        handle="", data_video="", ciclo="", destino="",
        status=(f"CADASTRO CORRIGIDO ({nome_coluna}) de "
                f"\"{valor_antigo or '(vazio)'}\" para \"{valor_novo}\" "
                f"por {quem or 'não identificado'}"),
        origem_ciclo="",
        quem=str(quem or ""),
    )])
    return valor_antigo, valor_novo


def adicionar_linha_no_cadastro(planilha_id, aba, cabecalho, valores_por_coluna,
                                colunas_permitidas, quem=None):
    """Acrescenta um influenciador novo na Dados_influ (15/09/2026).

    `valores_por_coluna` é um dict {nome_coluna: valor}, só com as colunas que
    a pessoa preencheu; o resto da linha nasce vazio. Mesma segunda barreira
    de `corrigir_campo_no_cadastro`: recusa por conta própria qualquer chave
    fora de `colunas_permitidas`, mesmo que a tela já limite o formulário a
    elas.

    NÃO USA `sheets_client.adicionar_linhas`, e a mudança é de 23/09/2026,
    achada testando: a coluna A da Dados_influ é vazia no cabeçalho (é assim
    na planilha real do Marketing), e o Google entende que a tabela começa na
    B, empurrando a linha inteira uma coluna pro lado. Toda linha entraria
    com @handle na coluna de ID_CONTA, e o resto deslocado atrás. Provado com
    escrita real numa cópia de teste antes de corrigir, não só lido no código:
    a resposta da própria API confirmou `updatedRange: B2:U2` para um pedido
    de `A:T`.

    ESTE MESMO DEFEITO JÁ TINHA ACONTECIDO ANTES, na Monitoramento, que
    também tem a coluna A vazia (ver o comentário grande em
    fluxo_downloads.registrar_na_monitoramento: "já foi tentado e revertido").
    A correção nunca tinha chegado até aqui, porque esta função nasceu depois,
    em 15/09, e ninguém religou os dois achados.

    A SAÍDA É A MESMA DE LÁ: ler quantas linhas já existem e gravar em
    POSIÇÃO EXPLÍCITA (`values().update` numa faixa com número de linha),
    em vez de pedir para o Google decidir onde a tabela começa. Fica uma
    janela pequena de corrida (duas pessoas cadastrando ao mesmo tempo
    poderiam mirar a mesma linha), aceitável aqui porque cadastrar
    influenciador é ação manual e rara, bem diferente do volume de downloads
    que levou a Monitoramento a precisar de reler-e-tentar-de-novo."""
    for nome_coluna in valores_por_coluna:
        if nome_coluna not in colunas_permitidas:
            raise ValueError(
                f"\"{nome_coluna}\" não está entre as colunas que esta função "
                f"pode preencher.")

    import sheets_client
    import fluxo_downloads as fluxo
    from datetime import datetime

    titulos_limpos = [str(c).strip() for c in cabecalho]
    linha = [str(valores_por_coluna.get(c, "") or "").strip() for c in titulos_limpos]
    ultima_letra = fluxo.letra_da_coluna(len(titulos_limpos))
    atuais = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
        spreadsheetId=planilha_id, range=f"'{aba}'!A2:{ultima_letra}20000").execute()).get("values", [])
    numero_linha = len(atuais) + 2
    sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().update(
        spreadsheetId=planilha_id,
        range=f"'{aba}'!A{numero_linha}:{ultima_letra}{numero_linha}",
        valueInputOption="USER_ENTERED",
        body={"values": [[sheets_client._neutralizar_formula(v) for v in linha]]},
    ).execute())

    resumo = ", ".join(f"{k}=\"{v}\"" for k, v in valores_por_coluna.items() if str(v or "").strip())
    fluxo.gravar_log([dict(
        quando=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        estagio="cadastro_novo",
        origem="Cadastro, linha nova",
        handle="", data_video="", ciclo="", destino="",
        status=f"CADASTRO: linha nova adicionada por {quem or 'não identificado'}: {resumo}",
        origem_ciclo="",
        quem=str(quem or ""),
    )])
    return True


def espelhar_cadastro_para_teste(planilha_real_id, planilha_teste_id, aba,
                                 faixa="A1:T"):
    """Copia a Dados_influ real, linha por linha, para a cópia de teste da tela (23/09/2026).

    POR QUE ISTO EXISTE

    A conta do programa só tem permissão de LEITURA na Dados_influ real
    (confirmado consultando `capabilities.canEdit`, que voltou False), e por
    regra do projeto a escrita nunca pode ir para lá. Até aqui a saída tinha
    sido dar à tela uma cópia de teste PRÓPRIA, vazia, pra testar Adicionar/
    Corrigir/Excluir sem risco.

    Só que Corrigir e Excluir apontam a linha por NÚMERO (a posição na tabela
    que a tela mostra), e número de linha só quer dizer a mesma coisa nos
    dois lados se leitura e escrita vierem da MESMA planilha, com as mesmas
    linhas, na mesma ordem. Uma cópia vazia serve para Adicionar (que só
    acrescenta), mas não para Corrigir/Excluir uma linha que existe na real e
    não existe na cópia. E apontar leitura e escrita para planilhas
    diferentes foi exatamente o desenho que causou o incidente de
    23/09/2026 registrado em `ARQUIVO_ID` da tela (a trava de criar pasta do
    download ficou cega por apontar pra cópia errada).

    A SAÍDA: antes de abrir a tela, o programa lê a Dados_influ real (leitura
    é permitida) e regrava o conteúdo inteiro na cópia de teste (que o
    programa é dono, pode escrever). A tela então lê e escreve SEMPRE na
    cópia, nunca na real, e como a cópia acabou de ser espelhada, os números
    de linha coincidem. A Dados_influ real nunca recebe escrita, aqui ou em
    qualquer outra função deste arquivo.

    Limpa a cópia inteira antes de regravar (não só as linhas que existem
    hoje na real): sem isso, uma linha excluída na real continuaria
    "fantasma" na cópia depois do espelhamento.

    Devolve quantas linhas de dado foram copiadas (sem contar o cabeçalho)."""
    import sheets_client

    resp = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha_real_id, range=f"'{aba}'!{faixa}",
        ).execute()
    )
    valores = resp.get("values", [])

    sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().clear(
            spreadsheetId=planilha_teste_id, range=f"'{aba}'!{faixa}",
            body={},
        ).execute()
    )
    if valores:
        neutralizadas = [[sheets_client._neutralizar_formula(v) for v in linha]
                         for linha in valores]
        sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().update(
                spreadsheetId=planilha_teste_id, range=f"'{aba}'!A1",
                valueInputOption="USER_ENTERED", body={"values": neutralizadas},
            ).execute()
        )
    return max(len(valores) - 1, 0)


def excluir_linha_no_cadastro(planilha_id, aba, numero_linha, identificacao="", quem=None):
    """Apaga a linha inteira do cadastro (15/09/2026).

    Não tem desfazer por este programa: a linha some da planilha (fica só no
    histórico de versões do próprio Google Sheets). Por isso a tela exige
    confirmação explícita antes de chamar esta função; ela mesma não confirma
    nada, só executa e registra."""
    import sheets_client
    import fluxo_downloads as fluxo
    from datetime import datetime

    sheets_client.apagar_linhas(planilha_id, aba, [int(numero_linha)])

    fluxo.gravar_log([dict(
        quando=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        estagio="cadastro_exclusao",
        origem=f"Cadastro linha {numero_linha}",
        handle="", data_video="", ciclo="", destino="",
        status=(f"CADASTRO: linha {numero_linha} ({identificacao}) excluída "
                f"por {quem or 'não identificado'}"),
        origem_ciclo="",
        quem=str(quem or ""),
    )])
    return True
