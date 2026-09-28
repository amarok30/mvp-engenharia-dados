# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Bronze: IBGE via API do SIDRA
# MAGIC
# MAGIC **Lê:** `/Volumes/mafia_office/bronze/pouso/ibge/sidra_9471.json` e `sidra_5434.json` (padrão), ou a própria
# MAGIC API do SIDRA se o workspace tiver saída de internet (widget `origem = api`).
# MAGIC
# MAGIC **Escreve:** `bronze.ibge_sidra_9471` e `bronze.ibge_sidra_5434`.
# MAGIC
# MAGIC **Por quê:** a Bronze guarda a resposta da API como veio, incluindo o cabeçalho `d[0]`. O primeiro elemento do
# MAGIC array JSON do SIDRA é um dicionário de rótulos, não dado. Ele só é descartado na Silver.
# MAGIC
# MAGIC Tabelas de origem:
# MAGIC - **9471**: pessoas de 14 anos ou mais ocupadas, por realização de trabalho remoto e teletrabalho. Só 2022,
# MAGIC   4º trimestre, marcada pelo IBGE como estatística experimental. Variáveis 4090 (pessoas), 4091 (CV de pessoas),
# MAGIC   12965 (percentual) e 12966 (CV do percentual).
# MAGIC - **5434**: pessoas de 14 anos ou mais ocupadas, por grupamento de atividade no trabalho principal. Trimestral,
# MAGIC   com período fixado em 201201-202602.
# MAGIC
# MAGIC O SIDRA aceita `/h/y` (padrão, com cabeçalho) e `/h/n` (sem cabeçalho). A carga usa o padrão `/h/y`, para que o descarte
# MAGIC do cabeçalho apareça como um passo da Silver.
# MAGIC
# MAGIC A API limita a consulta a 100.000 valores. A 5434 pede 27 UF × 13 grupamentos × 1 variável × 58 trimestres
# MAGIC (201201 a 202602), 20.358 valores.
# MAGIC
# MAGIC Decisões:
# MAGIC - Consulto a 9471 com `n1/all/n3/all`, que traz Brasil e UF juntos. Assim confiro os totais nacionais publicados
# MAGIC   sem somar UFs arredondadas.
# MAGIC - Na 9471, o CV de pessoas (4091) acompanha `pessoas_mil` e o CV do percentual (12966) acompanha o percentual.
# MAGIC - Na 5434 fixei o período `201201-202602` em vez de `p/all`, para que a contagem de 20.359 continue valendo quando
# MAGIC   o IBGE publicar trimestres novos.
# MAGIC - A carga acrescenta a coluna `_ordem_registro`, além das cinco de auditoria. O Delta não guarda ordem de linha, e sem ela não
# MAGIC   dá para achar o `d[0]` com segurança.
# MAGIC - `_safra` da 5434 fica nulo, porque a tabela é uma série de 2012 a 2026, não uma safra.
# MAGIC
# MAGIC A recarga usa `mode("overwrite")` e `overwriteSchema`.

# COMMAND ----------

import json
import os
import uuid
from datetime import datetime, timezone

import requests
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

CATALOGO = "mafia_office"
LANDING_IBGE = "/Volumes/mafia_office/bronze/pouso/ibge"
SISTEMA_ORIGEM = "ibge_sidra"
TIMEOUT_API_SEGUNDOS = 180

FONTES_SIDRA = {
    "9471": {
        "url": "https://apisidra.ibge.gov.br/values/t/9471/n1/all/n3/all/v/4090,4091,12965,12966/p/2022/c1675/all/d/m",
        "arquivo": f"{LANDING_IBGE}/sidra_9471.json",
        "safra": 2022,
        "registros_esperados": 673,  # medido em 13/09/2026, inclui o cabeçalho d[0]: 28 territórios × 6 × 4 + 1
    },
    "5434": {
        "url": "https://apisidra.ibge.gov.br/values/t/5434/n3/all/v/4090/p/201201-202602/c888/all",
        "arquivo": f"{LANDING_IBGE}/sidra_5434.json",
        "safra": None,
        "registros_esperados": 20_359,  # medido em 13/09/2026, inclui o cabeçalho d[0]
    },
}

dbutils.widgets.dropdown("origem", "arquivo", ["arquivo", "api"], "Origem dos dados SIDRA")
ORIGEM = dbutils.widgets.get("origem")

LOTE_ID = f"lote_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:8]}"
print(f"Origem: {ORIGEM} · lote: {LOTE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Carga com parâmetro `origem`
# MAGIC
# MAGIC - `origem = arquivo` (padrão): lê o JSON enviado para o Volume.
# MAGIC - `origem = api`: chama a API direto. Só funciona se o domínio do IBGE estiver liberado; na Free Edition a saída
# MAGIC   de rede é limitada a alguns domínios (`docs/referencias.md` §6.1). No fórum da Databricks aparece o erro de DNS
# MAGIC   `[Errno -3] Temporary failure in name resolution` (§6.7), que chega como `ConnectionError`. Por isso capturo
# MAGIC   `RequestException`, que cobre esse caso e o `HTTPError`.

# COMMAND ----------


def carregar_sidra(tabela_sidra: str, origem: str) -> tuple[list[dict], str]:
    """Devolve (registros, origem_registrada). origem_registrada é o caminho no Volume ou a URL."""
    fonte = FONTES_SIDRA[tabela_sidra]

    if origem == "arquivo":
        caminho = fonte["arquivo"]
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"{caminho} não encontrado. Faça upload ou rode com origem = api.")
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo), caminho

    if origem == "api":
        try:
            resposta = requests.get(fonte["url"], timeout=TIMEOUT_API_SEGUNDOS)
            resposta.raise_for_status()
        except requests.exceptions.RequestException as erro:
            raise RuntimeError(
                f"Falha ao chamar a API do SIDRA ({fonte['url']}): {erro}. "
                "Se a mensagem fala em name resolution, o workspace não tem saída de internet: "
                "baixe com scripts/baixar_fontes.sh, suba para o Volume e rode com origem = arquivo."
            ) from erro
        return resposta.json(), fonte["url"]

    raise ValueError(f"origem inválida: {origem}. Use 'arquivo' ou 'api'.")


def e_numero(texto: str) -> bool:
    try:
        float(texto.replace(",", "."))
        return True
    except ValueError:
        return False


def validar_estrutura(registros: list, tabela_sidra: str) -> None:
    if not isinstance(registros, list) or len(registros) < 2:
        raise ValueError(f"SIDRA {tabela_sidra}: resposta não é um array com cabeçalho e dados.")
    esperados = FONTES_SIDRA[tabela_sidra]["registros_esperados"]
    if esperados is not None and len(registros) != esperados:
        raise ValueError(
            f"SIDRA {tabela_sidra}: {len(registros)} registros; esperado {esperados} (com cabeçalho). "
            "Arquivo truncado ou consulta diferente da documentada nesta célula."
        )
    # d[0] é o dicionário de rótulos: o campo V traz um texto, não um número.
    valor_cabecalho = str(registros[0].get("V", ""))
    if e_numero(valor_cabecalho):
        raise ValueError(f"SIDRA {tabela_sidra}: d[0].V = {valor_cabecalho!r} é número; o cabeçalho não veio.")
    if tabela_sidra == "9471" and not any(str(r.get("NC")) == "1" for r in registros[1:]):
        raise ValueError("SIDRA 9471 sem registros de nível Brasil (NC = 1). A URL precisa ter /n1/all/n3/all/.")


def dominio_sidra(coluna: str) -> str:
    """Domínio de cada campo da resposta do SIDRA, pelo padrão de nome que a API usa."""
    if coluna == "V":
        return "número em texto com ponto decimal, ou sinal convencional do IBGE (-, .., ..., x)"
    if coluna == "NC":
        return "código do nível territorial (1 Brasil, 3 UF)"
    if coluna == "NN":
        return "nome do nível territorial"
    if coluna == "MC":
        return "código da unidade de medida"
    if coluna == "MN":
        return "unidade de medida (Mil pessoas ou %)"
    if len(coluna) == 3 and coluna[0] == "D" and coluna[2] == "C":
        return "código da dimensão em texto numérico"
    if len(coluna) == 3 and coluna[0] == "D" and coluna[2] == "N":
        return "rótulo da dimensão"
    return "texto da API"


def gravar_bronze_sidra(tabela_sidra: str, registros: list[dict], origem_registrada: str) -> None:
    fonte = FONTES_SIDRA[tabela_sidra]

    # Colunas na ordem do cabeçalho; chaves que só aparecem em registros de dado entram no fim.
    colunas = list(registros[0].keys())
    for registro in registros[1:]:
        for chave in registro:
            if chave not in colunas:
                colunas.append(chave)

    # Comentário de cada coluna a partir do rótulo que a própria API manda no cabeçalho d[0].
    rotulos = registros[0]
    schema = StructType(
        [
            StructField(
                coluna,
                StringType(),
                True,
                {"comment": f"Campo {coluna} da resposta da API do SIDRA. Rótulo no cabeçalho d[0]: {rotulos.get(coluna, 'sem rótulo')}. Texto como veio da fonte. Domínio: {dominio_sidra(coluna)}. Linhagem: campo {coluna} do JSON da API, sem transformação."},
            )
            for coluna in colunas
        ]
        + [
            StructField(
                "_ordem_registro",
                IntegerType(),
                False,
                {"comment": "Posição do registro no array JSON da resposta. 0 é o cabeçalho d[0], que a Silver descarta. Domínio: inteiro de 0 ao total de registros menos 1. Linhagem: posição do registro no array, gerada na leitura."},
            )
        ]
    )
    linhas = [
        tuple(None if registro.get(coluna) is None else str(registro.get(coluna)) for coluna in colunas) + (ordem,)
        for ordem, registro in enumerate(registros)
    ]

    df = (
        spark.createDataFrame(linhas, schema).select(
            "*",
            F.lit(SISTEMA_ORIGEM).alias("_sistema_origem", metadata={"comment": "Sistema de origem do registro. Domínio: stackoverflow_survey ou ibge_sidra. Linhagem: constante da carga."}),
            F.current_timestamp().alias("_ingerido_em", metadata={"comment": "Momento em que o registro foi gravado na Bronze. Domínio: data e hora UTC da carga. Linhagem: current_timestamp() da carga."}),
            F.lit(origem_registrada).alias("_arquivo_origem", metadata={"comment": "Arquivo do Volume (ou URL da API) de onde o registro veio. Domínio: caminho em /Volumes/mafia_office/bronze/pouso ou URL do SIDRA. Linhagem: parâmetro da carga."}),
            F.lit(LOTE_ID).alias("_lote_id", metadata={"comment": "Identificador da execução que gravou o registro. Domínio: lote_AAAAMMDDTHHMMSSZ seguido de 8 caracteres. Linhagem: gerado no início do notebook."}),
            F.lit(fonte["safra"]).cast("int").alias("_safra", metadata={"comment": "Ano de referência (2022 na tabela 9471; nulo na 5434, que é uma série de 2012 a 2026). Domínio: 2022 ou nulo. Linhagem: parâmetro da carga."}),
        )
    )

    tabela = f"{CATALOGO}.bronze.ibge_sidra_{tabela_sidra}"
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(tabela)
    )

    comentario = (
        f"Resposta fiel da API do SIDRA, tabela {tabela_sidra}, todas as colunas STRING. "
        f"URL exata que gerou o arquivo: {fonte['url']} . "
        "O registro com _ordem_registro = 0 é o cabeçalho d[0] (dicionário de rótulos), preservado aqui e descartado "
        "na Silver. A API aceita /h/n para suprimir o cabeçalho; a carga usa o padrão /h/y."
    ).replace("'", "\\'")
    spark.sql(f"COMMENT ON TABLE {tabela} IS '{comentario}'")

    gravadas = spark.table(tabela).count()
    if gravadas != len(registros):
        raise ValueError(f"{tabela}: {gravadas} linhas gravadas; {len(registros)} recebidas.")
    print(f"ok: {tabela} com {gravadas} registros (inclui cabeçalho) · colunas da fonte: {colunas}")


# COMMAND ----------

for codigo in FONTES_SIDRA:
    registros, origem_registrada = carregar_sidra(codigo, ORIGEM)
    validar_estrutura(registros, codigo)
    gravar_bronze_sidra(codigo, registros, origem_registrada)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidência: o cabeçalho está na Bronze
# MAGIC
# MAGIC Mostra o registro `d[0]` de cada tabela e a contagem total: 673 na 9471 e 20.359 na 5434.
# MAGIC

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT '9471' AS tabela, (SELECT COUNT(*) FROM {CATALOGO}.bronze.ibge_sidra_9471) AS registros, *
        FROM {CATALOGO}.bronze.ibge_sidra_9471 WHERE _ordem_registro = 0
        """
    )
)
display(
    spark.sql(
        f"""
        SELECT '5434' AS tabela, (SELECT COUNT(*) FROM {CATALOGO}.bronze.ibge_sidra_5434) AS registros, *
        FROM {CATALOGO}.bronze.ibge_sidra_5434 WHERE _ordem_registro = 0
        """
    )
)
