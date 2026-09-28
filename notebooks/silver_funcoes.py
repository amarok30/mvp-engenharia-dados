"""Funções da Silver compartilhadas pelos notebooks e pelos testes locais."""

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F


def empregado(coluna: Column) -> Column:
    """Reconhece o vínculo empregado nas respostas únicas e multivaloradas."""
    return F.coalesce(coluna.rlike(r"(^|;)\s*Employed(,|;|$)"), F.lit(False))


def autonomo(coluna: Column) -> Column:
    return F.coalesce(
        coluna.rlike(r"(^|;)\s*Independent contractor, freelancer, or self-employed(;|$)"), F.lit(False)
    )


def anos_codando(coluna: str, maximo: int = 50) -> Column:
    """Converte os limites textuais; descarta negativos e limita a experiência ao teto comum às safras."""
    identificador = "`" + coluna.replace("`", "``") + "`"
    bruto = (
        F.when(F.col(coluna) == "Less than 1 year", F.lit(0))
        .when(F.col(coluna) == "More than 50 years", F.lit(maximo))
        .otherwise(F.expr(f"try_cast({identificador} AS INT)"))
    )
    return F.when(bruto > maximo, F.lit(maximo)).when(bruto >= 0, bruto).cast("int")


def expandir_crosswalk(crosswalk: DataFrame, safras: DataFrame) -> DataFrame:
    """Replica as regras sem safra, inclusive a resposta ausente, para cada ano."""
    return crosswalk.filter(F.col("safra").isNotNull()).unionByName(
        crosswalk.filter(F.col("safra").isNull()).drop("safra").crossJoin(safras)
    )


def juntar_arranjo(respostas: DataFrame, crosswalk: DataFrame) -> DataFrame:
    """JOIN por safra e resposta, preservando aliases e fazendo nulo casar com nulo."""
    return respostas.alias("r").join(
        crosswalk.alias("c"),
        (F.col("r.safra") == F.col("c.safra")) & F.col("r.remote_work_n").eqNullSafe(F.col("c.valor_origem")),
        "left",
    )


def conferir_regras(df: DataFrame, regras: dict, tabela: str) -> None:
    """Conta, numa só leitura, as linhas que violam cada regra; a chave primária é conferida à parte."""
    violacoes = [F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(f"nao_nulo_{c}") for c in regras.get("nao_nulas", [])]
    violacoes += [F.sum(F.when(~F.expr(e), 1).otherwise(0)).alias(n) for n, e in regras.get("verificacoes", {}).items()]
    falhas = []
    if violacoes:
        contagens = df.agg(*violacoes).first().asDict()
        falhas = [f"{regra}: {n} linha(s)" for regra, n in contagens.items() if n]
    chave = regras.get("chave_primaria")
    if chave and df.groupBy(*chave).count().filter("count > 1").limit(1).count():
        falhas.append(f"chave primária {chave} repetida")
    if falhas:
        raise AssertionError(f"{tabela} não foi gravada; regras violadas: {falhas}")


def gravar_silver(spark, df: DataFrame, tabela: str, restricoes: dict) -> None:
    """Confere as regras de restricoes no DataFrame, grava a tabela e grava as mesmas regras nela.

    A checagem vem antes da escrita: se uma linha violar uma regra, o notebook para e a tabela antiga fica como
    estava. Depois da escrita, as regras voltam para a tabela (a sobrescrita troca o schema, e uma restrição antiga
    impediria isso), e o Delta passa a recusar qualquer escrita futura que as viole.
    """
    nome = tabela.split(".")[-1]
    regras = restricoes.get(nome, {})
    conferir_regras(df, regras, tabela)
    if spark.catalog.tableExists(tabela):
        if regras.get("chave_primaria"):
            spark.sql(f"ALTER TABLE {tabela} DROP CONSTRAINT IF EXISTS pk_{nome}")
        for restricao in regras.get("verificacoes", {}):
            spark.sql(f"ALTER TABLE {tabela} DROP CONSTRAINT IF EXISTS {restricao}")
        colunas_atuais = spark.table(tabela).columns
        for coluna in regras.get("nao_nulas", []):
            if coluna in colunas_atuais:
                spark.sql(f"ALTER TABLE {tabela} ALTER COLUMN {coluna} DROP NOT NULL")
    df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(tabela)
    for coluna in regras.get("nao_nulas", []):
        spark.sql(f"ALTER TABLE {tabela} ALTER COLUMN {coluna} SET NOT NULL")
    for restricao, expressao in regras.get("verificacoes", {}).items():
        spark.sql(f"ALTER TABLE {tabela} ADD CONSTRAINT {restricao} CHECK ({expressao})")
    if regras.get("chave_primaria"):
        spark.sql(f"ALTER TABLE {tabela} ADD CONSTRAINT pk_{nome} PRIMARY KEY ({', '.join(regras['chave_primaria'])}) RELY")
