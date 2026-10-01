# -*- coding: utf-8 -*-
"""
Vídeo bruto sobe pro Drive, mas nunca entra na validação nem na Monitoramento.

POR QUE ESTE TESTE EXISTE (23/09/2026)

Pedido do Marketing, trazido pelo auditor: uma sessão que só pede @ e o
arquivo, sobe para a pasta "vídeo bruto" do dia, dentro da mesma árvore que o
programa já usa. É material que o influenciador manda antes, só para
conferência informal, e não a peça publicitária final.

ISTO TOCA UMA DECISÃO ANTIGA, de 01/09/2026: material bruto é fora do escopo
da auditoria, e o programa nunca abre pasta com esse nome para analisar (ver
e_pasta_de_bruto, usada por procurar_arquivo_repetido). A decisão continua de
pé; o que muda em 23/09 é que o programa passa a ESCREVER ali também, sem
nunca ler para validar. Este teste garante as duas pontas:

  1. o caminho até a pasta é o certo (mesma árvore, mesma trava de cadastro)
  2. quem sobe vídeo bruto NUNCA cria linha na Monitoramento nem enfileira
     validação — só isso já distingue de todo o resto do programa

Não fala com o Drive nem com o Google Sheets: as duas pontas são dublês.

    py testes\\teste_video_bruto.py
"""
import inspect
import os
import sys
from datetime import date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo
import fila_trabalho

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    print("--- 1. o tipo de tarefa existe, e é distinto dos outros dois ---")
    conferir(fila_trabalho.ENVIAR_VIDEO_BRUTO == "enviar_bruto",
             "fila_trabalho.ENVIAR_VIDEO_BRUTO existe")
    conferir(len({fila_trabalho.BAIXAR_FILA, fila_trabalho.ENVIAR_ARQUIVOS,
                 fila_trabalho.ENVIAR_VIDEO_BRUTO}) == 3,
             "os três tipos de tarefa são valores distintos")

    print()
    print("--- 2. o trabalhador sabe despachar a tarefa nova ---")
    fonte_trabalhador = open(os.path.join(BASE, "trabalhador.py"), encoding="utf-8").read()
    conferir("def executar_video_bruto(" in fonte_trabalhador,
             "existe a função que executa o envio de vídeo bruto")
    conferir("fila.ENVIAR_VIDEO_BRUTO" in fonte_trabalhador
             and "executar_video_bruto" in fonte_trabalhador.split("def executar_video_bruto")[0] + ""
             or "linha_de_download.submit(executar_video_bruto" in fonte_trabalhador,
             "o laço principal manda a tarefa nova para executar_video_bruto")
    conferir("fila.proxima(tipos=(" in fonte_trabalhador
             and "fila.ENVIAR_VIDEO_BRUTO" in fonte_trabalhador,
             "e fila.proxima() sabe puxar esse tipo de tarefa")

    print()
    print("--- 3. o caminho até a pasta, no layout do Marketing ---")
    guardados = {
        "descer": fluxo._descer_criando,
        "layout": fluxo.LAYOUT_PASTAS,
        "cache": dict(fluxo._pastas_bruto_cache),
    }
    fluxo._pastas_bruto_cache.clear()
    capturado = {}

    def descer_de_mentira(segmentos, criar_somente_ultimos=0, avisar=None, autorizar=None):
        capturado["segmentos"] = list(segmentos)
        capturado["criar_somente_ultimos"] = criar_somente_ultimos
        capturado["autorizar"] = autorizar
        return "id-da-pasta-bruto"

    fluxo._descer_criando = descer_de_mentira
    try:
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_MARKETING
        destino = fluxo._pasta_de_video_bruto("fulano", date(2026, 9, 23), "EDS")
        conferir(destino == "id-da-pasta-bruto", "devolve o id que a descida achou")
        conferir(capturado["segmentos"] == ["01. EDS", "2026", "09. Setembro", "@fulano",
                                            "23/09", "vídeo bruto"],
                 "o caminho é bet / ano / mês / @handle / dia / vídeo bruto",
                 str(capturado["segmentos"]))
        conferir(capturado["criar_somente_ultimos"] == 4,
                 "cria @handle, dia e vídeo bruto, mas não bet nem ano",
                 str(capturado["criar_somente_ultimos"]))
        conferir(capturado["autorizar"] is fluxo.impedimento_para_criar_pasta,
                 "passa pela MESMA trava do cadastro que todo o resto do programa usa")

        print()
        print("--- 4. no layout Futebol, só a bet fica de fora ---")
        capturado.clear()
        fluxo._pastas_bruto_cache.clear()
        fluxo.LAYOUT_PASTAS = fluxo.LAYOUT_FUTEBOL
        fluxo._pasta_de_video_bruto("fulano", date(2026, 9, 23), "EDS")
        conferir(capturado["segmentos"] == ["01. EDS", "09. SETEMBRO", "@fulano",
                                            "23/09", "vídeo bruto"],
                 "sem o nível de ano, igual ao resto do layout futebol",
                 str(capturado["segmentos"]))
        conferir(capturado["criar_somente_ultimos"] == 4,
                 "aqui só a bet fica de fora, então 4 dos 5 níveis podem ser criados",
                 str(capturado["criar_somente_ultimos"]))

        print()
        print("--- 5. o resultado fica em cache por execução ---")
        capturado.clear()
        fluxo._pasta_de_video_bruto("fulano", date(2026, 9, 23), "EDS")
        conferir(capturado == {}, "a segunda chamada nem chegou a descer de novo")
    finally:
        fluxo._descer_criando = guardados["descer"]
        fluxo.LAYOUT_PASTAS = guardados["layout"]
        fluxo._pastas_bruto_cache.clear()
        fluxo._pastas_bruto_cache.update(guardados["cache"])

    print()
    print("--- 6. enviar_video_bruto NUNCA toca Monitoramento nem validação ---")
    # A prova mais forte não é rodar e conferir o que NÃO aconteceu: é o
    # código-fonte não ter como chamar as duas coisas, ponto final.
    fonte = inspect.getsource(fluxo.enviar_video_bruto)
    conferir("registrar_na_monitoramento" not in fonte,
             "a função não referencia registrar_na_monitoramento")
    conferir("enfileirar_analise" not in fonte,
             "nem enfileirar_analise")
    conferir("VALIDAR" not in fonte,
             "e não cria tarefa de validação")

    print()
    print("--- 7. formato aceito é só vídeo, e sem handle não sobe ---")
    logados = []
    guardado_log = fluxo.gravar_log
    fluxo.gravar_log = lambda linhas: logados.extend(linhas)
    try:
        r = fluxo.enviar_video_bruto("foto.png", b"x", "fulano", "EDS", log_fn=lambda m: None)
        conferir(r["status"] == "FORMATO NAO ACEITO",
                 "imagem não é aceita, só vídeo", r["status"])

        r = fluxo.enviar_video_bruto("video.mp4", b"x", "", "EDS", log_fn=lambda m: None)
        conferir(r["status"] == "SEM HANDLE", "sem handle não sobe", r["status"])
    finally:
        fluxo.gravar_log = guardado_log

    print()
    print("--- 8. no sucesso, sobe, loga como BRUTO e devolve o link ---")
    guardado_pasta = fluxo._pasta_de_video_bruto
    guardado_log = fluxo.gravar_log
    fluxo._pasta_de_video_bruto = lambda *a, **k: "id-pasta"
    fluxo.gravar_log = lambda linhas: logados.extend(linhas)
    logados.clear()
    import drive_client_upload
    guardado_upload = drive_client_upload.enviar_arquivo
    drive_client_upload.enviar_arquivo = lambda caminho, nome, pasta: ("id-arquivo", "https://drive/link")
    try:
        r = fluxo.enviar_video_bruto("video.mp4", b"conteudo", "@Fulano", "EDS",
                                     data_video=date(2026, 9, 23),
                                     log_fn=lambda m: None, pedido_por="alguem@empresa.com")
        conferir(r["status"] == "OK", "sucesso", r["status"])
        conferir(r["destino"] == "https://drive/link", "devolve o link do Drive")
        conferir(r["handle"] == "@fulano", "o @ vem limpo e minúsculo", r["handle"])
        conferir(logados and logados[0]["estagio"] == "BRUTO",
                 "o log de fluxo marca o estágio como BRUTO, distinto de A/ENVIO/LINK",
                 str(logados))
        conferir(logados[0]["quem"] == "alguem@empresa.com",
                 "e quem pediu viaja no log")
    finally:
        fluxo._pasta_de_video_bruto = guardado_pasta
        fluxo.gravar_log = guardado_log
        drive_client_upload.enviar_arquivo = guardado_upload

    print()
    print("--- 9. resumo_da_tarefa entende o formato do vídeo bruto ---")
    tarefa = {
        "situacao": fila_trabalho.CONCLUIDA,
        "tipo": fila_trabalho.ENVIAR_VIDEO_BRUTO,
        "terminou_em": "2026-09-23 10:00:00",
        "resultado": {"enviados": 2, "organizados": 1, "problemas": ["x.mp4: FALHA"]},
        "mensagens": [],
    }
    aparencia, texto, motivos = fluxo.resumo_da_tarefa(tarefa)
    conferir(aparencia == "atencao", "1 de 2 organizados é atenção", aparencia)
    conferir("enviados organizados" in texto, "usa o mesmo texto do envio de arquivo", texto)

    print()
    print("--- 10. as páginas refletem a separação Download / Uploads ---")
    pagina_download = open(os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py"),
                           encoding="utf-8").read()
    pagina_uploads = open(os.path.join(BASE, "pages", "5_Uploads.py"),
                          encoding="utf-8").read()
    # PROCURA O FORMULÁRIO, e não a frase solta: a página de Downloads
    # continua CITANDO as duas seções (comentário explicando a mudança, e um
    # texto de ajuda apontando pra onde elas foram), e isso é correto, não
    # sobra de reorganização malfeita.
    conferir('st.form("enviar_fotos"' not in pagina_download,
             "a página de Downloads não tem mais o formulário de enviar arquivo")
    conferir('st.form("registrar_link"' not in pagina_download,
             "nem o formulário de registrar link")
    conferir("Enviar arquivo do post" in pagina_uploads
             and "Link só para registrar" in pagina_uploads
             and "Vídeo bruto" in pagina_uploads,
             "a página de Uploads tem as três seções")
    # A ORDEM É A PEDIDA: bruto, depois link, depois o que exige supervisão.
    # Procura pelo st.subheader de cada seção, e não pela frase solta: as
    # duas primeiras seções CITAM as outras em comentário (ver linhas 59 e
    # 87), e um comentário antes do subheader real derrubaria esta conta.
    ordem = [pagina_uploads.find(t) for t in
            ('st.subheader("Vídeo bruto")',
             '"Link só para registrar"',
             'st.subheader("Enviar arquivo do post")')]
    conferir(ordem == sorted(ordem) and all(p != -1 for p in ordem),
             "na ordem: vídeo bruto, link, e por último o que exige supervisão",
             str(ordem))
    conferir("PAPEL_SUPERVISAO" in pagina_uploads,
             "'Enviar arquivo do post' continua exigindo supervisão na página nova")

    print()
    print("--- 11. a página nova está registrada na navegação, não só no disco ---")
    # ACHADO NA HORA DE ESCREVER ESTE TESTE (23/09/2026): painel.py REGISTRA
    # cada página à mão via st.Page(...) dentro de st.navigation(); não é
    # descoberta automática pela pasta pages/. Um arquivo novo sem entrar
    # nesta lista existe no disco e nunca aparece pra quem usa, sem erro
    # nenhum na tela: a página fica inalcançável em silêncio.
    fonte_painel = open(os.path.join(BASE, "painel.py"), encoding="utf-8").read()
    conferir('st.Page("pages/5_Uploads.py"' in fonte_painel,
             "painel.py registra a página de Uploads na navegação",
             "sem isso ela existiria no disco e nunca apareceria na tela")


if __name__ == "__main__":
    print("=" * 74)
    print("  Vídeo bruto: sobe pro Drive, nunca entra em validação")
    print("=" * 74)
    print()
    rodar()
    print()
    print("=" * 74)
    print("  PASSOU." if not falhas else f"  {len(falhas)} FALHA(S).")
    print("=" * 74)
    sys.exit(1 if falhas else 0)
