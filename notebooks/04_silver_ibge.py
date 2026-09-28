# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Silver: IBGE
# MAGIC
# MAGIC **Lê:** `bronze.ibge_sidra_9471` e `bronze.ibge_sidra_5434`.
# MAGIC
# MAGIC **Escreve:** `silver.ibge_teletrabalho_uf` e `silver.ibge_ocupados_uf_atividade`.
# MAGIC
# MAGIC **Por quê:** transforma a resposta bruta da API em tabelas tipadas, no grão da estimativa publicada. O processamento descarta o
# MAGIC cabeçalho `d[0]`, identifica cada par `DnC`/`DnN` pelo rótulo do cabeçalho (sem supor a ordem), pivota as
# MAGIC variáveis da 9471 em colunas, classifica o CV em faixas e converte o período `AAAATT` em ano e trimestre.
# MAGIC
# MAGIC O notebook para se a linha Brasil da 9471 não reproduzir os números oficiais de 2022: 96.695 mil ocupados,
# MAGIC 9.462 mil em trabalho remoto e 7.399 mil em teletrabalho.
# MAGIC
# MAGIC Decisões:
# MAGIC - `ibge_teletrabalho_uf` guarda também a linha Brasil, com `nivel_territorial = 'pais'`. Assim a checagem
# MAGIC   nacional e a Q6 usam o total publicado, com seu CV, em vez de somar UFs arredondadas.
# MAGIC - O filtro usa `modalidade_codigo` (código estável da classificação `c1675`).
# MAGIC - Na 9471, `ano = 2022`, que é o grão anual do modelo; a referência ao 4º trimestre fica no comentário.
# MAGIC - As seis faixas de CV (Exata a Imprecisa) são uma convenção do projeto. O IBGE publica o CV, mas as notas técnicas da
# MAGIC   PNAD Contínua não definem faixas (`docs/referencias.md` §6.3).
# MAGIC - CV de pessoas (4091) e CV do percentual (12966) ficam em colunas separadas, cada um com suas faixas.
# MAGIC   `pessoas_mil` segue o CV de pessoas e `percentual` segue o CV do percentual.
# MAGIC - `estimativa_confiavel` usa o CV do percentual, que é o usado nas comparações entre UFs, com limiar de 15%.
# MAGIC   Esse limiar também é critério do projeto, não do IBGE. CV nulo deixa a classificação e `estimativa_confiavel` nulos.
# MAGIC - Sinais convencionais do IBGE (`docs/referencias.md` §6.6): cada medida ganha a coluna `<medida>_sinal`.
# MAGIC   `-` (zero não resultante de arredondamento) vira 0; `..` (não se aplica), `...` (não disponível) e `x` (omitido
# MAGIC   para não individualizar a informação, verificação C27) viram nulo, com o sinal guardado; `0` ou `0,0` é número
# MAGIC   publicado e fica 0, sem sinal. Símbolo fora dessa lista para o notebook. No dado real só aparece `-`, no CV do
# MAGIC   Total da 9471 e no grupamento Atividades mal definidas da 5434 (contagem no C18).
# MAGIC - Pela nota da tabela 9471 (`docs/referencias.md` §6.8), as categorias "Realizou teletrabalho fora do domicílio"
# MAGIC   e "Realizou teletrabalho no domicílio e fora do domicílio" só estão disponíveis para Brasil e Grande Região.
# MAGIC   A API devolve essas categorias por UF mesmo assim. As linhas são preservadas com `disponivel_no_nivel = false`
# MAGIC   (verificação C28).
# MAGIC
# MAGIC A gravação com `mode("overwrite")` e `overwriteSchema` substitui o conteúdo, sem acumular registros.

# COMMAND ----------

from silver_funcoes import gravar_silver

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

CATALOGO = "mafia_office"

VAR_PESSOAS = "4090"
VAR_CV_PESSOAS = "4091"
VAR_PERCENTUAL = "12965"
VAR_CV_PERCENTUAL = "12966"

CODIGO_PROXY_TECNOLOGIA = "56624"

# Totais oficiais do Brasil, 2022 (mil pessoas), por código da classificação c1675.
TOTAIS_BRASIL_2022 = {
    "59803": 96_695,  # Total de ocupados
    "59804": 9_462,  # Realizou trabalho remoto
    "59805": 7_399,  # Realizou teletrabalho
}
TOLERANCIA_ARREDONDAMENTO = 0.5  # o valor publicado é inteiro em mil pessoas

NIVEL_TERRITORIAL = {"1": "pais", "3": "uf"}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de apoio

# COMMAND ----------


def rotulos_do_cabecalho(tabela: str) -> dict[str, str]:
    cabecalho = spark.table(tabela).filter(F.col("_ordem_registro") == 0).collect()
    if len(cabecalho) != 1:
        raise ValueError(f"{tabela}: esperado exatamente 1 registro de cabeçalho, encontrado {len(cabecalho)}.")
    return {chave: valor for chave, valor in cabecalho[0].asDict().items() if not chave.startswith("_")}


def papeis_das_dimensoes(rotulos: dict[str, str], tabela: str) -> dict[str, str]:
    """Descobre qual Dn é território, variável, período e classificação a partir dos rótulos de d[0]."""
    dimensoes = sorted({chave[:-1] for chave in rotulos if chave.startswith("D") and chave[-1] in "CN"})
    papeis: dict[str, str] = {}
    for dim in dimensoes:
        rotulo = (rotulos.get(f"{dim}N") or "").strip()
        if rotulo == "Variável":
            papeis["variavel"] = dim
        elif rotulo.startswith("Ano") or rotulo.startswith("Trimestre"):
            papeis["periodo"] = dim
        elif "Unidade da Federação" in rotulo or rotulo.startswith("Brasil"):
            papeis["territorio"] = dim
        else:
            papeis.setdefault("classificacao", dim)
    faltando = {"variavel", "periodo", "territorio", "classificacao"} - papeis.keys()
    if faltando:
        raise ValueError(f"{tabela}: dimensões não identificadas: {sorted(faltando)} nos rótulos do cabeçalho: {rotulos}")
    print(f"{tabela}: papéis das dimensões {papeis}")
    return papeis


def registros_de_dado(tabela: str) -> DataFrame:
    return spark.table(tabela).filter(F.col("_ordem_registro") > 0)


SINAIS_SEM_NUMERO = ["..", "...", "x"]
MODALIDADES_SO_BRASIL_E_REGIAO = ["59807", "59808"]


def sinal_ibge(coluna: str = "V") -> Column:
    """Sinal convencional da célula: `-`, `..`, `...` ou `x`; nulo quando a célula traz número; `outro` se desconhecido."""
    texto = F.trim(F.col(coluna))
    numero = F.expr(f"try_cast(replace(trim({coluna}), ',', '.') AS DOUBLE)")
    return (
        F.when(texto.isin("-", "..", "..."), texto)
        .when(F.lower(texto) == "x", F.lit("x"))
        .when(numero.isNotNull(), F.lit(None).cast("string"))
        .otherwise(F.lit("outro"))
    )


def valor_numerico(coluna: str = "V") -> Column:
    """`-` é zero não resultante de arredondamento; `..`, `...` e `x` não têm número; o resto é o número publicado."""
    sinal = sinal_ibge(coluna)
    return (
        F.when(sinal == "-", F.lit(0.0))
        .when(sinal.isNotNull(), F.lit(None).cast("double"))
        .otherwise(F.expr(f"try_cast(replace(trim({coluna}), ',', '.') AS DOUBLE)"))
    )


def exigir_sinais_conhecidos(tabela: str) -> None:
    desconhecidos = registros_de_dado(tabela).filter(sinal_ibge() == "outro").select("V").distinct().limit(10).collect()
    if desconhecidos:
        raise ValueError(f"{tabela}: valor sem número e fora dos sinais convencionais: {[l['V'] for l in desconhecidos]}")


def classificar_cv(cv: Column) -> Column:
    """Seis faixas definidas pelo projeto sobre o CV publicado; não são uma classificação do IBGE."""
    return (
        F.when(cv.isNull(), F.lit(None).cast("string"))
        .when(cv == 0, "Exata")
        .when(cv <= 5, "Ótima")
        .when(cv <= 15, "Boa")
        .when(cv <= 30, "Razoável")
        .when(cv <= 50, "Pouco precisa")
        .otherwise("Imprecisa")
    )


# Regras da Silver. São conferidas no DataFrame antes de gravar e depois gravadas na tabela como restrições do Delta;
# a chave primária é informativa no Unity Catalog e documenta o grão da tabela.
RESTRICOES = {
    "ibge_teletrabalho_uf": {
        "nao_nulas": ["nivel_territorial", "uf_codigo", "ano", "modalidade_codigo"],
        "verificacoes": {
            "ck_teletrabalho_ano": "ano = 2022",
            "ck_teletrabalho_percentual": "percentual IS NULL OR percentual BETWEEN 0 AND 100",
            "ck_teletrabalho_pessoas": "pessoas_mil IS NULL OR pessoas_mil >= 0",
            "ck_teletrabalho_cv": "(cv_percentual IS NULL OR cv_percentual >= 0) AND (cv_pessoas IS NULL OR cv_pessoas >= 0)",
        },
        "chave_primaria": ["uf_codigo", "modalidade_codigo"],
    },
    "ibge_ocupados_uf_atividade": {
        "nao_nulas": ["uf_codigo", "ano", "trimestre", "periodo_codigo", "atividade_codigo"],
        "verificacoes": {
            "ck_ocupados_trimestre": "trimestre BETWEEN 1 AND 4",
            "ck_ocupados_pessoas": "pessoas_mil IS NULL OR pessoas_mil >= 0",
        },
        "chave_primaria": ["uf_codigo", "periodo_codigo", "atividade_codigo"],
    },
}


# COMMAND ----------

# MAGIC %md
# MAGIC ## `ibge_teletrabalho_uf` (tabela 9471)

# COMMAND ----------

tabela_9471 = f"{CATALOGO}.bronze.ibge_sidra_9471"
p = papeis_das_dimensoes(rotulos_do_cabecalho(tabela_9471), tabela_9471)

niveis_encontrados = {linha["NC"] for linha in registros_de_dado(tabela_9471).select("NC").distinct().collect()}
niveis_desconhecidos = niveis_encontrados - NIVEL_TERRITORIAL.keys()
if niveis_desconhecidos:
    raise ValueError(f"9471: nível territorial inesperado {niveis_desconhecidos}; esperado 1 (Brasil) e 3 (UF).")

longo_9471 = registros_de_dado(tabela_9471).select(
    F.col(f"{p['territorio']}C").alias("uf_codigo"),
    F.col(f"{p['territorio']}N").alias("uf_nome"),
    F.col("NC").alias("nc"),
    F.col(f"{p['periodo']}C").alias("periodo_codigo"),
    F.col(f"{p['classificacao']}C").alias("modalidade_codigo"),
    F.col(f"{p['classificacao']}N").alias("modalidade"),
    F.col(f"{p['variavel']}C").alias("variavel_codigo"),
    valor_numerico().alias("valor"),
    sinal_ibge().alias("sinal"),
)
exigir_sinais_conhecidos(tabela_9471)

nivel_expr = F.create_map(*[F.lit(x) for par in NIVEL_TERRITORIAL.items() for x in par])
cv = F.col(f"`{VAR_CV_PERCENTUAL}_valor`")
cv_pessoas = F.col(f"`{VAR_CV_PESSOAS}_valor`")

ibge_teletrabalho_uf = (
    longo_9471.groupBy("uf_codigo", "uf_nome", "nc", "periodo_codigo", "modalidade_codigo", "modalidade")
    .pivot("variavel_codigo", [VAR_PESSOAS, VAR_CV_PESSOAS, VAR_PERCENTUAL, VAR_CV_PERCENTUAL])
    .agg(F.first("valor").alias("valor"), F.first("sinal").alias("sinal"))
    .select(
        nivel_expr[F.col("nc")].alias("nivel_territorial"),
        "uf_codigo",
        "uf_nome",
        F.substring("periodo_codigo", 1, 4).cast("int").alias("ano"),
        "modalidade_codigo",
        "modalidade",
        F.col(f"`{VAR_PESSOAS}_valor`").alias("pessoas_mil"),
        F.col(f"`{VAR_PESSOAS}_sinal`").alias("pessoas_mil_sinal"),
        cv_pessoas.alias("cv_pessoas"),
        F.col(f"`{VAR_CV_PESSOAS}_sinal`").alias("cv_pessoas_sinal"),
        classificar_cv(cv_pessoas).alias("cv_pessoas_classificacao"),
        F.col(f"`{VAR_PERCENTUAL}_valor`").alias("percentual"),
        F.col(f"`{VAR_PERCENTUAL}_sinal`").alias("percentual_sinal"),
        cv.alias("cv_percentual"),
        F.col(f"`{VAR_CV_PERCENTUAL}_sinal`").alias("cv_percentual_sinal"),
        classificar_cv(cv).alias("cv_classificacao"),
        F.when(cv.isNotNull(), cv <= 15).alias("estimativa_confiavel"),
        (~((nivel_expr[F.col("nc")] == "uf") & F.col("modalidade_codigo").isin(MODALIDADES_SO_BRASIL_E_REGIAO))).alias(
            "disponivel_no_nivel"
        ),
        F.lit(True).alias("e_experimental"),
    )
)

gravar_silver(spark, ibge_teletrabalho_uf, f"{CATALOGO}.silver.ibge_teletrabalho_uf", RESTRICOES)
tele = spark.table(f"{CATALOGO}.silver.ibge_teletrabalho_uf")
print(f"ok: silver.ibge_teletrabalho_uf com {tele.count()} linhas (28 territórios × 6 modalidades)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Checagem: a Silver reproduz os totais oficiais do Brasil

# COMMAND ----------

brasil = {
    linha["modalidade_codigo"]: linha["pessoas_mil"]
    for linha in tele.filter(F.col("nivel_territorial") == "pais")
    .filter(F.col("modalidade_codigo").isin(list(TOTAIS_BRASIL_2022)))
    .select("modalidade_codigo", "pessoas_mil")
    .collect()
}

divergencias = []
for codigo, esperado in TOTAIS_BRASIL_2022.items():
    obtido = brasil.get(codigo)
    if obtido is None or abs(obtido - esperado) > TOLERANCIA_ARREDONDAMENTO:
        divergencias.append(f"c1675={codigo}: obtido {obtido}, esperado {esperado}")

if divergencias:
    raise AssertionError("Silver não reproduz os totais oficiais do Brasil em 2022: " + "; ".join(divergencias))
print(f"ok: totais do Brasil reproduzidos {brasil}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## `ibge_ocupados_uf_atividade` (tabela 5434)

# COMMAND ----------

tabela_5434 = f"{CATALOGO}.bronze.ibge_sidra_5434"
p = papeis_das_dimensoes(rotulos_do_cabecalho(tabela_5434), tabela_5434)

variaveis_5434 = {linha[0] for linha in registros_de_dado(tabela_5434).select(f"{p['variavel']}C").distinct().collect()}
if variaveis_5434 != {VAR_PESSOAS}:
    raise ValueError(f"5434: variáveis {variaveis_5434}; esperado só {VAR_PESSOAS}.")

ibge_ocupados_uf_atividade = registros_de_dado(tabela_5434).select(
    F.col(f"{p['territorio']}C").alias("uf_codigo"),
    F.col(f"{p['territorio']}N").alias("uf_nome"),
    F.substring(F.col(f"{p['periodo']}C"), 1, 4).cast("int").alias("ano"),
    F.substring(F.col(f"{p['periodo']}C"), 5, 2).cast("int").alias("trimestre"),
    F.col(f"{p['periodo']}C").alias("periodo_codigo"),
    F.col(f"{p['classificacao']}C").alias("atividade_codigo"),
    F.col(f"{p['classificacao']}N").alias("atividade_nome"),
    (F.col(f"{p['classificacao']}C") == CODIGO_PROXY_TECNOLOGIA).alias("e_proxy_tecnologia"),
    valor_numerico().alias("pessoas_mil"),
    sinal_ibge().alias("pessoas_mil_sinal"),
)
exigir_sinais_conhecidos(tabela_5434)

gravar_silver(spark, ibge_ocupados_uf_atividade, f"{CATALOGO}.silver.ibge_ocupados_uf_atividade", RESTRICOES)

linhas_bronze = spark.table(tabela_5434).count()
linhas_silver = spark.table(f"{CATALOGO}.silver.ibge_ocupados_uf_atividade").count()
if linhas_silver != linhas_bronze - 1:
    raise ValueError(f"5434: Silver com {linhas_silver} linhas; esperado Bronze menos cabeçalho = {linhas_bronze - 1}.")

periodos_invalidos = (
    spark.table(f"{CATALOGO}.silver.ibge_ocupados_uf_atividade")
    .filter(~F.col("trimestre").between(1, 4) | F.col("ano").isNull())
    .count()
)
if periodos_invalidos:
    raise ValueError(f"5434: {periodos_invalidos} linhas com período fora do formato AAAATT.")

print(f"ok: silver.ibge_ocupados_uf_atividade com {linhas_silver} linhas (Bronze {linhas_bronze} menos cabeçalho)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidência
# MAGIC

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT modalidade_codigo, modalidade, pessoas_mil, percentual, cv_percentual, cv_classificacao
        FROM {CATALOGO}.silver.ibge_teletrabalho_uf
        WHERE nivel_territorial = 'pais'
        ORDER BY modalidade_codigo
        """
    )
)

# COMMAND ----------

display(
    spark.sql(
        f"""
        SELECT modalidade, cv_classificacao, COUNT(*) AS ufs
        FROM {CATALOGO}.silver.ibge_teletrabalho_uf
        WHERE nivel_territorial = 'uf' AND disponivel_no_nivel
        GROUP BY modalidade, cv_classificacao
        ORDER BY modalidade, cv_classificacao
        """
    )
)
