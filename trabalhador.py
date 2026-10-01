# -*- coding: utf-8 -*-
"""
Trabalhador: o único processo que executa o trabalho pesado do programa.

POR QUE EXISTE (29/08/2026)

Antes, quem clicava no botão executava o trabalho dentro da própria aba do
navegador. Isso funcionava com uma pessoa e quebra com cinco, pelos motivos
detalhados em fila_trabalho.py. Agora o app só põe tarefa na fila, e este
programa aqui é quem faz.

Ter UM trabalhador não é limitação técnica, é a decisão certa para este caso,
por três motivos medidos:

1. O modelo de visão é um servidor só, compartilhado. Medido em 28/08/2026:
   duas análises ao mesmo tempo rendem 110s por vídeo; três não melhoram
   nada. Ter mais processos analisando não aumenta a produção, só distribui a
   mesma capacidade entre mais gente esperando.
2. O Instagram conta as chamadas por conta e por endereço de rede. Dois
   processos falando com ele ao mesmo tempo furam o teto diário sem ninguém
   perceber, que é exatamente o que marcou duas contas em agosto de 2026.
3. Sendo um só, ele é o único que encosta nos arquivos de estado, e o risco
   de duas gravações se atropelarem desaparece por construção. A trava em
   trava.py continua existindo como segunda linha de defesa.

COMO RODAR

    cd C:\\Users\\auditor\\Documents\\Auditoria\\producao\\analises
    py trabalhador.py

Ou pelo atalho iniciar_trabalhador.bat. Ele precisa ficar aberto: se fechar,
o app avisa na tela que ninguém vai pegar as tarefas. O que estava rodando
volta para a fila sozinho quando ele subir de novo.

Para encerrar sem cortar trabalho no meio, use "Encerrar o trabalhador" na
tela, ou Ctrl+C aqui. Ele termina o que está fazendo e sai.

DE DENTRO PARA FORA

Análise de vídeo roda num grupo de dois processos que ficam de pé enquanto o
trabalhador viver. Isso é essencial: carregar o modelo de visão leva perto de
dois minutos na primeira chamada, então um grupo criado e destruído a cada
lote pagaria esse custo toda vez.

O download roda numa linha de execução própria, uma de cada vez. Fica
separado da análise porque ele passa a maior parte do tempo esperando a rede
e as pausas de propósito entre links do Instagram (de 45 a 120 segundos), e
não faz sentido esse tempo parado bloquear a análise, nem o contrário.
"""
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

# A janela do Prompt de Comando no Windows não usa UTF-8 por padrão, então
# acento sai embaralhado no que este programa escreve. Como é justamente por
# essa janela que se acompanha o trabalho, deixar ilegível não serve.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

import fila_trabalho as fila
import pipeline_influenciadores as pipeline

# De quanto em quanto tempo o laço principal olha a fila. Curto o bastante
# para a tela não parecer parada, longo o bastante para não consumir máquina
# à toa: cada volta é só olhar algumas pastas.
SEGUNDOS_ENTRE_VOLTAS = 2

# Quantas análises manter entregues ao grupo de processos. Uma a mais que o
# número de processos, para que nenhum deles fique parado esperando a próxima
# volta do laço quando terminar um vídeo.
ANALISES_ENTREGUES = pipeline.TRABALHADORES_PADRAO + 1

HORAS_ENTRE_LIMPEZAS = 6

# ------------------------------------------------------------------
# Link que ficou esperando baixa sozinho
# ------------------------------------------------------------------
# O PROBLEMA QUE ISTO RESOLVE (08/09/2026)
#
# Quem cola um link só cria tarefa de download se ainda não existe uma. Isso é
# de propósito: cada tarefa processa TODOS os links pendentes, e duas tarefas em
# paralelo acabariam com as pausas entre links do Instagram, que são o que
# protege a conta de bloqueio.
#
# A consequência é uma corrida. Colando um link enquanto uma tarefa de download
# está em andamento, ninguém cria tarefa nova, e a tela promete que o link
# "entra na rodada que já está em andamento". A rodada relê a fila uma vez no
# fim dela, justamente para cumprir essa promessa (correção de 06/09/2026). Mas
# se o link chega à planilha DEPOIS dessa releitura única, e antes de a tarefa
# terminar, ninguém mais olha por ele.
#
# Foi medido em uso real em 08/09/2026: dois stories da @lomma, a tarefa começou
# 10:28:43 e terminou 10:29:08, e o segundo link ficou parado com status vazio.
# Nada falhou, nada foi bloqueado, o teto do dia estava em 1 de 20. O link ficou
# esperando um clique que ninguém sabia que era necessário.
#
# A CORREÇÃO DE 06/09 ESTREITOU A JANELA, NÃO FECHOU. Aqui ela fecha por outro
# caminho: em vez de tentar ler a fila no instante exato, o trabalhador confere a
# fila quando está ocioso e cria a tarefa ele mesmo. Passa a acontecer DEPOIS de
# a tarefa terminar, e não antes, então não há instante em que a decisão se perca.
#
# POR QUE ESPERAR ANTES DE DISPARAR, e não disparar no primeiro link órfão: quem
# está colando um lote provavelmente vai colar mais. Disparando na hora, cada
# link viraria uma rodada de um link só, e as pausas entre links deixariam de
# existir, porque elas acontecem DENTRO de uma rodada. Esperar deixa o lote
# juntar e mantém o espaçamento que protege a conta.
#
# ESTE NÚMERO É ESCOLHA, NÃO MEDIÇÃO, e é bom que fique explícito. Curto demais
# devolve as rodadas de um link só; longo demais deixa a pessoa olhando a tela
# sem entender. Vale revisar depois de ver o Marketing usando: se aparecerem
# rodadas de um link só, aumente; se alguém reclamar de demora, diminua.
#
# O valor mora em fila_trabalho porque a TELA também precisa dele, para dizer à
# pessoa quanto falta. Um número escrito em dois lugares divergiria, e a tela
# passaria a prometer prazo que o trabalhador não cumpre.
SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO = fila.SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO

# Conferir a fila é uma chamada à planilha, e o laço principal roda a cada 2
# segundos. Sem este estrangulamento seriam 1.800 chamadas por hora ocioso.
SEGUNDOS_ENTRE_CONFERENCIAS_DA_FILA = 20


def decidir_se_baixa_sozinho(agora, ha_tarefa_de_download, quantas_esperando,
                             estado):
    """Decide se o trabalhador deve criar a tarefa de download por conta própria.

    Função PURA de propósito: não lê planilha, não cria tarefa, não escreve log.
    Recebe o retrato do momento e devolve a decisão. É o que permite testar o
    comportamento, inclusive os casos de laço, sem planilha e sem trabalhador
    de pé.

    `estado` é um dicionário que o chamador guarda entre as voltas, com:
        quantas          quantas linhas estavam esperando na conferência anterior
        esperando_desde  desde quando essa mesma quantidade está esperando
        tentou_com       quantas estavam esperando quando a última tarefa
                         automática foi criada, ou None

    Devolve (criar, motivo, novo_estado). `motivo` é texto curto para o log, e
    vem preenchido só quando há algo que valha registrar."""
    zerado = {"quantas": 0, "esperando_desde": None, "tentou_com": None}

    # Já existe tarefa esperando ou em andamento: ela vai pegar essas linhas,
    # porque uma tarefa processa todas as pendentes. Criar outra é o que a regra
    # de rajada evita.
    if ha_tarefa_de_download:
        return False, "", zerado

    if not quantas_esperando:
        return False, "", zerado

    # A quantidade mudou desde a última conferência, então ainda está entrando
    # link. Reinicia a espera para o lote juntar, e libera uma nova tentativa
    # automática, porque agora existe trabalho que a anterior não viu.
    if quantas_esperando != estado.get("quantas"):
        # AVISA NA PRIMEIRA VEZ QUE VÊ, e só nela. Dizer isto a cada conferência
        # seria uma linha a cada 20 segundos na janela do trabalhador, e o
        # auditor já reclamou de aviso demais na tela mais de uma vez. Como esta
        # mensagem só sai quando a quantidade MUDA, ela sai uma vez por lote.
        return (False,
                f"{quantas_esperando} link(s) esperando na fila. Se nada mais "
                f"entrar, baixo sozinho em "
                f"{SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO}s.",
                {"quantas": quantas_esperando,
                 "esperando_desde": agora,
                 "tentou_com": None})

    desde = estado.get("esperando_desde")
    if desde is None:
        return False, "", {"quantas": quantas_esperando,
                           "esperando_desde": agora,
                           "tentou_com": None}

    if agora - desde < SEGUNDOS_DE_ESPERA_ANTES_DE_BAIXAR_SOZINHO:
        return False, "", estado

    # FREIO CONTRA LAÇO. Se a última tarefa automática foi criada com esta mesma
    # quantidade esperando, ela não resolveu nada, e criar outra igual repetiria
    # o mesmo nada para sempre. Para aqui e deixa para a pessoa, que tem o botão
    # na tela. Linha que falha de verdade recebe status e sai desta contagem, o
    # que já evita a maior parte dos casos; isto é a rede embaixo.
    if estado.get("tentou_com") == quantas_esperando:
        return False, "", estado

    return (True,
            f"{quantas_esperando} link(s) ficaram esperando na fila. "
            f"Baixando sozinho, sem precisar de clique.",
            {"quantas": quantas_esperando,
             "esperando_desde": agora,
             "tentou_com": quantas_esperando})


def varrer_fila_esperando(agora, estado):
    """Confere a fila e cria a tarefa de download quando chega a hora.

    CHAMAR SÓ COM A LINHA DE DOWNLOAD PARADA. Não é preferência de desenho, é
    segurança: o motivo está registrado no laço principal, junto da chamada.

    Devolve o novo estado da varredura."""
    # Conferido ANTES de falar com a planilha. Tarefa esperando sem ter sido
    # pega ainda vai processar essas linhas de qualquer jeito, então a chamada
    # à planilha não se justifica.
    if fila.ha_trabalho(fila.BAIXAR_FILA):
        _criar, _motivo, estado = decidir_se_baixa_sozinho(agora, True, 0, estado)
        return estado

    try:
        import fluxo_downloads as fluxo
        # O MESMO CRITÉRIO que a rodada usa para saber o que está pendente:
        # link preenchido e status vazio. Não inventar critério aqui importa,
        # porque contar linha que a rodada não processaria faria a varredura
        # criar tarefa para sempre sem nada mudar.
        esperando = sum(1 for x in fluxo.ler_fila()
                        if x["link"] and not x["status"])
    except Exception as e:
        # Conferir a fila não pode derrubar o trabalhador. Se a planilha não
        # responder agora, tenta na volta seguinte.
        registrar(f"  (não consegui conferir a fila agora: {str(e)[:90]})")
        return estado

    criar, motivo, estado = decidir_se_baixa_sozinho(
        agora, False, esperando, estado)
    if motivo:
        registrar(motivo)
    if criar:
        # analisar_depois fica LIGADO, e isto é escolha consciente: a linha da
        # fila não guarda o que a pessoa marcou na tela, e baixar sem analisar
        # deixaria a peça no Drive sem veredito nenhum, o que é pior num
        # programa de auditoria do que analisar sem ter sido pedido.
        fila.criar(
            fila.BAIXAR_FILA,
            {"analisar_depois": True},
            rotulo="baixar o que ficou esperando · analisa em seguida",
            criada_por="automático (link ficou esperando na fila)")
    return estado


def registrar(mensagem):
    print(f"{datetime.now():%H:%M:%S} {mensagem}", flush=True)


# ------------------------------------------------------------------
# Análise de vídeo
# ------------------------------------------------------------------
def concluir_analise(tarefa, resultado):
    """Guarda o resultado e escreve o veredito na Monitoramento.

    A escrita acontece aqui, e não no app, porque é ela que fecha o ciclo:
    se ficasse do lado da tela, fechar o navegador na hora errada deixaria a
    análise feita e o veredito nunca escrito."""
    link = tarefa["dados"]["link"]
    pipeline.registrar_no_cache(link, resultado)

    linhas = tarefa["dados"].get("excel_rows") or []
    try:
        escritas = pipeline.gravar_veredito(linhas, resultado)
    except Exception as e:
        # A análise não se perde: ela já está guardada. Só a escrita falhou,
        # e a tarefa fica marcada como falha para dar para tentar de novo pela
        # tela, o que é instantâneo porque não reanalisa nada.
        fila.falhar(tarefa, f"Analisou, mas não consegui escrever na planilha: {e}")
        registrar(f"  [{tarefa['rotulo']}] analisou, mas falhou ao escrever: {str(e)[:120]}")
        return

    veredito = pipeline.formatar_para_planilha(resultado) or ""
    fila.concluir(tarefa, {
        "classificacao": resultado.get("classificacao"),
        "veredito": veredito,
        "motivo": str(resultado.get("motivo") or "")[:500],
        "linhas_escritas": escritas,
        "linhas": linhas,
    })
    registrar(f"  [{tarefa['rotulo']}] {veredito or resultado.get('classificacao')} "
              f"({escritas} linha(s) escrita(s))")


def entregar_analise(equipe, tarefa):
    """Manda o vídeo para o grupo de processos, ou resolve na hora se ele já
    foi analisado antes.

    O aproveitamento do que já foi analisado acontece aqui, e não na tela,
    para valer também para tarefa criada pela linha de comando ou por outra
    pessoa. É o caso de linha cujo veredito foi apagado de propósito para
    reprocessar, e o de lote que caiu depois de analisar e antes de escrever."""
    link = tarefa["dados"]["link"]
    guardado = pipeline.carregar_cache().get(link)
    if guardado:
        registrar(f"  [{tarefa['rotulo']}] já tinha análise guardada, indo direto para a planilha")
        concluir_analise(tarefa, guardado)
        return None

    # PEÇA ORGÂNICA NÃO VAI PARA A EQUIPE DE ANÁLISE (03/09/2026).
    #
    # Decisão do auditor: "orgânico realmente não precisa de análise
    # regulatória". Resolvido aqui, na entrega, e não dentro do processo de
    # análise, porque assim ele nem é acionado: a análise leva perto de 110
    # segundos por vídeo nesta máquina, e 81% disso é a IA de visão.
    #
    # Fica antes da submissão e DEPOIS do cache, na mesma ordem do resto: linha
    # que já tem análise guardada continua aproveitando o que existe.
    linha = tarefa["dados"]["linha"]
    if pipeline.e_linha_organica(linha):
        registrar(f"  [{tarefa['rotulo']}] marcada como orgânica: não passa pela "
                  f"régua regulatória, e não é analisada")
        concluir_analise(tarefa, pipeline.processar_organico(linha))
        return None

    return equipe.submit(pipeline.processar_linha_protegida, linha)


# ------------------------------------------------------------------
# Fila de downloads
# ------------------------------------------------------------------
def executar_download(tarefa):
    """Roda a fila de downloads inteira, uma vez.

    É uma tarefa só, e não uma por link, porque o próprio fluxo já controla
    quantos links do Instagram entram por rodada e a pausa entre eles. Quebrar
    em várias tarefas espalharia esse controle e é justamente ele que segura o
    risco de bloqueio."""
    import fluxo_downloads as fluxo

    def acompanhar(mensagem):
        registrar(f"  {mensagem}")
        try:
            fila.anotar(tarefa, str(mensagem))
        except OSError:
            pass

    # A tela manda "analisar_depois". Tarefa antiga, criada antes de 31/08/2026,
    # não tem esse campo, e para ela o padrão é analisar: é o comportamento novo
    # e o que o auditor pediu.
    analisar = bool((tarefa.get("dados") or {}).get("analisar_depois", True))

    # ESPERA A VEZ DA CONTA ANTES DE COMEÇAR (22/09/2026), só quando a fila
    # tem link do Instagram: outra máquina pode estar automatizando chamada
    # na MESMA conta agora, e rodar ao mesmo tempo é o padrão que mais se
    # parece com conta comprometida aos olhos do Instagram. Fica aqui, e não
    # dentro de processar_fila, de propósito: aquela função tem teste que
    # inspeciona o código-fonte dela diretamente
    # (teste_colunas_do_cadastro.py, teste_handle_do_servidor.py,
    # teste_story_de_foto.py, teste_calendario_no_fluxo.py), e um comentário
    # a mais no meio dela já mudaria posição que esses testes conferem.
    marcou_uso = (fluxo.fila_tem_link_do_instagram()
                  and fluxo.aguardar_vez_da_conta(log_fn=acompanhar))
    try:
        resultado = fluxo.processar_fila(log_fn=acompanhar, analisar_depois=analisar)
    finally:
        if marcou_uso:
            fluxo.liberar_vez_da_conta()
    certos = sum(1 for r in resultado if r["status"] == "OK")
    return {"processados": len(resultado), "organizados": certos,
            "mandados_para_analise": analisar}


def executar_envio(tarefa):
    """Organiza no Drive os arquivos que a pessoa enviou pela tela.

    Roda aqui, e não na tela, desde 30/08/2026. Cada arquivo lista o Drive
    algumas vezes e lê a Monitoramento inteira, então 25 arquivos prendiam a
    tela por minutos. E como quem escreve na planilha passa a ser um só, dois
    envios ao mesmo tempo deixam de disputar a mesma linha.

    Vai um arquivo por vez, de propósito: a numeração de tela de cada um
    depende do que já subiu antes.

    MANDA PARA ANÁLISE NO FIM, DESDE 23/09/2026. Achado testando: um envio
    feito pela tela "Enviar arquivo do post" cria a linha na Monitoramento
    (AGUARDANDO VALIDAÇÃO), mas até aqui nada mandava ela para a fila de
    análise. Só a fila de downloads fazia isso, em `enfileirar_analise`
    (chamada de dentro de `processar_fila`, quando `analisar_depois`). A
    linha ficava esperando para sempre, sem ninguém pedir, porque a única
    forma de criar tarefa VALIDAR era aquele caminho. A política do programa
    é "tudo que entra é analisado, sem escolha" (ver o comentário de
    `enfileirar_analise`), e isso vale igual para o que entra por envio de
    arquivo. `ENVIAR_VIDEO_BRUTO` continua de fora de propósito: aquele
    vídeo nunca cria linha na Monitoramento (ver `executar_video_bruto`)."""
    import shutil
    import fluxo_downloads as fluxo

    dados = tarefa["dados"]
    arquivos = dados.get("arquivos") or []
    campos = dados.get("campos") or {}
    inicio_tela = campos.get("tela")

    # A data viaja como texto, porque a tarefa é gravada em JSON.
    data_informada = None
    if campos.get("data"):
        try:
            data_informada = datetime.strptime(campos["data"][:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    def acompanhar(mensagem):
        registrar(f"  {mensagem}")
        try:
            fila.anotar(tarefa, str(mensagem))
        except OSError:
            pass

    certos, problemas = 0, []
    links_para_analisar = []
    for i, item in enumerate(arquivos):
        caminho, nome_original = item["caminho"], item["nome"]
        acompanhar(f"[{i + 1}/{len(arquivos)}] {nome_original}")
        if not os.path.exists(caminho):
            problemas.append(f"{nome_original}: o arquivo sumiu antes de ser processado")
            continue
        try:
            r = fluxo.processar_arquivo_no_disco(
                caminho, nome_original=nome_original,
                handle_manual=campos.get("handle"), data_manual=data_informada,
                ciclo_manual=campos.get("ciclo"), marca=campos.get("marca"),
                tipo=campos.get("tipo"), log_fn=acompanhar,
                tela=(inicio_tela + i) if inicio_tela else None,
                # Escolhido pela supervisão na tela, uma das três (orgânico,
                # publi, link). Vale para TODOS os arquivos deste envio, porque a
                # marcação é do envio e não de cada arquivo: quem manda uma peça
                # orgânica e uma com link no mesmo arraste precisa fazer dois
                # envios.
                marcacao=campos.get("marcacao"),
                # Quem enviou, para a coluna PEDIDO_POR. Vem dos campos da
                # tarefa porque um envio de arquivo é de uma pessoa só; para a
                # fila de links é diferente, e lá quem pediu viaja na linha.
                pedido_por=campos.get("pedido_por") or tarefa.get("criada_por"),
            )
            if r["status"] == "OK":
                certos += 1
                if r.get("destino"):
                    links_para_analisar.append(r["destino"])
            else:
                problemas.append(f"{nome_original}: {r['status']}")
        except Exception as e:
            problemas.append(f"{nome_original}: {str(e)[:120]}")

    # Limpa os arquivos guardados só depois de tudo, e sem derrubar a tarefa
    # se a limpeza falhar: o material já está no Drive, que é o destino.
    for item in arquivos:
        pasta = os.path.dirname(item["caminho"])
        try:
            shutil.rmtree(pasta, ignore_errors=True)
        except OSError:
            pass

    # MANDA PARA ANÁLISE (ver o porquê no docstring da função). Não derruba a
    # tarefa se falhar: o material já está no Drive, e a linha fica visível
    # na Monitoramento como AGUARDANDO VALIDAÇÃO, exatamente como já era
    # antes desta mudança, para alguém mandar à mão se a fila não pegar.
    if links_para_analisar:
        try:
            fluxo.enfileirar_analise(
                links_para_analisar, log_fn=acompanhar,
                criada_por=campos.get("pedido_por") or tarefa.get("criada_por"))
        except Exception as e:
            acompanhar(f"não consegui mandar para análise: {str(e)[:120]}")

    return {"enviados": len(arquivos), "organizados": certos, "problemas": problemas}


def executar_video_bruto(tarefa):
    """Sobe os vídeos brutos que a pessoa enviou pela tela.

    QUASE IGUAL A executar_envio, e de propósito NÃO reaproveita ela: aquela
    chama processar_arquivo_no_disco, que cria linha na Monitoramento e pode
    enfileirar validação. Este vídeo não passa por nenhuma das duas (ver
    fluxo.enviar_video_bruto), e a forma mais segura de garantir isso é o
    trabalhador nem ter a chance de chamar a função errada."""
    import shutil
    import fluxo_downloads as fluxo

    dados = tarefa["dados"]
    arquivos = dados.get("arquivos") or []
    campos = dados.get("campos") or {}

    data_informada = None
    if campos.get("data"):
        try:
            data_informada = datetime.strptime(campos["data"][:10], "%Y-%m-%d").date()
        except ValueError:
            pass

    def acompanhar(mensagem):
        registrar(f"  {mensagem}")
        try:
            fila.anotar(tarefa, str(mensagem))
        except OSError:
            pass

    certos, problemas = 0, []
    for i, item in enumerate(arquivos):
        caminho, nome_original = item["caminho"], item["nome"]
        acompanhar(f"[{i + 1}/{len(arquivos)}] {nome_original}")
        if not os.path.exists(caminho):
            problemas.append(f"{nome_original}: o arquivo sumiu antes de ser processado")
            continue
        try:
            with open(caminho, "rb") as f:
                conteudo = f.read()
            r = fluxo.enviar_video_bruto(
                nome_original, conteudo, campos.get("handle"), campos.get("marca"),
                data_video=data_informada, log_fn=acompanhar,
                pedido_por=campos.get("pedido_por") or tarefa.get("criada_por"))
            if r["status"] == "OK":
                certos += 1
            else:
                problemas.append(f"{nome_original}: {r['status']}")
        except Exception as e:
            problemas.append(f"{nome_original}: {str(e)[:120]}")

    for item in arquivos:
        pasta = os.path.dirname(item["caminho"])
        try:
            shutil.rmtree(pasta, ignore_errors=True)
        except OSError:
            pass

    return {"enviados": len(arquivos), "organizados": certos, "problemas": problemas}


# ------------------------------------------------------------------
# Laço principal
# ------------------------------------------------------------------
def main():
    fila.garantir_pastas()
    fila.limpar_pedido_de_parada()

    recuperadas = fila.recuperar_orfas()
    if recuperadas:
        registrar(f"{len(recuperadas)} tarefa(s) tinham ficado pela metade e voltaram para a fila.")

    registrar("Trabalhador de pé. Deixe esta janela aberta.")
    registrar(f"Fila em {fila.PASTA_FILA}")

    equipe = None
    analises_em_voo = {}     # futuro -> tarefa
    linha_de_download = ThreadPoolExecutor(max_workers=1)
    download_em_voo = None   # (futuro, tarefa)
    ultima_limpeza = time.time()
    encerrando = False
    ultima_conferencia_da_fila = 0.0
    varredura = {"quantas": 0, "esperando_desde": None, "tentou_com": None}

    try:
        while True:
            if fila.parada_pedida() and not encerrando:
                encerrando = True
                registrar("Pedido de encerramento recebido. Terminando o que já começou.")

            # 1. Recolhe as análises que terminaram.
            for futuro in [f for f in analises_em_voo if f.done()]:
                tarefa = analises_em_voo.pop(futuro)
                try:
                    concluir_analise(tarefa, futuro.result())
                except Exception as e:
                    fila.falhar(tarefa, f"{e}\n{traceback.format_exc()[:800]}")
                    registrar(f"  [{tarefa['rotulo']}] falhou: {str(e)[:160]}")

            # 2. Recolhe o download, se terminou.
            if download_em_voo and download_em_voo[0].done():
                futuro, tarefa = download_em_voo
                download_em_voo = None
                rotulo = {fila.BAIXAR_FILA: "fila de downloads",
                         fila.ENVIAR_ARQUIVOS: "envio de arquivos",
                         fila.ENVIAR_VIDEO_BRUTO: "envio de vídeo bruto"}.get(
                    tarefa["tipo"], tarefa["tipo"])
                try:
                    fila.concluir(tarefa, futuro.result())
                    registrar(f"  {rotulo} concluído")
                except Exception as e:
                    fila.falhar(tarefa, f"{e}\n{traceback.format_exc()[:800]}")
                    registrar(f"  {rotulo} falhou: {str(e)[:160]}")

            # 3. Pega trabalho novo, se não estiver encerrando.
            if not encerrando:
                while len(analises_em_voo) < ANALISES_ENTREGUES:
                    tarefa = fila.proxima(tipos=(fila.VALIDAR,))
                    if not tarefa:
                        break
                    registrar(f"analisando: {tarefa['rotulo']} (pedido por {tarefa.get('criada_por')})")
                    if equipe is None:
                        equipe = pipeline.abrir_equipe()
                    futuro = entregar_analise(equipe, tarefa)
                    if futuro is not None:
                        analises_em_voo[futuro] = tarefa

                # Download e envio compartilham a mesma linha de execução: os
                # dois falam com o Drive e com a planilha, e deixá-los
                # concorrer entre si só criaria disputa pela mesma linha.
                if download_em_voo is None:
                    tarefa = fila.proxima(tipos=(
                        fila.BAIXAR_FILA, fila.ENVIAR_ARQUIVOS, fila.ENVIAR_VIDEO_BRUTO))
                    if tarefa:
                        if tarefa["tipo"] == fila.BAIXAR_FILA:
                            registrar(f"baixando a fila (pedido por {tarefa.get('criada_por')})")
                            futuro = linha_de_download.submit(executar_download, tarefa)
                        elif tarefa["tipo"] == fila.ENVIAR_VIDEO_BRUTO:
                            quantos = len((tarefa["dados"].get("arquivos") or []))
                            registrar(f"organizando {quantos} vídeo(s) bruto(s) "
                                      f"(por {tarefa.get('criada_por')})")
                            futuro = linha_de_download.submit(executar_video_bruto, tarefa)
                        else:
                            quantos = len((tarefa["dados"].get("arquivos") or []))
                            registrar(f"organizando {quantos} arquivo(s) enviado(s) "
                                      f"(por {tarefa.get('criada_por')})")
                            futuro = linha_de_download.submit(executar_envio, tarefa)
                        download_em_voo = (futuro, tarefa)

            # 3.5. Link que ficou esperando na fila baixa sozinho.
            #
            # Fecha a corrida descrita em decidir_se_baixa_sozinho. Roda aqui, e
            # não dentro de processar_fila, porque o ponto é exatamente ser
            # DEPOIS de a tarefa terminar: assim não existe instante em que a
            # decisão de baixar se perca entre a tela e a rodada.
            # SÓ CONFERE A FILA COM A LINHA DE DOWNLOAD PARADA, e o motivo é o
            # propósito da varredura, não segurança.
            #
            # QUEM IMPEDE O SEGFAULT É A TRAVA EM sheets_client, e isso precisa
            # ficar claro aqui. A primeira versão desta varredura lia a fila a
            # cada 20 segundos sem olhar se havia download em andamento, e o
            # trabalhador morreu com "Segmentation fault" em 08/09/2026, porque
            # duas threads usavam o mesmo cliente do Google, que não é seguro
            # para uso simultâneo. A investigação mostrou que a mesma corrida já
            # existia ANTES, entre a thread principal escrevendo veredito
            # (concluir_analise) e a linha de download escrevendo na
            # Monitoramento. Por isso a correção foi feita na origem, e não
            # aqui. Ver o comentário de _TRAVA_DA_API em sheets_client.py.
            #
            # Esta guarda fica porque é o certo para o que a varredura faz: o
            # ponto dela sempre foi agir DEPOIS de a tarefa terminar, e conferir
            # a fila no meio de um download seria chamada à planilha sem uso.
            # Tirá-la não traz de volta o segfault; tirar a trava traz.
            if not encerrando and download_em_voo is None:
                agora = time.time()
                if agora - ultima_conferencia_da_fila >= SEGUNDOS_ENTRE_CONFERENCIAS_DA_FILA:
                    ultima_conferencia_da_fila = agora
                    varredura = varrer_fila_esperando(agora, varredura)

            # 4. Diz que está vivo.
            em_andamento = [t["rotulo"] for t in analises_em_voo.values()]
            if download_em_voo:
                em_andamento.append("fila de downloads")
            fila.registrar_sinal_de_vida({
                "pid": os.getpid(),
                "maquina": os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "",
                "analises_ao_mesmo_tempo": pipeline.TRABALHADORES_PADRAO,
                "fazendo_agora": em_andamento,
                "encerrando": encerrando,
            })

            # 5. Limpeza periódica do histórico de tarefas terminadas.
            if time.time() - ultima_limpeza > HORAS_ENTRE_LIMPEZAS * 3600:
                ultima_limpeza = time.time()
                apagadas = fila.limpar_terminadas()
                if apagadas:
                    registrar(f"{apagadas} tarefa(s) antigas saíram do histórico da fila.")

            if encerrando and not analises_em_voo and download_em_voo is None:
                registrar("Nada mais em andamento. Encerrando.")
                break

            time.sleep(SEGUNDOS_ENTRE_VOLTAS)

    except KeyboardInterrupt:
        registrar("Interrompido pelo teclado. O que estava em andamento volta para a fila.")
    finally:
        # Sem wait: o que ficou pela metade volta para a fila na próxima vez
        # que o trabalhador subir (ver recuperar_orfas). Esperar aqui deixaria
        # o Ctrl+C parecendo travado por vários minutos.
        if equipe is not None:
            equipe.shutdown(wait=False, cancel_futures=True)
        linha_de_download.shutdown(wait=False)
        fila.limpar_pedido_de_parada()
        fila.registrar_sinal_de_vida({"pid": os.getpid(), "fazendo_agora": [], "encerrado": True,
                                      "encerrado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        registrar("Trabalhador encerrado.")


# O laço fica atrás desta condição porque o grupo de processos de análise, no
# Windows, importa este arquivo de novo dentro de cada processo filho. Sem a
# condição, cada filho tentaria virar um trabalhador também.
if __name__ == "__main__":
    main()
