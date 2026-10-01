# -*- coding: utf-8 -*-
"""
Testa a lógica pura de vigia_trabalhador.decidir_estado, sem laço, sem
Windows e sem esperar tempo nenhum. Criado em 24/09/2026, junto com a
ferramenta.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import vigia_trabalhador as vigia


def teste_primeira_leitura_nunca_avisa():
    # Antes de ver o trabalhador de pé pelo menos uma vez, "não está de pé"
    # significa "ainda não subiu", não "caiu". Não pode avisar aqui.
    visto, avisado, avisar = vigia.decidir_estado(
        visto_de_pe=False, de_pe=False, ja_avisado=False, sinal={})
    assert visto is False
    assert avisado is False
    assert avisar is False


def teste_queda_depois_de_ter_visto_de_pe_avisa():
    visto, avisado, avisar = vigia.decidir_estado(
        visto_de_pe=True, de_pe=False, ja_avisado=False,
        sinal={"atualizado_em": "2026-09-24 10:00:00"})
    assert avisar is True
    assert avisado is True


def teste_encerramento_limpo_nao_avisa():
    # trabalhador.main grava "encerrado": True antes de sair, seja por
    # pedido de parada, seja por qualquer saída que passe pelo finally.
    visto, avisado, avisar = vigia.decidir_estado(
        visto_de_pe=True, de_pe=False, ja_avisado=False,
        sinal={"atualizado_em": "2026-09-24 10:00:00", "encerrado": True})
    assert avisar is False


def teste_nao_repete_aviso_para_a_mesma_queda():
    visto, avisado, avisar = vigia.decidir_estado(
        visto_de_pe=True, de_pe=False, ja_avisado=True,
        sinal={"atualizado_em": "2026-09-24 10:00:00"})
    assert avisar is False, "já avisou desta queda, não repete a cada volta do laço"


def teste_voltar_de_pe_zera_o_aviso():
    visto, avisado, avisar = vigia.decidir_estado(
        visto_de_pe=True, de_pe=True, ja_avisado=True, sinal={})
    assert visto is True
    assert avisado is False, "voltando de pé, uma queda futura precisa poder avisar de novo"
    assert avisar is False


if __name__ == "__main__":
    teste_primeira_leitura_nunca_avisa()
    teste_queda_depois_de_ter_visto_de_pe_avisa()
    teste_encerramento_limpo_nao_avisa()
    teste_nao_repete_aviso_para_a_mesma_queda()
    teste_voltar_de_pe_zera_o_aviso()
    print("OK")
