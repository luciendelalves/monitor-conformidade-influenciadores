# Calendário Geral de Divulgações: plano de implementação

> **Para quem for executar:** as etapas usam caixa de marcar (`- [ ]`) para
> acompanhamento. Cada tarefa termina com a bateria completa passando.

**Objetivo:** o programa passa a preencher `Jogo`, `Status`, `Horário` e
`Monitorado por` no CALENDÁRIO GERAL DIVULGAÇÕES do Marketing, a partir do que
já acontece no download, e ganha uma tela para marcar quem não postou.

**Arquitetura:** um módulo novo (`calendario_divulgacoes.py`) concentra tudo:
normalização de handle e marca, escolha da aba pelo mês, casamento da linha e
escrita. O fluxo de download chama esse módulo depois de registrar na
Monitoramento, e a falha dele nunca derruba o download. A escolha entre
planilha real e cópia de teste reaproveita o mecanismo que já existe.

**Tecnologia:** Python 3.14, Google Sheets API pelo `sheets_client` do projeto,
Streamlit nas telas.

**Desenho:** [DESENHO_CALENDARIO.md](DESENHO_CALENDARIO.md). O plano argumenta
a partir dele; quem executa lê os dois.

## Restrições que valem para TODAS as tarefas

- **Este repositório não usa git.** Onde um plano normal mandaria fazer commit,
  aqui a etapa é rodar a bateria inteira e ela precisa terminar com zero falhas:
  `for %f in (testes\*.py) do py "%f"`.
- **Rodar teste isolado:** `py testes\nome_do_teste.py`. Com acento na saída,
  prefixar `PYTHONIOENCODING=utf-8`.
- **Encerrar o trabalhador antes de mexer em qualquer módulo**, com
  `fila_trabalho.pedir_parada()`, e subir de novo depois. Ele guarda o código em
  memória.
- **Sem travessão** em texto que vá para tela, planilha ou documento. Vírgula ou
  ponto.
- **Sem jargão em texto visível.** Nada de "parser", "cache", "fallback".
- **Comentário no código explica o POR QUÊ e a data.**
- **Nunca comparar data como texto.** Usar `data_de_planilha.py`, que é o único
  lugar onde essa regra mora.
- **Escrita fora do modo real autorizado vai sempre para a cópia de teste.**
- **Nunca criar os arquivos de `marketing_producao\`** sem confirmação direta de
  quem administra a planilha do Marketing.
- **Teste não pode gastar chamada ao Instagram.** A bateria hoje consome zero, e
  precisa continuar assim.

---

## Arquivos

| arquivo | responsabilidade |
|---|---|
| `calendario_divulgacoes.py` (**novo**) | tudo do Calendário: normalizar, achar a aba, achar a linha, ler e escrever |
| `fluxo_downloads.py` (modificar) | devolver a hora do post; carregar `jogo` na fila; chamar o Calendário depois do download |
| `pages/1_Downloads_e_Organizacao.py` (modificar) | campo `Jogo` no formulário; seção "não postou" |
| `testes/teste_hora_do_post.py` (**novo**) | a hora deixa de ser descartada, e vem em horário de Brasília |
| `testes/teste_calendario_casamento.py` (**novo**) | normalização, aba pelo mês, escolha da linha |
| `testes/teste_calendario_escrita.py` (**novo**) | não sobrescreve, não cria linha, teste x real |
| `testes/teste_campo_jogo_na_fila.py` (**novo**) | o campo novo viaja na fila sem deslocar coluna antiga |
| `testes/teste_calendario_no_fluxo.py` (**novo**) | o download escreve no Calendário, e a falha dele não derruba o download |
| `testes/teste_nao_postou.py` (**novo**) | marca "Não Postada" sem gastar chamada do Instagram |

---

### Tarefa 1: a hora do post deixa de ser jogada fora

**Arquivos:**
- Modificar: `fluxo_downloads.py` (`baixar_story_instaloader`, `_baixar_post_instaloader`, `baixar_video`, e os dois pontos que chamam `baixar_video`)
- Criar: `testes/teste_hora_do_post.py`
- Modificar: `testes/teste_rodadas_seguidas.py` e `testes/teste_link_que_chega_no_meio.py` (os dublês de `baixar_video`)

**Interfaces:**
- Produz: `baixar_video(link, pasta_destino, link_post_do_perfil=None)` passa a
  devolver **quatro** valores: `(caminho, data_video, handle, hora_post)`.
  `data_video` continua sendo `datetime.date`, como hoje. `hora_post` é
  `datetime.datetime` no horário de Brasília, ou `None` quando a origem não
  informou hora.
- Produz: `hora_de_brasilia(quando_utc)` -> `datetime.datetime | None`.

**Por que `data_video` NÃO vira datetime:** `inferir_ciclo` compara
`dmin <= data_video <= dmax` contra objetos `date` vindos da Monitoramento.
Comparar `datetime` com `date` levanta `TypeError` em Python. Então a data
continua data, e a hora viaja separada.

- [ ] **Etapa 1: escrever o teste que falha**

Criar `testes/teste_hora_do_post.py`:

```python
# -*- coding: utf-8 -*-
"""
Prova que a hora da postagem para de ser descartada, e chega em horário de
Brasília.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário do Marketing tem coluna de Horário, e o auditor perguntou se dava
para estimar. Não precisa estimar: o Instagram já manda a hora exata, e o
programa jogava fora, ficando só com a data, em três lugares
(`item.date_utc.date()`, `post.date_utc.date()` e
`datetime.fromtimestamp(...).date()`).

O CUIDADO QUE ESTE TESTE PROTEGE: `date_utc` é UTC. Escrever direto na planilha
sairia 3 horas adiantado, e ninguém percebe olhando a tela, porque 22:17 e 19:17
são igualmente plausíveis.

    py testes\\teste_hora_do_post.py
"""
import datetime
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


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. UTC vira horário de Brasília ---")
    # 02/08/2026 às 01:17 UTC é 01/08/2026 às 22:17 em Brasília. O dia MUDA,
    # e é por isso que a conversão não é enfeite.
    utc = datetime.datetime(2026, 8, 2, 1, 17, tzinfo=datetime.timezone.utc)
    aqui = fluxo.hora_de_brasilia(utc)
    conferir(aqui is not None, "converte em vez de devolver nada")
    conferir(aqui.hour == 22 and aqui.minute == 17,
             "a hora bate com o horário de Brasília", str(aqui))
    conferir(aqui.day == 1,
             "e o DIA volta para o anterior, quando é o caso", str(aqui))

    print()
    print("--- 2. sem hora, devolve None em vez de inventar ---")
    conferir(fluxo.hora_de_brasilia(None) is None,
             "None entra, None sai",
             "inventar meia-noite faria a planilha afirmar algo que ninguém mediu")

    print()
    print("--- 3. hora que já vem sem fuso é tratada como UTC ---")
    # O instaloader entrega `date_utc` sem informação de fuso colada. Tratar
    # como horário local faria a conversão acontecer duas vezes, ou nenhuma.
    ingenua = datetime.datetime(2026, 8, 2, 1, 17)
    conferir(fluxo.hora_de_brasilia(ingenua).hour == 22,
             "sem fuso declarado, assume UTC", str(fluxo.hora_de_brasilia(ingenua)))

    print()
    print("--- 4. baixar_video devolve QUATRO valores ---")
    import inspect
    fonte = inspect.getsource(fluxo.baixar_video)
    conferir("hora_post" in fonte,
             "o caminho de download carrega a hora",
             "sem isso a coluna Horário do Calendário fica vazia para sempre")

    print()
    print("--- 5. os três lugares que cortavam a hora foram corrigidos ---")
    inteiro = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir("item.date_utc.date(), handle" not in inteiro,
             "o caminho de story não corta mais a hora ali")
    conferir(inteiro.count("hora_de_brasilia(") >= 3,
             "e os três caminhos passam pela conversão",
             f"achei {inteiro.count('hora_de_brasilia(')} usos")


if __name__ == "__main__":
    print("=" * 74)
    print("  A hora da postagem")
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
```

- [ ] **Etapa 2: rodar e confirmar que falha**

Rodar: `py testes\teste_hora_do_post.py`
Esperado: FALHA logo na primeira seção, com `AttributeError` ou
`module 'fluxo_downloads' has no attribute 'hora_de_brasilia'`.

- [ ] **Etapa 3: escrever a conversão**

Em `fluxo_downloads.py`, perto das outras funções de data:

```python
# FUSO DE BRASÍLIA ESCRITO À MÃO, E NÃO VINDO DE BIBLIOTECA (11/09/2026).
#
# O Brasil não tem horário de verão desde 2019, então o deslocamento é fixo em
# -3. Usar zoneinfo traria dependência de base de fusos do sistema, que é uma
# coisa a mais para faltar numa máquina nova, para resolver um caso que não
# existe mais. Se o horário de verão voltar, este é o lugar de mexer.
FUSO_DE_BRASILIA = timezone(timedelta(hours=-3))


def hora_de_brasilia(quando):
    """A hora do post no horário de Brasília, ou None se não veio hora.

    O Instagram entrega em UTC (`date_utc` do instaloader, `timestamp` do
    yt-dlp). Escrever isso direto na planilha do Marketing sairia 3 horas
    adiantado, e é erro que ninguém percebe olhando: 22:17 e 19:17 são
    igualmente plausíveis para um story.

    Hora sem fuso declarado é tratada como UTC, que é o que o instaloader
    entrega em `date_utc`. Supor o contrário converteria duas vezes."""
    if quando is None:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return quando.astimezone(FUSO_DE_BRASILIA)
```

Conferir que `timezone` e `timedelta` estão no import de `datetime` no topo do
arquivo; se não estiverem, acrescentar.

- [ ] **Etapa 4: fazer os três caminhos devolverem a hora**

Em `baixar_story_instaloader`, trocar o `return` final:

```python
    # ANTES: return os.path.join(...), item.date_utc.date(), handle
    # A hora vinha junto e era cortada aqui. Ver hora_de_brasilia.
    quando = hora_de_brasilia(getattr(item, "date_utc", None))
    return (os.path.join(pasta_destino, candidatos[0]),
            quando.date() if quando else None, handle, quando)
```

Em `_baixar_post_instaloader`, onde hoje está
`data = post.date_utc.date() if getattr(post, "date_utc", None) else None`:

```python
    quando = hora_de_brasilia(getattr(post, "date_utc", None))
    data = quando.date() if quando else None
```

e incluir `quando` no retorno dessa função, na mesma posição em que
`baixar_story_instaloader` passou a incluir.

No caminho do yt-dlp, onde hoje está
`data = datetime.fromtimestamp(int(escolhida["timestamp"])).date()`:

```python
            # fromtimestamp SEM fuso usa o fuso da máquina, que muda de
            # computador para computador. Com timezone.utc o resultado é o
            # mesmo em qualquer máquina, e a conversão para Brasília é
            # explícita logo abaixo.
            quando = hora_de_brasilia(
                datetime.fromtimestamp(int(escolhida["timestamp"]),
                                       tz=timezone.utc))
            data = quando.date()
```

O caminho de `upload_date` (formato `%Y%m%d`) não tem hora nenhuma: ali
`quando` fica `None`, e isso é honesto.

- [ ] **Etapa 5: `baixar_video` devolve quatro valores**

Cada `return` de `baixar_video` passa a devolver
`(caminho, data_video, handle, hora_post)`. Onde a origem não informa hora,
`hora_post` é `None`.

- [ ] **Etapa 6: atualizar os dois pontos que chamam**

Em `fluxo_downloads.py`, linha ~4728:

```python
                    baixado, data_video, handle_do_video, hora_post = baixar_video(
                        item["link"], tmp, post_do_perfil)
```

Fazer o mesmo no outro ponto (perto da linha 5300). `hora_post` ainda não é
usado nesta tarefa: entra na Tarefa 5.

- [ ] **Etapa 7: atualizar os dublês dos testes**

Em `testes/teste_rodadas_seguidas.py` e `testes/teste_link_que_chega_no_meio.py`,
o dublê `baixar_video` devolve três valores. Passar a devolver quatro:

```python
        import datetime
        return "arquivo.mp4", datetime.date(2026, 9, 1), "exemplo", None
```

- [ ] **Etapa 8: rodar o teste novo e a bateria**

Rodar: `py testes\teste_hora_do_post.py` (esperado: PASSOU)
Rodar: `for %f in (testes\*.py) do py "%f"` (esperado: zero falhas)

---

### Tarefa 2: o módulo do Calendário, só com a parte que não fala com ninguém

**Arquivos:**
- Criar: `calendario_divulgacoes.py`
- Criar: `testes/teste_calendario_casamento.py`

**Interfaces:**
- Produz: `normalizar_handle(bruto) -> str` (sem `@`, sem espaço, minúsculo)
- Produz: `normalizar_marca(bruto) -> str` (sem espaço nenhum, maiúsculo)
- Produz: `aba_do_mes(data) -> str` (ex: `date(2026, 9, 11)` -> `"SET.26"`)
- Produz: `COL` (dict com os índices das colunas A a I) e `PRIMEIRA_LINHA = 3`
- Produz: `achar_linha(linhas, handle, marca, data) -> (numero_da_linha, motivo)`,
  onde `linhas` é a lista de listas vinda do Sheets começando na linha 3,
  `numero_da_linha` é o número real na planilha ou `None`, e `motivo` é `""`
  quando achou, ou um texto explicando quando não achou.
- Produz: `apelidos_conhecidos(linhas) -> set[str]` (os nomes já usados na
  coluna `Monitorado por`, em minúsculo)

- [ ] **Etapa 1: escrever o teste que falha**

Criar `testes/teste_calendario_casamento.py`:

```python
# -*- coding: utf-8 -*-
"""
Prova como o programa acha a linha certa no Calendário do Marketing.

POR QUE ESTE TESTE EXISTE (11/09/2026)

Medido nas abas AGO.26 e SET.26, 1.984 linhas reais, antes de desenhar:

  - o handle é escrito de qualquer jeito: com e sem @, com espaço no fim
    ("nathanqueiroz  "), em maiúscula ("@Giroquue")
  - a marca muda de aba para aba: agosto escreve EDSCAP, setembro EDS CAP
  - a chave (handle, marca, data) REPETE em cerca de 3% das linhas, sempre 2
    vezes, e é justamente quem posta dois stories no mesmo dia
    (andersonneiff, eduardagutierrez, weslleyof_)

A REGRA QUE SAI DISSO: entre as linhas que casam, escrever na primeira que
ainda está com Status vazio. Assim o primeiro story cai na primeira linha e o
segundo na segunda, sem o programa precisar saber qual é qual.

Nada aqui fala com o Google: são listas de mentira, no mesmo formato que a API
devolve.

    py testes\\teste_calendario_casamento.py
"""
import datetime
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


def linha(handle, marca, data, status="", jogo="", horario="", monitorado=""):
    """Uma linha no formato que o Sheets devolve: lista de textos, A a I."""
    return [handle, marca, "Responsável", jogo, status, data, horario,
            monitorado, ""]


def rodar():
    import calendario_divulgacoes as cal

    print("--- 1. normalização do handle, com os casos reais da planilha ---")
    for bruto in ("@Giroquue", "giroquue", "  giroquue  ", "@giroquue"):
        conferir(cal.normalizar_handle(bruto) == "giroquue",
                 f"{bruto!r} vira 'giroquue'", cal.normalizar_handle(bruto))
    conferir(cal.normalizar_handle("nathanqueiroz  ") == "nathanqueiroz",
             "espaço no fim não atrapalha")

    print()
    print("--- 2. normalização da marca resolve EDSCAP x EDS CAP ---")
    conferir(cal.normalizar_marca("EDS CAP") == cal.normalizar_marca("EDSCAP"),
             "as duas grafias viram a mesma coisa",
             f"{cal.normalizar_marca('EDS CAP')} x {cal.normalizar_marca('EDSCAP')}")
    conferir(cal.normalizar_marca(" lottu ") == "LOTTU", "e a caixa não importa")

    print()
    print("--- 3. a aba sai do mês da postagem ---")
    conferir(cal.aba_do_mes(datetime.date(2026, 9, 11)) == "SET.26",
             "setembro de 2026 é SET.26", cal.aba_do_mes(datetime.date(2026, 9, 11)))
    conferir(cal.aba_do_mes(datetime.date(2026, 8, 1)) == "AGO.26",
             "agosto de 2026 é AGO.26", cal.aba_do_mes(datetime.date(2026, 8, 1)))
    conferir(cal.aba_do_mes(datetime.date(2025, 12, 31)) == "DEZ.25",
             "e dezembro de 2025 é DEZ.25", cal.aba_do_mes(datetime.date(2025, 12, 31)))

    print()
    print("--- 4. acha a linha, com o handle escrito diferente ---")
    linhas = [
        linha("@Giroquue", "EDS CAP", "11/09/2026"),
        linha("outrapessoa", "LOTTU", "11/09/2026"),
    ]
    n, motivo = cal.achar_linha(linhas, "giroquue", "EDSCAP",
                                datetime.date(2026, 9, 11))
    conferir(n == 3, "achou na primeira linha de dados, que é a 3", f"{n} {motivo}")

    print()
    print("--- 5. duas linhas iguais: preenche na ordem ---")
    # O caso do auditor: dois stories do mesmo influenciador, mesma marca, mesmo
    # dia. A planilha tem duas linhas, e elas são preenchidas em sequência.
    linhas = [
        linha("andersonneiff", "LOTTU", "11/09/2026", status="Publicada"),
        linha("andersonneiff", "LOTTU", "11/09/2026"),
    ]
    n, motivo = cal.achar_linha(linhas, "andersonneiff", "LOTTU",
                                datetime.date(2026, 9, 11))
    conferir(n == 4,
             "pula a que já tem Status e vai para a segunda", f"{n} {motivo}")

    print()
    print("--- 6. todas preenchidas: avisa, e não sobrescreve ---")
    linhas = [
        linha("andersonneiff", "LOTTU", "11/09/2026", status="Publicada"),
        linha("andersonneiff", "LOTTU", "11/09/2026", status="Não Postada"),
    ]
    n, motivo = cal.achar_linha(linhas, "andersonneiff", "LOTTU",
                                datetime.date(2026, 9, 11))
    conferir(n is None, "não devolve linha", str(n))
    conferir("já" in motivo.lower() or "preenchid" in motivo.lower(),
             "e o motivo diz que as linhas já estão preenchidas", motivo)

    print()
    print("--- 7. nenhuma linha casa: avisa o que procurou ---")
    linhas = [linha("outrapessoa", "LOTTU", "11/09/2026")]
    n, motivo = cal.achar_linha(linhas, "giroquue", "LOTTU",
                                datetime.date(2026, 9, 11))
    conferir(n is None, "não inventa linha", str(n))
    conferir("giroquue" in motivo, "e diz de quem estava procurando", motivo)

    print()
    print("--- 8. a data é comparada como DATA, não como texto ---")
    # 06/09/2026 gravado no Sheets volta como "06/09/26". Comparar texto faria
    # o casamento falhar em silêncio. Ver data_de_planilha.py.
    linhas = [linha("giroquue", "LOTTU", "06/09/26")]
    n, _ = cal.achar_linha(linhas, "giroquue", "LOTTU",
                           datetime.date(2026, 9, 6))
    conferir(n == 3, "ano com dois dígitos casa com a mesma data", str(n))

    print()
    print("--- 9. os apelidos saem da própria planilha ---")
    linhas = [
        linha("a", "LOTTU", "11/09/2026", monitorado="Responsável F"),
        linha("b", "LOTTU", "11/09/2026", monitorado="Responsável G"),
        linha("c", "LOTTU", "11/09/2026", monitorado=""),
    ]
    apelidos = cal.apelidos_conhecidos(linhas)
    conferir("responsável f" in apelidos and "responsável g" in apelidos,
             "lê o vocabulário de quem monitora da coluna deles",
             str(sorted(apelidos)))
    conferir("" not in apelidos, "e vazio não vira apelido")


if __name__ == "__main__":
    print("=" * 74)
    print("  Achar a linha certa no Calendário")
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
```

- [ ] **Etapa 2: rodar e confirmar que falha**

Rodar: `py testes\teste_calendario_casamento.py`
Esperado: `ModuleNotFoundError: No module named 'calendario_divulgacoes'`.

- [ ] **Etapa 3: escrever o módulo, só a parte pura**

Criar `calendario_divulgacoes.py`:

```python
# -*- coding: utf-8 -*-
"""
O Calendário Geral de Divulgações do Marketing.

É uma planilha SEPARADA da Monitoramento, com uma linha por post planejado. O
Marketing preenche à mão influenciador, marca, responsável e data; o programa
preenche o que só existe depois do vídeo: Jogo, Status, Horário e Monitorado
por. Ver DESENHO_CALENDARIO.md para o que foi medido antes de desenhar.

A ESTRUTURA, medida em 11/09/2026 nas abas AGO.26 e SET.26:

  - uma aba por mês, nomeada MMM.AA (DEZ.25 até DEZ.26)
  - cabeçalho na linha 2, dados a partir da linha 3, linha 1 vazia
  - colunas A a I: Influenciador, Marca, Responsável, Jogo, Status,
    Data da postagem, Horário, "Monitorado por:", "Coluna 1"
"""
import os

import data_de_planilha

# A linha 1 é vazia e a 2 é o cabeçalho. Dado começa na 3.
PRIMEIRA_LINHA = 3

COL = {"influenciador": 0, "marca": 1, "responsavel": 2, "jogo": 3,
       "status": 4, "data": 5, "horario": 6, "monitorado": 7}

# Os dois únicos valores que existem na coluna Status da planilha deles, medido
# em 1.984 linhas. "Apagada" NÃO existe lá, e criar vocabulário novo na planilha
# de outra área é decisão deles: decidido com o auditor em 11/09/2026.
STATUS_PUBLICADA = "Publicada"
STATUS_NAO_POSTADA = "Não Postada"

# Como o Marketing escreve os meses nas abas.
MESES_DA_ABA = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
                "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


def normalizar_handle(bruto):
    """O @ como chave de comparação.

    Na planilha deles o mesmo influenciador aparece como "@Giroquue",
    "giroquue" e "nathanqueiroz  ". Sem isto, o casamento falharia em silêncio,
    que é o pior resultado possível aqui: a linha fica vazia e ninguém sabe
    por quê."""
    return str(bruto or "").strip().lstrip("@").strip().lower()


def normalizar_marca(bruto):
    """A marca como chave de comparação.

    Agosto escreve EDSCAP e setembro escreve EDS CAP, na mesma planilha. Tirar
    todo espaço resolve os dois, e a caixa alta deixa a comparação estável."""
    return "".join(str(bruto or "").split()).upper()


def aba_do_mes(data):
    """O nome da aba a partir da data do post: 11/09/2026 -> 'SET.26'."""
    if data is None:
        return None
    return f"{MESES_DA_ABA[data.month - 1]}.{data.year % 100:02d}"


def _campo(linha, nome):
    indice = COL[nome]
    return str(linha[indice]).strip() if len(linha) > indice else ""


def achar_linha(linhas, handle, marca, data):
    """Em qual linha da planilha escrever, ou por que não dá.

    `linhas` são os valores devolvidos pelo Sheets a partir da PRIMEIRA_LINHA.
    Devolve (numero_da_linha_na_planilha, motivo). Com linha achada, o motivo é
    vazio.

    A REGRA DA PRIMEIRA VAZIA (11/09/2026): a chave influenciador + marca +
    data repete em cerca de 3% das linhas, sempre duas vezes, e é quem posta
    dois stories no mesmo dia. Escrever sempre na primeira que ainda está com
    Status vazio faz a primeira entrega cair na primeira linha e a segunda na
    segunda, sem o programa precisar saber qual story é qual."""
    procurado = (normalizar_handle(handle), normalizar_marca(marca))
    casaram = []
    for posicao, linha in enumerate(linhas):
        chave = (normalizar_handle(_campo(linha, "influenciador")),
                 normalizar_marca(_campo(linha, "marca")))
        if chave != procurado:
            continue
        # DATA COMPARADA COMO DATA, NUNCA COMO TEXTO. "06/09/2026" gravado no
        # Sheets volta "06/09/26", e comparar texto falharia sem dar erro.
        if not data_de_planilha.mesmo_dia(_campo(linha, "data"), data):
            continue
        casaram.append((PRIMEIRA_LINHA + posicao, linha))

    if not casaram:
        return None, (f"Não achei linha no Calendário para @{handle}, "
                      f"{marca}, {data:%d/%m/%Y}.")
    for numero, linha in casaram:
        if not _campo(linha, "status"):
            return numero, ""
    return None, (f"As {len(casaram)} linha(s) de @{handle}, {marca}, "
                  f"{data:%d/%m/%Y} já estão preenchidas. Não sobrescrevi.")


def apelidos_conhecidos(linhas):
    """Os nomes já usados na coluna 'Monitorado por', em minúsculo.

    A planilha deles é a fonte do vocabulário, como já é feito com as listas de
    seleção da Monitoramento. Serve para o programa não escrever ali um e-mail
    nem um nome que ninguém usa."""
    return {_campo(l, "monitorado").lower()
            for l in linhas if _campo(l, "monitorado")}
```

- [ ] **Etapa 4: rodar o teste novo e a bateria**

Rodar: `py testes\teste_calendario_casamento.py` (esperado: PASSOU)
Rodar: `for %f in (testes\*.py) do py "%f"` (esperado: zero falhas)

`data_de_planilha.mesmo_dia` já aceita texto de célula de um lado e `date` do
outro, conferido em 11/09/2026 contra as três grafias que interessam:
`mesmo_dia("06/09/26", date(2026, 9, 6))` e `mesmo_dia("06/09/2026", date(2026, 9, 6))`
devolvem `True`, e `mesmo_dia("07/09/2026", date(2026, 9, 6))` devolve `False`.
Não precisa converter antes.

---

### Tarefa 3: ler e escrever na planilha, com cópia de teste

**Arquivos:**
- Modificar: `calendario_divulgacoes.py`
- Criar: `testes/teste_calendario_escrita.py`
- Criar (uma vez, na conta do auditor): a cópia de teste do Calendário

**Interfaces:**
- Produz: `planilha_id() -> str | None` (real quando autorizado, cópia de teste
  caso contrário)
- Produz: `ler_aba(aba) -> list[list[str]]`
- Produz: `escrever(aba, numero_linha, valores) -> (bool, str)`, onde `valores`
  é um dict com chaves de `COL` (`{"jogo": "...", "status": "..."}`). Nunca
  escreve por cima de célula que já tem conteúdo, e devolve `(False, motivo)`
  em vez de levantar erro.

- [ ] **Etapa 1: criar a cópia de teste do Calendário**

Autorizado pelo auditor em 11/09/2026. Criar uma planilha nova na conta dele,
com as mesmas colunas e o mesmo formato (cabeçalho na linha 2), e algumas
linhas de exemplo, incluindo **um par de linhas iguais** em influenciador,
marca e data, para exercitar a regra da primeira vazia.

O nome precisa deixar claro que é teste, porque a ferramenta de limpeza recusa
alvo sem `TESTE` no nome: `TESTE - CALENDARIO GERAL DIVULGACOES`.

Guardar o identificador em `teste_watch_folder\calendario_teste_id.txt`, no
mesmo padrão dos outros identificadores por máquina.

- [ ] **Etapa 2: escrever o teste que falha**

Criar `testes/teste_calendario_escrita.py`:

```python
# -*- coding: utf-8 -*-
"""
Prova as três regras de escrita no Calendário, e a separação teste x real.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário é planilha VIVA de outra área, preenchida à mão todo dia. As três
regras existem para o programa nunca destruir trabalho de gente:

  1. nunca cria linha nova (se não achou, avisa)
  2. nunca escreve por cima de célula que já tem conteúdo, inclusive a sujeira
     medida na planilha real ("POSTADO NA LIVE", "-", "16:012")
  3. sem autorização de modo real, escreve na cópia de teste, sempre

Nada aqui fala com o Google: o sheets_client é dublê.

    py testes\\teste_calendario_escrita.py
"""
import os
import sys
import types

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


class SheetsFalso:
    """Guarda o que o programa quis escrever, sem escrever em lugar nenhum."""

    def __init__(self, linhas):
        self.linhas = linhas
        self.escritas = []

    def valores_da_aba(self, *a, **kw):
        return list(self.linhas)

    def escrever_lote(self, planilha, aba, coluna, atualizacoes):
        self.escritas.append((aba, coluna, list(atualizacoes)))


def rodar():
    import calendario_divulgacoes as cal

    linhas = [
        ["giroquue", "LOTTU", "Responsável F", "", "", "11/09/2026", "", "", ""],
        ["outro", "LOTTU", "Responsável A", "Mega Odds", "Publicada", "11/09/2026",
         "POSTADO NA LIVE", "Responsável A", ""],
    ]

    print("--- 1. escreve só onde está vazio ---")
    falso = SheetsFalso(linhas)
    guardado = cal.ler_aba, cal._escrever_celulas
    try:
        cal.ler_aba = lambda aba: falso.valores_da_aba()
        cal._escrever_celulas = falso.escrever_lote
        ok, motivo = cal.escrever("SET.26", 3,
                                  {"jogo": "Mines", "status": cal.STATUS_PUBLICADA,
                                   "horario": "19:07", "monitorado": "Responsável F"})
        conferir(ok, "grava na linha vazia", motivo)
        escritas = [c for _, c, _ in falso.escritas]
        conferir("D" in escritas and "E" in escritas,
                 "nas colunas de Jogo e Status", str(escritas))
    finally:
        cal.ler_aba, cal._escrever_celulas = guardado

    print()
    print("--- 2. NÃO escreve por cima do que já tem conteúdo ---")
    falso = SheetsFalso(linhas)
    guardado = cal.ler_aba, cal._escrever_celulas
    try:
        cal.ler_aba = lambda aba: falso.valores_da_aba()
        cal._escrever_celulas = falso.escrever_lote
        ok, motivo = cal.escrever("SET.26", 4, {"horario": "19:07"})
        colunas = [c for _, c, _ in falso.escritas]
        conferir("G" not in colunas,
                 "a coluna Horário com 'POSTADO NA LIVE' fica intacta",
                 str(falso.escritas))
    finally:
        cal.ler_aba, cal._escrever_celulas = guardado

    print()
    print("--- 3. falha de rede devolve motivo, e não derruba ---")
    guardado = cal.ler_aba
    try:
        def explode(aba):
            raise RuntimeError("rede fora")
        cal.ler_aba = explode
        ok, motivo = cal.escrever("SET.26", 3, {"status": cal.STATUS_PUBLICADA})
        conferir(ok is False, "devolve False em vez de levantar erro")
        conferir("rede fora" in motivo, "e o motivo real, para a tela dizer", motivo)
    finally:
        cal.ler_aba = guardado

    print()
    print("--- 4. sem autorização de modo real, é a cópia de teste ---")
    import fluxo_downloads as fluxo
    guardado = fluxo.modo_real_autorizado
    try:
        fluxo.modo_real_autorizado = lambda: False
        conferir(cal.planilha_id() != cal.ler_id_real(),
                 "fora do modo real, não devolve o identificador real",
                 "isto é o que impede escrever na planilha viva do Marketing")
    finally:
        fluxo.modo_real_autorizado = guardado

    print()
    print("--- 5. o identificador real mora em marketing_producao ---")
    conferir("marketing_producao" in cal.ARQUIVO_ID_REAL,
             "junto dos outros três, e não em teste_watch_folder",
             cal.ARQUIVO_ID_REAL)


if __name__ == "__main__":
    print("=" * 74)
    print("  Escrita no Calendário")
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
```

- [ ] **Etapa 3: rodar e confirmar que falha**

Rodar: `py testes\teste_calendario_escrita.py`
Esperado: FALHA com `AttributeError: module 'calendario_divulgacoes' has no
attribute 'escrever'`.

- [ ] **Etapa 4: escrever a leitura, a escrita e a escolha da planilha**

Acrescentar a `calendario_divulgacoes.py`:

```python
import fluxo_downloads

# O identificador da planilha REAL mora junto dos outros três de produção, e
# NÃO em teste_watch_folder. É o mesmo mecanismo do modo real: faltando
# qualquer peça, o programa escreve na cópia de teste, sem avisar, que é o
# comportamento seguro.
ARQUIVO_ID_REAL = os.path.join(fluxo_downloads.PASTA_PRODUCAO_MARKETING,
                               "calendario_id.txt")
ARQUIVO_ID_TESTE = os.path.join(fluxo_downloads.PASTA_TESTE,
                                "calendario_teste_id.txt")

# Até a coluna I, que é a última com dono na planilha deles.
ULTIMA_COLUNA = "I"


def ler_id_real():
    return fluxo_downloads.ler_identificador(ARQUIVO_ID_REAL)


def planilha_id():
    """Qual Calendário vale agora: o real ou a cópia de teste.

    Só devolve o real com o modo real autorizado (os três arquivos de sempre)
    E o identificador do Calendário presente. Faltando qualquer um, cai na
    cópia de teste."""
    if fluxo_downloads.modo_real_autorizado():
        real = ler_id_real()
        if real:
            return real
    return fluxo_downloads.ler_identificador(ARQUIVO_ID_TESTE)


def letra(nome):
    return chr(ord("A") + COL[nome])


def ler_aba(aba):
    """As linhas de dados da aba, a partir da PRIMEIRA_LINHA."""
    import sheets_client
    faixa = f"'{aba}'!A{PRIMEIRA_LINHA}:{ULTIMA_COLUNA}3000"
    resposta = sheets_client.executar(
        lambda: sheets_client.get_service().spreadsheets().values().get(
            spreadsheetId=planilha_id(), range=faixa).execute())
    return resposta.get("values", [])


def _escrever_celulas(planilha, aba, coluna, atualizacoes):
    import sheets_client
    sheets_client.escrever_lote(planilha, aba, coluna, atualizacoes)


def escrever(aba, numero_linha, valores):
    """Preenche as colunas do programa numa linha do Calendário.

    NUNCA ESCREVE POR CIMA DE CÉLULA COM CONTEÚDO. A planilha é preenchida à
    mão por outra área, e na coluna Horário existe coisa que o programa não
    entende e não precisa entender ("POSTADO NA LIVE", "-", "16:012"). Destruir
    isso seria apagar trabalho de gente sem ninguém pedir.

    Devolve (gravou, motivo). Falha de rede vira (False, motivo), nunca erro
    subindo: escrever no Calendário não pode derrubar o download."""
    try:
        linhas = ler_aba(aba)
    except Exception as e:
        return False, f"Não consegui ler o Calendário: {e}"
    posicao = numero_linha - PRIMEIRA_LINHA
    atual = linhas[posicao] if 0 <= posicao < len(linhas) else []
    gravou = []
    try:
        for nome, valor in valores.items():
            if not str(valor or "").strip():
                continue
            if _campo(atual, nome):
                continue  # já tem gente escrevendo ali
            _escrever_celulas(planilha_id(), aba, letra(nome),
                              [(numero_linha, valor)])
            gravou.append(nome)
    except Exception as e:
        return False, f"Não consegui escrever no Calendário: {e}"
    if not gravou:
        return False, "Nada a escrever: as células já estavam preenchidas."
    return True, ", ".join(gravou)
```

- [ ] **Etapa 5: rodar o teste novo e a bateria**

Rodar: `py testes\teste_calendario_escrita.py` (esperado: PASSOU)
Rodar: `for %f in (testes\*.py) do py "%f"` (esperado: zero falhas)

- [ ] **Etapa 6: acrescentar o Calendário ao verificador de ambiente**

Em `verificar_ambiente.py`, na camada de configuração, mostrar qual Calendário
está valendo (real ou teste) e se o identificador existe, do mesmo jeito que os
outros identificadores já aparecem. Sem isso, instalar numa máquina nova
esconde a falta do arquivo até alguém tentar usar.

---

### Tarefa 4: o campo Jogo viaja na fila

**Arquivos:**
- Modificar: `fluxo_downloads.py` (`COL_FILA`, `ULTIMA_COLUNA_FILA`, `ler_fila`, `adicionar_na_fila`)
- Modificar: `pages/1_Downloads_e_Organizacao.py`
- Criar: `testes/teste_campo_jogo_na_fila.py`

**Interfaces:**
- Produz: `COL_FILA` ganha `"jogo": 7`; `ULTIMA_COLUNA_FILA` vira `"H"`
- Produz: `ler_fila()` devolve `jogo` em cada item
- Produz: `adicionar_na_fila(itens)` aceita um sétimo elemento, o jogo

- [ ] **Etapa 1: escrever o teste que falha**

Criar `testes/teste_campo_jogo_na_fila.py`:

```python
# -*- coding: utf-8 -*-
"""
Prova que o campo Jogo entra na fila SEM deslocar as colunas antigas.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário do Marketing tem uma coluna Jogo (qual jogo a peça divulga:
CHUTE PREMIADO + AVIATOR, Mega Odds, Jogo do Chapéu). Reconhecer isso por
visão foi descartado pelo auditor: vira campo digitado na tela, junto com o
link, e viaja na linha da fila até a escrita no Calendário.

O RISCO: a fila é uma planilha que já tem linhas gravadas. Coluna nova no MEIO
desloca tudo o que já está lá, em silêncio. A coluna nova tem que entrar no
FIM, como a `quem_pediu` entrou em 02/09/2026.

    py testes\\teste_campo_jogo_na_fila.py
"""
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


def rodar():
    import fluxo_downloads as fluxo

    print("--- 1. as colunas antigas continuam onde estavam ---")
    ANTIGAS = {"influenciador": 0, "link": 1, "status": 2, "ciclo": 3,
               "marca": 4, "marcacao": 5, "quem_pediu": 6}
    for nome, posicao in ANTIGAS.items():
        conferir(fluxo.COL_FILA[nome] == posicao,
                 f"{nome} continua na posição {posicao}",
                 str(fluxo.COL_FILA.get(nome)))

    print()
    print("--- 2. o jogo entrou no FIM ---")
    conferir(fluxo.COL_FILA["jogo"] == 7,
             "jogo é a coluna H", str(fluxo.COL_FILA.get("jogo")))
    conferir(fluxo.ULTIMA_COLUNA_FILA == "H",
             "e a leitura da fila vai até H", fluxo.ULTIMA_COLUNA_FILA)

    print()
    print("--- 3. a tela manda o jogo junto com o link ---")
    caminho = os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py")
    tela = open(caminho, encoding="utf-8").read()
    conferir("jogo_novo" in tela, "a tela tem o campo do jogo")
    conferir("Jogo" in tela, "com rótulo em linguagem corrente")


if __name__ == "__main__":
    print("=" * 74)
    print("  O campo Jogo na fila")
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
```

- [ ] **Etapa 2: rodar e confirmar que falha**

Rodar: `py testes\teste_campo_jogo_na_fila.py`
Esperado: FALHA em "jogo é a coluna H", com `None`.

- [ ] **Etapa 3: acrescentar a coluna**

Em `fluxo_downloads.py`:

```python
# `jogo` entrou em 11/09/2026, e no FIM pelo mesmo motivo da `quem_pediu`:
# a fila é planilha com linhas já gravadas, e coluna nova no meio desloca tudo
# o que está lá, sem dar erro. É o jogo que a peça divulga (CHUTE PREMIADO +
# AVIATOR, Mega Odds), digitado na tela porque reconhecer por visão foi
# descartado: erraria, e o custo não se paga. Daqui vai para a coluna Jogo do
# Calendário de Divulgações.
COL_FILA = {"influenciador": 0, "link": 1, "status": 2, "ciclo": 3, "marca": 4,
            "marcacao": 5, "quem_pediu": 6, "jogo": 7}
ULTIMA_COLUNA_FILA = "H"
```

Em `ler_fila`, acrescentar `jogo=pega("jogo")` ao dict de cada item.

Em `adicionar_na_fila`, aceitar o sétimo elemento da tupla e gravá-lo na
posição nova, seguindo o que já é feito com `quem_pediu` (perto da linha 2918).

- [ ] **Etapa 4: acrescentar o campo na tela**

Em `pages/1_Downloads_e_Organizacao.py`, junto dos campos de ciclo e marca:

```python
jogo_novo = st.text_input(
    "Jogo",
    placeholder="ex: CHUTE PREMIADO + AVIATOR",
    help="O que a peça divulga. Vai para a coluna Jogo do Calendário de "
         "Divulgações do Marketing.",
)
```

E incluir no envio para a fila:

```python
            add, dup = fluxo.adicionar_na_fila(
                [("", link_novo, ciclo_novo, marca_nova, marcacao_nova,
                  identidade.quem_sou_eu(), jogo_novo)])
```

- [ ] **Etapa 5: rodar o teste novo e a bateria**

Rodar: `py testes\teste_campo_jogo_na_fila.py` (esperado: PASSOU)
Rodar: `for %f in (testes\*.py) do py "%f"` (esperado: zero falhas)

Atenção: se algum teste da fila quebrar por causa da coluna nova, é sinal de
que ele fixava `ULTIMA_COLUNA_FILA` ou o tamanho da linha. Corrigir o teste
para ler do módulo, e não repetir o valor.

---

### Tarefa 5: o download escreve no Calendário

**Arquivos:**
- Modificar: `fluxo_downloads.py` (o ponto que hoje registra na Monitoramento, perto da linha 4800)
- Criar: `testes/teste_calendario_no_fluxo.py`

**Interfaces:**
- Consome: `calendario_divulgacoes.achar_linha`, `.escrever`, `.aba_do_mes`,
  `.apelidos_conhecidos`, `.STATUS_PUBLICADA`
- Consome: `hora_post` da Tarefa 1 e `item["jogo"]` da Tarefa 4
- Produz: `registrar_no_calendario(handle, marca, data_video, hora_post, jogo, quem) -> (bool, str)`

- [ ] **Etapa 1: escrever o teste que falha**

Criar `testes/teste_calendario_no_fluxo.py`:

```python
# -*- coding: utf-8 -*-
"""
Prova que o download escreve no Calendário, e que falhar ali não derruba nada.

POR QUE ESTE TESTE EXISTE (11/09/2026)

O Calendário é o SEGUNDO destino de cada download, depois da Monitoramento.
Ele é conveniência para o Marketing, não é a evidência da auditoria. Então a
regra é a mesma já usada no registro de fechamentos: se falhar, avisa e segue.
Um vídeo baixado e organizado não pode virar falha porque uma planilha de outra
área estava fora do ar.

Confere também o "Monitorado por": só escreve nome que já existe naquela
coluna da planilha deles. E-mail vindo do login deixa a célula vazia.

    py testes\\teste_calendario_no_fluxo.py
"""
import datetime
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


def rodar():
    import calendario_divulgacoes as cal
    import fluxo_downloads as fluxo

    linhas = [["giroquue", "LOTTU", "Responsável F", "", "", "11/09/2026", "", "Responsável F", ""]]
    escritas = {}

    guardado = (cal.ler_aba, cal.escrever)
    try:
        cal.ler_aba = lambda aba: list(linhas)
        cal.escrever = lambda aba, n, valores: (escritas.update(valores), (True, "ok"))[1]

        print("--- 1. escreve Publicada, hora e jogo ---")
        ok, motivo = fluxo.registrar_no_calendario(
            handle="giroquue", marca="LOTTU",
            data_video=datetime.date(2026, 9, 11),
            hora_post=datetime.datetime(2026, 9, 11, 19, 7),
            jogo="Mines", quem="Responsável F")
        conferir(ok, "gravou", motivo)
        conferir(escritas.get("status") == cal.STATUS_PUBLICADA,
                 "com Status igual ao vocabulário deles", str(escritas.get("status")))
        conferir(escritas.get("horario") == "19:07",
                 "hora em HH:MM, como está na planilha deles",
                 str(escritas.get("horario")))
        conferir(escritas.get("jogo") == "Mines", "e o jogo digitado na tela")
        conferir(escritas.get("monitorado") == "Responsável F",
                 "o nome de quem monitorou, que já existe na coluna deles")

        print()
        print("--- 2. nome desconhecido deixa a célula vazia ---")
        escritas.clear()
        ok, motivo = fluxo.registrar_no_calendario(
            handle="giroquue", marca="LOTTU",
            data_video=datetime.date(2026, 9, 11),
            hora_post=None, jogo="", quem="responsavel.e@empresa.com")
        conferir(not escritas.get("monitorado"),
                 "e-mail do login não vai para a coluna de apelidos",
                 str(escritas.get("monitorado")))
    finally:
        cal.ler_aba, cal.escrever = guardado

    print()
    print("--- 3. falha no Calendário NÃO derruba o download ---")
    guardado = cal.ler_aba
    try:
        def explode(aba):
            raise RuntimeError("rede fora")
        cal.ler_aba = explode
        ok, motivo = fluxo.registrar_no_calendario(
            handle="giroquue", marca="LOTTU",
            data_video=datetime.date(2026, 9, 11),
            hora_post=None, jogo="", quem="Responsável F")
        conferir(ok is False, "devolve False, sem levantar erro")
        conferir("rede fora" in motivo or "Calendário" in motivo,
                 "e diz o motivo, para aparecer na tela", motivo)
    finally:
        cal.ler_aba = guardado

    print()
    print("--- 4. o fluxo chama o Calendário DEPOIS da Monitoramento ---")
    fonte = open(os.path.join(BASE, "fluxo_downloads.py"), encoding="utf-8").read()
    conferir("registrar_no_calendario(" in fonte, "o fluxo chama")
    conferir(fonte.index("registrar_na_monitoramento(") <
             fonte.rindex("registrar_no_calendario("),
             "a Monitoramento, que é a evidência da auditoria, vem primeiro",
             "se o Calendário falhar, a evidência já está gravada")


if __name__ == "__main__":
    print("=" * 74)
    print("  O Calendário dentro do fluxo de download")
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
```

- [ ] **Etapa 2: rodar e confirmar que falha**

Rodar: `py testes\teste_calendario_no_fluxo.py`
Esperado: FALHA com `AttributeError: module 'fluxo_downloads' has no attribute
'registrar_no_calendario'`.

- [ ] **Etapa 3: escrever a função no fluxo**

Em `fluxo_downloads.py`:

```python
def registrar_no_calendario(handle, marca, data_video, hora_post, jogo, quem):
    """Preenche a linha do Calendário de Divulgações do Marketing.

    SEGUNDO DESTINO, E NÃO O PRINCIPAL (11/09/2026). A evidência da auditoria é
    a Monitoramento, e ela é gravada antes. O Calendário é conveniência para o
    Marketing, então falhar aqui avisa e segue: vídeo baixado e organizado não
    pode virar falha porque a planilha de outra área estava fora do ar.

    Devolve (gravou, motivo)."""
    import calendario_divulgacoes as cal
    if not data_video:
        return False, "Sem a data do post não dá para achar a linha."
    aba = cal.aba_do_mes(data_video)
    try:
        linhas = cal.ler_aba(aba)
    except Exception as e:
        return False, f"Não consegui ler o Calendário: {e}"

    numero, motivo = cal.achar_linha(linhas, handle, marca, data_video)
    if numero is None:
        return False, motivo

    # O NOME SÓ VAI SE JÁ EXISTIR NAQUELA COLUNA. Com login, quem_sou_eu
    # devolve e-mail, e a coluna deles é de apelidos (Responsável F, Responsável A, Responsável G).
    # Vazio é melhor do que sujar a coluna com um valor que ninguém usa.
    monitorado = ""
    if str(quem or "").strip().lower() in cal.apelidos_conhecidos(linhas):
        monitorado = str(quem).strip()

    return cal.escrever(aba, numero, {
        "jogo": jogo or "",
        "status": cal.STATUS_PUBLICADA,
        "horario": hora_post.strftime("%H:%M") if hora_post else "",
        "monitorado": monitorado,
    })
```

- [ ] **Etapa 4: chamar no fluxo, depois da Monitoramento**

No ponto onde o download conclui e a linha da Monitoramento já foi criada
(perto da linha 4800), acrescentar:

```python
                gravou_cal, motivo_cal = registrar_no_calendario(
                    handle=handle_pasta,
                    marca=item.get("marca"),
                    data_video=data_video,
                    hora_post=hora_post,
                    jogo=item.get("jogo"),
                    quem=item.get("quem_pediu"))
                if gravou_cal:
                    log_fn(f"   -> Calendário preenchido ({motivo_cal})")
                else:
                    # AVISA, E SEGUE. Ver registrar_no_calendario.
                    log_fn(f"   -> Calendário não preenchido: {motivo_cal}")
```

- [ ] **Etapa 5: rodar o teste novo e a bateria**

Rodar: `py testes\teste_calendario_no_fluxo.py` (esperado: PASSOU)
Rodar: `for %f in (testes\*.py) do py "%f"` (esperado: zero falhas)

- [ ] **Etapa 6: provar na cópia de teste, de verdade**

Encerrar o trabalhador, subir de novo, e baixar um link de teste. Conferir na
cópia de teste do Calendário que a linha foi preenchida, com a hora certa
(comparar com a hora que aparece no Instagram).

---

### Tarefa 6: a tela de "não postou"

**Arquivos:**
- Modificar: `pages/1_Downloads_e_Organizacao.py`
- Criar: `testes/teste_nao_postou.py`

**Interfaces:**
- Consome: `calendario_divulgacoes.achar_linha`, `.escrever`, `.aba_do_mes`,
  `.STATUS_NAO_POSTADA`
- Produz: `fluxo_downloads.marcar_nao_postou(handle, marca, data, quem) -> (bool, str)`

- [ ] **Etapa 1: escrever o teste que falha**

Criar `testes/teste_nao_postou.py`:

```python
# -*- coding: utf-8 -*-
"""
Prova a marcação de "não postou", que não baixa nada.

POR QUE ESTE TESTE EXISTE (11/09/2026)

Desenho do próprio auditor: "caso não tenha sido publicada, deve ter um espaço
no programa apenas para colocar o handle do influencer e marcar como não
publicado (pq aí não vai baixar nada porque a pessoa não postou)".

O QUE ESTE TESTE PROTEGE, e é o ponto inteiro: isto NÃO PODE gastar chamada ao
Instagram. Não há vídeo, não há o que baixar, e a chamada é o recurso escasso
do programa (teto de 20 por dia por conta).

    py testes\\teste_nao_postou.py
"""
import datetime
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


def rodar():
    import calendario_divulgacoes as cal
    import fluxo_downloads as fluxo

    linhas = [["giroquue", "LOTTU", "Responsável F", "", "", "11/09/2026", "", "Responsável F", ""]]
    escritas = {}

    print("--- 1. marca Não Postada na linha certa ---")
    guardado = (cal.ler_aba, cal.escrever)
    try:
        cal.ler_aba = lambda aba: list(linhas)
        cal.escrever = lambda aba, n, valores: (escritas.update(valores), (True, "ok"))[1]
        ok, motivo = fluxo.marcar_nao_postou(
            "giroquue", "LOTTU", datetime.date(2026, 9, 11), "Responsável F")
        conferir(ok, "gravou", motivo)
        conferir(escritas.get("status") == cal.STATUS_NAO_POSTADA,
                 "com o vocabulário deles", str(escritas.get("status")))
        conferir(not escritas.get("horario"),
                 "e sem horário, porque não houve postagem",
                 str(escritas.get("horario")))
    finally:
        cal.ler_aba, cal.escrever = guardado

    print()
    print("--- 2. NÃO fala com o Instagram ---")
    import inspect
    corpo = inspect.getsource(fluxo.marcar_nao_postou)
    if '"""' in corpo:
        partes = corpo.split('"""')
        corpo = partes[0] + ("".join(partes[2:]) if len(partes) > 2 else "")
    for proibido in ("instaloader", "yt_dlp", "baixar_video", "baixar_story",
                     "_contar_uso_instagram", "resolver_userid"):
        conferir(proibido not in corpo,
                 f"não usa {proibido}",
                 "não há vídeo para baixar: gastar chamada aqui seria desperdício "
                 "do recurso mais escasso do programa")

    print()
    print("--- 3. a tela oferece o controle ---")
    caminho = os.path.join(BASE, "pages", "1_Downloads_e_Organizacao.py")
    tela = open(caminho, encoding="utf-8").read()
    conferir("marcar_nao_postou" in tela, "a tela de Downloads chama")
    conferir("não postou" in tela.lower() or "nao postou" in tela.lower(),
             "com nome em linguagem corrente")


if __name__ == "__main__":
    print("=" * 74)
    print("  Marcar quem não postou")
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
```

- [ ] **Etapa 2: rodar e confirmar que falha**

Rodar: `py testes\teste_nao_postou.py`
Esperado: FALHA com `AttributeError: ... has no attribute 'marcar_nao_postou'`.

- [ ] **Etapa 3: escrever a função**

Em `fluxo_downloads.py`:

```python
def marcar_nao_postou(handle, marca, data, quem):
    """Marca no Calendário que o influenciador não postou no dia.

    NÃO FALA COM O INSTAGRAM, de propósito: não existe vídeo para baixar, e
    chamada é o recurso escasso do programa. Ver o teste do mesmo nome.

    Devolve (gravou, motivo)."""
    import calendario_divulgacoes as cal
    if not data:
        return False, "Sem a data não dá para achar a linha."
    aba = cal.aba_do_mes(data)
    try:
        linhas = cal.ler_aba(aba)
    except Exception as e:
        return False, f"Não consegui ler o Calendário: {e}"
    numero, motivo = cal.achar_linha(linhas, handle, marca, data)
    if numero is None:
        return False, motivo
    monitorado = ""
    if str(quem or "").strip().lower() in cal.apelidos_conhecidos(linhas):
        monitorado = str(quem).strip()
    return cal.escrever(aba, numero, {
        "status": cal.STATUS_NAO_POSTADA,
        "monitorado": monitorado,
    })
```

- [ ] **Etapa 4: acrescentar a seção na tela**

Em `pages/1_Downloads_e_Organizacao.py`, num expansor fechado (é conserto de
exceção, não caminho normal, igual ao "Ensinar um perfil ao programa"):

```python
with st.expander("Marcar que alguém não postou (sem baixar nada)"):
    st.caption(
        "Quando o influenciador não publicou no dia combinado. Marca **Não "
        "Postada** na linha dele no Calendário do Marketing, sem baixar vídeo "
        "e sem gastar chamada do Instagram."
    )
    c1, c2, c3 = st.columns([2, 1, 1])
    handle_np = c1.text_input("@ do influenciador", key="handle_nao_postou")
    marca_np = c2.selectbox("Marca", options=[""] + fluxo.MARCAS,
                            key="marca_nao_postou")
    data_np = c3.date_input("Data combinada", key="data_nao_postou")
    if st.button("Marcar como não postada", key="botao_nao_postou"):
        if not handle_np.strip() or not marca_np:
            st.warning("Preencha o @ e a marca.")
        else:
            gravou, motivo = fluxo.marcar_nao_postou(
                handle_np, marca_np, data_np, identidade.quem_sou_eu())
            if gravou:
                st.success("Marcado no Calendário.")
            else:
                st.warning(motivo)
```

`fluxo.MARCAS` já existe e é `["EDS", "LOTTU", "ONA", "EDSCAP"]`
(`fluxo_downloads.py:212`), então a lista vem de lá e não é reescrita à mão.

- [ ] **Etapa 5: rodar o teste novo e a bateria**

Rodar: `py testes\teste_nao_postou.py` (esperado: PASSOU)
Rodar: `for %f in (testes\*.py) do py "%f"` (esperado: zero falhas)

- [ ] **Etapa 6: atualizar a documentação**

- `COMECE_AQUI.md`: o Calendário passa a ser um destino do fluxo, e existe a
  marcação de "não postou"
- `INSTALAR.md`: o `calendario_id.txt` entra na lista do Anexo do modo real, e
  o `calendario_teste_id.txt` na dos identificadores por máquina
- `DESENHO_CALENDARIO.md`: marcar como implementado, com a data

---

## Revisão do plano contra o desenho

Conferido item a item do `DESENHO_CALENDARIO.md`:

| requisito do desenho | onde está |
|---|---|
| escreve Jogo, Status, Horário, Monitorado por | Tarefas 4 e 5 |
| nunca cria linha nova | Tarefa 2, seção 7 do teste |
| nunca sobrescreve célula preenchida | Tarefa 3, seção 2 do teste |
| aba pela data do post | Tarefa 2, seção 3 do teste |
| normaliza handle e marca | Tarefa 2, seções 1 e 2 |
| primeira linha vazia entre as que casam | Tarefa 2, seção 5 |
| data comparada como data | Tarefa 2, seção 8 |
| horário do Instagram, em Brasília, HH:MM | Tarefas 1 e 5 |
| Monitorado por só com apelido conhecido | Tarefa 5, seção 2 |
| tela de não postou, sem chamada ao Instagram | Tarefa 6 |
| teste x real pelo arquivo novo | Tarefa 3, seções 4 e 5 |
| `Apagada` fora | não existe tarefa, por decisão |

Sem lacuna.
