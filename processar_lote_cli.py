"""
DESATUALIZADO DESDE 28/08/2026. NÃO USE SEM ATUALIZAR ANTES.

Dois motivos:

1. Ele escreve nas colunas F, G e H da planilha ANTIGA de validação, que saiu
   do fluxo em 28/08/2026. A fonte única passou a ser a Monitoramento, no
   bloco de colunas W a AB. Rodar isto hoje escreve no lugar errado.
2. Desde 29/08/2026 quem executa o trabalho é o trabalhador (trabalhador.py),
   que é um só de propósito. Este arquivo é um segundo caminho para o mesmo
   trabalho: rodá-lo junto com o trabalhador faz duas análises disputarem o
   mesmo modelo de visão e duas gravações disputarem os mesmos arquivos de
   estado, que é exatamente o que a fila de trabalho existe para impedir.

Para rodar um lote sem abrir a tela, ponha as tarefas na fila e deixe o
trabalhador executar. Se este arquivo voltar a ser necessário, ele precisa ser
reescrito para enfileirar, não para processar por conta própria.

O texto abaixo descreve como ele funcionava antes.

---

Versão sem interface (headless) do "Processar próximo lote" do
app_validacao_influenciadores.py — mesma lógica exata (pipeline.processar_linha /
processar_fora_do_escopo, cache salvo a cada linha, escrita em F/G/H em lote),
só que rodável direto por linha de comando, sem precisar abrir o Streamlit e
ficar clicando "próxima linha" na tela.

Pensado pra rodar um lote específico de novas linhas com um prazo (ex: "preciso
que esteja pronto até tal hora") — para automaticamente e escreve o que já foi
feito na planilha se o ritmo real mostrar que não vai dar tempo de terminar
tudo antes do prazo, em vez de estourar o horário sem aviso.

Uso:
    py processar_lote_cli.py --excel-row-min 2355 --deadline "2026-08-17 18:30" --buffer-min 10
    py processar_lote_cli.py --excel-row-min 2355                 (sem prazo, roda tudo)
    py processar_lote_cli.py --limite 5                           (só um teste rápido de ritmo)
"""

import argparse
import os
import sys
import time
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import sheets_client
import pipeline_influenciadores as pipeline


def formatar_duracao(segundos):
    segundos = int(max(segundos, 0))
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h}h {m:02d}min"
    if m:
        return f"{m}min {s:02d}s"
    return f"{s}s"


def escrever_veredito_no_sheets(cache, linhas):
    """Mesma lógica de escrita do app (seção 'Escrever o veredito da IA na
    planilha'): expande cada resultado do cache pra todas as linhas atuais que
    compartilham o mesmo link, e só escreve o que realmente mudou."""
    link_para_linhas_atuais = {}
    for l in linhas:
        link_para_linhas_atuais.setdefault(l["link"], []).append(l)

    linhas_com_sugestao = [r for r in cache.values() if pipeline.formatar_para_planilha(r) is not None]
    alvos = [
        (linha_atual, r)
        for r in linhas_com_sugestao
        for linha_atual in link_para_linhas_atuais.get(r["link"], [])
    ]
    if not alvos:
        return 0

    excel_rows = [linha_atual["excel_row"] for linha_atual, _ in alvos]
    valores_atuais_g = sheets_client.ler_coluna(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, pipeline.COLUNA_IA, excel_rows)

    atualizacoes_g, atualizacoes_h, atualizacoes_audio = [], [], []
    for linha_atual, r in alvos:
        nova = pipeline.formatar_para_planilha(r)
        atual_g = valores_atuais_g.get(linha_atual["excel_row"])
        if atual_g == nova:
            continue
        outras_linhas = [
            l["excel_row"] for l in link_para_linhas_atuais.get(r["link"], [])
            if l["excel_row"] != linha_atual["excel_row"]
        ]
        nota_extra = "link duplicado com linha " + ", ".join(str(x) for x in outras_linhas) if outras_linhas else None
        atualizacoes_g.append((linha_atual["excel_row"], nova))
        atualizacoes_h.append((linha_atual["excel_row"], pipeline.formatar_video_problema(r, nota_extra=nota_extra)))
        atualizacoes_audio.append((linha_atual["excel_row"], pipeline.formatar_alerta_audio(r)))

    sheets_client.escrever_lote(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, pipeline.COLUNA_IA, atualizacoes_g)
    sheets_client.escrever_lote(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, pipeline.COLUNA_MOTIVO, atualizacoes_h)
    sheets_client.escrever_lote(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, pipeline.COLUNA_ALERTA_AUDIO, atualizacoes_audio)
    return len(atualizacoes_g)


def main():
    # Trava de segurança posta em 29/08/2026. Ver o aviso no topo do arquivo:
    # ele escreve na planilha antiga e concorre com o trabalhador. Não é um
    # aviso na tela porque aviso na tela se ignora com pressa; aqui ele
    # simplesmente não roda sem alguém dizer que sabe do problema.
    if "--sei-que-esta-desatualizado" not in sys.argv:
        print(__doc__.split("---")[0].strip())
        print()
        print("Não rodei nada. Para insistir mesmo assim, acrescente "
              "--sei-que-esta-desatualizado")
        return
    sys.argv = [a for a in sys.argv if a != "--sei-que-esta-desatualizado"]

    ap = argparse.ArgumentParser()
    ap.add_argument("--excel-row-min", type=int, default=None, help="Só processa linhas com excel_row maior que esse valor")
    ap.add_argument("--deadline", type=str, default=None, help="Formato 'YYYY-MM-DD HH:MM' — para automaticamente se o ritmo real indicar que não vai dar tempo")
    ap.add_argument("--buffer-min", type=int, default=10, help="Minutos de folga reservados antes do prazo pra escrita final na planilha")
    ap.add_argument("--limite", type=int, default=None, help="Processa no máximo N linhas (útil pra medir ritmo antes de rodar tudo)")
    args = ap.parse_args()

    deadline = datetime.strptime(args.deadline, "%Y-%m-%d %H:%M") if args.deadline else None

    linhas = pipeline.carregar_planilha()
    if args.excel_row_min is not None:
        linhas = [l for l in linhas if l["excel_row"] > args.excel_row_min]

    cache = pipeline.carregar_cache()
    automatizaveis = [l for l in linhas if l["tipo_link"] in ("DRIVE_FOLDER", "DRIVE_FILE")]
    fora_do_escopo = [l for l in linhas if l["tipo_link"] not in ("DRIVE_FOLDER", "DRIVE_FILE")]

    fora_pendente = [l for l in fora_do_escopo if l["link"] not in cache]
    for l in fora_pendente:
        cache[l["link"]] = pipeline.processar_fora_do_escopo(l)
    if fora_pendente:
        pipeline.salvar_cache(cache)
        print(f"{len(fora_pendente)} linha(s) fora do escopo marcada(s) instantaneamente.")

    pendentes = [l for l in automatizaveis if l["link"] not in cache]
    if args.limite:
        pendentes = pendentes[: args.limite]

    print(f"{len(pendentes)} linha(s) automatizável(is) pendente(s) a processar.")
    if deadline:
        print(f"Prazo: {deadline} (buffer de {args.buffer_min} min reservado pro final).")

    inicio = time.time()
    feito = 0
    parou_por_prazo = False

    for linha in pendentes:
        if deadline is not None and feito >= 3:
            decorrido = time.time() - inicio
            media = decorrido / feito
            restantes = len(pendentes) - feito
            previsto_fim = datetime.now().timestamp() + media * restantes + args.buffer_min * 60
            if previsto_fim > deadline.timestamp():
                parou_por_prazo = True
                break

        t0 = time.time()
        try:
            r = pipeline.processar_linha(linha)
        except Exception as e:
            r = {**linha, "classificacao": "Requer Verificação",
                 "motivo": f"Erro inesperado ao processar a linha: {e}", "evidencia": "",
                 "processado_em": pipeline.datetime.now().strftime("%Y-%m-%d %H:%M")}
        dt = time.time() - t0
        cache[linha["link"]] = r
        pipeline.salvar_cache(cache)
        feito += 1
        media_atual = (time.time() - inicio) / feito
        print(f"[{feito}/{len(pendentes)}] {linha['influenciador']} {linha['data']} -> {r.get('classificacao')} ({dt:.1f}s, média {media_atual:.1f}s/linha)")

    decorrido_total = time.time() - inicio
    print()
    print(f"{feito} linha(s) processada(s) em {formatar_duracao(decorrido_total)}.")
    if parou_por_prazo:
        restantes = len(pendentes) - feito
        media = decorrido_total / feito if feito else 0
        print(f"PAROU por causa do prazo — ainda restam {restantes} linha(s) (~{formatar_duracao(media * restantes)} a mais no ritmo atual).")

    n_escritas = escrever_veredito_no_sheets(cache, pipeline.carregar_planilha())
    print(f"{n_escritas} linha(s) escrita(s)/atualizada(s) na planilha (colunas F/G/H).")


if __name__ == "__main__":
    main()
