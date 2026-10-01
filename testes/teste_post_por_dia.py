# -*- coding: utf-8 -*-
r"""
Prova que entrega do mesmo dia é UM post, e que a planilha guarda a pasta e o
arquivo em colunas diferentes.

O QUE O MARKETING SINALIZOU, repassado pelo auditor em 03/09/2026:

    "em entregas no mesmo dia (sequencia de stories por exemplo), eles devem ser
    considerados o mesmo post, ex: esses dois da Jubrasil deveriam ser POST 1 E
    1, ou seja, os dois são considerados o mesmo post, e portanto, o link deveria
    ir pra pasta onde estão os vídeos e não o link exato do vídeo. o LInk exato
    do vídeo é bom para mostrar a evidencia de não conformidae ou conformidade na
    parte de validação regulatória"

São duas mudanças, e a segunda tem consequência que a primeira não tem.

1. A COLUNA POST CONTA DIAS, E NÃO ARQUIVOS. Antes contava linhas e somava um,
   então três stories do mesmo dia saíam como POST 1, 2 e 3. Isso importa mais
   que arrumação: a cota do contrato é contada em posts, então quem publicasse
   cinco telas num dia aparecia como cinco posts entregues, e a conferência de
   cota ficava inflada sem ninguém perceber.

2. A COLUNA LINK APONTA PARA A PASTA, e o arquivo exato ganhou coluna própria
   (ARQUIVO). Sem a coluna nova, duas coisas quebrariam EM SILÊNCIO, e as duas
   estão testadas aqui:

     a conferência de linha repetida comparava a coluna LINK. Com a pasta ali, a
       segunda peça do mesmo dia seria lida como repetida e a linha NÃO seria
       criada: material no Drive sem linha na planilha.
     a análise lê o endereço da coluna LINK e SABE ABRIR PASTA. Com a pasta ali,
       cada linha do dia analisaria todos os arquivos do dia: quatro peças viram
       dezesseis análises, e o veredito de cada linha misturaria as quatro.
       Justamente a evidência por peça que o pedido quer preservar.

    py testes\teste_post_por_dia.py
"""
import datetime
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


def rodar():
    import fluxo_downloads as fluxo

    def linha_de(handle, dia, tipo="STORIES", ciclo="1", post="",
                 link="", arquivo="", marcacao="LINK"):
        """Monta uma linha da Monitoramento com só o que estas contas leem."""
        valores = [""] * fluxo.LARGURA_LINHA_MON
        valores[fluxo.COL_MON["handle"] - 1] = handle
        valores[fluxo.COL_MON["data_post"] - 1] = dia
        valores[fluxo.COL_MON["tipo"] - 1] = tipo
        valores[fluxo.COL_MON["ciclo"] - 1] = ciclo
        valores[fluxo.COL_MON["post"] - 1] = post
        valores[fluxo.COL_MON["link"] - 1] = link
        valores[fluxo.COL_MON["arquivo"] - 1] = arquivo
        valores[fluxo.COL_MON["marcacao"] - 1] = marcacao
        return valores

    D11 = datetime.date(2026, 8, 11)
    D12 = datetime.date(2026, 8, 12)

    print("--- 1. o caso exato que o Marketing apontou: @jubrasil, dois no mesmo dia ---")
    # Primeira peça do dia, planilha vazia.
    conferir(fluxo._numero_do_post([], "@jubrasil", "1", "STORIES", D11) == 1,
             "a primeira peça do dia é POST 1")
    # Segunda peça do MESMO dia: continua 1, e é isso que o Marketing pediu.
    ja_tem = [linha_de("@jubrasil", "11/08/2026", post="1")]
    conferir(fluxo._numero_do_post(ja_tem, "@jubrasil", "1", "STORIES", D11) == 1,
             "a segunda peça do MESMO dia também é POST 1",
             str(fluxo._numero_do_post(ja_tem, "@jubrasil", "1", "STORIES", D11)))
    # E a terceira, porque sequência de stories não tem tamanho fixo.
    ja_tem.append(linha_de("@jubrasil", "11/08/2026", post="1"))
    conferir(fluxo._numero_do_post(ja_tem, "@jubrasil", "1", "STORIES", D11) == 1,
             "e a terceira também")

    print()
    print("--- 2. dia novo ganha o próximo número ---")
    conferir(fluxo._numero_do_post(ja_tem, "@jubrasil", "1", "STORIES", D12) == 2,
             "outro dia é POST 2",
             str(fluxo._numero_do_post(ja_tem, "@jubrasil", "1", "STORIES", D12)))
    tres_dias = ja_tem + [linha_de("@jubrasil", "12/08/2026", post="2")]
    conferir(fluxo._numero_do_post(tres_dias, "@jubrasil", "1", "STORIES",
                                   datetime.date(2026, 8, 20)) == 3,
             "e o terceiro dia é POST 3, contando DIAS e não linhas",
             "com a conta antiga, quatro linhas dariam POST 5")

    print()
    print("--- 3. o que separa uma contagem da outra ---")
    # Influenciador, ciclo e tipo continuam separando, como antes.
    conferir(fluxo._numero_do_post(tres_dias, "@outra", "1", "STORIES", D11) == 1,
             "outro influenciador começa do 1")
    conferir(fluxo._numero_do_post(tres_dias, "@jubrasil", "2", "STORIES", D11) == 1,
             "outro ciclo começa do 1")
    conferir(fluxo._numero_do_post(tres_dias, "@jubrasil", "1", "REELS", D11) == 1,
             "e outro tipo também, porque a numeração é por tipo")

    print()
    print("--- 3b. a MARCAÇÃO separa posts, e o mesmo dia pode ter dois ---")
    # DECISÃO DELE depois de falar com o Marketing, no mesmo 03/09/2026: "a peça
    # orgânica nunca pode ser link ao mesmo tempo, além disso, elas não contam
    # como MESMO POST como é o caso do story em sequencia por exemplo, são tipos
    # de entrega diferentes mesmo".
    #
    # Sem a marcação na chave, o orgânico entraria no mesmo post do link e a cota
    # contaria UMA entrega onde houve DUAS: o erro contrário ao que esta função
    # conserta.
    dia_com_link = [linha_de("@jubrasil", "11/08/2026", post="1", marcacao="LINK")]
    conferir(fluxo._numero_do_post(dia_com_link, "@jubrasil", "1", "STORIES", D11,
                                   "organico") == 1,
             "o orgânico do mesmo dia começa a própria contagem, no 1",
             str(fluxo._numero_do_post(dia_com_link, "@jubrasil", "1", "STORIES",
                                       D11, "organico")))
    conferir(fluxo._numero_do_post(dia_com_link, "@jubrasil", "1", "STORIES", D11,
                                   "link") == 1,
             "e o link do mesmo dia continua no post dele")
    # Com os dois no dia, cada um segue a própria sequência.
    dia_misto = dia_com_link + [
        linha_de("@jubrasil", "11/08/2026", post="1", marcacao="ORGANICO")]
    conferir(fluxo._numero_do_post(dia_misto, "@jubrasil", "1", "STORIES", D12,
                                   "link") == 2
             and fluxo._numero_do_post(dia_misto, "@jubrasil", "1", "STORIES", D12,
                                       "organico") == 2,
             "no dia seguinte, as duas contagens vão para 2, cada uma na sua")
    # E o "SIM" das linhas de até 02/09 conta como orgânico nesta separação.
    antigo = [linha_de("@jubrasil", "11/08/2026", post="1", marcacao="SIM")]
    conferir(fluxo._numero_do_post(antigo, "@jubrasil", "1", "STORIES", D11,
                                   "organico") == 1,
             "linha antiga com SIM entra na contagem do orgânico",
             "sem isso ela seria lida como link e as duas contagens sairiam erradas")

    print()
    print("--- 4. número corrigido à mão na planilha MANDA ---")
    # Se alguém arrumou o número daquele dia, o programa usa o dele em vez de
    # recalcular. Recalcular desfaria a correção na peça seguinte do mesmo dia.
    corrigido = [linha_de("@jubrasil", "11/08/2026", post="7")]
    conferir(fluxo._numero_do_post(corrigido, "@jubrasil", "1", "STORIES", D11) == 7,
             "usa o 7 que está na planilha, e não recalcula",
             str(fluxo._numero_do_post(corrigido, "@jubrasil", "1", "STORIES", D11)))
    # Célula de post vazia ou com texto não serve de resposta: cai na contagem.
    vazio = [linha_de("@jubrasil", "11/08/2026", post="")]
    conferir(fluxo._numero_do_post(vazio, "@jubrasil", "1", "STORIES", D11) == 1,
             "célula de post vazia não vira número, cai na contagem de dias")
    texto = [linha_de("@jubrasil", "11/08/2026", post="ver com a Responsável A")]
    conferir(fluxo._numero_do_post(texto, "@jubrasil", "1", "STORIES", D11) == 1,
             "nem texto")

    print()
    print("--- 5. sem data, cada peça é um post próprio ---")
    # Não há como saber se é do mesmo dia de outra, e agrupar por engano juntaria
    # peças de dias diferentes sob o mesmo post.
    sem_data = [linha_de("@jubrasil", "", post="1")]
    conferir(fluxo._numero_do_post(sem_data, "@jubrasil", "1", "STORIES", None) == 1,
             "com a planilha só de linha sem data, responde 1")
    conferir(fluxo._numero_do_post(tres_dias, "@jubrasil", "1", "STORIES", None) == 3,
             "e não reaproveita o número de nenhum dia",
             str(fluxo._numero_do_post(tres_dias, "@jubrasil", "1", "STORIES", None)))

    print()
    print("--- 6. LINK é a pasta, ARQUIVO é a peça ---")
    conferir(fluxo.COL_MON["arquivo"] == 30
             and fluxo.letra_da_coluna(fluxo.COL_MON["arquivo"]) == "AD",
             "a coluna ARQUIVO é a AD", str(fluxo.COL_MON.get("arquivo")))
    conferir(fluxo.LARGURA_LINHA_MON >= fluxo.COL_MON["arquivo"],
             "e a largura da linha gravada alcança ela",
             f"largura={fluxo.LARGURA_LINHA_MON}")
    titulos = {chave: titulo for chave, _l, titulo, _p in fluxo.BLOCO_AUTOMACAO}
    conferir(titulos.get("arquivo") == "ARQUIVO", "o título é ARQUIVO")
    conferir(fluxo.link_de_pasta_no_drive("id123")
             == "https://drive.google.com/drive/folders/id123",
             "o endereço da pasta é montado do id",
             fluxo.link_de_pasta_no_drive("id123"))
    conferir(fluxo.link_de_pasta_no_drive(None) is None
             and fluxo.link_de_pasta_no_drive("") is None,
             "sem id, não inventa endereço",
             "aí a coluna LINK recebe o arquivo, como antes desta mudança")

    print()
    print("--- 7. a linha gravada põe cada endereço na sua coluna ---")
    import sheets_client
    gravadas = []

    class _Chamada:
        """Devolve a si mesma em qualquer chamada, e guarda o corpo do update.

        Serve de dublê da API do Google sem depender do formato exato das
        chamadas: o que este teste precisa é o `body` que sai daqui."""

        def __init__(self, registro):
            self.registro = registro

        def __getattr__(self, _nome):
            return self

        def __call__(self, *a, **kw):
            if "body" in kw:
                self.registro.append(kw["body"])
            return self

        def execute(self):
            # A leitura da planilha devolve vazio: nem linha existente nem
            # cabeçalho, que é o estado de uma Monitoramento nova.
            #
            # EXCETO DEPOIS DE JÁ TER ESCRITO (18/09/2026): desde que
            # registrar_na_monitoramento passou a RELER a própria linha
            # depois de escrever (trava entre máquinas diferentes), este
            # dublê precisa devolver o valor da coluna ARQUIVO que acabou de
            # ser gravado, senão a confirmação vê "nada gravado", trata como
            # colisão sempre, e o teste nunca termina de escrever de verdade.
            if self.registro:
                ultimo_corpo = self.registro[-1] or {}
                linhas = ultimo_corpo.get("values") or []
                if linhas:
                    indice = fluxo.COL_MON["arquivo"] - 1
                    linha = linhas[0]
                    if len(linha) > indice:
                        return {"values": [[linha[indice]]]}
            return {"values": []}

    guardados = {
        "_planilha_monitoramento_id": fluxo._planilha_monitoramento_id,
        "garantir_cabecalhos_automacao": fluxo.garantir_cabecalhos_automacao,
        "dados_de_cadastro_para_a_linha": fluxo.dados_de_cadastro_para_a_linha,
    }
    original_exec = sheets_client.executar
    original_service = sheets_client.get_service
    try:
        fluxo._planilha_monitoramento_id = lambda: "planilha-de-teste"
        fluxo.garantir_cabecalhos_automacao = lambda p: None
        fluxo.dados_de_cadastro_para_a_linha = lambda h, c: (None, "")
        # executar CHAMA a função, em vez de devolver um valor pronto: é dentro
        # dela que a gravação acontece, e um dublê que não chama engoliria
        # justamente o que este teste quer ver.
        sheets_client.executar = lambda funcao: funcao()
        sheets_client.get_service = lambda: _Chamada(gravadas)

        numero = fluxo.registrar_na_monitoramento(
            "jubrasil", D11, "Ciclo 1",
            "https://drive.google.com/file/d/ARQ1/view",
            marca="LOTTU", tipo="STORIES", marcacao="link",
            link_pasta="https://drive.google.com/drive/folders/PASTA1")
        conferir(numero == 2, "criou a linha 2, a primeira depois do cabeçalho",
                 str(numero))
        conferir(bool(gravadas), "e escreveu na planilha", str(len(gravadas)))
        escrita = None
        for corpo in gravadas:
            linhas_do_corpo = (corpo or {}).get("values") or []
            for valor in linhas_do_corpo:
                if len(valor) >= fluxo.COL_MON["arquivo"]:
                    escrita = valor
        conferir(escrita is not None, "e a linha tem largura suficiente",
                 str([len(v) for c in gravadas for v in (c.get("values") or [])]))
        if escrita:
            na_link = escrita[fluxo.COL_MON["link"] - 1]
            na_arquivo = escrita[fluxo.COL_MON["arquivo"] - 1]
            conferir(na_link == "https://drive.google.com/drive/folders/PASTA1",
                     "LINK recebeu a PASTA", str(na_link))
            conferir(na_arquivo == "https://drive.google.com/file/d/ARQ1/view",
                     "ARQUIVO recebeu a peça", str(na_arquivo))
            conferir(na_link != na_arquivo,
                     "e as duas colunas não são a mesma coisa")
            conferir(escrita[fluxo.COL_MON["post"] - 1] == 1,
                     "e o POST saiu 1", str(escrita[fluxo.COL_MON["post"] - 1]))
    finally:
        sheets_client.executar = original_exec
        sheets_client.get_service = original_service
        for nome, funcao in guardados.items():
            setattr(fluxo, nome, funcao)

    print()
    print("--- 8. a conferência de repetida olha as DUAS colunas ---")
    # Peça é arquivo. Com a pasta na coluna LINK, comparar LINK faria a segunda
    # peça do mesmo dia ser lida como repetida, e a linha não seria criada.
    import inspect
    fonte = inspect.getsource(fluxo.registrar_na_monitoramento)
    conferir('i_arquivo = COL_MON["arquivo"] - 1' in fonte,
             "compara pela coluna ARQUIVO")
    conferir("for indice in (i_arquivo, i_link)" in fonte,
             "e também pela LINK, para as linhas criadas até 02/09",
             "sem isso, baixar de novo uma peça antiga criaria linha repetida")

    print()
    print("--- 9. a análise lê ARQUIVO antes de LINK ---")
    with open(os.path.join(BASE, "pipeline_influenciadores.py"),
              encoding="utf-8-sig") as f:
        pipeline = f.read()
    conferir('campo("arquivo") or campo("link")' in pipeline,
             "a análise prefere a peça exata e cai na LINK só como reserva",
             "invertido, cada linha do dia analisaria a pasta inteira")
    conferir('fluxo.COL_MON["arquivo"]' in pipeline
             and "largura = max(" in pipeline,
             "e a largura lida alcança a coluna ARQUIVO",
             "com a largura antiga o arquivo apareceria vazio e a análise "
             "concluiria que não há o que analisar")

    print()
    print("--- 10. a tela mostra as duas colunas, e clicáveis ---")
    # Pedido do auditor em 03/09/2026, olhando a tela: "não tem como fazer
    # clicável como na planilha?". Sem isso a célula mostrava o endereço inteiro
    # em texto, que não abre e empurra a tabela para o lado.
    with open(os.path.join(BASE, "pages", "2_Monitoramento.py"),
              encoding="utf-8-sig") as f:
        tela = f.read()
    conferir('configuracao[col_de["arquivo"]] = st.column_config.LinkColumn' in tela,
             "a coluna ARQUIVO é clicável")
    conferir('configuracao[col_de["link"]] = st.column_config.LinkColumn' in tela,
             "e a da pasta também")
    conferir('"arquivo"' in tela.split("COLUNAS_PRINCIPAIS = [")[1].split("]")[0],
             "e ARQUIVO aparece na visão padrão, sem precisar ver todas",
             "é ela que serve para conferir a peça")
    # OS RÓTULOS TÊM QUE DIZER O QUE CADA UMA É. "Vídeo" na coluna LINK ficou
    # errado quando ela passou a apontar para a pasta.
    conferir('"link": "Pasta do post"' in tela,
             "o rótulo da LINK diz que é a pasta, e não mais Vídeo")
    conferir('"arquivo": "Arquivo"' in tela, "e a de arquivo diz que é o arquivo")
    # O PAINEL DE DETALHE ("Detalhe da validação", com "Abrir a peça
    # analisada") SAIU EM 14/09/2026, pedido do auditor para expor menos a
    # planilha. Quem precisa abrir a PEÇA que gerou o veredito faz isso pela
    # própria coluna ARQUIVO da tabela, que já é clicável (conferido acima) e
    # é a mesma coluna que a análise usa como evidência.
    conferir('configuracao[col_de["arquivo"]] = st.column_config.LinkColumn' in tela,
             "a peça continua acessível de um clique, pela coluna ARQUIVO da tabela")


if __name__ == "__main__":
    print("=" * 74)
    print("  Entrega do mesmo dia é um post, e a pasta não é o arquivo")
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
