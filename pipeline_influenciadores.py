"""
Lógica pura (sem Streamlit) do pipeline de validação de avisos regulatórios em
posts de influenciadores. Fica separada do app pra poder ser testada por
terminal com o EXATO mesmo código que o app usa — evita ter duas versões da
mesma lógica que podem divergir com o tempo.
"""

import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime

import openpyxl

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import drive_client
import trava
import validar_avisos_portaria136 as motor

PLANILHA_ID = "1Uzxi3K1o6Nq7bgUhLZNBIYm5Qw7hD9Y7FOtLxr4-V9w"
# O .xlsx trunca nomes de aba em 31 caracteres (limite do formato Excel), mas a
# API do Sheets precisa do nome REAL e completo da aba — são duas constantes
# porque servem pra APIs diferentes, não é a mesma coisa em dois lugares.
NOME_ABA_XLSX = "Validação Regulatória de Public"
NOME_ABA_SHEETS = "Validação Regulatória de Publicações (SPA/+18)"
# A antiga coluna F (validação manual) foi excluída da planilha em 13/08/2026
# — a partir daqui a IA é a fonte definitiva. Backup dos valores que existiam
# nela: producao/auditorias/avisos-influenciadores-portaria136/backup_coluna_F_validacao_manual.json
COLUNA_IA = "F"  # coluna própria da IA — sempre reflete o último veredito automático (era G antes da exclusão da F)
COLUNA_MOTIVO = "G"  # só o vídeo específico problemático (nome + link direto pra ele no Drive) (era H antes)
COLUNA_ALERTA_AUDIO = "H"  # alerta de fala problemática detectada por transcrição de áudio — dimensão
# separada do veredito de aviso visual (coluna F): um post pode estar CONFORME no aviso e ainda
# assim ter um alerta de áudio, ou vice-versa. Vazio quando nenhum alerta foi detectado.
COLUNA_ALERTA_CRIANCA = "I"  # alerta de possível aparição de criança, sugerida por IA de visão
# local — dimensão própria, de gravidade muito maior que as outras, nunca crava o achado sozinha
# (ver checar_crianca_visual). Vazio quando nenhum alerta foi detectado.

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "auditorias", "avisos-influenciadores-portaria136")
CACHE_PATH = os.path.join(BASE_DIR, "resultados.json")
MIDIA_DIR = os.path.join(BASE_DIR, "midia")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(MIDIA_DIR, exist_ok=True)

MIME_EXT = {
    "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm", "video/x-m4v": ".m4v",
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
}


def classificar_link(link):
    if link is None:
        return "SEM_LINK", None
    if "/folders/" in link:
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", link)
        return "DRIVE_FOLDER", m.group(1) if m else None
    if "/file/d/" in link:
        m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", link)
        return "DRIVE_FILE", m.group(1) if m else None
    if any(dom in link for dom in ["instagram.com", "tiktok.com", "x.com", "twitter.com"]):
        return "EXTERNO_AO_VIVO", None
    return "OUTRO", None


def _nome_gravavel(nome):
    """Mesmo arquivo, nome que o Windows aceita gravar.

    O padrão de nome do Marketing é "DD/MM - @handle - tela N", e a barra é
    válida no Google Drive, que não é sistema de arquivos. Ao baixar pra
    analisar, gravar com esse nome faz o programa procurar uma pasta "14" que
    não existe: a gravação falha e a linha era classificada como "não consegui
    acessar o material", o que apontava pro lugar errado. Aconteceu em
    28/08/2026, logo depois de adotarmos a nomenclatura deles.

    O nome tratado vale só pro arquivo temporário em disco; o nome de verdade,
    que aparece na evidência e casa com a planilha, continua o do Drive."""
    for proibido in '/\\:*?"<>|':
        nome = nome.replace(proibido, "-")
    return nome


def nome_com_extensao(nome, mime_type):
    if os.path.splitext(nome)[1]:
        return nome
    return nome + MIME_EXT.get(mime_type, "")


def is_midia(mime_type):
    return mime_type.startswith("video/") or mime_type.startswith("image/")


ROTULOS_FALTANDO_CURTO = {
    "18": "18+",
    "portaria": "aviso da portaria",
    "publi": "aviso de publicidade",
    "responsabilidade": "jogue com responsabilidade",
    "ministerio_fazenda": "aviso do Ministério da Fazenda",
}


# PEÇA ORGÂNICA NÃO PASSA PELA RÉGUA REGULATÓRIA (03/09/2026).
#
# Decisão do auditor, e ele explicou o porquê antes de pedir: "orgânico não é
# fazendo propaganda, logo, ele não precisa colocar os avisos regulatórios pq ele
# ta so mostrando o patrocinio". E depois definiu o que a planilha deve mostrar:
# "se for organico, no monitoramento, pode constar como POST ORGÂNICO, NÃO
# VALIDADO ou algo nesse sentido, pra não fechar como NÃO CONFORME ou REQUER
# ANALISE HUMANA".
#
# POR QUE UM RÓTULO PRÓPRIO, e não CONFORME: dizer CONFORME afirmaria que a peça
# atende à régua, e ela nem foi medida por ela. E REQUER ANÁLISE HUMANA pediria
# trabalho de conferência que não tem o que conferir. As duas seriam informação
# errada numa coluna de auditoria.
#
# O QUE ISSO EVITA, medido na Monitoramento de teste em 03/09/2026: a régua atual
# reprovava peça orgânica por construção, porque o nome da marca ("lottu",
# "esportes da sorte", "eds", "onabet") entra em REGEX_CONTEUDO_APOSTA. Uma
# garrafa com a logo legível é lida como conteúdo de aposta, os quatro avisos não
# estão ali, e o veredito saía NÃO CONFORME. Achado falso, e do tipo que vira
# acusação numa planilha que outras áreas leem.
CLASSIFICACAO_ORGANICO = "Orgânico"
ROTULO_ORGANICO = "POST ORGÂNICO, NÃO VALIDADO"
# A situação da linha, que é outra coluna e outra pergunta: a validação diz o
# RESULTADO, a situação diz em que ponto do fluxo a linha está. A peça orgânica
# saiu da fila sem ser validada, e é isso que este valor diz.
SITUACAO_ORGANICO = "FORA DA VALIDAÇÃO (ORGÂNICO)"


def _rotulo_base(r):
    classe = r.get("classificacao")

    if classe == "Conforme":
        return "CONFORME"

    if classe == CLASSIFICACAO_ORGANICO:
        return ROTULO_ORGANICO

    if classe == "Não Conforme":
        faltando = r.get("faltando") or []
        if faltando:
            itens = [ROTULOS_FALTANDO_CURTO.get(f, f) for f in faltando]
            # "ILEGÍVEL OU AUSENTE", E NÃO "FALTA" (09/09/2026).
            #
            # O auditor viu duas peças de @crissevieri.mov reprovadas com
            # "Falta 18+, aviso da portaria, ...", e os avisos ESTAVAM na
            # peça: escritos na vertical, girados 90 graus na borda. Nenhum
            # dos três OCR lê texto girado, então o programa não leu, e o
            # rótulo afirmou ausência a partir de não ter lido.
            #
            # POR QUE ISSO É GRAVE, e não questão de gosto: "falta o 18+" é
            # uma afirmação que o influenciador derruba abrindo a peça e
            # apontando o selo. O veredito estava certo (aviso na vertical não
            # cumpre a exigência, que é o aviso estar legível), mas a
            # JUSTIFICATIVA estava errada, e justificativa errada custa a
            # credibilidade do achado inteiro.
            #
            # "Ilegível ou ausente" é verdade nos dois casos, é o que o
            # programa de fato sabe, e sustenta o NÃO CONFORME do mesmo jeito.
            # O mesmo cuidado já existe duas vezes no motor, para o item que a
            # visão sugere estar presente (ver validar_avisos_portaria136.py,
            # o comentário acima de ROTULO_ELEMENTO_FALTANTE e o do bloco que
            # separa itens ambíguos).
            return f"NÃO CONFORME (Ilegível ou ausente: {', '.join(itens)})"
        return "NÃO CONFORME"

    if classe == "Requer Verificação":
        motivo = r.get("motivo", "")
        if "pasta_vazia" in motivo or "Pasta sem arquivo" in motivo:
            return "PASTA VAZIA"
        if "Falha ao acessar" in motivo:
            return "SEM ACESSO À PASTA"
        if "fora do escopo automático" in motivo:
            return "NÃO FOI POSSÍVEL ANALISAR (LINK DE REDE SOCIAL)"
        if "degradação técnica" in motivo or "qualidade da imagem" in motivo:
            return "REQUER ANÁLISE HUMANA"
        # O RÓTULO CURTO DIZ O QUE CONFERIR (02/09/2026), E ISSO VEIO DO FLUXO
        # QUE O AUDITOR DESCREVEU.
        #
        # Nele, o registro fica na Monitoramento e é ela que a analista lê:
        # CONFORME ela nem consulta; NÃO CONFORME ela vê o motivo e sinaliza a
        # coordenação; REQUER ANÁLISE ela vai verificar o motivo. Ou seja, esta
        # coluna é a PRIMEIRA COISA que a pessoa lê, e o Não Conforme já nomeia
        # o item ("NÃO CONFORME (Ilegível ou ausente: 18+, publi)"). O Requer
        # Análise não nomeava nada útil.
        #
        # O QUE ESTAVA AQUI ANTES, e enganou o próprio auditor: o rótulo era
        # "REQUER ANÁLISE HUMANA (aviso pequeno/baixo contraste)", escolhido por
        # procurar as palavras "texto pequeno" no motivo. Ele leu isso no caso do
        # @andersonneiff e concluiu "achei bem ok", quando o publi não estava na
        # peça e o rodapé estava perfeitamente legível. O rótulo afirmava uma
        # causa que o programa não conhecia.
        #
        # Agora ele nomeia O ITEM, que é o que a pessoa precisa saber para abrir
        # o vídeo e responder a pergunta da régua: está na tela?
        alvo = re.search(r"CONFERIR NA PEÇA:\s*(.+?)\s+está na tela\?", motivo)
        if alvo:
            return f"REQUER ANÁLISE HUMANA (conferir na tela: {alvo.group(1)})"
        if "não foi lido" in motivo and "mesmo aviso" in motivo:
            # Caso do banner do rodapé: um item não lido, outro do mesmo banner
            # confirmado. O item já vem nomeado no motivo.
            item = re.search(r"mas\s+(.+?)\s+não foi lido", motivo)
            if item:
                return f"REQUER ANÁLISE HUMANA (conferir na tela: {item.group(1)})"
        if "exige análise manual" in motivo:
            return "REQUER ANÁLISE HUMANA"
        # Ambíguo (ex: nenhum conteúdo de aposta detectado no material)
        return "REQUER ANÁLISE HUMANA"

    return None


def formatar_para_planilha(r):
    """Converte o resultado da IA pra um rótulo curto e padronizado da coluna F.
    Sem prefixo de IA, sem justificativa longa — só o veredito (CONFORME/NÃO
    CONFORME, em caixa alta por convenção) e, quando aplicável, uma observação
    curta entre parênteses nomeando o elemento que não foi encontrado de forma
    legível (não afirma que ele está ausente: ver o comentário em
    _rotulo_base, caso do aviso escrito na vertical) (em texto
    normal, não caixa alta — no mesmo estilo das observações manuais já usadas
    na planilha). O detalhe completo (motivo, evidência) continua disponível
    no cache local e na tabela do app.

    O alerta de fala problemática (achado por transcrição de áudio) NÃO entra
    aqui — é uma dimensão separada da análise (áudio vs. aviso visual), então
    vai na coluna própria (ver formatar_alerta_audio / COLUNA_ALERTA_AUDIO),
    não misturado neste rótulo."""
    return _rotulo_base(r)


def formatar_alerta_audio(r):
    """Rótulo da coluna própria de alerta de fala problemática (achado por
    transcrição de áudio local — ilusão de controle, promessa de
    enriquecimento, sugestão de repetibilidade do ganho, ver
    checar_fala_problematica). Vazio quando nenhum alerta foi detectado.

    Isso NUNCA crava violação sozinho — a transcrição de fala pode errar por
    sotaque/ruído/corte, então é só um pedido de conferência humana pontual
    pra esse ponto específico, independente do veredito da coluna F (um post
    pode estar CONFORME no aviso visual e ainda ter esse alerta, ou vice-versa)."""
    alertas = r.get("alerta_audio") or []
    if not alertas:
        return ""
    categorias = ", ".join(sorted({a["categoria"] for a in alertas}))
    return f"REQUER ANÁLISE DE ÁUDIO (possível fala problemática: {categorias})"


def formatar_alerta_crianca(r):
    """Rótulo da coluna própria de alerta de possível aparição de criança
    (sugerido por IA de visão local, ver checar_crianca_visual). Vazio quando
    nenhum alerta foi detectado.

    Gravidade muito maior que os outros alertas desta planilha — por isso o
    texto é deliberadamente mais enfático (PRIORITÁRIO) — mas o princípio é o
    mesmo: NUNCA crava o achado sozinho, o modelo pode alucinar. Sempre exige
    conferência humana, nunca um veredito automático.

    Com a checagem desligada (motor.CHECAR_CRIANCA_VISUAL), a célula NÃO fica
    em branco: diz que não houve verificação. Em branco seria lido como
    "conferido e sem criança", que é diferente de "não foi conferido"."""
    if not motor.CHECAR_CRIANCA_VISUAL:
        return ("não verificado (checagem automática de aparição de criança "
                "desligada em 28/08/2026 por custo de processamento)")
    arquivos = r.get("alerta_crianca") or []
    if not arquivos:
        return ""
    return f"⚠️ REQUER CONFERÊNCIA HUMANA PRIORITÁRIA (possível aparição de criança: {', '.join(arquivos)})"


def formatar_video_problema(r, nota_extra=None, como_formula=True):
    """Aponta só qual vídeo específico é o problema (nome do arquivo + link
    direto pra ele no Drive, se disponível). De propósito sem o texto longo do
    motivo completo (isso deixava a célula enorme); o detalhe completo continua
    disponível no cache local e na tabela do app.

    Usa a fórmula HYPERLINK em vez de só colar "nome — url" como texto: o
    Google Sheets às vezes não reconhece o link automaticamente quando ele
    vem misturado com texto antes dele, deixando alguns links clicáveis e
    outros não — a fórmula garante que sempre fique clicável.

    `nota_extra`: texto curto opcional (ex: aviso de link duplicado com outra
    linha) que entra no rótulo visível do link, sem quebrar a fórmula.

    `como_formula=False` DEVOLVE TEXTO, e existe por causa de um defeito real
    (02/09/2026). Célula do Sheets é fórmula OU texto, nunca as duas: quem
    juntar o resultado desta função com mais texto na mesma célula produz
    `=HYPERLINK(...) | resto`, que não é fórmula válida, e a célula inteira vira
    **#ERROR!**. O veredito e a evidência somem da vista de quem lê a planilha.

    Foi o que aconteceu com a coluna EVIDENCIA da Monitoramento, onde esta
    função é uma das três partes juntadas por _evidencia_para_planilha. A coluna
    da planilha da auditoria não sofre disso porque lá a fórmula fica sozinha na
    célula, e as 171 que existem lá funcionam.

    SOBRE O PONTO E VÍRGULA, para ninguém "consertar" o que está certo: o
    separador de argumentos de fórmula segue o IDIOMA DA PLANILHA, e as quatro
    planilhas deste projeto são pt_BR, onde o separador é `;`. Conferido em
    02/09/2026 lendo `properties.locale` de cada uma. Trocar por vírgula
    quebraria as 171 fórmulas que hoje funcionam."""
    arquivo = r.get("arquivo")
    if not arquivo:
        return f"({nota_extra})" if nota_extra else ""
    label = arquivo + (f" ({nota_extra})" if nota_extra else "")
    link = r.get("link_video_problema")
    if not link:
        return label
    if not como_formula:
        return f"{label} — {link}"
    label_escapado = label.replace('"', '""')
    return f'=HYPERLINK("{link}";"{label_escapado}")'


def _data_para_iso(valor):
    """A Monitoramento escreve data como 12/08/2026 ou 12/08/26. Devolve
    AAAA-MM-DD, que é o formato que o resto do programa usa para decidir qual
    aviso a data exige."""
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def carregar_monitoramento():
    """Lê a fila de validação direto da Monitoramento.

    Desde 28/08/2026 é ela a fonte única: o download grava o link do arquivo e
    a situação, e daqui sai a fila.

    Uma linha entra na fila quando a SITUACAO diz que há arquivo baixado para
    conferir (ver fluxo.tem_arquivo_para_analisar). O endereço do vídeo vem da
    coluna LINK. Nas linhas criadas pela automação essa coluna guarda o
    arquivo específico; nas que o Marketing preenche à mão ela aponta para a
    pasta do mês, e essas linhas ficam de fora porque a situação delas está
    vazia. Isso é limitação conhecida e anterior a esta leitura.

    Até 29/08/2026 o gatilho era uma coluna própria com o link do arquivo, que
    repetia na planilha o mesmo endereço da coluna LINK.

    Devolve as linhas no mesmo formato que o resto do programa já esperava, pra
    tela e pipeline não precisarem saber de onde vieram."""
    import sheets_client
    import fluxo_downloads as fluxo

    planilha = fluxo._planilha_monitoramento_id()
    if not planilha:
        return []
    fluxo.garantir_cabecalhos_automacao(planilha)

    ultima = fluxo.ULTIMA_COLUNA_MON
    valores = sheets_client.executar(lambda: sheets_client.get_service().spreadsheets().values().get(
        spreadsheetId=planilha,
        range=f"'{fluxo.ABA_MONITORAMENTO}'!A2:{ultima}20000").execute()).get("values", [])

    # A largura tem que alcançar a última coluna que este leitor USA, e desde
    # 03/09/2026 ele lê a coluna ARQUIVO, que vem depois de validado_em. Com a
    # largura antiga, a linha era preenchida só até validado_em e o arquivo
    # aparecia como vazio: a análise concluiria que não há o que analisar.
    largura = max(fluxo.COL_MON["validado_em"], fluxo.COL_MON["arquivo"])
    linhas = []
    for i, bruta in enumerate(valores, start=2):
        linha = list(bruta) + [""] * (largura - len(bruta))

        def campo(chave):
            return str(linha[fluxo.COL_MON[chave] - 1] or "").strip()

        # O gatilho é a SITUACAO, não uma coluna própria de link (mudança de
        # 29/08/2026, ver BLOCO_AUTOMACAO em fluxo_downloads). A situação diz se
        # aquela linha tem arquivo baixado para conferir.
        #
        # DE ONDE VEM O ENDEREÇO, em ordem (03/09/2026):
        #
        #   1. coluna ARQUIVO, que é a peça exata daquela linha
        #   2. coluna LINK, para as linhas criadas até 02/09 e para link externo
        #
        # A ORDEM NÃO PODE SER INVERTIDA, e o motivo é grave: desde 03/09 a
        # coluna LINK aponta para a PASTA do post, porque entrega do mesmo dia é
        # um post só. E este leitor sabe abrir pasta (DRIVE_FOLDER). Lendo LINK
        # primeiro, cada linha do dia analisaria TODOS os arquivos do dia:
        # quatro peças viram dezesseis análises, e o veredito de cada linha
        # misturaria as quatro. A evidência por peça, que é o motivo de a coluna
        # ARQUIVO existir, é justamente o que se perderia.
        link_arquivo = campo("arquivo") or campo("link")
        if not link_arquivo or not fluxo.tem_arquivo_para_analisar(campo("situacao")):
            continue  # sem arquivo não há o que analisar
        tipo_link, drive_id = classificar_link(link_arquivo)
        linhas.append({
            "excel_row": i,
            "influenciador": campo("handle"),
            "tipo_post": campo("tipo"),
            "data": _data_para_iso(campo("data_post")),
            # Quando o material foi CAPTURADO, que não é a data do post. Passou
            # a ser lido em 29/08/2026 porque é por ele que se separa "o que
            # baixei hoje" de "o que baixei ontem", que é como as pessoas
            # pensam na hora de escolher o que mandar analisar.
            "data_download": campo("data_download"),
            "link": link_arquivo,
            "tipo_link": tipo_link,
            "drive_id": drive_id,
            "veredito_na_planilha": campo("validacao"),
            "situacao": campo("situacao"),
            # QUEM BAIXOU (22/09/2026). Passou a ser lido para o
            # analisar_pendentes.py poder varrer as linhas de UMA pessoa só:
            # a máquina da Responsável B baixa mas não analisa, e a varredura tem
            # que alcançar as linhas dela sem tocar nas de quem está
            # funcionando normal.
            "pedido_por": campo("pedido_por"),
            # A MARCAÇÃO ENTRA AQUI (03/09/2026) porque ela decide se a linha
            # passa pela régua regulatória. Ver processar_organico.
            "marcacao": campo("marcacao"),
        })
    return linhas


def carregar_planilha():
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "planilha.xlsx")
        drive_client.export_file(
            PLANILHA_ID,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            dest,
        )
        wb = openpyxl.load_workbook(dest, data_only=True)
        ws = wb[NOME_ABA_XLSX]
        linhas = []
        for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True), start=2):
            # Indexação em vez de desempacotar a tupla inteira: a planilha pode
            # ter mais colunas do que A-E (ex: F com o veredito da IA, ou G em
            # diante que alguém adicione depois) sem quebrar a leitura. A antiga
            # coluna F (validação manual) foi excluída — não existe mais
            # gabarito humano pra ler aqui, a IA é a fonte definitiva agora.
            influ, ano, data, tipo, link = row[0], row[1], row[2], row[3], row[4]
            if link is None:
                continue
            data_str = data.strftime("%Y-%m-%d") if hasattr(data, "strftime") else (str(data)[:10] if data else None)
            tipo_link, drive_id = classificar_link(link)
            linhas.append({
                "excel_row": i,
                "influenciador": influ,
                "tipo_post": tipo,
                "data": data_str,
                "link": link,
                "tipo_link": tipo_link,
                "drive_id": drive_id,
            })
        return linhas


def carregar_cache():
    """Lê as análises já feitas. Se o arquivo estiver ilegível, tenta a cópia
    de segurança em vez de derrubar o programa na abertura: sem isso, um
    arquivo corrompido deixava o app sem abrir, e não havia como chegar na
    tela pra entender o que houve."""
    def _abrir(caminho):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)

    for caminho in (CACHE_PATH, CACHE_PATH + ".bak"):
        if not os.path.exists(caminho):
            continue
        try:
            # Insiste alguns instantes antes de desistir: desde 29/08/2026 o
            # trabalhador grava este arquivo enquanto a tela o lê, e no Windows
            # a troca do arquivo bloqueia a leitura por milissegundos. Desistir
            # nessa fração de segundo devolveria vazio, que aqui quer dizer
            # "nada foi analisado ainda" e mandaria refazer tudo de novo.
            dados = trava.ler_insistindo(caminho, _abrir)
            if caminho.endswith(".bak"):
                print(f"[aviso] {CACHE_PATH} estava ilegível; usei a cópia de segurança.")
            return dados
        except (ValueError, OSError) as e:
            print(f"[aviso] não consegui ler {caminho}: {e}")
    return {}


def _salvar_cache_sem_travar(cache):
    """Grava em arquivo temporário e só então troca pelo definitivo.

    Antes abria o arquivo final direto em modo de escrita, o que apaga o
    conteúdo ANTES de gravar: uma interrupção no meio (fechar o programa,
    faltar luz, o Streamlit recarregar) deixava o arquivo cortado e levava
    junto todas as análises já feitas. Com a troca no final, ou o arquivo
    antigo continua inteiro, ou o novo já está completo; nunca um meio termo.
    Guarda também a última versão boa como .bak, rede de segurança extra.

    Quem chama precisa já estar segurando a trava do arquivo. Use
    salvar_cache ou registrar_no_cache, que cuidam disso."""
    temporario = CACHE_PATH + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    if os.path.exists(CACHE_PATH):
        try:
            shutil.copy2(CACHE_PATH, CACHE_PATH + ".bak")
        except OSError:
            pass  # não conseguir fazer a cópia extra não pode impedir a gravação
    trava.substituir(temporario, CACHE_PATH)


def salvar_cache(cache):
    """Grava o registro inteiro de análises já feitas."""
    with trava.travar(CACHE_PATH):
        _salvar_cache_sem_travar(cache)


def registrar_no_cache(link, resultado):
    """Guarda a análise de UM vídeo, relendo o arquivo antes de gravar.

    Existe desde 29/08/2026 por causa do trabalhador. Ele guardava o registro
    inteiro em memória e regravava tudo a cada análise, o que desfazia
    qualquer alteração feita por outro caminho enquanto ele rodava: se alguém
    apagasse as análises guardadas pela tela no meio de um lote, elas voltavam
    todas na gravação seguinte. Relendo dentro da trava, só a análise nova é
    acrescentada ao que estiver valendo naquele momento."""
    with trava.travar(CACHE_PATH):
        cache = carregar_cache()
        cache[link] = resultado
        _salvar_cache_sem_travar(cache)


def zerar_cache():
    """Faz backup do cache atual (resultados_backup_<timestamp>.json) e zera
    resultados.json. Usado antes de uma rodada oficial pra garantir que
    resquício de teste/análise anterior não entre na prévia de escrita da
    coluna G nem nas estatísticas do painel."""
    with trava.travar(CACHE_PATH):
        cache = carregar_cache()
        if cache:
            backup_path = os.path.join(BASE_DIR, f"resultados_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        _salvar_cache_sem_travar({})


# JANELA DE PROPAGAÇÃO DO DRIVE, MEDIDA EM 22/09/2026.
#
# O vídeo sobe pelo token de ESCRITA (drive_file_token.json, escopo
# drive.file) e a análise tenta lê-lo segundos depois pelo token de LEITURA
# (drive_token.json, escopo drive.readonly), que é OUTRA autorização. O
# Google leva alguns segundos para tornar um arquivo recém-criado visível
# para uma autorização diferente da que o criou, e nessa janela a leitura
# volta 404.
#
# O QUE ISSO CAUSAVA: `_com_retentativas`, em drive_client.py, só repete em
# erro de rede (SSLError, ConnectionError, TimeoutError, OSError). HttpError
# não herda de nenhum desses, então o 404 falhava de primeira, sem segunda
# tentativa, e a linha era carimbada "SEM ACESSO À PASTA". Como
# gravar_veredito só escreve em célula vazia, a linha nunca mais era
# reanalisada sozinha: um tropeço de segundos virava rótulo permanente.
#
# MEDIDO, na Monitoramento de teste, em 22/09/2026: a linha 99
# (@dudafreiret) foi analisada às 15:05, com o arquivo criado às 15:05:18, e
# levou SEM ACESSO À PASTA. A linha 100, mesma pessoa, mesma máquina, mesmos
# tokens, analisada às 15:07, fechou CONFORME. O arquivo da linha 99 abre
# normalmente pelo token de leitura quando consultado depois, o que descarta
# permissão quebrada.
#
# POR QUE ESPERAR NÃO CUSTA: isto roda em fila, em segundo plano, sem
# ninguém olhando. 404 de verdade (arquivo que não existe mesmo) continua
# falhando, só que alguns segundos depois.
#
# NÃO COBRE, de propósito, o caso "pasta_vazia_ou_sem_midia": ele pode ter a
# mesma causa (a pasta aparece, o arquivo novo ainda não), mas isso não foi
# medido, e pasta legitimamente vazia é estado normal. Se aparecer evidência,
# o lugar de tratar é aqui.
TENTATIVAS_ACESSO_DRIVE = 3
ESPERA_ENTRE_TENTATIVAS_S = 5


def _e_janela_de_propagacao(erro):
    """404 ou 403 vindos da API do Drive, que é como a janela de propagação
    se manifesta. Qualquer outro erro não é repetido: repetir erro de
    verdade só atrasa o resultado sem mudar nada."""
    from googleapiclient.errors import HttpError
    if not isinstance(erro, HttpError):
        return False
    return getattr(getattr(erro, "resp", None), "status", None) in (403, 404)


def _buscar_material_do_drive(linha, row_dir, arquivos, drive_id_por_nome):
    """Baixa para `row_dir` o que a linha aponta no Drive.

    Preenche `arquivos` e `drive_id_por_nome` no lugar, em vez de devolver,
    para quem chama poder zerar os dois entre tentativas. Deixa a exceção
    subir: quem decide se repete é processar_linha, olhando se foi a janela
    de propagação (ver _e_janela_de_propagacao)."""
    if linha["tipo_link"] == "DRIVE_FOLDER":
        # Confirma acesso à PASTA em si antes de listar o conteúdo dela: a
        # API do Drive não dá erro quando a busca por filhos não encontra
        # nada (pasta sem permissão ou ID inválido também retornam lista
        # vazia, sem exceção) — sem essa checagem, "sem acesso" e "pasta
        # vazia" ficam indistinguíveis e a linha é mal classificada.
        drive_client.get_metadata(linha["drive_id"])
        arquivos_drive = drive_client.list_folder(linha["drive_id"])
        midia = [a for a in arquivos_drive if is_midia(a.get("mimeType", ""))]
        for a in midia:
            nome = nome_com_extensao(a["name"], a.get("mimeType", ""))
            dest = os.path.join(row_dir, _nome_gravavel(nome))
            drive_client.download_file(a["id"], dest)
            arquivos.append(dest)
            drive_id_por_nome[nome] = a["id"]
    elif linha["tipo_link"] == "DRIVE_FILE":
        meta = drive_client.get_metadata(linha["drive_id"])
        nome = nome_com_extensao(meta.get("name", linha["drive_id"]), meta.get("mimeType", ""))
        dest = os.path.join(row_dir, _nome_gravavel(nome))
        drive_client.download_file(linha["drive_id"], dest)
        arquivos.append(dest)
        drive_id_por_nome[nome] = linha["drive_id"]


def processar_linha(linha):
    import time

    row_dir = os.path.join(MIDIA_DIR, f"linha_{linha['excel_row']}")
    os.makedirs(row_dir, exist_ok=True)
    arquivos = []
    drive_id_por_nome = {}
    erro = None

    for _tentativa in range(1, TENTATIVAS_ACESSO_DRIVE + 1):
        # Zera a cada tentativa: sem isso, uma tentativa que baixou parte dos
        # arquivos antes de falhar deixaria resto acumulado na seguinte.
        arquivos = []
        drive_id_por_nome = {}
        erro = None
        try:
            _buscar_material_do_drive(linha, row_dir, arquivos, drive_id_por_nome)
        except Exception as e:
            erro = str(e)
            if _e_janela_de_propagacao(e) and _tentativa < TENTATIVAS_ACESSO_DRIVE:
                time.sleep(ESPERA_ENTRE_TENTATIVAS_S)
                continue
        else:
            if erro is None and not arquivos:
                erro = "pasta_vazia_ou_sem_midia"
        break

    if erro:
        resultado = {"classificacao": "Requer Verificação", "motivo": f"Falha ao acessar material: {erro}", "evidencia": ""}
    else:
        try:
            # Protegido de propósito: essa etapa envolve ffmpeg/Tesseract/
            # EasyOCR/Ollama, várias peças externas que podem falhar de jeitos
            # imprevisíveis (processo travado, binário ausente, resposta
            # malformada). Sem isso, um erro inesperado numa única linha
            # derrubava o lote inteiro — crítico pra rodadas longas sem
            # ninguém por perto pra reiniciar (ex: rodando durante a noite).
            resultado = motor.classificar_post(arquivos, row_dir, post_date=linha["data"])
            # Link direto pro vídeo específico apontado como problema (pior clipe) —
            # usado na coluna H, pra não precisar abrir a pasta inteira do post.
            arquivo_problema = resultado.get("arquivo")
            if arquivo_problema and arquivo_problema in drive_id_por_nome:
                resultado["link_video_problema"] = f"https://drive.google.com/file/d/{drive_id_por_nome[arquivo_problema]}/view"
        except Exception as e:
            resultado = {
                "classificacao": "Requer Verificação",
                "motivo": f"Erro inesperado ao analisar o material: {e}",
                "evidencia": "",
            }

    # Apaga a mídia bruta baixada E os frames extraídos (row_dir inteiro) —
    # achado real: numa sessão de testes de um dia só, isso acumulou quase 1GB
    # em milhares de arquivos sem nunca ser limpo. Numa rodada de centenas de
    # linhas durante a noite, sem ninguém pra perceber o disco enchendo, isso
    # pode travar o processamento inteiro. O texto completo da evidência
    # (achou_*, trechos de OCR) já fica salvo no cache/planilha — as imagens
    # em si não precisam sobreviver depois de processadas.
    try:
        shutil.rmtree(row_dir, ignore_errors=True)
    except OSError:
        pass

    return {**linha, **resultado, "processado_em": datetime.now().strftime("%Y-%m-%d %H:%M")}


def processar_linha_protegida(linha):
    """Mesma coisa que processar_linha, mas nunca levanta erro: qualquer
    imprevisto vira 'Requer Verificação' e a rodada continua. Existe pra ser
    chamada em outro processo, onde um erro solto derrubaria o trabalhador.

    PEÇA ORGÂNICA É BARRADA AQUI TAMBÉM (03/09/2026), e não só na entrega do
    trabalhador. Não é redundância inútil: esta é a função que qualquer caminho
    novo vai chamar para analisar uma linha, e sem a conferência aqui um caminho
    futuro voltaria a gastar 110 segundos por peça orgânica e a escrever um
    veredito de régua que não se aplica a ela. Custa uma leitura de célula."""
    try:
        if e_linha_organica(linha):
            return processar_organico(linha)
        return processar_linha(linha)
    except Exception as e:
        return {**linha, "classificacao": "Requer Verificação",
                "motivo": f"Erro inesperado ao processar a linha: {e}", "evidencia": "",
                "processado_em": datetime.now().strftime("%Y-%m-%d %H:%M")}


# Quantos vídeos analisar ao mesmo tempo.
#
# O limite aqui NÃO é só o número de núcleos: o modelo de visão roda num
# processo à parte (llama-server), é UM só pra todos os trabalhadores, e come
# sozinho perto de 6 núcleos. Medido em 27/08/2026 nesta máquina de 12
# núcleos: llama-server 5,9 núcleos + um trabalhador 3,8 núcleos. Com 3
# trabalhadores a conta pedia 9 + 6 = 15 núcleos numa máquina de 12, e todos
# passavam mais tempo esperando do que calculando (o lote ficou 9 minutos sem
# concluir uma linha sequer).
#
# Quantas linhas analisar ao mesmo tempo.
#
# Em 28/08/2026 medimos 1 trabalhador em uso real: 4 linhas, 8 vídeos, três
# intervalos consistentes de 180s, 180s e 200s por vídeo, ou seja 185s por
# vídeo (19,3 vídeos por hora). Durante essa medição a máquina usava só 3 dos
# 12 núcleos.
#
# Comparação feita no mesmo dia, sempre em uso real:
#
#   1 ao mesmo tempo:  185s por vídeo   (4 linhas, 10 arquivos, 25 min)
#   2 ao mesmo tempo:  110s por vídeo   (10 linhas, 25 arquivos, 46 min)
#   3 ao mesmo tempo:  107 a 129s       (7 linhas, 14 arquivos, ~25 a 30 min)
#
# De 1 para 2 o ganho é real, 1,68x. De 2 para 3 não há ganho: o gargalo volta
# a ser o modelo de visão, que roda num servidor único compartilhado por todos
# os processos, então a partir daí eles só se enfileiram nele. Por isso 2.
TRABALHADORES_PADRAO = 2


def gravar_veredito(excel_rows, resultado):
    """Escreve o veredito de UMA análise nas linhas da Monitoramento que
    apontam para aquele mesmo arquivo.

    Recebe uma lista de linhas porque o mesmo arquivo pode estar em mais de uma
    linha: nesse caso a análise roda uma vez e o resultado vale para todas, em
    vez de gastar processamento repetido e arriscar vereditos diferentes para o
    mesmo vídeo.

    Só escreve em célula VAZIA. Se alguém já anotou algo ali, a anotação da
    pessoa manda e a automação não passa por cima. Para reprocessar, apaga-se a
    célula. É previsível e não exige controle de versão nenhum."""
    import sheets_client
    import fluxo_downloads as fluxo

    planilha = fluxo._planilha_monitoramento_id()
    if not planilha or not excel_rows:
        return 0

    aba = fluxo.ABA_MONITORAMENTO
    col_validacao = fluxo.letra_da_coluna(fluxo.COL_MON["validacao"])
    ja_preenchidas = sheets_client.ler_coluna(planilha, aba, col_validacao, excel_rows)
    alvos = [n for n in excel_rows if not str(ja_preenchidas.get(n) or "").strip()]
    if not alvos:
        return 0

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # A SITUAÇÃO DA PEÇA ORGÂNICA NÃO É "VALIDADO" (03/09/2026).
    #
    # Escrever VALIDADO ao lado de um veredito que diz "NÃO VALIDADO" seria a
    # planilha se contradizendo em duas colunas vizinhas. A peça saiu da fila,
    # que é o que a situação precisa dizer, mas ninguém a validou: os avisos não
    # se aplicam a ela. Ver CLASSIFICACAO_ORGANICO.
    e_organico = resultado.get("classificacao") == CLASSIFICACAO_ORGANICO
    conteudo = {
        "validacao": formatar_para_planilha(resultado) or "",
        "evidencia": _evidencia_para_planilha(resultado),
        "validado_em": agora,
        "situacao": SITUACAO_ORGANICO if e_organico else fluxo.VALIDADO,
    }
    for chave, valor in conteudo.items():
        letra = fluxo.letra_da_coluna(fluxo.COL_MON[chave])
        sheets_client.escrever_lote(planilha, aba, letra, [(n, valor) for n in alvos])
    return len(alvos)


# Rótulo de linha que não deve ser analisada. Fica na mesma coluna do veredito
# de propósito: é ela que decide se a linha está na fila, então a saída da fila
# tem que passar por ali. Como a automação só escreve em célula vazia, uma
# linha marcada assim não é tocada por mais nada.
FORA_DA_ANALISE = "FORA DA ANÁLISE"


def marcar_fora_da_analise(excel_rows, motivo, quem):
    """Tira linhas da fila de validação sem analisar, deixando registrado o
    porquê, quem pediu e quando.

    Existe desde 29/08/2026, pedido do auditor durante o teste: uma vez
    baixado, o vídeo entrava na lista de pendentes e não saía mais de lá até
    receber um veredito, mesmo quando o download tinha sido por engano.

    O registro NÃO é enfeite. Numa auditoria, material que entrou e saiu do
    escopo precisa ter motivo e responsável, senão daqui a três meses ninguém
    sabe dizer se aquele vídeo foi analisado, foi descartado de propósito, ou
    passou batido. Por isso a linha não é apagada nem esvaziada: ela ganha um
    rótulo que diz o que aconteceu.

    Nada é apagado do Drive aqui. O arquivo continua onde está."""
    import sheets_client
    import fluxo_downloads as fluxo

    planilha = fluxo._planilha_monitoramento_id()
    if not planilha or not excel_rows:
        return 0

    aba = fluxo.ABA_MONITORAMENTO
    col_validacao = fluxo.letra_da_coluna(fluxo.COL_MON["validacao"])
    # Mesma regra da gravação de veredito: só mexe em célula vazia. Se alguém
    # já anotou algo ali, a anotação da pessoa manda.
    ja_preenchidas = sheets_client.ler_coluna(planilha, aba, col_validacao, excel_rows)
    alvos = [n for n in excel_rows if not str(ja_preenchidas.get(n) or "").strip()]
    if not alvos:
        return 0

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    texto_motivo = str(motivo or "").strip() or "sem motivo informado"
    conteudo = {
        "validacao": FORA_DA_ANALISE,
        "evidencia": f"Tirado da análise por {quem} em {agora}. Motivo: {texto_motivo}",
        "validado_em": agora,
        "situacao": FORA_DA_ANALISE,
    }
    for chave, valor in conteudo.items():
        letra = fluxo.letra_da_coluna(fluxo.COL_MON[chave])
        sheets_client.escrever_lote(planilha, aba, letra, [(n, valor) for n in alvos])
    return len(alvos)


def devolver_para_analise(excel_rows):
    """Desfaz o "fora da análise": limpa as células e a linha volta pra fila.

    Só mexe em linha que está marcada como fora da análise. Isso é proposital:
    limpar uma célula sem olhar o que tem nela poderia apagar um veredito de
    verdade, ou uma anotação que alguém escreveu à mão."""
    import sheets_client
    import fluxo_downloads as fluxo

    planilha = fluxo._planilha_monitoramento_id()
    if not planilha or not excel_rows:
        return 0

    aba = fluxo.ABA_MONITORAMENTO
    col_validacao = fluxo.letra_da_coluna(fluxo.COL_MON["validacao"])
    atuais = sheets_client.ler_coluna(planilha, aba, col_validacao, excel_rows)
    alvos = [n for n in excel_rows
             if str(atuais.get(n) or "").strip() == FORA_DA_ANALISE]
    if not alvos:
        return 0

    conteudo = {
        "validacao": "",
        "evidencia": "",
        "validado_em": "",
        "situacao": fluxo.AGUARDANDO_VALIDACAO,
    }
    for chave, valor in conteudo.items():
        letra = fluxo.letra_da_coluna(fluxo.COL_MON[chave])
        sheets_client.escrever_lote(planilha, aba, letra, [(n, valor) for n in alvos])
    return len(alvos)


def _evidencia_para_planilha(r):
    """Junta, numa célula só, o que sustenta o veredito: o arquivo específico
    com problema, o alerta de áudio e a evidência de texto. Existe para quem
    contestar o resultado ter como conferir sem abrir o programa.

    EM TEXTO, NUNCA EM FÓRMULA, e isso corrige um defeito real (02/09/2026).

    Célula do Sheets é fórmula OU texto, nunca as duas. Como esta função JUNTA
    três pedaços, o primeiro deles não pode ser uma fórmula: o resultado era
    `=HYPERLINK(...) | resto`, que não é fórmula válida, e a célula inteira virava
    **#ERROR!**. O efeito era o pior possível para quem lê a planilha: a
    evidência que sustenta o veredito desaparecia da vista.

    Achado pelo auditor em 02/09/2026, olhando a coluna EVIDENCIA: seis linhas
    seguidas com #ERROR!, todas as criadas depois que o link do arquivo passou a
    existir. As linhas antigas escapavam por acidente, porque naquelas o arquivo
    não tinha link e a função devolvia texto puro.

    NÃO É PROBLEMA DE SEPARADOR, e isso foi conferido antes de mexer: as quatro
    planilhas do projeto são pt_BR, onde o separador de argumentos é `;`, e as
    171 fórmulas HYPERLINK da planilha da auditoria funcionam. Trocar por vírgula
    quebraria as 171. O que quebra é juntar fórmula com texto."""
    partes = []
    problema = formatar_video_problema(r, como_formula=False)
    if problema:
        partes.append(problema)
    audio = formatar_alerta_audio(r)
    if audio:
        partes.append(audio)
    evidencia = str(r.get("evidencia") or "").strip()
    if evidencia:
        partes.append(evidencia)
    return " | ".join(partes)[:4000]  # célula do Sheets tem limite de tamanho


def abrir_equipe(trabalhadores=TRABALHADORES_PADRAO):
    """Cria a equipe de processos que vai analisar vários vídeos ao mesmo
    tempo. Cada processo carrega os modelos uma vez só e fica de pé até o fim
    do lote, senão o custo de carregar (o modelo de visão sozinho leva perto
    de 2 minutos na primeira chamada) comeria o ganho."""
    from concurrent.futures import ProcessPoolExecutor
    return ProcessPoolExecutor(max_workers=trabalhadores)


def processar_fora_do_escopo(linha):
    """Pra links de Instagram/TikTok/X ao vivo — nunca dá pra baixar pelo Drive,
    então não tem OCR nem download aqui, só marca a linha como fora do alcance
    da automação (instantâneo, sem custo de rede)."""
    resultado = {
        "classificacao": "Requer Verificação",
        "motivo": "Link de rede social ao vivo — fora do escopo automático (Instagram/TikTok/X)",
        "evidencia": "",
    }
    return {**linha, **resultado, "processado_em": datetime.now().strftime("%Y-%m-%d %H:%M")}


def e_linha_organica(linha):
    """Se aquela linha da Monitoramento está marcada como peça orgânica.

    Lê pela função do fluxo, e não comparando texto: a coluna tem "SIM" nas
    linhas gravadas até 02/09/2026 e "ORGANICO" nas novas, e as duas querem
    dizer a mesma coisa.

    O import fica DENTRO da função, como em todo este arquivo: ele roda também
    dentro dos processos da equipe de análise, e importar o fluxo no topo
    carregaria o cliente do Drive e do Sheets em cada um deles."""
    import fluxo_downloads as fluxo
    return fluxo.marcacao_de_celula(linha.get("marcacao")) == "organico"


def processar_organico(linha):
    """Peça orgânica: não passa pela régua regulatória, e não é analisada.

    Instantâneo e sem custo de rede, igual a processar_fora_do_escopo: não baixa
    o arquivo, não roda OCR, não chama a IA de visão e não transcreve áudio. Ver
    CLASSIFICACAO_ORGANICO para a decisão do auditor e para o achado falso que
    isto evita.

    O GANHO NÃO É SÓ DE VEREDITO: a análise leva perto de 110 segundos por vídeo
    nesta máquina, e 81% disso é a IA de visão. Peça orgânica deixa de gastar
    esse tempo, e numa fila com material orgânico junto isso libera a vez para o
    que precisa de análise."""
    resultado = {
        "classificacao": CLASSIFICACAO_ORGANICO,
        "motivo": ("Peça marcada como orgânica na hora do download: só mostra a "
                   "marca, sem anunciar jogo e sem link, então os avisos da "
                   "portaria não se aplicam e ela não passa pela régua"),
        "evidencia": "",
    }
    return {**linha, **resultado, "processado_em": datetime.now().strftime("%Y-%m-%d %H:%M")}
