"""
Backfill do alerta de fala problemática (checar_fala_problematica) pros posts
JÁ processados no cache — reaproveita o veredito visual existente (não refaz
OCR/visão), só baixa de novo os arquivos de vídeo, transcreve o áudio e checa
os padrões vedados (ilusão de controle, promessa de enriquecimento, sugestão
de repetibilidade). Escreve o resultado na coluna H (COLUNA_ALERTA_AUDIO) e
atualiza o campo "alerta_audio" de cada entrada do cache local.

Isolado por linha (like processar_linha): um erro numa linha não derruba o
resto do lote. Escreve na planilha em lotes de 20 pra não perder tudo se
travar no meio de uma rodada longa.

Rodar: py backfill_alerta_audio.py
"""

import os
import shutil
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "_drive_credenciais"))
import drive_client
import pipeline_influenciadores as pipeline
import sheets_client
import validar_avisos_portaria136 as motor

MOTIVOS_SEM_ARQUIVO_PRA_BAIXAR = (
    "Falha ao acessar", "Pasta sem arquivo", "fora do escopo automático",
)

TEMP_BASE = os.path.join(pipeline.BASE_DIR, "backfill_audio_tmp")
os.makedirs(TEMP_BASE, exist_ok=True)


def main():
    linhas = pipeline.carregar_planilha()
    cache = pipeline.carregar_cache()

    por_link_linhas = {}
    for l in linhas:
        por_link_linhas.setdefault(l["link"], []).append(l)

    alvos = []
    for link, r in cache.items():
        motivo = r.get("motivo", "")
        if any(m in motivo for m in MOTIVOS_SEM_ARQUIVO_PRA_BAIXAR):
            continue
        if link not in por_link_linhas:
            continue
        alvos.append((link, r))

    print(f"{len(alvos)} post(s) elegíveis pro backfill de áudio.", flush=True)

    atualizacoes_pendentes = {}
    processados = 0
    com_alerta = 0
    erros = 0

    for i, (link, r) in enumerate(alvos, start=1):
        l_info = por_link_linhas[link]
        linha0 = l_info[0]
        row_dir = os.path.join(TEMP_BASE, f"linha_{linha0['excel_row']}")
        os.makedirs(row_dir, exist_ok=True)

        try:
            arquivos_baixados = []
            if linha0["tipo_link"] == "DRIVE_FOLDER":
                itens = drive_client.list_folder(linha0["drive_id"])
                midia = [a for a in itens if pipeline.is_midia(a.get("mimeType", ""))]
                for a in midia:
                    nome = pipeline.nome_com_extensao(a["name"], a.get("mimeType", ""))
                    dest = os.path.join(row_dir, nome)
                    drive_client.download_file(a["id"], dest)
                    arquivos_baixados.append(dest)
            elif linha0["tipo_link"] == "DRIVE_FILE":
                meta = drive_client.get_metadata(linha0["drive_id"])
                nome = pipeline.nome_com_extensao(meta.get("name", linha0["drive_id"]), meta.get("mimeType", ""))
                dest = os.path.join(row_dir, nome)
                drive_client.download_file(linha0["drive_id"], dest)
                arquivos_baixados.append(dest)

            alertas = []
            for path in arquivos_baixados:
                ext = os.path.splitext(path)[1].lower()
                if ext not in motor.VIDEO_EXTS:
                    continue
                transcricao = motor.analisar_audio(path, row_dir)
                categorias = motor.checar_fala_problematica(transcricao)
                for cat in categorias:
                    alertas.append({
                        "arquivo": os.path.basename(path),
                        "categoria": cat,
                        "rotulo": motor.ROTULO_ALERTA_AUDIO[cat],
                    })

            r["alerta_audio"] = alertas
            pipeline.salvar_cache(cache)

            texto_alerta = pipeline.formatar_alerta_audio(r)
            for l in l_info:
                atualizacoes_pendentes[l["excel_row"]] = texto_alerta

            processados += 1
            if alertas:
                com_alerta += 1
                print(f"[{i}/{len(alvos)}] linha(s) {[l['excel_row'] for l in l_info]}: "
                      f"ALERTA -> {[a['categoria'] for a in alertas]}", flush=True)
            else:
                print(f"[{i}/{len(alvos)}] linha(s) {[l['excel_row'] for l in l_info]}: sem alerta", flush=True)

        except Exception as e:
            erros += 1
            print(f"[{i}/{len(alvos)}] linha {linha0['excel_row']}: ERRO {e}", flush=True)
        finally:
            shutil.rmtree(row_dir, ignore_errors=True)

        if len(atualizacoes_pendentes) >= 20:
            lote = list(atualizacoes_pendentes.items())
            sheets_client.escrever_lote(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, pipeline.COLUNA_ALERTA_AUDIO, lote)
            print(f"  -> escreveu {len(lote)} linha(s) na coluna H.", flush=True)
            atualizacoes_pendentes = {}

    if atualizacoes_pendentes:
        lote = list(atualizacoes_pendentes.items())
        sheets_client.escrever_lote(pipeline.PLANILHA_ID, pipeline.NOME_ABA_SHEETS, pipeline.COLUNA_ALERTA_AUDIO, lote)
        print(f"  -> escreveu {len(lote)} linha(s) na coluna H (lote final).", flush=True)

    print(f"\nconcluído: {processados} processado(s), {com_alerta} com alerta, {erros} erro(s).", flush=True)


if __name__ == "__main__":
    main()
