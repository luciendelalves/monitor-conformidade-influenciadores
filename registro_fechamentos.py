# -*- coding: utf-8 -*-
"""
O registro dos ciclos fechados, em planilha própria.

POR QUE ESTE ARQUIVO EXISTE (05/09/2026)

O fechamento de ciclo era gravado só num CSV local, dentro de
`teste_watch_folder`. O código já reconhecia a dívida ("o certo é isso virar uma
aba na planilha, para o Marketing e o Financeiro lerem sem depender desta
máquina"), e o auditor cobrou ao perguntar onde a justificativa ia parar: "essa
justificativa vai pra algum lugar na planilha ou só na mensagem do whatsapp?".

Ia para o texto do WhatsApp e para o CSV local. Mensagem de WhatsApp não é
registro de auditoria: não dá para filtrar, contar nem auditar depois. E o CSV
local vive numa máquina só, o que deixou de ser aceitável no momento em que uma
pessoa do Marketing passou a testar o programa na máquina dela: as
justificativas dela ficariam invisíveis para a auditoria, e as da auditoria
invisíveis para ela.

POR QUE PLANILHA SEPARADA, E NÃO UMA ABA NA MONITORAMENTO

Decidido com o auditor. Quatro razões, e a terceira é a que resolve na prática:

  1. GRÃO DIFERENTE. A Monitoramento é uma linha por post; isto é uma linha por
     ciclo fechado. Misturar grãos no mesmo arquivo é o que deixa planilha
     confusa para quem lê.
  2. DONO DIFERENTE. A Monitoramento é dado operacional do Marketing; isto é
     conclusão da auditoria, com justificativa e nome do achado. Auditoria não
     escreve conclusão dentro do arquivo operacional de quem ela audita.
  3. PÚBLICO DIFERENTE. O Financeiro precisa LER os fechamentos. Dar a
     Monitoramento a eles exporia todo o dado por post que não lhes interessa.
     Planilha separada se compartilha só leitura, e resolvido.
  4. SOBREVIVÊNCIA. A Monitoramento em uso é cópia de teste, que um dia será
     substituída. O registro de fechamento não pode morrer com ela.

O CSV LOCAL CONTINUA, E ISSO NÃO É REDUNDÂNCIA À TOA. Ele é a rede: se a
planilha não estiver configurada, ou se a escrita falhar (rede fora, token
expirado), o fechamento não pode se perder. Grava-se nos dois, e a tela diz
quando só um deu certo. Perder registro de auditoria por falha de rede seria
pior que ter o dado em dois lugares.

O QUE ESTE ARQUIVO NÃO FAZ: não apaga nem altera linha nenhuma. Só acrescenta.
Fechamento é fato datado; corrigir um fechamento é registrar outro, não reescrever
o anterior.
"""
import os

PASTA = os.path.dirname(os.path.abspath(__file__))
ABA = "Fechamentos"

# Segue a convenção dos outros identificadores do programa: arquivo de texto
# dentro de teste_watch_folder, lido por fluxo.ler_identificador. Assim quem
# instala numa máquina nova recebe este id junto dos outros quatro, pelo mesmo
# canal, sem passo especial.
NOME_DO_ARQUIVO_ID = "fechamentos_planilha_id.txt"


def arquivo_id():
    import fluxo_downloads as fluxo
    return os.path.join(fluxo.PASTA_TESTE, NOME_DO_ARQUIVO_ID)


def planilha_id():
    """O identificador da planilha de fechamentos, ou vazio se não configurada."""
    import fluxo_downloads as fluxo
    return fluxo.ler_identificador(arquivo_id())


def garantir_cabecalho(planilha, campos, aba=ABA):
    """Escreve os títulos que ainda faltam na primeira linha.

    NUNCA sobrescreve título existente: se alguém renomeou uma coluna, a
    escolha da pessoa manda. Mesma regra de garantir_cabecalhos_automacao.

    PREENCHE CÉLULA POR CÉLULA, E NÃO A LINHA INTEIRA DE UMA VEZ (11/09/2026).
    Antes, bastava a linha 1 ter qualquer coisa para a função desistir dela
    toda. A lista de campos cresce com o tempo (foi o que aconteceu ao entrar
    `cronograma_calendario`), e numa planilha que já tinha cabeçalho a coluna
    nova chegava SEM TÍTULO: dado gravado embaixo de célula vazia, que quem
    abre a planilha não tem como interpretar. Agora cada título só é escrito se
    a célula dele estiver vazia, o que mantém a regra de não sobrescrever e
    resolve o crescimento.

    `aba` entrou em 14/09/2026, para o Financeiro gravar um histórico de
    entregas numa aba própria ("Historico_Entregas", renomeada de
    "Notas_Financeiro" em 16/09/2026 quando o registro deixou de ser só uma
    nota e passou a guardar a fotografia inteira do fechamento), na mesma
    planilha de fechamentos, sem misturar com o grão de "ciclo fechado"
    desta aba. Sem passar nada, continua sendo "Fechamentos", igual sempre foi.

    CRIA A ABA QUANDO ELA NÃO EXISTE (16/09/2026), e isso fecha um buraco que
    estava escrito como pendência desde 07/09 e nunca tinha doído: "o módulo
    espera a aba existir e NÃO a cria. Numa planilha nova, toda gravação falha
    e cai em silêncio para o arquivo local". Doeu ao povoar a aba nova de
    histórico: o Google responde 400 "Unable to parse range" ao LER uma aba
    inexistente, `gravar` engolia esse erro e devolvia False, e quem chamava
    tinha acabado de dizer "registrado" para a pessoa. Agora a aba nasce na
    primeira gravação, que é o comportamento que todo mundo já supunha.

    Devolve quantos títulos foram escritos."""
    import sheets_client
    letra_fim = _letra(len(campos))
    faixa = f"'{aba}'!A1:{letra_fim}1"
    try:
        atuais = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha, range=faixa).execute()).get("values", [[]])
    except Exception:
        # NÃO DISTINGUE O MOTIVO DO ERRO DE PROPÓSITO: se a leitura falhou por
        # aba inexistente, criar resolve; se foi por qualquer outra razão
        # (rede, permissão), a criação falha também e o erro sobe igual, para
        # `gravar` tratar como sempre tratou. Tentar adivinhar a causa pelo
        # texto da mensagem do Google é o tipo de coisa que quebra quando eles
        # mudam a frase.
        _criar_aba(planilha, aba)
        atuais = [[]]
    linha = atuais[0] if atuais else []
    faltando = []
    for posicao, campo in enumerate(campos):
        ja_tem = posicao < len(linha) and str(linha[posicao]).strip()
        if not ja_tem:
            faltando.append((posicao, _titulo(campo, aba)))
    for posicao, titulo in faltando:
        celula = f"'{aba}'!{_letra(posicao + 1)}1"
        sheets_client.executar(
            lambda c=celula, t=titulo:
                sheets_client.get_service().spreadsheets().values().update(
                    spreadsheetId=planilha, range=c,
                    valueInputOption="USER_ENTERED",
                    body={"values": [[t]]}).execute())
    return len(faltando)


def _criar_aba(planilha, aba):
    """Acrescenta uma aba à planilha, já formatada como TEXTO.

    Se a aba já existir (duas gravações ao mesmo tempo, por exemplo), o Google
    recusa com 400 e a exceção sobe: quem chamou já está dentro de um try, e
    tentar de novo seria pior que deixar a segunda gravação falhar e ser
    repetida."""
    import sheets_client
    sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().batchUpdate(
            spreadsheetId=planilha,
            body={"requests": [{"addSheet": {"properties": {"title": aba}}}]},
        ).execute())
    formatar_como_texto(planilha, aba)


def formatar_como_texto(planilha, aba):
    """Faz a aba inteira ser TEXTO, para o Sheets não reinterpretar o que foi
    gravado.

    POR QUE (16/09/2026): "2026-08-16 00:18:57" na coluna QUANDO aparecia como
    `46250,01894`, e o PERÍODO DAS ENTREGAS da aba Fechamentos já vinha
    aparecendo assim como `46273` havia dias. A escrita usa USER_ENTERED (é o
    que faz o apóstrofo do anti-fórmula ficar invisível), e USER_ENTERED
    manda o Sheets INTERPRETAR o que chega: data vira número de série e o
    formato da célula decide como isso aparece. Numa aba de registro nada
    disso ajuda, porque tudo que o programa grava aqui já vem pronto como
    texto. Com a aba formatada como texto, o valor fica exatamente como foi
    escrito, e o anti-fórmula continua funcionando.

    Falha em silêncio de propósito: é cosmético, e não pode derrubar a
    gravação de um registro."""
    import sheets_client
    try:
        meta = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().get(
                spreadsheetId=planilha, fields="sheets.properties").execute())
        alvo = [s["properties"]["sheetId"] for s in meta.get("sheets", [])
                if s["properties"]["title"] == aba]
        if not alvo:
            return False
        sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().batchUpdate(
                spreadsheetId=planilha,
                body={"requests": [{"repeatCell": {
                    "range": {"sheetId": alvo[0]},
                    "cell": {"userEnteredFormat": {
                        "numberFormat": {"type": "TEXT"}}},
                    "fields": "userEnteredFormat.numberFormat",
                }}]}).execute())
        return True
    except Exception:
        return False


def _letra(numero):
    letras = ""
    while numero > 0:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _titulo(campo, aba=ABA):
    """O nome do campo em texto de gente, para quem abrir a planilha.

    `aba` ENTROU EM 16/09/2026: "QUANDO FECHOU"/"QUEM FECHOU" fazem sentido
    na aba Fechamentos, mas mentem na Historico_Entregas, onde a maioria dos
    registros não fecha ciclo nenhum, só confere e às vezes justifica. Sem
    isso, quem abre a planilha nova leria "fechou" onde não houve
    fechamento."""
    if aba != ABA and campo in ("quando", "quem"):
        return {"quando": "QUANDO REGISTROU", "quem": "QUEM REGISTROU"}[campo]
    return {
        "quando": "QUANDO FECHOU",
        "quem": "QUEM FECHOU",
        "influenciador": "INFLUENCIADOR",
        "ciclo": "CICLO",
        "marca": "MARCA",
        "periodo": "PERÍODO DAS ENTREGAS",
        "escopo": "ESCOPO CONTRATADO",
        "entregue": "ENTREGUE",
        "situacao": "SITUAÇÃO DA ENTREGA",
        # "pagamento", "achado" e "justificativa_pagamento" SAÍRAM DAQUI EM
        # 09/09/2026, junto com o rádio que os alimentava (ver
        # pages/3_Financeiro.py). A justificativa de "diferente do escopo"
        # ficou só em "justificativa", sem precisar de coluna própria.
        "justificativa": "JUSTIFICATIVA DA ENTREGA",
        "decisoes": "DECISÕES DE QUEM FECHOU",
        "pecas_reprovadas": "PEÇAS REPROVADAS",
        "pecas_sem_evidencia": "PEÇAS SEM EVIDÊNCIA",
        "pecas_no_limite_da_automacao": "PEÇAS NO LIMITE DA AUTOMAÇÃO",
        "pecas_sem_veredito": "PEÇAS SEM VEREDITO",
        # CONGELA O QUE O CALENDÁRIO DIZIA NO INSTANTE DO FECHAMENTO
        # (11/09/2026). O Calendário é planilha viva de outra área: o auditor
        # apontou que "é bem volátil, sempre pode mudar". Sem congelar, uma
        # edição posterior deles tornaria impossível saber o que a auditoria
        # viu quando concluiu. Gravado sempre, inclusive quando o cronograma
        # NÃO vai para a mensagem, porque é evidência, não é texto de aviso.
        "cronograma_calendario": "CRONOGRAMA NO CALENDÁRIO (no fechamento)",
    }.get(campo, campo.replace("_", " ").upper())


def gravar(registro, campos, aba=ABA):
    """Acrescenta uma linha na planilha de fechamentos (ou, com `aba`
    informado, numa outra aba da mesma planilha).

    Devolve (gravou, motivo). `gravou` False com motivo explicando, em vez de
    levantar erro: quem chama já gravou no CSV local e precisa seguir mostrando
    o texto do WhatsApp mesmo se a planilha falhar."""
    planilha = planilha_id()
    if not planilha:
        return False, (
            f"a planilha de fechamentos não está configurada (falta o arquivo "
            f"{NOME_DO_ARQUIVO_ID} em teste_watch_folder)")
    import sheets_client
    try:
        garantir_cabecalho(planilha, campos, aba=aba)
        # adicionar_linhas já neutraliza texto que começaria fórmula, o que
        # importa aqui: justificativa é texto livre digitado por uma pessoa, e
        # alguém pode começar a frase com "-" ou "=" sem pensar nisso.
        sheets_client.adicionar_linhas(
            planilha, aba, f"A:{_letra(len(campos))}",
            [[str(registro.get(c, "") or "") for c in campos]])
        return True, ""
    except Exception as e:
        return False, str(e)[:200]


def ler(campos, aba=ABA):
    """Os fechamentos (ou o que estiver em `aba`) já registrados na planilha,
    do mais novo para o mais antigo. Lista vazia quando não há planilha ou não
    há linha."""
    planilha = planilha_id()
    if not planilha:
        return []
    import sheets_client
    try:
        faixa = f"'{aba}'!A2:{_letra(len(campos))}5000"
        valores = sheets_client.executar(
            lambda: sheets_client.get_service().spreadsheets().values().get(
                spreadsheetId=planilha, range=faixa).execute()).get("values", [])
    except Exception:
        return []
    linhas = []
    for v in valores:
        if not any(str(c).strip() for c in v):
            continue
        linhas.append({c: (v[i] if i < len(v) else "")
                       for i, c in enumerate(campos)})
    return linhas[::-1]
