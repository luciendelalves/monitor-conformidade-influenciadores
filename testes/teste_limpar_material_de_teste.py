# -*- coding: utf-8 -*-
"""
Prova que a limpeza de material de teste alcança tudo o que precisa alcançar.

POR QUE ESTE TESTE EXISTE (01/09/2026)

Ele nasceu de um defeito que eu mesmo criei e não percebi. Quando os dois layouts
passaram a montar bet / ano / mês / @influenciador, a função de limpeza continuou
chamando `_pasta_do_influenciador(handle, None, None)`. Com o caminho novo isso
exige bet e data, que quem limpa não tem, então a função passou a responder
sempre "não tem pasta no Drive de teste" e NÃO APAGAVA NADA. A suíte inteira
passou, porque limpeza não tinha teste nenhum.

TRÊS COISAS QUE ESTE TESTE AMARRA, e cada uma foi um erro real:

1. UMA PASTA POR MÊS. O mesmo influenciador tem pasta em cada mês em que postou.
   @maumauzk tinha em "08. Agosto" e em "09. Setembro" no mesmo dia de teste,
   porque os posts eram de 31/08 e de 01/09. Limpar um mês só deixava metade do
   material, e quem refizesse o teste esbarrava na conferência de vídeo repetido
   sem entender por quê.

2. A FILA TEM QUE SER LIMPA. Quem limpa quer refazer o teste com os MESMOS
   links, e adicionar_na_fila recusa link que já está lá. Sem limpar a fila, a
   tela dizia "esse link já foi baixado" sobre material que não existe mais.

3. O QUE NÃO PODE SER APAGADO. A contagem de chamadas do Instagram do dia é a
   proteção contra conta marcada, e o número interno do perfil guardado é a
   chamada mais cara do programa. Limpar teste não pode custar nenhum dos dois.

Nada aqui fala com o Google: Drive, planilha e fila são dublês.

    py testes\teste_limpar_material_de_teste.py
"""
import inspect
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.append(os.path.join(BASE, "_drive_credenciais"))

falhas = []


def conferir(condicao, descricao, detalhe=""):
    if condicao:
        print(f"[  ok  ] {descricao}")
    else:
        print(f"[ FALHA] {descricao}   {detalhe}")
        falhas.append(descricao)


class DriveFalso:
    """Árvore de mentira, no formato do Drive de teste depois de 01/09/2026."""

    def __init__(self, caminhos):
        self.pastas = {}      # (id_pai, nome) -> id
        self.arquivos = {}    # id_pasta -> [nomes]
        self.lixeira = []
        self.proximo = 100
        for caminho, arquivos in caminhos.items():
            pai = "raiz"
            for nome in caminho:
                chave = (pai, nome)
                if chave not in self.pastas:
                    self.proximo += 1
                    self.pastas[chave] = f"id{self.proximo}"
                pai = self.pastas[chave]
            self.arquivos.setdefault(pai, []).extend(arquivos)

    def listar(self, id_pasta, so_pastas=False):
        if so_pastas:
            return [{"name": nome, "id": ident}
                    for (pai, nome), ident in self.pastas.items() if pai == id_pasta]
        return [{"name": nome, "id": f"arq:{id_pasta}:{nome}"}
                for nome in self.arquivos.get(id_pasta, [])]

    def lixo(self, ident):
        self.lixeira.append(ident)
        # Some da árvore, junto com o que estava dentro, como o Drive faz.
        nomes = [chave for chave, i in self.pastas.items() if i == ident]
        for chave in nomes:
            del self.pastas[chave]

    def caminho_de(self, ident):
        """Nome da pasta cujo id é esse, para conferir o que foi para a lixeira."""
        for (_pai, nome), i in self.pastas.items():
            if i == ident:
                return nome
        return ident


def rodar():
    import fluxo_downloads as fluxo
    import drive_client_upload

    print("--- 1. o defeito que este teste existe para pegar ---")
    # A limpeza NÃO pode montar o caminho, porque o caminho exige bet e data e
    # quem limpa não tem nenhuma das duas. Tem que PROCURAR.
    fonte = inspect.getsource(fluxo.remover_material_de_teste)
    conferir("pastas_de_influenciador_no_teste" in fonte,
             "a limpeza PROCURA a pasta, em vez de montar o caminho",
             "montar exige bet e data, que quem limpa não tem")
    conferir("_pasta_do_influenciador(handle, None, None" not in fonte,
             "e não usa mais a chamada que passou a falhar sempre")

    print()
    print("--- 2. acha a pasta em TODOS os meses ---")
    # O caso real: @maumauzk com post de 31/08 e de 01/09 no mesmo dia de teste.
    arvore = {
        ("03. LOTTU", "2026", "08. Agosto", "@maumauzk", "31/08", "reels"):
            ["@maumauzk Tela 1.mp4"],
        ("03. LOTTU", "2026", "09. Setembro", "@maumauzk", "01/09", "story"):
            ["@maumauzk Tela 1.mp4"],
        ("03. LOTTU", "2026", "09. Setembro", "@outrapessoa", "01/09", "story"):
            ["@outrapessoa Tela 1.mp4"],
    }
    drive = DriveFalso(arvore)

    listar_antes = drive_client_upload.listar_arquivos
    lixeira_antes = drive_client_upload.mandar_para_lixeira
    raiz_antes = fluxo._pasta_raiz_drive
    try:
        drive_client_upload.listar_arquivos = drive.listar
        drive_client_upload.mandar_para_lixeira = drive.lixo
        fluxo._pasta_raiz_drive = lambda: "raiz"

        achadas = fluxo.pastas_de_influenciador_no_teste("maumauzk")
        caminhos = sorted(c for c, _i in achadas)
        conferir(len(achadas) == 2,
                 "acha as DUAS pastas, uma por mês", str(caminhos))
        conferir(all("@maumauzk" in c for c in caminhos),
                 "e as duas são dele", str(caminhos))
        conferir(not any("@outrapessoa" in c for c in caminhos),
                 "e nenhuma é de outra pessoa", str(caminhos))

        print()
        print("--- 3. manda as duas para a lixeira, e poupa quem não é alvo ---")
        drive.lixeira.clear()
        fluxo.remover_material_de_teste(["maumauzk"], log_fn=lambda m: None,
                                        limpar_fila=False)
        conferir(len(drive.lixeira) == 2,
                 "duas pastas na lixeira, e não uma", str(len(drive.lixeira)))
        sobrou = fluxo.pastas_de_influenciador_no_teste("maumauzk")
        conferir(not sobrou, "não sobrou pasta dele", str(sobrou))
        conferir(bool(fluxo.pastas_de_influenciador_no_teste("outrapessoa")),
                 "e a pasta de quem não era alvo continua lá")
    finally:
        drive_client_upload.listar_arquivos = listar_antes
        drive_client_upload.mandar_para_lixeira = lixeira_antes
        fluxo._pasta_raiz_drive = raiz_antes

    print()
    print("--- 4. o número devolvido não pode MENTIR ---")
    # A versão anterior percorria dois níveis apagando arquivo por arquivo. Com a
    # árvore mais funda, os arquivos ficam três níveis abaixo, o laço não os
    # alcançava, e o resultado dizia "0 arquivos na lixeira" depois de remover
    # material de verdade. Aconteceu na limpeza real de 01/09/2026.
    conferir("itens_removidos" in fonte and "arquivos_removidos" not in fonte,
             "conta o que foi mandado para a lixeira, e não arquivo por arquivo",
             "contar arquivo em árvore funda devolve 0 e lê como nada removido")

    print()
    print("--- 5. a FILA é limpa, senão a limpeza não serve para nada ---")
    conferir("ler_fila()" in fonte and "ABA_FILA" in fonte,
             "a limpeza também apaga as linhas da fila de downloads",
             "sem isso, o mesmo link é recusado com \"já foi baixado\"")
    conferir("limpar_fila" in inspect.signature(
        fluxo.remover_material_de_teste).parameters,
             "e dá para desligar isso quando não se quer")

    print()
    print("--- 6. o que a limpeza NÃO PODE tocar ---")
    # Estas duas são as únicas coisas nesta área que causam dano de verdade se
    # zeradas, e nenhuma é vestígio de teste.
    conferir("_marcar_conta_do_dia" not in fonte
             and "situacao_da_conta" not in fonte
             and "CHAVE_MAQUINA" not in fonte,
             "não mexe na contagem de chamadas do Instagram do dia",
             "é a proteção que impede conta marcada")
    conferir("guardar_userid" not in fonte and "userid" not in fonte.lower(),
             "não apaga o número interno do perfil guardado",
             "redescobrir é a chamada mais cara e mais arriscada do programa")
    conferir("CACHE_PATH" not in fonte and "carregar_cache" not in fonte,
             "não mexe no cache de resultados da análise")

    print()
    print("--- 7. e nunca apaga de forma permanente ---")
    conferir("mandar_para_lixeira" in fonte and "excluir" not in fonte.lower(),
             "só manda para a lixeira, onde o Drive guarda 30 dias")


if __name__ == "__main__":
    print("=" * 74)
    print("  Limpeza de material de teste")
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
