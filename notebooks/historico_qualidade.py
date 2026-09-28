"""Persistência das verificações produzidas por uma etapa do pipeline."""

from uuid import uuid4

from pyspark.sql import functions as F


def persistir_historico(spark, verificacoes, job_run_id: str,
                       tabela: str = "mafia_office.gold.verificacoes_qualidade_historico") -> str:
    """Grava a tentativa mais recente de cada verificação no mesmo run.

    O DataFrame deve conter apenas resultados produzidos pela etapa atual.
    Verificações de etapas não executadas não são copiados da tabela de estado atual.
    Falhas anteriores à produção das verificações ficam no histórico do Jobs.
    """
    identificador = job_run_id.strip()
    if identificador in ("", "manual"):
        identificador = f"manual-{uuid4()}"
    if "{{" in identificador or "}}" in identificador:
        raise ValueError("job_run_id não foi resolvido pelo Jobs.")
    if not all(parte.isidentifier() for parte in tabela.split(".")):
        raise ValueError("Nome da tabela de histórico inválido.")

    verificacoes.withColumn("job_run_id", F.lit(identificador)).select(
        "job_run_id", *verificacoes.columns
    ).createOrReplaceTempView("_historico_etapa")

    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {tabela}
        USING DELTA AS SELECT * FROM _historico_etapa WHERE 1 = 0
    """)
    spark.sql(f"""
        MERGE INTO {tabela} AS t
        USING _historico_etapa AS s
        ON t.job_run_id = s.job_run_id AND t.verificacao_id = s.verificacao_id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)
    return identificador
