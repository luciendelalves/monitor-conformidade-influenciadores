# -*- coding: utf-8 -*-
"""
O teto de fim de semana vale só no fim de semana, e não mexe no de dia útil.

POR QUE ESTE TESTE EXISTE (12/09/2026)

O auditor levantou um caso que o teto único não cobria: no plantão de sábado e
domingo, UMA pessoa cobre sozinha, na própria conta, o que nos dias de semana
seis contas dividem entre si. Depois de mostrar o risco (o teto existe por
causa dos bloqueios de agosto, e ele é o freio contra insistência, não só
contra volume), o auditor decidiu por um teto maior, só para o fim de semana,
mantendo o freio contra insistência intacto. Ver `limite_diario_vigente` em
`fluxo_downloads.py`.

Este teste NÃO chama o Instagram e NÃO sobe teto nenhum de verdade. Simula o
dia da semana passando uma data explícita para `limite_diario_vigente`, e para
o teste de integração troca o relógio que `situacao_da_conta` enxerga, sempre
devolvendo o valor original no final.

    py testes\\teste_teto_fim_de_semana.py
"""
import datetime
import os
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


class _RelogioFixo:
    """Substitui `datetime.datetime` dentro do módulo do fluxo só pelo tempo
    do teste, para `situacao_da_conta` enxergar um dia da semana escolhido em
    vez do dia real da máquina que roda a bateria."""

    def __init__(self, quando):
        self._quando = quando

    def now(self):
        return self._quando

    def strptime(self, *a, **k):
        return datetime.datetime.strptime(*a, **k)


def rodar():
    import fluxo_downloads as fluxo

    SABADO = datetime.datetime(2026, 9, 12, 10, 0)   # 12/09/2026 é sábado
    DOMINGO = datetime.datetime(2026, 9, 13, 10, 0)
    SEGUNDA = datetime.datetime(2026, 9, 14, 10, 0)
    SEXTA = datetime.datetime(2026, 9, 18, 10, 0)

    conferir(SABADO.weekday() == 5, "a data escolhida para sábado é mesmo sábado")
    conferir(DOMINGO.weekday() == 6, "a data escolhida para domingo é mesmo domingo")
    conferir(SEGUNDA.weekday() == 0, "a data escolhida para segunda é mesmo segunda")
    conferir(SEXTA.weekday() == 4, "a data escolhida para sexta é mesmo sexta")

    teto_semana = fluxo.LIMITE_DIARIO_INSTAGRAM
    teto_fds = fluxo.LIMITE_DIARIO_INSTAGRAM_FIM_DE_SEMANA

    print(f"       teto de dia útil: {teto_semana}")
    print(f"       teto de fim de semana: {teto_fds}")
    print()

    print("--- 1. limite_diario_vigente muda só no fim de semana ---")
    conferir(fluxo.limite_diario_vigente(SEGUNDA) == teto_semana,
              "segunda usa o teto de sempre")
    conferir(fluxo.limite_diario_vigente(SEXTA) == teto_semana,
              "sexta usa o teto de sempre")
    conferir(fluxo.limite_diario_vigente(SABADO) == teto_fds,
              "sábado usa o teto de plantão")
    conferir(fluxo.limite_diario_vigente(DOMINGO) == teto_fds,
              "domingo usa o teto de plantão")
    conferir(teto_fds > teto_semana,
              "o teto de plantão é maior que o de dia útil, que é o pedido",
              f"{teto_fds} não é maior que {teto_semana}")

    print()
    print("--- 2. situacao_da_conta usa o teto do dia certo, de ponta a ponta ---")
    pasta = tempfile.mkdtemp(prefix="teto_fds_")
    fluxo.ARQUIVO_ESTADO_CONTA = os.path.join(pasta, "estado_conta_instagram.json")
    # DESLIGA O CONTADOR COMPARTILHADO (24/09/2026), pra este teste (que usa
    # _contar_uso_instagram/situacao_da_conta de verdade) não falar com a
    # planilha de fechamentos configurada nesta máquina. Vale para as duas
    # seções deste arquivo, é o mesmo módulo `fluxo` o tempo todo.
    fluxo._planilha_fechamentos_id = lambda: None
    conta_original = fluxo.USUARIO_DOS_COOKIES
    datetime_original = fluxo.datetime
    fluxo.USUARIO_DOS_COOKIES = "conta_plantao_teste"
    try:
        # Simula sábado: usa até o teto de DIA ÚTIL e confirma que ainda sobra,
        # porque no fim de semana o teto vigente é o maior.
        fluxo.datetime = _RelogioFixo(SABADO)
        for _ in range(teto_semana):
            fluxo._contar_uso_instagram()
        pode, motivo, usados, restantes = fluxo.situacao_da_conta()
        conferir(pode,
                  f"com {teto_semana} usados num sábado, ainda pode usar "
                  f"(teto vigente é {teto_fds})",
                  motivo[:90])
        conferir(restantes == teto_fds - teto_semana,
                  "e o restante bate com a diferença entre os dois tetos",
                  str(restantes))

        # Completa até o teto de fim de semana: virou aviso, não bloqueia mais
        # (17/09/2026, decisão do auditor: o número é recomendação, as outras
        # duas travas da função continuam de verdade).
        for _ in range(teto_fds - teto_semana):
            fluxo._contar_uso_instagram()
        pode2, motivo2, usados2, restantes2 = fluxo.situacao_da_conta()
        conferir(pode2,
                  f"com {teto_fds} usados no sábado, o teto recomendado não trava")
        conferir(restantes2 == 0, "o restante mostrado é zero", str(restantes2))
        conferir("teto recomendado" in motivo2.lower(),
                  "e o aviso deixa claro que é recomendação", motivo2[:90])

    finally:
        fluxo.USUARIO_DOS_COOKIES = conta_original
        fluxo.datetime = datetime_original

    print()
    print("--- 3. na segunda, o MESMO número de usos já chega no teto (que é menor) ---")
    # Conta e pasta novas: o contador zera por dia de propósito (é o comportamento
    # correto), então testar "o mesmo consumo visto em outro dia" exigiria burlar
    # esse reset. Em vez disso, prova o ponto direto: gasta teto_semana numa
    # segunda simulada do zero, e confirma que isso já é o suficiente para o
    # aviso aparecer (restantes == 0), o que no sábado (passo 2 acima) não
    # bastava. Desde 17/09/2026 o teto não bloqueia mais em nenhum dos dois
    # casos, só muda quando o aviso liga.
    pasta2 = tempfile.mkdtemp(prefix="teto_fds_segunda_")
    fluxo.ARQUIVO_ESTADO_CONTA = os.path.join(pasta2, "estado_conta_instagram.json")
    fluxo.USUARIO_DOS_COOKIES = "conta_plantao_teste_segunda"
    datetime_original = fluxo.datetime
    try:
        fluxo.datetime = _RelogioFixo(SEGUNDA)
        for _ in range(teto_semana):
            fluxo._contar_uso_instagram()
        pode3, _motivo3, usados3, restantes3 = fluxo.situacao_da_conta()
        conferir(pode3,
                  f"com {teto_semana} usados numa segunda, o teto recomendado "
                  f"não bloqueia",
                  f"usados={usados3}")
        conferir(restantes3 == 0,
                  "mas o restante mostrado já é zero (no sábado o mesmo número "
                  "ainda tinha folga)",
                  str(restantes3))
    finally:
        fluxo.USUARIO_DOS_COOKIES = conta_original
        fluxo.datetime = datetime_original


if __name__ == "__main__":
    print("=" * 74)
    print("  Teto de fim de semana")
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
