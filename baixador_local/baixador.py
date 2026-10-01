# -*- coding: utf-8 -*-
"""
Baixador local de vídeos de influenciadores, para a auditoria da EGB.

PARA QUE SERVE

Baixa os vídeos na SUA máquina, usando a sessão do Instagram que você já tem
aberta no Firefox. Depois é só arrastar os arquivos para a aba Downloads do
programa de auditoria, que ele renomeia, guarda na pasta certa do Drive e
registra na Monitoramento.

POR QUE NA SUA MÁQUINA, E NÃO NO SERVIDOR (decidido em 29/08/2026)

Porque o Instagram olha o padrão de acesso, não só a quantidade. Cinco pessoas
baixando de cinco computadores, cada uma com a sua sessão e o seu endereço de
rede, é o que já acontece hoje e o Instagram trata como uso normal. Juntar tudo
num servidor só concentra 125 downloads por dia num endereço e numa conta, que
é justamente o padrão que derrubou duas contas em agosto de 2026.

POR QUE NÃO PRECISA DE EXTENSÃO

O yt-dlp lê a sessão direto do Firefox. Medido em 29/08/2026 nesta máquina:
Chrome e Edge NÃO funcionam, porque da versão 127 em diante eles cifram os
cookies de um jeito que amarra a leitura ao próprio navegador. O Firefox não
faz isso. Por isso: **use o Firefox para o Instagram do trabalho.**

O QUE ELE NÃO FAZ

Não fala com o Google, não tem credencial nenhuma, não sobe nada para lugar
nenhum. Só baixa para uma pasta aqui do lado. Isso é proposital: assim não é
preciso espalhar credencial da auditoria por cinco computadores.

COMO USAR

1. Abra o Firefox e entre no Instagram do trabalho (uma vez só).
2. Dê dois cliques em Baixar.bat.
3. Cole os endereços dos posts, um por linha, e dê Enter numa linha vazia.
4. Espere. Os vídeos aparecem na pasta "videos".
5. Arraste os arquivos para a aba Downloads do programa de auditoria.

INSTALAÇÃO

Precisa de Python e do yt-dlp:

    py -m pip install --upgrade yt-dlp
"""
import json
import os
import random
import re
import sys
import time
from datetime import datetime

PASTA = os.path.dirname(os.path.abspath(__file__))
PASTA_VIDEOS = os.path.join(PASTA, "videos")
ARQUIVO_LINKS = os.path.join(PASTA, "links.txt")
ARQUIVO_CONTAGEM = os.path.join(PASTA, "_contagem_do_dia.json")

NAVEGADOR = "firefox"

# Teto diário nesta máquina.
#
# LIGADO EM 20 NO DIA 30/08/2026, primeira etapa de uma subida medida. Ficou
# desligado de 29 a 30/08 de propósito, porque o 40 anterior tinha sido
# escolhido no chute, e número inventado num freio de segurança é pior que
# freio nenhum: passa a sensação de que alguém calculou.
#
# O QUE SUSTENTA O 20, agora que há registro:
#
#   o custo por vídeo caiu pela metade   desde 29/08 o story é baixado em 2
#                                        chamadas, e não 3 a 4, e nenhuma
#                                        delas vai para a consulta por @, que
#                                        é o endereço mais limitado
#
#   o dia 25/08 não foi o que parecia    das 34 chamadas, só 10 deram certo;
#                                        24 foram falha, boa parte repetindo
#                                        em cima de perfil sem story. Não foi
#                                        volume, foi insistência
#
#   acima de 15 por dia não há dado      nenhum, no regime novo. Por isso 20 e
#                                        não 25, que é o que o Marketing pede
#
# COMO CONTINUAR: uma semana em 20 sem nenhum sinal de "vá devagar" autoriza
# ir a 30. Cada etapa precisa da semana de observação antes da próxima. Este
# número precisa acompanhar o LIMITE_DIARIO_INSTAGRAM do fluxo_downloads.py,
# que tem a mesma justificativa escrita por extenso.
#
# Para desligar de novo, ponha None. O contador continua funcionando e
# aparecendo na tela dos dois jeitos.
TETO_DIARIO = 20

# Pausa entre um post do Instagram e o outro.
#
# Alargada em 29/08/2026, de 20 a 45 para 30 a 180 segundos, pelo mesmo
# raciocínio do servidor: regularidade é sinal. Pausa sempre dentro de uma
# faixa estreita desenha um padrão, porque ninguém clica com precisão de
# relógio. Alargar sobe a média e sobe a variação.
#
# Custo: 30 vídeos passam de uns 16 minutos para uns 52. Como roda em segundo
# plano, enquanto a pessoa faz outra coisa, isso não atrapalha.
PAUSA_MIN, PAUSA_MAX = 30, 180

EH_INSTAGRAM = re.compile(r"instagram\.com", re.IGNORECASE)


def dizer(msg=""):
    print(msg, flush=True)


# ------------------------------------------------------------------
# Teto do dia
# ------------------------------------------------------------------
def _ler_contagem():
    """Quantos endereços já foram processados hoje nesta máquina.

    Duas coisas aprendidas em 30/08/2026, no primeiro uso real:

    utf-8-sig, e não utf-8: se alguém editar este arquivo pelo Bloco de Notas
    ou pelo PowerShell, ele ganha uma marca invisível no começo que faz a
    leitura falhar. O resto do programa já lia assim, por esse mesmo motivo.

    E, principalmente: NÃO ZERAR EM SILÊNCIO. Antes, qualquer falha de leitura
    reiniciava a contagem do zero sem avisar, e foi o que aconteceu: o
    contador dizia 2 quando o uso real do dia era 4. Contador que se reinicia
    sozinho é pior que contador nenhum, porque subestima o uso justamente
    quando ele serve para decidir um teto seguro para a conta da pessoa."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(ARQUIVO_CONTAGEM):
        return {"dia": hoje, "baixados": 0}
    try:
        with open(ARQUIVO_CONTAGEM, encoding="utf-8-sig") as f:
            dados = json.load(f)
    except (OSError, ValueError) as e:
        dizer("AVISO: não consegui ler a contagem de hoje, então ela recomeça do zero.")
        dizer(f"       O número na tela vai ficar MENOR que o uso real. {str(e)[:80]}")
        dizer()
        return {"dia": hoje, "baixados": 0}
    if dados.get("dia") != hoje:
        return {"dia": hoje, "baixados": 0}
    dados.setdefault("baixados", 0)
    return dados


def _gravar_contagem(dados):
    try:
        with open(ARQUIVO_CONTAGEM, "w", encoding="utf-8") as f:
            json.dump(dados, f)
    except OSError:
        pass


# ------------------------------------------------------------------
# Sessão do Firefox
# ------------------------------------------------------------------
def conferir_sessao():
    """Confere que dá para ler a sessão do Instagram do Firefox, ANTES de
    tentar baixar. Sem isso a pessoa só descobriria o problema depois de o
    primeiro download falhar com uma mensagem que não explica nada."""
    try:
        from yt_dlp.cookies import extract_cookies_from_browser
    except Exception:
        dizer("Não achei o yt-dlp. Instale com:")
        dizer("    py -m pip install --upgrade yt-dlp")
        return False

    try:
        jar = extract_cookies_from_browser(NAVEGADOR)
    except Exception as e:
        dizer("Não consegui ler a sessão do Firefox.")
        dizer(f"   Detalhe técnico: {str(e)[:160]}")
        dizer()
        dizer("O que costuma resolver:")
        dizer("  1. O Firefox está instalado? Este programa usa o Firefox de propósito:")
        dizer("     Chrome e Edge cifram os cookies e não deixam ler.")
        dizer("  2. Você já entrou no Instagram pelo Firefox pelo menos uma vez?")
        return False

    nomes = {c.name for c in jar if "instagram.com" in (c.domain or "")}
    if "sessionid" not in nomes:
        dizer("O Firefox está acessível, mas não há sessão do Instagram nele.")
        dizer()
        dizer("Abra o Firefox, entre no Instagram do trabalho, e rode de novo.")
        return False

    dizer("Sessão do Instagram encontrada no Firefox.")
    return True


# ------------------------------------------------------------------
# Links
# ------------------------------------------------------------------
def ler_links():
    """Do arquivo links.txt, se existir; senão pergunta na tela."""
    if os.path.exists(ARQUIVO_LINKS):
        with open(ARQUIVO_LINKS, encoding="utf-8") as f:
            links = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        if links:
            dizer(f"{len(links)} endereço(s) lidos de links.txt")
            return links

    dizer()
    dizer("Cole os endereços dos posts, um por linha.")
    dizer("Quando terminar de colar, dê ENTER numa linha VAZIA para começar.")
    dizer()
    links = []
    while True:
        try:
            linha = input("  ").strip()
        except EOFError:
            break
        if not linha:
            if links:
                break
            # Enter numa lista vazia costuma ser engano, não fim.
            dizer("  (nenhum endereço ainda. Cole um, ou dê Enter de novo para sair)")
            try:
                if not input("  ").strip():
                    break
            except EOFError:
                break
            continue
        links.append(linha)
        # Retorno depois de cada link. Sem isto a tela fica muda enquanto o
        # programa espera, e parece travada: foi o que aconteceu no primeiro
        # uso real, em 30/08/2026. A pessoa colou dois endereços e ficou sem
        # saber que faltava um Enter.
        dizer(f"     {len(links)} endereço(s) na lista. "
              f"Cole o próximo, ou ENTER para começar a baixar.")
    return links


# ------------------------------------------------------------------
# Download
# ------------------------------------------------------------------
def _nome_seguro(texto):
    for proibido in '/\\:*?"<>|':
        texto = texto.replace(proibido, "-")
    return texto.strip()


def _opcoes_de_disfarce():
    """Faz o programa se apresentar como um navegador de verdade.

    A extensão que o Marketing usa hoje pega o vídeo que o navegador já
    carregou. Este programa faz requisições próprias, com os mesmos cookies,
    mas com assinatura de script, que é mais fácil de distinguir de uma pessoa
    navegando. Com a biblioteca curl-cffi instalada, o yt-dlp consegue imitar
    um navegador de verdade até no nível da conexão.

    Volta vazio se a biblioteca não estiver instalada, para o programa
    continuar funcionando, só com risco maior de ser reconhecido.

        py -m pip install "yt-dlp[default,curl-cffi]" """
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        return {"impersonate": ImpersonateTarget("chrome")}
    except Exception:
        return {}


_HANDLE_NA_URL = re.compile(
    r"instagram\.com/(?:stories/)?(?P<handle>[A-Za-z0-9_.]+)(?:/|$)", re.IGNORECASE)
# Trechos que aparecem na posição do @ mas não são o @ de ninguém.
_NAO_SAO_HANDLE = {"p", "reel", "reels", "tv", "stories", "explore", "accounts",
                   "share", "s", "direct"}


def descobrir_handle(link, entrada):
    """Descobre o @ do influenciador, na ordem do mais confiável.

    O ENDEREÇO VEM PRIMEIRO, e isso foi aprendido no primeiro uso real
    (30/08/2026): num download de story o Instagram devolveu o NÚMERO interno
    do perfil no campo do autor, e o arquivo saiu chamado
    "4777871830_..." em vez de "lomma_...". A tela então procuraria uma pasta
    @4777871830, que não existe no Drive de ninguém.

    O endereço que a pessoa colou traz o @ de verdade, escrito por gente:
    instagram.com/stories/lomma/... ou instagram.com/lomma/reel/...

    Número puro é recusado em qualquer origem: nenhum @ do Instagram é só
    dígito, então se veio só dígito é o identificador interno, não o nome."""
    def limpar(valor):
        v = str(valor or "").strip().lstrip("@").strip().lower()
        # RECUSAR, não limpar. Tirar os caracteres estranhos transformaria
        # "Canal do Fulano" em "canaldofulano", que parece um @ e não é o @ de
        # ninguém, e aí o vídeo iria procurar uma pasta que não existe. Um @ do
        # Instagram só tem letra, número, ponto e sublinhado; qualquer outra
        # coisa quer dizer que aquele campo trouxe outra informação.
        if not re.fullmatch(r"[a-z0-9_.]+", v):
            return ""
        if v.isdigit() or v in _NAO_SAO_HANDLE:
            return ""
        return v

    m = _HANDLE_NA_URL.search(str(link or ""))
    if m:
        do_endereco = limpar(m.group("handle"))
        if do_endereco:
            return do_endereco

    for campo in ("channel", "uploader_id", "uploader"):
        achado = limpar(entrada.get(campo))
        if achado:
            return achado
    return ""


def _arrumar_nome(ydl, entrada, indice, link=""):
    """Renomeia o arquivo baixado para o padrão que o programa de auditoria
    sabe ler sozinho:

        handle_1756500000_2026-08-29 - DMvHalbg8dD.mp4

    Por isso NÃO é preciso digitar o @ de ninguém: ele vem do próprio vídeo,
    informado pelo Instagram, que é mais confiável que digitação à mão.

    Devolve (caminho, handle, data) ou None se o arquivo não apareceu."""
    bruto = ydl.prepare_filename(entrada)
    if not os.path.exists(bruto):
        return None

    handle = descobrir_handle(link or entrada.get("webpage_url"), entrada)

    data = None
    if entrada.get("upload_date"):
        try:
            data = datetime.strptime(entrada["upload_date"], "%Y%m%d").date()
        except ValueError:
            pass
    if data is None and entrada.get("timestamp"):
        try:
            data = datetime.fromtimestamp(int(entrada["timestamp"])).date()
        except (ValueError, OSError):
            pass
    if data is None:
        data = datetime.now().date()

    extensao = os.path.splitext(bruto)[1] or ".mp4"
    codigo = _nome_seguro(str(entrada.get("id") or indice))
    if handle:
        # O número do meio precisa ter 10 dígitos ou mais para o programa de
        # auditoria reconhecer o padrão. O horário serve bem e ainda evita que
        # dois arquivos do mesmo dia se sobreponham. O micro-segundo entra
        # porque uma story inteira baixa no mesmo segundo.
        carimbo = int(time.time() * 100) % 10_000_000_000
        nome = f"{handle}_{carimbo:010d}_{data:%Y-%m-%d} - {codigo}{extensao}"
    else:
        # Sem o @, o arquivo ainda serve: a pessoa informa o influenciador na
        # tela ao enviar. Melhor entregar o vídeo do que recusar.
        nome = f"SEM-INFLUENCIADOR_{data:%Y-%m-%d}_{codigo}{extensao}"

    destino = os.path.join(PASTA_VIDEOS, nome)
    os.replace(bruto, destino)
    return destino, handle, data


def baixar(link, indice, total):
    """Baixa um endereço e devolve a lista do que veio.

    UM ENDEREÇO PODE TRAZER VÁRIOS VÍDEOS (corrigido em 30/08/2026, no
    primeiro uso real). Endereço de story traz a sequência inteira do perfil,
    e post em carrossel traz todos os itens. A primeira versão só sabia lidar
    com um: baixava os três, não conseguia renomear nenhum, e dava o endereço
    como falho, deixando os arquivos órfãos na pasta com nome provisório.

    Aqui pegar todos é o certo, diferente do caminho do servidor. Lá uma linha
    da planilha é um vídeo, então é preciso saber qual. Aqui são só arquivos:
    a pessoa arrasta todos na tela depois, e cada um vira a sua linha."""
    import yt_dlp

    os.makedirs(PASTA_VIDEOS, exist_ok=True)
    opcoes = {
        "outtmpl": os.path.join(PASTA_VIDEOS, "_baixando_%(id)s.%(ext)s"),
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "cookiesfrombrowser": (NAVEGADOR,),
        **_opcoes_de_disfarce(),
    }

    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(link, download=True)
        entradas = [e for e in (info.get("entries") or [info]) if e]
        arrumados = [r for r in (_arrumar_nome(ydl, e, f"{indice}_{i}", link)
                                 for i, e in enumerate(entradas)) if r]

    if not arrumados:
        raise RuntimeError("nenhum arquivo gerado, o conteúdo pode ter saído do ar")
    return arrumados


def limpar_provisorios():
    """Apaga sobras de nome provisório de execuções que falharam no meio.

    Existe porque a primeira versão deixava esses arquivos para trás quando o
    endereço trazia mais de um vídeo. São inúteis: o programa de auditoria não
    reconhece o nome deles, e eles voltam a ser baixados numa nova tentativa."""
    if not os.path.isdir(PASTA_VIDEOS):
        return 0
    apagados = 0
    for nome in os.listdir(PASTA_VIDEOS):
        if nome.startswith("_baixando_"):
            try:
                os.remove(os.path.join(PASTA_VIDEOS, nome))
                apagados += 1
            except OSError:
                pass
    return apagados


def main():
    dizer("=" * 66)
    dizer("  Baixador de vídeos  |  Auditoria Interna EGB")
    dizer("=" * 66)
    dizer()

    if not conferir_sessao():
        return 1

    sobras = limpar_provisorios()
    if sobras:
        dizer(f"Limpei {sobras} arquivo(s) pela metade, de uma tentativa anterior.")
        dizer()

    contagem = _ler_contagem()
    if TETO_DIARIO is None:
        # Sem teto, mas com contagem: é ela que vai dizer, depois de alguns
        # dias de uso real, qual número faz sentido.
        dizer(f"Baixados hoje nesta máquina: {contagem['baixados']} (sem teto definido).")
        restam = None
    else:
        restam = TETO_DIARIO - contagem["baixados"]
        dizer(f"Baixados hoje nesta máquina: {contagem['baixados']} de {TETO_DIARIO}.")
        if restam <= 0:
            dizer()
            dizer("Você chegou ao teto de hoje. O contador zera amanhã.")
            dizer("O teto não é capricho: insistir depois do limite é o que")
            dizer("transforma conta normal em conta sinalizada.")
            return 1
        if restam <= 5:
            # Avisar ANTES de bater no teto, e não só quando bate: a pessoa
            # precisa poder decidir o que baixar hoje e o que deixa para amanhã,
            # em vez de descobrir no meio da lista.
            dizer(f"Atenção: restam só {restam} para hoje.")

    links = ler_links()
    if not links:
        dizer("Nenhum endereço informado. Nada a fazer.")
        return 0

    if restam is not None and len(links) > restam:
        dizer()
        dizer(f"Você colou {len(links)}, mas só restam {restam} para hoje. "
              f"Vou baixar os {restam} primeiros.")
        links = links[:restam]

    dizer()
    dizer(f"Baixando {len(links)} vídeo(s). Pode deixar rodando e ir fazer outra coisa.")
    dizer()

    certos, erros = [], []
    for i, link in enumerate(links, 1):
        dizer(f"[{i}/{len(links)}] {link[:80]}")
        try:
            vieram = baixar(link, i, len(links))
            if len(vieram) > 1:
                dizer(f"          esse endereço trouxe {len(vieram)} vídeos "
                      f"(story ou carrossel)")
            for caminho, handle, data in vieram:
                quem = f"@{handle}" if handle else "influenciador não identificado"
                dizer(f"          pronto: {quem}, {data:%d/%m/%Y}, "
                      f"{os.path.getsize(caminho) / 1024 / 1024:.1f} MB")
                certos.append(caminho)
            contagem["baixados"] += 1
            _gravar_contagem(contagem)
        except Exception as e:
            texto = str(e)
            if any(s in texto.lower() for s in ("429", "rate", "too many", "login", "checkpoint")):
                dizer(f"          o Instagram barrou: {texto[:120]}")
                dizer()
                dizer("PARANDO AQUI DE PROPÓSITO. Insistir depois de um bloqueio é o que")
                dizer("transforma limite temporário em conta sinalizada. Tente de novo")
                dizer("daqui a algumas horas, ou amanhã.")
                erros.append((link, "Instagram barrou o acesso"))
                break
            dizer(f"          não deu: {texto[:120]}")
            erros.append((link, texto[:120]))

        if i < len(links) and EH_INSTAGRAM.search(link):
            pausa = random.uniform(PAUSA_MIN, PAUSA_MAX)
            dizer(f"          (pausa de {pausa:.0f}s antes do próximo, de propósito)")
            time.sleep(pausa)

    dizer()
    dizer("=" * 66)
    dizer(f"  {len(certos)} baixado(s), {len(erros)} com problema.")
    if certos:
        dizer(f"  Estão em: {PASTA_VIDEOS}")
        dizer()
        dizer("  Agora arraste esses arquivos para a aba Downloads do programa")
        dizer("  de auditoria. Ele descobre o influenciador e a data pelo nome,")
        dizer("  renomeia no padrão do Marketing e registra na Monitoramento.")
    if erros:
        dizer()
        dizer("  Não deram certo:")
        for link, motivo in erros:
            dizer(f"    - {link[:60]}: {motivo}")
    dizer("=" * 66)
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except KeyboardInterrupt:
        dizer()
        dizer("Interrompido.")
        codigo = 1
    dizer()
    try:
        # A janela do Prompt de Comando fecha sozinha ao terminar, e sem esta
        # pausa a pessoa não chega a ler o resultado. O try existe para o
        # programa também poder ser chamado sem teclado, em teste.
        input("Pressione Enter para fechar.")
    except EOFError:
        pass
    sys.exit(codigo)
