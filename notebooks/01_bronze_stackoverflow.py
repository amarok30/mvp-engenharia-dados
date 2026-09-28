# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Bronze: Stack Overflow Developer Survey
# MAGIC
# MAGIC **Lê:** `/Volumes/mafia_office/bronze/pouso/stackoverflow/{2022..2025}/results.csv` e `schema.csv`.
# MAGIC
# MAGIC **Escreve:** `bronze.so_pesquisa_2022`, `bronze.so_pesquisa_2023`, `bronze.so_pesquisa_2024`, `bronze.so_pesquisa_2025`
# MAGIC e `bronze.so_esquema`.
# MAGIC
# MAGIC **Por quê:** a Bronze guarda o dado como a fonte entregou. Todas as colunas são `STRING` e nada é descartado ou
# MAGIC corrigido. Se a Silver errar, dá para refazer sem baixar de novo.
# MAGIC
# MAGIC O schema é montado a partir da primeira linha do arquivo, sem inferência automática.
# MAGIC Uma passagem adicional pelo CSV mede o perfil por atributo. A carga preserva todas as respostas.
# MAGIC
# MAGIC O notebook para se o tamanho do arquivo, o número de colunas ou o número de linhas de uma safra não bate. O teste
# MAGIC de tamanho pega o ponteiro de 134 bytes do Git LFS.
# MAGIC
# MAGIC Cada tabela é recriada com `CREATE OR REPLACE TABLE ... AS SELECT`. Rodar de novo gera o mesmo conteúdo; só
# MAGIC `_ingerido_em` e `_lote_id` mudam.
# MAGIC
# MAGIC Decisões:
# MAGIC - Colunas com espaço no nome (`OpSysPersonal use`, `AIToolCurrently Using`) ficam como estão, com
# MAGIC   `delta.columnMapping.mode = 'name'`. Renomear já seria corrigir na Bronze.
# MAGIC - A carga usa `CREATE OR REPLACE TABLE` porque o column mapping precisa ser declarado na
# MAGIC   criação da tabela.
# MAGIC - O texto `NA` do CSV fica como `NA`. A conversão para nulo é feita na Silver.

# COMMAND ----------

import csv
import json
from pathlib import Path
from perfil_captura import perfil_csv
import os
import re
import uuid
from datetime import datetime, timezone

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

CATALOGO = "mafia_office"
LANDING_SO = "/Volumes/mafia_office/bronze/pouso/stackoverflow"
SISTEMA_ORIGEM = "stackoverflow_survey"
TAMANHO_PONTEIRO_LFS = 134

# Medido no dado real em 13/09/2026. Divergência = arquivo errado ou erro de leitura.
SAFRAS_ESPERADAS = {
    2022: {"bytes": 108_829_270, "linhas": 73_268, "colunas": 79},
    2023: {"bytes": 158_626_799, "linhas": 89_184, "colunas": 84},
    2024: {"bytes": 159_525_875, "linhas": 65_437, "colunas": 114},
    2025: {"bytes": 140_893_245, "linhas": 49_191, "colunas": 172},
}

# Colunas que a Stack Overflow acrescenta ao arquivo e que não são perguntas do questionário.
COLUNAS_SEM_PERGUNTA = {
    "ResponseId": "Identificador da resposta dentro da safra, criado pela Stack Overflow. Único na safra e repetido entre safras. Texto como veio da fonte.",
    "ConvertedCompYearly": "Remuneração anual convertida para dólar pela própria Stack Overflow, com o câmbio da safra. Texto como veio da fonte (NA quando em branco).",
}

# O perfil é calculado sobre a captura, sem alterar os valores da Bronze.
PERFIS_CAPTURA = {}
PASTA_PERFIS = Path(LANDING_SO).parent / "exportacao" / "perfil-captura"
PASTA_PERFIS.mkdir(parents=True, exist_ok=True)


def dominio_da_coluna(coluna: str, safra: int) -> str:
    dominio = PERFIS_CAPTURA[safra][coluna]["dominio"]
    return f" Domínio: {dominio} Linhagem: coluna {coluna} do results.csv {safra}, sem transformação."

# Comentário das colunas de auditoria, iguais em todas as tabelas Bronze.
COMENTARIOS_AUDITORIA = {
    "_sistema_origem": "Sistema de origem do registro. Domínio: stackoverflow_survey ou ibge_sidra. Linhagem: constante da carga.",
    "_ingerido_em": "Momento em que o registro foi gravado na Bronze. Domínio: data e hora UTC da carga. Linhagem: current_timestamp() da carga.",
    "_arquivo_origem": "Arquivo do Volume (ou URL da API) de onde o registro veio. Domínio: caminho em /Volumes/mafia_office/bronze/pouso ou URL do SIDRA. Linhagem: parâmetro da carga.",
    "_lote_id": "Identificador da execução que gravou o registro. Domínio: lote_AAAAMMDDTHHMMSSZ seguido de 8 caracteres. Linhagem: gerado no início do notebook.",
    "_safra": "Ano da edição da pesquisa (nulo na tabela 5434 do IBGE, que é uma série). Domínio: 2022 a 2025 ou nulo. Linhagem: parâmetro da carga.",
}

# Um identificador por execução, legível e ordenável.
LOTE_ID = f"lote_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:8]}"
print(f"Lote desta execução: {LOTE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Funções de apoio

# COMMAND ----------


def validar_arquivo(caminho: str, bytes_esperados: int | None) -> None:
    """Interrompe a execução se o arquivo não existe, é o ponteiro do Git LFS ou tem tamanho diferente do medido."""
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo não encontrado no Volume: {caminho}. Faça o upload antes de rodar.")
    tamanho = os.path.getsize(caminho)
    if tamanho == TAMANHO_PONTEIRO_LFS:
        raise ValueError(
            f"{caminho} tem {TAMANHO_PONTEIRO_LFS} bytes: é o ponteiro do Git LFS, não o dado. "
            "Baixe de media.githubusercontent.com (ver scripts/baixar_fontes.sh)."
        )
    if bytes_esperados is not None and tamanho != bytes_esperados:
        raise ValueError(f"{caminho} tem {tamanho} bytes; esperado {bytes_esperados}.")


def ler_cabecalho(caminho: str) -> list[str]:
    """Lê só a primeira linha do CSV. utf-8-sig remove um eventual BOM do primeiro nome de coluna."""
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        return next(csv.reader(arquivo))


def schema_todo_string(colunas: list[str], caminho: str, comentarios: dict[str, str] | None = None) -> StructType:
    """Schema explícito, todas as colunas STRING. Falha se houver nome repetido (Delta não diferencia caixa).

    O comentário de cada coluna vai no metadado do campo e é gravado junto com a tabela, na mesma escrita.
    """
    vistos: dict[str, str] = {}
    for coluna in colunas:
        chave = coluna.lower()
        if chave in vistos:
            raise ValueError(f"{caminho}: colunas '{vistos[chave]}' e '{coluna}' colidem sem diferenciar caixa.")
        vistos[chave] = coluna
    comentarios = comentarios or {}
    return StructType(
        [
            StructField(coluna, StringType(), True, {"comment": comentarios[coluna]} if coluna in comentarios else {})
            for coluna in colunas
        ]
    )


def texto_limpo(texto: str) -> str:
    """Tira marcação HTML e espaços repetidos do texto da pergunta."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto or "")).strip()


def comentarios_da_pesquisa(safra: int, colunas: list[str]) -> dict[str, str]:
    """Comentário em português para cada coluna do results.csv, a partir do schema.csv da mesma safra.

    Três casos, medidos no dado real: a coluna tem o mesmo nome de uma pergunta (qname); a coluna é um item de uma
    pergunta e começa com o qname dela (por exemplo LanguageHaveWorkedWith, da pergunta Language); ou a coluna foi
    criada pela própria Stack Overflow e não está no schema.csv (ResponseId e ConvertedCompYearly).
    """
    with open(f"{LANDING_SO}/{safra}/schema.csv", encoding="utf-8-sig", newline="") as arquivo:
        perguntas = {linha["qname"]: texto_limpo(linha["question"]) for linha in csv.DictReader(arquivo) if linha.get("qname")}
    comentarios = {}
    for coluna in colunas:
        if coluna in COLUNAS_SEM_PERGUNTA:
            comentarios[coluna] = COLUNAS_SEM_PERGUNTA[coluna] + dominio_da_coluna(coluna, safra)
            continue
        if coluna in perguntas:
            qname, relacao = coluna, "Resposta à pergunta"
        else:
            candidatos = [q for q in perguntas if len(q) > 2 and coluna.startswith(q)]
            if not candidatos:
                comentarios[coluna] = (
                    f"Coluna do results.csv de {safra} sem pergunta correspondente no schema.csv. Texto como veio da fonte."
                    + dominio_da_coluna(coluna, safra)
                )
                continue
            qname, relacao = max(candidatos, key=len), "Item ou variação da pergunta"
        comentarios[coluna] = (
            f"{relacao} {qname} da pesquisa {safra}, texto como veio da fonte (NA quando em branco). "
            f"Texto original da pergunta: {perguntas[qname][:600]}"
            + dominio_da_coluna(coluna, safra)
        )
    return comentarios


def ler_csv_bruto(caminho: str, schema: StructType) -> DataFrame:
    """Uma leitura por arquivo. multiLine e escape são obrigatórios: respostas livres têm vírgula, aspas e quebra."""
    return (
        spark.read.format("csv")
        .schema(schema)
        .option("header", "true")
        .option("multiLine", "true")
        .option("quote", '"')
        .option("escape", '"')
        .option("encoding", "UTF-8")
        .load(caminho)
    )


def com_auditoria(df: DataFrame, arquivo_origem: str, safra: int) -> DataFrame:
    valores = {
        "_sistema_origem": F.lit(SISTEMA_ORIGEM),
        "_ingerido_em": F.current_timestamp(),
        "_arquivo_origem": F.lit(arquivo_origem),
        "_lote_id": F.lit(LOTE_ID),
        "_safra": F.lit(safra).cast("int"),
    }
    return df.select(
        "*", *[valor.alias(nome, metadata={"comment": COMENTARIOS_AUDITORIA[nome]}) for nome, valor in valores.items()]
    )


def gravar_bronze(df: DataFrame, tabela: str, comentario: str) -> None:
    """CREATE OR REPLACE com column mapping por nome, para aceitar nomes de coluna com espaço."""
    visao = f"_bronze_{tabela.split('.')[-1]}"
    df.createOrReplaceTempView(visao)
    comentario_sql = comentario.replace("'", "\\'")
    spark.sql(
        f"""
        CREATE OR REPLACE TABLE {tabela}
        TBLPROPERTIES (
          'delta.columnMapping.mode' = 'name',
          'delta.minReaderVersion' = '2',
          'delta.minWriterVersion' = '5'
        )
        COMMENT '{comentario_sql}'
        AS SELECT * FROM {visao}
        """
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Quatro safras de `results.csv`

# COMMAND ----------

resumo_carga = []

for safra, esperado in SAFRAS_ESPERADAS.items():
    caminho = f"{LANDING_SO}/{safra}/results.csv"
    validar_arquivo(caminho, esperado["bytes"])

    colunas = ler_cabecalho(caminho)
    if len(colunas) != esperado["colunas"]:
        raise ValueError(f"{safra}: {len(colunas)} colunas no cabeçalho; esperado {esperado['colunas']}.")

    PERFIS_CAPTURA[safra] = perfil_csv(caminho, colunas)
    (PASTA_PERFIS / f"so_pesquisa_{safra}.json").write_text(
        json.dumps(PERFIS_CAPTURA[safra], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    schema = schema_todo_string(colunas, caminho, comentarios_da_pesquisa(safra, colunas))
    df = com_auditoria(ler_csv_bruto(caminho, schema), caminho, safra)
    tabela = f"{CATALOGO}.bronze.so_pesquisa_{safra}"
    gravar_bronze(
        df,
        tabela,
        f"Stack Overflow Developer Survey {safra}, results.csv fiel à fonte: {esperado['colunas']} colunas STRING "
        f"mais 5 de auditoria. Origem: {caminho}. Nada convertido, descartado ou corrigido.",
    )

    # Contagem feita na tabela Delta gravada, não no CSV: é a tabela que o resto do pipeline usa.
    linhas = spark.table(tabela).count()
    if linhas != esperado["linhas"]:
        raise ValueError(
            f"{tabela}: {linhas} linhas; esperado {esperado['linhas']}. "
            "Causa provável: leitura sem multiLine/escape ou arquivo diferente do medido."
        )
    resumo_carga.append((tabela, safra, esperado["colunas"], linhas))
    print(f"ok: {tabela} com {linhas} linhas e {esperado['colunas']} colunas de dado")

total = sum(item[3] for item in resumo_carga)
if total != 277_080:
    raise ValueError(f"Total de linhas {total}; esperado 277080.")
print(f"Total das quatro safras: {total}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## `schema.csv` das quatro safras, unificado
# MAGIC
# MAGIC Em 2022 a 2024 as colunas são `qid, qname, question, force_resp, type, selector`. Em 2025 mudaram para
# MAGIC `qid, qname, question, type, sub, sq_id`. Uno por nome, e a coluna que falta numa safra entra nula.

# COMMAND ----------

COMENTARIOS_SCHEMA_CSV = {
    "qid": "Identificador interno da pergunta no questionário. Texto como veio da fonte. Domínio: códigos QID da safra. Linhagem: coluna qid do schema.csv, sem transformação.",
    "qname": "Nome da pergunta, que dá nome à coluna (ou ao prefixo das colunas) do results.csv. Texto como veio da fonte. Domínio: identificador sem espaço. Linhagem: coluna qname do schema.csv, sem transformação.",
    "question": "Texto da pergunta, em inglês, como veio da fonte. Domínio: texto livre, com marcação HTML. Linhagem: coluna question do schema.csv, sem transformação.",
    "force_resp": "Indica se a resposta era obrigatória. Só existe de 2022 a 2024. Texto como veio da fonte. Domínio: TRUE, FALSE ou nulo em 2025. Linhagem: coluna force_resp do schema.csv.",
    "type": "Tipo da pergunta no questionário. Texto como veio da fonte. Domínio: códigos de tipo da safra (MC, TE e outros). Linhagem: coluna type do schema.csv.",
    "selector": "Tipo de seletor da pergunta. Só existe de 2022 a 2024. Texto como veio da fonte. Domínio: códigos de seletor ou nulo em 2025. Linhagem: coluna selector do schema.csv.",
    "sub": "Subitem da pergunta. Só existe em 2025. Texto como veio da fonte. Domínio: texto livre ou nulo de 2022 a 2024. Linhagem: coluna sub do schema.csv 2025.",
    "sq_id": "Identificador do subitem da pergunta. Só existe em 2025. Texto como veio da fonte. Domínio: código numérico em texto ou nulo de 2022 a 2024. Linhagem: coluna sq_id do schema.csv 2025.",
}

partes_schema = []
for safra in SAFRAS_ESPERADAS:
    caminho = f"{LANDING_SO}/{safra}/schema.csv"
    validar_arquivo(caminho, bytes_esperados=None)
    colunas = ler_cabecalho(caminho)
    schema = schema_todo_string(colunas, caminho, COMENTARIOS_SCHEMA_CSV)
    partes_schema.append(com_auditoria(ler_csv_bruto(caminho, schema), caminho, safra))

so_esquema = partes_schema[0]
for parte in partes_schema[1:]:
    so_esquema = so_esquema.unionByName(parte, allowMissingColumns=True)

# A união por nome cria as colunas que faltam numa safra sem o comentário. Reaplica o comentário em todas.
comentarios_esquema = {**COMENTARIOS_SCHEMA_CSV, **COMENTARIOS_AUDITORIA}
so_esquema = so_esquema.select(
    *[F.col(f"`{c}`").alias(c, metadata={"comment": comentarios_esquema[c]}) for c in so_esquema.columns]
)

gravar_bronze(
    so_esquema,
    f"{CATALOGO}.bronze.so_esquema",
    "União dos schema.csv das quatro safras da Stack Overflow Developer Survey. Colunas ausentes numa safra ficam "
    "nulas (2022 a 2024: force_resp, selector; 2025: sub, sq_id). Valores fiéis à fonte.",
)

# Contagem sem valor de referência: só registrada, não validada.
print("Linhas por safra em bronze.so_esquema (registradas, sem valor de referência):")
for linha in (
    spark.table(f"{CATALOGO}.bronze.so_esquema").groupBy("_safra").count().orderBy("_safra").collect()
):
    print(f"  {linha['_safra']}: {linha['count']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidência de carga
# MAGIC

# COMMAND ----------

# Tabela de 4 linhas: display aqui não varre dado.
display(spark.createDataFrame(resumo_carga, "tabela STRING, safra INT, colunas_dado INT, linhas BIGINT"))
