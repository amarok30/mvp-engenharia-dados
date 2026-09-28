# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Silver: Stack Overflow
# MAGIC
# MAGIC **Lê:** `bronze.so_pesquisa_2022` a `bronze.so_pesquisa_2025`, `bronze.so_esquema` e o de-para versionado
# MAGIC `docs/mapa-de-para-arranjo.csv` (enviado para `/Volumes/mafia_office/bronze/pouso/referencia/`).
# MAGIC
# MAGIC **Escreve:** `silver.so_respondente`, `silver.so_de_para_arranjo`, `silver.so_metadados_pergunta`.
# MAGIC
# MAGIC **Por quê:** a Silver guarda cada registro validado, tipado e harmonizado entre safras, sem agregação. Dimensões
# MAGIC e fatos ficam só na Gold.
# MAGIC
# MAGIC O texto da pergunta de `RemoteWork` é o mesmo nas quatro safras, mas as opções mudaram em 2023 e em 2025, sem
# MAGIC aviso nos metadados. Por isso o de-para por safra é um arquivo no Git e uma tabela. Se aparecer um valor fora do
# MAGIC de-para, o notebook interrompe a execução para exigir a revisão do mapeamento da nova safra.
# MAGIC
# MAGIC O notebook também para se o de-para não tiver 15 linhas, se a chave `(safra, resposta_id)` vier nula ou repetida
# MAGIC ou se o total não for 277.080 linhas.
# MAGIC
# MAGIC Decisões:
# MAGIC - `NA` e vazio viram nulo aqui, para que o percentual de nulos conte nulo de verdade.
# MAGIC - As aspas tipográficas U+2018 e U+2019 viram `'` em `OrgSize`, `DevType`, `MainBranch`, `Employment` e
# MAGIC   `Country`. Sem isso, `I don’t know` não casa com filtro ASCII. `arranjo_trabalho_origem` fica como cópia fiel.
# MAGIC - `empregado` é verdadeiro quando algum item de `Employment` é `Employed` ou começa com `Employed,`. De 2022 a
# MAGIC   2024 os rótulos são `Employed, full-time` e `Employed, part-time` (multi-resposta); em 2025 a pergunta virou
# MAGIC   resposta única com o rótulo `Employed`. Freelancer e autônomo não entram.
# MAGIC - `autonomo` é verdadeiro quando algum item de `Employment` é `Independent contractor, freelancer, or self-employed`
# MAGIC   (rótulo igual nas quatro safras). Freelancer também responde `RemoteWork`.
# MAGIC - `trabalhando` = `empregado OR autonomo`: é a população a quem a pergunta de arranjo se aplica. Estudante,
# MAGIC   aposentado e desempregado ficam fora das análises de arranjo (ver verificação C02).
# MAGIC - `perfil_principal` é o primeiro valor de `DevType` antes do `;`. Em 2022 a pergunta é multi-resposta e a ordem
# MAGIC   segue o questionário; de 2023 a 2025 é resposta única ("the one you do most of the time"). Por isso os perfis de
# MAGIC   2022 não se comparam aos das outras safras. As respostas permanecem em uma linha para preservar o grão.
# MAGIC - `OrgSize` fora do mapa deixa `porte_empresa` nulo, sem parar o notebook. O caso é contado na verificação C06 e
# MAGIC   vira o membro `-1` na Gold; `OrgSize` ausente vira `Não informado` na Gold. Só o arranjo, que é a série
# MAGIC   principal, para a execução.
# MAGIC - `anos_codando` acima de 50 vira 50. De 2022 a 2024 a fonte já corta em "More than 50 years"; 2025 vem sem teto
# MAGIC   (há valores de 51 a 100). Valor negativo ou não numérico vira nulo.
# MAGIC - `satisfacao_trabalho` fora de 0 a 10 vira nulo e é contado.
# MAGIC - Remuneração fora de [1.000; 1.000.000] USD é marcada em `remuneracao_outlier`, nunca removida.
# MAGIC
# MAGIC A gravação com `mode("overwrite")` e `overwriteSchema` substitui o conteúdo, sem acumular registros.

# COMMAND ----------

from functools import reduce

from silver_funcoes import anos_codando, autonomo, empregado, expandir_crosswalk, gravar_silver, juntar_arranjo

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

CATALOGO = "mafia_office"
SAFRAS = [2022, 2023, 2024, 2025]
LINHAS_ESPERADAS = 277_080
LINHAS_CROSSWALK = 15
NULOS_TEXTUAIS = ["", "NA"]
REMUNERACAO_MIN_PLAUSIVEL = 1_000.0
REMUNERACAO_MAX_PLAUSIVEL = 1_000_000.0
ANOS_CODANDO_MAX = 50

dbutils.widgets.text(
    "caminho_crosswalk",
    "/Volumes/mafia_office/bronze/pouso/referencia/mapa-de-para-arranjo.csv",
    "Crosswalk (CSV versionado)",
)
CAMINHO_CROSSWALK = dbutils.widgets.get("caminho_crosswalk")

# Rótulos da fonte após normalização Unicode → faixa canônica e ordem (1 a 9).
MAPA_PORTE = {
    "Just me - I am a freelancer, sole proprietor, etc.": ("Autônomo", 1),
    "2 to 9 employees": ("Menos de 20", 2),
    "10 to 19 employees": ("Menos de 20", 2),
    "Less than 20 employees": ("Menos de 20", 2),  # 2025 funde as duas faixas acima
    "20 to 99 employees": ("20 a 99", 3),
    "100 to 499 employees": ("100 a 499", 4),
    "500 to 999 employees": ("500 a 999", 5),
    "1,000 to 4,999 employees": ("1.000 a 4.999", 6),
    "5,000 to 9,999 employees": ("5.000 a 9.999", 7),
    "10,000 or more employees": ("10.000 ou mais", 8),
    "I don't know": ("Não sabe", 9),
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de apoio

# COMMAND ----------


def nulo_textual(coluna: Column) -> Column:
    """NA e vazio viram nulo. Aplicado só na Silver."""
    return F.when(F.trim(coluna).isin(NULOS_TEXTUAIS), F.lit(None).cast("string")).otherwise(coluna)


def normalizar_unicode(coluna: Column) -> Column:
    """Aspas tipográficas simples (U+2018, U+2019) viram apóstrofo ASCII."""
    return F.translate(coluna, "‘’", "''")


def coluna_ou_nula(df: DataFrame, nome: str) -> Column:
    """Campo ausente na safra (JobSat em 2022 e 2023) entra como nulo tipado: ausência estrutural."""
    return F.col(f"`{nome}`") if nome in df.columns else F.lit(None).cast("string")


# Regras da Silver. São conferidas no DataFrame antes de gravar e depois gravadas na tabela como restrições do Delta;
# a chave primária é informativa no Unity Catalog e documenta o grão da tabela.
RESTRICOES = {
    "so_respondente": {
        "nao_nulas": ["safra", "resposta_id", "arranjo_trabalho", "comparavel_serie", "empregado", "autonomo", "trabalhando"],
        "verificacoes": {
            "ck_respondente_safra": "safra IN (2022, 2023, 2024, 2025)",
            "ck_respondente_arranjo": "arranjo_trabalho IN ('Remoto', 'Híbrido', 'Presencial', 'Flexível', 'Não informado')",
            "ck_respondente_anos_codando": "anos_codando IS NULL OR anos_codando BETWEEN 0 AND 50",
            "ck_respondente_satisfacao": "satisfacao_trabalho IS NULL OR satisfacao_trabalho BETWEEN 0 AND 10",
            "ck_respondente_remuneracao": "remuneracao_usd IS NULL OR remuneracao_usd >= 0",
            "ck_respondente_porte_ordem": "porte_ordem IS NULL OR porte_ordem BETWEEN 1 AND 9",
        },
        "chave_primaria": ["safra", "resposta_id"],
    },
    "so_de_para_arranjo": {
        "nao_nulas": ["valor_canonico", "entra_serie_historica"],
        "verificacoes": {
            "ck_de_para_canonico": "valor_canonico IN ('Remoto', 'Híbrido', 'Presencial', 'Flexível', 'Não informado')",
        },
    },
    "so_metadados_pergunta": {
        "nao_nulas": ["safra", "qname", "presente_na_safra"],
        "verificacoes": {"ck_metadados_safra": "safra IN (2022, 2023, 2024, 2025)"},
        "chave_primaria": ["safra", "qname"],
    },
}


# COMMAND ----------

# MAGIC %md
# MAGIC ## Crosswalk de arranjo de trabalho, materializado

# COMMAND ----------

schema_crosswalk = StructType(
    [
        StructField("safra", StringType(), True),
        StructField("valor_origem", StringType(), True),
        StructField("valor_canonico", StringType(), True),
        StructField("entra_serie_historica", StringType(), True),
        StructField("observacao", StringType(), True),
    ]
)

crosswalk_csv = (
    spark.read.format("csv")
    .schema(schema_crosswalk)
    .option("header", "true")
    .option("quote", '"')
    .option("escape", '"')
    .option("encoding", "UTF-8")
    .load(CAMINHO_CROSSWALK)
)

# safra 'todas' vira nulo (vale para todas as safras); valor_origem vazio já chega nulo.
so_de_para_arranjo = crosswalk_csv.select(
    F.when(F.col("safra") == "todas", F.lit(None).cast("int")).otherwise(F.col("safra").cast("int")).alias("safra"),
    F.col("valor_origem"),
    F.col("valor_canonico"),
    (F.lower(F.col("entra_serie_historica")) == "true").alias("entra_serie_historica"),
    F.col("observacao"),
)

qtd_crosswalk = so_de_para_arranjo.count()
if qtd_crosswalk != LINHAS_CROSSWALK:
    raise ValueError(f"Crosswalk com {qtd_crosswalk} linhas; esperado {LINHAS_CROSSWALK}. Confira o CSV.")

duplicadas = so_de_para_arranjo.groupBy("safra", "valor_origem").count().filter("count > 1").count()
if duplicadas:
    raise ValueError(f"Crosswalk tem {duplicadas} pares (safra, valor_origem) repetidos; o JOIN duplicaria linhas.")

gravar_silver(spark, so_de_para_arranjo, f"{CATALOGO}.silver.so_de_para_arranjo", RESTRICOES)
print(f"ok: silver.so_de_para_arranjo com {qtd_crosswalk} linhas")

# Para o JOIN: a linha 'todas' (valor nulo) é replicada para cada safra.
safras_df = spark.createDataFrame([(s,) for s in SAFRAS], "safra INT")
crosswalk_join = expandir_crosswalk(so_de_para_arranjo, safras_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## União das quatro safras, só com os campos harmonizados

# COMMAND ----------

CAMPOS = [
    "ResponseId",
    "MainBranch",
    "Employment",
    "RemoteWork",
    "Country",
    "OrgSize",
    "DevType",
    "YearsCode",
    "ConvertedCompYearly",
    "JobSat",
]


def selecionar_safra(safra: int) -> DataFrame:
    bronze = spark.table(f"{CATALOGO}.bronze.so_pesquisa_{safra}")
    return bronze.select(
        F.lit(safra).cast("int").alias("safra"),
        *[coluna_ou_nula(bronze, campo).alias(campo) for campo in CAMPOS],
        F.col("_ingerido_em"),
    )


# lambda em vez de DataFrame.unionByName não vinculado: funciona no DataFrame clássico e no do Spark Connect.
base = reduce(lambda esquerda, direita: esquerda.unionByName(direita), [selecionar_safra(s) for s in SAFRAS])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tipagem, normalização e derivações

# COMMAND ----------

mapa_porte_nome = F.create_map(*[F.lit(x) for chave, (nome, _) in MAPA_PORTE.items() for x in (chave, nome)])
mapa_porte_ordem = F.create_map(*[F.lit(x) for chave, (_, ordem) in MAPA_PORTE.items() for x in (chave, ordem)])

tratado = (
    base.withColumn("main_branch_n", normalizar_unicode(nulo_textual(F.col("MainBranch"))))
    .withColumn("employment_n", normalizar_unicode(nulo_textual(F.col("Employment"))))
    .withColumn("remote_work_n", nulo_textual(F.col("RemoteWork")))
    .withColumn("pais_n", F.trim(normalizar_unicode(nulo_textual(F.col("Country")))))
    .withColumn("org_size_n", normalizar_unicode(nulo_textual(F.col("OrgSize"))))
    .withColumn("perfil_n", normalizar_unicode(nulo_textual(F.col("DevType"))))
    .withColumn("years_code_n", nulo_textual(F.col("YearsCode")))
    .withColumn("satisfacao_bruta", F.expr("try_cast(nullif(trim(JobSat), 'NA') AS DOUBLE)"))
    .withColumn("remuneracao_usd", F.expr("try_cast(nullif(trim(ConvertedCompYearly), 'NA') AS DOUBLE)"))
)

# JOIN com o de-para por (safra, valor), nulo casando com nulo.
com_arranjo = juntar_arranjo(tratado, crosswalk_join)

nao_mapeados = (
    com_arranjo.filter(F.col("c.valor_canonico").isNull())
    .groupBy(F.col("r.safra").alias("safra"), F.col("r.RemoteWork").alias("valor"))
    .count()
    .collect()
)
if nao_mapeados:
    detalhes = "; ".join(f"{linha['safra']}: {linha['valor']!r} ({linha['count']})" for linha in nao_mapeados)
    raise ValueError(
        f"RemoteWork com valor fora do de-para: {detalhes}. "
        "Acrescente a linha em docs/mapa-de-para-arranjo.csv, atualize LINHAS_CROSSWALK neste notebook, "
        "suba o arquivo de novo e reexecute."
    )

anos_valido = anos_codando("years_code_n", ANOS_CODANDO_MAX)
satisfacao = F.col("satisfacao_bruta")

so_respondente = com_arranjo.select(
    F.col("r.safra").alias("safra"),
    F.expr("try_cast(r.ResponseId AS BIGINT)").alias("resposta_id"),
    (F.col("main_branch_n") == "I am a developer by profession").alias("e_profissional"),
    empregado(F.col("employment_n")).alias("empregado"),
    autonomo(F.col("employment_n")).alias("autonomo"),
    (empregado(F.col("employment_n")) | autonomo(F.col("employment_n"))).alias("trabalhando"),
    F.col("r.RemoteWork").alias("arranjo_trabalho_origem"),
    F.col("c.valor_canonico").alias("arranjo_trabalho"),
    (~F.col("c.valor_canonico").isin("Flexível", "Não informado")).alias("comparavel_serie"),
    F.col("pais_n").alias("pais"),
    F.coalesce(F.col("pais_n") == "Brazil", F.lit(False)).alias("e_brasil"),
    F.col("org_size_n").alias("porte_empresa_origem"),
    mapa_porte_nome[F.col("org_size_n")].alias("porte_empresa"),
    mapa_porte_ordem[F.col("org_size_n")].cast("int").alias("porte_ordem"),
    F.trim(F.split(F.col("perfil_n"), ";").getItem(0)).alias("perfil_principal"),
    anos_valido.cast("int").alias("anos_codando"),
    F.when(anos_valido.isNull(), F.lit(None).cast("string"))
    .when(anos_valido <= 2, "0–2")
    .when(anos_valido <= 5, "3–5")
    .when(anos_valido <= 10, "6–10")
    .when(anos_valido <= 20, "11–20")
    .otherwise("21+")
    .alias("faixa_experiencia"),
    F.col("remuneracao_usd"),
    F.coalesce(
        (F.col("remuneracao_usd") < REMUNERACAO_MIN_PLAUSIVEL) | (F.col("remuneracao_usd") > REMUNERACAO_MAX_PLAUSIVEL),
        F.lit(False),
    ).alias("remuneracao_outlier"),
    F.when((satisfacao >= 0) & (satisfacao <= 10), satisfacao).alias("satisfacao_trabalho"),
    F.col("r._ingerido_em").alias("_ingerido_em"),
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validações e gravação de `so_respondente`

# COMMAND ----------

gravar_silver(spark, so_respondente, f"{CATALOGO}.silver.so_respondente", RESTRICOES)
silver = spark.table(f"{CATALOGO}.silver.so_respondente")

resumo = silver.agg(
    F.count(F.lit(1)).alias("linhas"),
    F.sum(F.col("resposta_id").isNull().cast("int")).alias("chave_nula"),
    F.countDistinct("safra", "resposta_id").alias("chaves_distintas"),
).first()

if resumo["linhas"] != LINHAS_ESPERADAS:
    raise ValueError(f"so_respondente com {resumo['linhas']} linhas; esperado {LINHAS_ESPERADAS}.")
if resumo["chave_nula"]:
    raise ValueError(f"{resumo['chave_nula']} linhas com resposta_id nulo ou não numérico.")
if resumo["chaves_distintas"] != resumo["linhas"]:
    raise ValueError("Chave (safra, resposta_id) repetida dentro de alguma safra.")

print(f"ok: silver.so_respondente com {resumo['linhas']} linhas e chave (safra, resposta_id) única")

# Contagens só para acompanhar; o registro de qualidade fica no notebook 05.
display(
    silver.groupBy("safra")
    .agg(
        F.count(F.lit(1)).alias("linhas"),
        F.sum((F.col("porte_empresa_origem").isNotNull() & F.col("porte_empresa").isNull()).cast("int")).alias(
            "porte_nao_mapeado"
        ),
        F.sum(F.col("remuneracao_outlier").cast("int")).alias("remuneracao_outlier"),
    )
    .orderBy("safra")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## `so_metadados_pergunta`
# MAGIC
# MAGIC Uma linha por pergunta (`qname`) em cada safra, inclusive quando a pergunta não existia naquela safra
# MAGIC (`presente_na_safra = false`). É isso que distingue ausência estrutural de ausência real.
# MAGIC
# MAGIC Em 2025 o `schema.csv` pode repetir `qname` em subperguntas (`sub`, `sq_id`). Mantém-se uma linha por
# MAGIC `(safra, qname)`, com o menor texto e o menor tipo em ordem alfabética, para o resultado ser sempre o mesmo. O
# MAGIC grão é a pergunta, não a subpergunta.

# COMMAND ----------

schema_bronze = spark.table(f"{CATALOGO}.bronze.so_esquema").filter(F.col("qname").isNotNull())

por_safra = schema_bronze.groupBy(F.col("_safra").alias("safra"), "qname").agg(
    F.min("question").alias("texto_pergunta"),
    F.min("type").alias("tipo"),
)

universo = schema_bronze.select("qname").distinct().crossJoin(safras_df)

so_metadados_pergunta = universo.join(por_safra, ["safra", "qname"], "left").select(
    "safra",
    "qname",
    "texto_pergunta",
    "tipo",
    F.col("texto_pergunta").isNotNull().alias("presente_na_safra"),
)

gravar_silver(spark, so_metadados_pergunta, f"{CATALOGO}.silver.so_metadados_pergunta", RESTRICOES)
print(f"ok: silver.so_metadados_pergunta com {spark.table(f'{CATALOGO}.silver.so_metadados_pergunta').count()} linhas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Mesma pergunta, opções diferentes
# MAGIC
# MAGIC A primeira consulta mostra o texto da pergunta de `RemoteWork` nas quatro safras. A segunda mostra as opções de
# MAGIC cada safra. É essa mudança que o de-para trata.
# MAGIC

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT safra, presente_na_safra, texto_pergunta
        FROM {CATALOGO}.silver.so_metadados_pergunta
        WHERE qname = 'RemoteWork'
        ORDER BY safra
        """
    )
)

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT safra, arranjo_trabalho_origem, arranjo_trabalho, COUNT(*) AS respondentes
        FROM {CATALOGO}.silver.so_respondente
        GROUP BY safra, arranjo_trabalho_origem, arranjo_trabalho
        ORDER BY safra, arranjo_trabalho
        """
    )
)
