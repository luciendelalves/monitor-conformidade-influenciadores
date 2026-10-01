# -*- coding: utf-8 -*-
"""
Preenche a coluna Influenciador das linhas antigas da fila, usando o @ que o
programa já descobriu e registrou.

POR QUE (31/08/2026)

Desde 30/08 o @ é descoberto sozinho nos links do Instagram, então ninguém
digita mais, e a coluna Influenciador ficou vazia na maioria das linhas: 13 de
18 na conferência do auditor. Lida como se faltasse dado, quando estava tudo
certo.

O programa passou a gravar o @ de volta na planilha ao processar, mas isso vale
para as linhas NOVAS. As antigas continuariam vazias para sempre, e a
informação existe: está no registro em CSV, na coluna handle, ligada ao mesmo
endereço.

SÓ PREENCHE CÉLULA VAZIA. Nunca sobrescreve o que alguém escreveu à mão, mesmo
que o registro discorde: nesse caso o certo é uma pessoa olhar, não o programa
decidir.

Confere primeiro e só escreve com --aplicar.

Uso:
    py preencher_influenciador_na_fila.py            (só mostra o que faria)
    py preencher_influenciador_na_fila.py --aplicar  (escreve)
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

import fluxo_downloads as fluxo
import sheets_client


def main():
    aplicar = "--aplicar" in sys.argv

    planilha = fluxo._planilha_fila_id()
    if not planilha:
        print("Não achei o identificador da planilha da fila. Nada feito.")
        return

    # handle por endereço, do registro. O último vence, porque uma linha pode
    # ter sido reaberta e processada mais de uma vez.
    por_link = {}
    for l in fluxo.ler_log():
        handle = str(l.get("handle") or "").strip().lstrip("@")
        origem = str(l.get("origem") or "").strip()
        if handle and origem and str(l.get("status")) == "OK":
            por_link[origem] = handle

    fila = fluxo.ler_fila()
    a_preencher = []
    sem_registro = []
    for x in fila:
        if str(x["influenciador"]).strip():
            continue
        handle = por_link.get(str(x["link"]).strip())
        if handle:
            a_preencher.append((x["numero_linha"], handle, x["link"]))
        else:
            sem_registro.append((x["numero_linha"], x["link"], x["status"]))

    print(f"linhas na fila: {len(fila)}")
    print(f"vazias com @ no registro: {len(a_preencher)}")
    print(f"vazias SEM @ no registro: {len(sem_registro)}")
    print()

    if a_preencher:
        print("o que seria preenchido:")
        for numero, handle, link in a_preencher:
            print(f"   linha {numero:>3}  ->  {handle:<20} ({link[:44]})")
        print()

    if sem_registro:
        # Não é defeito: linha que nunca foi baixada com sucesso não tem @ para
        # recuperar, e é isso que se espera dela.
        print("ficam vazias, e está certo (nunca baixaram com sucesso):")
        for numero, link, status in sem_registro:
            print(f"   linha {numero:>3}  {link[:40]:<42} {str(status)[:30]}")
        print()

    if not a_preencher:
        print("Nada a preencher.")
        return

    if not aplicar:
        print("Nada foi alterado. Para valer, rode de novo com --aplicar")
        return

    sheets_client.escrever_lote(
        planilha, fluxo.ABA_FILA, fluxo.letra_da_coluna_fila("influenciador"),
        [(numero, handle) for numero, handle, _ in a_preencher])
    print(f"{len(a_preencher)} linha(s) preenchida(s).")


if __name__ == "__main__":
    main()
