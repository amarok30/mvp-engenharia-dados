"""
Testes unitários das regras da Silver, com DataFrames de poucas linhas e saída esperada declarada.

Os testes importam as funções compartilhadas da Silver ou carregam definições dos notebooks 03 e 04.
As regras de transformação exercitadas são as mesmas executadas pelo pipeline. A validação local (`validacao_local.py`) é o teste de integração;
este arquivo prova as regras uma a uma, sem os dados reais.

Uso (da raiz do repositório, com o ambiente de .teste-local preparado):
    .teste-local/venv/bin/python -m pytest testes/test_silver.py -q
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "testes"))
import validacao_local as local  # noqa: E402
import silver_funcoes as silver  # noqa: E402

NB03 = REPO / "notebooks" / "03_silver_stackoverflow.py"
NB04 = REPO / "notebooks" / "04_silver_ibge.py"


def definicoes(caminho: Path, nomes: set[str]) -> dict:
    """Executa só as funções e constantes pedidas do notebook, com `F`, `Column` e `DataFrame` no escopo."""
    from pyspark.sql import Column, DataFrame
    from pyspark.sql import functions as F

    modulo = ast.parse(caminho.read_text(encoding="utf-8"))
    escolhidos = [
        no for no in modulo.body
        if (isinstance(no, ast.FunctionDef) and no.name in nomes)
        or (isinstance(no, ast.Assign) and any(isinstance(a, ast.Name) and a.id in nomes for a in no.targets))
    ]
    escopo = {"F": F, "Column": Column, "DataFrame": DataFrame, "__name__": "__teste__"}
    exec(compile(ast.Module(body=escolhidos, type_ignores=[]), str(caminho), "exec"), escopo)
    faltando = nomes - set(escopo)
    assert not faltando, f"definições não encontradas em {caminho.name}: {faltando}"
    return escopo


@pytest.fixture(scope="session")
def spark():
    local.configurar_java()
    os.environ.setdefault("VALIDACAO_NUCLEOS", "2")
    os.environ.setdefault("VALIDACAO_MEMORIA", "2g")
    sessao = local.criar_spark()
    yield sessao
    sessao.stop()


@pytest.fixture(scope="session")
def so():
    return definicoes(NB03, {"nulo_textual", "normalizar_unicode", "NULOS_TEXTUAIS", "MAPA_PORTE", "ANOS_CODANDO_MAX"})


@pytest.fixture(scope="session")
def regras():
    return {"conferir_regras": silver.conferir_regras}


@pytest.fixture(scope="session")
def ibge():
    return definicoes(NB04, {"sinal_ibge", "valor_numerico", "classificar_cv"})


# ---------------------------------------------------------------------------------------------------------------
# Notebook 03: Stack Overflow
# ---------------------------------------------------------------------------------------------------------------


def test_nulo_textual_trata_na_e_vazio_como_nulo(spark, so):
    from pyspark.sql import functions as F

    df = spark.createDataFrame([("NA",), ("",), ("  NA ",), ("Remote",), (None,)], ["v"])
    saida = [r[0] for r in df.select(so["nulo_textual"](F.col("v"))).collect()]
    assert saida == [None, None, None, "Remote", None]


def test_normalizar_unicode_troca_aspas_tipograficas(spark, so):
    from pyspark.sql import functions as F

    df = spark.createDataFrame([("I don’t know",), ("I don't know",), ("‘x’",)], ["v"])
    saida = [r[0] for r in df.select(so["normalizar_unicode"](F.col("v"))).collect()]
    assert saida == ["I don't know", "I don't know", "'x'"]


def test_regex_de_empregado_aceita_2025_e_multi_resposta(spark):
    # A regra do notebook: Employed como item único (2025) ou "Employed, ..." dentro de multi-resposta (2022 a 2024).
    from pyspark.sql import functions as F

    casos = [
        ("Employed", True),
        ("Employed, full-time", True),
        ("Independent contractor, freelancer, or self-employed;Employed, part-time", True),
        ("Student, full-time", False),
        ("Not employed, but looking for work", False),
        (None, False),
    ]
    df = spark.createDataFrame([(v,) for v, _ in casos], ["employment_n"])
    saida = [r[0] for r in df.select(silver.empregado(F.col("employment_n"))).collect()]
    assert saida == [esperado for _, esperado in casos]


def test_mapa_de_porte_funde_as_duas_menores_faixas_em_2025(so):
    mapa = so["MAPA_PORTE"]
    assert mapa["2 to 9 employees"] == mapa["Less than 20 employees"] == ("Menos de 20", 2)
    assert mapa["10 to 19 employees"][0] == "Menos de 20"
    nomes = {nome for nome, _ in mapa.values()}
    assert "10,000 or more employees" in mapa and mapa["10,000 or more employees"][0] == "10.000 ou mais"
    assert len(nomes) < len(mapa), "o mapa deve reduzir dez rótulos de origem a menos faixas canônicas"


def test_anos_codando_censura_pontas_e_valores_acima_de_50(spark, so):
    from pyspark.sql import functions as F

    maximo = so["ANOS_CODANDO_MAX"]
    assert maximo == 50
    df = spark.createDataFrame(
        [("Less than 1 year",), ("More than 50 years",), ("7",), ("63",), ("NA",), ("abc",), ("-1",), (None,)], ["years_code_n"]
    )
    saida = [r[0] for r in df.select(silver.anos_codando("years_code_n", maximo)).collect()]
    assert saida == [0, 50, 7, 50, None, None, None, None]


def test_crosswalk_versionado_tem_quinze_linhas_e_chave_unica():
    import csv

    with (REPO / "docs" / "mapa-de-para-arranjo.csv").open(encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert len(linhas) == 15
    chaves = [(l.get("safra"), l.get("valor_origem")) for l in linhas]
    assert len(chaves) == len(set(chaves)), "par (safra, valor_origem) repetido duplicaria linhas no JOIN"


def test_join_com_crosswalk_preserva_safra_nulos_e_valor_desconhecido(spark):
    from pyspark.sql import functions as F

    crosswalk = spark.createDataFrame(
        [(2024, "Your choice", "Flexível"), (2025, "Remote", "Remoto"), (None, None, "Não informado")],
        "safra INT, valor_origem STRING, valor_canonico STRING",
    )
    safras = spark.createDataFrame([(2024,), (2025,)], "safra INT")
    respostas = spark.createDataFrame(
        [(2024, "Your choice"), (2025, "Your choice"), (2025, "Remote"), (2025, None)],
        "safra INT, remote_work_n STRING",
    )
    juntas = silver.juntar_arranjo(respostas, silver.expandir_crosswalk(crosswalk, safras))
    resultados = {
        (r["safra"], r["remote_work_n"]): r["valor_canonico"]
        for r in juntas.select("r.safra", "remote_work_n", "valor_canonico").collect()
    }
    assert resultados == {
        (2024, "Your choice"): "Flexível", (2025, "Your choice"): None,
        (2025, "Remote"): "Remoto", (2025, None): "Não informado",
    }
    assert juntas.count() == respostas.count()


def test_autonomo_e_trabalhando_nao_confundem_desemprego(spark):
    from pyspark.sql import functions as F

    casos = [
        ("Independent contractor, freelancer, or self-employed", False, True, True),
        ("Employed;Independent contractor, freelancer, or self-employed", True, True, True),
        ("Not employed, and not looking for work", False, False, False),
        (None, False, False, False),
    ]
    df = spark.createDataFrame([(c[0],) for c in casos], "v STRING")
    e, a = silver.empregado(F.col("v")), silver.autonomo(F.col("v"))
    assert [tuple(r) for r in df.select(e, a, e | a).collect()] == [c[1:] for c in casos]


def test_conferir_regras_para_antes_de_gravar(spark, regras):
    regra = {
        "nao_nulas": ["safra"],
        "verificacoes": {"ck_safra": "safra IN (2022, 2023, 2024, 2025)"},
        "chave_primaria": ["safra", "resposta_id"],
    }
    boa = spark.createDataFrame([(2024, 1), (2025, 1)], "safra INT, resposta_id BIGINT")
    regras["conferir_regras"](boa, regra, "teste")  # não levanta erro
    for linhas, esperado in [
        ([(2021, 1)], "ck_safra"),
        ([(None, 1)], "nao_nulo_safra"),
        ([(2024, 1), (2024, 1)], "chave primária"),
    ]:
        ruim = spark.createDataFrame(linhas, "safra INT, resposta_id BIGINT")
        with pytest.raises(AssertionError, match=esperado):
            regras["conferir_regras"](ruim, regra, "teste")


# ---------------------------------------------------------------------------------------------------------------
# Notebook 04: IBGE
# ---------------------------------------------------------------------------------------------------------------


def test_sinais_convencionais_do_ibge(spark, ibge):
    df = spark.createDataFrame([("-",), ("..",), ("...",), ("x",), ("X",), ("12,5",), ("0",), ("abc",)], ["V"])
    sinais = [r[0] for r in df.select(ibge["sinal_ibge"]()).collect()]
    valores = [r[0] for r in df.select(ibge["valor_numerico"]()).collect()]
    assert sinais == ["-", "..", "...", "x", "x", None, None, "outro"]
    assert valores == [0.0, None, None, None, None, 12.5, 0.0, None]


def test_faixas_de_cv_sao_as_seis_declaradas(spark, ibge):
    from pyspark.sql import functions as F

    df = spark.createDataFrame([(None,), (0.0,), (5.0,), (5.1,), (15.0,), (15.1,), (30.0,), (30.1,), (50.0,), (50.1,)], ["cv"])
    saida = [r[0] for r in df.select(ibge["classificar_cv"](F.col("cv"))).collect()]
    assert saida == [None, "Exata", "Ótima", "Boa", "Boa", "Razoável", "Razoável", "Pouco precisa", "Pouco precisa", "Imprecisa"]


def test_magics_python_em_sql_sao_executadas(monkeypatch, tmp_path):
    caminho = tmp_path / "teste.sql"
    caminho.write_text("-- Databricks notebook source\n-- MAGIC %python\n-- MAGIC resultado = 7\n")
    monkeypatch.setattr(local, "PASTA_NOTEBOOKS", tmp_path)
    contexto = {}
    local.executar_notebook(None, caminho.name, contexto)
    assert contexto["resultado"] == 7
    assert local.codigo_celula("-- MAGIC %md\n-- MAGIC texto", ".sql") == ("md", "")
    with pytest.raises(ValueError, match="não suportada"):
        local.codigo_celula("# MAGIC %sh\n# MAGIC echo oi", ".py")


@pytest.mark.parametrize("divergente,c15,esperado", [(False, 3, 0), (True, 3, 1), (False, 0, 1)])
def test_validacao_retorna_falha_para_divergencia_ou_perda_c15(monkeypatch, tmp_path, divergente, c15, esperado):
    class Consulta:
        def __init__(self, valor):
            self.valor = valor

        def first(self):
            return [self.valor]

    class Sessao:
        def sql(self, consulta):
            return Consulta(c15 if "LIKE" in consulta else 32)

        def stop(self):
            pass

    monkeypatch.setattr(local, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(local, "RESULTADOS", tmp_path / "resultados")
    monkeypatch.setattr(local, "WAREHOUSE", tmp_path / "warehouse")
    monkeypatch.setattr(local, "configurar_java", lambda: None)
    monkeypatch.setattr(local, "montar_pouso", lambda: None)
    monkeypatch.setattr(local, "criar_spark", Sessao)
    monkeypatch.setattr(local, "executar_pipeline", lambda *args: {})
    monkeypatch.setattr(local, "salvar_resultados", lambda *args: None)
    digitais = iter([{"silver.t": [1, "1"]}, {"silver.t": [1, "2" if divergente else "1"]}])
    monkeypatch.setattr(local, "impressoes_digitais", lambda *args: next(digitais))
    monkeypatch.delenv("VALIDACAO_UMA_PASSADA", raising=False)
    assert local.main() == esperado
    import json
    relatorio = json.loads((local.RESULTADOS / "relatorio.json").read_text())
    assert relatorio["status"] == ("falha" if esperado else "ok")


def test_gravacao_silver_reexecuta_e_bloqueia_antes_de_sobrescrever(spark):
    from uuid import uuid4

    nome = f"teste_silver_{uuid4().hex}"
    tabela = f"default.{nome}"
    regras = {
        nome: {"nao_nulas": ["id"], "verificacoes": {"ck_id": "id > 0"}, "chave_primaria": ["id"]}
    }
    sessao = local.SparkLocal(spark)
    try:
        silver.gravar_silver(sessao, spark.createDataFrame([(1,), (2,)], "id INT"), tabela, regras)
        silver.gravar_silver(sessao, spark.createDataFrame([(3,)], "id INT"), tabela, regras)
        assert [r.id for r in spark.table(tabela).collect()] == [3]
        with pytest.raises(AssertionError, match="ck_id"):
            silver.gravar_silver(sessao, spark.createDataFrame([(-1,)], "id INT"), tabela, regras)
        assert [r.id for r in spark.table(tabela).collect()] == [3]
    finally:
        spark.sql(f"DROP TABLE IF EXISTS {tabela}")


def test_magic_pip_confere_dependencia_sem_instalar(monkeypatch, tmp_path):
    celula = "# MAGIC %pip install statsmodels==0.15.0 --quiet"
    monkeypatch.setattr(local.metadata, "version", lambda pacote: "0.15.0")
    assert local.codigo_celula(celula, ".py") == ("dependencia", "")
    caminho = tmp_path / "dependencia.py"
    caminho.write_text(celula)
    monkeypatch.setattr(local, "PASTA_NOTEBOOKS", tmp_path)
    local.executar_notebook(None, caminho.name, {})

    monkeypatch.setattr(local.metadata, "version", lambda pacote: "0.14.5")
    with pytest.raises(RuntimeError, match="versão instalada: 0.14.5"):
        local.codigo_celula(celula, ".py")

    def ausente(pacote):
        raise local.metadata.PackageNotFoundError(pacote)

    monkeypatch.setattr(local.metadata, "version", ausente)
    with pytest.raises(RuntimeError, match="Prepare o ambiente"):
        local.codigo_celula(celula, ".py")

    with pytest.raises(ValueError, match="não suportada"):
        local.codigo_celula("# MAGIC %pip install outro-pacote", ".py")
    with pytest.raises(ValueError, match="apenas a declaração"):
        local.codigo_celula(celula + "\n# MAGIC print(1)", ".py")
