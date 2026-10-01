# -*- coding: utf-8 -*-
"""
Limpa, na máquina NOVA, o estado que pertencia à máquina de origem.

PARA QUE SERVE

O projeto não tem repositório remoto: ele viaja por cópia de pasta. A cópia leva
junto arquivos que descrevem a OUTRA máquina, e cada um deles causa um problema
diferente e silencioso aqui. Rode este comando uma vez, depois de copiar a
pasta, e ele resolve os doze de uma vez:

    py preparar_copia.py

POR QUE ISTO EXISTE (07/09/2026)

O manual de instalação tinha uma tabela de doze linhas dizendo o que NÃO copiar,
e tabela de doze linhas em manual de instalação é tabela que se lê pela metade.
Pior: ela exigia que a pessoa apagasse arquivo a arquivo dentro de pastas que
ela não conhece, o que é justamente o tipo de instrução que se executa errado.

O QUE ELE NÃO TOCA, de propósito: identificador de planilha, credencial, cookie,
`conta_instagram.txt`, `netlex_contratos.csv` e o cache de perfis. Esses são os
arquivos que a máquina nova PRECISA receber. Um comando de limpeza que apagasse
um deles transformaria uma instalação pela metade numa instalação impossível.

E ELE PERGUNTA ANTES. Rodado por engano na máquina de origem, ele apagaria o
contador diário de chamadas ao Instagram, que é o freio contra bloqueio da
conta. Por isso não tem modo silencioso e não aceita ser rodado sem resposta.
"""
import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_TESTE = os.path.join(BASE, "teste_watch_folder")
BAIXADOR = os.path.join(BASE, "baixador_local")

# CADA LINHA TEM O MOTIVO ESCRITO. Sem o motivo, a próxima pessoa que mexer aqui
# não tem como decidir se um arquivo novo entra na lista ou não.
A_APAGAR = [
    (os.path.join(PASTA_TESTE, "estado_conta_instagram.json"),
     "freio do Instagram da outra máquina: contador do dia, pausa por bloqueio "
     "e a marca de qual conta usou o Instagram hoje. Mantido, ele recusa o "
     "primeiro download desta pessoa acusando a conta de outra"),
    (os.path.join(PASTA_TESTE, "cookies_instagram.txt.anterior"),
     "sessão antiga que nenhum módulo lê. Segredo sem uso é risco sem benefício"),
    (os.path.join(PASTA_TESTE, "log_fluxo_completo.csv"),
     "registro dos downloads da outra máquina. Mantido, a tela abre mostrando "
     "trabalho que nunca aconteceu aqui, e é dele que sai o diagnóstico de "
     "download quebrado"),
    (os.path.join(PASTA_TESTE, "versoes_dos_baixadores.json"),
     "nasce sozinho. Ele guarda quando cada versão foi vista NESTA máquina, "
     "então mantido ele congela a data da outra e o aviso de biblioteca velha "
     "passa a medir o tempo errado"),
    (os.path.join(PASTA_TESTE, "rebaixamentos_pedidos.json"),
     "pedidos pendentes consumidos no uso. É o único cuja permanência pode "
     "APAGAR UM ACHADO: um pedido velho suprime o aviso de peça reaproveitada"),
    (os.path.join(PASTA_TESTE, "fechamentos_ciclo.csv"),
     "conclusão de auditoria assinada por quem fechou na outra máquina. O "
     "histórico compartilhado é a planilha de fechamentos, não este arquivo"),
    (os.path.join(PASTA_TESTE, "fila_trabalho"),
     "fila e sinal de vida do trabalhador da outra máquina. Mantido, a tela "
     "pode considerar de pé um trabalhador que nunca subiu aqui"),
    (os.path.join(PASTA_TESTE, "downloads_simulado"),
     "vídeos e material de teste da outra máquina"),
    (os.path.join(PASTA_TESTE, "drive_simulado"),
     "material de teste da outra máquina"),
    (os.path.join(PASTA_TESTE, "envios_aguardando"),
     "arquivos que a outra máquina tinha na fila de envio à mão"),
    (os.path.join(BAIXADOR, "videos"),
     "vídeos baixados na outra máquina, e quase todo o peso da cópia"),
    (os.path.join(BAIXADOR, "_contagem_do_dia.json"),
     "contador de chamadas ao Instagram do baixador avulso daquela máquina. "
     "Mantido, esta máquina começa o dia com cota já gasta ou já liberada"),
]

# O QUE FICA, e é conferido: se um destes tiver sido apagado por engano, o
# comando avisa, porque a instalação vai falhar depois e sem dizer por quê.
PRECISA_FICAR = [
    ("monitoramento_teste_id.txt", "identificador da Monitoramento"),
    ("fila_downloads_id.txt", "identificador da fila"),
    ("cadastro_planilha_id.txt", "identificador do cadastro"),
    ("fechamentos_planilha_id.txt", "identificador dos fechamentos"),
    ("drive_teste_pasta_raiz_id.txt", "identificador da pasta do Drive"),
    ("conta_instagram.txt", "o @ da conta do Instagram desta pessoa"),
    ("netlex_contratos.csv", "registro de contratos do Netlex"),
    ("instagram_userids.json", "cache de perfis, que poupa a chamada limitada"),
]


def apagar(caminho):
    if os.path.isdir(caminho):
        shutil.rmtree(caminho)
    else:
        os.remove(caminho)


def main():
    print("=" * 74)
    print("  Preparar a cópia  |  Monitoramento de Influenciadores")
    print("=" * 74)
    print()
    print("Este comando apaga, DESTA pasta, o estado que descreve a máquina de")
    print("onde a cópia veio. Ele não toca em identificador, credencial, cookie")
    print("nem no cache de perfis.")
    print()

    presentes = [(c, m) for c, m in A_APAGAR if os.path.exists(c)]
    if not presentes:
        print("Nada a apagar: esta pasta já está limpa.")
    else:
        print(f"Vai apagar {len(presentes)} item(ns):")
        print()
        for caminho, motivo in presentes:
            print(f"  {os.path.relpath(caminho, BASE)}")
            print(f"      {motivo}")
        print()
        print("-" * 74)
        print("ATENÇÃO: rode isto na máquina NOVA, não na de origem. Na máquina")
        print("de origem você apagaria o freio diário do Instagram, que é a")
        print("proteção contra bloqueio da conta.")
        print("-" * 74)
        print()
        try:
            resposta = input("Esta é a máquina NOVA? Digite SIM para apagar: ")
        except EOFError:
            print()
            print("Sem resposta. Nada foi apagado.")
            return 1
        if resposta.strip().upper() != "SIM":
            print()
            print("Nada foi apagado.")
            return 1
        print()
        for caminho, _ in presentes:
            try:
                apagar(caminho)
                print(f"  apagado   {os.path.relpath(caminho, BASE)}")
            except OSError as e:
                print(f"  NÃO DEU   {os.path.relpath(caminho, BASE)}: {e}")

    print()
    print("--- o que precisa ter chegado nesta pasta ---")
    faltando = []
    for nome, para_que in PRECISA_FICAR:
        if os.path.exists(os.path.join(PASTA_TESTE, nome)):
            print(f"  [ ok ] {nome}")
        else:
            print(f"  [FALTA] {nome}  ({para_que})")
            faltando.append(nome)

    print()
    print("=" * 74)
    if faltando:
        print(f"  {len(faltando)} arquivo(s) faltando. Peça a quem administra o")
        print("  programa. Depois rode:  py verificar_ambiente.py")
    else:
        print("  Pronto. Agora rode:  py verificar_ambiente.py")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
