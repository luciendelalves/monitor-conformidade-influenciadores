# -*- coding: utf-8 -*-
"""
A visão recebe a FAIXA do rodapé ampliada, não o quadro inteiro.

POR QUE ESTE ARQUIVO EXISTE (06/09/2026)

O auditor: "a visão local precisa trabalhar mais". Investigado, e o problema não
era esforço: era o que ela recebia. Medido na tela 3 da @jojotodynho, a peça em
que a portaria ESTÁ na tela e o programa insistia em pedir conferência dela:

    pergunta          quadro inteiro            faixa ampliada 4x
    genérica          SIM                       SIM
    específica        NÃO                       SIM
    transcrição       "PAGA PELA PORTE SUA      "JOGUE COM RESPONSABILIDADE.
    aberta            NÃO 18" (ilegível)        CONSULTE T&CS. A CONCURSO DA
                                                PORTEIRA EM 36/2" (quase exata)

No quadro inteiro ela chuta; na faixa ela lê. Num quadro de 720x1280 a linha da
portaria é o texto mais fino da tela.

A CONTRADIÇÃO APARENTE COM O OCR, registrada para ninguém "consertar" depois: no
mesmo dia, recortar e ampliar para o OCR PIOROU a leitura, e a hipótese foi
descartada. Não é contradição. O OCR precisa de caractere nítido e a ampliação
borra; a visão precisa de resolução relativa e contexto, e a ampliação entrega
os dois. São dois consumidores com necessidades opostas sobre a mesma imagem.

RESULTADO NAS TRÊS PEÇAS REAIS: antes, todas pediam conferência humana de itens
que estavam na tela. Depois da regra do bloco (ver teste_rodape_bloco_unico.py)
duas fecharam. Com esta correção da visão, as três fecham como Conforme.

Rodar:

    py testes\teste_visao_recebe_a_faixa.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


def rodar():
    import validar_avisos_portaria136 as v

    print("--- 1. os numeros do recorte sao explicitos ---")
    conferir(0 < v.FAIXA_DO_RODAPE < 0.5,
             f"a faixa e uma fracao da altura ({v.FAIXA_DO_RODAPE})",
             "se passar de metade da tela deixa de ser 'faixa do rodape'")
    conferir(v.AMPLIACAO_DA_FAIXA >= 2,
             f"e ela e ampliada ({v.AMPLIACAO_DA_FAIXA}x)",
             "sem ampliar, o recorte nao resolve resolucao relativa")

    print()
    print("--- 2. o #publi tem a faixa DELE, e ela foi medida ---")
    # ATUALIZADO EM 07/09/2026. Antes o #publi era o unico item que recebia o
    # QUADRO INTEIRO, porque recortar o rodape o cortaria fora. O auditor pegou
    # o efeito em uso real: "o publi geralmente fica em outro canto da pagina,
    # longe do +18 e do aviso da portaria, e ontem faltou pegar isso, e estava
    # visivel". Quadro inteiro e exatamente a condicao em que a visao chuta, que
    # e o que se mediu no rodape.
    #
    # MEDICAO, 450 quadros do cache, 55 ocorrencias com coordenada:
    #     topo, ate 25% da altura   38 (69%)   mediana 0,091
    #     base, acima de 80%       ~14 (25%)   p75 0,873
    #     meio                      ~3 (6%)
    # Ele e BIMODAL, e por isso recebe as DUAS faixas, nao uma.
    conferir("publi" not in v.ITENS_DO_RODAPE_PARA_VISAO,
             "o #publi continua fora da lista de itens do rodape",
             str(v.ITENS_DO_RODAPE_PARA_VISAO))
    for item in ("18", "portaria", "extra", "ministerio_fazenda"):
        conferir(item in v.ITENS_DO_RODAPE_PARA_VISAO,
                 f"{item} usa a faixa de baixo")
    conferir(0 < v.FAIXA_DO_PUBLI_TOPO <= 0.30,
             f"existe faixa do topo, e ela e uma fracao pequena "
             f"({v.FAIXA_DO_PUBLI_TOPO})",
             "acima de 0,30 deixa de ser faixa: a medicao mostrou que entre "
             "0,25 e 0,80 nao ha praticamente nada")

    print()
    print("--- 3. NENHUM item recebe mais o quadro inteiro ---")
    fonte = open(os.path.join(BASE, "validar_avisos_portaria136.py"),
                 encoding="utf-8").read()
    trecho = fonte.split("if itens_para_visao and frame_para_visao:")[1][:2200]
    conferir("recortar_faixa_do_rodape(frame_para_visao)" in trecho,
             "a faixa de baixo e usada")
    conferir("recortar_faixa_do_topo(frame_para_visao)" in trecho,
             "a faixa de cima tambem")
    conferir("perguntar_visao_local(frame_para_visao," not in trecho,
             "e o quadro inteiro NAO e mais perguntado a visao",
             "era o que o #publi recebia, e e onde a visao chuta")
    # Duas faixas sao dois LUGARES do mesmo item, nao dois requisitos.
    # TESTA O COMPORTAMENTO, E NAO O TEXTO DO CODIGO (08/09/2026). A versao
    # anterior exigia a linha literal `if achou:`, e reprovou quando a fusao das
    # duas faixas passou a usar _combinar_respostas para nao afirmar ausencia
    # com resposta de uma faixa so. A propriedade sob teste sempre foi a regra,
    # nao a forma de escrever.
    conferir("_combinar_respostas" in trecho,
             "as duas faixas sao COMBINADAS, e nao uma sobrescrevendo a outra")
    conferir(v._combinar_respostas(False, True) is True
             and v._combinar_respostas(True, False) is True,
             "basta uma das duas faixas responder sim",
             "exigir as duas seria exigir o publi duas vezes na mesma peca")
    conferir(v._combinar_respostas(False, None) is None
             and v._combinar_respostas(None, False) is None,
             "e faixa que NAO RESPONDEU nao deixa a outra cravar ausencia",
             "sem isso, resposta de uma faixa so afirmaria que o item nao esta la")

    print()
    print("--- 3b. o OCR ganhou a faixa do topo, em UNIAO com o quadro ---")
    # Medido em 160 quadros: quadro inteiro le o publi em 14, recorte cru le em
    # 8, recorte ampliado le em 5 (ampliar borra o caractere, mesmo achado do
    # rodape), e a UNIAO le em 19. O recorte sozinho e pior e ainda assim acha 5
    # quadros que o quadro inteiro perde. Daí a uniao, e nao a troca.
    conferir("recortar_faixa_do_topo(f, ampliar=False)" in fonte,
             "o OCR usa o recorte CRU, sem ampliar")
    conferir("_buscar_matches(ocr_texto)[5]" in fonte,
             "e so entra quando o publi NAO foi lido nos tres degraus",
             "peca com publi legivel nao paga esse custo")
    conferir("ocr_texto +=" in fonte.split("ampliar=False")[1][:400],
             "e o resultado SOMA ao texto ja lido, em vez de substituir")

    print()
    print("--- 4. o recorte FALHA SEGURO ---")
    # Se o ffmpeg nao estiver disponivel, ou a imagem for invalida, a visao
    # tem que receber ALGO. Devolver None a deixaria sem imagem e o item
    # ficaria sem confirmacao por um motivo que nao e a peca.
    inexistente = os.path.join(BASE, "nao_existe_esta_imagem_12345.jpg")
    devolvido = v.recortar_faixa_do_rodape(inexistente)
    conferir(devolvido == inexistente,
             "imagem invalida devolve a original, nao None",
             str(devolvido)[-40:])

    print()
    print("--- 5. o recorte funciona de verdade num quadro ---")
    # Prova end-to-end do recorte, sem envolver a visao: gera um quadro, recorta
    # e confere que saiu imagem MENOR em altura e MAIOR em largura que a fatia.
    import subprocess
    import tempfile
    if not v.FFMPEG_CMD:
        conferir(False, "ffmpeg disponivel para o teste", "FFMPEG_CMD vazio")
        return
    pasta = tempfile.mkdtemp(prefix="faixa_")
    origem = os.path.join(pasta, "q.png")
    subprocess.run([v.FFMPEG_CMD, "-y", "-f", "lavfi", "-i",
                    "color=c=black:s=720x1280:d=1", "-frames:v", "1", origem],
                   capture_output=True, timeout=60, check=False)
    conferir(os.path.exists(origem), "quadro de teste 720x1280 criado")
    if not os.path.exists(origem):
        return
    recorte = v.recortar_faixa_do_rodape(origem)
    conferir(recorte != origem, "o recorte gerou arquivo proprio",
             os.path.basename(str(recorte)))
    if recorte != origem and os.path.exists(recorte):
        saida = subprocess.run(
            [v.FFMPEG_CMD.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "error",
             "-select_streams", "v:0", "-show_entries", "stream=width,height",
             "-of", "csv=s=x:p=0", recorte],
            capture_output=True, text=True, timeout=60, check=False).stdout.strip()
        conferir(bool(saida), "e o recorte e uma imagem legivel", saida)
        if "x" in saida:
            larg, alt = (int(x) for x in saida.split("x")[:2])
            conferir(larg == 720 * v.AMPLIACAO_DA_FAIXA,
                     f"largura ampliada {v.AMPLIACAO_DA_FAIXA}x", str(larg))
            conferir(alt < 1280,
                     "e a altura e so a faixa, nao a tela inteira", str(alt))


if __name__ == "__main__":
    print("=" * 74)
    print("  A visao recebe a faixa do rodape, ampliada")
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
