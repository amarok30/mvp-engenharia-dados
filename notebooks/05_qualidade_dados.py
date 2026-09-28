# Databricks notebook source
# MAGIC %md
# MAGIC # 05 · Qualidade de dados
# MAGIC
# MAGIC **Lê:** tabelas Bronze e Silver.
# MAGIC
# MAGIC **Escreve:** `gold.verificacoes_qualidade` e `gold.verificacoes_qualidade_historico`.
# MAGIC
# MAGIC **Por quê:** cada verificação tem um valor esperado, grava o resultado numa tabela e é classificada como
# MAGIC `problema_real` (defeito ou característica da fonte que muda a análise) ou `guarda_defensiva` (proteção contra
# MAGIC erro de código ou mudança futura da fonte).
# MAGIC
# MAGIC Duas colunas identificam a dimensão:
# MAGIC - `dimensao_qualidade`: completude, consistência, unicidade, acurácia e outliers, mais validade, integridade,
# MAGIC   estrutural e tempestividade.
# MAGIC - `dimensao_dama`: a dimensão, entre as seis primárias da DAMA UK, que de fato se aplica (Black e Van Nederpelt,
# MAGIC   2020). Por exemplo, a remuneração aparece em Acurácia na primeira coluna, mas a pesquisa não tem referência
# MAGIC   externa. O que dá para medir ali é Validade (valor dentro de uma faixa plausível).
# MAGIC
# MAGIC `valor_medido` segue o formato `medido: ... | esperado: ...`.
# MAGIC
# MAGIC Valores de `resultado`: `aprovado`, `reprovado`, `conferir` (precisa de leitura humana), `explicado` (diferença
# MAGIC conhecida), `medido` (sem valor esperado; o número é o achado) e `registrado` (fato documental).
# MAGIC
# MAGIC A C15 (contagem preservada nos fatos) só roda depois que a Gold existe, então fica no notebook 07. Os dois gravam
# MAGIC na mesma tabela com `MERGE` por `verificacao_id`, e cada um só remove linhas da própria camada.
# MAGIC
# MAGIC Depois de gravar tudo, o notebook para se faltar ou sobrar verificação, se algum resultado ou classificação sair
# MAGIC do domínio, se algo terminar `reprovado` ou se uma `guarda_defensiva` terminar `conferir`. O registro fica gravado
# MAGIC mesmo assim. O histórico recebe somente os resultados desta etapa, antes da validação final.
# MAGIC Execuções interrompidas antes de produzir resultados devem ser consultadas no Jobs.

# COMMAND ----------

from datetime import datetime, timezone
from functools import reduce

from historico_qualidade import persistir_historico

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

CATALOGO = "mafia_office"
SAFRAS = [2022, 2023, 2024, 2025]
NULOS_TEXTUAIS = ["", "NA"]
EXECUTADO_EM = datetime.now(timezone.utc)

dbutils.widgets.text("job_run_id", "manual", "Id da execução do job")
JOB_RUN_ID = dbutils.widgets.get("job_run_id")

verificações: list[dict] = []

# Tipo de regra de cada verificação:
# - regra: vale para qualquer carga, sem depender de um número medido (domínio, estrutura, chave, hierarquia);
# - referencia_externa: compara com um número publicado pela própria fonte (totais do IBGE, respostas da metodologia);
# - retrato_da_extracao: compara com os valores dos arquivos baixados em 13/09/2026. Funciona como teste de
#   regressão: se a fonte republicar o arquivo, "reprovado" quer dizer que o arquivo mudou.
TIPO_REGRA = {
    "C01": "retrato_da_extracao", "C02": "regra", "C03": "regra", "C04": "regra", "C05": "regra",
    "C06": "regra", "C07": "regra", "C08": "retrato_da_extracao", "C09": "regra", "C10": "regra",
    "C11": "retrato_da_extracao", "C12": "retrato_da_extracao", "C13": "regra", "C14": "referencia_externa",
    "C16": "referencia_externa", "C17": "regra", "C18": "regra", "C19": "regra", "C20": "regra", "C21": "regra",
    "C22": "regra", "C23": "regra", "C24": "regra", "C25": "regra", "C26": "regra", "C27": "regra", "C28": "regra",
    "C29": "regra", "C30": "regra",
}


def registrar(
    verificacao_id: str,
    camada: str,
    tabela: str,
    atributo: str,
    dimensao_qualidade: str,
    dimensao_dama: str,
    resultado: str,
    medido: str,
    esperado: str,
    linhas_afetadas: int | None,
    classificacao: str,
    severidade: str,
    tratamento: str,
) -> None:
    verificações.append(
        {
            "verificacao_id": verificacao_id,
            "camada": camada,
            "tabela": tabela,
            "atributo": atributo,
            "dimensao_qualidade": dimensao_qualidade,
            "dimensao_dama": dimensao_dama,
            "resultado": resultado,
            "valor_medido": f"medido: {medido} | esperado: {esperado}",
            "linhas_afetadas": None if linhas_afetadas is None else int(linhas_afetadas),
            "classificacao": classificacao,
            "tipo_regra": TIPO_REGRA[verificacao_id],
            "severidade": severidade,
            "tratamento": tratamento,
            "executado_em": EXECUTADO_EM,
        }
    )
    print(f"{verificacao_id} [{resultado}] {atributo}: {medido}")


def bronze_so(safra: int) -> DataFrame:
    return spark.table(f"{CATALOGO}.bronze.so_pesquisa_{safra}")


def preenchido(coluna: str) -> Column:
    c = F.col(f"`{coluna}`")
    return c.isNotNull() & ~F.trim(c).isin(NULOS_TEXTUAIS)


def por_safra(df: DataFrame, *agregacoes: Column) -> dict[int, dict]:
    return {linha["safra"]: linha.asDict() for linha in df.groupBy("safra").agg(*agregacoes).collect()}


respondente = spark.table(f"{CATALOGO}.silver.so_respondente")
tele = spark.table(f"{CATALOGO}.silver.ibge_teletrabalho_uf")
ocupados = spark.table(f"{CATALOGO}.silver.ibge_ocupados_uf_atividade")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Completude

# COMMAND ----------

# C01: nulos de RemoteWork sobre o total da safra.
PREENCHIDOS_REMOTE = {2022: 58_958, 2023: 73_810, 2024: 54_806, 2025: 33_780}
PCT_NULO_REMOTE = {2022: 19.5, 2023: 17.2, 2024: 16.2, 2025: 31.3}
INFORMADOS_TOTAL = 221_354

c01 = por_safra(
    respondente,
    F.count(F.lit(1)).alias("total"),
    F.sum((F.col("arranjo_trabalho") == "Não informado").cast("int")).alias("nulos"),
)
medido = {s: (c01[s]["total"] - c01[s]["nulos"], round(100 * c01[s]["nulos"] / c01[s]["total"], 1)) for s in SAFRAS}
base = sum(v[0] for v in medido.values())
ok = all(medido[s] == (PREENCHIDOS_REMOTE[s], PCT_NULO_REMOTE[s]) for s in SAFRAS) and base == INFORMADOS_TOTAL
registrar(
    "C01", "silver", "silver.so_respondente", "RemoteWork", "Completude", "Completude",
    "aprovado" if ok else "reprovado",
    f"(preenchidos, % nulo) por safra {medido}; informados nas quatro safras {base}",
    f"preenchidos {PREENCHIDOS_REMOTE}; % nulo {PCT_NULO_REMOTE}; informados nas quatro safras {INFORMADOS_TOTAL}",
    sum(c01[s]["nulos"] for s in SAFRAS),
    "problema_real", "alta",
    "Categoria Não informado, excluída dos percentuais. O salto de 2025 é achado, não erro.",
)

# COMMAND ----------

# C02: nulos de RemoteWork sobre quem trabalha (empregado ou autônomo), contra o total da safra (C01).
# Hipótese a partir do C01: o nulo se concentra em quem não trabalha, porque a pergunta de arranjo não se aplica a
# estudante, aposentado ou desempregado. O teste usa um limite fixo (NULO_TRABALHANDO_MAX_PCT entre quem trabalha), porque
# "menor que o total" passaria mesmo com metade dos nulos vindo de quem trabalha. O teste também exige empregados, autônomos
# e profissionais acima de zero em cada safra, para pegar mudança de rótulo em Employment ou MainBranch (aconteceu
# com Employment em 2025).
NULO_TRABALHANDO_MAX_PCT = 1.0
# 2025 muda o questionário (C05) e a não resposta entre quem trabalha foi medida em 19,8%: registrada, não aprovada.
SAFRAS_NAO_RESPOSTA_REGISTRADA = [2025]
nulo_arranjo = F.col("arranjo_trabalho") == "Não informado"
c02 = por_safra(
    respondente,
    F.count(F.lit(1)).alias("total"),
    F.sum(nulo_arranjo.cast("int")).alias("nulos"),
    F.sum(F.col("trabalhando").cast("int")).alias("trabalhando"),
    F.sum((F.col("trabalhando") & nulo_arranjo).cast("int")).alias("nulos_trabalhando"),
    F.sum((~F.col("trabalhando") & nulo_arranjo).cast("int")).alias("nulos_nao_trabalhando"),
    F.sum(F.col("empregado").cast("int")).alias("empregados"),
    F.sum(F.col("autonomo").cast("int")).alias("autonomos"),
    F.sum(F.col("e_profissional").cast("int")).alias("profissionais"),
)


def pct(parte: int, todo: int) -> float | None:
    return None if not todo else round(100 * parte / todo, 1)


medido = {
    s: {
        "% nulo no total": pct(c02[s]["nulos"], c02[s]["total"]),
        "% nulo entre quem trabalha": pct(c02[s]["nulos_trabalhando"], c02[s]["trabalhando"]),
        "% nulo entre quem não trabalha": pct(c02[s]["nulos_nao_trabalhando"], c02[s]["total"] - c02[s]["trabalhando"]),
        "empregados": c02[s]["empregados"],
        "autônomos (marcaram a opção)": c02[s]["autonomos"],
        "profissionais": c02[s]["profissionais"],
    }
    for s in SAFRAS
}
guarda_rotulos = all(c02[s]["empregados"] and c02[s]["autonomos"] and c02[s]["profissionais"] for s in SAFRAS)


def dentro_do_limite(s: int) -> bool:
    valor = medido[s]["% nulo entre quem trabalha"]
    return valor is not None and valor <= NULO_TRABALHANDO_MAX_PCT


hipotese = all(dentro_do_limite(s) for s in SAFRAS if s not in SAFRAS_NAO_RESPOSTA_REGISTRADA)
excecoes = [s for s in SAFRAS_NAO_RESPOSTA_REGISTRADA if not dentro_do_limite(s)]
if not (guarda_rotulos and hipotese):
    resultado_c02 = "reprovado"
elif excecoes:
    resultado_c02 = "medido"
else:
    resultado_c02 = "aprovado"
registrar(
    "C02", "silver", "silver.so_respondente", "RemoteWork (base: quem trabalha)", "Completude", "Completude",
    resultado_c02,
    str(medido),
    f"% nulo entre quem trabalha até {NULO_TRABALHANDO_MAX_PCT} nas safras fora de {SAFRAS_NAO_RESPOSTA_REGISTRADA}; "
    "empregados, autônomos e profissionais > 0",
    sum(c02[s]["nulos_trabalhando"] for s in SAFRAS),
    "problema_real", "alta",
    "Análises de arranjo usam a base trabalhando (empregado ou autônomo). De 2022 a 2024 o nulo é quase todo de quem "
    "não trabalha (não aplicabilidade). Em 2025 parte relevante de quem trabalha não informou o arranjo: não resposta "
    "real, de direção desconhecida, que limita a leitura da Q1 e da Q3 em 2025.",
)

# COMMAND ----------

# C03: JobSat ausente em 2022 e 2023 (ausência estrutural) e preenchimento em 2024 e 2025 (ausência real).
presenca = {s: "JobSat" in bronze_so(s).columns for s in SAFRAS}
c03 = por_safra(
    respondente,
    F.count(F.lit(1)).alias("total"),
    F.sum(F.col("satisfacao_trabalho").isNull().cast("int")).alias("nulos"),
)
pct_nulo = {s: pct(c03[s]["nulos"], c03[s]["total"]) for s in SAFRAS}
textos_jobsat = {
    linha["safra"]: (linha["texto_pergunta"] or "").strip()
    for linha in spark.table(f"{CATALOGO}.silver.so_metadados_pergunta")
    .filter((F.col("qname") == "JobSat") & F.col("presente_na_safra"))
    .collect()
}
ok = (
    presenca == {2022: False, 2023: False, 2024: True, 2025: True}
    and pct_nulo[2022] == 100
    and pct_nulo[2023] == 100
    and set(textos_jobsat) == {2024, 2025}
    and len(set(textos_jobsat.values())) == 1
)
registrar(
    "C03", "silver", "silver.so_respondente + silver.so_metadados_pergunta", "JobSat", "Completude", "Completude",
    "aprovado" if ok else "reprovado",
    f"coluna presente {presenca}; % nulo na Silver {pct_nulo}; safras com a pergunta no schema {sorted(textos_jobsat)}; "
    f"textos distintos {len(set(textos_jobsat.values()))}",
    "ausente e 100% nulo em 2022 e 2023; presente em 2024 e 2025 com o mesmo texto de pergunta",
    c03[2024]["nulos"] + c03[2025]["nulos"],
    "problema_real", "média",
    "Q5 restrita a 2024 e 2025, limite declarado. Nulo de 2022 e 2023 é estrutural; o de 2024 e 2025 é não resposta.",
)

# COMMAND ----------

# C04: YearsCodePro ausente em 2025.
presenca = {s: "YearsCodePro" in bronze_so(s).columns for s in SAFRAS}
ok = presenca == {2022: True, 2023: True, 2024: True, 2025: False}
registrar(
    "C04", "bronze", "bronze.so_pesquisa_{safra}", "YearsCodePro", "Completude", "Completude",
    "aprovado" if ok else "reprovado",
    f"coluna presente {presenca}", "presente em 2022 a 2024; ausente em 2025", None,
    "problema_real", "baixa",
    "Fora do núcleo harmonizado. anos_codando usa YearsCode, presente nas quatro safras.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Consistência

# COMMAND ----------

# C05: RemoteWork com texto de pergunta idêntico e opções diferentes entre safras.
OPCOES_REMOTE = {
    2022: {"Fully remote", "Hybrid (some remote, some in-person)", "Full in-person"},
    2023: {"Remote", "Hybrid (some remote, some in-person)", "In-person"},
    2024: {"Remote", "Hybrid (some remote, some in-person)", "In-person"},
    2025: {
        "Remote",
        "In-person",
        "Hybrid (some remote, leans heavy to in-person)",
        "Hybrid (some in-person, leans heavy to flexibility)",
        "Your choice (very flexible, you can come in when you want or just as needed)",
    },
}
TEXTO_PERGUNTA_REMOTE = "Which best describes your current work situation?"

opcoes = {s: set() for s in SAFRAS}
for linha in (
    respondente.filter(preenchido("arranjo_trabalho_origem")).select("safra", "arranjo_trabalho_origem").distinct().collect()
):
    opcoes[linha["safra"]].add(linha["arranjo_trabalho_origem"])

textos = {
    linha["safra"]: linha["texto_pergunta"]
    for linha in spark.table(f"{CATALOGO}.silver.so_metadados_pergunta")
    .filter((F.col("qname") == "RemoteWork") & F.col("presente_na_safra"))
    .collect()
}
textos_distintos = {(t or "").strip() for t in textos.values()}

if opcoes != OPCOES_REMOTE or len(textos_distintos) > 1:
    resultado = "reprovado"
elif set(textos) != set(SAFRAS):
    resultado = "conferir"  # qname ausente no schema.csv de alguma safra: a prova documental fica incompleta
else:
    resultado = "aprovado"

registrar(
    "C05", "silver", "silver.so_respondente + silver.so_metadados_pergunta", "RemoteWork", "Consistência", "Consistência",
    resultado,
    f"safras com a pergunta no schema {sorted(textos)}; textos distintos {len(textos_distintos)}; "
    f"igual ao texto de referência {textos_distintos == {TEXTO_PERGUNTA_REMOTE}}; "
    f"opções iguais às esperadas {opcoes == OPCOES_REMOTE}",
    f"um único texto ({TEXTO_PERGUNTA_REMOTE!r}); opções {{safra: conjunto}} conforme de-para",
    None,
    "problema_real", "alta",
    "Crosswalk por safra (docs/mapa-de-para-arranjo.csv), arranjo_trabalho_origem preservado e flag comparavel_serie.",
)

# COMMAND ----------

# C06: OrgSize com dez categorias em 2022 a 2024 e nove em 2025.
CATEGORIAS_ORGSIZE = {2022: 10, 2023: 10, 2024: 10, 2025: 9}
c06 = por_safra(
    respondente,
    F.countDistinct("porte_empresa_origem").alias("categorias"),
    F.sum((F.col("porte_empresa_origem").isNotNull() & F.col("porte_empresa").isNull()).cast("int")).alias("nao_mapeado"),
)
categorias = {s: c06[s]["categorias"] for s in SAFRAS}
nao_mapeado = sum(c06[s]["nao_mapeado"] for s in SAFRAS)
registrar(
    "C06", "silver", "silver.so_respondente", "OrgSize", "Consistência", "Consistência",
    "aprovado" if categorias == CATEGORIAS_ORGSIZE and nao_mapeado == 0 else "reprovado",
    f"categorias por safra {categorias}; rótulos sem mapeamento {nao_mapeado}",
    f"categorias {CATEGORIAS_ORGSIZE}; rótulos sem mapeamento 0",
    nao_mapeado,
    "problema_real", "média",
    "Faixa canônica Menos de 20 funde 2 to 9 e 10 to 19 (2022 a 2024) com Less than 20 (2025).",
)

# COMMAND ----------

# C07: apóstrofo tipográfico U+2019 em OrgSize.
bronze_2019 = {s: bronze_so(s).filter(F.col("OrgSize").contains("’")).count() for s in SAFRAS}
nao_sabe = por_safra(respondente, F.sum((F.col("porte_empresa") == "Não sabe").cast("int")).alias("n"))
nao_sabe = {s: nao_sabe[s]["n"] for s in SAFRAS}
restante_silver = respondente.filter(F.col("porte_empresa_origem").contains("’")).count()
registrar(
    "C07", "bronze", "bronze.so_pesquisa_{safra} → silver.so_respondente", "OrgSize (encoding)",
    "Consistência", "Consistência",
    "aprovado" if bronze_2019 == nao_sabe and restante_silver == 0 else "reprovado",
    f"linhas com U+2019 na Bronze {bronze_2019}; Não sabe na Silver {nao_sabe}; U+2019 restante na Silver {restante_silver}",
    "toda linha com U+2019 vira Não sabe; nenhum U+2019 na Silver",
    sum(bronze_2019.values()),
    "problema_real", "média",
    "Normalização Unicode na entrada da Silver (U+2018 e U+2019 para apóstrofo ASCII).",
)

# COMMAND ----------

# C08: Currency com separador TAB inconsistente.
# Base do valor de referência: Currency preenchido (não nulo, não NA) na safra 2024, onde 72,4% têm TAB (33.810 de
# 46.684, medido no arquivo real). As outras safras são só medidas e registradas.
SAFRA_REFERENCIA_TAB = 2024
PCT_TAB_REFERENCIA = 72.4
TOLERANCIA_PP = 0.05
REGEX_CURRENCY = r"^([A-Z]{3})[\s\t]+(.*)$"

por_ano, sem_coluna = {}, []
for s in SAFRAS:
    df = bronze_so(s)
    if "Currency" not in df.columns:
        sem_coluna.append(s)
        continue
    linha = df.filter(preenchido("Currency")).agg(
        F.count(F.lit(1)).alias("preenchidos"),
        F.sum(F.col("Currency").contains("\t").cast("int")).alias("com_tab"),
        F.sum((~F.col("Currency").rlike(REGEX_CURRENCY)).cast("int")).alias("fora_regex"),
    ).first()
    por_ano[s] = linha.asDict()

pct_tab_por_ano = {s: pct(v["com_tab"], v["preenchidos"]) for s, v in por_ano.items()}
pct_tab_referencia = pct_tab_por_ano.get(SAFRA_REFERENCIA_TAB)
fora_regex = sum(v["fora_regex"] for v in por_ano.values())
exemplos_fora = [
    linha[0]
    for s in por_ano
    for linha in bronze_so(s)
    .filter(preenchido("Currency") & ~F.col("Currency").rlike(REGEX_CURRENCY))
    .select("Currency").distinct().limit(5).collect()
]
registrar(
    "C08", "bronze", "bronze.so_pesquisa_{safra}", "Currency", "Consistência", "Validade",
    "aprovado" if pct_tab_referencia is not None and abs(pct_tab_referencia - PCT_TAB_REFERENCIA) <= TOLERANCIA_PP
    else "reprovado",
    f"% com TAB por safra {pct_tab_por_ano}; contagens {por_ano}; safras sem a coluna {sem_coluna}; "
    f"valores fora da regex {fora_regex} (exemplos {sorted(set(exemplos_fora))})",
    f"{PCT_TAB_REFERENCIA}% com TAB em {SAFRA_REFERENCIA_TAB}, sobre Currency preenchido",
    sum(v["preenchidos"] - v["com_tab"] for v in por_ano.values()),
    "problema_real", "baixa",
    "Regex tolerante ^([A-Z]{3})[\\s\\t]+(.*)$, nunca split por TAB. Valores fora da regex (código de moeda 'none' "
    "em minúsculas) ficam registrados; Currency não entra na Silver porque ConvertedCompYearly já vem em USD.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Unicidade

# COMMAND ----------

# C09: ResponseId único por safra e colidindo entre safras.
repetidos_na_safra = respondente.groupBy("safra", "resposta_id").count().filter("count > 1").count()
colisoes = respondente.groupBy("resposta_id").agg(F.countDistinct("safra").alias("safras")).filter("safras > 1").count()
registrar(
    "C09", "silver", "silver.so_respondente", "ResponseId", "Unicidade", "Unicidade",
    "aprovado" if repetidos_na_safra == 0 and colisoes > 0 else "reprovado",
    f"repetidos dentro da safra {repetidos_na_safra}; resposta_id presentes em mais de uma safra {colisoes}",
    "0 repetidos dentro da safra; colisões entre safras maior que 0 (prova de que a chave precisa da safra)",
    colisoes,
    "problema_real", "alta",
    "Chave composta (safra, resposta_id) na Silver e na Gold.",
)

# COMMAND ----------

# C10: registros SIDRA sem duplicata pela combinação de dimensões.
duplicatas = {}
for codigo in ["9471", "5434"]:
    bronze = spark.table(f"{CATALOGO}.bronze.ibge_sidra_{codigo}").filter(F.col("_ordem_registro") > 0)
    chaves = ["NC"] + sorted(c for c in bronze.columns if c.startswith("D") and c.endswith("C"))
    duplicatas[codigo] = bronze.groupBy(*chaves).count().filter("count > 1").count()
registrar(
    "C10", "bronze", "bronze.ibge_sidra_9471, bronze.ibge_sidra_5434", "território × classificação × período × variável",
    "Unicidade", "Unicidade",
    "aprovado" if sum(duplicatas.values()) == 0 else "reprovado",
    f"combinações repetidas {duplicatas}", "0 em cada tabela",
    sum(duplicatas.values()),
    "guarda_defensiva", "média",
    "Nenhum: a API devolve uma célula por combinação. A verificação protege o pivot da Silver, que usa first().",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Acurácia

# COMMAND ----------

# C11: ConvertedCompYearly 2024.
# Valores medidos no arquivo real em 13/09/2026 (o máximo exato é 16.256.603).
ESPERADO_COMP_2024 = {"minimo": 1.0, "maximo": 16_256_603.0, "mediana": 65_000.0, "media": 86_155.0}
linha = (
    respondente.filter((F.col("safra") == 2024) & F.col("remuneracao_usd").isNotNull())
    .agg(
        F.min("remuneracao_usd").alias("minimo"),
        F.max("remuneracao_usd").alias("maximo"),
        F.expr("percentile(remuneracao_usd, 0.5)").alias("mediana"),
        F.avg("remuneracao_usd").alias("media"),
        F.sum(F.col("remuneracao_outlier").cast("int")).alias("outliers"),
    )
    .first()
)
ok = (
    linha["minimo"] == ESPERADO_COMP_2024["minimo"]
    and linha["maximo"] == ESPERADO_COMP_2024["maximo"]
    and linha["mediana"] == ESPERADO_COMP_2024["mediana"]
    and abs(linha["media"] - ESPERADO_COMP_2024["media"]) < 1
)
registrar(
    "C11", "silver", "silver.so_respondente", "ConvertedCompYearly (2024)", "Acurácia", "Validade",
    "aprovado" if ok else "reprovado",
    f"mínimo {linha['minimo']}, máximo {linha['maximo']}, mediana {linha['mediana']}, média {round(linha['media'], 2)}",
    f"{ESPERADO_COMP_2024} (média com tolerância de 1 USD por arredondamento)",
    linha["outliers"],
    "problema_real", "alta",
    "Marcar fora de [1.000; 1.000.000] em remuneracao_outlier, sem apagar. Mediana sempre, nunca média. "
    "Dimensão DAMA é Validade: a pesquisa não tem referência externa, então acurácia não é mensurável.",
)

# COMMAND ----------

# C12: tamanho da subamostra brasileira.
N_BRASIL = {2022: 2_109, 2023: 2_042, 2024: 1_375, 2025: 825}
N_BRASIL_ARRANJO_2025 = 649
c12 = por_safra(
    respondente.filter("e_brasil"),
    F.count(F.lit(1)).alias("n"),
    F.sum((F.col("arranjo_trabalho") != "Não informado").cast("int")).alias("com_arranjo"),
)
n_brasil = {s: c12.get(s, {}).get("n", 0) for s in SAFRAS}
com_arranjo_2025 = c12.get(2025, {}).get("com_arranjo", 0)
registrar(
    "C12", "silver", "silver.so_respondente", "Country = Brazil", "Acurácia", "Não se aplica (limite amostral)",
    "aprovado" if n_brasil == N_BRASIL and com_arranjo_2025 == N_BRASIL_ARRANJO_2025 else "reprovado",
    f"n por safra {n_brasil}; com arranjo informado em 2025 {com_arranjo_2025}",
    f"n {N_BRASIL}; com arranjo em 2025 {N_BRASIL_ARRANJO_2025}",
    com_arranjo_2025,
    "problema_real", "alta",
    "Q3 só no agregado nacional; n visível em toda tabela e gráfico; nunca desagregar o Brasil por UF, porte ou perfil.",
)

# COMMAND ----------

# C13: precisão das estimativas por UF nas seis faixas de CV adotadas no projeto, para o percentual e para pessoas.
faixas_cv = {
    coluna: {
        linha[coluna]: linha["count"]
        for linha in tele.filter((F.col("nivel_territorial") == "uf") & F.col("disponivel_no_nivel")).groupBy(coluna).count().collect()
    }
    for coluna in ["cv_classificacao", "cv_pessoas_classificacao"]
}
extremos = tele.filter((F.col("nivel_territorial") == "uf") & F.col("disponivel_no_nivel")).agg(
    F.min("cv_percentual").alias("min_pct"), F.max("cv_percentual").alias("max_pct"),
    F.min("cv_pessoas").alias("min_pes"), F.max("cv_pessoas").alias("max_pes"),
).first()
nao_confiaveis = tele.filter(
    (F.col("nivel_territorial") == "uf") & F.col("disponivel_no_nivel") & ~F.col("estimativa_confiavel")
).count()
# CV máximo até 1 sugere unidade em fração, não em %: as faixas ficariam erradas.
unidade_suspeita = any(extremos[k] is not None and extremos[k] <= 1 for k in ["max_pct", "max_pes"])
registrar(
    "C13", "silver", "silver.ibge_teletrabalho_uf", "cv_percentual, cv_pessoas", "Acurácia",
    "Não se aplica (precisão amostral)",
    "conferir" if unidade_suspeita else "medido",
    f"linhas UF por faixa {faixas_cv}; CV do percentual de {extremos['min_pct']} a {extremos['max_pct']}; "
    f"CV de pessoas de {extremos['min_pes']} a {extremos['max_pes']}",
    "sem valor fixado; UFs pequenas com CV mais alto; CV em %",
    nao_confiaveis,
    "problema_real", "alta",
    "Faixas de CV adotadas no projeto, sobre o CV publicado pelo IBGE (convenção, não norma do IBGE). Razoável "
    "aparece com ressalva; Pouco precisa e Imprecisa não sustentam conclusão. CV mede precisão amostral (variância), "
    "não viés contra referência.",
)

# COMMAND ----------

# C14: validação externa, totais oficiais do Brasil em 2022 (mil pessoas).
TOTAIS_BRASIL_2022 = {"59803": 96_695, "59804": 9_462, "59805": 7_399}
obtidos = {
    linha["modalidade_codigo"]: linha["pessoas_mil"]
    for linha in tele.filter((F.col("nivel_territorial") == "pais") & F.col("modalidade_codigo").isin(list(TOTAIS_BRASIL_2022)))
    .select("modalidade_codigo", "pessoas_mil")
    .collect()
}
ok = all(obtidos.get(k) is not None and abs(obtidos[k] - v) <= 0.5 for k, v in TOTAIS_BRASIL_2022.items())
registrar(
    "C14", "silver", "silver.ibge_teletrabalho_uf", "pessoas_mil (Brasil)", "Acurácia", "Consistência",
    "aprovado" if ok else "reprovado",
    f"{obtidos}", f"{TOTAIS_BRASIL_2022} (Total, trabalho remoto, teletrabalho)", None,
    "guarda_defensiva", "alta",
    "Linha nacional publicada pela API do SIDRA (medida em 13/09/2026). O notebook 04 é interrompido se a Silver não "
    "reproduzir esses valores.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Integridade
# MAGIC
# MAGIC A verificação C15 (preservação de contagem nos fatos) é gravada pelo notebook 07.

# COMMAND ----------

# C16: reconciliação do microdado de 2025 com o número publicado na metodologia.
LINHAS_CSV_2025 = 49_191
RESPOSTAS_PUBLICADAS_2025 = 49_009
linhas_2025 = bronze_so(2025).count()
registrar(
    "C16", "bronze", "bronze.so_pesquisa_2025", "linhas do results.csv", "Integridade", "Consistência",
    "medido" if linhas_2025 == LINHAS_CSV_2025 else "reprovado",
    f"{linhas_2025} linhas no CSV; diferença para o publicado {linhas_2025 - RESPOSTAS_PUBLICADAS_2025}",
    f"{LINHAS_CSV_2025} no CSV × {RESPOSTAS_PUBLICADAS_2025} respostas publicadas (diferença 182)",
    linhas_2025 - RESPOSTAS_PUBLICADAS_2025,
    "problema_real", "baixa",
    "A metodologia de 2025 registra 49.009 respostas qualificadas e não explica a diferença para as linhas do CSV "
    "(docs/referencias.md §6.2). O pipeline usa as linhas do CSV e declara a diferença.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validade

# COMMAND ----------

# C17: domínio do arranjo de trabalho.
DOMINIO_ARRANJO = ["Remoto", "Híbrido", "Presencial", "Flexível", "Não informado"]
fora = respondente.filter(F.col("arranjo_trabalho").isNull() | ~F.col("arranjo_trabalho").isin(DOMINIO_ARRANJO)).count()
registrar(
    "C17", "silver", "silver.so_respondente", "arranjo_trabalho", "Validade", "Validade",
    "aprovado" if fora == 0 else "reprovado",
    f"{fora} linhas fora do domínio", f"0; domínio {DOMINIO_ARRANJO}", fora,
    "guarda_defensiva", "alta",
    "O JOIN com o de-para interrompe o notebook 03 antes de chegar aqui.",
)

# COMMAND ----------

# C18: percentuais do IBGE em [0, 100], CV e pessoas não negativos, e símbolos da API por tipo.
fora_faixa = tele.filter(
    ~F.col("percentual").between(0, 100) | (F.col("cv_percentual") < 0) | (F.col("cv_pessoas") < 0)
).count()
pessoas_negativas = tele.filter(F.col("pessoas_mil") < 0).count() + ocupados.filter(F.col("pessoas_mil") < 0).count()
simbolos = {}
for codigo in ["9471", "5434"]:
    simbolos[codigo] = {
        linha["V"]: linha["count"]
        for linha in spark.table(f"{CATALOGO}.bronze.ibge_sidra_{codigo}")
        .filter((F.col("_ordem_registro") > 0) & F.expr("try_cast(replace(V, ',', '.') AS DOUBLE) IS NULL"))
        .groupBy("V").count().collect()
    }
registrar(
    "C18", "silver", "silver.ibge_teletrabalho_uf, silver.ibge_ocupados_uf_atividade",
    "percentual, cv_percentual, cv_pessoas, pessoas_mil", "Validade", "Validade",
    "aprovado" if fora_faixa == 0 and pessoas_negativas == 0 else "reprovado",
    f"fora de faixa {fora_faixa}; pessoas negativas {pessoas_negativas}; símbolos na Bronze por tabela {simbolos}",
    "0 fora de faixa; 0 negativos; símbolos sem valor fixado",
    fora_faixa + pessoas_negativas,
    "guarda_defensiva", "média",
    "Sinais convencionais do IBGE (Normas de apresentação tabular): - vira 0; .., ... e x viram nulo com o sinal "
    "preservado em <medida>_sinal; qualquer outro texto interrompe o notebook 04.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Outliers

# COMMAND ----------

# C19: cauda da remuneração por safra.
c19 = por_safra(
    respondente.filter(F.col("remuneracao_usd").isNotNull()),
    F.count(F.lit(1)).alias("n"),
    F.sum((F.col("remuneracao_usd") < 1_000).cast("int")).alias("abaixo"),
    F.sum((F.col("remuneracao_usd") > 1_000_000).cast("int")).alias("acima"),
    F.expr("percentile(remuneracao_usd, 0.5)").alias("p50"),
    F.expr("percentile(remuneracao_usd, 0.99)").alias("p99"),
)
registrar(
    "C19", "silver", "silver.so_respondente", "remuneracao_usd", "Outliers", "Validade",
    "medido",
    str({s: {k: c19[s][k] for k in ["n", "abaixo", "acima", "p50", "p99"]} for s in SAFRAS if s in c19}),
    "sem valor fixado; cauda extrema à direita",
    sum(c19[s]["abaixo"] + c19[s]["acima"] for s in c19),
    "problema_real", "média",
    "Corte documentado [1.000; 1.000.000] USD, marcado e não removido. Boxplot por safra no notebook 08. "
    "Valores em câmbio da safra: não comparar entre anos sem ressalva.",
)

# COMMAND ----------

# C20: anos de código censurados nas pontas.
# 2022 a 2024 censuram em texto (Less than 1 year, More than 50 years); 2025 é numérico e sem teto (valores acima de
# 50 existem), então a Silver aplica o mesmo teto de 50 para manter as safras comparáveis.
c20 = {}
for s in SAFRAS:
    linha = bronze_so(s).agg(
        F.sum((F.col("YearsCode") == "Less than 1 year").cast("int")).alias("menos_de_1"),
        F.sum((F.col("YearsCode") == "More than 50 years").cast("int")).alias("mais_de_50_texto"),
        F.sum((F.expr("try_cast(YearsCode AS INT)") > 50).cast("int")).alias("acima_de_50_numerico"),
    ).first()
    c20[s] = linha.asDict()
nao_convertidos = respondente.filter(F.col("anos_codando").isNull()).count()
convertidos_errado = 0
for s in SAFRAS:
    preenchidos_bronze = bronze_so(s).filter(preenchido("YearsCode")).count()
    convertidos_silver = respondente.filter((F.col("safra") == s) & F.col("anos_codando").isNotNull()).count()
    convertidos_errado += preenchidos_bronze - convertidos_silver
registrar(
    "C20", "silver", "silver.so_respondente", "anos_codando", "Outliers", "Validade",
    "aprovado" if convertidos_errado == 0 else "conferir",
    f"censurados por safra {c20}; preenchidos na Bronze sem conversão válida {convertidos_errado}; nulos na Silver {nao_convertidos}",
    "todo YearsCode preenchido convertido para 0 a 50",
    sum(v["menos_de_1"] + v["mais_de_50_texto"] + v["acima_de_50_numerico"] for v in c20.values()),
    "problema_real", "baixa",
    "Less than 1 year → 0; More than 50 years (2022 a 2024) e valores numéricos acima de 50 (2025) → 50. "
    "Valores censurados: estatísticas de anos subestimam a cauda superior.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Estrutural e tempestividade

# COMMAND ----------

# C21: o primeiro registro da resposta do SIDRA é cabeçalho.
cabecalhos = {}
for codigo in ["9471", "5434"]:
    bronze = spark.table(f"{CATALOGO}.bronze.ibge_sidra_{codigo}")
    cabecalhos[codigo] = (
        bronze.filter((F.col("_ordem_registro") == 0) & F.expr("try_cast(replace(V, ',', '.') AS DOUBLE) IS NULL")).count()
    )
silver_menos_um = ocupados.count() == spark.table(f"{CATALOGO}.bronze.ibge_sidra_5434").count() - 1
registrar(
    "C21", "bronze", "bronze.ibge_sidra_9471, bronze.ibge_sidra_5434", "d[0]", "Estrutural", "Validade",
    "aprovado" if cabecalhos == {"9471": 1, "5434": 1} and silver_menos_um else "reprovado",
    f"registros de cabeçalho não numéricos {cabecalhos}; Silver 5434 = Bronze menos 1: {silver_menos_um}",
    "1 cabeçalho por tabela na Bronze; ausente na Silver",
    2,
    "problema_real", "média",
    "Cabeçalho preservado na Bronze (_ordem_registro = 0) e descartado na Silver.",
)

# COMMAND ----------

# C22: defasagem temporal entre as fontes.
ultima_safra = respondente.agg(F.max("safra")).first()[0]
ano_teletrabalho = tele.agg(F.max("ano")).first()[0]
ultimo_trimestre = ocupados.agg(F.max("periodo_codigo")).first()[0]
registrar(
    "C22", "silver", "silver.so_respondente, silver.ibge_teletrabalho_uf, silver.ibge_ocupados_uf_atividade",
    "período de referência", "Tempestividade", "Tempestividade",
    "registrado",
    f"última safra da pesquisa {ultima_safra}; teletrabalho IBGE {ano_teletrabalho} (4º trimestre); "
    f"último trimestre da 5434 {ultimo_trimestre}; defasagem pesquisa × teletrabalho {ultima_safra - ano_teletrabalho} anos",
    "teletrabalho só em 2022, sem série; pesquisa até 2025",
    None,
    "problema_real", "média",
    "Q8 declara que aplica taxa de 2022 a ocupação de 2022T4; tendência posterior vem só da pesquisa, que não é probabilística.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Consistência entre recortes do IBGE
# MAGIC
# MAGIC As categorias das duas tabelas do IBGE não são aditivas. Somar sem conhecer a hierarquia conta a mesma pessoa
# MAGIC mais de uma vez. Estas verificações confirmam a hierarquia no dado.

# COMMAND ----------

# C23: 9471. Teletrabalho no domicílio (59806) e fora do domicílio (59807) se sobrepõem em "no domicílio e fora"
# (59808): 59806 + 59807 - 59808 = 59805. E teletrabalho (59805) está contido em trabalho remoto (59804), que está
# contido no total (59803). Tolerância de 2 mil: quatro valores arredondados a inteiro, cada um com erro de até 0,5.
TOLERANCIA_C23 = 2.0
pessoas_por_modalidade = (
    tele.groupBy("nivel_territorial", "uf_codigo").pivot("modalidade_codigo").agg(F.first("pessoas_mil")).collect()
)
# A identidade usa 59807 e 59808, que o IBGE declara disponíveis só para Brasil e Grande Região (C28): ela é verificada
# no Brasil. A ordem 59805 <= 59804 <= 59803 usa categorias disponíveis por UF e é verificada nos 28 territórios.
desvios_c23, violacoes_ordem = [], 0
for linha in pessoas_por_modalidade:
    if linha["nivel_territorial"] == "pais":
        desvios_c23.append(linha["59806"] + linha["59807"] - linha["59808"] - linha["59805"])
    if not (linha["59805"] <= linha["59804"] <= linha["59803"]):
        violacoes_ordem += 1
maior_desvio = max(abs(d) for d in desvios_c23)
registrar(
    "C23", "silver", "silver.ibge_teletrabalho_uf", "pessoas_mil por modalidade (c1675)", "Consistência", "Consistência",
    "aprovado" if maior_desvio <= TOLERANCIA_C23 and violacoes_ordem == 0 else "reprovado",
    f"identidade 59806+59807-59808-59805 no Brasil: desvio {maior_desvio}; "
    f"violações de 59805 <= 59804 <= 59803 em {len(pessoas_por_modalidade)} territórios: {violacoes_ordem}",
    f"desvio <= {TOLERANCIA_C23} mil (arredondamento) e 0 violações de ordem",
    violacoes_ordem,
    "problema_real", "alta",
    "Modalidades não se somam: views filtram um código por vez; dim_modalidade_ibge declara a hierarquia. A "
    "identidade por UF não é verificada porque 59807 e 59808 não estão disponíveis por UF segundo o IBGE (C28).",
)

# COMMAND ----------

# C24: 5434. O grupamento 47946 (Total) é a soma dos grupamentos de primeiro nível, e 60031 (Indústria de
# transformação) está contido em 47948 (Indústria geral). Tolerância de 5,5 mil: onze valores arredondados.
TOLERANCIA_C24 = 5.5
CODIGO_TOTAL_5434 = "47946"
CODIGO_INDUSTRIA_GERAL = "47948"
CODIGO_INDUSTRIA_TRANSFORMACAO = "60031"
hierarquia = (
    ocupados.groupBy("uf_codigo", "periodo_codigo")
    .agg(
        F.sum(F.when(~F.col("atividade_codigo").isin(CODIGO_TOTAL_5434, CODIGO_INDUSTRIA_TRANSFORMACAO), F.col("pessoas_mil"))).alias("nivel1"),
        F.max(F.when(F.col("atividade_codigo") == CODIGO_TOTAL_5434, F.col("pessoas_mil"))).alias("total"),
        F.max(F.when(F.col("atividade_codigo") == CODIGO_INDUSTRIA_GERAL, F.col("pessoas_mil"))).alias("geral"),
        F.max(F.when(F.col("atividade_codigo") == CODIGO_INDUSTRIA_TRANSFORMACAO, F.col("pessoas_mil"))).alias("transformacao"),
    )
    .agg(
        F.count(F.lit(1)).alias("combinacoes"),
        F.max(F.abs(F.col("nivel1") - F.col("total"))).alias("maior_desvio"),
        F.sum((F.col("transformacao") > F.col("geral")).cast("int")).alias("violacoes"),
    )
    .first()
)
registrar(
    "C24", "silver", "silver.ibge_ocupados_uf_atividade", "pessoas_mil por grupamento (c888)", "Consistência", "Consistência",
    "aprovado" if hierarquia["maior_desvio"] <= TOLERANCIA_C24 and hierarquia["violacoes"] == 0 else "reprovado",
    f"{hierarquia['combinacoes']} combinações UF × trimestre; maior desvio entre Total e soma do primeiro nível "
    f"{hierarquia['maior_desvio']}; transformação maior que indústria geral {hierarquia['violacoes']}",
    f"desvio <= {TOLERANCIA_C24} mil (arredondamento) e 0 violações",
    hierarquia["violacoes"],
    "problema_real", "alta",
    "Grupamentos não se somam livremente: Total e Indústria de transformação ficam fora de qualquer soma; "
    "dim_atividade_economica marca e_total e e_subgrupamento.",
)

# COMMAND ----------

# C25: universo das duas tabelas do IBGE no mesmo período (2022, 4º trimestre).
total_9471 = tele.filter((F.col("nivel_territorial") == "pais") & (F.col("modalidade_codigo") == "59803")).first()["pessoas_mil"]
total_5434 = (
    ocupados.filter((F.col("periodo_codigo") == "202204") & (F.col("atividade_codigo") == CODIGO_TOTAL_5434))
    .agg(F.sum("pessoas_mil")).first()[0]
)
registrar(
    "C25", "silver", "silver.ibge_teletrabalho_uf × silver.ibge_ocupados_uf_atividade", "total de ocupados em 2022T4",
    "Consistência", "Consistência",
    "medido",
    f"9471 (Brasil) {total_9471} mil; 5434 (soma das UFs) {total_5434} mil; diferença {total_5434 - total_9471} mil "
    f"({round(100 * (total_5434 - total_9471) / total_9471, 2)}%)",
    "sem valor fixado; as tabelas vêm de divulgações diferentes da PNAD Contínua",
    None,
    "problema_real", "média",
    "A nota da 9471 exclui as pessoas ocupadas afastadas do trabalho e a 5434 foi reponderada em 2025 (Nota Técnica "
    "02/2025), ambas registradas no SIDRA (docs/referencias.md §6.8); a diferença é compatível com isso, sem "
    "decomposição medida. A Q8 aplica razões entre tabelas, nunca soma níveis.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Não resposta de `RemoteWork` em 2025

# COMMAND ----------

# C26: estrutura da não resposta de RemoteWork entre quem trabalha em 2025 (o C02 mede a magnitude).
# Mede se o nulo vem junto de outras perguntas sobre a organização (OrgSize e ICorPM), se quem deixou esse bloco em
# branco respondeu perguntas de outros temas (o que afasta abandono simples do questionário) e como o nulo se divide
# por vínculo. A ordem das perguntas não é medida: o schema.csv de 2025 lista subitens antes das perguntas-mãe, então a
# ordem das linhas do arquivo não é a ordem de exibição, e a lógica de exibição do questionário não está nos dados.
SAFRA_NAO_RESPOSTA = 2025
BLOCO_ORGANIZACAO = ["OrgSize", "ICorPM"]
PERGUNTAS_OUTROS_TEMAS = [
    "PurchaseInfluence", "Industry", "JobSat", "Country", "Currency", "LanguageHaveWorkedWith", "DatabaseHaveWorkedWith",
]

bronze_nao_resposta = bronze_so(SAFRA_NAO_RESPOSTA)
ausentes = [c for c in BLOCO_ORGANIZACAO + PERGUNTAS_OUTROS_TEMAS if c not in bronze_nao_resposta.columns]
if ausentes:
    raise ValueError(f"C26: colunas ausentes em {SAFRA_NAO_RESPOSTA}: {ausentes}")

nulo_rw = F.col("arranjo_trabalho") == "Não informado"
bloco_vazio = ~reduce(lambda a, b: a | b, [preenchido(c) for c in BLOCO_ORGANIZACAO])
responde_outros_temas = reduce(lambda a, b: a | b, [preenchido(c) for c in PERGUNTAS_OUTROS_TEMAS])
autonomo_so = F.col("autonomo") & ~F.col("empregado")

c26 = (
    respondente.filter((F.col("safra") == SAFRA_NAO_RESPOSTA) & F.col("trabalhando"))
    .join(
        bronze_nao_resposta.select(
            F.expr("try_cast(ResponseId AS BIGINT)").alias("resposta_id"), *BLOCO_ORGANIZACAO, *PERGUNTAS_OUTROS_TEMAS
        ),
        "resposta_id",
    )
    .agg(
        F.count(F.lit(1)).alias("trabalhando"),
        F.sum(nulo_rw.cast("int")).alias("nulos"),
        F.sum(F.col("empregado").cast("int")).alias("empregados"),
        F.sum((F.col("empregado") & nulo_rw).cast("int")).alias("nulos_empregados"),
        F.sum(autonomo_so.cast("int")).alias("autonomos"),
        F.sum((autonomo_so & nulo_rw).cast("int")).alias("nulos_autonomos"),
        F.sum((nulo_rw & bloco_vazio).cast("int")).alias("nulos_com_bloco_vazio"),
        F.sum((nulo_rw & bloco_vazio & responde_outros_temas).cast("int")).alias("bloco_vazio_responde_outros_temas"),
    )
    .first()
    .asDict()
)
if c26["trabalhando"] != respondente.filter((F.col("safra") == SAFRA_NAO_RESPOSTA) & F.col("trabalhando")).count():
    raise AssertionError("C26: o join por resposta_id perdeu linhas de quem trabalha.")
medido_c26 = {
    "trabalhando": c26["trabalhando"],
    "nulos": c26["nulos"],
    "% nulo entre empregados": pct(c26["nulos_empregados"], c26["empregados"]),
    "% nulo entre autônomos sem vínculo de empregado": pct(c26["nulos_autonomos"], c26["autonomos"]),
    "nulos com OrgSize e ICorPM também vazios": c26["nulos_com_bloco_vazio"],
    "desses, com resposta a pergunta de outro tema": c26["bloco_vazio_responde_outros_temas"],
    "empregados": c26["empregados"],
    "nulos_empregados": c26["nulos_empregados"],
    "autônomos": c26["autonomos"],
    "nulos_autônomos": c26["nulos_autonomos"],
}
registrar(
    "C26", "silver", "silver.so_respondente × bronze.so_pesquisa_2025", "RemoteWork 2025 (estrutura do nulo)",
    "Completude", "Completude",
    "medido",
    str(medido_c26),
    "sem valor fixado; descreve a estrutura da não resposta medida no C02",
    c26["nulos"],
    "problema_real", "alta",
    "Leitura na view gold.vw_q1_remoto_por_vinculo: série por vínculo nas duas classificações de quem marcou empregado "
    "e autônomo, padronizada pela composição de 2024 e com limites para os nulos. O dado não mostra a lógica de "
    "exibição do questionário de 2025.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sinais e disponibilidade do IBGE

# COMMAND ----------

# C27: células omitidas por sigilo (sinal x: "Dado numérico omitido a fim de evitar a individualização da
# informação"). É ausência deliberada da fonte, diferente de não disponível (...) e de não se aplica (..).
COLUNAS_SINAL_9471 = ["pessoas_mil_sinal", "cv_pessoas_sinal", "percentual_sinal", "cv_percentual_sinal"]
sigilo = {
    "9471": sum(tele.filter(F.col(c) == "x").count() for c in COLUNAS_SINAL_9471),
    "5434": ocupados.filter(F.col("pessoas_mil_sinal") == "x").count(),
}
outros_sinais = {
    "9471": {c: {l[c]: l["count"] for l in tele.filter(F.col(c).isNotNull()).groupBy(c).count().collect()} for c in COLUNAS_SINAL_9471},
    "5434": {l["pessoas_mil_sinal"]: l["count"] for l in ocupados.filter(F.col("pessoas_mil_sinal").isNotNull()).groupBy("pessoas_mil_sinal").count().collect()},
}
# A guarda: toda célula marcada com x precisa ter o valor nulo. Número ao lado de um x seria erro de leitura do sinal.
x_com_valor = sum(
    tele.filter((F.col(c) == "x") & F.col(c.removesuffix("_sinal")).isNotNull()).count() for c in COLUNAS_SINAL_9471
) + ocupados.filter((F.col("pessoas_mil_sinal") == "x") & F.col("pessoas_mil").isNotNull()).count()
registrar(
    "C27", "silver", "silver.ibge_teletrabalho_uf, silver.ibge_ocupados_uf_atividade", "sinal x (sigilo)",
    "Completude", "Completude",
    "aprovado" if x_com_valor == 0 else "reprovado",
    f"células com x por tabela {sigilo}; células com x e valor preenchido {x_com_valor}; sinais presentes por coluna {outros_sinais}",
    "toda célula com x tem o valor nulo (0 células com x e valor preenchido)",
    sum(sigilo.values()),
    "guarda_defensiva", "média",
    "Célula com x fica com valor nulo e sinal x; nenhuma view consome as colunas de sinal, e agregações ignoram o nulo.",
)

# COMMAND ----------

# C28: disponibilidade territorial declarada pelo IBGE. A nota da tabela 9471 diz que a classificação "está disponível
# apenas para os níveis territoriais Brasil e Grande Região nas categorias Realizou teletrabalho fora do domicílio e
# Realizou teletrabalho no domicílio e fora do domicílio". Mede quantas linhas por UF dessas categorias a API entregou.
indisponiveis = tele.filter(~F.col("disponivel_no_nivel"))
com_valor = indisponiveis.filter(F.col("pessoas_mil").isNotNull()).count()
registrar(
    "C28", "silver", "silver.ibge_teletrabalho_uf", "disponivel_no_nivel (59807 e 59808 por UF)", "Validade", "Validade",
    "medido",
    f"linhas fora da disponibilidade declarada {indisponiveis.count()}; com valor numérico {com_valor}",
    "sem valor fixado; o IBGE declara as duas categorias só para Brasil e Grande Região",
    indisponiveis.count(),
    "problema_real", "média",
    "Linhas mantidas na Silver e na Gold com disponivel_no_nivel = false; a view Q6 e as verificações C13 e C23 as excluem.",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Hipóteses testadas para a diferença do C16 e perda de informação na Silver

# COMMAND ----------

# C29: hipóteses para a diferença de 182 linhas entre o CSV de 2025 e as respostas qualificadas publicadas.
# Cada hipótese é uma contagem no microdado; a que der 182 explica a diferença.
b25 = bronze_so(2025)
colunas_resposta = [c for c in b25.columns if c not in ("ResponseId",) and not c.startswith("_")]
n_preenchidas = reduce(lambda a, b: a + b, [preenchido(c).cast("int") for c in colunas_resposta])
b25_n = b25.withColumn("_n_preenchidas", n_preenchidas)
hipoteses = {
    "linhas sem nenhuma resposta": b25_n.filter(F.col("_n_preenchidas") == 0).count(),
    "linhas com MainBranch vazio": b25.filter(~preenchido("MainBranch")).count(),
    "linhas com até três respostas": b25_n.filter(F.col("_n_preenchidas") <= 3).count(),
    "ResponseId repetido": b25.groupBy("ResponseId").count().filter(F.col("count") > 1).count(),
}
explica = [h for h, n in hipoteses.items() if n == LINHAS_CSV_2025 - RESPOSTAS_PUBLICADAS_2025]
registrar(
    "C29", "bronze", "bronze.so_pesquisa_2025", "hipóteses para a diferença do C16", "Integridade", "Consistência",
    "medido",
    f"{hipoteses}; hipóteses que igualam a diferença de 182: {explica or 'nenhuma'}",
    "sem valor fixado; a hipótese que igualar 182 explica a diferença",
    len(explica),
    "problema_real", "baixa",
    "Contagens registradas. Sem hipótese que iguale a diferença, o pipeline segue usando as linhas do CSV (C16) e a "
    "diferença continua declarada sem causa atribuída.",
)

# COMMAND ----------

# C30: perda de informação em perfil_principal. DevType é multi-resposta em 2022 e resposta única depois; a Silver
# guarda só o primeiro valor. Mede quantos respondentes de 2022 tinham mais de um valor e quantos valores foram
# descartados, e confirma que nas outras safras não há perda.
def valores_devtype(safra: int):
    df = bronze_so(safra).filter(preenchido("DevType"))
    return df.select(F.size(F.split(F.col("DevType"), ";")).alias("n_valores"))

perda = {}
for s_ in SAFRAS:
    v = valores_devtype(s_)
    agg = v.agg(
        F.count(F.lit(1)).alias("informados"),
        F.sum((F.col("n_valores") > 1).cast("int")).alias("multi"),
        F.sum(F.col("n_valores") - 1).alias("descartados"),
        F.max("n_valores").alias("max_valores"),
    ).collect()[0]
    perda[s_] = (int(agg["informados"]), int(agg["multi"]), int(agg["descartados"]), int(agg["max_valores"]))
sem_perda_depois = all(perda[s_][1] == 0 for s_ in SAFRAS if s_ != 2022)
registrar(
    "C30", "silver", "silver.so_respondente", "perfil_principal (DevType multi-resposta)", "Completude", "Completude",
    "medido" if sem_perda_depois else "reprovado",
    f"(informados, com mais de um valor, valores descartados, máximo de valores) por safra {perda}",
    "multi-resposta só em 2022; zero respondentes com mais de um valor de 2023 a 2025",
    perda[2022][1],
    "problema_real", "média",
    "A Q4 usa o primeiro valor listado em 2022 e declara que perfis de 2022 não se comparam aos das safras seguintes. "
    "A alternativa registrada é uma tabela ponte para 2022 (docs/referencias.md §2.2).",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Persistência em `gold.verificacoes_qualidade`

# COMMAND ----------

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {CATALOGO}.gold.verificacoes_qualidade (
      verificacao_id STRING,
      camada STRING,
      tabela STRING,
      atributo STRING,
      dimensao_qualidade STRING,
      dimensao_dama STRING,
      resultado STRING,
      valor_medido STRING,
      linhas_afetadas BIGINT,
      classificacao STRING,
      tipo_regra STRING,
      severidade STRING,
      tratamento STRING,
      executado_em TIMESTAMP
    )
    USING DELTA
    """
)

# Tabela criada antes da coluna tipo_regra existir: acrescenta a coluna uma vez, sem apagar o histórico.
if "tipo_regra" not in spark.table(f"{CATALOGO}.gold.verificacoes_qualidade").columns:
    spark.sql(f"ALTER TABLE {CATALOGO}.gold.verificacoes_qualidade ADD COLUMNS (tipo_regra STRING AFTER classificacao)")
    spark.sql(
        f"UPDATE {CATALOGO}.gold.verificacoes_qualidade SET tipo_regra = 'regra' WHERE verificacao_id LIKE 'C15%'"
    )

schema_verificações = spark.table(f"{CATALOGO}.gold.verificacoes_qualidade").schema
# Tuplas na ordem do schema: não depende de como o Spark Connect casa chaves de dict com colunas.
linhas_verificações = [tuple(c[campo.name] for campo in schema_verificações.fields) for c in verificações]
spark.createDataFrame(linhas_verificações, schema_verificações).createOrReplaceTempView("_verificacoes_05")

# Persiste os resultados desta etapa antes do MERGE de estado atual e da validação final.
# Repetir uma tentativa do mesmo job substitui seus verificações, sem duplicar ou apagar C15.
JOB_RUN_ID = persistir_historico(spark, spark.table("_verificacoes_05"), JOB_RUN_ID)

# Atualiza as verificações deste notebook e remove as que deixaram de existir, sem tocar nos da camada gold (notebook 07).
spark.sql(
    f"""
    MERGE INTO {CATALOGO}.gold.verificacoes_qualidade AS t
    USING _verificacoes_05 AS s
    ON t.verificacao_id = s.verificacao_id
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
    WHEN NOT MATCHED BY SOURCE AND t.camada <> 'gold' THEN DELETE
    """
)

# Regras gravadas na própria tabela: o Delta recusa qualquer escrita futura com valor fora do domínio.
for nome, regra in {
    "ck_verificacao_resultado": "resultado IN ('aprovado', 'reprovado', 'conferir', 'explicado', 'medido', 'registrado')",
    "ck_verificacao_classificacao": "classificacao IN ('problema_real', 'guarda_defensiva')",
    "ck_verificacao_tipo_regra": "tipo_regra IN ('regra', 'referencia_externa', 'retrato_da_extracao')",
}.items():
    spark.sql(f"ALTER TABLE {CATALOGO}.gold.verificacoes_qualidade DROP CONSTRAINT IF EXISTS {nome}")
    spark.sql(f"ALTER TABLE {CATALOGO}.gold.verificacoes_qualidade ADD CONSTRAINT {nome} CHECK ({regra})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidência
# MAGIC

# COMMAND ----------

display(spark.sql(f"SELECT * FROM {CATALOGO}.gold.verificacoes_qualidade ORDER BY verificacao_id"))

# COMMAND ----------

# Checagem final, depois de gravar:
# 1. o conjunto de verificações tem de ser o de CHECKS_DECLARADOS; verificação a menos ou a mais é erro de código;
# 2. resultado e classificação ficam nos domínios definidos;
# 3. qualquer `reprovado` para o notebook; uma `guarda_defensiva` em `conferir` também, porque uma guarda sem
#    resultado não protege nada. Um `problema_real` em `conferir` só fica registrado.
CHECKS_DECLARADOS = {f"C{i:02d}" for i in range(1, 31)} - {"C15"}  # C15 nasce no notebook 07
DOMINIO_RESULTADO = {"aprovado", "reprovado", "conferir", "explicado", "medido", "registrado"}
DOMINIO_CLASSIFICACAO = {"problema_real", "guarda_defensiva"}

ids = {c["verificacao_id"] for c in verificações}
if ids != CHECKS_DECLARADOS:
    raise AssertionError(f"conjunto de verificações diferente do declarado: faltam {CHECKS_DECLARADOS - ids}, sobram {ids - CHECKS_DECLARADOS}")
fora_do_dominio = [c["verificacao_id"] for c in verificações if c["resultado"] not in DOMINIO_RESULTADO or c["classificacao"] not in DOMINIO_CLASSIFICACAO]
if fora_do_dominio:
    raise AssertionError(f"resultado ou classificação fora do domínio: {fora_do_dominio}")
reprovados = [c["verificacao_id"] for c in verificações if c["resultado"] == "reprovado"]
guardas_sem_veredito = [c["verificacao_id"] for c in verificações if c["classificacao"] == "guarda_defensiva" and c["resultado"] == "conferir"]
if reprovados or guardas_sem_veredito:
    raise AssertionError(
        f"Verificações reprovadas: {reprovados}; guardas defensivas sem veredito: {guardas_sem_veredito}. Os valores esperados "
        "foram medidos no dado real: divergência indica erro de código ou arquivo diferente do medido. O registro já "
        "está gravado em gold.verificacoes_qualidade."
    )
print(f"{len(verificações)} verificações gravadas; nenhuma reprovada; nenhuma guarda defensiva sem veredito.")
