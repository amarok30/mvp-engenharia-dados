"""Testes do histórico em tabelas Delta temporárias, sem dados externos."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))
sys.path.insert(0, str(REPO / "testes"))

from historico_qualidade import persistir_historico
import validacao_local as local


@pytest.fixture(scope="module")
def spark_historico():
    local.configurar_java()
    sessao = local.criar_spark()
    yield sessao
    sessao.stop()


@pytest.fixture
def tabela(spark_historico):
    nome = f"default.teste_historico_{uuid4().hex}"
    yield nome
    spark_historico.sql(f"DROP TABLE IF EXISTS {nome}")


def resultados(spark, *linhas):
    return spark.createDataFrame(linhas, "verificacao_id STRING, resultado STRING")


def test_retry_substitui_sem_apagar_outra_etapa(spark_historico, tabela):
    spark = spark_historico
    persistir_historico(spark, resultados(spark, ("C01", "aprovado")), "run-1", tabela)
    persistir_historico(spark, resultados(spark, ("C15.1", "aprovado")), "run-1", tabela)
    persistir_historico(spark, resultados(spark, ("C01", "reprovado")), "run-1", tabela)

    obtido = {r.verificacao_id: r.resultado for r in spark.table(tabela).collect()}
    assert spark.table(tabela).count() == 2
    assert obtido == {"C01": "reprovado", "C15.1": "aprovado"}


def test_novo_run_contem_apenas_resultados_produzidos(spark_historico, tabela):
    spark = spark_historico
    persistir_historico(
        spark, resultados(spark, ("C01", "aprovado"), ("C15.1", "aprovado")), "anterior", tabela
    )
    persistir_historico(spark, resultados(spark, ("C01", "reprovado")), "atual", tabela)

    atual = spark.table(tabela).where("job_run_id = 'atual'").collect()
    assert len(atual) == 1
    assert atual[0].verificacao_id == "C01"
    assert atual[0].resultado == "reprovado"


def test_execucoes_manuais_nao_compartilham_identificador(spark_historico, tabela):
    spark = spark_historico
    primeiro = persistir_historico(spark, resultados(spark, ("C01", "aprovado")), "manual", tabela)
    segundo = persistir_historico(spark, resultados(spark, ("C01", "aprovado")), "manual", tabela)
    assert primeiro != segundo
    assert spark.table(tabela).select("job_run_id").distinct().count() == 2


def test_parametro_nao_resolvido_interrompe_antes_da_escrita():
    with pytest.raises(ValueError, match="não foi resolvido"):
        persistir_historico(None, None, "{{job.run_id}}")
