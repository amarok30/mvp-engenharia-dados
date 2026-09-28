"""
Validação local do pipeline, fora do Databricks.

Executa os notebooks 00 a 10 sobre os arquivos reais baixados por scripts/baixar_fontes.sh, com Spark e Delta Lake
locais, SEM alterar o código dos notebooks. Só traduz o que é exclusivo do Databricks:

- catálogo Unity Catalog `mafia_office` → `spark_catalog`;
- Volume `/Volumes/mafia_office/bronze/pouso` → pasta local `.teste-local/pouso`, montada com links para `dados/`;
- `USE CATALOG`, `CREATE CATALOG`, `CREATE VOLUME`, `SHOW VOLUMES` → ignorados;
- `COMMENT ON COLUMN c.s.t.col IS '...'` → `ALTER TABLE s.t ALTER COLUMN col COMMENT '...'`;
- `information_schema.tables/columns` → views temporárias montadas do catálogo local (ordinal_position a partir de 0);
- `dbutils.widgets` e `display` → substitutos mínimos;
- chave primária, chave estrangeira e tags (`ADD CONSTRAINT pk_`/`fk_`, `SET TAGS`) → ignoradas, porque só existem no
  Unity Catalog. NOT NULL e CHECK rodam de verdade, porque o Delta aberto também as aplica.

Células %python e %sql são executadas; %md é ignorada. A instalação declarada de statsmodels apenas
confere a versão já instalada no ambiente local. Outras magics interrompem a validação.
Os testes locais não validam permissões, tags, PK/FK informativas nem execução do job no Unity Catalog.
ANSI ligado e Delta como formato padrão.

Testes feitos:
1. transformações e validações dos notebooks (contagens, crosswalk, totais do IBGE, checks);
2. segunda execução completa e comparação de impressão digital (contagem e hash) de todas as tabelas Silver e Gold:
   idempotência;
3. notebook 05 executado de novo depois do 07: as linhas C15 precisam continuar em gold.verificacoes_qualidade.

Uso (da raiz do repositório, com o ambiente de .teste-local preparado):
    .teste-local/venv/bin/python testes/validacao_local.py
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import shlex
import sys
import time
import traceback
import uuid
from contextlib import redirect_stdout
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("VALIDACAO_BASE", REPO / ".teste-local")).resolve()
LANDING = BASE / "pouso"
LOGS = BASE / "logs"
RESULTADOS = BASE / "resultados"
WAREHOUSE = BASE / "warehouse"
# Pasta dos notebooks e catálogo usado neles (dá para validar uma cópia com outro catálogo).
PASTA_NOTEBOOKS = Path(os.environ.get("VALIDACAO_NOTEBOOKS", REPO / "notebooks")).resolve()
sys.path.insert(0, str(PASTA_NOTEBOOKS))
CATALOGO_NOTEBOOKS = os.environ.get("VALIDACAO_CATALOGO", "mafia_office")
NOTEBOOKS = [
    "00_setup_catalogo.sql",
    "01_bronze_stackoverflow.py",
    "02_bronze_ibge.py",
    "03_silver_stackoverflow.py",
    "04_silver_ibge.py",
    "05_qualidade_dados.py",
    "05b_qualidade_por_atributo.py",
    "06_gold_dimensoes.sql",
    "07_gold_fatos.sql",
    "08_analise_perguntas.sql",
    "08b_analise_modelo.py",
    "09_catalogo_comentarios.sql",
    "10_gerar_catalogo_markdown.py",
]
LINHAS_EXIBIDAS = 60


# ---------------------------------------------------------------------------------------------------------------
# Ambiente
# ---------------------------------------------------------------------------------------------------------------


def configurar_java() -> None:
    # JAVA_HOME já definido (por exemplo no CI) tem prioridade; senão usa o JDK preparado em .teste-local/jdk.
    if not os.environ.get("JAVA_HOME"):
        candidatos = sorted((BASE / "jdk").glob("*/Contents/Home"))
        if not candidatos:
            sys.exit("JDK não encontrado em .teste-local/jdk e JAVA_HOME não definido. Prepare o ambiente antes.")
        os.environ["JAVA_HOME"] = str(candidatos[0])
        os.environ["PATH"] = f"{candidatos[0] / 'bin'}:{os.environ['PATH']}"
    os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"
    # Driver e workers no mesmo Python do venv (sem isso o worker usa o python3 do sistema).
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


def montar_pouso() -> None:
    if LANDING.exists():
        shutil.rmtree(LANDING)
    for ano in (2022, 2023, 2024, 2025):
        destino = LANDING / "stackoverflow" / str(ano)
        destino.mkdir(parents=True)
        for nome in ("results.csv", "schema.csv"):
            (destino / nome).symlink_to(REPO / "dados" / "stackoverflow" / str(ano) / nome)
    (LANDING / "ibge").mkdir(parents=True)
    for nome in ("sidra_9471.json", "sidra_5434.json"):
        (LANDING / "ibge" / nome).symlink_to(REPO / "dados" / "ibge" / nome)
    (LANDING / "referencia").mkdir(parents=True)
    shutil.copy(REPO / "docs" / "mapa-de-para-arranjo.csv", LANDING / "referencia" / "mapa-de-para-arranjo.csv")
    # export/ não é criado de propósito: o notebook 10 precisa criá-lo.


def criar_spark():
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    construtor = (
        SparkSession.builder.master(f"local[{os.environ.get('VALIDACAO_NUCLEOS', '6')}]")
        .appName("mvp-validacao-local")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", str(WAREHOUSE))
        .config("spark.local.dir", str(BASE / "spark-tmp"))
        .config("spark.jars.ivy", os.environ.get("VALIDACAO_IVY", str(BASE / "ivy")))
        .config("spark.driver.memory", os.environ.get("VALIDACAO_MEMORIA", "6g"))
        .config("spark.sql.ansi.enabled", "true")
        .config("spark.sql.sources.default", "delta")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.extraJavaOptions", shlex.join([f"-Dderby.system.home={BASE}", f"-Djava.io.tmpdir={BASE / 'spark-tmp'}"]))
    )
    spark = configure_spark_with_delta_pip(construtor).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


class Widgets:
    def __init__(self) -> None:
        self.valores: dict[str, str] = {}

    def text(self, nome: str, padrao: str, rotulo: str | None = None) -> None:
        self.valores.setdefault(nome, padrao)

    def dropdown(self, nome: str, padrao: str, opcoes: list[str], rotulo: str | None = None) -> None:
        self.valores.setdefault(nome, padrao)

    def get(self, nome: str) -> str:
        return self.valores[nome]


class Dbutils:
    def __init__(self) -> None:
        self.widgets = Widgets()


def exibir(df) -> None:
    df.show(LINHAS_EXIBIDAS, truncate=160)


# ---------------------------------------------------------------------------------------------------------------
# information_schema emulado
# ---------------------------------------------------------------------------------------------------------------


def atualizar_information_schema(spark) -> None:
    tabelas, colunas = [], []
    for schema in ("bronze", "silver", "gold"):
        for tabela in spark.catalog.listTables(schema):
            if tabela.isTemporary:
                continue
            nome = f"{schema}.{tabela.name}"
            tipo = "VIEW" if tabela.tableType == "VIEW" else "MANAGED"
            comentario_tabela = None
            for linha in spark.sql(f"DESCRIBE TABLE EXTENDED {nome}").collect():
                if linha["col_name"] == "Comment":
                    comentario_tabela = linha["data_type"]
            if tipo == "VIEW":
                comentario_tabela = tabela.description or comentario_tabela
            tabelas.append((schema, tabela.name, tipo, comentario_tabela))
            posicao = 0
            for linha in spark.sql(f"DESCRIBE TABLE {nome}").collect():
                if not linha["col_name"] or linha["col_name"].startswith("#"):
                    break
                colunas.append((schema, tabela.name, linha["col_name"], posicao, linha["data_type"], "YES", linha["comment"]))
                posicao += 1
    spark.createDataFrame(
        tabelas, "table_schema STRING, table_name STRING, table_type STRING, comment STRING"
    ).createOrReplaceTempView("_is_tables")
    spark.createDataFrame(
        colunas,
        "table_schema STRING, table_name STRING, column_name STRING, ordinal_position INT, "
        "full_data_type STRING, is_nullable STRING, comment STRING",
    ).createOrReplaceTempView("_is_columns")


# ---------------------------------------------------------------------------------------------------------------
# Tradução e execução de células
# ---------------------------------------------------------------------------------------------------------------

RE_COMMENT_COLUMN = re.compile(r"^\s*COMMENT ON COLUMN\s+(\w+)\.(\w+)\.(\w+)\s+IS\s+", re.IGNORECASE)
IGNORAR_SQL = re.compile(r"^\s*(USE CATALOG|CREATE CATALOG|CREATE VOLUME|SHOW VOLUMES)\b", re.IGNORECASE)
# Recursos só do Unity Catalog, sem equivalente no Spark e no Delta de código aberto: chave primária e estrangeira
# (restrições informativas) e tags. NOT NULL e CHECK existem no Delta aberto e são executadas de verdade.
IGNORAR_UNITY_CATALOG = re.compile(
    r"^\s*ALTER\s+(TABLE|SCHEMA|VIEW|VOLUME)\s+\S+\s+(SET TAGS|ALTER\s+COLUMN\s+\S+\s+SET TAGS|ADD CONSTRAINT\s+(pk|fk)_\w+|DROP CONSTRAINT IF EXISTS\s+(pk|fk)_\w+)",
    re.IGNORECASE,
)


# O Delta aberto não muda uma coluna existente para NOT NULL. Localmente, a regra vira uma restrição CHECK equivalente,
# que confere as mesmas linhas; no Databricks roda o comando original.
RE_NOT_NULL = re.compile(r"^\s*ALTER\s+TABLE\s+(\S+)\s+ALTER\s+COLUMN\s+(\w+)\s+(SET|DROP)\s+NOT\s+NULL\s*;?\s*$", re.IGNORECASE)


def traduzir_not_null(spark, consulta: str) -> bool:
    m = RE_NOT_NULL.match(consulta)
    if not m:
        return False
    tabela, coluna, acao = m.group(1), m.group(2), m.group(3).upper()
    spark.sql(f"ALTER TABLE {tabela} DROP CONSTRAINT IF EXISTS nn_{coluna}")
    if acao == "SET":
        spark.sql(f"ALTER TABLE {tabela} ADD CONSTRAINT nn_{coluna} CHECK ({coluna} IS NOT NULL)")
    return True


class SparkLocal:
    """Repassa tudo para o SparkSession local, só ignorando em spark.sql o que é exclusivo do Unity Catalog."""

    def __init__(self, spark) -> None:
        self._spark = spark

    def sql(self, consulta: str, *args, **kwargs):
        consulta = traduzir_texto(consulta)
        if IGNORAR_UNITY_CATALOG.match(consulta):
            return self._spark.sql("SELECT 1 AS ignorado_fora_do_unity_catalog").limit(0)
        if traduzir_not_null(self._spark, consulta):
            return self._spark.sql("SELECT 1 AS traduzido").limit(0)
        return self._spark.sql(consulta, *args, **kwargs)

    def __getattr__(self, nome):
        return getattr(self._spark, nome)


def traduzir_texto(texto: str) -> str:
    texto = texto.replace(f"/Volumes/{CATALOGO_NOTEBOOKS}/bronze/pouso", str(LANDING))
    texto = texto.replace(f'CATALOGO = "{CATALOGO_NOTEBOOKS}"', 'CATALOGO = "spark_catalog"')
    texto = texto.replace("{CATALOGO}.information_schema.tables", "_is_tables")
    texto = texto.replace("{CATALOGO}.information_schema.columns", "_is_columns")
    texto = texto.replace(f"{CATALOGO_NOTEBOOKS}.information_schema.tables", "_is_tables")
    texto = texto.replace(f"{CATALOGO_NOTEBOOKS}.information_schema.columns", "_is_columns")
    texto = texto.replace(f"SHOW SCHEMAS IN {CATALOGO_NOTEBOOKS}", "SHOW SCHEMAS")
    texto = texto.replace(f"{CATALOGO_NOTEBOOKS}.", "spark_catalog.")
    return texto


def celulas(caminho: Path) -> list[str]:
    separador = "# COMMAND ----------" if caminho.suffix == ".py" else "-- COMMAND ----------"
    return caminho.read_text(encoding="utf-8").split(separador)


def sem_comentarios_sql(instrucao: str) -> str:
    return "\n".join(l for l in instrucao.splitlines() if not l.strip().startswith("--")).strip()


def executar_sql(spark, celula: str) -> None:
    import sqlparse

    for instrucao in sqlparse.split(traduzir_texto(celula)):
        codigo = sem_comentarios_sql(instrucao).rstrip(";").strip()
        if not codigo or IGNORAR_SQL.match(codigo) or IGNORAR_UNITY_CATALOG.match(codigo):
            continue
        if traduzir_not_null(spark, codigo):
            continue
        # COMMENT ON COLUMN schema.tabela.coluna IS '...'  →  ALTER TABLE schema.tabela ALTER COLUMN coluna COMMENT '...'
        codigo = RE_COMMENT_COLUMN.sub(lambda m: f"ALTER TABLE {m.group(1)}.{m.group(2)} ALTER COLUMN {m.group(3)} COMMENT ", codigo)
        if "_is_tables" in codigo or "_is_columns" in codigo:
            atualizar_information_schema(spark)
        resultado = spark.sql(codigo)
        # Toda instrução que devolve linhas é materializada: raise_error só dispara com ação.
        if resultado.columns:
            linhas = resultado.limit(LINHAS_EXIBIDAS + 1).collect()
            print(f"-- {len(linhas)} linha(s)")
            for linha in linhas[:LINHAS_EXIBIDAS]:
                print("   ", {k: (str(v)[:160] if v is not None else None) for k, v in linha.asDict().items()})


def codigo_celula(celula: str, sufixo: str) -> tuple[str, str]:
    """Identifica markdown, Python e SQL; rejeita magics sem tradução local."""
    prefixo = "# MAGIC" if sufixo == ".py" else "-- MAGIC"
    magics = [linha.split(prefixo, 1)[1].removeprefix(" ") for linha in celula.splitlines()
              if linha.lstrip().startswith(prefixo)]
    if magics:
        linguagem = next((linha.strip() for linha in magics if linha.strip()), "")
        if linguagem.startswith("%"):
            if linguagem == "%md":
                return "md", ""
            if linguagem == "%pip install statsmodels==0.15.0 --quiet":
                if sum(bool(linha.strip()) for linha in magics) != 1:
                    raise ValueError("A célula de dependência deve conter apenas a declaração autorizada.")
                try:
                    instalada = metadata.version("statsmodels")
                except metadata.PackageNotFoundError as erro:
                    raise RuntimeError(
                        "A validação local exige statsmodels==0.15.0. Prepare o ambiente antes da execução."
                    ) from erro
                if instalada != "0.15.0":
                    raise RuntimeError(
                        f"A validação local exige statsmodels==0.15.0; versão instalada: {instalada}."
                    )
                return "dependencia", ""
            if linguagem not in ("%python", "%sql"):
                raise ValueError(f"Magic não suportada na validação local: {linguagem}")
            indice = next(i for i, linha in enumerate(magics) if linha.strip() == linguagem)
            return linguagem[1:], "\n".join(magics[indice + 1:])
    return ("python" if sufixo == ".py" else "sql"), celula


def executar_notebook(spark, nome: str, contexto_py: dict) -> float:
    caminho = PASTA_NOTEBOOKS / nome
    inicio = time.time()
    contexto_py["__file__"] = str(caminho)
    for indice, celula in enumerate(celulas(caminho)):
        try:
            linguagem, codigo = codigo_celula(celula, caminho.suffix)
            if linguagem in ("md", "dependencia"):
                continue
            codigo = traduzir_texto(codigo)
            if linguagem == "python":
                if "_is_tables" in codigo or "_is_columns" in codigo:
                    atualizar_information_schema(spark)
                exec(compile(codigo, f"{nome}#celula{indice}", "exec"), contexto_py)
            else:
                executar_sql(spark, codigo)
        except Exception as erro:
            raise RuntimeError(
                f"{nome}, célula {indice}: {type(erro).__name__}: {str(erro)[:2500]}\n{celula[:1200]}"
            ) from erro
    return time.time() - inicio


def executar_pipeline(spark, rotulo: str, notebooks: list[str] = NOTEBOOKS) -> dict[str, float]:
    tempos = {}
    run_id = f"local-{uuid.uuid4()}"
    for nome in notebooks:
        contexto = {"spark": SparkLocal(spark), "dbutils": Dbutils(), "display": exibir, "__name__": "__notebook__"}
        contexto["dbutils"].widgets.valores["job_run_id"] = run_id
        log = LOGS / f"{rotulo}_{nome}.log"
        buffer = io.StringIO()
        print(f"[{rotulo}] {nome} ...", flush=True)
        try:
            with redirect_stdout(buffer):
                tempos[nome] = executar_notebook(spark, nome, contexto)
        finally:
            log.write_text(buffer.getvalue(), encoding="utf-8")
        print(f"[{rotulo}] {nome} ok em {tempos[nome]:.0f} s", flush=True)
    return tempos


# ---------------------------------------------------------------------------------------------------------------
# Verificações
# ---------------------------------------------------------------------------------------------------------------


def impressoes_digitais(spark) -> dict[str, list]:
    """Contagem e hash do conteúdo de cada tabela Silver e Gold, ignorando colunas de auditoria de tempo."""
    resultado = {}
    for schema in ("silver", "gold"):
        for tabela in spark.catalog.listTables(schema):
            # O histórico das verificações só cresce, por desenho: fica fora da comparação entre execuções.
            if tabela.tableType == "VIEW" or tabela.isTemporary or tabela.name.endswith("_historico"):
                continue
            nome = f"{schema}.{tabela.name}"
            colunas = [c for c in spark.table(nome).columns if not c.startswith("_") and c != "executado_em"]
            expr = ", ".join(f"`{c}`" for c in colunas)
            # DECIMAL(38,0): a soma de hashes de 64 bits estoura BIGINT com ANSI ligado.
            linha = spark.sql(f"SELECT COUNT(*) AS n, SUM(CAST(xxhash64({expr}) AS DECIMAL(38, 0))) AS h FROM {nome}").first()
            resultado[nome] = [linha["n"], str(linha["h"])]
    return resultado


def salvar_csv(df, caminho: Path) -> None:
    import csv

    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(df.columns)
        for linha in df.toLocalIterator():
            escritor.writerow(list(linha))


def salvar_resultados(spark) -> None:
    """Contagens por tabela, checks de qualidade e resultado das views, para conferência."""
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    contagens = [
        (schema, tabela.name, spark.table(f"{schema}.{tabela.name}").count())
        for schema in ("bronze", "silver", "gold")
        for tabela in spark.catalog.listTables(schema)
        if tabela.tableType != "VIEW" and not tabela.isTemporary
    ]
    (RESULTADOS / "contagens.json").write_text(json.dumps(contagens, ensure_ascii=False, indent=1), encoding="utf-8")
    salvar_csv(spark.table("gold.verificacoes_qualidade").orderBy("verificacao_id"), RESULTADOS / "verificacoes_qualidade.csv")
    for tabela in spark.catalog.listTables("gold"):
        if tabela.name.startswith("vw_"):
            salvar_csv(spark.table(f"gold.{tabela.name}"), RESULTADOS / f"{tabela.name}.csv")


def main() -> int:
    configurar_java()
    for pasta in (LOGS, RESULTADOS):
        pasta.mkdir(parents=True, exist_ok=True)
    if WAREHOUSE.exists():
        shutil.rmtree(WAREHOUSE)
    montar_pouso()
    spark = criar_spark()
    relatorio: dict = {}
    try:
        relatorio["execucao_1"] = executar_pipeline(spark, "exec1")
        digitais_1 = impressoes_digitais(spark)
        salvar_resultados(spark)
        if os.environ.get("VALIDACAO_UMA_PASSADA") == "1":
            relatorio["status"] = "uma passada"
            return 0

        relatorio["execucao_2"] = executar_pipeline(spark, "exec2")
        digitais_2 = impressoes_digitais(spark)
        divergentes = {t: (digitais_1.get(t), digitais_2.get(t)) for t in set(digitais_1) | set(digitais_2) if digitais_1.get(t) != digitais_2.get(t)}
        relatorio["idempotencia"] = {"tabelas_comparadas": len(digitais_1), "divergentes": divergentes}

        executar_pipeline(spark, "exec3_05_depois_do_07", ["05_qualidade_dados.py"])
        c15 = spark.sql("SELECT COUNT(*) FROM gold.verificacoes_qualidade WHERE verificacao_id LIKE 'C15%'").first()[0]
        total = spark.sql("SELECT COUNT(*) FROM gold.verificacoes_qualidade").first()[0]
        relatorio["merge_05_apos_07"] = {"linhas_c15": c15, "linhas_total": total}
        relatorio["impressoes_digitais"] = digitais_2
        relatorio["status"] = "ok" if not divergentes and c15 == 3 else "falha"
        return 0 if relatorio["status"] == "ok" else 1
    except Exception:
        relatorio["status"] = "erro"
        relatorio["erro"] = traceback.format_exc()[-4000:]
        raise
    finally:
        (RESULTADOS / "relatorio.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in relatorio.items() if k != "impressoes_digitais"}, ensure_ascii=False, indent=1))
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
