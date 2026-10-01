"""
Validação automatizada dos avisos obrigatórios da Portaria SPA/MF nº 136/2025
("18+" e menção à portaria) em vídeos/imagens de posts de influenciadores.

Lê um manifesto de posts já baixados (pasta local por post, com os vídeos/imagens
daquele post dentro) e classifica cada post em:
  - Conforme: todos os elementos obrigatórios (18+, portaria, #publi, e o item
    condicional por data — "jogue com responsabilidade" antes de 17/07/2026 ou
    a frase do Ministério da Fazenda a partir dessa data) encontrados no texto.
  - Não Conforme: falta algum elemento obrigatório em algum arquivo do post
    (motivo específico dizendo qual elemento falta) — sem meio-termo.
  - Requer Verificação: pasta vazia/sem arquivo de mídia, arquivo com indício
    real de recompressão técnica, ou fragmento ambíguo do aviso que o OCR não
    consegue confirmar nem descartar com segurança (problema de dado, não de
    mérito regulatório).

Não escreve na planilha original — gera um relatório à parte para revisão humana.
"""

import json
import os
import re
import subprocess
import sys

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))

# ------------------------------------------------------------------
# Onde está o Tesseract
# ------------------------------------------------------------------
# DEIXOU DE SER CAMINHO FIXO EM 30/08/2026. Antes apontava direto para uma
# pasta dentro de c:\Users\auditor, que não existe em outra máquina nem
# em Linux. Era um dos bloqueios para subir no servidor.
#
# A ordem é: variável de ambiente, depois os lugares onde ele costuma ser
# instalado no Windows, depois o PATH. O ffmpeg logo abaixo já fazia assim.
def _achar_tesseract():
    indicado = os.environ.get("TESSERACT_CMD")
    if indicado:
        # Indicado à mão vale mesmo se não existir: melhor falhar dizendo que o
        # caminho apontado não está lá do que procurar outro pelas costas.
        return indicado
    candidatos = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Programs", "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""),
                     "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""),
                     "Tesseract-OCR", "tesseract.exe"),
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    # Última opção: deixa o sistema resolver pelo PATH. É o caso normal em
    # Linux, onde o pacote instala em lugar já conhecido.
    return "tesseract"


PYTESSERACT_CMD = _achar_tesseract()
pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_CMD


def idioma_portugues_instalado():
    """Se o Tesseract tem o português. O programa pede "por+eng" e o Tesseract
    NÃO reclama quando o idioma falta: cai para o inglês em silêncio.

    Medido em 30/08/2026: só com inglês, duas das três frases obrigatórias do
    Ministério da Fazenda nunca eram encontradas em texto pequeno, e peça que
    tem o aviso seria classificada como se não tivesse. Por isso vale conferir
    e não supor."""
    try:
        return "por" in {str(i).strip() for i in pytesseract.get_languages()}
    except Exception:
        return None  # não deu para saber, que é diferente de não ter

# Dois motores de OCR, em cascata por VELOCIDADE, não por qualidade sozinha:
# Tesseract primeiro (rápido, ~1s por chamada, resolve a maioria) e EasyOCR
# (rede neural) só como reforço nos casos em que o Tesseract não achou nada —
# testamos EasyOCR em tudo e cada chamada dele numa imagem real (não sintética)
# levou de 2 a 190s dependendo do tamanho, o que tornava o pipeline inteiro
# 10x+ mais lento. Como fallback só nos casos difíceis, mantém a velocidade
# média e ainda pega os casos que o Tesseract sozinho perdia (ex: linha 95).
_easyocr_reader = None


def get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(["pt", "en"], gpu=False)
    return _easyocr_reader

FFMPEG_CMD = None
for candidate_root in [os.environ.get("LOCALAPPDATA", "")]:
    pkg_dir = os.path.join(candidate_root, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(pkg_dir):
        for name in os.listdir(pkg_dir):
            if name.startswith("Gyan.FFmpeg"):
                for root, _, files in os.walk(os.path.join(pkg_dir, name)):
                    if "ffmpeg.exe" in files:
                        FFMPEG_CMD = os.path.join(root, "ffmpeg.exe")
if FFMPEG_CMD is None:
    FFMPEG_CMD = "ffmpeg"

FFPROBE_CMD = FFMPEG_CMD.replace("ffmpeg.exe", "ffprobe.exe") if FFMPEG_CMD != "ffmpeg" else "ffprobe"

WHISPER_MODEL_SIZE = "small"
_whisper_model = None

REGEX_18 = re.compile(
    # "1\s?8" (não só "18") pra tolerar o espaço que aparece entre o "1" e o "8"
    # em alguns banners reais (achado de auditoria: @lannaleticiaa, "1 8+ JOGUE
    # COM RESPONSABILIDADE" — o "18+" tem um espaço no meio, seja por kerning
    # do banner ou ruído do OCR em fonte pequena, e SEM essa tolerância o
    # regex original não casava mesmo com o aviso presente e visível).
    # Espaco opcional nas frases, pelo motivo registrado em
    # REGEX_MINISTERIO_FAZENDA: um dos motores de OCR entrega tudo colado.
    r"(1\s?8\s*\+|\+\s*1\s?8|maior(es)?\s*de\s*idade|proibid[oa]\s*para\s*menor|"
    r"menor(es)?\s*de\s*idade\s*(n[aã]o|proibid))",
    re.IGNORECASE,
)
REGEX_PORTARIA = re.compile(
    r"(portaria|SPA\s*/\s*MF|136\s*/\s*2025)",
    re.IGNORECASE,
)
# O NÚMERO DA PORTARIA É INFORMAÇÃO EXTRA, E NÃO EXIGÊNCIA (02/09/2026).
#
# Decisão do auditor, com as palavras dele: "vamos deixar como está, sem exigir o
# número, o número vai entrar como um PLUS, pq o obrigatório mesmo é o AUTORIZADO
# PELA PORTARIA, e a frase do ministério com o aviso de APOSTA NÃO É
# INVESTIMENTO".
#
# Ele confirmou que "AUTORIZADO PELA PORTARIA SPA/MF Nº 136/25" é o que a peça
# deve conter, e que 136/25 é a versão atual. Mesmo assim o número NÃO entra em
# REGEX_PORTARIA, e o motivo é o de sempre neste programa: o número é a linha
# mais fina do banner e falha no OCR com frequência. Exigi-lo criaria Não
# Conforme em peça que traz o aviso completo com o número ilegível, que é o erro
# mais caro que esta ferramenta pode cometer.
#
# O QUE ESTE PADRÃO FAZ: captura o número quando ele é legível, para aparecer na
# evidência. Não decide nada. Serve para alguém olhar a coluna e perceber, por
# exemplo, uma peça citando número antigo, sem que o programa acuse a partir de
# leitura de texto miúdo.
#
# Tolera o ruído do OCR no "Nº". As formas abaixo são as que apareceram DE
# VERDADE no levantamento de 02/09/2026, sobre as peças já analisadas:
#
#     17x  PORTARIA SPA/MF Nº 136/25
#     11x  PORTARIA SPA/MF NO 136/25
#      1x  PORTARIA SPA/MF N 136/25
#      1x  PORTARIA SPA/MF N° 136/25
#      1x  PORTARIA SPAIMF N2 136/25      "/" lido como "I"
#      1x  PORTARIA SPAMF N2 136/25       "/" perdido
#
# O "2" ENTRA NA LISTA DE RUÍDO do "º", e isso corrigiu um erro da primeira
# versão deste padrão: com "N2136/25" ela absorvia o 2 e devolvia "2136/25",
# um número que não existe. Só vale depois de um "n", então "PORTARIA 2136/25"
# sem o "Nº" continuaria sendo lido como 2136/25, que é o correto nesse caso.
REGEX_NUMERO_PORTARIA = re.compile(
    r"portaria[\s:]*(?:spa\s*[/i]?\s*mf)?[\s]*(?:n[ºo°\.2\s]*)?(\d{1,4}\s*/\s*\d{2,4})",
    re.IGNORECASE,
)


def numero_da_portaria(texto):
    """Número da portaria citada na peça, como o OCR leu, ou None.

    Informação extra: nunca entra em nenhuma decisão de conformidade. Ver o
    comentário de REGEX_NUMERO_PORTARIA."""
    achado = REGEX_NUMERO_PORTARIA.search(str(texto or ""))
    if not achado:
        return None
    # "136 / 25" e "136/25" são a mesma coisa lida com ruído diferente.
    return re.sub(r"\s+", "", achado.group(1))
# Aviso de "jogo responsável" exigido nos posts ANTERIORES a 17/07/2026 (ver
# precisa_jogue_responsabilidade) — duas variantes de banner observadas no
# material real, qualquer uma das duas satisfaz a exigência.
REGEX_EXTRA = re.compile(
    r"jogue\s*com\s*responsabilidade|"
    r"se\s*deixar\s*de\s*ser\s*divers[aã]o[,]?\s*pare",
    re.IGNORECASE,
)
# "Aposta é assunto para adultos" — facultativa/boa prática, NUNCA obrigatória
# (só valia como alternativa opcional no período pré-17/07/2026). Não entra em
# nenhuma exigência de conformidade, é só sinal informativo extra na evidência.
REGEX_ASSUNTO_ADULTOS = re.compile(
    r"aposta\s*[ée]\s*assunto\s*para\s*adultos",
    re.IGNORECASE,
)

# Portaria SPA/MF nº 1.964/2026, art. 13, II — em vigor a partir de 17/07/2026:
# pelo menos UMA dessas três frases (o prefixo "Ministério da Fazenda adverte:"
# às vezes fica cortado no banner, então casamos pela frase distintiva final).
DATA_VIGENCIA_MINISTERIO_FAZENDA = "2026-07-17"
REGEX_MINISTERIO_FAZENDA = re.compile(
    r"(apostar\s*pode\s*causar\s*depend[êe]ncia|"
    r"apostar\s*faz\s*voc[êe]\s*perder\s*dinheiro|"
    r"aposta\s*n[aã]o\s*[ée]\s*investimento)",
    re.IGNORECASE,
)

# O ESPAÇO ENTRE AS PALAVRAS É OPCIONAL, E ISSO É CORREÇÃO DE DEFEITO
# (03/09/2026). Vale para esta regra, para a REGEX_EXTRA e para as frases de
# REGEX_CONTEUDO_APOSTA.
#
# COMO APARECEU. O auditor mostrou uma peça da @perlladecassia com o rodapé
# perfeitamente legível e perguntou por que o programa não pegou. Medido nos três
# motores, no mesmo arquivo:
#
#   Tesseract  APOS IMVESTIMENTO                 (leitura ruim de verdade)
#   RapidOCR   APOSTANAO EINVESTIMENTO           frase INTEIRA, sem espaços
#   RapidOCR   APOSTANAOEINVESTIMENTO            idem, no quadro seguinte
#   EasyOCR    APOSTA NÃO É INVESThento          leitura ruim de verdade
#
# Ou seja: um dos três motores leu a frase CORRETA e o programa a rejeitou,
# porque a regra exigia \s+ entre as palavras e aquele motor entrega tudo
# colado. O mesmo acontecia com "JOGUECOMRESPONSABILIDADE". A peça estava
# conforme e o veredito saía REQUER ANÁLISE.
#
# POR QUE \s* NÃO AFROUXA A EXIGÊNCIA: ele tolera a AUSÊNCIA de espaço, e nada
# mais. As palavras continuam todas obrigatórias, na mesma ordem, e \s* não casa
# caractere qualquer no meio. Conferido contra frases que NÃO devem passar, e
# nenhuma passa:
#
#   "aposta e investimento"                  não casa
#   "aposta nao investimento"                não casa
#   "investimento nao e aposta"              não casa
#   "aposta, nao. e! investimento"           não casa
#   "apostas nao sao investimentos"          não casa
#   "a aposta que nao parece investimento"   não casa
#
# Está em testes\teste_espaco_do_ocr.py, com os trechos reais lidos naquele dia.
#
# O QUE FOI DESCARTADO NO CAMINHO: recortar a faixa do rodapé e ampliar antes de
# ler. Medido no mesmo arquivo, melhorou a leitura do Tesseract
# ("APOSTÁTIM > VESTIMENTO" no lugar de "APOS IMVESTIMENTO") mas não fez nenhuma
# peça passar, e custava uma passada de OCR a mais por quadro. A correção da
# regra custa zero e resolve o caso.
# Indica que o arquivo mostra/menciona conteúdo de aposta (mesmo sem narração) —
# usado pra decidir se ESSE arquivo específico precisa ter seu próprio aviso.
# Regra: a Portaria SPA/MF 1.231/2024 exige advertência em "qualquer peça, material
# ou inserção" e proíbe dissimular publicidade como entretenimento — ou seja, o
# aviso é por peça/clipe, não por post. Um clipe sem aviso não é "coberto" pelo
# aviso de outro clipe do mesmo story, mesmo que publicados juntos.
# As 3 casas de aposta que a EGB realmente patrocina (confirmado pelo auditor):
# Esportes da Sorte (também abreviado "EDS"), Lottu, e Ona/Onabet — as demais
# palavras-chave (bet365, cassino genérico, nomes de jogo) ficam como sinal de
# apoio pra pegar conteúdo hospedado dentro dessas plataformas (ex: o jogo
# "Cheesy Road" visto rodando dentro do site da Lottu), não marcas à parte.
# O ESPAÇO É OPCIONAL NAS FRASES DE VÁRIAS PALAVRAS (03/09/2026), pelo mesmo
# motivo registrado em REGEX_MINISTERIO_FAZENDA: um dos motores de OCR entrega as
# palavras coladas, e exigir espaço fazia o programa rejeitar leitura correta.
REGEX_CONTEUDO_APOSTA = re.compile(
    r"(\.bet\.br|\bbet365\b|cassino|aposta|apostar|slot|jogo\s*de\s*azar|"
    r"giros?\s*gr[aá]tis|rodadas?\s*gr[aá]tis|jackpot|multiplicador|"
    r"cr[ée]dito\s|dep[oó]sito|lottu|esportes?\s*da\s*sorte|esportesdasorte|"
    r"\beds\b|\bona\s*bet\b|\bonabet\b|\bona\b|"
    r"gates\s*of\s*olympus|fortune\s*dragon|aviator|clica\s*pra\s*jogar|"
    r"cadastro\s*gr[aá]tis|deposite|vem\s*se\s*divertir)",
    re.IGNORECASE,
)
# Portaria SPA/MF 1.231/2024 — proíbe dissimular publicidade como conteúdo
# editorial/entretenimento; a publicação precisa evidenciar o caráter comercial
# (a própria auditoria manual também não vinha checando isso até agora).
#
# AMPLIADO EM 02/09/2026, com os termos aprovados pelo auditor, e a razão da
# ampliação é um defeito de simetria: a pergunta que o programa faz à IA DE VISÃO
# é mais ampla do que esta lista conseguia confirmar. A pergunta diz "selo ou
# marca indicando publicidade, parceria paga ou CONTEÚDO PATROCINADO", e
# "patrocinado" não estava aqui.
#
# O efeito era nos dois casos na direção acusatória: peça que declarava com
# "conteúdo patrocinado" não era confirmável por OCR, então caía em Requer
# Análise, ou em Não Conforme quando a visão também não pegava. E parte dos casos
# ambíguos que vínhamos combatendo podia ser exatamente isso, a visão vendo um
# selo que existe e o OCR sem a palavra para confirmar.
#
# "#publicidade" JÁ ERA RECONHECIDO e continua sendo pelo mesmo termo: em
# "#publicidade" existe borda de palavra entre o "#" e o "p", porque "#" não é
# caractere de palavra, então `\bpublicidade\b` casa. O auditor pediu para
# incluir, e a nota fica aqui em vez de um alternativa repetida no regex.
#
# TERMOS RECUSADOS, e a decisão é do auditor: "recebido", "oferecido por" e
# "presente de" NÃO entram, porque não são necessariamente declaração de
# publicidade paga.
#
# RISCO CONHECIDO de "patrocinado", registrado para quem for revisar: ele pode
# aparecer na tela falando de outra coisa, como "patrocinado pelo time X", e aí
# seria confirmação indevida. É risco na direção de PERDER achado, ao contrário
# do defeito que esta mudança corrige. "patrocinador" não casa, porque a
# terminação exigida é o/a/os/as.
#
# AMPLIADO EM 08/09/2026, com a lista que o auditor passou: "#publicidade,
# #publi, #anúncio, #patrocinado ou Parceria paga com [Nome da Marca]". Quatro
# dos cinco já valiam. Entraram dois, e a diferença de tratamento entre eles é
# deliberada:
#
#   publipost SOLTO, além do "#publipost" que já valia. Entra sem ressalva
#   porque não é palavra com outro sentido: só existe como marcação de
#   publicidade. Note que "\bpubli\b" NÃO pegava "publipost", por causa da
#   borda de palavra.
#
#   #anúncio SÓ COM CERQUILHA. "Anúncio" é palavra corrente do português e
#   aparece na tela falando de outra coisa ("veja o anúncio de hoje").
#   Aceitá-la solta faria peça SEM declaração passar como declarada, que é o
#   erro que PERDE achado. É o mesmo critério já aplicado ao "#ad", que também
#   não vale solto. Se o auditor quiser mais largo, é uma linha.
#
# SEM ACENTO TAMBÉM VALE, porque o OCR come acento com frequência. Mesmo motivo
# do espaço opcional nas regras de duas palavras.
REGEX_PUBLI = re.compile(
    r"#publi\b|\bpubli\b|\bpublicidade\b|"
    r"#publiposts?\b|\bpubliposts?\b|"
    r"#an[úu]ncios?\b|"
    # Espaco opcional nas de duas palavras, pelo motivo registrado em
    # REGEX_MINISTERIO_FAZENDA: um dos motores de OCR entrega tudo colado.
    r"parceria\s*paga|patrocinad[oa]s?\b|#ads?\b|pag[oa]\s*(?:por|pel[ao])\b",
    re.IGNORECASE)

# Fragmentos soltos do texto-padrão do banner ("SE DEIXAR DE SER DIVERSÃO,
# PARE. [...] AUTORIZADO PELA PORTARIA..."), sem exigir o match exato de
# REGEX_18/REGEX_PORTARIA. Serve só pra distinguir "não achei nada, não tem
# mesmo" (Não Conforme) de "achei pedaço bagunçado/obstruído do aviso, mas não
# fecha limpo" (Requer Verificação — exige análise manual) — ex: banner
# sobreposto por outro elemento da tela, ou vídeo cortado no meio da frase.
REGEX_SINAL_FRACO_AVISO = re.compile(
    r"diversão|\bpare\b|autorizad[oa]|\bspa\b|\bmf\b|responsabilidad|"
    r"\b18\b|menor(es)?\s*de|social|bolsa\s*fam[ií]lia",
    re.IGNORECASE,
)

# Achado de auditoria (amostra real de 51 áudios transcritos em 14/08/2026):
# linguagem de hype genérica ("ganhe um milhão", "de graça", "sorte", "prêmios")
# é a esmagadora maioria da fala dos influenciadores e NÃO é vedada — só entram
# aqui os 3 padrões que realmente apareceram batendo nas vedações do CONAR
# Anexo X / Portaria SPA/MF (ilusão de controle sobre o resultado, promessa de
# enriquecimento, sugestão de que o ganho é repetível só de copiar o passo a
# passo). Cada regex aqui é propositalmente estreito (poucos casos reais
# confirmados) — o objetivo NUNCA é cravar um veredito sozinho, só levantar um
# alerta pra conferência humana (ver ROTULO_ALERTA_AUDIO / classificar_post).
_PADROES_FALA_PROBLEMATICA = {
    "ilusao_controle": re.compile(
        r"(a\s+gente|eu|n[oó]s)\s+(que\s+)?(manda|mando|decide|decido|controla|controlo)\b.{0,20}\b(jogo|hora|estrat[ée]gia|resultado)|"
        r"quem\s+manda\s+(n[oa]|[ée])\s+jogo\s+[ée]\s+(a\s+gente|eu|voc[êe])|"
        r"sei\s+a\s+hora\s+certa\s+de\s+(parar|sair)",
        re.IGNORECASE,
    ),
    "promessa_enriquecimento": re.compile(
        r"(chance|certeza)\s+de\s+ficar\s+rico|ficar\s+rico\b|"
        r"vai(s)?\s+enriquecer|garantido\s+que\s+(voc[êe]|ce)\s+ganha|"
        r"certeza\s+de\s+ganhar|renda\s+garantida|investimento\s+seguro",
        re.IGNORECASE,
    ),
    "sugestao_repetibilidade": re.compile(
        r"s[oó]\s+fazer\s+igual|[ée]\s+s[oó]\s+copiar|faz(er)?\s+que\s+nem\s+eu|"
        r"quer\s+faturar,?\s+[ée]\s+s[oó]\s+fazer",
        re.IGNORECASE,
    ),
}

ROTULO_ALERTA_AUDIO = {
    "ilusao_controle": "sugere que o jogador controla o resultado de um jogo de sorte (ilusão de controle, vedada pelo CONAR Anexo X)",
    "promessa_enriquecimento": "sugere promessa de enriquecimento/ganho garantido (vedado pelo CONAR Anexo X e pela Portaria SPA/MF)",
    "sugestao_repetibilidade": "sugere que o ganho de outra pessoa é repetível só de copiar o mesmo passo a passo (indução a erro sobre chance real de ganho)",
}


def checar_fala_problematica(texto_transcrito):
    """Verifica se a transcrição do áudio contém algum dos 3 padrões de fala
    vedados pelo CONAR Anexo X / Portaria SPA/MF (ilusão de controle, promessa
    de enriquecimento, sugestão de repetibilidade do ganho). NUNCA usado pra
    cravar Não Conforme sozinho — só gera um alerta à parte pedindo conferência
    humana pontual (ver ROTULO_ALERTA_AUDIO), porque transcrição de fala tem
    risco real de erro por sotaque/ruído/corte que um regex não distingue de
    uma fala genuinamente problemática."""
    if not texto_transcrito:
        return []
    return [
        categoria for categoria, padrao in _PADROES_FALA_PROBLEMATICA.items()
        if padrao.search(texto_transcrito)
    ]


VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


# Quantos quadros olhar em cada vídeo.
#
# Três é herança, não escolha medida. Vale rever agora que eles vêm de trechos
# diferentes: a escada de OCR para assim que acha tudo o que a data exige, então
# quadro a mais só custa tempo nos vídeos em que já falta alguma coisa. Medido
# em 29/08/2026 nesta máquina: cada quadro a mais custa cerca de 13s de EasyOCR
# no pior caso, e nada no caso conforme.
QUADROS_POR_VIDEO = 3


def duracao_do_video(path):
    """Duração em segundos, ou None quando não dá para descobrir."""
    try:
        resultado = subprocess.run(
            [FFPROBE_CMD, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return float(resultado.stdout.strip())
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def extract_frames(video_path, out_dir, n_frames=QUADROS_POR_VIDEO):
    """Tira n_frames do vídeo, espalhados do começo ao fim.

    CORRIGIDO EM 29/08/2026. Um vídeo, um quadro por fatia, no meio de cada
    fatia: num vídeo de 30s com 3 quadros, sai um aos 5s, um aos 15s e um aos
    25s.

    O QUE ESTAVA ERRADO. A versão anterior pedia ao ffmpeg 3 quadros por
    segundo e ficava com os 3 primeiros, ou seja, **todos os quadros vinham do
    primeiro 0,7 segundo do vídeo**. Num vídeo de 37s, mais de 98% dele nunca
    era olhado, e os três quadros eram praticamente a mesma imagem lida três
    vezes.

    POR QUE ISSO É ACHADO DE AUDITORIA, E NÃO SÓ DESPERDÍCIO. O aviso
    obrigatório que aparece depois do primeiro segundo era simplesmente não
    encontrado, e a peça ia para NÃO CONFORME por falta de um aviso que estava
    lá. Esse é o erro mais caro que este programa pode cometer, porque acusa
    indevidamente. A correção anda na direção segura: passa a achar aviso que
    antes escapava.

    O CUSTO É O MESMO. Continuam três quadros e três leituras. O que muda é de
    onde eles vêm.

    ATENÇÃO: isto muda o resultado de análises já feitas. Peça classificada
    como não conforme por causa de aviso tardio pode virar conforme ao ser
    reprocessada."""
    os.makedirs(out_dir, exist_ok=True)
    caminhos = []

    duracao = duracao_do_video(video_path)
    if duracao and duracao > 0:
        for i in range(n_frames):
            # Meio de cada fatia, e não a borda: começo de vídeo costuma ter
            # transição e fim costuma ter corte, e quadro de transição sai
            # borrado ou preto.
            instante = duracao * (i + 0.5) / n_frames
            destino = os.path.join(out_dir, f"frame_{i + 1:02d}.jpg")
            subprocess.run(
                # -ss antes do -i faz o ffmpeg pular direto para o instante em
                # vez de decodificar o vídeo inteiro até lá.
                [FFMPEG_CMD, "-y", "-ss", f"{instante:.3f}", "-i", video_path,
                 "-frames:v", "1", "-q:v", "2", destino],
                capture_output=True, check=False,
            )
            if os.path.exists(destino):
                caminhos.append(destino)

    # Sem duração legível (arquivo estranho, corrompido, formato incomum), cai
    # no caminho antigo em vez de devolver nada: quadro do começo é melhor que
    # quadro nenhum.
    if not caminhos:
        pattern = os.path.join(out_dir, "frame_%02d.jpg")
        subprocess.run(
            [FFMPEG_CMD, "-y", "-i", video_path, "-vf", "fps=1",
             "-frames:v", str(n_frames), pattern],
            capture_output=True, check=False,
        )

    return sorted(
        os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith("frame_")
    )


def extract_audio(video_path, out_path):
    subprocess.run(
        [FFMPEG_CMD, "-y", "-i", video_path, "-ar", "16000", "-ac", "1", "-vn", out_path],
        capture_output=True, check=False,
    )
    return out_path if os.path.exists(out_path) else None


BLUR_THRESHOLD = 60.0  # variância do Laplaciano abaixo disso = imagem considerada borrada


def medir_nitidez(path):
    """Variância do Laplaciano: quanto menor, mais borrada a imagem."""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    return cv2.Laplacian(img, cv2.CV_64F).var()


LARGURA_MINIMA_ORIGINAL = 720  # abaixo disso, story/reels (normalmente 1080x1920) já veio recomprimido


def medir_qualidade_video(path):
    """Resolução e bitrate reais do arquivo (via ffprobe), pra distinguir 'o
    arquivo foi salvo/comprimido com qualidade ruim' de 'o aviso realmente não
    está lá'. Sem isso, um vídeo recomprimido pelo WhatsApp/Drive pode ser
    confundido com um post que nunca teve o aviso."""
    try:
        resultado = subprocess.run(
            [FFPROBE_CMD, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,bit_rate",
             "-of", "json", path],
            capture_output=True, text=True, check=False, timeout=30,
        )
        dados = json.loads(resultado.stdout or "{}")
        stream = (dados.get("streams") or [{}])[0]
        largura = stream.get("width")
        altura = stream.get("height")
        bit_rate = stream.get("bit_rate")
        return {
            "largura": largura,
            "altura": altura,
            "bit_rate": int(bit_rate) if bit_rate else None,
            "possivel_recompressao": bool(largura) and min(largura, altura or largura) < LARGURA_MINIMA_ORIGINAL,
        }
    except Exception:
        return {"largura": None, "altura": None, "bit_rate": None, "possivel_recompressao": False}


def _preprocessar_para_ocr(pil_img):
    """Escala de cinza + contraste + upscale — ajuda mesmo o EasyOCR em texto
    minúsculo (ex: o banner cortado de tela cheia pra um recorte pequeno)."""
    img = pil_img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    return img


def _easyocr_texto(pil_img_ou_array):
    reader = get_easyocr_reader()
    try:
        return " ".join(reader.readtext(np.array(pil_img_ou_array), detail=0))
    except Exception:
        return ""


def ocr_image_rapido(path):
    """Tesseract: imagem inteira + recortes de cima/baixo com contraste. Rápido
    (~1-2s no total) e resolve a maioria dos casos — é a passada padrão."""
    textos = []
    try:
        img = Image.open(path)
        textos.append(pytesseract.image_to_string(img, lang="por+eng"))
        textos.append(pytesseract.image_to_string(_preprocessar_para_ocr(img), lang="por+eng"))

        w, h = img.size
        faixa_inferior = img.crop((0, int(h * 0.72), w, h))
        textos.append(pytesseract.image_to_string(_preprocessar_para_ocr(faixa_inferior), lang="por+eng"))
        faixa_superior = img.crop((0, 0, w, int(h * 0.18)))
        textos.append(pytesseract.image_to_string(_preprocessar_para_ocr(faixa_superior), lang="por+eng"))
    except Exception:
        pass
    return "\n".join(textos)


def ocr_image_forte(path):
    """EasyOCR (rede neural): só chamado quando o Tesseract não achou nada
    relevante. Muito mais preciso em texto pequeno/borrado (ex: linha 95 do
    piloto), mas também muito mais lento por chamada — por isso é reforço,
    não a passada padrão."""
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        textos = [_easyocr_texto(img)]
        faixa_inferior = img.crop((0, int(h * 0.72), w, h))
        textos.append(_easyocr_texto(_preprocessar_para_ocr(faixa_inferior)))
        faixa_superior = img.crop((0, 0, w, int(h * 0.18)))
        textos.append(_easyocr_texto(_preprocessar_para_ocr(faixa_superior)))
        return "\n".join(textos)
    except Exception:
        return ""


# RapidOCR: 2º degrau da escada de OCR, inserido em 28/08/2026 entre o
# Tesseract e o EasyOCR. Medido em 40 quadros reais (24 deles dos casos
# difíceis que o código já nomeia), cada motor sozinho:
#
#   motor       s/quadro   18+  portaria  jogue c/resp  Min.Fazenda  #publi
#   Tesseract      1,49s    31       33         29            0          4
#   EasyOCR       11,29s    31       31         34            1         17
#   RapidOCR       5,92s    36       36         24            2         22
#
# Ou seja: o RapidOCR é o melhor dos três em 18+, portaria e #publi, custa
# metade do EasyOCR, e é FRACO justamente no "jogue com responsabilidade",
# que é onde o EasyOCR é o melhor. Eles erram em lugares diferentes.
#
# Por isso ele NÃO substitui o EasyOCR (essa troca foi testada e perdia 6
# detecções, 5 delas do aviso de jogo responsável em casos difíceis
# conhecidos). Ele entra ANTES: como resolve o #publi muito melhor que o
# Tesseract (22 contra 4), a escada passa a parar nele com frequência e o
# EasyOCR, que é o caro, deixa de ser chamado quase sempre. Somando os três
# a detecção melhora nos cinco elementos e não perde nenhum caso.
_rapidocr_engine = None
_rapidocr_indisponivel = False


def get_rapidocr_engine():
    """Carrega o RapidOCR uma vez só. Se o pacote não estiver instalado na
    máquina (ex: servidor novo), devolve None e a escada segue direto pro
    EasyOCR — um degrau ausente nunca pode impedir a análise de rodar."""
    global _rapidocr_engine, _rapidocr_indisponivel
    if _rapidocr_indisponivel:
        return None
    if _rapidocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapidocr_engine = RapidOCR()
        except Exception:
            _rapidocr_indisponivel = True
            return None
    return _rapidocr_engine


def _rapidocr_texto(pil_img):
    engine = get_rapidocr_engine()
    if engine is None:
        return ""
    try:
        resultado, _tempos = engine(np.array(pil_img))
    except Exception:
        return ""
    return " ".join(linha[1] for linha in (resultado or []))


def ocr_image_medio(path):
    """RapidOCR nas mesmas 3 regiões que o EasyOCR usa (imagem inteira, faixa
    de baixo, faixa de cima). Mesma estratégia de recorte de propósito: foi
    assim que ele foi medido, e sem as faixas o aviso de jogo responsável cai
    de 24 para 1 acerto em 40 quadros (é texto miúdo de rodapé)."""
    if get_rapidocr_engine() is None:
        return ""
    try:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        return "\n".join([
            _rapidocr_texto(img),
            _rapidocr_texto(_preprocessar_para_ocr(img.crop((0, int(h * 0.72), w, h)))),
            _rapidocr_texto(_preprocessar_para_ocr(img.crop((0, 0, w, int(h * 0.18))))),
        ])
    except Exception:
        return ""


def transcribe_audio(path):
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        return ""
    try:
        model = get_whisper_model()
        segments, _info = model.transcribe(path, language="pt")
        return " ".join(s.text for s in segments)
    except Exception as e:
        return f"[ERRO_TRANSCRICAO: {e}]"


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_VISION_MODEL = "minicpm-v"
OLLAMA_TIMEOUT = 120

_PERGUNTAS_VISAO = {
    # "18" usa DUAS perguntas (ver perguntar_visao_local) em vez de uma só —
    # testamos e uma pergunta única focada em "símbolo/emoji" não pegava o
    # caso de texto "18+" pequeno no rodapé (achado @lannaleticiaa), e uma
    # pergunta única focada em "texto, mesmo pequeno" não pegava o caso de
    # emoji/selo gráfico sem texto (achado @debochad_a) — nenhuma frase única
    # cobriu os dois casos reais ao mesmo tempo.
    "18_texto": (
        "Esta imagem contém, em qualquer lugar (mesmo em texto pequeno no "
        "rodapé), a indicação '18+' escrita ou uma restrição de idade mínima "
        "de 18 anos em texto? Responda apenas SIM ou NAO."
    ),
    "18_simbolo": (
        "Esta imagem contém um símbolo, selo ou emoji GRÁFICO de restrição de "
        "idade, sem ser texto comum (ex: círculo/faixa vermelha com o número "
        "18 cortado por uma linha)? Responda apenas SIM ou NAO."
    ),
    "portaria": (
        "Esta imagem contém texto mencionando uma portaria, norma ou órgão "
        "regulador (ex: 'Portaria', 'SPA/MF')? Responda apenas SIM ou NAO."
    ),
    # A PERGUNTA DO PUBLI NOMEIA O TEXTO, COMO AS OUTRAS CINCO (08/09/2026).
    #
    # A VERSÃO ANTERIOR ERA A ÚNICA CONCEITUAL DESTE DICIONÁRIO. Ela perguntava
    # "contém um selo ou marca INDICANDO PUBLICIDADE, parceria paga ou conteúdo
    # patrocinado", sem nomear texto nenhum, enquanto portaria, extra,
    # ministerio_fazenda e 18_texto todas citam a frase literal que procuram.
    #
    # O EFEITO, MEDIDO: o modelo respondia sim sempre que a faixa legal do
    # rodapé estava no recorte, porque ela é, literalmente, uma marca que indica
    # publicidade autorizada. Ele não estava errando, estava respondendo a
    # pergunta que recebeu. Um controle confirmou: perguntando na faixa do MEIO,
    # onde o publi quase nunca está e não há faixa legal, ele disse não em 20 de
    # 20. E a única peça em que disse não na faixa de baixo (@patriciaaparada)
    # foi justamente aquela em que a faixa legal caía ACIMA do recorte.
    #
    # MEDIÇÃO DA CORREÇÃO, em 27 peças com verdade conhecida (17 com publi, das
    # quais 12 confirmadas pelo próprio OCR e 5 conferidas a olho; 10 sem publi,
    # conferidas a olho):
    #
    #     pergunta   acha o publi que existe   não inventa o que não há   geral
    #     conceitual        17/17 (100%)              1/10 (10%)           67%
    #     nomeando          17/17 (100%)             10/10 (100%)         100%
    #
    # O que mudou não foi só a taxa: com a pergunta nomeando o texto, os
    # positivos passaram a ser confirmados na FAIXA DE CIMA, que é onde o publi
    # de fato está. A resposta virou locacional em vez de reflexo do rodapé.
    #
    # ALCANCE DA MEDIÇÃO, e ela não autoriza mais do que isso: 27 peças, os
    # rótulos manuais são do auditor que fez a medição e não de quem audita a
    # peça, e todas são do banner anterior a 17/07/2026. Vale repetir com peça
    # nova quando houver volume.
    #
    # NÃO ACRESCENTE a exclusão explícita do aviso legal aqui sem medir de novo:
    # ela foi escrita como terceira variante e nunca precisou ser testada,
    # porque nomear o texto já resolveu. Pergunta mais longa é mais uma chance
    # de o modelo se perder, e o próprio código já registra que empacotar mais
    # instrução numa pergunta piorou a resposta em outro caso.
    # A CERQUILHA EM '#publipost' NÃO É DETALHE (08/09/2026). A primeira versão
    # desta pergunta citava 'publipost' solto, e o teste de simetria reprovou:
    # REGEX_PUBLI reconhece '#publipost' e não a palavra sem a cerquilha. Sem o
    # ajuste, a visão poderia confirmar algo que o OCR não sabe confirmar, e
    # resposta certa da visão viraria dúvida na classificação.
    #
    # O ajuste foi feito NA PERGUNTA e não na lista do OCR de propósito: o que
    # conta como declaração de publicidade é decisão de auditoria, aprovada
    # termo por termo em 02/09/2026, e não cabe a quem mexe no código ampliar.
    # '#anúncio' ENTROU EM 08/09/2026, junto da ampliação de REGEX_PUBLI. Se a
    # forma conta como declaração, a visão precisa saber procurá-la: sem isso,
    # peça marcada só com '#anúncio' e que o OCR não lê receberia um "não" da
    # visão, e "não" afirma ausência, ou seja, acusação.
    "publi": (
        "Esta imagem contém, em qualquer lugar e mesmo em texto pequeno, "
        "alguma destas palavras ESCRITAS: '#publi', 'publi', 'publicidade', "
        "'parceria paga', '#publipost', '#anúncio', '#ads' ou 'patrocinado'? "
        "Responda apenas SIM ou NAO."
    ),
    "extra": (
        "Esta imagem contém texto do tipo 'jogue com responsabilidade' ou "
        "'se deixar de ser diversão, pare' (aviso de jogo responsável)? "
        "Responda apenas SIM ou NAO."
    ),
    "ministerio_fazenda": (
        "Esta imagem contém texto do tipo 'Ministério da Fazenda adverte', "
        "'apostar pode causar dependência', 'apostar faz você perder dinheiro' "
        "ou 'aposta não é investimento'? Responda apenas SIM ou NAO."
    ),
}


# TRÊS ESTADOS, E NÃO DOIS (08/09/2026)
#
# O QUE ESTAVA ERRADO. A leitura da resposta era
# `re.match(r"\s*sim\b", resposta)`, e erro do Ollama virava `resposta = ""`.
# Isso colapsava três situações diferentes em um `False`:
#
#     o modelo disse sim           -> True
#     o modelo disse que não viu   -> False
#     o modelo NÃO RESPONDEU       -> False    <-- o problema
#
# ERA FALHA SEGURA ATÉ 07/09/2026, E DEIXOU DE SER NO MESMO DIA. Enquanto
# visão-sim ABSOLVIA o publi, juntar "não" com "não respondeu" era conservador.
# Desde que a regra mudou, visão-NÃO produz NÃO CONFORME. Ou seja: com o Ollama
# fora do ar, toda peça cujo publi o OCR não lê sairia como NÃO CONFORME. Falha
# de infraestrutura virando acusação contra influenciador, que é o erro mais
# caro que este programa pode cometer.
#
# LIBERAL NO SIM, ESTRITO NO NÃO, e a assimetria é deliberada, porque o custo
# dos dois erros é muito diferente:
#
#   ler resposta duvidosa como SIM  -> item vira pendência, requer conferência
#   ler resposta duvidosa como NÃO  -> vira acusação
#
# Por isso o SIM aceita a resposta que COMEÇA com sim ou yes, inclusive quando
# vem seguida de explicação, e o NÃO só é aceito quando a resposta é SÓ isso.
# "No meio da imagem há um celular" começa com "no" e não pode ser lida como
# negativa.
#
# O INGLÊS CONTA. Medido em 81 respostas reais do modelo: 13 vieram em inglês
# ("NO", "NO."), e nenhuma afirmativa veio assim. Mas o modelo troca de idioma,
# e um "YES" lido como negativa seria acusação errada.
_NEGATIVAS_INTEIRAS = ("nao", "não", "no", "nope", "negativo")


def ler_resposta_da_visao(resposta):
    """O que o modelo respondeu: True (viu), False (disse que não viu) ou
    None (não respondeu, ou respondeu coisa que não dá para interpretar).

    None NÃO é o mesmo que False. Quem chama decide o que fazer com a dúvida, e
    as três funções de visão deste arquivo decidem coisas diferentes, cada uma
    documentada no próprio lugar."""
    texto = str(resposta or "").strip()
    if not texto:
        return None
    if re.match(r"(sim|yes)\b", texto, re.IGNORECASE):
        return True
    limpo = re.sub(r"[\s.,;:!?\"'()\[\]*_-]+", "", texto).lower()
    if limpo in _NEGATIVAS_INTEIRAS:
        return False
    return None


def _combinar_respostas(a, b):
    """Junta duas respostas da visão sobre o MESMO item.

    Usado quando o programa pergunta duas vezes: as duas perguntas do 18+, e as
    duas faixas do publi. Um SIM em qualquer uma confirma, porque são dois jeitos
    de achar a mesma coisa. Mas só dá para afirmar ausência quando AS DUAS
    negaram: se uma não respondeu, o que se tem é dúvida, não negativa."""
    if a is True or b is True:
        return True
    if a is None or b is None:
        return None
    return False


def visao_deixa_duvida(visao_confirmados, item, ocr_achou):
    """Se aquele item fica como dúvida por causa do que a visão disse.

    A regra, e o "não respondeu" é o motivo desta função existir:

        OCR leu                        -> não há dúvida, qualquer resposta
        visão disse que VIU            -> dúvida: ela sugere, não confirma
        visão NÃO RESPONDEU            -> dúvida: o programa não sabe
        visão NEGOU                    -> ausência, e é o ÚNICO caso em que dá
                                          para afirmar que não está na peça

    Item que não está no dicionário não foi perguntado, e não gera dúvida: marcar
    isso encheria a evidência de aviso sem uso, para item que a data da peça nem
    exige."""
    if ocr_achou:
        return False
    if item not in visao_confirmados:
        return False
    return visao_confirmados[item] is not False

# Pergunta deliberadamente restrita a "claramente uma criança" (não "um
# adolescente em dúvida") — um modelo de visão genérico não é um classificador
# de idade calibrado e erra muito na faixa 15-20 anos, que é justamente onde
# a Portaria se preocupa (menor de 18). Restringir a casos óbvios (criança
# nitidamente pré-adolescente) troca cobertura por confiabilidade: o modelo
# tem chance real de acertar "isso claramente é uma criança", mas nenhuma
# chance de acertar com confiança "isso é alguém com 17 anos". Nunca cobre o
# problema inteiro (adolescentes de 15-17 continuam fora do alcance confiável
# desta checagem) — é um alerta adicional, não um substituto da revisão humana.
_PERGUNTA_CRIANCA = (
    "Esta imagem mostra alguma pessoa que aparente ser CLARAMENTE uma criança "
    "(idade aproximada até 15 anos, sem contar adolescentes em dúvida)? "
    "Responda apenas SIM ou NAO."
)


# Liga/desliga a checagem de aparição de criança.
#
# DESLIGADA em 28/08/2026, por decisão do auditor, com base em medição: numa
# rodada completa de 3 vídeos reais ela consumiu 451,6s de 897,4s, ou seja
# 50,3% de todo o tempo de análise, e sempre 3 chamadas por vídeo (uma por
# quadro). Desligar cortou o tempo pela metade, de 299s para 149s por vídeo.
#
# O que se perde: pouco, e por dois motivos já registrados aqui. Primeiro, a
# pergunta é deliberadamente restrita a "claramente uma criança" e nunca
# alcançou a faixa de 15 a 17 anos, que é justamente a que a norma protege.
# Segundo, os 3 quadros saíam todos do primeiro 0,7 segundo do vídeo (ver
# extract_frames), então as 3 chamadas olhavam praticamente a mesma imagem e
# o resto do clipe nunca era visto.
#
# O que NÃO se perde: nada da classificação de conformidade. Este alerta
# nunca cravou nem descartou nada sozinho, era só um pedido de conferência
# humana à parte.
#
# Atenção: publicidade de aposta dirigida a menor é vedação normativa, não
# boa prática. Desligar a checagem NÃO significa que o risco deixou de
# existir, significa que ele passou a depender inteiramente da conferência
# humana e do critério do influenciador. Por isso a coluna de alerta passa a
# dizer "não verificado" em vez de ficar em branco (ver
# formatar_alerta_crianca): planilha em branco seria lida como "conferido e
# sem criança", o que não é verdade. Voltar a ligar é trocar False por True.
CHECAR_CRIANCA_VISUAL = False


def checar_crianca_visual(frame_path):
    """Pergunta ao modelo de visão local se o frame mostra claramente uma
    criança. NUNCA usado pra cravar violação sozinho — só gera um alerta à
    parte pedindo conferência humana obrigatória (mesmo padrão de
    checar_fala_problematica), porque é um sinal de altíssima gravidade e o
    modelo pode alucinar. Falha segura no sentido inverso das outras funções
    de visão desta cascata: aqui um FALSO NEGATIVO (deixar passar uma criança
    de verdade) é o erro mais caro que existe neste programa — mas mesmo
    assim erro/timeout devolve False (não inventa um alerta sem resposta
    válida do modelo), consistente com o resto do código; se o Ollama estiver
    fora do ar, toda a camada de visão já está degradada, não só esta checagem."""
    try:
        resposta = _perguntar_ollama(frame_path, _PERGUNTA_CRIANCA)
    except Exception:
        return False
    # A POLÍTICA DAQUI CONTINUA A MESMA, e é diferente da de
    # perguntar_visao_local de propósito: dúvida devolve False, para não
    # inventar um alerta de altíssima gravidade sem resposta válida do modelo.
    # O que mudou em 08/09/2026 é só quem interpreta o texto, agora
    # ler_resposta_da_visao, que também reconhece resposta em inglês.
    return ler_resposta_da_visao(resposta) is True


# Largura máxima da imagem enviada ao modelo de visão. Ele reduz a imagem por
# dentro de qualquer jeito, então mandar o quadro em tamanho cheio era pagar
# pra transferir e processar pixels que ele descartava. Medido em 27/08/2026,
# com 3 perguntas em 3 quadros de vídeos diferentes: 258s em tamanho cheio
# contra 45s reduzido, 5,8x mais rápido, com as 9 respostas IDÊNTICAS.
#
# Não confundir com reduzir imagem pro OCR, que aí SIM piora: o OCR precisa
# dos pixels do texto pequeno. Isso vale só pro modelo de visão.
LARGURA_MAX_VISAO = 768


def _imagem_para_visao(image_path, work_dir=None):
    """Devolve o caminho de uma cópia reduzida da imagem, ou a original se ela
    já for pequena. Reduzir antes de enviar é o que deixa a etapa de visão
    quase 6x mais rápida sem mudar nenhuma resposta."""
    try:
        img = Image.open(image_path)
        if img.width <= LARGURA_MAX_VISAO:
            return image_path
        proporcao = LARGURA_MAX_VISAO / img.width
        menor = img.resize((LARGURA_MAX_VISAO, int(img.height * proporcao)), Image.LANCZOS)
        destino = os.path.join(work_dir or os.path.dirname(image_path),
                               "visao_" + os.path.basename(image_path))
        menor.convert("RGB").save(destino, quality=90)
        return destino
    except Exception:
        return image_path  # se algo der errado, manda a original: correção nunca pode impedir a análise


def _perguntar_ollama(image_path, pergunta):
    import base64
    import urllib.request

    with open(_imagem_para_visao(image_path), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    payload = json.dumps({
        "model": OLLAMA_VISION_MODEL,
        "prompt": pergunta,
        "images": [b64],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "")


# ---------------------------------------------------------------------------
# A VISÃO RECEBE A FAIXA DO RODAPÉ, NÃO O QUADRO INTEIRO
# ---------------------------------------------------------------------------
# POR QUE ISTO EXISTE (06/09/2026)
#
# O auditor: "a visão local precisa trabalhar mais". Investigado, e o problema
# não era esforço, era o que ela recebia. MEDIDO na tela 3 da @jojotodynho, a
# peça em que a portaria está na tela e o programa pedia conferência dela:
#
#   pergunta        quadro inteiro          faixa recortada e ampliada 4x
#   generica        SIM                     SIM
#   especifica      NÃO                     SIM
#   transcricao     "PAGA PELA PORTE SUA    "JOGUE COM RESPONSABILIDADE.
#   aberta          NÃO 18" (ilegivel)      CONSULTE T&CS. A CONCURSO DA
#                                           PORTEIRA EM 36/2" (quase exata)
#
# No quadro inteiro ela chuta; na faixa ela LÊ. A linha da portaria é o texto
# mais fino da tela, e num quadro de 720x1280 ela ocupa poucos pixels de altura.
#
# E ISSO É O CONTRÁRIO DO QUE ACONTECEU COM O OCR no mesmo dia: recortar e
# ampliar PIOROU a leitura por OCR, e a hipótese foi descartada. Não é
# contradição: o OCR precisa de caractere nítido, e ampliar borra; a visão
# precisa de resolução relativa e contexto, e ampliar entrega os dois.
#
# CUSTO ZERO EM CHAMADAS: é o mesmo número de perguntas ao modelo, só com uma
# imagem melhor. O recorte é um ffmpeg de milissegundos.
FAIXA_DO_RODAPE = 0.14   # os últimos 14% da altura, onde o aviso obrigatório fica
AMPLIACAO_DA_FAIXA = 4   # medido: 4x foi onde a visão passou a transcrever


def recortar_faixa_do_rodape(image_path):
    """Devolve o caminho de um recorte ampliado da faixa de baixo.

    Falha segura: qualquer problema devolve a imagem original, para a visão
    receber ALGO em vez de nada."""
    try:
        destino = os.path.join(
            os.path.dirname(image_path),
            "rodape_" + os.path.basename(os.path.splitext(image_path)[0]) + ".png")
        if os.path.exists(destino):
            return destino
        filtro = (f"crop=iw:ih*{FAIXA_DO_RODAPE}:0:ih*{1 - FAIXA_DO_RODAPE},"
                  f"scale=iw*{AMPLIACAO_DA_FAIXA}:ih*{AMPLIACAO_DA_FAIXA}:flags=lanczos")
        subprocess.run([FFMPEG_CMD, "-y", "-i", image_path, "-vf", filtro, destino],
                       capture_output=True, timeout=60, check=False)
        return destino if os.path.exists(destino) else image_path
    except Exception:
        return image_path


# Quais itens ficam NA FAIXA do rodapé. O #publi não está aqui: ele fica num
# canto do topo, e recortar o rodapé o cortaria fora da imagem.
ITENS_DO_RODAPE_PARA_VISAO = ("18", "portaria", "extra", "ministerio_fazenda")


# O #PUBLI TEM A FAIXA DELE, E ELA FOI MEDIDA (07/09/2026)
#
# O auditor: "o publi geralmente fica em outro canto da página, longe do +18 e
# do aviso da portaria, e ontem faltou pegar isso, e estava visível".
#
# Até aqui o #publi era o único item que recebia o QUADRO INTEIRO na pergunta à
# visão, porque recortar o rodapé o cortaria fora. Só que quadro inteiro é
# exatamente a condição em que a visão chuta: foi o que se mediu no rodapé, e a
# linha do #publi é ainda mais fina que a da portaria.
#
# MEDIÇÃO, 450 quadros do cache, 55 ocorrências lidas pelo Tesseract com as
# coordenadas (0 = topo, 1 = base):
#
#     onde                        quantas      posição
#     topo, até 25% da altura     38 (69%)     mediana 0,091
#     base, acima de 80%          ~14 (25%)    p75 0,873   p90 0,935
#     meio                        ~3 (6%)      quase nada
#
# ELE É BIMODAL, e é isso que o desenho tem de refletir: ou está no topo, junto
# do nome do perfil, ou está no rodapé junto do resto. Entre 0,25 e 0,80 não há
# praticamente nada, então perguntar sobre o meio da tela é gastar resolução com
# a parte da imagem onde ele não aparece.
#
# A FAIXA DE BAIXO JÁ EXISTE, é a do rodapé. O que faltava era a de cima. Com as
# duas, a pergunta cobre cerca de 95% das ocorrências medidas, com a mesma
# quantidade de chamadas ao modelo: são duas imagens pequenas em vez de uma
# grande.
FAIXA_DO_PUBLI_TOPO = 0.25   # os primeiros 25% da altura, onde ele fica em 69%


def recortar_faixa_do_topo(image_path, ampliar=True):
    """Devolve o caminho de um recorte da faixa de cima.

    `ampliar` decide para QUEM é o recorte, e os dois valores foram medidos:

        consumidor   ampliar   publi lido em 160 quadros
        OCR          não       8    (contra 14 no quadro inteiro)
        OCR          4x        5    (ampliar borra o caractere)
        visão        4x        é o que a fez LER em vez de chutar

    O OCR fica com o recorte CRU e usado em UNIÃO com o quadro inteiro: sozinho
    ele lê menos (8 contra 14), mas acha 5 quadros que o quadro inteiro perde, e
    a união sobe para 19. A visão fica com o ampliado, pelo mesmo motivo do
    rodapé.

    Falha segura: qualquer problema devolve a imagem original, para quem chamou
    receber ALGO em vez de nada."""
    try:
        prefixo = "topo_" if ampliar else "topocru_"
        destino = os.path.join(
            os.path.dirname(image_path),
            prefixo + os.path.basename(os.path.splitext(image_path)[0]) + ".png")
        if os.path.exists(destino):
            return destino
        filtro = f"crop=iw:ih*{FAIXA_DO_PUBLI_TOPO}:0:0"
        if ampliar:
            filtro += (f",scale=iw*{AMPLIACAO_DA_FAIXA}:"
                       f"ih*{AMPLIACAO_DA_FAIXA}:flags=lanczos")
        subprocess.run([FFMPEG_CMD, "-y", "-i", image_path, "-vf", filtro, destino],
                       capture_output=True, timeout=60, check=False)
        return destino if os.path.exists(destino) else image_path
    except Exception:
        return image_path


def perguntar_visao_local(image_path, itens):
    """3º nível da cascata de detecção (depois de Tesseract e EasyOCR): pergunta
    a um modelo de visão local via Ollama (roda 100% na máquina, nenhum dado
    sai dela) se a imagem contém, visualmente, algum dos `itens` pedidos —
    mesmo que não seja texto legível por OCR. Achado real de auditoria: o
    "18+" pode estar representado como emoji/selo gráfico em vez de texto
    digitado, e nenhum OCR de caracteres reconhece isso.

    Uma pergunta simples e direta POR item, uma chamada por item — testamos
    empacotar todos os itens numa única pergunta estruturada ("responda
    EXATAMENTE no formato...") e o modelo se confundia com o formato mesmo
    reconhecendo a imagem corretamente (confirmado comparando com uma
    pergunta aberta, que descrevia o símbolo com precisão). Pergunta direta e
    isolada por item é mais lenta (mais chamadas) mas muito mais confiável.

    `itens`: subconjunto de {"18", "portaria", "publi"} — só os que ainda não
    foram confirmados pelo OCR, pra manter o custo baixo. "18" dispara DUAS
    perguntas (texto pequeno + símbolo gráfico) e aceita SIM em qualquer
    uma das duas, já que nenhuma pergunta única cobriu os dois casos reais.

    Devolve dict {item: bool}. Falha segura: qualquer erro (Ollama fora do
    ar, timeout) ou resposta que não comece claramente com "sim" devolve
    False — nunca confirma um item sem uma resposta afirmativa clara."""
    def _perguntar(pergunta):
        """Devolve True, False ou None. None é "não sei", e sobe até a
        classificação como dúvida, nunca como negativa. Ver
        ler_resposta_da_visao."""
        try:
            resposta = _perguntar_ollama(image_path, pergunta)
        except Exception:
            return None
        return ler_resposta_da_visao(resposta)

    resultado = {}
    for item in itens:
        if item == "18":
            # As duas perguntas do 18+, combinadas com a mesma regra das duas
            # faixas: sim em qualquer uma confirma, e só as DUAS negando afirma
            # ausência.
            resultado["18"] = _combinar_respostas(
                _perguntar(_PERGUNTAS_VISAO["18_texto"]),
                _perguntar(_PERGUNTAS_VISAO["18_simbolo"]))
        elif item in _PERGUNTAS_VISAO:
            resultado[item] = _perguntar(_PERGUNTAS_VISAO[item])
    return resultado


def mostra_conteudo_aposta_visual(frame_path):
    """Confere se um frame REALMENTE não mostra nada visual de aposta antes de
    isentar um clipe 'só menção de áudio' do aviso próprio (ver classificar_post)
    — evita isentar um clipe que na verdade mostra jogo/app de aposta mas sem
    texto legível pro OCR confirmar (ex: giros de slot, interface do jogo, sem
    nenhum texto/logo escrito). Falha segura: erro/timeout devolve True (assume
    que PODE ter conteúdo visual) — nunca concede a isenção por incerteza."""
    if not frame_path:
        return True
    pergunta = (
        "Esta imagem mostra alguma tela de jogo, cassino, aposta esportiva, "
        "interface de aplicativo de apostas, ou qualquer elemento visual "
        "relacionado a apostas (símbolos de slot, cartas, giros, roleta, "
        "placar de aposta)? Responda apenas SIM ou NAO."
    )
    try:
        resposta = _perguntar_ollama(frame_path, pergunta)
    except Exception:
        return True
    # A POLÍTICA DAQUI TAMBÉM CONTINUA A MESMA, e é o inverso da anterior:
    # dúvida devolve True, para nunca conceder a isenção por incerteza. Só uma
    # negativa CLARA isenta o clipe.
    return ler_resposta_da_visao(resposta) is not False


def _aviso_pleno_resolvido(texto, exige_mf=False, exige_responsabilidade=False):
    """Decide se a escada de OCR já pode parar: só para quando TODOS os
    elementos exigidos para aquele post já foram encontrados no texto.

    Checa 18+, portaria e #publi sempre. Achado real de auditoria (caso
    @cassinha.161): o #publi pode estar genuinamente presente em baixo
    contraste/canto da tela e só um motor reforçado resolver — por isso #publi
    ENTRA nessa decisão (versão anterior excluía #publi de propósito,
    assumindo que sua ausência era quase sempre real; essa suposição se
    mostrou errada).

    Corrigido em 28/08/2026: agora também checa o "jogue com responsabilidade"
    e a frase do Ministério da Fazenda, quando a data do post os exige. A
    versão anterior parava sem procurar por eles, o que abria a porta pra
    deixar de achar um aviso obrigatório e classificar como Não Conforme um
    post que estava certo. Isso ficava escondido porque o EasyOCR acabava
    rodando quase sempre por outro motivo (o Tesseract quase nunca acha
    #publi) e encontrava o aviso de qualquer jeito. Ao inserir o RapidOCR na
    escada, a parada passaria a acontecer bem mais cedo e o defeito
    apareceria: medimos 6 detecções perdidas, 5 delas desse aviso, em casos
    difíceis conhecidos.

    Os dois parâmetros vêm da data do post (ver precisa_ministerio_fazenda e
    precisa_jogue_responsabilidade). Sem eles, o padrão é não exigir, que é o
    comportamento antigo."""
    m18, mport, mextra, mmf, _maposta, mpubli, _massunto = _buscar_matches(texto)
    if not (m18 and mport and mpubli):
        return False
    if exige_responsabilidade and not mextra:
        return False
    if exige_mf and not mmf:
        return False
    return True


def analisar_visual(path, work_dir, exige_mf=False, exige_responsabilidade=False):
    """OCR (frames de vídeo ou imagem) + nitidez + qualidade técnica do arquivo
    — nunca toca em áudio. É a parte rápida; roda pra todo arquivo antes de
    decidir se vale a pena transcrever (o Whisper é a etapa mais lenta do
    pipeline, de longe).

    Dentro do próprio OCR tem uma escada de TRÊS degraus, do mais rápido pro
    mais demorado, subindo só enquanto faltar algum elemento exigido para a
    data daquele post (ver _aviso_pleno_resolvido):

      1. Tesseract (1,5s por quadro) — resolve a maioria dos banners nítidos.
      2. RapidOCR (5,9s) — muito melhor em 18+, portaria e principalmente
         #publi, que o Tesseract quase nunca acha (22 contra 4 em 40 quadros).
      3. EasyOCR (11,3s) — o mais demorado, mantido porque é o único bom no
         "jogue com responsabilidade" em texto miúdo de rodapé.

    Usar o EasyOCR sempre deixava o pipeline 10x+ mais lento; com o RapidOCR
    no meio, a escada costuma parar antes de chegar nele. Se mesmo assim
    faltar algo, escala pro 4º nível — um modelo de visão local (Ollama) que
    reconhece o elemento mesmo como símbolo/emoji gráfico, não só texto
    digitado (achado real: o "18+" pode estar representado como selo/emoji,
    que nenhum OCR de caracteres lê). Devolve também se houve escalada além do
    Tesseract, pra poder avisar na evidência quando nem os motores reforçados
    confirmarem tudo, e o que a visão local confirmou (se foi chamada)."""
    ext = os.path.splitext(path)[1].lower()
    ocr_texto = ""
    nitidez_minima = None
    qualidade = {"possivel_recompressao": False}
    escalou_ocr = False
    frame_para_visao = None
    todos_os_frames = []

    def resolvido(texto):
        return _aviso_pleno_resolvido(texto, exige_mf, exige_responsabilidade)

    if ext in IMAGE_EXTS:
        ocr_texto = ocr_image_rapido(path)
        if not resolvido(ocr_texto):
            escalou_ocr = True
            ocr_texto += "\n" + ocr_image_medio(path)
        if not resolvido(ocr_texto):
            ocr_texto += "\n" + ocr_image_forte(path)
        nitidez_minima = medir_nitidez(path)
        frame_para_visao = path
        todos_os_frames = [path]
    elif ext in VIDEO_EXTS:
        frames_dir = os.path.join(work_dir, "frames_" + os.path.splitext(os.path.basename(path))[0])
        frames = extract_frames(path, frames_dir)

        # Sai assim que o aviso completo for confirmado — se o frame 1 já tem
        # tudo, nem olha o frame 2/3. É o que mais economiza tempo na prática,
        # já que o banner costuma aparecer do início ao fim do clipe. Cada
        # degrau da escada percorre os quadros do mesmo jeito.
        def passar_motor(motor, texto_ate_agora):
            partes = []
            for f in frames:
                partes.append(motor(f))
                if resolvido(texto_ate_agora + "\n" + "\n".join(partes)):
                    break
            return "\n".join(partes)

        ocr_texto = passar_motor(ocr_image_rapido, "")

        if not resolvido(ocr_texto):
            escalou_ocr = True
            ocr_texto += "\n" + passar_motor(ocr_image_medio, ocr_texto)

        if not resolvido(ocr_texto):
            ocr_texto += "\n" + passar_motor(ocr_image_forte, ocr_texto)

        # UM QUARTO DEGRAU, SÓ PARA O #PUBLI, E SÓ QUANDO ELE NÃO FOI LIDO
        # (07/09/2026).
        #
        # O auditor: "o publi geralmente fica em outro canto da página, longe do
        # +18 e do aviso da portaria, e ontem faltou pegar isso, e estava
        # visível". Medido em 450 quadros do cache: ele está no topo em 69% das
        # ocorrências, com a mediana em 9% da altura, e a linha dele é ainda
        # mais fina que a da portaria.
        #
        # MEDIÇÃO DA CORREÇÃO, em 160 quadros: o quadro inteiro lê o publi em
        # 14, o recorte cru do topo lê em 8, e a UNIÃO dos dois lê em 19. O
        # recorte sozinho é pior, e mesmo assim acha 5 quadros que o quadro
        # inteiro perde. Daí a união, e não a troca. São +36% de detecção.
        #
        # CUSTO: Tesseract, o degrau mais barato, e só nos casos em que o publi
        # não apareceu nos três degraus anteriores. Peça com publi legível não
        # paga nada por isso.
        if frames and not _buscar_matches(ocr_texto)[5]:
            for f in frames:
                recorte = recortar_faixa_do_topo(f, ampliar=False)
                if recorte == f:
                    continue
                ocr_texto += "\n" + ocr_image_rapido(recorte)
                if _buscar_matches(ocr_texto)[5]:
                    break

        if frames:
            nitidez_minima = min(medir_nitidez(f) for f in frames)
            frame_para_visao = max(frames, key=medir_nitidez)
        qualidade = medir_qualidade_video(path)
        todos_os_frames = frames

    # Pergunta pra visão sobre qualquer elemento EXIGIDO que o texto não
    # confirmou. Achados reais de auditoria: 18+, #publi e portaria já
    # apareceram, cada um deles, no mesmo banner pequeno, comprimido e de
    # baixo contraste que escapa de Tesseract e EasyOCR ao mesmo tempo. Pedido
    # explícito do auditor: qualquer frase ilegível pros motores de OCR deve
    # cair em "requer verificação", não só alguns itens, e por isso a pergunta
    # vale também pro aviso da data, não só pros 3 já observados com falha.
    visao_confirmados = {}
    m18, mport, mextra, mmf, _maposta, mpubli, _massunto = _buscar_matches(ocr_texto)

    # Só pergunta pelo que a DATA daquele post exige (corrigido em 29/08/2026).
    #
    # A portaria SUBSTITUI um aviso pelo outro em 17/07/2026, não acumula os
    # dois (ver precisa_jogue_responsabilidade e precisa_ministerio_fazenda).
    # Até aqui a lista trazia os cinco elementos sem olhar a data, então uma
    # das perguntas era SEMPRE jogada fora: em post de hoje, a do "jogue com
    # responsabilidade"; em post anterior a 17/07, a do Ministério da Fazenda.
    #
    # Não era só desperdício pequeno. Medido em 29/08/2026 nesta máquina, o
    # custo do modelo de visão é POR IMAGEM, não por pergunta: a primeira
    # pergunta sobre um quadro custa 73s, e cada pergunta seguinte sobre o
    # MESMO quadro custa 4,5s. Ou seja, num post em que o OCR leu tudo o que a
    # data exige, o aviso que ela NÃO exige era o único item faltando, e
    # sozinho disparava os 73s inteiros para produzir uma observação que a
    # classificação descarta em seguida (ver mf_ok e resp_ok em
    # analisar_por_arquivo). Post conforme passa a não chamar a visão nenhuma
    # vez.
    #
    # Sem data no post, nenhum dos dois é exigido, então nenhum dos dois é
    # perguntado. É o mesmo princípio já adotado na classificação: sem dado,
    # não se cobra o aviso, e não se cobra também não se pergunta.
    candidatos = [("18", m18), ("publi", mpubli), ("portaria", mport)]
    if exige_responsabilidade:
        candidatos.append(("extra", mextra))
    if exige_mf:
        candidatos.append(("ministerio_fazenda", mmf))
    itens_para_visao = [item for item, achou in candidatos if not achou]

    if itens_para_visao and frame_para_visao:
        # CADA ITEM RECEBE A FAIXA ONDE ELE APARECE, e nenhum recebe mais o
        # quadro inteiro (07/09/2026).
        #
        # Os itens do rodapé vão na faixa de baixo, que foi onde a visão passou
        # a LER em vez de chutar. O #publi agora vai nas DUAS faixas, porque a
        # medição mostrou que ele é bimodal: 69% no topo e 25% na base, quase
        # nada no meio. Ver FAIXA_DO_PUBLI_TOPO.
        #
        # POR QUE O QUADRO INTEIRO SAIU: era o que o #publi recebia, e é a
        # condição em que a visão chuta. O auditor pegou o efeito em uso real,
        # com o publi visível na tela e o programa dizendo que faltava.
        #
        # BASTA UMA DAS DUAS FAIXAS RESPONDER SIM. São dois lugares possíveis do
        # mesmo item, não dois requisitos: exigir as duas seria exigir o publi
        # duas vezes na mesma peça.
        do_rodape = [i for i in itens_para_visao if i in ITENS_DO_RODAPE_PARA_VISAO]
        do_topo = [i for i in itens_para_visao if i not in ITENS_DO_RODAPE_PARA_VISAO]
        visao_confirmados = {}
        if do_rodape or do_topo:
            faixa_baixo = recortar_faixa_do_rodape(frame_para_visao)
            visao_confirmados.update(
                perguntar_visao_local(faixa_baixo, do_rodape + do_topo))
        if do_topo:
            # O topo é perguntado depois e só acrescenta: item já confirmado
            # embaixo não é reperguntado, e um "não" de cima não apaga um "sim"
            # de baixo.
            falta_ainda = [i for i in do_topo
                           if visao_confirmados.get(i) is not True]
            if falta_ainda:
                do_topo_resposta = perguntar_visao_local(
                    recortar_faixa_do_topo(frame_para_visao), falta_ainda)
                # COMBINA AS DUAS FAIXAS EM VEZ DE SÓ SOBRESCREVER NO SIM
                # (08/09/2026). Antes, só um sim de cima substituía o resultado
                # de baixo. Então "negou embaixo, NÃO RESPONDEU em cima" ficava
                # como negativa, e negativa afirma ausência: o programa cravaria
                # que o item não está na peça tendo recebido resposta de uma
                # faixa só. Ver _combinar_respostas.
                for item, resposta in do_topo_resposta.items():
                    visao_confirmados[item] = _combinar_respostas(
                        visao_confirmados.get(item), resposta)

    return ocr_texto, nitidez_minima, qualidade, escalou_ocr, visao_confirmados, frame_para_visao, todos_os_frames


def analisar_audio(path, work_dir):
    """Extrai e transcreve o áudio — só chamar quando o OCR sozinho não já
    tiver confirmado o aviso completo (custo alto: é a etapa mais lenta)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in VIDEO_EXTS:
        return ""
    audio_path = os.path.join(work_dir, os.path.splitext(os.path.basename(path))[0] + ".wav")
    audio_path = extract_audio(path, audio_path)
    return transcribe_audio(audio_path)


def precisa_ministerio_fazenda(post_date):
    """A partir de 17/07/2026 (Portaria SPA/MF 1.964/2026), também é obrigatória
    uma das 3 frases do Ministério da Fazenda. post_date: string 'YYYY-MM-DD...'
    ou None (se não sabemos a data, não exigimos — sem dado não vira violação)."""
    if not post_date:
        return False
    return str(post_date)[:10] >= DATA_VIGENCIA_MINISTERIO_FAZENDA


def precisa_jogue_responsabilidade(post_date):
    """Antes de 17/07/2026 o aviso exigido era "jogue com responsabilidade" (ou
    "se deixar de ser diversão, pare") — a partir dessa data ele é SUBSTITUÍDO
    pela exigência da frase do Ministério da Fazenda (precisa_ministerio_fazenda),
    não exigido em cumulação com ela. post_date None: sem dado, não exigimos
    (mesmo princípio de precisa_ministerio_fazenda)."""
    if not post_date:
        return False
    return str(post_date)[:10] < DATA_VIGENCIA_MINISTERIO_FAZENDA


def _buscar_matches(texto):
    return (
        REGEX_18.search(texto),
        REGEX_PORTARIA.search(texto),
        REGEX_EXTRA.search(texto),
        REGEX_MINISTERIO_FAZENDA.search(texto),
        REGEX_CONTEUDO_APOSTA.search(texto),
        REGEX_PUBLI.search(texto),
        REGEX_ASSUNTO_ADULTOS.search(texto),
    )


def analisar_por_arquivo(arquivos, work_dir, exige_mf=False, exige_responsabilidade=False):
    """Roda OCR em cada arquivo primeiro; só transcreve o áudio (etapa lenta)
    se o OCR sozinho não já tiver confirmado o aviso completo.

    Importante: a Portaria exige que o aviso seja ESCRITO — falado não conta.
    Por isso o áudio NUNCA alimenta achou_18/achou_portaria/achou_publi/
    achou_ministerio_fazenda/achou_extra, só ocr_texto alimenta isso. O áudio
    serve só pra detectar se o clipe é sobre aposta (tem_conteudo_aposta) nos
    casos em que o OCR não achou nem o aviso nem nenhuma palavra-chave de
    aposta na tela — ex: influenciador falando sobre a bet sem nada escrito."""
    resultado_arquivos = []
    for path in arquivos:
        # Passa o que a DATA do post exige: sem isso a escada de OCR pararia
        # sem procurar o "jogue com responsabilidade" nem a frase do
        # Ministério da Fazenda (ver _aviso_pleno_resolvido).
        ocr_texto, nitidez, qualidade, escalou_ocr, visao_confirmados, frame_para_visao, todos_os_frames = analisar_visual(
            path, work_dir, exige_mf=exige_mf, exige_responsabilidade=exige_responsabilidade)

        # Roda em TODOS os frames extraídos, não só o mais nítido — achado real
        # que motivou esta checagem (@djmaryduarte) descreve a criança aparecendo
        # só no INÍCIO do clipe, então o frame mais nítido (que pode ser de outro
        # trecho) sozinho não seria suficiente. Roda sempre, independente de o
        # aviso já estar confirmado ou de o arquivo parecer sobre aposta ou não —
        # esse risco não depende de nenhuma outra condição do post.
        # Desligada em 28/08/2026 por custo (metade do tempo total de análise).
        # Ver o comentário completo em CHECAR_CRIANCA_VISUAL.
        alerta_crianca = (
            CHECAR_CRIANCA_VISUAL
            and any(checar_crianca_visual(f) for f in todos_os_frames)
        )

        m18, mport, mextra, mmf, maposta_visual, mpubli, massunto = _buscar_matches(ocr_texto)
        # OCR é a fonte primária e a ÚNICA que conta como "achado" confiável —
        # achado real de auditoria: a IA de visão local pode alucinar (viu "18+"
        # numa imagem que só tinha print de conversa, sem nada relacionado).
        # Uma confirmação SÓ por visão (sem texto de OCR por trás) não vira
        # achou_18=True — vira um sinal "ambíguo" à parte, que classificar_post
        # trata como REQUER VERIFICAÇÃO (precisa de olho humano), nunca como
        # confirmação automática de conformidade.
        achou_18 = bool(m18)
        achou_portaria = bool(mport)
        achou_publi = bool(mpubli)
        achou_extra = bool(mextra)
        achou_mf = bool(mmf)
        # DÚVIDA INCLUI "A VISÃO NÃO RESPONDEU" (08/09/2026). Estas cinco linhas
        # eram `visao_confirmados.get(item, False) and not achou_item`, que trata
        # não ter respondido igual a ter negado. Ver visao_deixa_duvida.
        achou_18_ambiguo_visao = visao_deixa_duvida(visao_confirmados, "18", achou_18)
        achou_publi_ambiguo_visao = visao_deixa_duvida(visao_confirmados, "publi", achou_publi)
        achou_portaria_ambiguo_visao = visao_deixa_duvida(visao_confirmados, "portaria", achou_portaria)
        achou_extra_ambiguo_visao = visao_deixa_duvida(visao_confirmados, "extra", achou_extra)
        achou_mf_ambiguo_visao = visao_deixa_duvida(visao_confirmados, "ministerio_fazenda", achou_mf)
        nucleo_ok = achou_18 and achou_portaria and achou_publi
        mf_ok = achou_mf or not exige_mf
        resp_ok = achou_extra or not exige_responsabilidade

        maposta_audio = None
        transcricao = ""
        # Antes só transcrevia quando o aviso não estava confirmado (checar
        # "tem_conteudo_aposta"). Agora também transcreve quando o texto já
        # confirmou conteúdo de aposta (achou_18/portaria/extra/mf), mesmo com
        # aviso completo — porque a checagem de fala problemática (ilusão de
        # controle, promessa de enriquecimento, etc.) é independente de o
        # aviso estar certo: um clipe pode ter o aviso perfeito E ainda assim
        # o influenciador falar algo vedado.
        if not (nucleo_ok and mf_ok and resp_ok) or achou_18 or achou_portaria or achou_extra or achou_mf:
            transcricao = analisar_audio(path, work_dir)
            if transcricao:
                maposta_audio = REGEX_CONTEUDO_APOSTA.search(transcricao)

        categorias_alerta_audio = checar_fala_problematica(transcricao)

        maposta = maposta_visual or maposta_audio
        msinal_fraco = REGEX_SINAL_FRACO_AVISO.search(ocr_texto)

        # Se o próprio aviso apareceu (18+, portaria, "jogue com responsabilidade" ou
        # uma das frases do Ministério da Fazenda), o arquivo obviamente é sobre
        # aposta — a lista de palavras-chave de contexto é só um sinal extra pra
        # pegar arquivos que mostram aposta SEM nenhum elemento do aviso.
        tem_conteudo_aposta = bool(maposta or achou_18 or achou_portaria or mextra or mmf)

        # Achado real de auditoria: pastas com imagem estática mostrando só a
        # LOGO da casa de aposta (sem nenhum texto), que o OCR não reconhece
        # como conteúdo de aposta — o arquivo ficava fora da checagem inteira,
        # pior que um falso negativo comum, porque nem entrava na análise.
        # Só pergunta pra visão quando o texto não achou nada (custo baixo,
        # já que a maioria dos arquivos resolve via texto).
        aposta_suspeita_visual = False
        if not tem_conteudo_aposta and frame_para_visao:
            aposta_suspeita_visual = mostra_conteudo_aposta_visual(frame_para_visao)

        evidencia_partes = [
            f"{label}: '{m.group(0)}'"
            for label, m in [("18+", m18), ("portaria", mport), ("extra", mextra),
                              ("ministério_fazenda", mmf), ("conteúdo_aposta", maposta),
                              ("publi", mpubli), ("assunto_adultos", massunto)]
            if m
        ]
        # O NÚMERO DA PORTARIA, quando legível, entra como informação extra
        # (02/09/2026, pedido do auditor: "o número vai entrar como um PLUS").
        #
        # Fica logo depois do item "portaria" de propósito, para quem lê a
        # evidência ver os dois juntos. E NÃO participa de decisão nenhuma: a
        # exigência continua sendo a menção à portaria, não o número.
        numero_portaria = numero_da_portaria(ocr_texto)
        if numero_portaria:
            evidencia_partes.append(f"portaria_número: '{numero_portaria}' (informação "
                                    f"extra, não é exigência)")
        # A RÉGUA DA LEGIBILIDADE, decidida pelo auditor em 02/09/2026, e vale
        # para TODOS os itens exigidos:
        #
        #     "se estiver na tela, ainda que pequeno, É OK; se não estiver na
        #      tela, é problema"
        #
        # O critério é PRESENÇA, não perceptibilidade. Item pequeno ou de baixo
        # contraste, mas presente, é conforme naquele item. Isso encerra a dúvida
        # que estava aberta sobre aviso ilegível poder ser considerado ostensivo:
        # não é critério.
        #
        # E NÃO MUDA NADA AQUI, de propósito. O que este trecho trata é o caso em
        # que o programa NÃO SABE se o item está na tela: nenhum OCR leu, e a IA
        # de visão sugeriu que está. "Está na tela e o OCR não leu" e "não está na
        # tela" chegam idênticos aqui. A régua diz qual pergunta responder, não
        # dá ao programa como responder, então o caso continua indo para Requer
        # Verificação, com a pergunta na forma que a régua pede.
        #
        # A FRASE COMEÇA PELO QUE NÃO FOI CONFIRMADO (02/09/2026), E ISSO VEIO DE
        # UM ERRO DE LEITURA DO PRÓPRIO AUDITOR.
        #
        # O texto antigo começava por "IA de visão local sugere presença", e o
        # auditor, lendo o resultado do @andersonneiff, concluiu "achei bem ok" e
        # depois percebeu por conta própria, olhando o vídeo, que faltava o publi.
        # Ou seja: a frase escondeu o achado de quem escreveu a ferramenta.
        #
        # A ordem das frases não é estilo. Quem lê uma linha de planilha lê o
        # começo, e o começo dizia a parte tranquilizadora. Agora começa pelo
        # fato, que é a NÃO confirmação, e a sugestão da visão vem depois, como
        # ressalva do por que não crava ausência.
        #
        # A CLASSIFICAÇÃO NÃO MUDOU, de propósito. Item que a visão sugeriu não
        # conta como ausência confirmada, e o post vai para Requer Verificação em
        # vez de Não Conforme. Isso está certo: cravar ausência que três motores
        # de OCR não conseguiram confirmar seria a ferramenta afirmando mais do
        # que sabe. O que estava errado era só o texto.
        # NÃO AFIRMAR A CAUSA, E DIZER O QUE O OCR LEU NO MESMO CLIPE
        # (02/09/2026, segunda correção do dia no mesmo trecho).
        #
        # A primeira versão desta frase, escrita hoje mesmo, dizia "(texto pequeno
        # ou baixo contraste)" como explicação de por que o item não foi lido. O
        # auditor derrubou isso com o caso concreto: no @andersonneiff o rodapé
        # estava "consideravelmente legível", e o OCR leu CINCO itens naquele
        # clipe. O publi não foi lido porque NÃO ESTAVA LÁ, e não porque era
        # pequeno.
        #
        # Ou seja: eu havia trocado uma frase que escondia o achado por outra que
        # afirmava uma causa que o programa não conhece. Mesmo defeito de fundo,
        # que é a ferramenta dizer mais do que sabe.
        #
        # O que ela diz agora é só fato: o item não foi confirmado, a visão sugere
        # presença, e ESTES outros itens foram lidos por OCR no mesmo clipe. Essa
        # última parte é o que permite a quem confere julgar sozinho: se o OCR leu
        # cinco itens ali, "não deu para ler" perde força como explicação.
        lidos_no_clipe = [label for label, m in [
            ("18+", m18), ("portaria", mport), ("jogue com responsabilidade", mextra),
            ("Ministério da Fazenda", mmf), ("conteúdo de aposta", maposta),
            ("publi", mpubli)] if m]

        # DUAS FRASES, PORQUE SÃO DUAS SITUAÇÕES (08/09/2026). A frase única
        # afirmava que "a IA de visão sugere que está presente", e desde que
        # "não respondeu" passou a gerar dúvida essa frase seria mentira nesse
        # caso. A evidência é o que a pessoa lê para decidir, então ela tem de
        # dizer qual dos dois aconteceu.
        def _frase_ambigua(rotulo, item):
            if visao_confirmados.get(item) is None:
                frase = (f"{rotulo}: NÃO CONFIRMADO por nenhum motor de OCR, e a "
                         f"IA de visão NÃO RESPONDEU (fora do ar, tempo esgotado "
                         f"ou resposta ininteligível). O programa não tem nenhuma "
                         f"informação sobre este item")
            else:
                frase = (f"{rotulo}: NÃO CONFIRMADO por nenhum motor de OCR, e a IA de "
                         f"visão sugere que está presente. A sugestão não confirma nem "
                         f"crava ausência, e o programa NÃO sabe a causa de não ter lido")
            if lidos_no_clipe:
                frase += (f". Neste mesmo clipe o OCR leu: "
                          f"{', '.join(lidos_no_clipe)}")
            else:
                frase += ". Neste clipe o OCR não leu nenhum outro item do aviso"
            return frase + ". Precisa de conferência humana: está na tela?"

        if achou_18_ambiguo_visao:
            evidencia_partes.append(_frase_ambigua("18+", "18"))
        if achou_publi_ambiguo_visao:
            evidencia_partes.append(
                _frase_ambigua("publi (identificação de publicidade)", "publi"))
        if achou_portaria_ambiguo_visao:
            evidencia_partes.append(_frase_ambigua("portaria", "portaria"))
        if achou_extra_ambiguo_visao:
            evidencia_partes.append(
                _frase_ambigua("jogue com responsabilidade", "extra"))
        if achou_mf_ambiguo_visao:
            evidencia_partes.append(
                _frase_ambigua("Ministério da Fazenda", "ministerio_fazenda"))
        if aposta_suspeita_visual:
            evidencia_partes.append(
                "IA de visão local sugere possível logo/interface de aposta na imagem, mas "
                "nenhum texto confirma — requer conferência humana"
            )
        if escalou_ocr and not (bool(m18) and bool(mport) and bool(mpubli)):
            # Já tentamos o motor reforçado (EasyOCR) e ainda assim não achamos
            # tudo via texto — registra isso pra não parecer que a ausência é
            # "óbvia" sem ter tentado; pode ser texto muito pequeno/baixo
            # contraste que nenhum OCR confirma com segurança (não muda a
            # classificação, é só contexto pra conferência manual).
            evidencia_partes.append(
                "aviso incompleto mesmo após os motores reforçados de OCR (RapidOCR e "
                "EasyOCR) — pode haver texto muito pequeno ou de baixo contraste não "
                "confirmável automaticamente"
            )
        for categoria in categorias_alerta_audio:
            evidencia_partes.append(
                f"ALERTA DE ÁUDIO — fala transcrita {ROTULO_ALERTA_AUDIO[categoria]} — "
                "requer conferência humana pontual (transcrição automática pode errar por "
                "sotaque/ruído, não crava violação sozinha)"
            )
        if alerta_crianca:
            evidencia_partes.append(
                "ALERTA — IA de visão local sugere possível aparição de uma criança no vídeo — "
                "REQUER CONFERÊNCIA HUMANA OBRIGATÓRIA E IMEDIATA (o modelo pode errar/alucinar, "
                "isso não confirma nem descarta o caso sozinho, mas a gravidade exige checagem "
                "prioritária, não apenas rotina)"
            )

        resultado_arquivos.append({
            "arquivo": os.path.basename(path),
            "categorias_alerta_audio": categorias_alerta_audio,
            "alerta_crianca": alerta_crianca,
            "tem_conteudo_aposta": tem_conteudo_aposta or aposta_suspeita_visual,
            "aposta_so_suspeita_visual": aposta_suspeita_visual and not tem_conteudo_aposta,
            # Só é True se ALGUM sinal visual (OCR) apontou aposta/aviso nesse
            # arquivo — usado por classificar_post pra distinguir "menção só de
            # áudio" (elegível pra isenção quando outro clipe do post já tem o
            # aviso completo) de "tem conteúdo visual de aposta" (nunca isento).
            "achou_aposta_visual": bool(maposta_visual or achou_18 or achou_portaria or achou_publi or mextra or mmf),
            "achou_18": achou_18,
            "achou_18_ambiguo_visao": achou_18_ambiguo_visao,
            "achou_portaria": achou_portaria,
            "achou_portaria_ambiguo_visao": achou_portaria_ambiguo_visao,
            "achou_extra": achou_extra,
            "achou_extra_ambiguo_visao": achou_extra_ambiguo_visao,
            "achou_ministerio_fazenda": achou_mf,
            "achou_ministerio_fazenda_ambiguo_visao": achou_mf_ambiguo_visao,
            "achou_publi": achou_publi,
            "achou_publi_ambiguo_visao": achou_publi_ambiguo_visao,
            "achou_assunto_adultos": bool(massunto),
            "achou_sinal_fraco": bool(msinal_fraco),
            "nitidez": nitidez,
            "qualidade": qualidade,
            "evidencia": ", ".join(evidencia_partes),
            "frame_para_visao": frame_para_visao,
        })
    return resultado_arquivos


ROTULO_ELEMENTO_FALTANTE = {
    "18": "aviso 18+",
    "portaria": "aviso da portaria",
    "publi": "identificação de publicidade (#publi)",
    "responsabilidade": "aviso de jogo responsável ('jogue com responsabilidade' ou equivalente, obrigatório antes de 17/07/2026)",
    "ministerio_fazenda": "uma das 3 frases do Ministério da Fazenda (obrigatória a partir de 17/07/2026)",
}


# ---------------------------------------------------------------------------
# O RODAPÉ É UM BLOCO GRÁFICO ÚNICO
# ---------------------------------------------------------------------------
# Quantas linhas do rodapé o OCR precisa ler para se poder afirmar que o bloco
# está na tela. DUAS, e o número tem razão: uma linha só pode ser texto solto da
# legenda que por acaso casou com um termo da régua. Duas linhas do mesmo bloco
# não acontecem por acaso.
MINIMO_LINHAS_PARA_PROVAR_RODAPE = 2

# As quatro linhas que compõem o rodapé obrigatório. O #publi NÃO está aqui de
# propósito: ele fica num canto da tela, em banner separado, e ler o rodapé não
# prova nada sobre ele.
LINHAS_DO_RODAPE = ("18", "portaria", "responsabilidade", "ministerio_fazenda")


def linhas_do_rodape_lidas(r):
    """Quais linhas do rodapé o OCR confirmou NESTE clipe."""
    return [chave for chave, presente in (
        ("18", r.get("achou_18")),
        ("portaria", r.get("achou_portaria")),
        ("responsabilidade", r.get("achou_extra")),
        ("ministerio_fazenda", r.get("achou_ministerio_fazenda")),
    ) if presente]


def rodape_esta_na_tela(r):
    """Se dá para afirmar que o bloco do rodapé está na tela deste clipe.

    POR QUE ISTO PODE SER AFIRMADO (06/09/2026). O rodapé exigido pela Portaria
    é uma peça gráfica renderizada inteira, com o 18+, a advertência do
    Ministério da Fazenda, o jogue com responsabilidade e a menção à portaria
    no mesmo bloco. Ele não aparece pela metade. Então ler duas de suas linhas
    é ler o bloco, e os itens que o OCR não pegou são os de fonte mais fina, não
    itens ausentes.

    Isto NÃO é afrouxamento da régua: a régua de legibilidade decidida pelo
    auditor em 02/09/2026 é PRESENÇA, não perceptibilidade. Se está na tela,
    ainda que pequeno, o item é conforme. Ver o comentário longo em
    classificar_post."""
    return len(linhas_do_rodape_lidas(r)) >= MINIMO_LINHAS_PARA_PROVAR_RODAPE


def classificar_post(arquivos, work_dir, post_date=None):
    """Classifica por peça/clipe: a Portaria SPA/MF 1.231/2024 exige a advertência
    em cada peça publicitária. Um clipe que mostra/menciona aposta e não tem seu
    próprio aviso completo torna o post inteiro Não Conforme, mesmo que outro
    clipe do mesmo post tenha o aviso (um clipe não "cobre" o outro) — não tem
    meio-termo: 4 de 5 clipes certos e 1 errado é post inteiro Não Conforme.

    Exigências sempre valem: 18+, portaria, #publi. Exigência condicional por
    data do post: antes de 17/07/2026 exige também "jogue com responsabilidade"
    (ou equivalente); a partir de 17/07/2026 (Portaria SPA/MF 1.964/2026) essa
    exigência é SUBSTITUÍDA pela de uma das 3 frases do Ministério da Fazenda."""
    if not arquivos:
        return {
            "classificacao": "Requer Verificação",
            "motivo": "Pasta sem arquivo de mídia (vazia ou inacessível)",
            "evidencia": "",
        }

    exige_mf = precisa_ministerio_fazenda(post_date)
    exige_responsabilidade = precisa_jogue_responsabilidade(post_date)
    por_arquivo = analisar_por_arquivo(
        arquivos, work_dir, exige_mf=exige_mf, exige_responsabilidade=exige_responsabilidade
    )
    evidencia_txt = " | ".join(
        f"[{r['arquivo']}] {r['evidencia']}" for r in por_arquivo if r["evidencia"]
    ) or "(nenhum termo do aviso ou de conteúdo de aposta encontrado em nenhum arquivo)"

    # Agrega os alertas de fala problemática de TODOS os arquivos do post (não só
    # do pior clipe) — é um alerta à parte, nunca muda a classificação principal
    # (ver checar_fala_problematica). Um post pode estar Conforme no aviso E
    # ainda assim ter um alerta de áudio, ou vice-versa.
    alertas_audio = [
        {"arquivo": r["arquivo"], "categoria": cat, "rotulo": ROTULO_ALERTA_AUDIO[cat]}
        for r in por_arquivo for cat in r.get("categorias_alerta_audio", [])
    ]

    # Mesmo princípio do alerta de áudio: nunca muda a classificação principal,
    # é um alerta à parte pra conferência humana obrigatória. Roda em TODO
    # arquivo do post, mesmo os "não relacionados a aposta" — a presença de uma
    # criança não depende de o post ser ou não sobre aposta.
    alertas_crianca = [r["arquivo"] for r in por_arquivo if r.get("alerta_crianca")]

    relacionados_aposta = [r for r in por_arquivo if r["tem_conteudo_aposta"]]

    if not relacionados_aposta:
        # Nenhum arquivo do post parece falar de aposta — pode ser um post
        # legitimamente sem esse conteúdo, ou a palavra-chave não pegou. Como
        # esperávamos conteúdo patrocinado de aposta nessas linhas, é mais seguro
        # sinalizar pro auditor conferir do que assumir "Conforme" silenciosamente.
        return {
            "classificacao": "Requer Verificação",
            "motivo": "Nenhum arquivo do post parece conter conteúdo de aposta — confirmar manualmente",
            "evidencia": evidencia_txt,
            # Nenhum clipe específico foi apontado como suspeito, mas o auditor
            # ainda precisa de um jeito rápido de abrir o post pra conferir —
            # aponta pro primeiro arquivo analisado como referência de entrada
            # na pasta, não como "o" arquivo problemático.
            "arquivo": por_arquivo[0]["arquivo"] if por_arquivo else None,
            "alerta_audio": alertas_audio,
            "alerta_crianca": alertas_crianca,
        }

    # Pré-calcula o que falta em cada clipe e se existe um "clipe-âncora" (com
    # o aviso completo) no post — usado a seguir pra decidir a isenção de
    # menção só-áudio.
    faltando_por_arquivo = []
    for r in relacionados_aposta:
        faltando = []
        if not r["achou_18"]:
            faltando.append("18")
        if not r["achou_portaria"]:
            faltando.append("portaria")
        if not r["achou_publi"]:
            faltando.append("publi")
        if exige_responsabilidade and not r["achou_extra"]:
            faltando.append("responsabilidade")
        if exige_mf and not r["achou_ministerio_fazenda"]:
            faltando.append("ministerio_fazenda")
        faltando_por_arquivo.append((r, faltando))

    tem_ancora = any(not faltando for _, faltando in faltando_por_arquivo)

    piores = []
    clipes_isentos_audio = 0
    for r, faltando in faltando_por_arquivo:
        if not faltando:
            continue  # este clipe está conforme

        # Achado real de auditoria: imagem estática só com logo/interface de
        # aposta, sem nenhum texto — nenhum achou_* de OCR bate (não é ausência
        # confirmada, é ausência de TEXTO), só a IA de visão suspeitou de
        # conteúdo. Não crava violação nem libera — exige olho humano.
        if r.get("aposta_so_suspeita_visual"):
            piores.append(("Requer Verificação", {
                **r,
                "motivo_extra": "IA de visão local sugere possível logo/interface de aposta, mas nenhum texto confirma — requer conferência manual (imagem pode ser só logo em produto/vestuário, sem intenção publicitária clara)",
            }))
            continue

        # Achado real de auditoria: a IA de visão pode alucinar (confirmou "18+"
        # numa imagem que era só print de conversa, sem nada relacionado) ou
        # simplesmente não conseguir confirmar algo que provavelmente está lá
        # (texto de baixo contraste). Itens marcados "ambíguos por visão" NÃO
        # contam como confirmadamente ausentes. Se TODOS os itens faltando
        # forem só ambíguos, não crava Não Conforme nem Conforme — exige
        # confirmação humana pontual. Se tiver ao menos um elemento
        # confirmadamente ausente por OCR, o post já é Não Conforme por causa
        # dele, independente da ambiguidade dos outros.
        ambiguos_por_visao = {
            "18": r.get("achou_18_ambiguo_visao"),
            "publi": r.get("achou_publi_ambiguo_visao"),
            "portaria": r.get("achou_portaria_ambiguo_visao"),
            "responsabilidade": r.get("achou_extra_ambiguo_visao"),
            "ministerio_fazenda": r.get("achou_ministerio_fazenda_ambiguo_visao"),
        }
        itens_ambiguos = [f for f in faltando if ambiguos_por_visao.get(f)]
        faltando_nao_ambiguo = [f for f in faltando if f not in itens_ambiguos]

        # O AVISO É UM BLOCO GRÁFICO ÚNICO, E LER DUAS LINHAS DELE PROVA QUE ELE
        # ESTÁ NA TELA (06/09/2026).
        #
        # POR QUE ISTO EXISTIA COMO PROBLEMA. O auditor conferiu três peças da
        # @jojotodynho e reprovou o resultado: "todos estão com o 18+, todos tem
        # identificação de publicidade... pela primeira vez fiquei insatisfeito".
        # Depois: "se for deixar assim, TODOS VÃO FICAR COMO REQUER ANALISE
        # HUMANA, ai nao vai adiantar de naada". Ele estava certo nas duas
        # coisas, e eu conferi os quadros um por um: os quatro itens do rodapé e
        # o #publi estavam na tela nas três peças.
        #
        # O QUE O OCR LEU nas três, medido: "jogue com responsabilidade",
        # "Ministério da Fazenda adverte: aposta não é investimento", "lottu" e
        # em duas delas o "publi". O que ele NÃO leu foi sempre o "18+" e, em
        # duas, a menção à portaria. São os dois itens de fonte mais fina do
        # bloco, e o "18+" é o pior caso conhecido (o código já registra um caso
        # real grafado "1 8+" que desapareceu da leitura).
        #
        # ENTÃO A RÉGUA EXIGIA QUE O OCR LESSE JUSTAMENTE O QUE ELE NÃO LÊ, e
        # sem caminho para CONFORME a automação virava fila de conferência
        # manual. No papel de trabalho isso já aparecia medido: dos 341 casos
        # "não validada", 107 eram "aviso pequeno/baixo contraste".
        #
        # O FUNDAMENTO NÃO É AFROUXAR, É A RÉGUA DELE MESMO. A regra de
        # legibilidade que ele decidiu em 02/09/2026 é PRESENÇA, não
        # perceptibilidade: se está na tela, ainda que pequeno, o item é
        # conforme. E o rodapé obrigatório é UMA peça gráfica renderizada
        # inteira, não linhas independentes: ela sempre traz o 18+ e a portaria
        # junto do resto. Ler duas linhas dela é ler o bloco.
        #
        # AS DUAS TRAVAS QUE MANTÊM ISSO HONESTO:
        #
        #   1. exige DUAS ou mais linhas do bloco lidas por OCR no mesmo clipe.
        #      Uma só não prova bloco: pode ser texto solto da legenda.
        #   2. exige que a IA de visão sugira presença do item que falta. Sem
        #      ela, o programa não conclui nada.
        #
        # Quando o rodapé REALMENTE não está na peça, o OCR não lê nenhuma linha
        # dele, a primeira trava não passa, e nada muda em relação a antes.
        _bloco_na_tela = rodape_esta_na_tela(r)
        if _bloco_na_tela:
            _do_rodape_ambiguos = [f for f in itens_ambiguos
                                   if f in LINHAS_DO_RODAPE]
            if _do_rodape_ambiguos:
                itens_ambiguos = [f for f in itens_ambiguos
                                  if f not in _do_rodape_ambiguos]
                faltando = [f for f in faltando if f not in _do_rodape_ambiguos]

        # O #publi NÃO ENTRA NA REGRA ACIMA, e a diferença é física: ele fica num
        # canto da tela, em banner separado do rodapé. Ler o rodapé não prova
        # nada sobre ele.
        #
        # E O PUBLI NÃO É ABSOLVIDO PELA VISÃO (revisto em 07/09/2026).
        #
        # Até aqui, com o rodapé provado e a visão dizendo que viu o selo, o
        # publi saía da lista e a peça fechava CONFORME. Era um passo além do
        # que a evidência sustenta, e a contraprova está neste próprio arquivo:
        # o Tesseract acha o publi em 4 de 40 quadros e a visão "responde sim
        # com facilidade". Absolver com base nesse sinal é declarar conforme uma
        # peça em que ninguém leu a identificação de publicidade.
        #
        # A REGRA QUE VALE, dita pelo auditor em 07/09/2026: o publi é
        # OBRIGATÓRIO, em qualquer das formas (#publi, publicidade, parceria
        # paga). Ter o rodapé completo e não ter o publi é NÃO CONFORME, e ter
        # só o publi sem o rodapé também é.
        #
        # O QUE DECIDE O VEREDITO NÃO É QUAL ITEM FALTA, É SE O PROGRAMA SABE:
        #
        #     publi lido por OCR                    cumprido
        #     não lido, e a visão diz que NÃO viu   NÃO CONFORME (ausência
        #                                           confirmada por dois motores)
        #     não lido, e a visão diz que viu       REQUER VERIFICAÇÃO (não dá
        #                                           para afirmar ausência)
        #
        # É o que a frase do auditor descreve: "pode ser que não tenha o publi e
        # aí até poderia ir para requer análise, mas só se tiver o restante dos
        # avisos". Sem tirar o publi de `faltando`, o fluxo abaixo faz
        # exatamente isso, porque `itens_ambiguos` sem `faltando_nao_ambiguo`
        # cai em Requer Verificação, e ausência confirmada cai em Não Conforme.
        #
        # O QUE REDUZ A CONFERÊNCIA HUMANA é o OCR ler mais, não a régua
        # perdoar: por isso o quarto degrau de OCR na faixa do topo, que subiu a
        # detecção do publi em 36% na medição de 160 quadros.

        if not faltando:
            continue  # o bloco estava na tela: este clipe está conforme

        if itens_ambiguos and not faltando_nao_ambiguo:
            rotulos_ambiguos = ", ".join(ROTULO_ELEMENTO_FALTANTE[f] for f in itens_ambiguos)
            # O MOTIVO COMEÇA PELO ITEM QUE FALTA CONFERIR, e não pela sugestão da
            # visão (02/09/2026). O texto antigo começava por "IA de visão local
            # sugere presença de...", e foi assim que o próprio auditor leu o
            # resultado do @andersonneiff e concluiu que estava tudo certo, quando
            # o publi não estava na peça. Quem lê linha de planilha lê o começo.
            # SEM AFIRMAR A CAUSA, pelo mesmo motivo da frase de evidência acima:
            # no caso do @andersonneiff o rodapé estava legível e o OCR leu cinco
            # itens; o publi não foi lido porque não estava lá. Dizer "texto
            # pequeno" ali era afirmar causa desconhecida.
            piores.append(("Requer Verificação", {
                **r,
                "motivo_extra": (
                    f"CONFERIR NA PEÇA: {rotulos_ambiguos} está na tela? Nenhum "
                    f"motor de OCR confirmou, e a IA de visão sugere que está "
                    f"presente, o que não confirma nem crava ausência. A régua é "
                    f"presença: se estiver na tela, ainda que pequeno, o item é "
                    f"conforme; se não estiver, é achado"
                ),
            }))
            continue

        # Achado real de auditoria (10+ casos reais confirmados visualmente):
        # 18+, "jogue com responsabilidade" e a menção à portaria costumam vir
        # todos no MESMO banner de 3 linhas (a da portaria é sempre a menor e
        # mais fina, mas qualquer uma das 3 pode falhar no OCR dependendo de
        # fundo/movimento/oclusão — achado real @apoline: "18+" grafado
        # "1 8+" sumiu do OCR enquanto a portaria da MESMA linha foi lida
        # normalmente). Quando só UM item desse banner ficou confirmadamente
        # ausente e outro item do MESMO banner já foi confirmado por OCR no
        # mesmo clipe, é bem mais provável ser falha de leitura pontual do
        # que o banner realmente ter saído incompleto — não crava Não
        # Conforme, exige conferência humana pontual. #publi fica de fora do
        # gatilho de "ausente" (é um banner à parte, em outro canto da tela),
        # mas conta como corroboração de que o OCR está funcionando na cena.
        ITENS_MESMO_BANNER = ("18", "portaria", "responsabilidade")
        if len(faltando_nao_ambiguo) == 1 and faltando_nao_ambiguo[0] in ITENS_MESMO_BANNER:
            confirmados_no_clipe = {
                "18": r["achou_18"], "portaria": r["achou_portaria"],
                "responsabilidade": r["achou_extra"], "publi": r["achou_publi"],
            }
            item_faltando = faltando_nao_ambiguo[0]
            outros_confirmados = [k for k, v in confirmados_no_clipe.items() if k != item_faltando and v]
            if outros_confirmados:
                piores.append(("Requer Verificação", {
                    **r,
                    "motivo_extra": f"outra(s) linha(s) do mesmo aviso ({', '.join(outros_confirmados)}) já foram confirmadas por OCR neste clipe, mas {ROTULO_ELEMENTO_FALTANTE[item_faltando]} não foi lido — o texto costuma ser pequeno/fino e falhar no OCR mesmo quando presente, então é mais provável falha de leitura do que ausência real — requer conferência manual",
                }))
                continue

        # Exceção: um clipe cujo ÚNICO indício de aposta veio do ÁUDIO (nenhum
        # elemento visual de aposta ou de aviso na tela) não precisa do aviso
        # próprio SE outro clipe do mesmo post já tem o aviso completo (o
        # "clipe-âncora") — caso de influenciador só comentando a bet
        # verbalmente sobre uma cena sem nada visual relacionado, dentro de
        # uma sequência que já traz o aviso em outro clipe. Confirma com a IA
        # de visão antes de isentar, pra não isentar um clipe que na verdade
        # mostra o jogo/app sem texto legível pro OCR (falha seguro: em caso
        # de dúvida, NÃO isenta).
        apenas_audio = r["tem_conteudo_aposta"] and not r["achou_aposta_visual"]
        if apenas_audio and tem_ancora:
            if not mostra_conteudo_aposta_visual(r.get("frame_para_visao")):
                clipes_isentos_audio += 1
                continue  # isento: coberto pelo clipe-âncora do post

        qualidade = r.get("qualidade") or {}
        # Só conta como "problema técnico do arquivo" (Requer Verificação) quando
        # há evidência REAL de recompressão (resolução/bitrate abaixo do esperado
        # pro formato original). Texto pequeno/ilegível num arquivo de qualidade
        # normal não é desculpa — a Portaria exige legibilidade, então isso é
        # Não Conforme direto, não "talvez seja só o arquivo".
        possivel_problema_tecnico = bool(qualidade.get("possivel_recompressao"))
        algum_sinal_limpo = (
            r["achou_18"] or r["achou_portaria"] or r["achou_publi"]
            or r["achou_extra"] or r["achou_ministerio_fazenda"]
        )

        if possivel_problema_tecnico:
            piores.append(("Requer Verificação", {
                **r,
                "motivo_extra": f"possível degradação técnica do arquivo salvo (resolução {qualidade.get('largura')}x{qualidade.get('altura')}, abaixo do esperado pro formato original) — não dá pra confirmar ausência do aviso com segurança, pode não ser não conformidade real",
            }))
        elif not algum_sinal_limpo and r["achou_sinal_fraco"]:
            # Não achou nenhum elemento do aviso limpo, mas achou fragmento solto
            # do texto-padrão do banner (ex: "diversão", "pare", "responsabilidad")
            # — indício de que existe uma TENTATIVA de aviso ali, só que obstruída,
            # cortada ou bagunçada demais pro OCR fechar. Isso não é "não tem o
            # aviso", é "não dá pra confirmar com segurança" — exige olho humano,
            # não crava violação.
            piores.append(("Requer Verificação", {
                **r,
                "motivo_extra": "exige análise manual — encontrado fragmento do aviso (possivelmente obstruído, cortado ou ilegível), não dá pra confirmar nem descartar com segurança só pelo OCR",
            }))
        else:
            # Sem meio-termo: algum elemento obrigatório não foi encontrado de
            # forma legível. Motivo específico, sempre citando qual(is)
            # elemento(s) — mas exclui da lista reportada qualquer item que
            # seja só ambíguo por visão (não confirmadamente ausente): dizer
            # "falta 18+"/"falta #publi" quando na verdade a IA de visão
            # sugere que ESTÁ lá seria impreciso e contradiz a evidência
            # (achados reais: selo "18+" visível e #publi de baixo contraste,
            # ambos confirmados por visão, mas o rótulo dizia "falta" mesmo
            # assim).
            #
            # "ILEGÍVEL OU AUSENTE", E NÃO "FALTA" (09/09/2026). Achado real:
            # duas peças de @crissevieri.mov reprovadas com "falta 18+, aviso
            # da portaria" quando os avisos ESTAVAM lá, escritos na vertical
            # (girados 90°). Nenhum dos três OCR lê texto girado, então o
            # programa não leu — e não ter lido não é o mesmo que confirmar
            # ausência. O veredito Não Conforme continua certo (aviso na
            # vertical não cumpre a exigência de estar legível), mas afirmar
            # "falta" é uma frase que o influenciador derruba abrindo a peça e
            # apontando o selo. Mesmo ajuste em pipeline._rotulo_base, que
            # monta o rótulo curto da planilha a partir deste motivo.
            detalhe = "ilegível ou ausente: " + ", ".join(ROTULO_ELEMENTO_FALTANTE[f] for f in faltando_nao_ambiguo)
            # Corrigido em 28/08/2026: os itens tirados da lista por serem só
            # ambíguos passam a ser DITOS, em vez de sumirem calados. Antes a
            # mensagem listava só os confirmadamente ausentes e quem lia
            # concluía que o resto tinha sido encontrado, o que é falso: o item
            # não foi lido por OCR nenhum, apenas a IA de visão sugeriu que
            # estava lá. Acontecia em 23 dos 56 casos Não Conforme do cache,
            # quase sempre com o #publi, que o OCR raramente lê (o Tesseract
            # acha em 4 de 40 quadros) e sobre o qual a visão responde "sim"
            # com facilidade. A classificação não muda, só o texto.
            if itens_ambiguos:
                nao_lidos = ", ".join(ROTULO_ELEMENTO_FALTANTE[f] for f in itens_ambiguos)
                detalhe += (f" (também não foi lido por nenhum OCR: {nao_lidos}, "
                            "mas a IA de visão sugere que está presente, por isso "
                            "não entra como ausente e requer conferência humana)")
            piores.append(("Não Conforme", {**r, "faltando": faltando_nao_ambiguo, "motivo_extra": detalhe}))

    if not piores:
        motivo_conforme = "Todo clipe com conteúdo de aposta tem o aviso completo exigido para a data do post"
        if clipes_isentos_audio:
            motivo_conforme += f" ({clipes_isentos_audio} clipe(s) com menção só de áudio, sem nada visual, isento(s) por já haver aviso completo em outro clipe do post)"
        return {"classificacao": "Conforme", "motivo": motivo_conforme, "evidencia": evidencia_txt, "alerta_audio": alertas_audio, "alerta_crianca": alertas_crianca}

    # Prioriza o pior veredito entre os clipes problemáticos: Não Conforme > Requer
    # Verificação. Dentro de clipes igualmente "Não Conforme", prioriza o que tem
    # MAIS elementos faltando (o mais grave) — sem esse critério, min() pegava o
    # primeiro da lista em caso de empate de classe, o que podia esconder um clipe
    # sem NENHUM elemento do aviso atrás de outro clipe que só faltava um item.
    ordem = {"Não Conforme": 0, "Requer Verificação": 1}
    pior_classe, pior_r = min(
        piores, key=lambda x: (ordem[x[0]], -len(x[1].get("faltando", [])))
    )
    detalhe = pior_r.get("motivo_extra", "sem aviso completo próprio")
    return {
        "classificacao": pior_classe,
        "motivo": f"Clipe '{pior_r['arquivo']}' mostra conteúdo de aposta: {detalhe}",
        "evidencia": evidencia_txt,
        "arquivo": pior_r["arquivo"],
        "achou_18": pior_r["achou_18"],
        "achou_portaria": pior_r["achou_portaria"],
        "achou_publi": pior_r["achou_publi"],
        "achou_extra": pior_r["achou_extra"],
        "achou_ministerio_fazenda": pior_r["achou_ministerio_fazenda"],
        "exigia_ministerio_fazenda": exige_mf,
        "exigia_jogue_responsabilidade": exige_responsabilidade,
        "faltando": pior_r.get("faltando", []),
        "alerta_audio": alertas_audio,
        "alerta_crianca": alertas_crianca,
    }


def rodar_manifesto(manifest_path, work_dir):
    import json
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    resultados = []
    for entry in manifest:
        row_work_dir = os.path.join(work_dir, "_work_" + str(entry["excel_row"]))
        os.makedirs(row_work_dir, exist_ok=True)

        arquivos = entry.get("arquivos_baixados", [])
        if entry.get("erro"):
            resultado = {
                "classificacao": "Requer Verificação",
                "motivo": f"Falha ao acessar material: {entry['erro']}",
                "evidencia": "",
            }
        else:
            resultado = classificar_post(arquivos, row_work_dir, post_date=entry.get("data"))

        resultados.append({**entry, **resultado})
        print(entry["excel_row"], entry["influenciador"], "->", resultado["classificacao"], "| gabarito:", entry.get("f"))

    return resultados


if __name__ == "__main__":
    import json
    manifest_path = sys.argv[1]
    work_dir = sys.argv[2]
    out_path = sys.argv[3]
    resultados = rodar_manifesto(manifest_path, work_dir)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
